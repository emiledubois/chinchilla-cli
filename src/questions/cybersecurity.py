"""Cuestionario: Ley 21.663 — Marco de Ciberseguridad e Infraestructura
Crítica de la Información (Chile).

Contenido declarativo en `src/questions/data/cybersecurity.yaml`; este
módulo solo carga y valida (ver `src/questions/loader.py`).
"""

from __future__ import annotations

from src.models.assessment import QuestionModule
from src.questions.loader import load_question_bank

CYBERSECURITY_QUESTIONS = load_question_bank("cybersecurity.yaml", QuestionModule.CYBERSECURITY)
