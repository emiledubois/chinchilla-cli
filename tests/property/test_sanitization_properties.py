"""Pruebas basadas en propiedades (Hypothesis) de la capa de sanitización.

`sanitize_input` y `safe_filename` son la frontera de seguridad entre
input arbitrario de usuario y el resto del sistema (ASI06 Context
Poisoning / A03 Inyección). Se generan cadenas Unicode arbitrarias
(incluye caracteres de control, RTL, combinantes, emojis) para verificar
que las invariantes de seguridad se sostienen frente a CUALQUIER input,
no solo los ejemplos manuales de `tests/unit`.
"""

from __future__ import annotations

import unicodedata

from hypothesis import given, settings
from hypothesis import strategies as st

from src.utils.security import safe_filename, sanitize_input

_ARBITRARY_TEXT = st.text(min_size=0, max_size=300)
_ALLOWED_FILENAME_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-")


@given(_ARBITRARY_TEXT)
@settings(deadline=None, max_examples=200)
def test_sanitize_input_strips_all_control_characters(value: str) -> None:
    cleaned = sanitize_input(value, max_length=500)
    assert not any(unicodedata.category(char) == "Cc" for char in cleaned)


@given(_ARBITRARY_TEXT, st.integers(min_value=1, max_value=200))
@settings(deadline=None, max_examples=200)
def test_sanitize_input_never_exceeds_max_length(value: str, max_length: int) -> None:
    cleaned = sanitize_input(value, max_length=max_length)
    assert len(cleaned) <= max_length


@given(_ARBITRARY_TEXT)
@settings(deadline=None, max_examples=200)
def test_sanitize_input_is_idempotent(value: str) -> None:
    once = sanitize_input(value, max_length=500)
    twice = sanitize_input(once, max_length=500)
    assert once == twice


@given(_ARBITRARY_TEXT)
@settings(deadline=None, max_examples=200)
def test_safe_filename_only_uses_allow_listed_characters(value: str) -> None:
    """Invariante de seguridad real: si CADA carácter del nombre de archivo
    pertenece al allow-list [A-Za-z0-9_.-], entonces no puede existir un
    separador de ruta ('/', '\\\\') y por lo tanto no hay path traversal
    posible al unirlo con el directorio de salida, sin importar el input."""
    filename = safe_filename(value)
    assert filename.endswith(".pdf")
    assert set(filename) <= _ALLOWED_FILENAME_CHARS


@given(_ARBITRARY_TEXT)
@settings(deadline=None, max_examples=200)
def test_safe_filename_never_produces_empty_stem(value: str) -> None:
    filename = safe_filename(value)
    stem = filename.removesuffix(".pdf")
    assert len(stem) > 0
