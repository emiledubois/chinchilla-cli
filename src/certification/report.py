"""Generación del Informe Final de Certificación (PDF).

Estructura basada en ISO/IEC 17021-1, ISO/IEC 17065, ISO 19011 e IAF MD 4
(ver contexto/data 2.4.1 y specs/TEST_PLAN.md): identificación y portada,
resumen ejecutivo, metodología, casos de prueba, hallazgos detallados,
conclusiones y recomendación, anexos.

Reutiliza la hoja de estilos de `src/report/templates/style.py` para
mantener consistencia visual con el informe de preauditoría normativa.
"""

from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from src.certification.models import CertificationDecision, CertificationReport, Severity
from src.report.templates.style import PAGE_MARGIN, build_stylesheet
from src.utils.security import (
    record_audit_event,
    safe_filename,
    write_file_with_restricted_permissions,
)

TOOL_NAME = "preaudit-cli — módulo de certificación"

DECISION_COLOR_HEX: dict[CertificationDecision, str] = {
    CertificationDecision.OTORGAR: "#2E7D32",
    CertificationDecision.OTORGAR_CON_CONDICIONES: "#F9A825",
    CertificationDecision.DENEGAR: "#C62828",
}

SEVERITY_COLOR_HEX: dict[Severity, str] = {
    Severity.CRITICO: "#C62828",
    Severity.ALTO: "#EF6C00",
    Severity.MEDIO: "#F9A825",
    Severity.BAJO: "#2E7D32",
    Severity.INFORMATIVO: "#5A5A5A",
}

FOOTER_TEXT = "Informe generado automáticamente. No reemplaza una certificación acreditada formal."

METHODOLOGY_NOTE = (
    "La evidencia de este informe se obtiene ejecutando de forma automatizada, dentro "
    "de un contenedor Docker aislado (ver Dockerfile), las herramientas del pipeline de "
    "aseguramiento continuo: pytest (casos de prueba funcionales y de diseño formal), "
    "ruff (estilo y reglas de seguridad estática), y bandit (SAST). Cada hallazgo queda "
    "clasificado como Conformidad, No Conformidad (Mayor/Menor) u Observación, con "
    "evidencia objetiva verificable y trazable (herramienta, archivo y línea de origen)."
)


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica-Oblique", 7)
    canvas.setFillColor(colors.HexColor("#5A5A5A"))
    page_width = A4[0]
    canvas.drawCentredString(page_width / 2, 1.2 * cm, FOOTER_TEXT)
    canvas.drawRightString(page_width - PAGE_MARGIN, 1.2 * cm, f"Página {doc.page}")
    canvas.restoreState()


def _build_cover(report: CertificationReport, styles) -> list:
    decision_hex = DECISION_COLOR_HEX[report.decision]
    return [
        Spacer(1, 3 * cm),
        Paragraph(TOOL_NAME, styles["CoverTitle"]),
        Paragraph("Informe Final de Certificación de Calidad y Seguridad", styles["CoverSubtitle"]),
        Spacer(1, 1 * cm),
        Paragraph(f"<b>Código de documento:</b> {report.document_code}", styles["BodyTextCustom"]),
        Paragraph(f"<b>Organización / proyecto auditado:</b> {report.organization}", styles["BodyTextCustom"]),
        Paragraph(f"<b>Alcance:</b> {report.scope}", styles["BodyTextCustom"]),
        Paragraph(f"<b>Norma/estándar de referencia:</b> {report.normative_reference}", styles["BodyTextCustom"]),
        Paragraph(
            f"<b>Fecha de auditoría:</b> {report.audit_date.strftime('%Y-%m-%d %H:%M %Z')}",
            styles["BodyTextCustom"],
        ),
        Paragraph(
            f"<b>Fecha de emisión:</b> {report.issue_date.strftime('%Y-%m-%d %H:%M %Z')}",
            styles["BodyTextCustom"],
        ),
        Paragraph(f"<b>Equipo auditor:</b> {', '.join(report.auditor_team)}", styles["BodyTextCustom"]),
        Spacer(1, 0.6 * cm),
        Paragraph(
            f'<b>Decisión:</b> <font color="{decision_hex}"><b>{report.decision.value}</b></font>',
            styles["BodyTextCustom"],
        ),
        PageBreak(),
    ]


