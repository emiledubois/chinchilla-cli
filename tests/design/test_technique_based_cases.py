"""Ejecución de los casos de prueba diseñados con técnicas formales.

Cada clase implementa uno de los `TestCase` documentados en
`src/certification/test_cases.py` (IDs TC-*). Mantener el `id` referenciado
en el docstring de cada clase sincronizado con ese archivo.

TC-EXP-01 (prueba exploratoria estructurada del flujo completo de CLI) se
implementa en `tests/e2e/test_cli.py::test_full_run_generates_pdf_report`
y no se duplica aquí.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.certification.models import (
    CertificationDecision,
    Finding,
    FindingType,
    decide_certification,
)
from src.models.assessment import (
    Answer,
    AnswerOption,
    Assessment,
    Question,
    QuestionModule,
    RiskLevel,
)


class TestBVAWeightBoundaries:
    """TC-BVA-01: valores límite de Question.weight (rango válido [1,3])."""

    @pytest.mark.parametrize("weight", [0, 4])
    def test_weight_outside_range_is_rejected(self, weight: int) -> None:
        with pytest.raises(ValidationError):
            Question(id="q", module=QuestionModule.OWASP, category="c", weight=weight, text="?")

    @pytest.mark.parametrize("weight", [1, 3])
    def test_weight_at_boundary_is_accepted(self, weight: int) -> None:
        question = Question(id="q", module=QuestionModule.OWASP, category="c", weight=weight, text="?")
        assert question.weight == weight


class TestBVARiskThresholds:
    """TC-BVA-02: valores límite exactos de los umbrales de RiskLevel (40/65/85)."""

    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (39.9, RiskLevel.CRITICO),
            (40.0, RiskLevel.ALTO),
            (40.1, RiskLevel.ALTO),
            (64.9, RiskLevel.ALTO),
            (65.0, RiskLevel.MEDIO),
            (65.1, RiskLevel.MEDIO),
            (84.9, RiskLevel.MEDIO),
            (85.0, RiskLevel.BAJO),
            (85.1, RiskLevel.BAJO),
        ],
    )
    def test_risk_level_boundary(self, score: float, expected: RiskLevel) -> None:
        assert Assessment._risk_level_from_score(score) == expected


class TestEquivalencePartitionAnswerOptions:
    """TC-EQ-01: las 4 clases de equivalencia de AnswerOption aportan puntaje distinto."""

    @pytest.mark.parametrize(
        ("option", "expected_module_score"),
        [
            (AnswerOption.SI, 100.0),
            (AnswerOption.PARCIAL, 50.0),
            (AnswerOption.NO, 0.0),
        ],
    )
    def test_answer_option_contributes_expected_score(self, option: AnswerOption, expected_module_score: float) -> None:
        question = Question(id="q1", module=QuestionModule.OWASP, category="c", weight=2, text="?")
        assessment = Assessment(answers=[Answer(question_id="q1", selected_option=option)])

        assessment.compute_scores([question])

        assert assessment.scores["owasp"] == expected_module_score

    def test_no_aplica_excludes_question_from_denominator(self) -> None:
        question = Question(id="q1", module=QuestionModule.OWASP, category="c", weight=2, text="?")
        assessment = Assessment(answers=[Answer(question_id="q1", selected_option=AnswerOption.NO_APLICA)])

        assessment.compute_scores([question])

        assert "owasp" not in assessment.scores
        assert assessment.scores["total"] == 0.0


class TestDecisionTableCertificationDecision:
    """TC-DT-01: tabla de decisión de decide_certification según combinación de hallazgos.

    | Mayor | Falla | Menor | Decisión              |
    |-------|-------|-------|------------------------|
    |   V   |   -   |   -   | Denegar                |
    |   -   |   V   |   -   | Denegar                |
    |   F   |   F   |   V   | Otorgar con condiciones|
    |   F   |   F   |   F   | Otorgar                |
    """

    @staticmethod
    def _finding(finding_type: FindingType) -> Finding:
        return Finding(id="f1", type=finding_type, description="desc", objective_evidence="evidencia")

    def test_major_nonconformity_denies_regardless_of_others(self) -> None:
        decision, _ = decide_certification([self._finding(FindingType.NO_CONFORMIDAD_MAYOR)], failed_test_cases=0)
        assert decision == CertificationDecision.DENEGAR

    def test_failed_test_denies_regardless_of_findings(self) -> None:
        decision, _ = decide_certification([], failed_test_cases=1)
        assert decision == CertificationDecision.DENEGAR

    def test_only_minor_nonconformity_grants_with_conditions(self) -> None:
        decision, _ = decide_certification([self._finding(FindingType.NO_CONFORMIDAD_MENOR)], failed_test_cases=0)
        assert decision == CertificationDecision.OTORGAR_CON_CONDICIONES

    def test_no_nonconformities_grants_unconditionally(self) -> None:
        findings = [self._finding(FindingType.CONFORMIDAD), self._finding(FindingType.OBSERVACION)]
        decision, _ = decide_certification(findings, failed_test_cases=0)
        assert decision == CertificationDecision.OTORGAR
