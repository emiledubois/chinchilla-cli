"""Verificación por propiedades de `CertificationReport` (partición de hallazgos).

Cierra el punto más débil detectado en el primer baseline de mutation
testing (ver specs/TEST_PLAN.md §2.2): `certification/models.py` tenía
16.1% de score porque ningún test ejercitaba las `@property` de
`CertificationReport` con una mezcla real de tipos de hallazgo.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from src.certification.models import (
    CertificationDecision,
    CertificationReport,
    Finding,
    FindingType,
    TestPlanMeta,
)

_FINDING_TYPES = st.sampled_from(list(FindingType))


def _plan() -> TestPlanMeta:
    return TestPlanMeta(
        scope="s",
        objectives=["o"],
        strategy="s",
        resources_and_roles={"qa": "r"},
        acceptance_criteria=["c"],
    )


def _report(types: list[FindingType]) -> CertificationReport:
    findings = [Finding(id=f"f{i}", type=t, description="d", objective_evidence="e") for i, t in enumerate(types)]
    return CertificationReport(
        document_code="X",
        organization="o",
        scope="s",
        normative_reference="n",
        test_plan=_plan(),
        findings=findings,
        decision=CertificationDecision.OTORGAR,
        decision_justification="j",
    )


@given(st.lists(_FINDING_TYPES, max_size=30))
@settings(deadline=None, max_examples=150)
def test_finding_partition_covers_every_finding_exactly_once(types: list[FindingType]) -> None:
    report = _report(types)
    categorized = report.conformities + report.major_nonconformities + report.minor_nonconformities + report.observations

    assert len(categorized) == len(types)
    assert {f.id for f in categorized} == {f.id for f in report.findings}


@given(st.lists(_FINDING_TYPES, max_size=30))
@settings(deadline=None, max_examples=150)
def test_finding_partition_counts_match_reference(types: list[FindingType]) -> None:
    report = _report(types)
    assert len(report.conformities) == types.count(FindingType.CONFORMIDAD)
    assert len(report.major_nonconformities) == types.count(FindingType.NO_CONFORMIDAD_MAYOR)
    assert len(report.minor_nonconformities) == types.count(FindingType.NO_CONFORMIDAD_MENOR)
    assert len(report.observations) == types.count(FindingType.OBSERVACION)
