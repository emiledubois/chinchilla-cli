# TEST_PLAN.md — Plan de Pruebas de Calidad, Seguridad y Cumplimiento

> Documento vivo, complementario a `specs/SPEC.md`. Estructura de 5
> componentes exigida por la metodología del curso (ver
> `contexto/data/2.1.1 ... plan de pruebas con enfoque en calidad y
> seguridad.pdf`): alcance y objetivos, estrategia, recursos y roles,
> criterios de aceptación, documentación y cierre. La versión Python
> equivalente (usada por `preaudit certify`) vive en
> `src/certification/plan.py` — mantener ambas sincronizadas.

**Nota de mapeo normativo**: el curso presenta DOS plantillas de plan de
pruebas en distintas unidades. La usada aquí (5 componentes, unidad 2.1)
es la que se implementa en código. `contexto/data/1.4.1 ...plan de
pruebas de calidad, seguridad y cumplimiento efectivo.pdf` presenta una
plantilla más extensa de 7 secciones basada en **ISO/FDIS 22342:2023**
("Guidelines for the development of a security plan for an
organization"): Gobernanza del plan, Objetivos estratégicos, Alcance y
contexto, Recursos y capacidades, Metodología de pruebas, Gestión de
riesgos, Evidencia y trazabilidad. Mapeo a las 5 secciones de este
documento: Gobernanza→§3 (Recursos y roles); Objetivos→§1; Alcance y
contexto→§1; Recursos y capacidades→§3; Metodología→§2; Gestión de
riesgos→§4 (criterios de aceptación) + la propia clasificación de no
conformidades Mayor/Menor del informe de certificación; Evidencia y
trazabilidad→§5 + `src/certification/evidence.py`. Se optó por la
plantilla de 5 componentes por ser más directa de mapear a código; ambas
son válidas y trazables al material del curso.

## 1. Alcance y objetivos

**Alcance**: verificación de calidad, seguridad y cumplimiento normativo
del código fuente de `preaudit-cli` (paquete `src/`) y de sus dos
artefactos generados (informe de preauditoría normativa e informe de
certificación de calidad/seguridad). Fuera de alcance: infraestructura de
terceros y el software de las organizaciones que usen la herramienta.

**Objetivos**:
1. Verificar que el modelo de puntaje (`Assessment.compute_scores`) sea
   determinístico y correcto en sus valores límite.
2. Verificar que toda entrada de usuario se sanitice antes de persistirse
   o renderizarse (`src/utils/security.py::sanitize_input`).
3. Verificar ausencia de hallazgos de seguridad estática HIGH/CRITICAL
   (bandit) y de violaciones de estilo/seguridad sin resolver (ruff).
4. Verificar que ambos flujos de CLI (`preaudit run`, `preaudit certify`)
   generen PDFs válidos con permisos restringidos (`0600`).
5. Verificar que las dependencias declaradas no tengan vulnerabilidades
   conocidas (`pip-audit`).

## 2. Estrategia de pruebas

Pirámide de pruebas:
- **Base — pruebas unitarias con técnicas formales** (partición de
  equivalencia, análisis de valores límite, tabla de decisión) sobre
  `src/models/assessment.py` y `src/certification/models.py`. Ver
  `tests/design/` para los casos documentados en
  `src/certification/test_cases.py`.
- **Pruebas e2e** sobre el flujo completo de CLI vía `CliRunner`
  (`tests/e2e/test_cli.py`).
- **Análisis estático continuo** (ruff, bandit, pip-audit) como evidencia
  automatizada en cada ejecución de `preaudit certify`
  (`src/certification/evidence.py`).
- **Entorno reproducible**: contenedor Docker (`python:3.11-slim`, ver
  `Dockerfile`) — ninguna prueba se ejecuta contra el filesystem del
  host; `docker-compose.yml` define el servicio `test`.
- **Filosofía Fail Fast**: CI (`ci.yml`) corta en el primer fallo
  (`--maxfail=1`) en cada etapa.

### 2.1 Pruebas basadas en propiedades (Hypothesis)

`tests/property/` complementa los casos de ejemplo de `tests/unit` y
`tests/design` generando cientos de entradas aleatorias por invariante en
vez de fijar valores a mano. Invariantes verificadas:

- **Puntaje**: siempre en [0,100]; determinístico; "Sí" en todas las
  respuestas ⇒ 100%; "No" en todas ⇒ 0%; "No aplica" nunca cambia el
  total; mejorar cualquier respuesta a "Sí" nunca disminuye el puntaje
  (invariante matemática: (P+w)/(M+w) ≥ P/M cuando P≤M, w>0).
- **Sanitización**: ningún carácter de categoría Unicode "Cc" sobrevive;
  longitud siempre acotada; idempotente; `safe_filename` solo usa el
  allow-list `[A-Za-z0-9_.-]` (lo que garantiza ausencia de separadores
  de ruta, sin importar el input).
- **Decisión de certificación**: la tabla de decisión completa
  (`decide_certification`) verificada contra una implementación de
  referencia independiente, sobre combinaciones aleatorias de hallazgos;
  determinística; independiente del orden de la lista.

### 2.2 Mutation testing (calidad de la suite, no del producto)

Mide si la suite *realmente* detecta bugs, no solo si pasa. Config en
`setup.cfg`, fijado a `mutmut==2.4.4` (la serie 3.x falla con paquetes
llamados literalmente `src` — colisiona con su propio directorio interno
de mutación; documentado como decisión de ingeniería, no un supuesto).
Alcance: `src/models/assessment.py`, `src/utils/security.py`,
`src/certification/models.py` (lógica pura; se excluye CLI/IO/PDF por
costo — cada mutante re-ejecuta la suite completa). Corre semanalmente
en CI (`security-scan.yml`, job `mutation-testing`), no en cada push.

**Baseline real** (última corrida completa, `mutmut run` con
`tests/unit`+`tests/design`+`tests/property`):

| Archivo | Mutantes | Matados | Sobrevivientes | Score |
|---|---:|---:|---:|---:|
| `src/models/assessment.py` | 112 | 73 | 39 | 65.2% |
| `src/utils/security.py` | 50 | 21 | 29 | 42.0% |
| `src/certification/models.py` | 118 | 58 | 60 | 49.2% |
| **Total** | **280** | **152** | **128** | **54.3%** |

`certification/models.py` partió en 16.1% (19/118) en el primer ciclo.
Se agregaron `tests/property/test_certification_report_properties.py`
(partición exacta de `CertificationReport.conformities`/
`major_nonconformities`/`minor_nonconformities`/`observations` sobre
combinaciones aleatorias de hallazgos) y
`tests/unit/test_certification_models.py` (valores por defecto de
campos Pydantic omitidos, y conteos exactos embebidos en el mensaje de
`decide_certification`), subiendo el archivo a 49.2% — más que
triplicó su score sin tocar el código de producción, solo agregando
las pruebas que faltaban.

**Sobrevivientes restantes, categorizados (no perseguidos más allá de
esto en este ciclo):**
- Mutaciones de **valores string de enums** (`Severity.CRITICO =
  "Crítico"` → otro string): solo se detectarían fijando el texto
  exacto de display en un test, lo que acopla los tests a la redacción
  del PDF en vez de a comportamiento. Deliberadamente no perseguido.
- Mutaciones de **prosa libre** en mensajes de justificación (envolver
  fragmentos de texto en marcadores): mismo argumento — ya se verifica
  que el *número* embebido en el mensaje sea correcto
  (`test_decide_certification_justification_embeds_accurate_*_count`),
  que es la parte con valor informativo real.

Un mutation score de 100% no es la meta de este proyecto: perseguir los
sobrevivientes restantes significaría escribir tests que verifican
strings de presentación palabra por palabra, no lógica. El valor de la
métrica está en identificar y cerrar los gaps de comportamiento real
(como el de las `@property` de `CertificationReport`), no en maximizar
el número.

## 3. Recursos y roles

| Rol | Responsabilidad en el plan de pruebas |
|---|---|
| `architect` | Diseña el alcance de cada ciclo y actualiza este documento y `specs/SPEC.md`. |
| `developer` | Implementa código y casos de prueba en su worktree aislado. |
| `reviewer` | Ejecuta `.claude/skills/security-scan.md` sobre cada diff. |
| `qa` | Ejecuta `preaudit certify`, valida el informe y reporta pass/fail. |

## 4. Criterios de aceptación

- 0 pruebas fallidas en `tests/unit`, `tests/e2e`, `tests/design` y `tests/property`.
- 0 hallazgos bandit de severidad HIGH o CRITICAL.
- 0 violaciones ruff sin resolver (o justificadas con `noqa` documentado).
- 0 vulnerabilidades conocidas en dependencias (`pip-audit`) sin mitigar.
- PDF generado por ambos comandos: válido, no vacío, permisos `0600`.

Estos mismos criterios son los que evalúa automáticamente
`decide_certification()` (`src/certification/models.py`) para emitir la
decisión Otorgar / Otorgar con condiciones / Denegar del informe final.

## 5. Documentación, comunicación y cierre

- Cada corrida de `preaudit certify` produce un **Informe Final de
  Certificación** en PDF (`reports/certification/`), estructurado según
  ISO/IEC 17021-1, ISO/IEC 17065, ISO 19011 e IAF MD 4: portada con
  código de documento, resumen ejecutivo, metodología, casos de prueba,
  hallazgos (conformidades / no conformidades mayores-menores /
  observaciones), conclusiones y recomendación, y anexos A-D.
- Cierre de ciclo: si la decisión es "Denegar", el comando retorna código
  de salida 1 (usable como gate de CI) y **requiere** un nuevo ciclo tras
  corrección — nunca se autoaprueba (ver ASI09 en
  `.claude/skills/security-scan.md`).
- Trazabilidad: cada informe generado (de preauditoría o de
  certificación) queda registrado en `logs/audit.log` con timestamp,
  actor, acción y hash SHA-256 del PDF (`scripts/audit-log.sh`).

## 6. Marco normativo ampliado citado por el curso

Además de las leyes ya centrales al proyecto (21.663, 21.719 — ver
`specs/SPEC.md` §3), `contexto/data/1.1.1` y `1.3.1` citan explícitamente
este marco adicional, relevante si `preaudit certify` se aplica a
software de terceros (sector público, financiero):

- **Ley 19.628** — Protección de Datos Personales (1999, predecesora de
  la 21.719; sigue vigente en las materias no derogadas hasta que el
  reemplazo complete su entrada en vigor).
- **Ley 21.180** — Transformación Digital del Estado (interoperabilidad y
  trazabilidad de servicios digitales públicos).
- **Normas CMF NCG 386 y 461** — transparencia y sostenibilidad
  (reportabilidad financiera, criterios ESG), aplicables a entidades
  fiscalizadas por la Comisión para el Mercado Financiero.
- **Ley de Cambio Climático y Ley REP** — sostenibilidad tecnológica
  (impacto ambiental, gestión de residuos electrónicos).
- **Estándares de testing/aseguramiento citados por el curso**: IEEE 829
  (plantillas de plan de pruebas), IEEE 610 (definición de caso de
  prueba), IEEE 730 e ISO/IEC/IEEE 29119 (aseguramiento de calidad y
  pruebas de software), ISO/FDIS 22342:2023 (plan de seguridad), ISO/FDIS
  27025:2023 (Product Quality Assurance Requirements), ISO 9001, ISO/IEC
  25010 (SQuaRE), ISO/IEC 27001, ISO 19011, ISO/IEC 17021-1, ISO/IEC
  17065, IAF MD 4, Common Criteria CEM v3.1, PCI-DSS, WCAG.

Fuera de alcance de `preaudit certify` v1 (no implementado, documentado
para trazabilidad): validación automática contra CMF/Ley REP/WCAG — el
alcance actual es exclusivamente el código fuente de este proyecto.

## Historial de hallazgos reales relevantes

- 2026-08: la remediación en vivo de `preaudit remediate` reveló que
  `ruff` siempre reporta rutas ABSOLUTAS en su JSON (sin importar cómo
  se le invoque), mientras el resto del pipeline asumía relativas —
  `is_target_allowed()` rechazaba en silencio cada propuesta de fix
  real, aunque los tests unitarios (con `Finding` fabricados a mano)
  pasaban. Corregido normalizando `Finding.location` en
  `src/certification/evidence.py`. Ningún test automatizado lo detectó;
  solo correr el flujo completo contra evidencia real lo hizo.
- 2026-08: cobertura de código medida por primera vez (`pytest-cov`):
  69.1% en `src/`, por debajo del umbral de 75% definido en
  `MIN_COVERAGE_PCT_THRESHOLD`. Registrado como no conformidad menor
  real en el propio informe de certificación, no ocultado.
- 2026-08: `pip-audit` detectó CVEs en `click==8.1.7`
  (PYSEC-2026-2132) y `pytest==8.2.0` (PYSEC-2026-1845) durante el
  primer ciclo de certificación de este proyecto. Corregido fijando
  `click==8.3.3` y `pytest==9.0.3` en `requirements.txt`. Este es un
  ejemplo real (no hipotético) de por qué el criterio de aceptación §4
  incluye `pip-audit` como paso obligatorio, no opcional.
- 2026-08: una prueba de propiedad (`test_sanitize_input_strips_all_control_characters`,
  Hypothesis) encontró que `sanitize_input` no eliminaba el bloque de
  controles Unicode C1 (`\x80`-`\x9f`), solo el bloque ASCII C0 — el
  regex original cubría `[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]` pero omitía
  C1. Caso mínimo reproducido por Hypothesis: `"\x80"`. Corregido
  reemplazando el regex por un filtro sobre la categoría Unicode "Cc"
  (cubre C0 y C1 por definición). Ningún test de ejemplo escrito a mano
  había cubierto este caso.
- 2026-08: mutation testing (`mutmut`) encontró que
  `Assessment.compute_scores` sobrevivía a la mutación de
  `points_by_module[module] += question.weight * 0.5` a `=` (asignación
  en vez de acumulación) porque ningún caso de prueba respondía dos
  preguntas `PARCIAL` en el mismo módulo. Corregido agregando
  `test_compute_scores_accumulates_multiple_answers_in_same_module` en
  `tests/unit/test_models.py`.
- 2026-08: primer baseline completo de mutation testing: 113/280
  (40.4%) — ver desglose por archivo arriba. `certification/models.py`
  quedó identificado como el punto más débil (16.1%), documentado como
  backlog en vez de inflado artificialmente.
