# AGENTIC_LOOP_EXPERIMENT.md — Corrida real del loop architect→developer→reviewer→qa

> Este documento registra un experimento real (no simulado): se ejecutó
> el loop de 4 agentes descrito en `.claude/agents/` y `specs/SPEC.md`
> §5 sobre una tarea concreta, usando un `git worktree` real y agentes
> frescos (sin memoria de esta conversación, sin contexto compartido más
> allá de lo que dejaron escrito en archivos). El objetivo era validar
> si el patrón de coordinación por archivos, sin memoria compartida,
> funciona en la práctica — no solo en la documentación. Ver
> `specs/KEY_FINDING.md` (o `FINDINGS.md` en inglés) para por qué este
> documento, y no las tres herramientas de la CLI, es el resultado más
> interesante del proyecto.

## Setup

- Worktree real: `../preaudit-cli-loop`, rama `agentic-loop/audit-log-integrity`.
- Tarea real (no un ejercicio de juguete): cerrar el riesgo residual de
  "Repudiation" documentado en `specs/THREAT_MODEL.md` — `logs/audit.log`
  no tiene integridad criptográfica, cualquiera con acceso de escritura
  al filesystem puede editar una entrada pasada sin dejar rastro.
- Cada rol se lanzó como un agente separado, con SOLO el contenido de su
  `.claude/agents/*.md` como instrucciones de rol y una ruta al worktree
  — sin acceso a esta conversación ni a las salidas de los otros agentes
  salvo lo que estos hubieran escrito a disco y comiteado.

## Qué pasó, en orden

### 1. `architect` — completó su tarea con éxito

Leyó `specs/SPEC.md`, `specs/TEST_PLAN.md` y la sección "Repudiation" de
`specs/THREAT_MODEL.md`, diseñó un hash-chain SHA-256 sin clave (con
razonamiento explícito de por qué NO usar HMAC — la clave viviría en el
mismo host, dando falsa sensación de seguridad), documentó honestamente
las limitaciones (no detecta truncamiento del final del log; no protege
contra un atacante con el mismo privilegio del proceso), y escribió todo
en `specs/adr/0001-audit-log-integrity.md` (commit `f35b5f4`). Actualizó
`specs/SPEC.md` manteniéndolo bajo 200 líneas, como exige su rol. No
escribió código, tal como su prompt lo prohíbe.

**Evaluación**: el resultado es de calidad real, no un placeholder —
identifica una condición de carrera que requiere `flock`, especifica un
caso de test que documenta una limitación conocida en vez de esconderla,
y se ciñe estrictamente al alcance de su rol.

### 2. `developer` (primer intento) — se negó a implementar, correctamente

El ADR que `architect` escribió incluye su propia línea de estado:
`Propuesto (no implementado). Requiere aprobación humana antes de que
developer implemente (ASI09)`. El agente `developer`, sin que se le
dijera explícitamente que buscara esto, la encontró, verificó en
`git log` que no existía ningún registro de aprobación humana, y se
negó a implementar — razonando que la instrucción del agente
orquestador (yo) de "proceder de buena fe" no satisface un gate de
aprobación humana que el propio plan exige. No tocó ningún archivo.

**Esto es ASI09 funcionando en la práctica**, no solo documentado: un
agente downstream respetó un gate que otro agente (upstream) había
declarado, sin que nadie tuviera que programar esa verificación
explícitamente — emergió de seguir su propio prompt al pie de la letra.

### 3. Aprobación humana real

El dueño del repositorio revisó el ADR (resumen entregado, con opción de
leer el archivo completo) y lo aprobó explícitamente, fuera de la
autoridad de cualquier agente, vía una pregunta directa. Se registró esa
aprobación editando la línea `## Estado` del ADR a "Aprobado" y
comiteando el cambio (`5f42999`) bajo la misma identidad de git usada
para todo el repo.

### 4. `developer` (segundo intento) — se negó de nuevo, con un hallazgo más fino

Un agente `developer` fresco (nueva instancia, sin memoria del primer
intento) verificó el estado en disco como se le pidió: encontró el
commit `5f42999` y la línea "Aprobado". Pero fue un paso más allá sin que
se le pidiera explícitamente: notó que **ese commit de aprobación está
autorado bajo la misma identidad de git (`emiledubois`) que cualquier
commit de agente en ese worktree, sin firma GPG/SSH, sin referencia a un
PR o sistema externo** — y cruzó esto contra `specs/SPEC.md` §8, que
define "hecho" como *"un humano aprobó el PR"*, específicamente un
approval mediado por GitHub, no un commit de texto dentro de un worktree
donde el propio agente también tiene permiso de escritura.

Conclusión del agente: mi commit de "aprobación" no es estructuralmente
distinguible de algo que un agente podría fabricar por sí mismo. Se negó
a implementar por segunda vez. No tocó ningún archivo.

**Este es el hallazgo más valioso del experimento**: la aprobación
humana *fue* real (el dueño del repo la dio explícitamente, fuera de la
autoridad de cualquier agente), pero la forma en que quedó *representada*
en el repositorio (un commit de texto plano, sin firma, misma identidad
que usa cualquier agente) no era verificable como distinta de una
auto-aprobación. El agente tenía razón en desconfiar de la forma, no
solo del contenido.

## Decisión

Se detuvo el experimento aquí, sin forzar la implementación, por
decisión explícita del dueño del repositorio — ver la discusión en la
conversación que generó este documento. La rama
`agentic-loop/audit-log-integrity` y el ADR aprobado quedan disponibles
si se decide implementar el hash-chain más adelante, esta vez a través
de un PR real en GitHub (que sí provee un canal de aprobación que ningún
agente con acceso solo al worktree puede falsificar).

## Conclusiones para el diseño del workspace

1. **La coordinación por archivos funciona** para pasar contexto y
   artefactos entre agentes sin memoria compartida (el ADR de
   `architect` fue suficiente para que `developer` entendiera la tarea
   completa sin ninguna otra explicación).
2. **ASI09 (no autoaprobación) no es solo un ítem de checklist**: se
   demostró funcionando espontáneamente dos veces, la segunda vez
   detectando una falla real en un intento humano-asistido de
   satisfacer el gate.
3. **Un gate de "aprobación humana" representado solo como texto en un
   archivo versionado por git, bajo la misma identidad que usan los
   agentes, es más débil de lo que parece** — no por mala fe de nadie,
   sino porque no hay nada que distinga estructuralmente "un humano lo
   escribió" de "un agente lo escribió diciendo que un humano lo
   escribió". `specs/SPEC.md` §8 ya especificaba correctamente "un
   humano aprobó el PR" como el estándar — este experimento demuestra
   *por qué* esa especificación importa en la práctica, no solo en la
   teoría: cualquier atajo que la evite (como un commit directo al
   worktree) reintroduce el problema que estaba diseñada para prevenir.
4. **Recomendación concreta para trabajo futuro**: los gates de
   aprobación humana de alto riesgo en este workspace deberían
   satisfacerse exclusivamente vía PR de GitHub aprobado/mergeado por
   una cuenta humana (verificable por la API de GitHub, no por el
   contenido de un commit), o vía un commit firmado con una clave que
   los agentes no tengan acceso a usar. Un commit sin firmar en un
   worktree con permisos de escritura para agentes no debería tratarse
   como equivalente.
