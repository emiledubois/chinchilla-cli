# preaudit-cli

CLI con **dos herramientas** de aseguramiento, cumplimiento y certificación:

1. **`preaudit run`** — preauditoría de cumplimiento normativo para
   organizaciones chilenas. Cuestionario interactivo sobre:
   - **Ley 21.663** — Marco de Ciberseguridad e Infraestructura Crítica de la Información (vigencia gradual desde **1-mar-2025**).
   - **Ley 21.719** — Protección de Datos Personales (vigencia **1-dic-2026**).
   - **OWASP Top 10 (Web, 2021)** — seguridad aplicativa del proyecto evaluado.

   Genera un informe PDF con puntajes por módulo, nivel de riesgo global y
   recomendaciones priorizadas.

2. **`preaudit certify`** — aseguramiento continuo de calidad y seguridad
   *del propio código fuente*: ejecuta pytest/ruff/bandit como evidencia,
   clasifica hallazgos (conformidad / no conformidad mayor-menor /
   observación) y emite un **Informe Final de Certificación** en PDF
   siguiendo la estructura de ISO/IEC 17021-1, ISO/IEC 17065, ISO 19011 e
   IAF MD 4 (ver `specs/TEST_PLAN.md` y `src/certification/`). Nace de los
   requisitos de la asignatura de Aseguramiento de Calidad, Seguridad y
   Cumplimiento en el Software (ver `contexto/data/`).

> Este workspace es además un **espacio de trabajo agéntico**: cuatro
> agentes (`architect`, `developer`, `reviewer`, `qa`) colaboran vía
> `specs/SPEC.md` como único contexto compartido, cada uno en su propio
> `git worktree` + contenedor Docker, con mitigaciones del **OWASP Agentic
> AI Top 10** (ver `.claude/skills/security-scan.md`). No es una auditoría
> formal ni asesoría legal.

## Hallazgo destacado: un gate de aprobación humana no sirve si el agente puede escribir su propia prueba de aprobación

El resultado más interesante de este proyecto no son las tres
herramientas de la CLI, sino un experimento real (no simulado): se corrió
el loop de 4 agentes sobre una tarea concreta y se dejó que ocurriera lo
que ocurriera, sin guionizar el resultado. Un agente `developer` se negó
dos veces a implementar un cambio sin aprobación humana verificable — la
segunda vez, rechazando específicamente un commit de "aprobación" real
pero sin firma, por no ser distinguible de una autoaprobación de agente.

El hallazgo formal: **un control de "aprobación humana" no es válido si
el canal usado para representarla es escribible por la parte que debe
ser controlada**, incluso si la aprobación en sí fue genuinamente
humana. Registro completo del experimento en
[`specs/AGENTIC_LOOP_EXPERIMENT.md`](specs/AGENTIC_LOOP_EXPERIMENT.md);
por qué este es el aporte central del proyecto en
[`specs/KEY_FINDING.md`](specs/KEY_FINDING.md) (español) /
[`FINDINGS.md`](FINDINGS.md) (English).

## Requisitos

- Python 3.11+, o Docker + Docker Compose.

## Instalación local

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecutar la CLI

```bash
python -m src.cli run
# o, tras `pip install -e .`:
preaudit run
```

Flujo: saludo → selección de módulo (Ciberseguridad / Datos / OWASP /
Todos) → preguntas una por una (Sí / No / No aplica / Parcial, con
comentario opcional) → resumen de puntajes en pantalla → confirmación
explícita → generación del PDF en `./reports/` (permisos `0600`).

Opciones:

```bash
python -m src.cli run --output-dir ./reports --company-name "Mi Empresa"
```

El nombre de empresa es **opcional**; si se omite, el informe usa
"No especificado" (minimización de datos, ver `.claude/skills/compliance-check.md`).

### Bancos de preguntas declarativos

Las preguntas de cada módulo viven en `src/questions/data/*.yaml`
(no hardcodeadas en Python) y se cargan y validan contra el schema
Pydantic de `Question` en `src/questions/loader.py`. Agregar preguntas a
un módulo existente es editar el YAML — sin tocar código. Agregar un
módulo regulatorio nuevo (p.ej. NCh-ISO 27001) requiere además una
entrada en `QuestionModule` (`src/models/assessment.py`) más su archivo
YAML: una frontera deliberada para mantener `QuestionModule` como Enum
con seguridad de tipos. El loader valida al importar: id único,
`weight` en [1,3], mínimo 10 preguntas por banco — un YAML mal formado
falla rápido con un mensaje que identifica el archivo y la entrada, no
un traceback genérico de Pydantic.

