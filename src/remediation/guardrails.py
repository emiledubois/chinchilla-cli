"""Guardrails de alcance para el agente de remediación (ASI02 Tool Misuse).

Ningún `ProposedFix` puede aplicarse a un archivo fuera de este
allow-list, sin importar qué herramienta lo generó ni qué diga el
finding de origen. Se valida tanto al proponer como al aplicar (defensa
en profundidad — ver `tests/unit/test_remediation_guardrails.py`).
"""

from __future__ import annotations

from pathlib import Path

ALLOWED_TARGET_PREFIXES: tuple[str, ...] = ("src/", "tests/")
ALLOWED_TARGET_FILES: tuple[str, ...] = ("requirements.txt",)


def is_target_allowed(target_file: str) -> bool:
    """Valida que `target_file` (ruta relativa, con '/') esté en el alcance permitido.

    Rechaza: rutas vacías, absolutas, con '~', con componentes '..'
    (path traversal), y cualquier ruta fuera de src/, tests/ o
    requirements.txt.
    """
    if not target_file or target_file.startswith(("/", "~")):
        return False

    normalized = Path(target_file).as_posix()
    if ".." in Path(normalized).parts:
        return False

    if normalized in ALLOWED_TARGET_FILES:
        return True
    return normalized.startswith(ALLOWED_TARGET_PREFIXES)
