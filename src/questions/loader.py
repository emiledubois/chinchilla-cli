"""Carga y valida bancos de preguntas declarativos (YAML).

Agregar preguntas a un módulo EXISTENTE es un cambio de datos: editar el
YAML correspondiente en `src/questions/data/`, sin tocar Python. Agregar
un módulo regulatorio nuevo (p.ej. NCh-ISO 27001) requiere además una
entrada en `QuestionModule` (`src/models/assessment.py`) — un límite
deliberado, no un descuido: mantener `QuestionModule` como Enum preserva
la seguridad de tipos que ya validan `tests/design/` y
`tests/property/` sobre `Assessment.compute_scores`. Ver specs/SPEC.md.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from src.models.assessment import Question, QuestionModule

DATA_DIR = Path(__file__).resolve().parent / "data"
MIN_QUESTIONS_PER_BANK = 10


class QuestionBankError(ValueError):
    """Error al cargar o validar un banco de preguntas declarativo.

    El mensaje siempre identifica el archivo y, cuando aplica, el índice
    o id de la entrada problemática — un error de datos debe poder
    corregirse sin leer el traceback de Pydantic.
    """


def load_question_bank(yaml_filename: str, module: QuestionModule) -> list[Question]:
    """Carga y valida `src/questions/data/{yaml_filename}` como lista de `Question`."""
    path = DATA_DIR / yaml_filename
    if not path.is_file():
        raise QuestionBankError(f"Banco de preguntas no encontrado: {path}")

    try:
        raw_entries = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    except yaml.YAMLError as exc:
        raise QuestionBankError(f"{path}: YAML inválido: {exc}") from exc

    if not isinstance(raw_entries, list):
        raise QuestionBankError(f"{path}: se esperaba una lista de preguntas en el nivel superior del YAML.")

    questions: list[Question] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(raw_entries):
        if not isinstance(entry, dict):
            raise QuestionBankError(f"{path}: la entrada #{index} no es un mapeo (clave: valor).")
        try:
            question = Question(module=module, **entry)
        except ValidationError as exc:
            entry_id = entry.get("id", "?")
            raise QuestionBankError(f"{path}: entrada #{index} (id={entry_id}) inválida: {exc}") from exc
        if question.id in seen_ids:
            raise QuestionBankError(f"{path}: id duplicado '{question.id}'.")
        seen_ids.add(question.id)
        questions.append(question)

    if len(questions) < MIN_QUESTIONS_PER_BANK:
        raise QuestionBankError(
            f"{path}: se requieren al menos {MIN_QUESTIONS_PER_BANK} preguntas, " f"se encontraron {len(questions)}."
        )

    return questions