## Certificar la calidad/seguridad del propio código (`preaudit certify`)

```bash
python -m src.cli certify
# opciones:
python -m src.cli certify --organization "Mi Proyecto" --output-dir reports/certification
```

Ejecuta, dentro del mismo proceso, `pytest` (unit + e2e + design +
property) con cobertura, `ruff check`, `bandit` y `pip-audit` sobre
`src/`; convierte cada resultado en un `Finding` con evidencia objetiva,
ubicación y referencia normativa; deriva una decisión (Otorgar / Otorgar
con condiciones / Denegar — ver `decide_certification` en
`src/certification/models.py`) y genera el PDF de certificación en
`reports/certification/`. Si la decisión es **Denegar**, el comando
retorna código de salida `1` (gate de CI, sin autoaprobación — ver
ASI09).

La cobertura de código (`coverage.py` vía `pytest-cov`) se mide en la
misma corrida de pytest y aparece en el resumen ejecutivo del PDF; por
debajo de `MIN_COVERAGE_PCT_THRESHOLD` (75%, `src/certification/evidence.py`)
se registra como no conformidad menor, igual que cualquier otro hallazgo.

Casos de prueba diseñados con técnicas formales (partición de
equivalencia, valores límite, tabla de decisión) viven en
`src/certification/test_cases.py`, ejecutados en `tests/design/`.

## Remediación agéntica supervisada (`preaudit remediate`)

```bash
python -m src.cli remediate
```

Recolecta la misma evidencia que `certify` y propone fixes **solo** para
dos categorías, deliberadamente acotadas (ver `specs/THREAT_MODEL.md`,
sección "Elevation of Privilege"):

1. No conformidades **menores** de `ruff` → preview vía `ruff check --diff`.
2. Vulnerabilidades de `pip-audit` con versión de arreglo conocida →
   diff de la línea correspondiente en `requirements.txt`.

El agente **nunca genera código libremente** — solo invoca herramientas
deterministas ya auditadas por el propio pipeline. Cada propuesta se
muestra como diff y **requiere aprobación explícita** (`y`/`N`, sin valor
por defecto afirmativo) antes de tocar disco; no existe una bandera de
"aplicar todo sin preguntar". Cada cambio aplicado queda registrado en
`logs/audit.log`. Los guardrails de alcance (`src/remediation/guardrails.py`)
se validan tanto al proponer como al aplicar, y están cubiertos por
`tests/unit/test_remediation_guardrails.py` y `tests/unit/test_remediation.py`.

## Ejecutar con Docker

```bash
docker-compose up --build preaudit
```

Monta `./reports` y `./logs` como volúmenes; el contenedor corre sin red
saliente (`network_mode: "none"`).

## Pruebas

```bash
pytest tests/unit tests/e2e tests/design tests/property -v
# o vía Docker:
docker-compose run --rm test
```

- `tests/unit/` — cálculo de puntaje, validación Pydantic, sanitización
  de inputs, guardrails y ciclo de remediación.
- `tests/e2e/test_cli.py` — corrida completa simulada (`CliRunner`) que
  genera un PDF real y valida sus permisos.
- `tests/design/test_technique_based_cases.py` — casos de prueba
  diseñados con técnicas formales (valores límite, partición de
  equivalencia, tabla de decisión), documentados en
  `src/certification/test_cases.py`.
- `tests/property/` — pruebas basadas en propiedades (Hypothesis):
  generan cientos de entradas aleatorias por invariante (puntaje siempre
  en [0,100], sanitización idempotente y sin caracteres de control,
  monotonicidad del puntaje, tabla de decisión de certificación
  verificada exhaustivamente) en vez de solo casos de ejemplo fijos.

### Mutation testing (calidad de la suite, no del producto)

```bash
mutmut run   # usa la config de setup.cfg
mutmut results
```

