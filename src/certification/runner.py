"""Orquestador del ciclo de aseguramiento continuo: evidencia -> decisión -> informe.

Ejecutado por el comando `preaudit certify` (ver src/cli.py) y pensado
para correr también como paso de CI (mantenimiento del aseguramiento
continuo — contexto/data 3.4.1).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from src.certification.evidence import collect_all_evidence
from src.certification.models import (
    CertificationDecision,
    CertificationReport,
    PipelineMetrics,
    decide_certification,
)
from src.certification.plan import PREAUDIT_CLI_TEST_PLAN
from src.certification.test_cases import DESIGNED_TEST_CASES
from src.utils.security import sanitize_input

NORMATIVE_REFERENCE = (
    "IEEE 829 / IEEE 610 / IEEE 730 / ISO-IEC-IEEE 29119 / ISO-FDIS 22342:2023 / "
    "ISO-IEC 17021-1 / ISO-IEC 17065 / ISO 19011 / IAF MD 4 / OWASP Top 10 / "
    "Ley 21.663 / Ley 21.719"
)


def run_certification(
    project_root: Path,
    organization: str = "preaudit-cli (auto-certificación)",
) -> CertificationReport:
    """Ejecuta pytest/ruff/bandit/pip-audit sobre `project_root` y arma el informe."""
    findings, failed, coverage_pct = collect_all_evidence(project_root)
    decision, justification = decide_certification(findings, failed)

    now = datetime.now(UTC)
    document_code = f"PREAUDIT-CLI-{now.strftime('%Y%m%d-%H%M%S')}-V1-INTERNO"

    conditions: list[str] = []
    if decision == CertificationDecision.OTORGAR_CON_CONDICIONES:
        conditions = [
            "Resolver las no conformidades menores en el próximo ciclo de aseguramiento continuo.",
            "Volver a ejecutar `preaudit certify` tras la corrección para confirmar el cierre.",
        ]
    elif decision == CertificationDecision.DENEGAR:
        conditions = [
            "No proceder a despliegue/publicación hasta resolver las no conformidades mayores y/o pruebas fallidas.",
            "Re-ejecutar `preaudit certify` tras la corrección; requiere nueva aprobación humana antes de merge.",
        ]

    return CertificationReport(
        document_code=document_code,
        organization=sanitize_input(organization, max_length=200) or "No especificado",
        scope=PREAUDIT_CLI_TEST_PLAN.scope,
        normative_reference=NORMATIVE_REFERENCE,
        test_plan=PREAUDIT_CLI_TEST_PLAN,
        test_cases=DESIGNED_TEST_CASES,
        findings=findings,
        pipeline_metrics=PipelineMetrics(coverage_pct=coverage_pct),
        decision=decision,
        decision_justification=justification,
        conditions=conditions,
    )
