"""Cuestionario: OWASP Top 10 (Web, 2021) aplicado al proyecto evaluado.

Contenido declarativo en `src/questions/data/owasp_web.yaml`; este
módulo solo carga y valida (ver `src/questions/loader.py`).
"""

from __future__ import annotations

from src.models.assessment import QuestionModule
from src.questions.loader import load_question_bank

OWASP_QUESTIONS = load_question_bank("owasp_web.yaml", QuestionModule.OWASP)
