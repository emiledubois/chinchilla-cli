"""Paleta de colores y estilos de párrafo para el informe PDF."""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.lib.units import cm

COLOR_PRIMARY = colors.HexColor("#1B2A4A")
COLOR_ACCENT = colors.HexColor("#2E6F95")
COLOR_MUTED = colors.HexColor("#5A5A5A")
COLOR_BG_LIGHT = colors.HexColor("#F2F4F7")
COLOR_BORDER = colors.HexColor("#D0D5DD")

COLOR_RISK_BAJO = colors.HexColor("#2E7D32")
COLOR_RISK_MEDIO = colors.HexColor("#F9A825")
COLOR_RISK_ALTO = colors.HexColor("#EF6C00")
COLOR_RISK_CRITICO = colors.HexColor("#C62828")

RISK_COLOR_MAP: dict[str, colors.Color] = {
    "Bajo": COLOR_RISK_BAJO,
    "Medio": COLOR_RISK_MEDIO,
    "Alto": COLOR_RISK_ALTO,
    "Crítico": COLOR_RISK_CRITICO,
}

ANSWER_COLOR_MAP: dict[str, colors.Color] = {
    "Sí": COLOR_RISK_BAJO,
    "Parcial": COLOR_RISK_MEDIO,
    "No": COLOR_RISK_CRITICO,
    "No aplica": COLOR_MUTED,
}

# Versiones hexadecimales para uso dentro de markup <font color="..."> de
# Paragraph, donde no se puede pasar un objeto Color directamente.
RISK_COLOR_HEX: dict[str, str] = {
    "Bajo": "#2E7D32",
    "Medio": "#F9A825",
    "Alto": "#EF6C00",
    "Crítico": "#C62828",
}
ANSWER_COLOR_HEX: dict[str, str] = {
    "Sí": "#2E7D32",
    "Parcial": "#F9A825",
    "No": "#C62828",
    "No aplica": "#5A5A5A",
}

PAGE_MARGIN = 2 * cm
BAR_CHART_MAX_WIDTH = 11 * cm


def build_stylesheet() -> StyleSheet1:
    """Construye el StyleSheet reutilizado por `report/generator.py`."""
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=32,
            textColor=COLOR_PRIMARY,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverSubtitle",
            fontName="Helvetica",
            fontSize=13,
            leading=18,
            textColor=COLOR_MUTED,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=COLOR_PRIMARY,
            spaceBefore=18,
            spaceAfter=8,
            borderPadding=0,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubHeading",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=COLOR_ACCENT,
            spaceBefore=10,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyTextCustom",
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.black,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="QuestionText",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.black,
            spaceBefore=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Interpretation",
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=12,
            textColor=COLOR_MUTED,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="LegalNotice",
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=COLOR_MUTED,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FooterText",
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            leading=10,
            textColor=COLOR_MUTED,
            alignment=1,  # centrado
        )
    )
    return styles
