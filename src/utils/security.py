"""Sanitización y validación de inputs (mitiga ASI06 Context Poisoning, A03 Inyección).

Toda entrada de usuario que llega desde el CLI (nombre de empresa,
comentarios de respuestas) debe pasar por `sanitize_input` antes de:
  - persistirse en un modelo Pydantic,
  - renderizarse en el PDF,
  - usarse para construir un nombre de archivo,
  - pasarse a un subproceso (p.ej. `scripts/audit-log.sh`).
"""

from __future__ import annotations

import re
import subprocess
import unicodedata
from pathlib import Path

# Caracteres relevantes para inyección de shell/comandos. Nunca se pasa
# input de usuario a `shell=True`, pero se eliminan igual como defensa en
# profundidad para cualquier construcción de nombres de archivo o rutas.
_UNSAFE_FOR_FILENAME_RE = re.compile(r"[^A-Za-z0-9_.-]")

AUDIT_LOG_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "audit-log.sh"
AUDIT_SUBPROCESS_TIMEOUT_SECONDS = 10  # ASI08: circuit breaker / timeout explícito


def sanitize_input(value: str, *, max_length: int = 500) -> str:
    """Normaliza, elimina caracteres de control y trunca un input libre.

    No lanza excepciones sobre input "sucio": lo limpia y retorna un string
    seguro para persistir/renderizar. Cadenas vacías tras limpiar retornan "".

    Elimina TODO carácter de la categoría Unicode "Cc" (control), no solo
    el bloque ASCII C0 (\\x00-\\x1f, \\x7f): una versión anterior usaba un
    regex que cubría C0 pero omitía el bloque C1 (\\x80-\\x9f, también
    "Cc"), un gap que detectó `tests/property/test_sanitization_properties.py`
    con Hypothesis (caso mínimo: "\\x80" sobrevivía sin limpiar).
    """
    if not isinstance(value, str):
        raise TypeError(f"sanitize_input espera str, recibió {type(value).__name__}")

    normalized = unicodedata.normalize("NFKC", value)
    without_control = "".join(char for char in normalized if unicodedata.category(char) != "Cc")
    collapsed = " ".join(without_control.split())
    return collapsed[:max_length].strip()


def safe_filename(value: str, *, default: str = "preaudit-report", extension: str = "pdf") -> str:
    """Convierte un string arbitrario en un nombre de archivo seguro.

    Solo permite [A-Za-z0-9_.-]; cualquier otro carácter se descarta. Evita
    path traversal (sin '/', '..', separadores) y caracteres especiales de
    shell/filesystem.
    """
    cleaned = sanitize_input(value, max_length=100)
    safe = _UNSAFE_FOR_FILENAME_RE.sub("_", cleaned).strip("._") or default
    return f"{safe}.{extension}"


def write_file_with_restricted_permissions(path: Path, data: bytes) -> None:
    """Escribe `data` en `path` y restringe permisos a 0600 (solo owner).

    Evita que el informe de preauditoría (que puede contener hallazgos de
    seguridad y de cumplimiento de la organización auditada) quede legible
    por otros usuarios del sistema.
    """
    path.write_bytes(data)
    path.chmod(0o600)


def record_audit_event(actor: str, action: str, purpose: str, artifact_hash: str = "-") -> None:
    """Invoca `scripts/audit-log.sh` de forma segura (sin shell=True).

    Los argumentos se sanitizan y se pasan como lista a `subprocess.run`,
    nunca interpolados en una cadena de shell (mitiga A03 Inyección /
    ASI02 Tool Misuse). Falla de forma silenciosa-pero-visible: si el
    logging de auditoría falla, no debe tumbar la generación del reporte,
    pero sí se reporta el error por stderr del propio script.
    """
    args = [
        sanitize_input(actor, max_length=100) or "unknown",
        sanitize_input(action, max_length=100) or "unknown",
        sanitize_input(purpose, max_length=200) or "unspecified",
        sanitize_input(artifact_hash, max_length=128) or "-",
    ]
    if not AUDIT_LOG_SCRIPT.exists():
        return
    subprocess.run(
        ["bash", str(AUDIT_LOG_SCRIPT), *args],  # noqa: S603, S607 — args fijos/sanitizados, sin shell=True.
        check=False,
        timeout=AUDIT_SUBPROCESS_TIMEOUT_SECONDS,
        capture_output=True,
    )
