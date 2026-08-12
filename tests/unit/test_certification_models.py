"""Pruebas de valores por defecto y mensajes de `src/certification/models.py`.

Complementa `tests/property/test_certification_report_properties.py`.
Nacen de revisar los sobrevivientes del segundo ciclo de mutation
testing: mutar un `Field(default=...)` a `None` solo se detecta si algún
test construye el modelo SIN pasar ese campo explícitamente (todos los
demás tests del proyecto siempre lo pasan); y mutar el conteo usado en
el mensaje de `decide_certification` (`sum(1 for ...)` -> `sum(2 for
...)`) solo se detecta si algún test verifica el número embebido en el
texto, no solo la decisión resultante.
"""

from __future__ import annotations

from datetime import datetime

from src.certification.models import (
    CertificationDecision,
    CertificationReport,
    Finding,
    FindingType,
    TestCase,
    TestPlanMeta,
    TestTechnique,
    decide_certification,
)


def _plan() -> TestPlanMeta:
    return TestPlanMeta(
        scope="s",
        objectives=["o"],
        strategy="s",
        resources_and_roles={"qa": "r"},
        acceptance_criteria=["c"],
    )


def _finding(finding_type: FindingType, index: int = 0) -> Finding:
    return Finding(id=f"f{index}", type=finding_type, description="d", objective_evidence="e")


def test_finding_defaults_when_optional_fields_are_omitted() -> None:
    finding = Finding(id="f1", type=FindingType.OBSERVACION, description="d", objective_evidence="e")
    assert finding.location == "-"
    assert finding.normative_reference == "-"
    assert finding.severity is None
    assert finding.corrective_action is None
    assert finding.source_tool == "manual"


def test_test_case_defaults_when_optional_fields_are_omitted() -> None:
    case = TestCase(id="t1", technique=TestTechnique.CAMINO_BASICO, description="d", expected_result="r")
    assert case.preconditions == "-"
    assert case.steps == []
    assert case.input_data == "-"
    assert case.postconditions == "-"
    assert case.passed is None


def test_certification_report_defaults_when_optional_fields_are_omitted() -> None:
    report = CertificationReport(
        document_code="X",
        organization="o",
        scope="s",
        normative_reference="n",
        test_plan=_plan(),
        decision=CertificationDecision.OTORGAR,
        decision_justification="j",
    )
    assert report.auditor_team == ["architect", "developer", "reviewer", "qa"]
    assert report.test_cases == []
    assert report.findings == []
    assert report.pipeline_metrics is None
    assert report.conditions == []
    assert isinstance(report.audit_date, datetime)
    assert isinstance(report.issue_date, datetime)


def test_decide_certification_justification_embeds_accurate_major_count() -> None:
    findings = [_finding(FindingType.NO_CONFORMIDAD_MAYOR, i) for i in range(2)]
    _, justification = decide_certification(findings, failed_test_cases=3)
    assert "2 no conformidad" in justification
    assert "3 caso" in justification


def test_decide_certification_justification_embeds_accurate_minor_count() -> None:
    findings = [_finding(FindingType.NO_CONFORMIDAD_MENOR, i) for i in range(4)]
    _, justification = decide_certification(findings, failed_test_cases=0)
    assert "4 no conformidad" in justification
