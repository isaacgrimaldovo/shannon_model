## Why

Hoy iterar contra Colab requiere reabrir y re-ejecutar manualmente la celda de pull + train cada vez que hay un cambio local. Eso corta el ciclo de feedback durante desarrollo activo (sesiones cortas, varios cambios seguidos). Se busca un loop en el propio notebook que detecte pushes nuevos y dispare el entrenamiento sin intervencion manual repetida, mantieniendo el codigo como unica fuente de verdad en git (Colab nunca commitea).

## What Changes

- Agregar celda de "poll loop" en `notebooks/colab_train.ipynb` que:
  - hace `git pull` cada N segundos (intervalo configurable, default 20s)
  - compara el SHA de HEAD contra el ultimo SHA corrido
  - si cambio y el diff toca `src/`, `scripts/` o `configs/`, dispara `scripts/train.py` con la config vigente
  - ignora cambios que solo tocan docs/README/notebooks
  - se detiene limpio ante interrupcion manual (boton Colab "Interrupt") sin dejar proceso colgado
- Documentar en el notebook (celda markdown) el flujo esperado: local commit+push -> Colab detecta y corre -> resultados en `checkpoints/` (o Drive si esta montado)
- Sin cambios en `src/shannon_model/` ni en `scripts/train.py` — el loop solo orquesta, no reimplementa el entrenamiento

## Capabilities

### New Capabilities

(ninguna)

### Modified Capabilities

- `colab-integration`: agrega requirement de deteccion automatica de cambios (poll de git) que dispara el entrenamiento sin re-ejecucion manual de celdas, con filtro de paths relevantes y corte limpio ante interrupcion

## Impact

- Afecta solo `notebooks/colab_train.ipynb` (celdas nuevas)
- No afecta `src/`, `scripts/train.py`, ni configs
- No agrega dependencias nuevas (usa `git`, `time`, `subprocess` ya disponibles en el runtime Colab)

## Fuera de alcance

- Webhooks/push real-time (GitHub Actions disparando Colab) — requeriria exponer un endpoint publico, no calza con sesiones cortas manuales
- Keep-alive / manejo de desconexion por inactividad de Colab (free tier) — se asume sesion corta supervisada
- Sync sin git (Drive como filesystem compartido) — se descarto en exploracion, prioriza trazabilidad de version
- Auto-commit/push desde local en cada guardado — el trigger sigue siendo push manual
