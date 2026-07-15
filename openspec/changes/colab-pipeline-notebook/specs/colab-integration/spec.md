## ADDED Requirements

### Requirement: Notebook de pipeline de negocio

El repositorio SHALL incluir un notebook `notebooks/colab_pipeline.ipynb`, separado de `notebooks/colab_train.ipynb`, que ejecute el pipeline real de negocio (extract de notas, impacto en vistas, oportunidades editoriales) invocando los mismos entrypoints documentados en `docs/COLAB.md` (`scripts/scrape_news.py`, `scripts/train_views_model.py`, `scripts/report_editorial_opportunities.py`).

#### Scenario: Ejecucion manual completa
- **WHEN** el usuario ejecuta en orden las celdas de `notebooks/colab_pipeline.ipynb` (clone/install, mount Drive + copia de datos, extract, pipelines de negocio) con los datos esperados ya presentes en `data/raw/` y `data/processed/`
- **THEN** se generan `checkpoints/views_impact/model.joblib`, `checkpoints/views_impact/feature_impact.csv` y `checkpoints/editorial_opportunities/report.json` usando el codigo del clone, sin reimplementar la logica de extract/train dentro del notebook

### Requirement: Poll loop acotado a pasos rapidos

El poll loop de `notebooks/colab_pipeline.ipynb` SHALL detectar commits nuevos via `git pull`, filtrar por paths (`src/`, `scripts/`, `configs/`) igual que el poll loop de `colab_train.ipynb`, y disparar automaticamente `train_views_model.py` + `report_editorial_opportunities.py` cuando el filtro aprueba el cambio. El paso de extract (`scrape_news.py`) MUST NOT dispararse automaticamente desde este poll loop.

#### Scenario: Push toca configs/ de negocio
- **WHEN** el usuario hace commit y push de un cambio que toca `configs/views_impact.yaml` y el poll loop ya esta corriendo en Colab
- **THEN** dentro del intervalo de poll configurado, el loop detecta el commit nuevo y dispara `train_views_model.py` + `report_editorial_opportunities.py` con la config vigente, sin ejecutar `scrape_news.py`

#### Scenario: Push fuera de paths vigilados
- **WHEN** el commit nuevo detectado solo toca paths fuera de `src/`, `scripts/` y `configs/` (por ejemplo `README.md` o `docs/`)
- **THEN** el loop actualiza el SHA de referencia pero no dispara ningun run

#### Scenario: Interrupcion del loop
- **WHEN** el usuario presiona "Interrupt execution" en Colab mientras el loop de `colab_pipeline.ipynb` esta corriendo
- **THEN** el loop captura la interrupcion y termina sin dejar el proceso de `train_views_model.py` / `report_editorial_opportunities.py` en un estado colgado

### Requirement: Extract manual, no automatico

El notebook `colab_pipeline.ipynb` SHALL exponer el paso de extract (`scrape_news.py`, modo reprocess o fetch) como una celda de ejecucion manual e independiente del poll loop, dado que es una operacion lenta y dependiente de red.

#### Scenario: Extract no se re-dispara solo
- **WHEN** el poll loop detecta un commit nuevo que toca `scripts/scrape_news.py`
- **THEN** el loop dispara `train_views_model.py` + `report_editorial_opportunities.py` pero no ejecuta `scrape_news.py` automaticamente; el usuario debe correr esa celda a mano cuando lo necesite
