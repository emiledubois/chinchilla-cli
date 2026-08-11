"""Generación del informe PDF de preauditoría (ReportLab).

El PDF se construye siempre en memoria (BytesIO) y solo se escribe a
disco al final, con permisos 0600 (ver `src/utils/security.py`). No se
persiste ningún estado intermedio en disco.
"""

from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from src.models.assessment import AnswerOption, Assessment, Question, QuestionModule
from src.report.templates.style import (
    ANSWER_COLOR_HEX,
    BAR_CHART_MAX_WIDTH,
    PAGE_MARGIN,
    RISK_COLOR_HEX,
    build_stylesheet,
)
from src.utils.security import (
    record_audit_event,
    safe_filename,
    write_file_with_restricted_permissions,
)

TOOL_NAME = "preaudit-cli"

MODULE_LABELS: dict[QuestionModule, str] = {
    QuestionModule.CYBERSECURITY: "Ciberseguridad — Ley 21.663",
    QuestionModule.DATA_PROTECTION: "Protección de Datos — Ley 21.719",
    QuestionModule.OWASP: "OWASP Top 10 (Web)",
}

MODULE_CHART_LABELS: dict[str, str] = {
    "cybersecurity": "Ciberseguridad",
    "data_protection": "Protección de Datos",
    "owasp": "OWASP Top 10",
    "total": "TOTAL",
}

ANSWER_INTERPRETATION: dict[AnswerOption, str] = {
    AnswerOption.SI: "Cumple con el control evaluado.",
    AnswerOption.NO: "No cumple: representa una brecha que requiere acción.",
    AnswerOption.PARCIAL: "Cumplimiento parcial o informal: requiere formalización.",
    AnswerOption.NO_APLICA: "No aplica al contexto evaluado; excluido del puntaje.",
}

LEGAL_DISCLAIMER = (
    "Este informe se genera de forma automatizada a partir de respuestas de "
    "autoevaluación y tiene carácter preliminar e informativo. No constituye "
    "asesoría legal ni reemplaza una auditoría formal realizada por un "
    "profesional o entidad certificada. Referencias normativas: <b>Ley "
    "21.663</b> (Marco de Ciberseguridad e Infraestructura Crítica de la "
    "Información, vigencia gradual desde el <b>1 de marzo de 2025</b>) y "
    "<b>Ley 21.719</b> (Protección de Datos Personales, vigencia a partir "
    "del <b>1 de diciembre de 2026</b>). Ambas leyes contemplan reglamentos "
    "y normativa complementaria aún en desarrollo; este informe refleja el "
    "estado normativo conocido a la fecha de generación y debe revalidarse "
    "periódicamente. El uso de este informe y las decisiones que de él se "
    "deriven son responsabilidad exclusiva de quien lo genera."
)

FOOTER_TEXT = "Este informe es de carácter preliminar y no reemplaza una auditoría formal."


def _score_risk_bucket(pct: float) -> str:
    if pct >= 85:
        return "Bajo"
    if pct >= 65:
        return "Medio"
    if pct >= 40:
        return "Alto"
    return "Crítico"


def _build_score_bar_chart(scores: dict[str, float]):
    """Gráfico de barras simple dibujado con primitivas de reportlab.graphics."""
    from reportlab.graphics.shapes import Drawing, Rect, String

    modules = [m for m in ("cybersecurity", "data_protection", "owasp", "total") if m in scores]
    row_height = 24
    label_width = 130
    bar_area_width = BAR_CHART_MAX_WIDTH
    height = row_height * len(modules) + 10
    drawing = Drawing(label_width + bar_area_width + 55, height)

    for index, module in enumerate(modules):
        pct = max(0.0, min(100.0, scores.get(module, 0.0)))
        y = height - (index + 1) * row_height + 6
        bar_width = bar_area_width * (pct / 100)
        bar_color = colors.HexColor(RISK_COLOR_HEX[_score_risk_bucket(pct)])
        is_total = module == "total"

        drawing.add(
            Rect(
                label_width,
                y,
                bar_area_width,
                14,
                fillColor=colors.HexColor("#F2F4F7"),
                strokeColor=colors.HexColor("#D0D5DD"),
            )
        )
        drawing.add(Rect(label_width, y, bar_width, 14, fillColor=bar_color, strokeColor=None))
        drawing.add(
            String(
                0,
                y + 3,
                MODULE_CHART_LABELS.get(module, module),
                fontName="Helvetica-Bold" if is_total else "Helvetica",
                fontSize=9,
            )
        )
        drawing.add(
            String(
                label_width + bar_area_width + 6,
                y + 3,
                f"{pct:.1f}%",
                fontName="Helvetica-Bold",
                fontSize=9,
            )
        )
    return drawing


