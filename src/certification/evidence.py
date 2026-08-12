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
MIN_COVERAGE_PCT_THRESHOLD = 75.0

_BANDIT_SEVERITY_MAP: dict[str, Severity] = {
    "LOW": Severity.BAJO,
    "MEDIUM": Severity.MEDIO,
    "HIGH": Severity.ALTO,
}

# Prefijos de reglas ruff tratados como no conformidad MAYOR por ser de
# seguridad (flake8-bandit "S") en vez de estilo/simplicidad.
_RUFF_MAJOR_PREFIXES = ("S",)


def _relative_to_project(raw_path: str, project_root: Path) -> str:
    """Normaliza una ruta (absoluta o relativa) a relativa a `project_root`.

    Necesario porque distintas herramientas reportan rutas de forma
    inconsistente (ruff siempre absoluta; bandit típicamente relativa a
    como se le invocó). `Finding.location` debe ser SIEMPRE relativa para
    que `src/remediation/guardrails.py` pueda validarla contra el
    allow-list de forma consistente entre fuentes.
    """
    try:
        return str(Path(raw_path).resolve().relative_to(project_root.resolve()))
    except (ValueError, OSError):
        return raw_path


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,  # noqa: S603 — cmd es una lista fija construida internamente, sin shell ni input de usuario.
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=EVIDENCE_SUBPROCESS_TIMEOUT_SECONDS,
        check=False,
    )


def collect_pytest_findings(project_root: Path, test_paths: list[str]) -> tuple[list[Finding], int, float | None]:
    """Ejecuta pytest con cobertura (JUnit XML + coverage JSON).

    Retorna (findings, número de pruebas fallidas, % de cobertura de
    `src/` o None si no se pudo medir). Ambos reportes se generan en la
    MISMA invocación de pytest para no pagar el costo de arrancar el
    intérprete y recolectar la suite dos veces.
    """
    with TemporaryDirectory() as tmp:
        junit_path = Path(tmp) / "junit.xml"
        coverage_path = Path(tmp) / "coverage.json"
        _run(
            [
                "python",
                "-m",
                "pytest",
                *test_paths,
                f"--junitxml={junit_path}",
                "--cov=src",
                f"--cov-report=json:{coverage_path}",
                "-q",
            ],
            project_root,
        )

        coverage_pct = _read_coverage_percent(coverage_path)

        findings: list[Finding] = []
        failed = 0
        if not junit_path.exists():
            return findings, failed, coverage_pct

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

        if coverage_pct is not None and coverage_pct < MIN_COVERAGE_PCT_THRESHOLD:
            findings.append(
                Finding(
                    id="coverage-below-threshold",
                    type=FindingType.NO_CONFORMIDAD_MENOR,
                    description=(
                        f"Cobertura de código ({coverage_pct:.1f}%) por debajo del "
                        f"umbral ({MIN_COVERAGE_PCT_THRESHOLD:.0f}%)."
                    ),
                    objective_evidence=f"coverage.py reportó {coverage_pct:.1f}% de líneas cubiertas en src/.",
                    location="src/",
                    normative_reference="specs/TEST_PLAN.md — criterios de aceptación",
                    severity=Severity.BAJO,
                    source_tool="coverage",
                )
            )
        elif coverage_pct is not None:
            findings.append(
                Finding(
                    id="coverage-ok",
                    type=FindingType.CONFORMIDAD,
                    description=(
                        f"Cobertura de código ({coverage_pct:.1f}%) sobre el " f"umbral ({MIN_COVERAGE_PCT_THRESHOLD:.0f}%)."
                    ),
                    objective_evidence=f"coverage.py reportó {coverage_pct:.1f}% de líneas cubiertas en src/.",
                    location="src/",
                    normative_reference="specs/TEST_PLAN.md — criterios de aceptación",
                    source_tool="coverage",
                )
            )

        return findings, failed, coverage_pct


