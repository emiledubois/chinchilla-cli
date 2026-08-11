"""Modelos del módulo de remediación agéntica supervisada."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

MAX_DIFF_LENGTH = 20_000


class RemediationTool(str, Enum):
    """Las ÚNICAS dos formas en que este módulo puede modificar el árbol.

    Ninguna involucra generación de código libre: ambas invocan una
    herramienta determinista externa ya auditada por el propio pipeline
    (`ruff`, `pip-audit`).
    """

    RUFF_FIX = "ruff --fix"
    DEPENDENCY_BUMP = "dependency-version-bump"


class RemediationOutcome(str, Enum):
    APPLIED = "Aplicado"
    REJECTED = "Rechazado por el usuario"


class ProposedFix(BaseModel):
    """Un cambio propuesto, mostrado al usuario como diff antes de aplicarse.

    `diff` es siempre generado por la herramienta subyacente (nunca texto
    libre), por lo que refleja exactamente lo que se aplicaría.
    """

    finding_id: str
    tool: RemediationTool
    target_file: str
    description: str = Field(max_length=500)
    diff: str = Field(max_length=MAX_DIFF_LENGTH)
    outcome: RemediationOutcome | None = None
