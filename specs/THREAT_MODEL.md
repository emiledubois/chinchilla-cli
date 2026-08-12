# THREAT_MODEL.md — Modelo de amenazas (STRIDE)

> Complementa `specs/SPEC.md` y `specs/TEST_PLAN.md`. Cubre las dos
> herramientas (`preaudit run`, `preaudit certify`) y el workspace
> agéntico que las desarrolla. Metodología: STRIDE (Spoofing, Tampering,
> Repudiation, Information Disclosure, Denial of Service, Elevation of
> Privilege), aplicada por activo. Referencia del curso: "seguridad por
> diseño" y threat modeling en fase de diseño (`contexto/data/1.1.1`,
> `2.1.1`).

## Activos y superficie de ataque

| Activo | Descripción |
|---|---|
| Input del cuestionario | Nombre de empresa, comentarios de respuesta (texto libre) |
| PDF generado | Informe de preauditoría o de certificación, en disco |
| `logs/audit.log` | Registro de trazabilidad |
| Subprocesos invocados | `bash scripts/audit-log.sh`, `pytest`/`ruff`/`bandit`/`pip-audit` (evidencia), `ruff --fix` (remediación) |
| Dependencias (`requirements.txt`) | Cadena de suministro |
| Workspace agéntico (`.claude/`) | Prompts y permisos de los 4 agentes |

## Análisis STRIDE

### Spoofing (suplantación)
- **Amenaza**: un proceso o script se hace pasar por `preaudit-cli` al invocar `audit-log.sh` con un `actor` falso.
- **Mitigación**: `record_audit_event` sanitiza y trunca `actor`; no hay autenticación fuerte de proceso porque la CLI corre localmente/en CI de un único usuario — riesgo residual aceptado y documentado (fuera de alcance de un CLI local sin red).
- **Residual**: si se expone como servicio multiusuario en el futuro, requeriría autenticación real (no implementado — ver "Fuera de alcance" en `SPEC.md`).

### Tampering (manipulación)
- **Amenaza**: input de usuario (nombre de empresa, comentario) contiene payloads (control chars, secuencias de escape ANSI/Rich markup, HTML/XML para el PDF) que alteran el documento generado o el log.
- **Mitigación**: `sanitize_input` (verificado por propiedades en `tests/property/test_sanitization_properties.py`: ningún carácter de control sobrevive, longitud acotada, idempotente). ReportLab escapa el contenido de `Paragraph` salvo el markup `<b>/<font>` que la propia CLI construye (no proviene de input de usuario sin sanitizar — ver `_build_module_detail` en `src/report/generator.py`).
- **Amenaza**: manipulación del PDF ya escrito en disco después de generado.
- **Mitigación**: permisos `0600` (`write_file_with_restricted_permissions`) reducen la superficie a otros usuarios del mismo host; hash SHA-256 registrado en `logs/audit.log` permite detectar manipulación posterior (integridad verificable, no preventiva).

### Repudiation (repudio)
- **Amenaza**: alguien genera un informe y luego niega haberlo hecho, o modifica un hallazgo sin dejar rastro.
- **Mitigación**: `logs/audit.log` registra timestamp UTC, actor, acción, finalidad y hash del artefacto para cada generación (`scripts/audit-log.sh`). Limitación conocida: el log es un archivo local sin firma criptográfica ni append-only garantizado a nivel de filesystem — alguien con acceso de escritura al host podría editarlo. Mitigación complementaria: permisos `0600` en el log mismo.
- **Diseño aprobado, no implementado**: `specs/adr/0001-audit-log-integrity.md` (rama `agentic-loop/audit-log-integrity`) propone un hash-chain SHA-256 entre entradas (tamper-*evidencia*, no prevención) más `scripts/verify-audit-log.sh`. Aprobado por el dueño del repositorio; pendiente de implementación real vía PR — ver `specs/AGENTIC_LOOP_EXPERIMENT.md` para por qué se detuvo ahí a propósito.