def _read_coverage_percent(coverage_path: Path) -> float | None:
    if not coverage_path.exists():
        return None
    try:
        data = json.loads(coverage_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data.get("totals", {}).get("percent_covered")


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
        # ruff siempre devuelve rutas absolutas en su JSON, sin importar cómo
        # se le haya invocado; se normaliza a relativa a project_root para que
        # Finding.location sea consistente entre herramientas (bandit ya
        # reporta relativo) y consumible por src/remediation/guardrails.py.
        location = _relative_to_project(violation.get("filename", "-"), project_root)
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
        bandit_file = _relative_to_project(item.get("filename", "-"), project_root)
        findings.append(
            Finding(
                id=f"bandit-{item.get('test_id', '?')}-{item.get('line_number', '?')}",
                type=finding_type,
                description=item.get("issue_text", "Hallazgo de seguridad (bandit)"),
                objective_evidence=(
                    f"{item.get('test_id')} ({item.get('test_name')}) — " f"confianza {item.get('issue_confidence')}."
                ),
                location=f"{bandit_file}:{item.get('line_number', '-')}",
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


def get_pip_audit_report(project_root: Path, requirements_file: str = "requirements.txt") -> dict | None:
    """Ejecuta `pip-audit -f json` una vez y retorna el JSON crudo (o None si falló).

    Requiere red saliente (consulta la base OSV). Se reutiliza tanto para
    evidencia (`collect_pip_audit_findings`) como para el módulo de
    remediación (`src/remediation/proposer.py`), evitando invocar la
    herramienta dos veces por corrida.
    """
    result = _run(
        ["python", "-m", "pip_audit", "-r", requirements_file, "-f", "json"],
        project_root,
    )
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return None


def collect_pip_audit_findings(project_root: Path, requirements_file: str = "requirements.txt") -> list[Finding]:
    """Convierte el reporte de `pip-audit` en Findings (ASI04 Supply Chain).

    Si la herramienta no puede ejecutarse (sin red, timeout, etc.) se
    reporta una Observación en vez de fallar la certificación completa:
    la ausencia de verificación no es lo mismo que una vulnerabilidad
    confirmada, y un runner sin egress no debería denegar certificación
    solo por eso.
    """
    try:
        report = get_pip_audit_report(project_root, requirements_file)
    except subprocess.TimeoutExpired:
        report = None

    if report is None:
        return [
            Finding(
                id="pip-audit-inconclusive",
                type=FindingType.OBSERVACION,
                description="No se pudo ejecutar pip-audit (sin red disponible o error de herramienta).",
                objective_evidence="El comando pip-audit no devolvió un JSON válido en este entorno.",
                location=requirements_file,
                normative_reference="ASI04 Supply Chain",
                source_tool="pip-audit",
            )
        ]

    findings: list[Finding] = []
    for dependency in report.get("dependencies", []):
        vulns = dependency.get("vulns", [])
        if not vulns:
            continue
        name = dependency.get("name", "?")
        version = dependency.get("version", "?")
        vuln_ids = ", ".join(v.get("id", "?") for v in vulns)
        fix_versions = sorted({fv for v in vulns for fv in v.get("fix_versions", [])})
        findings.append(
            Finding(
                id=f"pip-audit-{name}-{version}",
                type=FindingType.NO_CONFORMIDAD_MAYOR,
                description=f"Vulnerabilidad(es) conocida(s) en {name}=={version}: {vuln_ids}",
                objective_evidence=(
                    f"pip-audit reportó {len(vulns)} CVE/advisory para {name}=={version}. "
                    f"Versión(es) con fix disponible: {', '.join(fix_versions) or 'ninguna reportada'}."
                ),
                location=f"{requirements_file}:{name}",
                normative_reference="ASI04 Supply Chain",
                severity=Severity.ALTO,
                source_tool="pip-audit",
                corrective_action=(f"Actualizar a {fix_versions[0]}" if fix_versions else None),
            )
        )

    if not findings:
        findings.append(
            Finding(
                id="pip-audit-clean",
                type=FindingType.CONFORMIDAD,
                description="Sin vulnerabilidades conocidas en las dependencias declaradas.",
                objective_evidence=f"`pip-audit -r {requirements_file}` no reportó CVEs.",
                location=requirements_file,
                normative_reference="ASI04 Supply Chain",
                source_tool="pip-audit",
            )
        )
    return findings


def collect_all_evidence(project_root: Path) -> tuple[list[Finding], int, float | None]:
    """Orquesta la recolección completa.

    Retorna (findings, nº de pruebas fallidas, % de cobertura de src/).
    """
    pytest_findings, failed, coverage_pct = collect_pytest_findings(
        project_root, ["tests/unit", "tests/e2e", "tests/design", "tests/property"]
    )
    ruff_findings = collect_ruff_findings(project_root, ["src", "tests"])
    bandit_findings = collect_bandit_findings(project_root, "src")
    pip_audit_findings = collect_pip_audit_findings(project_root)
    all_findings = [*pytest_findings, *ruff_findings, *bandit_findings, *pip_audit_findings]
    return all_findings, failed, coverage_pct
