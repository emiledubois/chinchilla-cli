# SPEC.md — Contexto único del proyecto (preaudit-cli)

> Este es el ÚNICO archivo de contexto compartido entre agentes. Cada agente
> (architect, developer, reviewer, qa) lee este archivo y NADA MÁS del estado
> de otros agentes. La comunicación entre agentes es SIEMPRE vía archivos
> (este SPEC, PRs, logs), nunca vía memoria compartida o mensajes directos.

## 1. Qué es este proyecto

`preaudit` es una CLI con dos herramientas:

1. **Preauditoría de cumplimiento normativo** (`preaudit run`) para
   organizaciones chilenas. No reemplaza una auditoría formal: produce un
   PDF con hallazgos, puntajes y recomendaciones priorizadas.
2. **Certificación de calidad y seguridad del propio software**
   (`preaudit certify`), que nace de los requisitos de la asignatura
   "Aseguramiento de Calidad, Seguridad y Cumplimiento en el Software"
   (material fuente en `contexto/data/`): plan de pruebas, casos de
   prueba con técnicas formales, obtención de evidencias y un Informe
   Final de Certificación. Ver `specs/TEST_PLAN.md` y
   `src/certification/`.

Ambas herramientas comparten `src/utils/security.py` (sanitización,
permisos, log de auditoría) y la hoja de estilos del PDF.

## 2. Alcance funcional

**Herramienta 1 — `preaudit run`:**
- Cuestionario interactivo (Ciberseguridad / Datos / OWASP / Todos),
  respuestas Sí/No/No aplica/Parcial.
- Modelo de datos Pydantic: `Question`, `Answer`, `Assessment`.
- Informe PDF (ReportLab): portada, resumen ejecutivo con puntajes por
  módulo, detalle pregunta a pregunta, recomendaciones priorizadas,
  advertencia legal, pie de página de descargo.
- Sin persistencia de PII salvo el nombre de empresa (opcional).

**Herramienta 2 — `preaudit certify`:**
- Ejecuta pytest (`tests/unit`, `tests/e2e`, `tests/design`), `ruff
  check` y `bandit` sobre el proyecto como evidencia automatizada
  (`src/certification/evidence.py`).
- Clasifica cada resultado como `Finding` (Conformidad / No conformidad
  Mayor / No conformidad Menor / Observación) con evidencia objetiva,
  ubicación y referencia normativa (`src/certification/models.py`).
- Deriva una decisión determinística (Otorgar / Otorgar con condiciones /
  Denegar — `decide_certification`) y genera un Informe Final de
  Certificación en PDF siguiendo ISO/IEC 17021-1, ISO/IEC 17065, ISO
  19011 e IAF MD 4 (`src/certification/report.py`): portada, resumen
  ejecutivo, metodología, casos de prueba, hallazgos, conclusiones y
  anexos A-D.
- Casos de prueba diseñados con técnicas formales (partición de
  equivalencia, valores límite, tabla de decisión) en
  `src/certification/test_cases.py`, ejecutados en `tests/design/`.
- Exit code 1 si la decisión es "Denegar" — usable como gate de CI, sin
  autoaprobación (ASI09).

**Ambas herramientas:**
- Log de auditoría de cada ejecución (`logs/audit.log`, vía `scripts/audit-log.sh`).

## 3. Marco legal aplicable (Chile)

- **Ley 21.663 — Marco de Ciberseguridad e Infraestructura Crítica de la
  Información** (publicada 8-abr-2024). Vigencia GRADUAL, no única: los
  artículos 5, 8, 9 y el Título VII (régimen sancionatorio) rigen desde el
  **1-marzo-2025**; el resto entra en vigor por etapas conforme la ANCI
  (Agencia Nacional de Ciberseguridad) va calificando Operadores de
  Importancia Vital (OIV) en procesos públicos de 6 etapas de 30 días
  corridos cada uno, durante 2025-2026. Exige gobernanza de
  ciberseguridad, gestión de riesgo, reporte de incidentes al CSIRT
  Nacional en plazos 3h (alerta temprana) / 72h (reporte completo) / 15
  días (reporte final), y contempla multas de hasta 5.000/10.000/20.000
  UTM (40.000 UTM para OIV en infracciones gravísimas). **Corrección
  importante**: el enunciado original de este proyecto citaba "Ley
  21.633"; el número correcto, verificado en BCN/LeyChile, es **21.663**.
  No debe confundirse con la Ley 21.719 (dato distinto, vigencia distinta).
