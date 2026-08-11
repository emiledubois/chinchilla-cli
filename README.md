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

## Certificar la calidad/seguridad del propio código (`preaudit certify`)

```bash
python -m src.cli certify
# opciones:
python -m src.cli certify --organization "Mi Proyecto" --output-dir reports/certification
```

Ejecuta, dentro del mismo proceso, `pytest` (unit + e2e + design),
`ruff check` y `bandit` sobre `src/`; convierte cada resultado en un
`Finding` con evidencia objetiva, ubicación y referencia normativa; deriva
una decisión (Otorgar / Otorgar con condiciones / Denegar — ver
`decide_certification` en `src/certification/models.py`) y genera el PDF
de certificación en `reports/certification/`. Si la decisión es
**Denegar**, el comando retorna código de salida `1` (gate de CI, sin
autoaprobación — ver ASI09).

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
- `security-scan.yml` — bandit, semgrep, detect-secrets, pip-audit y
  (si hay Node disponible) `promptfoo` sobre los prompts de agentes.

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
  questions/             bancos de preguntas por módulo (preaudit run)
  models/                modelos Pydantic + cálculo de puntaje (preaudit run)
  report/                generación del PDF de preauditoría (ReportLab)
  certification/         plan de pruebas, evidencia, decisión e informe (preaudit certify)
  remediation/           propuesta y aplicación supervisada de fixes (preaudit remediate)
  utils/security.py      sanitización, permisos, log de auditoría (compartido)
tests/                   unit + e2e + design + property (Hypothesis)
specs/SPEC.md            contexto único compartido entre agentes
specs/TEST_PLAN.md       plan de pruebas narrativo (preaudit certify)
specs/THREAT_MODEL.md    modelo de amenazas STRIDE
setup.cfg                configuración de mutmut
scripts/audit-log.sh     script de trazabilidad
```

## Descargo

Este informe y esta herramienta son de carácter **preliminar** y **no
reemplazan una auditoría formal** ni constituyen asesoría legal.
