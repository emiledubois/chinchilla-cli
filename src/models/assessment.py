"""Modelos Pydantic del cuestionario de preauditoría.

Cálculo de puntaje (ver specs/SPEC.md §6): por pregunta, Sí=1.0*weight,
Parcial=0.5*weight, No=0.0, ponderado por `weight` (1-3). "No aplica" se
excluye del denominador del módulo correspondiente.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from enum import Enum, IntEnum

from pydantic import BaseModel, Field, field_validator

from src.utils.security import sanitize_input

MAX_COMMENT_LENGTH = 500
MAX_COMPANY_NAME_LENGTH = 200
DEFAULT_COMPANY_NAME = "No especificado"


class QuestionModule(str, Enum):
    """Módulos disponibles del cuestionario."""

    CYBERSECURITY = "cybersecurity"
    DATA_PROTECTION = "data_protection"
    OWASP = "owasp"


class AnswerOption(IntEnum):
    """Opciones de respuesta, en el orden mostrado al usuario en el CLI."""

    SI = 0
    NO = 1
    NO_APLICA = 2
    PARCIAL = 3

    @property
    def label(self) -> str:
        return {
            AnswerOption.SI: "Sí",
            AnswerOption.NO: "No",
            AnswerOption.NO_APLICA: "No aplica",
            AnswerOption.PARCIAL: "Parcial",
        }[self]


class RiskLevel(str, Enum):
    """Nivel de riesgo global calculado a partir del puntaje total."""

    BAJO = "Bajo"
    MEDIO = "Medio"
    ALTO = "Alto"
    CRITICO = "Crítico"


class Question(BaseModel):
    """Una pregunta del cuestionario de preauditoría."""

    id: str
    module: QuestionModule
    text: str
    category: str
    weight: int = Field(ge=1, le=3)

    model_config = {"frozen": True}


class Answer(BaseModel):
    """Respuesta de un usuario a una `Question` específica.

    `comment` pasa por `sanitize_input` (ASI06 / Context Poisoning): todo
    input libre de usuario se sanitiza antes de persistir o renderizar.
    """

    question_id: str
    selected_option: AnswerOption
    comment: str | None = Field(default=None, max_length=MAX_COMMENT_LENGTH)

    @field_validator("comment")
    @classmethod
    def _sanitize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = sanitize_input(value, max_length=MAX_COMMENT_LENGTH)
        return cleaned or None


class Assessment(BaseModel):
    """Resultado completo de una corrida de preauditoría."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    company_name: str = DEFAULT_COMPANY_NAME
    answers: list[Answer] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    risk_level: RiskLevel | None = None

    @field_validator("company_name")
    @classmethod
    def _sanitize_company_name(cls, value: str) -> str:
        cleaned = sanitize_input(value, max_length=MAX_COMPANY_NAME_LENGTH)
        return cleaned or DEFAULT_COMPANY_NAME

    def compute_scores(self, questions: list[Question]) -> None:
        """Calcula `scores` (por módulo y total) y `risk_level` in-place."""
        questions_by_id = {q.id: q for q in questions}
        points_by_module: dict[str, float] = defaultdict(float)
        max_by_module: dict[str, float] = defaultdict(float)

        for answer in self.answers:
            question = questions_by_id.get(answer.question_id)
            if question is None or answer.selected_option == AnswerOption.NO_APLICA:
                continue
            module = question.module.value
            max_by_module[module] += question.weight
            if answer.selected_option == AnswerOption.SI:
                points_by_module[module] += question.weight
            elif answer.selected_option == AnswerOption.PARCIAL:
                points_by_module[module] += question.weight * 0.5

        scores: dict[str, float] = {}
        total_points = 0.0
        total_max = 0.0
        for module, max_points in max_by_module.items():
            earned = points_by_module.get(module, 0.0)
            scores[module] = round((earned / max_points) * 100, 1) if max_points else 0.0
            total_points += earned
            total_max += max_points

        scores["total"] = round((total_points / total_max) * 100, 1) if total_max else 0.0
        self.scores = scores
        self.risk_level = self._risk_level_from_score(scores["total"])

    @staticmethod
    def _risk_level_from_score(total_score: float) -> RiskLevel:
        if total_score >= 85:
            return RiskLevel.BAJO
        if total_score >= 65:
            return RiskLevel.MEDIO
        if total_score >= 40:
            return RiskLevel.ALTO
        return RiskLevel.CRITICO
