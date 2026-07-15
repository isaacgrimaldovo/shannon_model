## Why

`content-only-impact-model` confirmó que las features de contenido estructural (`num_palabras`, `largo_titulo`, `num_etiquetas`, `num_imagenes_real`, etc.) tienen SHAP casi plano (~0.03-0.045) en dos modelos distintos (modelo A completo, R² 0.459±0.071; modelo B sin autor/canal, R² 0.602±0.025 pero explicado por `categoria_nota`, no por contenido). No se sabe todavía si ese techo es una limitación de `RandomForestRegressor` o si realmente no hay más señal que exprimir en las features actuales. Antes de invertir en features NLP/texto (la apuesta grande y cara), conviene descartar la opción barata: probar otro algoritmo sobre exactamente las mismas features.

## What Changes

- Entrenar `GradientBoostingRegressor` (ya en scikit-learn, sin dependencia nueva) sobre el modelo A (dataset nota×source completo) y el modelo B (content-only), usando el mismo dataset, mismas features y mismo target (`views_7d` real, `log1p`) que ambos modelos actuales — no se toca `dataset.py`.
- Mismo esquema de CV: `TimeSeriesSplit` sobre notas ordenadas por fecha. Modelo A respeta `fit_author_stats`/`apply_author_stats` por fold (evitar leakage, decisión 9 de `predict-views-impact`); modelo B usa el CV simplificado sin author stats ya existente.
- Nuevo grid de hiperparámetros de GBR (`n_estimators`, `max_depth`, `learning_rate`, `subsample`) en `configs/views_impact.yaml`, sección propia — no reemplaza el grid de RandomForest.
- Reportar R² mean±std de GBR para ambos modelos, comparado en el mismo reporte contra los valores actuales de RandomForest.
- Reportar SHAP top features de GBR (reusando `build_impact_table`/`build_impact_table_by_category` sin cambios) para ver si el ranking de importancia cambia de algoritmo a algoritmo.
- RandomForest sigue siendo el modelo vigente — GBR convive en paralelo hasta decidir, con los resultados en mano, si vale la pena migrar.

## Capabilities

### New Capabilities
(ninguna — se modela como extensión de `views-impact-model`, reusa su infraestructura de dataset/CV/explain)

### Modified Capabilities
- `views-impact-model`: agrega un algoritmo alternativo (GradientBoostingRegressor) entrenado y evaluado en paralelo a RandomForest para ambos modelos (A y B), sin reemplazar el algoritmo vigente.

## Impact

- Código: `src/shannon_model/impact_model/cv.py` (grid search para GBR, reusando las funciones de CV existentes con el estimador parametrizado), `src/shannon_model/impact_model/pipeline.py` (orquestar el entrenamiento GBR en paralelo), `scripts/train_views_model.py` (reportar y comparar los 3 resultados: RF-A, RF-B, GBR-A, GBR-B).
- Config: extiende `configs/views_impact.yaml` con grid de hiperparámetros propio para GBR.
- Datos: nuevos artefactos `checkpoints/views_impact/model_gbr.joblib`, `model_content_only_gbr.joblib`, `feature_impact_gbr.csv`, `feature_impact_content_only_gbr.csv` (y sus versiones `_by_category`) — mismo directorio ya excluido de git.
- Sin dependencias nuevas (`GradientBoostingRegressor` ya en `scikit-learn>=1.4.0`, ya en `requirements.txt`).
- Fuera de alcance: XGBoost/LightGBM (requerirían dependencia nueva, se evalúan después si GBR muestra mejora), residualizar target por autor/canal, separar modelo por categoría, features NLP/texto.
- Sin impacto en `scrape-news-content`, `scraper-reliability`, `data-quality-eda` ni `section-editorial-opportunities`.