def _build_cover(assessment: Assessment, styles) -> list:
    risk_label = assessment.risk_level.value if assessment.risk_level else "Sin calcular"
    risk_hex = RISK_COLOR_HEX.get(risk_label, "#5A5A5A")
    return [
        Spacer(1, 5 * cm),
        Paragraph(TOOL_NAME, styles["CoverTitle"]),
        Paragraph("Informe de Preauditoría de Cumplimiento Normativo", styles["CoverSubtitle"]),
        Spacer(1, 1 * cm),
        Paragraph(f"<b>Empresa:</b> {assessment.company_name}", styles["BodyTextCustom"]),
        Paragraph(
            f"<b>Fecha de generación:</b> {assessment.timestamp.strftime('%Y-%m-%d %H:%M %Z')}",
            styles["BodyTextCustom"],
        ),
        Paragraph(
            f"<b>Puntaje total:</b> {assessment.scores.get('total', 0.0):.1f}% &nbsp;&nbsp; "
            f'<b>Nivel de riesgo:</b> <font color="{risk_hex}"><b>{risk_label}</b></font>',
            styles["BodyTextCustom"],
        ),
        Spacer(1, 0.5 * cm),
        Paragraph(
            "Alcance: Ley 21.663 (Ciberseguridad), Ley 21.719 (Protección de "
            "Datos Personales, vigencia 1-dic-2026) y OWASP Top 10 (Web).",
            styles["Interpretation"],
        ),
        PageBreak(),
    ]


def _build_executive_summary(assessment: Assessment, styles) -> list:
    risk_label = assessment.risk_level.value if assessment.risk_level else "Sin calcular"
    risk_hex = RISK_COLOR_HEX.get(risk_label, "#5A5A5A")
    flowables = [
        Paragraph("Resumen ejecutivo", styles["SectionHeading"]),
        Paragraph(
            f'Nivel de riesgo global: <font color="{risk_hex}"><b>{risk_label}</b></font> '
            f"(puntaje total: {assessment.scores.get('total', 0.0):.1f}%).",
            styles["BodyTextCustom"],
        ),
        Spacer(1, 0.3 * cm),
        _build_score_bar_chart(assessment.scores),
        Spacer(1, 0.4 * cm),
    ]
    return flowables


def _build_module_detail(
    module: QuestionModule,
    module_questions: list[Question],
    answers_by_id: dict,
    styles,
) -> list:
    flowables = [Paragraph(MODULE_LABELS.get(module, module.value), styles["SectionHeading"])]
    for question in module_questions:
        answer = answers_by_id.get(question.id)
        if answer is None:
            continue
        answer_hex = ANSWER_COLOR_HEX.get(answer.selected_option.label, "#000000")
        flowables.append(
            Paragraph(
                f"{question.text} " f'&nbsp;→&nbsp; <font color="{answer_hex}"><b>{answer.selected_option.label}</b></font>',
                styles["QuestionText"],
            )
        )
        interpretation = ANSWER_INTERPRETATION[answer.selected_option]
        if answer.comment:
            interpretation = f"{interpretation} Comentario: {answer.comment}"
        flowables.append(Paragraph(f"[{question.category}] {interpretation}", styles["Interpretation"]))
    return flowables


