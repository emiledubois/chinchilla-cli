"""Banco de casos de prueba diseñados con técnicas formales (IEEE 610).

Estos objetos documentan el DISEÑO del caso (id, precondiciones, pasos,
datos de entrada, resultado esperado) tal como exige la estructura de
contexto/data 2.2.1. Su ejecución real vive en `tests/design/`, que
implementa cada uno de estos casos como una prueba pytest — mantener
ambos sincronizados por `id`.
"""

from __future__ import annotations

from src.certification.models import TestCase, TestTechnique

DESIGNED_TEST_CASES: list[TestCase] = [
    TestCase(
        id="TC-BVA-01",
        technique=TestTechnique.VALOR_LIMITE,
        description="Question.weight rechaza valores fuera del rango [1,3].",
        preconditions="Ninguna.",
        steps=[
            "Construir Question con weight=0 (mín-1).",
            "Construir Question con weight=1 (mín).",
            "Construir Question con weight=3 (máx).",
            "Construir Question con weight=4 (máx+1).",
        ],
        input_data="weight ∈ {0, 1, 3, 4}",
        expected_result="weight=0 y weight=4 lanzan ValidationError; weight=1 y weight=3 se aceptan.",
        postconditions="Ninguna (validación pura, sin efectos secundarios).",
    ),
    TestCase(
        id="TC-BVA-02",
        technique=TestTechnique.VALOR_LIMITE,
        description="Umbrales de RiskLevel (40/65/85) clasifican correctamente en el límite exacto.",
        preconditions="Ninguna.",
        steps=[
            "Evaluar _risk_level_from_score en 39.9, 40.0, 40.1.",
            "Evaluar en 64.9, 65.0, 65.1.",
            "Evaluar en 84.9, 85.0, 85.1.",
        ],
        input_data="score ∈ {39.9, 40.0, 40.1, 64.9, 65.0, 65.1, 84.9, 85.0, 85.1}",
        expected_result=("39.9→Crítico, 40.0/40.1/64.9→Alto, 65.0/65.1/84.9→Medio, 85.0/85.1→Bajo."),
        postconditions="Ninguna.",
    ),
    TestCase(
        id="TC-EQ-01",
        technique=TestTechnique.PARTICION_EQUIVALENCIA,
        description="Las 4 clases de AnswerOption (Sí/No/Parcial/No aplica) aportan puntaje distinto.",
        preconditions="Una Question de weight=2 existe en el banco de preguntas evaluado.",
        steps=[
            "Responder la pregunta con cada clase de AnswerOption por separado.",
            "Calcular compute_scores() para cada caso.",
        ],
        input_data="selected_option ∈ {SI, NO, PARCIAL, NO_APLICA}",
        expected_result=(
            "SI aporta 100% del peso; PARCIAL aporta 50%; NO aporta 0%; "
            "NO_APLICA excluye la pregunta del denominador del módulo."
        ),
        postconditions="Assessment.scores refleja el módulo recalculado.",
    ),
    TestCase(
        id="TC-DT-01",
        technique=TestTechnique.TABLA_DECISION,
        description="Decisión de certificación (decide_certification) según combinación de hallazgos.",
        preconditions="Se cuenta con una lista de Finding clasificados y un conteo de pruebas fallidas.",
        steps=[
            "C1: ¿hay no conformidad mayor? C2: ¿hay prueba fallida? C3: ¿hay no conformidad menor?",
            "Evaluar las combinaciones: (V,-,-)→DENEGAR; (-,V,-)→DENEGAR; "
            "(F,F,V)→OTORGAR_CON_CONDICIONES; (F,F,F)→OTORGAR.",
        ],
        input_data="findings=[], failed=0 | findings=[menor], failed=0 | findings=[mayor], failed=0 | findings=[], failed=1",
        expected_result="La decisión y justificación coinciden exactamente con la tabla de decisión.",
        postconditions="Ninguna (función pura).",
    ),
    TestCase(
        id="TC-EXP-01",
        technique=TestTechnique.EXPLORATORIA_ESTRUCTURADA,
        description="Flujo completo de `preaudit run` genera un PDF válido con permisos 0600.",
        preconditions="Contenedor Docker con dependencias instaladas; directorio de salida vacío.",
        steps=[
            "Invocar `preaudit run --output-dir <tmp>` simulando respuestas vía CliRunner.",
            "Responder el módulo Ciberseguridad completo con 'Sí'.",
            "Confirmar la generación del PDF.",
        ],
        input_data="Respuestas simuladas: módulo=1, 12x('Sí', comentario vacío), confirmación='y'.",
        expected_result="exit_code=0; se crea exactamente 1 PDF no vacío con permisos 0600 en el directorio de salida.",
        postconditions="Se registra un evento en logs/audit.log con el hash SHA-256 del PDF.",
    ),
]
