# Design: Foundation next

## Context

Hoy el pipeline usa `build_synthetic_loaders` + `ShannonBaseline` (MLP) y entrypoint `scripts/train.py`. Colab orquesta el mismo codigo. OpenSpec ya documenta el comportamiento actual en `openspec/specs/`.

## Goals / Non-Goals

**Goals**
- Una via clara para datos reales sin romper el bootstrap.
- Arquitectura final plug-in via config (`model.name` / factory).
- Tracking opcional detras de flag/env.

**Non-goals**
- Forzar tracker en todos los runs.
- Eliminar sinteticos en el primer merge.

## Decisions

1. **Datos**: introducir loader real detras de una clave de config (p. ej. `data.source: synthetic | local | drive | url`) con `synthetic` como default hasta que el equipo fije la fuente.
2. **Modelo**: registrar arquitecturas por nombre en config; baseline permanece hasta que exista la real.
3. **Tracking**: opcional via env (`WANDB_API_KEY` ya en `.env.example`); si no hay key/flag, el run solo loguea a consola/archivo local.
4. **Colab**: notebook sigue orquestando; celdas nuevas solo si Drive/Kaggle lo requieren.

## Risks / Trade-offs

| Riesgo | Mitigacion |
|--------|------------|
| Dataset grande en git | Mantener gitignore; documentar download |
| Divergencia local vs Colab | Un solo entrypoint + YAML |
| Dependencia dura de W&B | Flag off por defecto |

## Migration Plan

1. Specs/tasks (esta change) -> acuerdo de fuente de datos y arquitectura.
2. Implementar loaders/modelo con fallback sintetico.
3. Anadir tracking opcional.
4. Actualizar notebook y docs.
5. `/opsx:archive` tras verificar local + Colab.

## Open Questions

- Fuente canonica del dataset (Drive path, URL, Kaggle, otro)?
- Arquitectura objetivo y metricas de exito?
- Tracker preferido (W&B vs MLflow vs solo CSV local)?
