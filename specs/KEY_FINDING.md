# KEY_FINDING.md — Un gate de "aprobación humana" no sirve si quien debe respetarlo puede escribir su propia prueba de que lo cumplió

> Este documento no describe código nuevo. Argumenta por qué
> `specs/AGENTIC_LOOP_EXPERIMENT.md` —no las tres herramientas de la
> CLI— es el resultado más interesante de este proyecto. Versión en
> inglés: `FINDINGS.md` (raíz del repo).

## 1. La pregunta

Un gate de aprobación humana es un control de seguridad estándar en
cualquier pipeline con revisión antes de aplicar un cambio (CODEOWNERS,
ambientes con aprobación manual, etc.). Ese patrón asume implícitamente
que quien podría estar tentado a saltárselo es una persona o un proceso
determinista.

Este proyecto agrega una variable que ese patrón no contempla: **¿qué
pasa cuando quien implementa el cambio es un agente de IA con permiso
de escritura sobre el mismo repositorio donde se registra la
aprobación?** ¿Sigue siendo válido representar "un humano aprobó esto"
como texto plano versionado, o ese canal deja de ser confiable en
cuanto el agente tiene acceso de escritura a él?

`specs/AGENTIC_LOOP_EXPERIMENT.md` responde esa pregunta de forma
empírica, no por argumento teórico: se montó la situación real
(worktree real, agentes frescos sin memoria compartida, una tarea
real) y se dejó que ocurriera lo que ocurriera, sin guionizar el
resultado de antemano.

## 2. Por qué esto, y no las tres herramientas de la CLI

Las tres herramientas (`preaudit run`, `certify`, `remediate`) son
necesarias pero no son el aporte: son la aplicación competente de
técnicas ya conocidas (partición de equivalencia, valores límite, tabla
de decisión, evidencia automatizada, informes estructurados). Demuestran
manejo de la materia, no generan conocimiento nuevo — son el sustrato
que hizo posible el experimento, no el punto en sí.

El experimento sí produce algo que no es obvio de antemano: que un gate
de aprobación humana representado como un commit de texto plano, bajo
la misma identidad de git que usan los agentes, **no es
estructuralmente distinguible de una autoaprobación** — y que un agente
que simplemente sigue su propio rol al pie de la letra puede detectar
esa falla sin que nadie se la programe explícitamente.

## 3. El experimento como caso de estudio (resumen)

Ver `specs/AGENTIC_LOOP_EXPERIMENT.md` para el registro completo. En
síntesis:

1. `architect` diseñó un ADR real (hash-chain para `logs/audit.log`,
   commit `f35b5f4`) con una condición explícita: "requiere aprobación
   humana antes de implementar".
2. `developer` (primer intento) verificó `git log`, no encontró esa
   aprobación, y se negó a implementar — sin que se le pidiera buscarla.
3. El dueño del repositorio aprobó explícitamente, fuera de la
   autoridad de cualquier agente. Se registró como commit de texto
   (`5f42999`), bajo la misma identidad de git usada en todo el repo.
4. `developer` (segundo intento, instancia fresca) verificó ese commit
   y lo rechazó también: notó que no tenía firma ni referencia a un PR,
   y que el estándar de "hecho" del proyecto exige aprobación "vía PR",
   no un commit de worktree. **La aprobación había sido real; su
   representación en el repositorio no era verificablemente distinta de
   una autoaprobación.**
5. Se detuvo el experimento ahí, por decisión explícita del dueño del
   repositorio, dejando el ADR aprobado-pero-no-implementado como
   registro honesto en vez de forzar un cierre artificial.

## 4. El hallazgo, en términos formales

> Un control de "aprobación humana" en un sistema donde agentes de IA
> tienen permiso de escritura sobre el mismo canal usado para
> *representar* esa aprobación no es un control válido, incluso si la
> aprobación en sí fue genuinamente humana — porque el control depende
> de que el canal sea inobservable/inescribible para la parte que debe
> ser controlada, y un commit de texto bajo la identidad compartida del
> repositorio no cumple esa condición.

Es una instancia concreta de un principio de seguridad clásico
(separación de privilegios entre quien ejecuta una acción y quien la
autoriza) aplicado a un contexto nuevo: agentes de IA como parte del
proceso cuyo output necesita autorización.

## 5. Qué agrega esto sobre la práctica estándar de aprobación en CI/CD

La idea de "canal de aprobación falsificable" no es nueva en seguridad
(es una variante de separación de privilegios / TOCTOU en control de
acceso). Lo que aporta el experimento es haberla encontrado *dentro de
un workspace agéntico real*, mediante el comportamiento espontáneo de
un agente que sigue su rol, no mediante un ataque diseñado a propósito
para ilustrar el punto.

## 6. Limitaciones honestas del experimento

- **n=1.** Es una corrida, no una serie estadísticamente representativa.
  El resultado es reproducible en su lógica (cualquier agente que lea
  el estándar de "hecho" del proyecto literalmente debería llegar a la
  misma conclusión), pero no se corrió múltiples veces ni con distintos
  modelos para medir variabilidad.
- **Un solo proveedor/familia de modelo.** No se sabe si el
  comportamiento de negarse-y-razonar-correctamente es específico de
  este modelo o generalizable.
- **El "éxito" del experimento depende de que los agentes sigan sus
  prompts fielmente.** Un agente con un prompt menos cuidadoso podría no
  haber detectado la falla — el hallazgo demuestra que *puede* pasar,
  no que *siempre* pasará sin un control estructural (de ahí la
  recomendación de §7: no depender de que el agente lo note).
- **No hay contraprueba con un agente adversarial real** intentando
  activamente fabricar una aprobación falsa; el segundo rechazo fue
  sobre una aprobación *genuina* mal representada, no sobre un intento
  de engaño deliberado. Sería un experimento de seguimiento válido.

## 7. Implicancia práctica / trabajo futuro

La recomendación que el propio experimento generó
(`specs/AGENTIC_LOOP_EXPERIMENT.md` §"Conclusiones", punto 4): los gates
de aprobación de alto riesgo deben satisfacerse vía un canal que los
agentes no puedan escribir por sí mismos — un PR de GitHub
aprobado/mergeado por una cuenta humana (verificable por API, no por
contenido de commit) o un commit firmado con una clave a la que los
agentes no tengan acceso. El ADR 0001 sigue aprobado y sin implementar
en la rama `agentic-loop/audit-log-integrity`; implementarlo **a través
de un PR real de GitHub** cerraría el experimento aplicando su propia
conclusión — pero es una decisión pendiente, no asumida por este
documento.
