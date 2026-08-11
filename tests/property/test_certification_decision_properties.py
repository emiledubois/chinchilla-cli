"""Verificación por propiedades de la tabla de decisión de certificación.

`decide_certification` implementa una tabla de decisión (TC-DT-01 en
`src/certification/test_cases.py`). En vez de fijar 4 combinaciones a
mano, se generan cientos de combinaciones aleatorias de hallazgos y se
verifica la regla completa contra una implementación de referencia
independiente — la forma más cercana a una prueba exhaustiva que permite
un espacio de entrada no acotado.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from src.certification.models import CertificationDecision, Finding, FindingType, decide_certification

_FINDING_TYPES = st.sampled_from(list(FindingType))


def _finding(finding_type: FindingType, index: int) -> Finding:
    return Finding(id=f"f{index}", type=finding_type, description="d", objective_evidence="e")


@given(st.lists(_FINDING_TYPES, max_size=25), st.integers(min_value=0, max_value=5))
@settings(deadline=None, max_examples=200)
def test_decision_matches_reference_rule(types: list[FindingType], failed: int) -> None:
    findings = [_finding(finding_type, index) for index, finding_type in enumerate(types)]
    decision, _justification = decide_certification(findings, failed)

    majors = types.count(FindingType.NO_CONFORMIDAD_MAYOR)
    minors = types.count(FindingType.NO_CONFORMIDAD_MENOR)

    if majors > 0 or failed > 0:
        assert decision == CertificationDecision.DENEGAR
    elif minors > 0:
        assert decision == CertificationDecision.OTORGAR_CON_CONDICIONES
    else:
        assert decision == CertificationDecision.OTORGAR


@given(st.lists(_FINDING_TYPES, max_size=25), st.integers(min_value=0, max_value=5))
@settings(deadline=None, max_examples=100)
def test_decision_is_deterministic(types: list[FindingType], failed: int) -> None:
    findings = [_finding(finding_type, index) for index, finding_type in enumerate(types)]
    first, _ = decide_certification(findings, failed)
    second, _ = decide_certification(findings, failed)
    assert first == second


@given(st.lists(_FINDING_TYPES, max_size=25), st.integers(min_value=0, max_value=5))
@settings(deadline=None, max_examples=100)
def test_decision_is_order_independent(types: list[FindingType], failed: int) -> None:
    """La decisión depende de los CONTEOS por tipo, no del orden en que
    aparecen los hallazgos en la lista."""
    findings = [_finding(finding_type, index) for index, finding_type in enumerate(types)]
    reversed_findings = list(reversed(findings))

    forward, _ = decide_certification(findings, failed)
    backward, _ = decide_certification(reversed_findings, failed)
    assert forward == backward
