"""Plan de Pruebas de `preaudit-cli` (ver specs/TEST_PLAN.md para la versión narrativa).

Estructura de 5 componentes exigida por la asignatura (contexto/data
2.1.1): alcance y objetivos, estrategia, recursos y roles, criterios de
aceptación, documentación/cierre.
"""

from __future__ import annotations

from src.certification.models import TestPlanMeta

PREAUDIT_CLI_TEST_PLAN = TestPlanMeta(
    scope=(
        "Verificación de calidad, seguridad y cumplimiento normativo del código "
        "fuente de preaudit-cli (paquete `src/`) y de sus artefactos generados "
        "(informes PDF). No cubre infraestructura de terceros ni el software de "
        "las organizaciones que usan la herramienta."
    ),
    objectives=[
        "Verificar que el modelo de puntaje (Assessment.compute_scores) sea determinístico y correcto en sus límites.",
        "Verificar que toda entrada de usuario se sanitice antes de persistirse o renderizarse.",
        "Verificar ausencia de hallazgos de seguridad estática HIGH/CRITICAL (bandit) y de estilo sin resolver (ruff).",
        "Verificar que el flujo completo de CLI (preaudit run) genere un PDF válido con permisos restringidos (0600).",
        "Verificar que las dependencias declaradas no tengan vulnerabilidades conocidas (pip-audit).",
        "Verificar mediante pruebas basadas en propiedades que las invariantes de "
        "puntaje y sanitización se sostengan frente a entradas arbitrarias, no solo "
        "ejemplos elegidos a mano.",
    ],
    strategy=(
        "Pirámide de pruebas: base de pruebas unitarias con técnicas formales "
        "(partición de equivalencia, valores límite, tabla de decisión) sobre "
        "src/models/assessment.py; pruebas basadas en propiedades (Hypothesis, "
        "tests/property/) que verifican invariantes matemáticas sobre cientos "
        "de entradas generadas, no solo ejemplos fijos; una prueba e2e sobre "
        "el flujo completo de CLI vía CliRunner; análisis estático continuo "
        "(ruff, bandit, pip-audit) como evidencia automatizada en cada "
        "ejecución de `preaudit certify`; mutation testing semanal (mutmut) "
        "sobre los módulos de lógica pura para medir si la suite detecta "
        "bugs reales, no solo si pasa. Entorno reproducible: contenedor "
        "Docker (python:3.11-slim, ver Dockerfile) — nunca se ejecuta contra "
        "el filesystem del host."
    ),
    resources_and_roles={
        "architect": "Diseña el alcance de cada ciclo de aseguramiento y actualiza specs/SPEC.md y specs/TEST_PLAN.md.",
        "developer": "Implementa código y casos de prueba en su worktree aislado.",
        "reviewer": "Ejecuta el checklist de seguridad (.claude/skills/security-scan.md) sobre cada diff.",
        "qa": "Ejecuta `preaudit certify`, valida el informe de certificación y reporta veredicto pass/fail.",
    },
    acceptance_criteria=[
        "0 pruebas fallidas en tests/unit, tests/e2e, tests/design y tests/property.",
        "0 hallazgos bandit de severidad HIGH o CRITICAL.",
        "0 violaciones ruff sin resolver (o justificadas explícitamente con noqa documentado en el código).",
        "0 vulnerabilidades conocidas en dependencias (pip-audit) sin mitigar.",
        "El PDF generado por `preaudit run` y por `preaudit certify` tiene permisos 0600 y es un PDF válido no vacío.",
    ],
)
