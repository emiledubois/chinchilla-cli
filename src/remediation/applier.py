"""Aplica un `ProposedFix` YA APROBADO por un humano.

Este módulo nunca pide confirmación por sí mismo — eso ocurre en
`src/cli.py::remediate`. Se limita a ejecutar, con guardrails de
alcance verificados de nuevo (defensa en profundidad), un cambio que
un humano ya vio como diff y aprobó explícitamente.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from src.remediation.guardrails import is_target_allowed
from src.remediation.models import ProposedFix, RemediationOutcome, RemediationTool
from src.utils.security import record_audit_event

APPLY_SUBPROCESS_TIMEOUT_SECONDS = 60


class RemediationScopeError(RuntimeError):
    """El fix propuesto intenta tocar un archivo fuera del alcance permitido,
    o su diff no se pudo aplicar de forma segura."""


def apply_fix(fix: ProposedFix, project_root: Path, *, actor: str = "preaudit-remediate") -> ProposedFix:
    """Aplica `fix` a disco. Retorna una copia con `outcome=APPLIED`.

    Lanza `RemediationScopeError` si el archivo objetivo viola el
    allow-list de `src/remediation/guardrails.py` — esta verificación se
    repite aquí aunque `propose_*` ya la haga, porque nunca se debe
    confiar en que el estado de un `ProposedFix` no fue alterado entre
    la propuesta y la aplicación.
    """
    if not is_target_allowed(fix.target_file):
        raise RemediationScopeError(f"'{fix.target_file}' está fuera del alcance permitido para remediación.")

    if fix.tool == RemediationTool.RUFF_FIX:
        subprocess.run(
            ["python", "-m", "ruff", "check", fix.target_file, "--fix"],  # noqa: S603, S607 — lista fija, sin shell.
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=APPLY_SUBPROCESS_TIMEOUT_SECONDS,
            check=False,
        )
    elif fix.tool == RemediationTool.DEPENDENCY_BUMP:
        _apply_dependency_bump(fix, project_root)

    record_audit_event(
        actor=actor,
        action="apply_remediation",
        purpose=f"{fix.tool.value}:{fix.target_file}",
        artifact_hash=fix.finding_id,
    )
    return fix.model_copy(update={"outcome": RemediationOutcome.APPLIED})


def _apply_dependency_bump(fix: ProposedFix, project_root: Path) -> None:
    """Aplica el bump de versión parseando el diff generado por `propose_dependency_bump`."""
    target_path = project_root / fix.target_file
    old_line: str | None = None
    new_line: str | None = None
    for diff_line in fix.diff.splitlines():
        if diff_line.startswith("-") and not diff_line.startswith("---"):
            old_line = diff_line[1:]
        elif diff_line.startswith("+") and not diff_line.startswith("+++"):
            new_line = diff_line[1:]

    if old_line is None or new_line is None:
        raise RemediationScopeError("Diff de dependencia mal formado; no se aplica por seguridad.")

    content = target_path.read_text(encoding="utf-8")
    if old_line not in content:
        raise RemediationScopeError("La línea original ya no coincide con requirements.txt; regenerar la propuesta.")
    target_path.write_text(content.replace(old_line, new_line, 1), encoding="utf-8")