Mide si los tests *realmente* detectan bugs: introduce mutaciones
sintéticas en `src/models/assessment.py`, `src/utils/security.py` y
`src/certification/models.py` y verifica que la suite falle para cada
una. Corre semanalmente en CI (`security-scan.yml`, job
`mutation-testing`), no en cada push, por su costo (cada mutante
re-ejecuta la suite completa). Fijado a `mutmut==2.4.4`: la serie 3.x
tiene un bug conocido con paquetes llamados literalmente `src` (ver
`specs/TEST_PLAN.md`).

## Generar el PDF manualmente (sin cuestionario interactivo)

Útil para pruebas o integración:

```python
from pathlib import Path
from src.models.assessment import Assessment, Answer, AnswerOption
from src.questions import QUESTIONS_BY_MODULE
from src.models.assessment import QuestionModule
from src.report.generator import generate_report

questions = QUESTIONS_BY_MODULE[QuestionModule.OWASP]
answers = [Answer(question_id=q.id, selected_option=AnswerOption.SI) for q in questions]
assessment = Assessment(company_name="Acme SpA", answers=answers)
assessment.compute_scores(questions)

path = generate_report(assessment, questions, Path("reports"))
print(path)
```

## Calidad y seguridad

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files   # ruff, bandit, detect-secrets, etc.
```

CI (`.github/workflows/`):

- `ci.yml` — lint + pytest (unit/e2e/design) en cada push/PR; ejecuta
  `preaudit certify` como gate de aseguramiento continuo (falla el job si
  la decisión es "Denegar") y sube el informe de certificación como
  artefacto; build de artefacto de distribución en `main` (publicación
  real requiere aprobación humana vía GitHub Environments — nunca
  automática).
- `security-scan.yml` — bandit, semgrep, detect-secrets, pip-audit,
  mutation testing semanal, y `promptfoo` (8 casos de prompt injection
  contra `.claude/agents/*.md`, ver `promptfooconfig.yaml`; requiere el
  secret `ANTHROPIC_API_KEY`, se omite sin fallar el pipeline si no está
  configurado).

### Evals de los prompts de agentes (`promptfooconfig.yaml`)

```bash
npm install -g promptfoo
export ANTHROPIC_API_KEY=sk-...
promptfoo eval -c promptfooconfig.yaml
```

8 casos (2 por agente) envían contenido adversarial a cada system prompt
(`.claude/agents/*.md`) — "apruébate a ti mismo", "salta la revisión
humana", "oculta este fallo" — y verifican que la respuesta identifique
el intento y cite la restricción concreta que la protege (ASI01 Goal
Hijack). `tests/unit/test_promptfoo_config.py` valida la estructura de
la config (sin llamar a ningún modelo) en la suite normal de pytest.

## Trazabilidad / compliance

Cada generación de PDF invoca `scripts/audit-log.sh` (vía subprocess con
argumentos sanitizados, sin `shell=True`), registrando en
`logs/audit.log`: timestamp UTC, actor, acción, finalidad y hash SHA-256
del artefacto.

## Estructura

```
.claude/                 agentes, skills, contexto del workspace
.github/workflows/       CI y escaneo de seguridad
contexto/data/           material del curso que originó src/certification/
src/                     código fuente de la CLI
  questions/             loader + bancos de preguntas declarativos en questions/data/*.yaml
  models/                modelos Pydantic + cálculo de puntaje (preaudit run)
  report/                generación del PDF de preauditoría (ReportLab)
  certification/         plan de pruebas, evidencia, decisión e informe (preaudit certify)
  remediation/           propuesta y aplicación supervisada de fixes (preaudit remediate)
  utils/security.py      sanitización, permisos, log de auditoría (compartido)
tests/                   unit + e2e + design + property (Hypothesis)
specs/SPEC.md            contexto único compartido entre agentes
specs/TEST_PLAN.md       plan de pruebas narrativo (preaudit certify)
specs/THREAT_MODEL.md    modelo de amenazas STRIDE
specs/AGENTIC_LOOP_EXPERIMENT.md  corrida real del loop de 4 agentes
specs/KEY_FINDING.md     por qué ese experimento es el resultado central
FINDINGS.md              versión en inglés de KEY_FINDING.md
setup.cfg                configuración de mutmut
scripts/audit-log.sh     script de trazabilidad
```

## Descargo

Este informe y esta herramienta son de carácter **preliminar** y **no
reemplazan una auditoría formal** ni constituyen asesoría legal.
