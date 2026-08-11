"""Obtención de evidencias y registro de resultados (ver contexto/data 2.3.1).

Ejecuta las herramientas ya usadas en el pipeline (pytest, ruff, bandit) y
convierte su salida cruda en `Finding` estructurados y trazables: cada uno
con evidencia objetiva, ubicación exacta y referencia normativa, tal como
exige la estructura de no conformidad de ISO/IEC 17021-1 (ver
contexto/data 2.4.1).

Todas las invocaciones de subproceso usan listas fijas (nunca `shell=True`)
y timeout explícito (ASI08 — circuit breaker / mitigación de cascading
failures).
"""

from __future__ import annotations

import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from tempfile import TemporaryDirectory

from src.certification.models import Finding, FindingType, Severity

EVIDENCE_SUBPROCESS_TIMEOUT_SECONDS = 120

_BANDIT_SEVERITY_MAP: dict[str, Severity] = {
    "LOW": Severity.BAJO,
    "MEDIUM": Severity.MEDIO,
    "HIGH": Severity.ALTO,
}

# Prefijos de reglas ruff tratados como no conformidad MAYOR por ser de
# seguridad (flake8-bandit "S") en vez de estilo/simplicidad.
_RUFF_MAJOR_PREFIXES = ("S",)


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,  # noqa: S603 — cmd es una lista fija construida internamente, sin shell ni input de usuario.
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=EVIDENCE_SUBPROCESS_TIMEOUT_SECONDS,
        check=False,
    )


def collect_pytest_findings(project_root: Path, test_paths: list[str]) -> tuple[list[Finding], int]:
    """Ejecuta pytest (JUnit XML) y retorna (findings, número de pruebas fallidas)."""
    with TemporaryDirectory() as tmp:
        junit_path = Path(tmp) / "junit.xml"
        _run(["python", "-m", "pytest", *test_paths, f"--junitxml={junit_path}", "-q"], project_root)

        findings: list[Finding] = []
        failed = 0
        if not junit_path.exists():
            return findings, failed

        # El XML lo genera nuestro propio proceso pytest (no es input externo
        # no confiable), por lo que xml.etree es aceptable aquí sin defusedxml.
        root = ET.parse(junit_path).getroot()  # noqa: S314
        suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))

        for suite in suites:
            for case in suite.findall("testcase"):
                name = f"{case.get('classname', '')}::{case.get('name', '')}"
                node = case.find("failure")
                if node is None:
                    node = case.find("error")
                if node is None:
                    continue
                failed += 1
                findings.append(
                    Finding(
                        id=f"pytest-{name}",
                        type=FindingType.NO_CONFORMIDAD_MAYOR,
                        description=f"Prueba fallida: {name}",
                        objective_evidence=(node.get("message") or "sin mensaje")[:500],
                        location=name,
                        normative_reference="specs/TEST_PLAN.md — criterios de aceptación",
                        severity=Severity.ALTO,
                        source_tool="pytest",
                    )
                )

        total = sum(int(s.get("tests", 0)) for s in suites)
        if failed == 0 and total > 0:
            findings.append(
                Finding(
                    id="pytest-suite",
                    type=FindingType.CONFORMIDAD,
                    description=f"{total} caso(s) de prueba ejecutados sin fallos ni errores.",
                    objective_evidence=f"Suite completa: {total} pruebas, 0 fallos, 0 errores.",
                    location=", ".join(test_paths),
                    normative_reference="specs/TEST_PLAN.md — criterios de aceptación",
                    source_tool="pytest",
                )
            )
        return findings, failed


def collect_ruff_findings(project_root: Path, paths: list[str]) -> list[Finding]:
    """Ejecuta `ruff check --output-format json` y clasifica cada violación."""
    result = _run(["python", "-m", "ruff", "check", *paths, "--output-format", "json"], project_root)
    try:
        violations = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        violations = []

    findings: list[Finding] = []
    for violation in violations:
        code = violation.get("code") or "?"
        is_major = code.startswith(_RUFF_MAJOR_PREFIXES)
        location = violation.get("filename", "-")
        row = (violation.get("location") or {}).get("row")
        if row:
            location = f"{location}:{row}"
        findings.append(
            Finding(
                id=f"ruff-{code}-{location}",
                type=FindingType.NO_CONFORMIDAD_MAYOR if is_major else FindingType.NO_CONFORMIDAD_MENOR,
                description=f"[{code}] {violation.get('message', 'Hallazgo de lint')}",
                objective_evidence=f"`ruff check` reportó la regla '{code}' en {location}.",
                location=location,
                normative_reference="pyproject.toml [tool.ruff]" + (" / OWASP Top 10" if is_major else ""),
                severity=Severity.MEDIO if is_major else Severity.BAJO,
                source_tool="ruff",
            )
        )

    if not violations:
        findings.append(
            Finding(
                id="ruff-clean",
                type=FindingType.CONFORMIDAD,
                description="Sin hallazgos de lint/estilo/seguridad estática (ruff).",
                objective_evidence="`ruff check` retornó 0 violaciones.",
                location=", ".join(paths),
                normative_reference="pyproject.toml [tool.ruff]",
                source_tool="ruff",
            )
        )
    return findings


def collect_bandit_findings(project_root: Path, target: str = "src") -> list[Finding]:
    """Ejecuta `bandit -f json` y clasifica cada hallazgo por severidad."""
    result = _run(["python", "-m", "bandit", "-r", target, "-f", "json"], project_root)
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        data = {}

    results = data.get("results", [])
    findings: list[Finding] = []
    for item in results:
        severity = _BANDIT_SEVERITY_MAP.get(item.get("issue_severity", "LOW"), Severity.BAJO)
        finding_type = (
            FindingType.NO_CONFORMIDAD_MAYOR
            if severity in (Severity.ALTO, Severity.CRITICO)
            else FindingType.NO_CONFORMIDAD_MENOR
        )
        cwe_id = (item.get("issue_cwe") or {}).get("id", "-")
        findings.append(
            Finding(
                id=f"bandit-{item.get('test_id', '?')}-{item.get('line_number', '?')}",
                type=finding_type,
                description=item.get("issue_text", "Hallazgo de seguridad (bandit)"),
                objective_evidence=(
                    f"{item.get('test_id')} ({item.get('test_name')}) — " f"confianza {item.get('issue_confidence')}."
                ),
                location=f"{item.get('filename', '-')}:{item.get('line_number', '-')}",
                normative_reference=f"OWASP Top 10 / CWE-{cwe_id}",
                severity=severity,
                source_tool="bandit",
            )
        )

    if not results:
        findings.append(
            Finding(
                id="bandit-clean",
                type=FindingType.CONFORMIDAD,
                description="Sin hallazgos de seguridad estática (bandit).",
                objective_evidence=f"`bandit -r {target}` retornó 0 resultados.",
                location=target,
                normative_reference="OWASP Top 10",
                source_tool="bandit",
            )
        )
    return findings


def collect_all_evidence(project_root: Path) -> tuple[list[Finding], int]:
    """Orquesta la recolección completa. Retorna (findings, nº de pruebas fallidas)."""
    pytest_findings, failed = collect_pytest_findings(project_root, ["tests/unit", "tests/e2e", "tests/design"])
    ruff_findings = collect_ruff_findings(project_root, ["src", "tests"])
    bandit_findings = collect_bandit_findings(project_root, "src")
    return [*pytest_findings, *ruff_findings, *bandit_findings], failed
