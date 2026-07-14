## Why

`category-impact-breakdown` confirmó que el modelo actual (`RandomForestRegressor` con las ~30 features juntas) reparte casi todo su peso SHAP en `autor_avg_views`/`autor_num_notas`/`source_*` — las features accionables de contenido (título, cuerpo, imágenes, estructura) quedan con impacto casi nulo en las 6 categorías, sin excepción. Esto no necesariamente significa que el contenido no importe: un modelo con features de autor/canal muy fuertes puede "tapar" (masking) el residuo de señal que el contenido sí tenga, porque el árbol gasta sus splits donde la señal es más limpia primero. Para poder ofrecer una recomendación de "qué cambiar en esta nota" que dependa de contenido real (opción B discutida), hace falta un modelo que no tenga autor/canal para competir por esa señal.

## What Changes

- Nuevo modelo (**modelo B**) entrenado **solo con features accionables** (`feature_kinds.ACTIONABLE_FEATURES`: título, cuerpo, imágenes, etiquetas, estructura, tiempo) + `categoria_nota` como contexto — sin `autor_avg_views`, `autor_num_notas` ni `source_*`.
- Dataset a nivel **nota** (no nota×canal): un target por nota (`views_7d` real, sumado entre canales), reusando el mismo cálculo que ya existe en `dataset.py` (`load_real_views_targets`, valor `by_note`) — no se reentrena a nivel nota×fuente porque sin `source` como feature esa granularidad solo agregaría filas casi-duplicadas sin nueva información.
- CV más simple que el modelo actual: sin ajuste de estadísticas de autor por fold (no aplica, autor no es feature), pero mantiene el mismo esquema temporal (`TimeSeriesSplit` sobre notas ordenadas por fecha) para evitar look-ahead.
- Reporta impacto SHAP (global y por categoría, reusando `build_impact_table`/`build_impact_table_by_category` de `category-impact-breakdown`) sobre este modelo — para confirmar si, aislado de autor/canal, el contenido sí muestra señal.
- **Fuera de alcance**: el entrypoint de "pasame una nota nueva y decime qué cambiar" (extracción de features de texto plano + contrafactual) — este change solo entrena y reporta el modelo B; el scoring de una nota puntual es un change posterior que consume este modelo ya entrenado.
- No modifica el modelo actual (modelo A, `predict-views-impact`) ni sus artefactos — conviven, dos modelos con propósitos distintos (mismo patrón que ya existe entre el modelo de CV y el modelo de SHAP dentro de modelo A).

## Capabilities

### New Capabilities
(ninguna — se modela como extensión de `views-impact-model`, no una capability nueva, porque reusa su infraestructura de dataset/CV/explain)

### Modified Capabilities
- `views-impact-model`: agrega un segundo modelo (features accionables únicamente, sin autor/canal) entrenado y evaluado en paralelo al modelo existente, con su propio reporte de impacto SHAP.

## Impact

- Código: `src/shannon_model/impact_model/dataset.py` (nueva función para el frame a nivel nota, sin autor/canal), `src/shannon_model/impact_model/cv.py` (CV simplificado sin author stats), `src/shannon_model/impact_model/pipeline.py` (orquestar el segundo modelo), `scripts/train_views_model.py` (reportar ambos modelos).
- Config: extiende `configs/views_impact.yaml` con un grid de hiperparámetros propio para el modelo B (puede diferir del modelo A — menos features, dataset más chico).
- Datos: nuevos artefactos `checkpoints/views_impact/model_content_only.joblib`, `feature_impact_content_only.csv`, `feature_impact_content_only_by_category.csv` — mismo directorio ya excluido de git.
- Sin dependencias nuevas.
- Sin impacto en `scrape-news-content`, `scraper-reliability`, `data-quality-eda` ni `section-editorial-opportunities` (no se tocan sus archivos).
