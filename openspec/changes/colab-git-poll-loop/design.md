## Context

`notebooks/colab_train.ipynb` ya clona/hace pull del repo y opcionalmente monta Drive para checkpoints/datos, pero cada nuevo cambio local requiere re-ejecutar manualmente la celda de pull + entrenamiento. El objetivo es agregar una celda de "poll loop" que automatice ese re-disparo dentro de una sesion Colab ya abierta, sin cambiar la fuente de verdad del codigo (sigue viviendo en el repo local, versionado en git).

Sesiones son cortas (minutos a ~1h), supervisadas por el usuario — no se necesita keep-alive ni manejo de reconexion de runtime.

## Goals / Non-Goals

**Goals:**
- Loop en una celda del notebook que detecte commits nuevos via `git pull` + comparacion de SHA
- Disparar `scripts/train.py` solo cuando el diff toca paths relevantes (`src/`, `scripts/`, `configs/`)
- Corte limpio ante interrupcion manual (Colab "Interrupt"), sin dejar el proceso de training a medias sin feedback
- Loguear cada iteracion (SHA, si corrio o no, motivo) para que el usuario vea el estado del loop

**Non-Goals:**
- Webhooks o triggers real-time desde GitHub
- Keep-alive / reconexion automatica de runtime Colab
- Auto-commit o auto-push desde el entorno local
- Cambios a `src/shannon_model/` o `scripts/train.py`

## Decisions

**Poll interval fijo con default 20s, configurable via variable en la celda**
Alternativa considerada: watchdog/webhook — descartada porque requiere exponer un endpoint publico desde Colab (tunel), complejidad injustificada para sesiones cortas supervisadas.

**Filtro de paths via `git diff --name-only <sha_anterior> <sha_nuevo>`**
Evita re-entrenar en cambios que solo tocan `README.md`, `docs/`, o el propio notebook. Alternativa (correr siempre que haya commit nuevo) generaria runs innecesarios y ruido en checkpoints.

**Loop vive en la celda del notebook, no en un script separado (`scripts/colab_watch.py`)**
Mantiene consistencia con la convencion existente de "notebooks solo orquestan" pero sin agregar un archivo nuevo al paquete versionado que solo tiene sentido en contexto Colab. El loop es codigo de orquestacion, no logica de entrenamiento.

**Deteccion de cambios via polling de git, no via `inotify`/watchdog sobre el filesystem**
El filesystem de Colab es una copia clonada; el cambio real ocurre en GitHub via push local. Polling de `git pull` es la señal correcta, no hace falta observar el filesystem local del runtime.

**Manejo de interrupcion: `try/except KeyboardInterrupt` alrededor del loop**
Colab traduce el boton "Interrupt execution" en `KeyboardInterrupt` sobre la celda corriendo. Sin este manejo, la interrupcion corta el loop en medio de un `subprocess.run` de forma abrupta sin mensaje claro.

## Risks / Trade-offs

- [Latencia de hasta `poll_interval` segundos entre push y run] → aceptable para sesiones cortas supervisadas; el usuario puede bajar el intervalo si necesita mas velocidad
- [Si el training tarda mas que el poll interval, el loop debe esperar a que termine antes de chequear de nuevo] → el `git pull` + chequeo de SHA solo corre entre runs, nunca en paralelo a un training activo (loop secuencial, no concurrente)
- [Filtro de paths por nombre puede dar falsos negativos si un cambio relevante toca un path no listado] → lista de paths documentada y facil de editar en la celda; se prioriza evitar runs innecesarios sobre cubrir el 100% de casos
- [Usuario cierra el notebook o pierde conexion a media ejecucion] → mismo comportamiento que cualquier celda larga en Colab hoy, sin cambio de riesgo respecto al flujo actual

## Migration Plan

- Cambio aditivo: se agregan celdas nuevas al notebook, no se modifican las existentes (clone/pull, mount Drive)
- No requiere migracion de datos ni checkpoints
- Rollback: eliminar las celdas nuevas, el notebook vuelve al flujo manual actual

## Open Questions

(ninguna pendiente — decisiones cerradas en exploracion previa)
