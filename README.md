# shannon_model

Proyecto de entrenamiento de modelo con Google Colab y colaboracion en equipo via GitHub.

## Estructura

```
shannon_model/
  configs/              hiperparametros YAML
  data/                 datos locales (no versionados)
  checkpoints/          pesos entrenados (no versionados)
  notebooks/            notebooks para Colab
  scripts/              CLI de entrenamiento
  src/shannon_model/    codigo reproducible
  docs/                 guias del equipo
```

## Arranque rapido (local)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/train.py --config configs/default.yaml
```

## Google Colab (equipo)

Guia completa (clone, Drive, **extract/scrape**, train de vistas, receta editorial):

**→ [`docs/COLAB.md`](docs/COLAB.md)**

Resumen:

1. Repo en GitHub: `isaacgrimaldovo/shannon_model`.
2. Runtime → GPU. Clonar en `/content` + `pip install -r requirements.txt`.
3. Copiar datos desde Drive a `data/raw/` y `data/processed/` (ver guía).
4. Extract: `python scripts/scrape_news.py --reprocess` (o scrape con fetch).
5. Pipelines: `train_views_model.py` + `report_editorial_opportunities.py`.

`notebooks/colab_train.ipynb` es solo **smoke test** (MLP sintético). No usa notas reales.

### Clonado tipico (repo publico)

```python
%cd /content
!git clone https://github.com/isaacgrimaldovo/shannon_model.git
%cd shannon_model
!pip install -q -r requirements.txt
```

Secrets / equipo: `docs/COLABORACION.md`.

## Trabajo en equipo

Ver `docs/COLABORACION.md`.

Resumen:
- Rama por feature / experimento
- No commitear datos ni checkpoints
- Cambios de hiperparametros en YAML bajo `configs/`
- Revisar por PR hacia `main`

## Spec-Driven Development (OpenSpec)

El repo usa OpenSpec para acordar comportamiento antes de implementar.

- Specs actuales: `openspec/specs/`
- Cambios activos: `openspec/changes/` (ver `training-foundation-next` como roadmap)
- Guia agentes: `AGENTS.md`, `CLAUDE.md`

Flujo corto (chat AI):

1. `/opsx:explore` (opcional) — mapear area
2. `/opsx:propose <nombre>` — proposal, specs delta, design, tasks
3. Revisar artefacts en `openspec/changes/<nombre>/`
4. `/opsx:apply` (implementacion) → `/opsx:archive` al cerrar

CLI util: `openspec list`, `openspec validate --all`, `openspec doctor`.

Docs: https://github.com/Fission-AI/OpenSpec

## Estado actual

- Smoke Colab/local: MLP sintético (`scripts/train.py`).
- Pipeline real: scrape/extract → `data/processed/notes_structured.parquet` + `data/raw/csv_urls/` → impacto vistas (SHAP) → reporte editorial (receta).
- Datos y checkpoints: no versionados; en Colab usar Drive (`docs/COLAB.md`).

## Config

Edita `configs/default.yaml` o crea `configs/exp_*.yaml`:

```bash
python scripts/train.py --config configs/exp_mi_prueba.yaml
```