def _build_executive_summary(report: CertificationReport, styles) -> list:
    decision_hex = DECISION_COLOR_HEX[report.decision]
    return [
        Paragraph("Resumen ejecutivo", styles["SectionHeading"]),
        Paragraph(
            f"Conformidades: <b>{len(report.conformities)}</b> &nbsp;|&nbsp; "
            f"No conformidades mayores: <b>{len(report.major_nonconformities)}</b> &nbsp;|&nbsp; "
            f"No conformidades menores: <b>{len(report.minor_nonconformities)}</b> &nbsp;|&nbsp; "
            f"Observaciones: <b>{len(report.observations)}</b>",
            styles["BodyTextCustom"],
        ),
        Paragraph(
            f'Decisión final: <font color="{decision_hex}"><b>{report.decision.value}</b></font>. '
            f"{report.decision_justification}",
            styles["BodyTextCustom"],
        ),
        Spacer(1, 0.4 * cm),
    ]


def _build_methodology(report: CertificationReport, styles) -> list:
    plan = report.test_plan
    flowables = [
        Paragraph("Metodología aplicada", styles["SectionHeading"]),
        Paragraph(METHODOLOGY_NOTE, styles["BodyTextCustom"]),
        Paragraph("Alcance del plan de pruebas", styles["SubHeading"]),
        Paragraph(plan.scope, styles["BodyTextCustom"]),
        Paragraph("Objetivos", styles["SubHeading"]),
    ]
    for objective in plan.objectives:
        flowables.append(Paragraph(f"• {objective}", styles["BodyTextCustom"]))
    flowables.append(Paragraph("Estrategia", styles["SubHeading"]))
    flowables.append(Paragraph(plan.strategy, styles["BodyTextCustom"]))
    flowables.append(Paragraph("Criterios de aceptación", styles["SubHeading"]))
    for criterion in plan.acceptance_criteria:
        flowables.append(Paragraph(f"• {criterion}", styles["BodyTextCustom"]))
    return flowables


def _build_test_cases(report: CertificationReport, styles) -> list:
    flowables = [
        Paragraph("Casos de prueba diseñados (técnicas formales)", styles["SectionHeading"]),
        Paragraph(
            "Diseño documentado por caso; su ejecución real vive en tests/design/ "
            "(ver conteo de pruebas fallidas en la sección de hallazgos).",
            styles["Interpretation"],
        ),
    ]
    if not report.test_cases:
        flowables.append(Paragraph("No se registraron casos de prueba en esta corrida.", styles["BodyTextCustom"]))
        return flowables
    for case in report.test_cases:
        status = ""
        if case.passed is True:
            status = " ✓"
        elif case.passed is False:
            status = " ✗"
        flowables.append(
            Paragraph(
                f"<b>{case.id}</b> [{case.technique.value}]{status} — {case.description}",
                styles["QuestionText"],
            )
        )
        flowables.append(
            Paragraph(
                f"Entrada: {case.input_data} → Resultado esperado: {case.expected_result}",
                styles["Interpretation"],
            )
        )
    return flowables


def _findings_block(title: str, findings: list, styles) -> list:
    flowables = [Paragraph(title, styles["SubHeading"])]
    if not findings:
        flowables.append(Paragraph("Sin hallazgos en esta categoría.", styles["Interpretation"]))
        return flowables
    for finding in findings:
        severity_txt = f" [{finding.severity.value}]" if finding.severity else ""
        severity_hex = SEVERITY_COLOR_HEX.get(finding.severity, "#000000") if finding.severity else "#000000"
        flowables.append(
            Paragraph(
                f'<font color="{severity_hex}"><b>{finding.id}</b>{severity_txt}</font> — {finding.description}',
                styles["BodyTextCustom"],
            )
        )
        flowables.append(
            Paragraph(
                f"Evidencia objetiva: {finding.objective_evidence} | Ubicación: {finding.location} | "
                f"Referencia: {finding.normative_reference} | Herramienta: {finding.source_tool}",
                styles["Interpretation"],
            )
        )
    return flowables