def _build_recommendations(assessment: Assessment, questions_by_id: dict, styles) -> list:
    flowables = [Paragraph("Recomendaciones priorizadas", styles["SectionHeading"])]
    gaps = [a for a in assessment.answers if a.selected_option in (AnswerOption.NO, AnswerOption.PARCIAL)]

    def _priority_key(answer):
        question = questions_by_id.get(answer.question_id)
        weight = question.weight if question else 0
        severity = 0 if answer.selected_option == AnswerOption.NO else 1
        return (-weight, severity)

    gaps.sort(key=_priority_key)

    if not gaps:
        flowables.append(
            Paragraph(
                "No se identificaron brechas: todas las respuestas fueron " '"Sí" o "No aplica".',
                styles["BodyTextCustom"],
            )
        )
        return flowables

    priority_label = {3: "ALTA", 2: "MEDIA", 1: "BAJA"}
    for answer in gaps:
        question = questions_by_id.get(answer.question_id)
        if question is None:
            continue
        priority = priority_label.get(question.weight, "MEDIA")
        module_label = MODULE_LABELS.get(question.module, question.module.value)
        flowables.append(
            Paragraph(
                f"<b>[{priority}]</b> ({module_label} — {question.category}): "
                f"{question.text} — respuesta registrada: "
                f"<b>{answer.selected_option.label}</b>.",
                styles["BodyTextCustom"],
            )
        )
    return flowables


def _build_legal_notice(styles) -> list:
    return [
        Paragraph("Advertencia legal", styles["SectionHeading"]),
        Paragraph(LEGAL_DISCLAIMER, styles["LegalNotice"]),
    ]


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica-Oblique", 7.5)
    canvas.setFillColor(colors.HexColor("#5A5A5A"))
    page_width = A4[0]
    canvas.drawCentredString(page_width / 2, 1.2 * cm, FOOTER_TEXT)
    canvas.drawRightString(page_width - PAGE_MARGIN, 1.2 * cm, f"Página {doc.page}")
    canvas.restoreState()


def build_pdf_bytes(assessment: Assessment, questions: list[Question]) -> bytes:
    """Construye el PDF completo en memoria y retorna sus bytes."""
    styles = build_stylesheet()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=PAGE_MARGIN,
        title=f"Preauditoría — {assessment.company_name}",
        author=TOOL_NAME,
    )

    answers_by_id = {a.question_id: a for a in assessment.answers}
    questions_by_id = {q.id: q for q in questions}
    questions_by_module: dict[QuestionModule, list[Question]] = {}
    for question in questions:
        questions_by_module.setdefault(question.module, []).append(question)

    story: list = []
    story += _build_cover(assessment, styles)
    story += _build_executive_summary(assessment, styles)
    story.append(PageBreak())

    for module in (QuestionModule.CYBERSECURITY, QuestionModule.DATA_PROTECTION, QuestionModule.OWASP):
        module_questions = questions_by_module.get(module, [])
        if not module_questions:
            continue
        story += _build_module_detail(module, module_questions, answers_by_id, styles)

    story.append(PageBreak())
    story += _build_recommendations(assessment, questions_by_id, styles)
    story.append(Spacer(1, 0.6 * cm))
    story += _build_legal_notice(styles)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def generate_report(
    assessment: Assessment,
    questions: list[Question],
    output_dir: Path,
    *,
    actor: str = "preaudit-cli-user",
) -> Path:
    """Genera el PDF, lo escribe con permisos 0600 y registra auditoría.

    Retorna la ruta del archivo generado.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_bytes = build_pdf_bytes(assessment, questions)

    filename = safe_filename(f"preaudit-{assessment.company_name}-{assessment.timestamp.strftime('%Y%m%dT%H%M%S')}")
    output_path = output_dir / filename
    write_file_with_restricted_permissions(output_path, pdf_bytes)

    artifact_hash = hashlib.sha256(pdf_bytes).hexdigest()
    record_audit_event(
        actor=actor,
        action="generate_report",
        purpose="preauditoria-cumplimiento-normativo",
        artifact_hash=artifact_hash,
    )
    return output_path
