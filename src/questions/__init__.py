"""Bancos de preguntas por módulo, más el registro combinado."""

from __future__ import annotations

from src.models.assessment import Question, QuestionModule
from src.questions.cybersecurity import CYBERSECURITY_QUESTIONS
from src.questions.data_protection import DATA_PROTECTION_QUESTIONS
from src.questions.owasp_web import OWASP_QUESTIONS

ALL_QUESTIONS: list[Question] = [
    *CYBERSECURITY_QUESTIONS,
    *DATA_PROTECTION_QUESTIONS,
    *OWASP_QUESTIONS,
]

QUESTIONS_BY_MODULE: dict[QuestionModule, list[Question]] = {
    QuestionModule.CYBERSECURITY: CYBERSECURITY_QUESTIONS,
    QuestionModule.DATA_PROTECTION: DATA_PROTECTION_QUESTIONS,
    QuestionModule.OWASP: OWASP_QUESTIONS,
}

__all__ = [
    "ALL_QUESTIONS",
    "QUESTIONS_BY_MODULE",
    "CYBERSECURITY_QUESTIONS",
    "DATA_PROTECTION_QUESTIONS",
    "OWASP_QUESTIONS",
]
