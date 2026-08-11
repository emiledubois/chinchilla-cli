"""Modelos Pydantic del subsistema de certificación de calidad/seguridad.

Estructura basada en la metodología del curso (ver specs/TEST_PLAN.md):
- `Finding`: hallazgo de auditoría (conformidad/no conformidad/observación),
  con evidencia objetiva y referencia normativa — estructura exigida por
  ISO/IEC 17021-1 e IAF MD 4 para que un hallazgo sea admisible.
- `TestCase`: caso de prueba diseñado con una técnica formal (partición de
  equivalencia, valores límite, tabla de decisión, camino básico) —
  estructura IEEE 610/829.
- `CertificationReport`: documento final, con código de control de
  versiones, metodología, hallazgos, decisión y anexos.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field

from src.utils.security import sanitize_input

MAX_TEXT_LENGTH = 1000


class Severity(str, Enum):
    """Escala de criticidad usada en hallazgos técnicos (informe de pentesting)."""

    CRITICO = "Crítico"
    ALTO = "Alto"
    MEDIO = "Medio"
    BAJO = "Bajo"
    INFORMATIVO = "Informativo"


class FindingType(str, Enum):
    """Clasificación de hallazgos de auditoría (ISO/IEC 17021-1)."""

    CONFORMIDAD = "Conformidad"
    NO_CONFORMIDAD_MAYOR = "No conformidad mayor"
    NO_CONFORMIDAD_MENOR = "No conformidad menor"
    OBSERVACION = "Observación"


class TestTechnique(str, Enum):
    """Técnicas formales de diseño de casos de prueba (caja negra/blanca/híbrida)."""

    PARTICION_EQUIVALENCIA = "Partición de equivalencia"
    VALOR_LIMITE = "Análisis de valores límite"
    TABLA_DECISION = "Tabla de decisión"
    CAMINO_BASICO = "Camino básico (caja blanca)"
    EXPLORATORIA_ESTRUCTURADA = "Prueba exploratoria estructurada"


class CertificationDecision(str, Enum):
    """Decisión final del informe de certificación."""

    OTORGAR = "Otorgar"
    OTORGAR_CON_CONDICIONES = "Otorgar con condiciones"
    DENEGAR = "Denegar"


class Finding(BaseModel):
    """Hallazgo de auditoría con evidencia objetiva verificable y trazable."""

    id: str
    type: FindingType
    description: str = Field(max_length=MAX_TEXT_LENGTH)
    objective_evidence: str = Field(max_length=MAX_TEXT_LENGTH)
    location: str = Field(default="-", max_length=300)
    normative_reference: str = Field(default="-", max_length=300)
    severity: Severity | None = None
    corrective_action: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    source_tool: str = Field(default="manual", max_length=50)

    def model_post_init(self, __context: object) -> None:
        self.description = sanitize_input(self.description, max_length=MAX_TEXT_LENGTH)
        self.objective_evidence = sanitize_input(self.objective_evidence, max_length=MAX_TEXT_LENGTH)


class TestCase(BaseModel):
    """Caso de prueba diseñado con una técnica formal (IEEE 610)."""

    id: str
    technique: TestTechnique
    description: str = Field(max_length=MAX_TEXT_LENGTH)
    preconditions: str = Field(default="-", max_length=MAX_TEXT_LENGTH)
    steps: list[str] = Field(default_factory=list)
    input_data: str = Field(default="-", max_length=300)
    expected_result: str = Field(max_length=MAX_TEXT_LENGTH)
    postconditions: str = Field(default="-", max_length=MAX_TEXT_LENGTH)
    passed: bool | None = None


class TestPlanMeta(BaseModel):
    """Componentes de un plan de pruebas (5 componentes exigidos por el curso)."""

    scope: str
    objectives: list[str]
    strategy: str
    resources_and_roles: dict[str, str]
    acceptance_criteria: list[str]


class PipelineMetrics(BaseModel):
    """KPIs de un pipeline CI/CD (referencia del curso: build<15min, éxito>95%,
    cobertura>80%, MTTR<2h)."""

    build_time_seconds: float | None = None
    success_rate_pct: float | None = None
    coverage_pct: float | None = None
    mttr_hours: float | None = None


class CertificationReport(BaseModel):
    """Informe final de certificación (estructura ISO/IEC 17021-1 / 17065 / 19011 / IAF MD 4)."""

    document_code: str
    organization: str
    scope: str
    normative_reference: str
    audit_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    issue_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    auditor_team: list[str] = Field(default_factory=lambda: ["architect", "developer", "reviewer", "qa"])
    test_plan: TestPlanMeta
    test_cases: list[TestCase] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    pipeline_metrics: PipelineMetrics | None = None
    decision: CertificationDecision
    decision_justification: str = Field(max_length=MAX_TEXT_LENGTH)
    conditions: list[str] = Field(default_factory=list)

    @property
    def major_nonconformities(self) -> list[Finding]:
        return [f for f in self.findings if f.type == FindingType.NO_CONFORMIDAD_MAYOR]

    @property
    def minor_nonconformities(self) -> list[Finding]:
        return [f for f in self.findings if f.type == FindingType.NO_CONFORMIDAD_MENOR]

    @property
    def conformities(self) -> list[Finding]:
        return [f for f in self.findings if f.type == FindingType.CONFORMIDAD]

    @property
    def observations(self) -> list[Finding]:
        return [f for f in self.findings if f.type == FindingType.OBSERVACION]


def decide_certification(findings: list[Finding], failed_test_cases: int) -> tuple[CertificationDecision, str]:
    """Deriva la decisión final a partir de los hallazgos (regla de negocio simple y determinística).

    DENEGAR si hay al menos una no conformidad mayor o una prueba fallida.
    OTORGAR CON CONDICIONES si solo hay no conformidades menores.
    OTORGAR si no hay no conformidades de ningún tipo.
    """
    majors = sum(1 for f in findings if f.type == FindingType.NO_CONFORMIDAD_MAYOR)
    minors = sum(1 for f in findings if f.type == FindingType.NO_CONFORMIDAD_MENOR)

    if majors > 0 or failed_test_cases > 0:
        return (
            CertificationDecision.DENEGAR,
            f"Se identificaron {majors} no conformidad(es) mayor(es) y "
            f"{failed_test_cases} caso(s) de prueba fallido(s). Deben resolverse "
            "antes de una nueva evaluación.",
        )
    if minors > 0:
        return (
            CertificationDecision.OTORGAR_CON_CONDICIONES,
            f"Se identificaron {minors} no conformidad(es) menor(es) sin impacto "
            "crítico. Se otorga certificación condicionada a su corrección en el "
            "próximo ciclo de aseguramiento continuo.",
        )
    return (
        CertificationDecision.OTORGAR,
        "No se identificaron no conformidades. Todos los casos de prueba y "
        "controles de seguridad evaluados fueron conformes.",
    )