- **Ley 21.719 — Protección de Datos Personales** (publicada 13-dic-2024).
  Entra en vigencia el **1-dic-2026** (fecha única, no gradual como
  21.663) y en ese momento crea la Agencia de Protección de Datos
  Personales (APDP). Exige base de licitud (consentimiento u otra),
  derechos ARCO+ (Acceso, Rectificación, Cancelación, Oposición,
  Portabilidad), Registro de Actividades de Tratamiento, DPO en ciertos
  casos, EIPD para tratamientos de alto riesgo, notificación de brechas en
  plazos breves (≤72h a la Agencia), transferencias internacionales solo a
  países con nivel adecuado o garantías equivalentes. Multas hasta 20.000
  UTM. Los reglamentos que detallan las obligaciones se han venido
  publicando progresivamente desde 2025; el módulo de preguntas debe
  tratarse como referencia viva, no definitiva, hasta que la APDP quede
  operativa.
- **Normativa a posteriori prevista** (no vigente aún, pero anticipable —
  ver `.claude/skills/compliance-check.md` §"Horizonte regulatorio"):
  reglamentos complementarios de la Ley 21.663 para sectores OIV aún no
  calificados; reglamentos de la Ley 21.719 pendientes de publicación
  completa; inicio de operaciones de la APDP (dic-2026); posibles
  actualizaciones de ISO/IEC 27001:2022 y del catálogo CVSS; nuevas
  versiones del OWASP Top 10 y del OWASP Agentic AI Top 10.
- **OWASP Top 10 (Web, 2021)**: referencia técnica para el módulo de
  seguridad aplicativa del proyecto evaluado.
- **OWASP Agentic AI Top 10 (2026, ASI01–ASI10)**: aplica al *workspace
  agéntico en sí* (cómo los agentes que desarrollan esta CLI operan), no al
  cuestionario de negocio. Ver `.claude/skills/security-scan.md`.

## 4. No-objetivos

- No es asesoría legal. Todo output del PDF lleva descargo explícito.
- No conecta a sistemas externos, no hace scraping, no llama APIs de
  terceros. Todo el cuestionario es local y offline.
- No almacena respuestas entre ejecuciones (cada corrida es efímera salvo
  el PDF final y la entrada de log).

## 5. Arquitectura de agentes

| Agente | Rol | Entrada | Salida |
|---|---|---|---|
| `architect` | Diseña cambios estructurales, actualiza este SPEC | SPEC.md, issue/ask | diff propuesto + SPEC actualizado |
| `developer` | Implementa código en `src/`/`tests/` | SPEC.md, tarea asignada | commit en worktree aislado |
| `reviewer` | Revisión de seguridad (OWASP Agentic + código) | diff del developer | hallazgos + veredicto aprobar/rechazar |
| `qa` | Pruebas unitarias/e2e, valida cuestionarios y PDF | código + tests | reporte pass/fail |

Cada agente corre en su propio `git worktree` + contenedor Docker aislado
(ver `docker-compose.yml`). Ningún agente tiene permisos de merge a `main`;
eso requiere aprobación humana explícita (ASI09).

## 6. Modelo de puntaje

Por pregunta: `Sí=1.0`, `Parcial=0.5`, `No=0.0`, ponderado por `weight`
(1–3). `No aplica` se excluye del denominador del módulo. Score de módulo =
suma ponderada / máximo ponderado posible, en %. Riesgo global:
`>=85% Bajo | >=65% Medio | >=40% Alto | <40% Crítico`.

## 7. Restricciones técnicas

- Python 3.11, sin dependencias de red en runtime del cuestionario.
- Dependencias fijadas en `requirements.txt`; integridad verificada vía
  hashes (`pip install --require-hashes`) — ver ASI04 en security-scan.md.
- El PDF se escribe con permisos `0600`.
- Todo input de usuario pasa por `src/utils/security.py::sanitize_input`.
- Prompts de agentes (`.claude/agents/*.md`) ≤500 tokens cada uno.

## 8. Definición de "hecho"

Un cambio está terminado cuando: (1) pasa `pytest` (unit + e2e + design),
(2) pasa `ruff` + `bandit` + `detect-secrets` en pre-commit, (3)
`preaudit certify` no retorna "Denegar" (o, si retorna "Otorgar con
condiciones", las condiciones quedan registradas como tarea de
seguimiento), (4) el workflow `security-scan.yml` no reporta hallazgos
HIGH/CRITICAL nuevos, (5) este SPEC.md se actualiza si el alcance
cambió, (6) un humano aprobó el PR.
