"""Pruebas basadas en propiedades (Hypothesis) del cálculo de puntaje.

Complementan los casos de ejemplo de `tests/unit` y `tests/design`:
en vez de fijar entradas puntuales, generan cientos de combinaciones
aleatorias de preguntas/respuestas y verifican invariantes matemáticas
del algoritmo (`Assessment.compute_scores`) que deben cumplirse SIEMPRE,
no solo en los casos que un humano pensó en escribir a mano.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from src.models.assessment import Answer, AnswerOption, Assessment, Question, QuestionModule

_WEIGHTS = st.integers(min_value=1, max_value=3)
_OPTIONS = st.sampled_from(list(AnswerOption))
_ANSWER_SPECS = st.lists(st.tuples(_WEIGHTS, _OPTIONS), min_size=1, max_size=15)


def _build(specs: list[tuple[int, AnswerOption]]) -> tuple[list[Question], Assessment]:
    questions = [
        Question(id=f"q{i}", module=QuestionModule.OWASP, category="prop", weight=weight, text="?")
        for i, (weight, _option) in enumerate(specs)
    ]
    answers = [Answer(question_id=f"q{i}", selected_option=option) for i, (_weight, option) in enumerate(specs)]
    assessment = Assessment(answers=answers)
    assessment.compute_scores(questions)
    return questions, assessment


@given(_ANSWER_SPECS)
@settings(deadline=None, max_examples=150)
def test_scores_are_always_within_0_100(specs: list[tuple[int, AnswerOption]]) -> None:
    _, assessment = _build(specs)
    for value in assessment.scores.values():
        assert 0.0 <= value <= 100.0


@given(_ANSWER_SPECS)
@settings(deadline=None, max_examples=150)
def test_compute_scores_is_deterministic(specs: list[tuple[int, AnswerOption]]) -> None:
    questions, assessment = _build(specs)
    first_pass = dict(assessment.scores)
    assessment.compute_scores(questions)
    assert assessment.scores == first_pass


@given(st.lists(_WEIGHTS, min_size=1, max_size=15))
@settings(deadline=None, max_examples=100)
def test_all_si_yields_full_score(weight_list: list[int]) -> None:
    specs = [(weight, AnswerOption.SI) for weight in weight_list]
    _, assessment = _build(specs)
    assert assessment.scores["total"] == 100.0


@given(st.lists(_WEIGHTS, min_size=1, max_size=15))
@settings(deadline=None, max_examples=100)
def test_all_no_yields_zero_score(weight_list: list[int]) -> None:
    specs = [(weight, AnswerOption.NO) for weight in weight_list]
    _, assessment = _build(specs)
    assert assessment.scores["total"] == 0.0


@given(_ANSWER_SPECS)
@settings(deadline=None, max_examples=150)
def test_no_aplica_questions_never_change_the_total_score(specs: list[tuple[int, AnswerOption]]) -> None:
    _, baseline = _build(specs)
    baseline_total = baseline.scores.get("total")

    _, extended = _build([*specs, (2, AnswerOption.NO_APLICA)])

    assert extended.scores.get("total") == baseline_total


@given(_ANSWER_SPECS)
@settings(deadline=None, max_examples=150)
def test_upgrading_one_answer_to_si_never_decreases_the_total_score(
    specs: list[tuple[int, AnswerOption]],
) -> None:
    """Invariante matemática: si P <= M (puntos <= máximo), entonces
    (P+w)/(M+w) >= P/M para todo w > 0. Convertir cualquier respuesta en
    'Sí' solo puede subir o mantener el puntaje total, nunca bajarlo."""
    upgradable_indices = [i for i, (_weight, option) in enumerate(specs) if option != AnswerOption.SI]
    if not upgradable_indices:
        return

    _, before = _build(specs)
    upgraded_specs = list(specs)
    index = upgradable_indices[0]
    weight, _option = upgraded_specs[index]
    upgraded_specs[index] = (weight, AnswerOption.SI)
    _, after = _build(upgraded_specs)

    assert after.scores.get("total", 0.0) >= before.scores.get("total", 0.0)
