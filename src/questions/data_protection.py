"""Cuestionario: Ley 21.719 — Protección de Datos Personales (Chile).

Vigencia: 1-dic-2026. 12 preguntas. Pesos (1-3) reflejan obligaciones
estructurales (consentimiento, ARCO+, notificación de brechas) vs. buenas
prácticas complementarias.
"""

from __future__ import annotations

from src.models.assessment import Question, QuestionModule

DATA_PROTECTION_QUESTIONS: list[Question] = [
    Question(
        id="dp-01",
        module=QuestionModule.DATA_PROTECTION,
        category="Base de licitud",
        weight=3,
        text="¿Se obtiene consentimiento EXPLÍCITO y REVOCABLE para cada tratamiento de datos?",
    ),
    Question(
        id="dp-02",
        module=QuestionModule.DATA_PROTECTION,
        category="Derechos de titulares",
        weight=3,
        text="¿El titular puede ejercer sus derechos ARCO (Acceso, Rectificación, Cancelación, Oposición)?",
    ),
    Question(
        id="dp-03",
        module=QuestionModule.DATA_PROTECTION,
        category="Registro",
        weight=2,
        text="¿Existe un Registro Nacional de Tratamiento de Datos actualizado?",
    ),
    Question(
        id="dp-04",
        module=QuestionModule.DATA_PROTECTION,
        category="Gobernanza",
        weight=2,
        text="¿Se designó un Delegado de Protección de Datos (DPO)?",
    ),
    Question(
        id="dp-05",
        module=QuestionModule.DATA_PROTECTION,
        category="Evaluación de impacto",
        weight=3,
        text="¿Se realiza Evaluación de Impacto en Protección de Datos (EIPD) para tratamientos de alto riesgo?",
    ),
    Question(
        id="dp-06",
        module=QuestionModule.DATA_PROTECTION,
        category="Minimización",
        weight=2,
        text="¿Se anonimizan o seudonimizan los datos en entornos de desarrollo y QA?",
    ),
    Question(
        id="dp-07",
        module=QuestionModule.DATA_PROTECTION,
        category="Notificación de brechas",
        weight=3,
        text="¿Se notifica a la Agencia de Protección de Datos en caso de violación de seguridad en <72 horas?",
    ),
    Question(
        id="dp-08",
        module=QuestionModule.DATA_PROTECTION,
        category="Notificación de brechas",
        weight=2,
        text="¿Se notifica a los titulares afectados de manera inmediata?",
    ),
    Question(
        id="dp-09",
        module=QuestionModule.DATA_PROTECTION,
        category="Encargados de tratamiento",
        weight=2,
        text="¿Existen contratos específicos con encargados de tratamiento (proveedores)?",
    ),
    Question(
        id="dp-10",
        module=QuestionModule.DATA_PROTECTION,
        category="Transferencias internacionales",
        weight=2,
        text="¿Se garantiza la transferencia internacional de datos solo a países con nivel adecuado?",
    ),
    Question(
        id="dp-11",
        module=QuestionModule.DATA_PROTECTION,
        category="Privacidad desde el diseño",
        weight=2,
        text='¿Se aplica el principio de "privacidad desde el diseño" en nuevos productos?',
    ),
    Question(
        id="dp-12",
        module=QuestionModule.DATA_PROTECTION,
        category="Trazabilidad",
        weight=1,
        text="¿Se mantiene un registro de todas las operaciones de tratamiento (logs de auditoría)?",
    ),
]
