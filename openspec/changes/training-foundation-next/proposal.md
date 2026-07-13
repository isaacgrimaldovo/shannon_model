# Proposal: Foundation next - dataset real, arquitectura y tracking

## Why

El bootstrap (datos sinteticos + MLP + Colab/Git) ya valida el entorno. El equipo necesita un camino especificado hacia entrenamiento con datos reales, arquitectura definitiva y tracking de experimentos, sin romper el pipeline local+Colab actual.

## What Changes

- Definir e integrar ruta/fuente del dataset real (Drive / URL / Kaggle u otra acordada).
- Sustituir o extender el baseline MLP por la arquitectura final acordada, manteniendo config YAML.
- Anadir experiment tracking opcional (p. ej. Weights & Biases) sin hacerlo obligatorio para runs locales/Colab minimos.
- Actualizar specs (`training-pipeline`, y dominios nuevos si aplica) al archivar.

## Impact

- Afecta: `src/shannon_model/` (data loaders, model), `configs/`, posiblemente `notebooks/colab_train.ipynb`, `requirements.txt` / `pyproject.toml`, `.env.example`.
- No afecta (salvo docs): flujo Git/PR ya documentado.
- Riesgo: romper bootstrap sintetico si no se mantiene un modo fallback.

## Fuera de alcance

- Reescritura completa del repo o cambio de stack.
- Infra de serving/inference en produccion.
- CI/CD de entrenamiento en la nube (puede proponerse despues).
- Commits automaticos de checkpoints o datasets.

## Non-goals

- No exigir W&B (u otro tracker) para que un run exitoso sea valido.
- No eliminar el modo sintetico hasta que el dataset real este estable.
