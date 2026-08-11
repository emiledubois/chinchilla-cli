# Skill: compliance-check — Leyes chilenas aplicables al workspace

Checklist para `architect`/`reviewer` al tocar código que maneje datos de
usuarios reales del CLI (respuestas de cuestionario, nombre de empresa,
PDF generado). Referencia normativa para `.claude/skills/security-scan.md`
y para el propio contenido del módulo `data_protection.py`.

## Ley 21.663 — Marco de Ciberseguridad e Infraestructura Crítica
(publicada 8-abr-2024; **no confundir con "21.633"**, número incorrecto
que circuló en versiones tempranas de este proyecto). Vigencia GRADUAL:
arts. 5, 8, 9 y Título VII (régimen sancionatorio) desde **1-mar-2025**;
el resto entra en vigor por etapas conforme la ANCI califica Operadores
de Importancia Vital (OIV), proceso que se extiende durante 2025-2026 y
podría continuar más allá.
- ¿El cambio afecta el manejo de incidentes de seguridad del propio
  workspace? Si sí, debe quedar trazado en `logs/audit.log` (plazos de
  referencia de la ley: 3h alerta temprana / 72h reporte completo / 15
  días reporte final al CSIRT Nacional).
- ¿Se introduce un nuevo activo de información (nuevo dato persistido)?
  Documentarlo en `specs/SPEC.md` §7.
- Seguridad por diseño: todo nuevo endpoint/comando CLI nace con
  validación de input, no se agrega después.

## Horizonte regulatorio (normativa a posteriori prevista)
No vigente todavía, pero razonablemente anticipable — al evaluar cambios
de alcance, considerar que puede requerirse ajuste cuando:
- Se publiquen reglamentos complementarios de la Ley 21.663 aplicables al
  sector/tamaño de la organización auditada (aún en emisión progresiva
  por la ANCI).
- Se completen los reglamentos de la Ley 21.719 (varios ya en desarrollo
  desde 2025) que definirán el detalle de EIPD, formato del Registro de
  Actividades de Tratamiento y criterios de designación de DPO.
- La Agencia de Protección de Datos Personales (APDP) inicie operaciones
  (prevista para dic-2026) y emita normas generales de interpretación.
- Se actualicen ISO/IEC 27001, el catálogo CVSS, o el OWASP Top 10 /
  OWASP Agentic AI Top 10 referenciados por este proyecto.
Acción esperada de `architect`: cuando cualquiera de estos ocurra,
actualizar `specs/SPEC.md` §3 y los bancos de preguntas correspondientes,
dejando registro del cambio normativo en el PR.

## Ley 21.719 — Protección de Datos Personales (vigencia 1-dic-2026)
- **Minimización**: ¿el cambio agrega un campo de dato personal no
  estrictamente necesario? Si sí, requiere justificación explícita en el
  PR y aprobación humana.
- **Nombre de empresa**: es el único dato "identificable" que la CLI
  puede recolectar, y es opcional (default `"No especificado"`). Ningún
  otro campo debe capturar PII de personas naturales.
- **Sin persistencia entre corridas**: las respuestas del cuestionario no
  se guardan en disco salvo dentro del PDF final generado explícitamente
  por el usuario.
- **Derechos ARCO+**: no aplica a la CLI en sí (no hay base de datos de
  titulares), pero el contenido del PDF debe advertir a la organización
  auditada que ESA información sí está sujeta a la ley si la usan sobre
  datos reales.
- **Notificación de brechas (≤72h)**: si el workspace agéntico tuviera un
  incidente que exponga datos de una corrida real (ej. PDF filtrado desde
  un runner de CI), debe tratarse como brecha y registrarse en
  `logs/audit.log` con severidad CRÍTICA.

## Marco normativo adicional (citado en contexto/data, fuera del núcleo del proyecto)
Relevante solo si `preaudit certify` se apunta a software de terceros
(no al propio `preaudit-cli`) en estos sectores — no requiere acción para
cambios normales de este repo:
- **Ley 19.628** — Protección de Datos Personales (1999, predecesora de
  la 21.719, aún parcialmente vigente).
- **Ley 21.180** — Transformación Digital del Estado (software de
  organismos públicos).
- **Normas CMF NCG 386/461** — entidades fiscalizadas por la CMF
  (transparencia/ESG).
- **Ley de Cambio Climático / Ley REP** — sostenibilidad tecnológica.

## OWASP Top 10 (2021) — para el código de la propia CLI
Aplica como código fuente, no solo como cuestionario de negocio:
- A03 Inyección: `scripts/audit-log.sh` se invoca siempre con `subprocess`
  por lista de argumentos, nunca `shell=True` con input de usuario.
- A05 Configuración insegura: sin puertos expuestos innecesarios en
  `docker-compose.yml`; el contenedor de la CLI no necesita red saliente.
- A06 Componentes vulnerables: `requirements.txt` fijado, revisado por
  `security-scan.yml`.

## Uso
Antes de aprobar un PR que toque `src/models`, `src/report`, o
`src/utils/security.py`, recorrer esta lista y dejar constancia en el
review de qué ítems aplicaron.
