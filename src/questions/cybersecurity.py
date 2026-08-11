"""Cuestionario: Ley 21.663 — Marco de Ciberseguridad e Infraestructura
Crítica de la Información (Chile).

12 preguntas. Pesos (1-3) reflejan criticidad relativa: 3 = control
estructural exigido por ley, 2 = control operativo esperado, 1 = buena
práctica complementaria. Vigencia gradual: arts. 5, 8, 9 y Título VII
desde 1-mar-2025; el resto por etapas según calificación de Operadores de
Importancia Vital (OIV) por la ANCI durante 2025-2026.
"""

from __future__ import annotations

from src.models.assessment import Question, QuestionModule

CYBERSECURITY_QUESTIONS: list[Question] = [
    Question(
        id="cy-01",
        module=QuestionModule.CYBERSECURITY,
        category="Gobernanza",
        weight=3,
        text=("¿La organización tiene una política de ciberseguridad aprobada " "por la alta dirección?"),
    ),
    Question(
        id="cy-02",
        module=QuestionModule.CYBERSECURITY,
        category="Gestión de activos",
        weight=2,
        text="¿Se realiza un inventario actualizado de activos de información?",
    ),
    Question(
        id="cy-03",
        module=QuestionModule.CYBERSECURITY,
        category="Respuesta a incidentes",
        weight=3,
        text="¿Existe un plan de respuesta a incidentes con roles definidos?",
    ),
    Question(
        id="cy-04",
        module=QuestionModule.CYBERSECURITY,
        category="Pruebas de seguridad",
        weight=2,
        text="¿Se realizan pruebas de penetración al menos anualmente?",
    ),
    Question(
        id="cy-05",
        module=QuestionModule.CYBERSECURITY,
        category="Seguridad por diseño",
        weight=2,
        text='¿El principio de "seguridad por diseño" se aplica en nuevos desarrollos?',
    ),
    Question(
        id="cy-06",
        module=QuestionModule.CYBERSECURITY,
        category="Gestión de vulnerabilidades",
        weight=2,
        text="¿Se gestionan las vulnerabilidades con un proceso formal (CVSS)?",
    ),
    Question(
        id="cy-07",
        module=QuestionModule.CYBERSECURITY,
        category="Cultura",
        weight=1,
        text="¿Existe un programa de concienciación en ciberseguridad para empleados?",
    ),
    Question(
        id="cy-08",
        module=QuestionModule.CYBERSECURITY,
        category="Control de acceso",
        weight=3,
        text="¿Se implementa autenticación multifactor (MFA) en accesos críticos?",
    ),
    Question(
        id="cy-09",
        module=QuestionModule.CYBERSECURITY,
        category="Continuidad operacional",
        weight=2,
        text="¿Se realizan copias de seguridad cifradas con periodicidad definida?",
    ),
    Question(
        id="cy-10",
        module=QuestionModule.CYBERSECURITY,
        category="Auditoría",
        weight=2,
        text="¿Se audita el acceso a sistemas críticos?",
    ),
    Question(
        id="cy-11",
        module=QuestionModule.CYBERSECURITY,
        category="Estándares",
        weight=1,
        text="¿Se cumplen los estándares de la NIST o ISO 27001?",
    ),
    Question(
        id="cy-12",
        module=QuestionModule.CYBERSECURITY,
        category="Reporte regulatorio",
        weight=3,
        text="¿La organización reporta incidentes al CSIRT de Chile?",
    ),
]