def _build_findings(report: CertificationReport, styles) -> list:
    flowables = [Paragraph("Hallazgos detallados", styles["SectionHeading"])]
    flowables += _findings_block("Conformidades", report.conformities, styles)
    flowables += _findings_block("No conformidades mayores", report.major_nonconformities, styles)
    flowables += _findings_block("No conformidades menores", report.minor_nonconformities, styles)
    flowables += _findings_block("Observaciones", report.observations, styles)
    return flowables


def _build_conclusions(report: CertificationReport, styles) -> list:
    decision_hex = DECISION_COLOR_HEX[report.decision]
    flowables = [
        Paragraph("Conclusiones y recomendación", styles["SectionHeading"]),
        Paragraph(
            f'Decisión: <font color="{decision_hex}"><b>{report.decision.value}</b></font>',
            styles["BodyTextCustom"],
        ),
        Paragraph(report.decision_justification, styles["BodyTextCustom"]),
    ]
    if report.conditions:
        flowables.append(Paragraph("Condiciones para el seguimiento", styles["SubHeading"]))
        for condition in report.conditions:
            flowables.append(Paragraph(f"• {condition}", styles["BodyTextCustom"]))
    return flowables


def _build_annexes(report: CertificationReport, styles) -> list:
    return [
        Paragraph("Anexos", styles["SectionHeading"]),
        Paragraph("Anexo A — Plan de auditoría", styles["SubHeading"]),
        Paragraph(
            "Ver specs/TEST_PLAN.md para la versión narrativa completa del plan de "
            "pruebas vigente al momento de esta corrida.",
            styles["BodyTextCustom"],
        ),
        Paragraph("Anexo B — Lista de participantes", styles["SubHeading"]),
        Paragraph(
            "No aplica: esta auditoría es 100% automatizada (sin entrevistas ni "
            "observación directa de personas). El equipo auditor declarado corresponde "
            "a los roles de agente definidos en .claude/agents/.",
            styles["BodyTextCustom"],
        ),
        Paragraph("Anexo C — Registro de evidencias", styles["SubHeading"]),
        Paragraph(
            "La evidencia objetiva de cada hallazgo se detalla en la sección "
            "'Hallazgos detallados' de este mismo informe (herramienta, archivo y línea "
            "de origen cuando aplica).",
            styles["BodyTextCustom"],
        ),
        Paragraph("Anexo D — Competencias del equipo auditor", styles["SubHeading"]),
        Paragraph(
            f"Equipo declarado: {', '.join(report.auditor_team)}. Ver .claude/agents/*.md "
            "para el alcance y las restricciones de cada rol.",
            styles["BodyTextCustom"],
        ),
    ]


def build_certification_pdf_bytes(report: CertificationReport) -> bytes:
    """Construye el PDF del informe de certificación en memoria."""
    styles = build_stylesheet()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=PAGE_MARGIN,
        title=f"Certificación — {report.organization} — {report.document_code}",
        author=TOOL_NAME,
    )

    story: list = []
    story += _build_cover(report, styles)
    story += _build_executive_summary(report, styles)
    story.append(PageBreak())
    story += _build_methodology(report, styles)
    story.append(PageBreak())
    story += _build_test_cases(report, styles)
    story.append(PageBreak())
    story += _build_findings(report, styles)
    story.append(PageBreak())
    story += _build_conclusions(report, styles)
    story.append(Spacer(1, 0.6 * cm))
    story += _build_annexes(report, styles)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def generate_certification_report(
    report: CertificationReport,
    output_dir: Path,
    *,
    actor: str = "preaudit-cli-certify",
) -> Path:
    """Genera el PDF, lo escribe con permisos 0600 y registra auditoría."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_bytes = build_certification_pdf_bytes(report)

    filename = safe_filename(f"certification-{report.document_code}")
    output_path = output_dir / filename
    write_file_with_restricted_permissions(output_path, pdf_bytes)

    artifact_hash = hashlib.sha256(pdf_bytes).hexdigest()
    record_audit_event(
        actor=actor,
        action="generate_certification_report",
        purpose="aseguramiento-continuo-calidad-seguridad",
        artifact_hash=artifact_hash,
    )
    return output_path
