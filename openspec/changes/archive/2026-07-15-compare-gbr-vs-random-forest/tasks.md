## 1. Parametrizar el estimador en `cv.py` y `train.py`

- [x] 1.1 En `src/shannon_model/impact_model/cv.py`, agregar parámetro `model_cls: type = RandomForestRegressor` a `cross_validate`, `cross_validate_content_model`, `grid_search_cv` y `grid_search_content_model`; reemplazar la instanciación hardcodeada por `model_cls(random_state=seed, **model_params)`
- [x] 1.2 En `src/shannon_model/impact_model/train.py`, agregar parámetro `model_cls: type = RandomForestRegressor` a `fit_final_model`, mismo cambio de instanciación
- [x] 1.3 Verificar que las llamadas existentes (sin pasar `model_cls`) siguen usando `RandomForestRegressor` y producen resultados idénticos a antes de este change

## 2. Parametrizar orquestación en `pipeline.py`

- [x] 2.1 En `src/shannon_model/impact_model/pipeline.py`, agregar parámetros `model_cls: type = RandomForestRegressor` y `artifact_suffix: str = ""` a `run_pipeline` y `run_content_only_pipeline`; propagar `model_cls` a `grid_search_cv`/`grid_search_content_model`/`fit_final_model`/instanciación directa
- [x] 2.2 Insertar `artifact_suffix` en los nombres de archivo de salida antes de la extensión (`model.joblib` → `model{suffix}.joblib`, `feature_impact.csv` → `feature_impact{suffix}.csv`, `feature_impact_by_category.csv` → `feature_impact{suffix}_by_category.csv`, y equivalentes de `run_content_only_pipeline`)
- [x] 2.3 Confirmar que llamar ambas funciones sin argumentos nuevos genera exactamente los mismos artefactos que antes (`model.joblib`, `model_content_only.joblib`, etc.)

## 3. Config: grids de hiperparámetros de GBR

- [x] 3.1 En `configs/views_impact.yaml`, agregar sección `gbr_model.param_grid` (hiperparámetros de `GradientBoostingRegressor`: `n_estimators`, `max_depth`, `learning_rate`, `subsample`) para el modelo A
- [x] 3.2 Agregar sección `content_gbr_model.param_grid` con grid equivalente para el modelo B (dataset más chico, valores conservadores similares al criterio ya usado en `content_model.param_grid`)
- [x] 3.3 En `src/shannon_model/impact_model/pipeline.py`, agregar campos `gbr_param_grid` y `content_gbr_param_grid` a `ImpactModelConfig` (mismo patrón que `param_grid`/`content_model_param_grid`)

## 4. Script de entrenamiento: correr y comparar los 4 pipelines

- [x] 4.1 En `scripts/train_views_model.py`, cargar `gbr_model.param_grid` y `content_gbr_model.param_grid` desde el YAML hacia `ImpactModelConfig`
- [x] 4.2 Correr `run_pipeline`/`run_content_only_pipeline` con `model_cls=GradientBoostingRegressor`, `artifact_suffix="_gbr"` y los grids de GBR, además de las corridas existentes con RandomForest
- [x] 4.3 Agregar una tabla comparativa final que muestre R² mean±std (y MAE mean±std) de las 4 combinaciones (RandomForest-A, RandomForest-B, GBR-A, GBR-B) una debajo de la otra, con etiqueta clara de cuál es cuál

## 5. Verificación

- [x] 5.1 Correr `python scripts/train_views_model.py --config configs/views_impact.yaml` sobre los datos reales y confirmar que las 4 combinaciones entrenan sin error y generan sus artefactos por separado en `checkpoints/views_impact/`
- [x] 5.2 Confirmar que los artefactos de RandomForest (`model.joblib`, `model_content_only.joblib`, `feature_impact.csv`, `feature_impact_content_only.csv` y `_by_category`) no cambiaron respecto a la corrida anterior a este change (mismos valores SHAP)
- [x] 5.3 Documentar en el resumen de la corrida (o en `design.md`, sección de resultados) si GBR mejora, empata o empeora el R² de RandomForest en modelo A y en modelo B — esta es la respuesta que motiva el change
- [x] 5.4 `openspec validate --all` pasa sin errores