### Information Disclosure (divulgación de información)
- **Amenaza**: el cuestionario o el informe de certificación exponen más PII de la necesaria.
- **Mitigación**: minimización de datos — el único campo identificable es el nombre de empresa (opcional, default "No especificado"); ver `.claude/skills/compliance-check.md`. `preaudit certify` audita el propio código fuente, no datos de terceros.
- **Amenaza**: `logs/audit.log` o los PDFs en `reports/` se filtran desde un runner de CI compartido.
- **Mitigación**: `.gitignore` excluye `reports/` y `logs/*.log` del repositorio; CI sube el informe de certificación como artefacto con retención acotada (30 días, `ci.yml`), no lo publica.

### Denial of Service (denegación de servicio)
- **Amenaza**: un subproceso de evidencia (`pytest`/`ruff`/`bandit`) se cuelga y bloquea `preaudit certify` indefinidamente.
- **Mitigación**: `EVIDENCE_SUBPROCESS_TIMEOUT_SECONDS = 120` en `src/certification/evidence.py`; `AUDIT_SUBPROCESS_TIMEOUT_SECONDS = 10` en `src/utils/security.py` (ASI08 — circuit breaker, ver `.claude/skills/security-scan.md`).
- **Amenaza**: input de usuario extremadamente largo degrada el rendimiento de sanitización/generación de PDF.
- **Mitigación**: `max_length` acotado en todos los campos de texto (`MAX_COMMENT_LENGTH`, `MAX_COMPANY_NAME_LENGTH`, `MAX_TEXT_LENGTH`); verificado por propiedad (`test_sanitize_input_never_exceeds_max_length`).

### Elevation of Privilege (elevación de privilegios)
- **Amenaza**: input de usuario inyecta comandos a través de `audit-log.sh` o de las herramientas de evidencia.
- **Mitigación**: todo subproceso se invoca con lista fija de argumentos (`subprocess.run([...])`, nunca `shell=True`); verificado por bandit (S603/S607 revisados y documentados con `noqa` justificado, no suprimidos ciegamente).
- **Amenaza (nueva, ver §"Remediación agéntica")**: el módulo de remediación (`src/remediation/`) podría escribir fuera del árbol del proyecto o aplicar cambios sin supervisión.
- **Mitigación**: allow-list de rutas (`src/`, `tests/`, `requirements.txt`), solo dos herramientas deterministas permitidas (`ruff --fix`, bump de versión de dependencia), aprobación humana obligatoria por cada cambio antes de escribir a disco — nunca autoaprobación (ASI09). Ver `tests/unit/test_remediation_guardrails.py`.

## Amenazas específicas del workspace agéntico (no del producto)

| ID OWASP Agentic | Amenaza | Mitigación |
|---|---|---|
| ASI01 Goal Hijack | Contenido de un PR/issue con instrucciones embebidas redirige a `architect`/`developer` | Input externo tratado como dato, nunca como instrucción; cambios de alcance requieren aprobación humana |
| ASI02 Tool Misuse | `developer` instala paquetes no aprobados | Permisos escopeados por agente en `.claude/agents/*.md`; `requirements.txt` requiere aprobación humana para cambios |
| ASI05 Unexpected Code Execution | Código de agentes corre en el host | Todo corre en Docker (`Dockerfile`, `docker-compose.yml`), usuario no-root |
| ASI09 Human Trust | Un agente se autoaprueba | Ningún agente tiene permisos de merge; `reviewer` solo recomienda; remediación requiere confirmación humana explícita por cada fix. **Validado en la práctica, no solo documentado**: en `specs/AGENTIC_LOOP_EXPERIMENT.md`, un agente `developer` se negó dos veces a implementar un ADR sin aprobación humana verificable — la segunda vez, rechazando específicamente un commit de "aprobación" sin firma por no ser distinguible de una auto-aprobación de agente. |

## Fuera de alcance (documentado, no implementado)

- Autenticación/autorización multiusuario (la CLI es de un solo usuario local o de un runner de CI).
- Cifrado en reposo de `reports/`/`logs/` (se asume filesystem del host ya protegido; permisos `0600` son la mitigación de primera línea).
- Firma criptográfica del log de auditoría (ver Repudiation) — candidato para trabajo futuro si se necesita no-repudio fuerte.
