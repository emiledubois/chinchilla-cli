"""Genera `ProposedFix` a partir de los `Finding` de un `CertificationReport`.

Solo dos estrategias, ambas deterministas y ya usadas en otras partes del
pipeline (nada de código generado libremente):

1. Hallazgos de `ruff` de tipo No Conformidad MENOR -> `ruff check --diff`
   (dry-run, no escribe nada) sobre el archivo puntual. Los hallazgos
   MAYORES (reglas de seguridad `S*`) quedan deliberadamente fuera: un
   fix automático de una regla de seguridad requiere criterio humano, no
   solo una transformación de estilo.
2. Hallazgos de `pip-audit` con una versión de arreglo conocida -> diff
   textual de la línea `paquete==version` correspondiente en
   requirements.txt. Aquí sí se permite sobre hallazgos MAYORES porque la
   acción es inequívoca (hay o no una versión sin la vulnerabilidad
   conocida), a diferencia de un fix de seguridad en código propio.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from src.certification.evidence import get_pip_audit_report
from src.certification.models import Finding, FindingType
from src.remediation.guardrails import is_target_allowed
from src.remediation.models import ProposedFix, RemediationTool

PROPOSAL_SUBPROCESS_TIMEOUT_SECONDS = 60
_REQUIREMENT_LINE_RE = re.compile(r"^([A-Za-z0-9_.-]+)==([A-Za-z0-9_.-]+)\s*$")


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,  # noqa: S603 — lista fija construida internamente, sin shell ni input de usuario.
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=PROPOSAL_SUBPROCESS_TIMEOUT_SECONDS,
        check=False,
    )


def propose_ruff_fix(finding: Finding, project_root: Path) -> ProposedFix | None:
    """Propone un fix para un hallazgo MENOR de ruff, vía `ruff check --diff`."""
    if finding.source_tool != "ruff" or finding.type != FindingType.NO_CONFORMIDAD_MENOR:
        return None

    target_file = finding.location.split(":")[0]
    if not is_target_allowed(target_file) or not (project_root / target_file).is_file():
        return None

    result = _run(["python", "-m", "ruff", "check", target_file, "--diff"], project_root)
    diff = result.stdout.strip()
    if not diff:
        return None  # nada auto-corregible (requiere intervención manual)

    return ProposedFix(
        finding_id=finding.id,
        tool=RemediationTool.RUFF_FIX,
        target_file=target_file,
        description=f"Aplicar auto-fix de ruff: {finding.description}"[:500],
        diff=diff[:20_000],
    )


def propose_dependency_bump(finding: Finding, project_root: Path) -> ProposedFix | None:
    """Propone actualizar una línea `paquete==version` en requirements.txt."""
    if finding.source_tool != "pip-audit":
        return None

    target_file = "requirements.txt"
    if not is_target_allowed(target_file):
        return None
    requirements_path = project_root / target_file
    if not requirements_path.is_file():
        return None

    package_name = finding.location.split(":", 1)[-1].strip()
    report = get_pip_audit_report(project_root, target_file)
    if report is None:
        return None

    fix_version = None
    for dependency in report.get("dependencies", []):
        if dependency.get("name", "").lower() != package_name.lower():
            continue
        fix_versions = sorted({fv for vuln in dependency.get("vulns", []) for fv in vuln.get("fix_versions", [])})
        if fix_versions:
            fix_version = fix_versions[0]
        break
    if fix_version is None:
        return None

    lines = requirements_path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        match = _REQUIREMENT_LINE_RE.match(line.strip())
        if match and match.group(1).lower() == package_name.lower():
            new_line = f"{match.group(1)}=={fix_version}"
            diff = f"--- {target_file}\n+++ {target_file}\n" f"@@ line {index + 1} @@\n-{line}\n+{new_line}\n"
            return ProposedFix(
                finding_id=finding.id,
                tool=RemediationTool.DEPENDENCY_BUMP,
                target_file=target_file,
                description=f"Actualizar {match.group(1)} a {fix_version} (corrige vulnerabilidad conocida)",
                diff=diff,
            )
    return None


def propose_fixes(findings: list[Finding], project_root: Path) -> list[ProposedFix]:
    """Orquesta ambas estrategias sobre una lista de hallazgos.

    `ruff --fix` opera a nivel de ARCHIVO completo, no por violación
    individual: si un archivo tiene 3 hallazgos ruff, corregir el primero
    ya corrige los 3. Sin deduplicar, se mostrarían 3 propuestas con el
    diff idéntico y aplicar cualquiera dejaría a las otras dos como
    no-ops confusos. Se deduplica por (herramienta, archivo objetivo),
    agregando en la descripción cuántos hallazgos cubre cada propuesta.
    """
    proposals_by_key: dict[tuple[RemediationTool, str], ProposedFix] = {}
    counts: dict[tuple[RemediationTool, str], int] = {}

    for finding in findings:
        proposal = propose_ruff_fix(finding, project_root) or propose_dependency_bump(finding, project_root)
        if proposal is None:
            continue
        key = (proposal.tool, proposal.target_file)
        counts[key] = counts.get(key, 0) + 1
        proposals_by_key.setdefault(key, proposal)

    proposals: list[ProposedFix] = []
    for key, proposal in proposals_by_key.items():
        count = counts[key]
        if count > 1:
            proposal = proposal.model_copy(
                update={"description": f"{proposal.description} (cubre {count} hallazgos en este archivo)"}
            )
        proposals.append(proposal)
    return proposals
