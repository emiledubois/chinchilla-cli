"""Pruebas unitarias del modelo de datos y del cálculo de puntaje."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models.assessment import (
    DEFAULT_COMPANY_NAME,
    Answer,
    AnswerOption,
    Assessment,
    Question,
    QuestionModule,
    RiskLevel,
)


def _make_questions() -> list[Question]:
    return [
        Question(id="q1", module=QuestionModule.CYBERSECURITY, category="Test", weight=3, text="¿Uno?"),
        Question(id="q2", module=QuestionModule.CYBERSECURITY, category="Test", weight=1, text="¿Dos?"),
        Question(id="q3", module=QuestionModule.DATA_PROTECTION, category="Test", weight=2, text="¿Tres?"),
    ]


def test_compute_scores_full_compliance_is_bajo_risk() -> None:
    questions = _make_questions()
    answers = [Answer(question_id=q.id, selected_option=AnswerOption.SI) for q in questions]
    assessment = Assessment(answers=answers)

    assessment.compute_scores(questions)

    assert assessment.scores["total"] == 100.0
    assert assessment.risk_level == RiskLevel.BAJO


def test_compute_scores_excludes_no_aplica_from_denominator() -> None:
    questions = _make_questions()
    answers = [
        Answer(question_id="q1", selected_option=AnswerOption.SI),
        Answer(question_id="q2", selected_option=AnswerOption.NO_APLICA),
        Answer(question_id="q3", selected_option=AnswerOption.NO),
    ]
    assessment = Assessment(answers=answers)

    assessment.compute_scores(questions)

    assert assessment.scores["cybersecurity"] == 100.0  # solo q1 cuenta
    assert assessment.scores["data_protection"] == 0.0  # q3 no cumplido


def test_compute_scores_accumulates_multiple_answers_in_same_module() -> None:
    """Regresión: mutation testing (mutmut) reveló que `points_by_module[module] +=`
    mutado a `=` sobrevivía porque ningún caso previo respondía dos preguntas del
    mismo módulo. Con dos preguntas PARCIAL de weight=2, la puntuación debe sumar
    ambas contribuciones (50%+50%=100%), no descartar la primera."""
    questions = [
        Question(id="q1", module=QuestionModule.OWASP, category="Test", weight=2, text="¿Uno?"),
        Question(id="q2", module=QuestionModule.OWASP, category="Test", weight=2, text="¿Dos?"),
    ]
    answers = [
        Answer(question_id="q1", selected_option=AnswerOption.PARCIAL),
        Answer(question_id="q2", selected_option=AnswerOption.PARCIAL),
    ]
    assessment = Assessment(answers=answers)

    assessment.compute_scores(questions)

    assert assessment.scores["owasp"] == 50.0


def test_compute_scores_partial_counts_as_half_weight() -> None:
    questions = [Question(id="q1", module=QuestionModule.OWASP, category="Test", weight=2, text="¿?")]
    answers = [Answer(question_id="q1", selected_option=AnswerOption.PARCIAL)]
    assessment = Assessment(answers=answers)

    assessment.compute_scores(questions)

    assert assessment.scores["owasp"] == 50.0
    assert assessment.risk_level == RiskLevel.ALTO  # 40% <= 50% < 65%


def test_company_name_blank_falls_back_to_default() -> None:
    assessment = Assessment(company_name="   ")
    assert assessment.company_name == DEFAULT_COMPANY_NAME


def test_question_weight_out_of_range_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        Question(id="q1", module=QuestionModule.OWASP, category="x", weight=5, text="¿?")


def test_answer_comment_is_sanitized() -> None:
    dirty = "hola\x00mundo\x1b  con   espacios"
    answer = Answer(question_id="q1", selected_option=AnswerOption.NO, comment=dirty)
    assert "\x00" not in (answer.comment or "")
    assert "  " not in (answer.comment or "")
