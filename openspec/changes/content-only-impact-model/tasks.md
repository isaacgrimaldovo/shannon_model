## 1. Dataset a nivel nota (sin autor/canal)

- [x] 1.1 En `src/shannon_model/impact_model/dataset.py`, crear `build_content_frame(structured_path, csv_urls_dir)`: una fila por nota, features = `feature_kinds.ACTIONABLE_FEATURES` + one-hot de `categoria_nota`, target = `by_note` de `load_real_views_targets` (reusa el cálculo existente, no lo duplica)
- [x] 1.2 Excluir explícitamente `autor_*`/`source_*` del frame resultante (verificar que ninguna columna de esas familias quede incluida por accidente)

## 2. CV simplificado

- [x] 2.1 Crear `cross_validate_content_model(content_df, seed, n_splits, model_params)` en `src/shannon_model/impact_model/cv.py`: `TimeSeriesSplit` sobre notas ordenadas por fecha, sin `fit_author_stats`/`apply_author_stats`
- [x] 2.2 `grid_search_content_model(content_df, seed, n_splits, param_grid)`: mismo patrón que `grid_search_cv` existente, sobre la función de 2.1

## 3. Entrenamiento final y reporte de impacto

- [x] 3.1 En `src/shannon_model/impact_model/pipeline.py`, agregar `run_content_only_pipeline(config)`: dataset (1.1) → grid search CV (2.2) → fit final sobre 100% → `build_impact_table` + `build_impact_table_by_category` (reusadas sin cambios) → persistir `model_content_only.joblib`, `feature_impact_content_only.csv`, `feature_impact_content_only_by_category.csv`
- [x] 3.2 `run_pipeline` (modelo A) queda sin cambios — se agrega el nuevo pipeline en paralelo, no se modifica el existente

## 4. Config y CLI

- [x] 4.1 Agregar sección `content_model.param_grid` (y `n_splits` si difiere) a `configs/views_impact.yaml`
- [x] 4.2 `scripts/train_views_model.py` corre ambos pipelines (A y B) y muestra el resumen de impacto de los dos, uno debajo del otro, con etiqueta clara de cuál es cuál

## 5. Verificación

- [x] 5.1 Correr `scripts/train_views_model.py` sobre los datos reales y confirmar que ambos modelos entrenan sin error y generan sus artefactos por separado — confirmado, ambos corrieron sin error, artefactos separados en `checkpoints/views_impact/`
- [x] 5.2 Confirmar que el modelo A y sus artefactos no cambiaron respecto a antes de este change — confirmado, valores SHAP idénticos a la corrida de `category-impact-breakdown` (`autor_avg_views` 0.504449, `source_Facebook` 0.297864, `autor_num_notas` 0.283567 — exactos)
- [x] 5.3 Comparar el top de impacto SHAP del modelo B contra el del modelo A — **hipótesis de masking NO confirmada en el sentido fuerte esperado**: las features de contenido (`num_palabras`, `largo_titulo`, `num_etiquetas`, `num_imagenes_real`, `tiene_numero`, `es_fin_de_semana`) tienen `mean_abs_shap` prácticamente IGUAL en ambos modelos (~0.03-0.045 en A y en B) — no crecieron al sacar autor/canal, solo subieron de *ranking relativo* porque las features más grandes (autor/source) ya no compiten. Lo que domina el top del modelo B no es contenido: es `categoria_nota` misma (`categoria_economia` 0.889, `categoria_estilo-de-vida` 0.290, `categoria_tendencias` 0.108) — la categoría de la nota es un proxy fuerte de vistas base (economia/estilo-de-vida tienen promedios de vistas muy distintos, ya visto en `data-quality-eda`), no es señal de "qué mejorar" en el contenido
- [x] 5.4 R² del modelo B = 0.602±0.025 (mejor combo), **más alto** que el modelo A (0.459±0.071) — pero engañoso: ese R² más alto viene de que `categoria_nota` por sí sola explica gran parte de la varianza (distintas categorías tienen promedios de vistas muy distintos), no de que el contenido estructural se volvió más predictivo
- [x] 5.5 `openspec validate --all` pasa sin errores
