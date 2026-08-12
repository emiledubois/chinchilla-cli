"""Cuestionario: Ley 21.719 — Protección de Datos Personales (Chile).

Vigencia: 1-dic-2026. Contenido declarativo en
`src/questions/data/data_protection.yaml`; este módulo solo carga y
valida (ver `src/questions/loader.py`).
"""

from __future__ import annotations

from src.models.assessment import QuestionModule
from src.questions.loader import load_question_bank

DATA_PROTECTION_QUESTIONS = load_question_bank("data_protection.yaml", QuestionModule.DATA_PROTECTION)
