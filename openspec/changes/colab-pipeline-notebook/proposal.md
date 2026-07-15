## Why

`notebooks/colab_train.ipynb` solo corre el train sintetico (`scripts/train.py` + `configs/default.yaml`) para validar GPU/PyTorch. El pipeline real de negocio (extract de notas, impacto en vistas, oportunidades editoriales) esta documentado en `docs/COLAB.md` pero requiere copiar celdas a mano desde el doc — no existe un notebook versionado que lo ejecute. Se necesita poder correr y ver funcionar el flujo completo en Colab ahora, y que los pasos rapidos (views + editorial) se re-disparen solos ante cada push relevante, sin repetir el paso lento de extract en cada iteracion.

## What Changes

- Nuevo notebook `notebooks/colab_pipeline.ipynb` que ejecuta en orden: clone/install, mount Drive + copia de datos, extract (celda manual), `train_views_model.py`, `report_editorial_opportunities.py`, copia de resultados a Drive.
- Poll loop propio en el notebook: detecta commits nuevos via `git pull`, filtra por paths (`src/`, `scripts/`, `configs/`) y dispara `train_views_model.py` + `report_editorial_opportunities.py` automaticamente. El extract NO se dispara por el poll loop (es lento / depende de red) — queda como celda manual separada.
- `docs/COLAB.md` se referencia desde el notebook como fuente de detalle (secciones de layout de datos, flags de `scrape_news.py`).

## Capabilities

### New Capabilities
(ninguna — se extiende la capability existente `colab-integration`)

### Modified Capabilities
- `colab-integration`: se agrega el requisito de un segundo notebook de orquestacion (pipeline real de negocio) distinto del notebook de smoke train, con su propio poll loop acotado a los pasos rapidos (views + editorial), excluyendo extract del auto-trigger.

## Impact

- Archivo nuevo: `notebooks/colab_pipeline.ipynb`.
- Sin cambios en `scripts/scrape_news.py`, `scripts/train_views_model.py`, `scripts/report_editorial_opportunities.py` (se invocan tal cual, no se modifican).
- Sin cambios en `notebooks/colab_train.ipynb` (queda como esta: smoke train + su propio poll loop).
- Fuera de alcance: `Shannon_EDA_y_Scraping_3.ipynb` (notebook standalone con motor de scraping/EDA propio) no se toca en este change.

## Fuera de alcance / Non-goals

- No se modifica el motor de scraping standalone (`Shannon_EDA_y_Scraping_3.ipynb`) ni se migra su logica a `src/shannon_model/`.
- No se agrega auto-trigger de `extract` (scrape_news.py) en el poll loop — queda manual por ser lento y dependiente de red.
- No se cambia el notebook de smoke train (`colab_train.ipynb`) ni su poll loop existente.
- No se agregan nuevos flags/parametros a los scripts existentes; el notebook solo los invoca con la config ya definida en `configs/`.
