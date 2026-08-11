"""Cuestionario: OWASP Top 10 (Web, 2021) aplicado al proyecto evaluado.

10 preguntas, una por categoría A01-A10. Todas con weight=3: en este
módulo cada categoría representa un riesgo estructural equivalente.
"""

from __future__ import annotations

from src.models.assessment import Question, QuestionModule

OWASP_QUESTIONS: list[Question] = [
    Question(
        id="ow-a01",
        module=QuestionModule.OWASP,
        category="A01 - Control de Acceso Roto",
        weight=3,
        text="¿Se validan los permisos en cada solicitud?",
    ),
    Question(
        id="ow-a02",
        module=QuestionModule.OWASP,
        category="A02 - Fallos Criptográficos",
        weight=3,
        text="¿Se usan cifrados fuertes (TLS 1.3, AES-256) para datos sensibles?",
    ),
    Question(
        id="ow-a03",
        module=QuestionModule.OWASP,
        category="A03 - Inyección",
        weight=3,
        text="¿Se parametrizan todas las consultas a BD y comandos del sistema?",
    ),
    Question(
        id="ow-a04",
        module=QuestionModule.OWASP,
        category="A04 - Diseño Inseguro",
        weight=3,
        text="¿Se realizan amenazas de modelado en la fase de diseño?",
    ),
    Question(
        id="ow-a05",
        module=QuestionModule.OWASP,
        category="A05 - Configuración Insegura",
        weight=3,
        text="¿Se eliminan configuraciones por defecto y puertos innecesarios?",
    ),
    Question(
        id="ow-a06",
        module=QuestionModule.OWASP,
        category="A06 - Componentes Vulnerables",
        weight=3,
        text="¿Se mantiene un inventario de dependencias y se actualizan?",
    ),
    Question(
        id="ow-a07",
        module=QuestionModule.OWASP,
        category="A07 - Fallos de Autenticación",
        weight=3,
        text="¿Se implementa MFA y políticas robustas de contraseñas?",
    ),
    Question(
        id="ow-a08",
        module=QuestionModule.OWASP,
        category="A08 - Fallos de Integridad",
        weight=3,
        text="¿Se usan firmas digitales para verificar integridad del código?",
    ),
    Question(
        id="ow-a09",
        module=QuestionModule.OWASP,
        category="A09 - Fallos de Monitoreo",
        weight=3,
        text="¿Se centralizan logs y se generan alertas ante anomalías?",
    ),
    Question(
        id="ow-a10",
        module=QuestionModule.OWASP,
        category="A10 - Server-Side Request Forgery",
        weight=3,
        text="¿Se valida y restringe las solicitudes a recursos externos?",
    ),
]
