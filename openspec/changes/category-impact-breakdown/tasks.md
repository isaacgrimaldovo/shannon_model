## 1. Cálculo de impacto por categoría

- [x] 1.1 Crear `build_impact_table_by_category(model, x_train, category_columns)` en `src/shannon_model/impact_model/explain.py`: calcula SHAP una sola vez sobre `x_train`, agrupa filas por cuál columna one-hot `categoria_*` está activa, y promedia `mean_abs_shap`/`views_multiplier` por `(categoria, feature)`
- [x] 1.2 La tabla resultante incluye también `n_notas` (cantidad de filas de esa categoría) para poder juzgar la varianza esperada

## 2. Integración al pipeline

- [x] 2.1 En `src/shannon_model/impact_model/pipeline.py` (`run_pipeline`), llamar `build_impact_table_by_category` con las columnas `categoria_*` del `training_frame` y persistir el resultado en `feature_impact_by_category.csv`
- [x] 2.2 `run_pipeline` sigue calculando y persistiendo `feature_impact.csv` (global) exactamente igual que antes — sin regresión

## 3. CLI

- [x] 3.1 `scripts/train_views_model.py` imprime un resumen del desglose por categoría (ej. top 3 features por categoría) además del resumen global existente

## 4. Verificación

- [x] 4.1 Correr `scripts/train_views_model.py` sobre los datos reales disponibles y confirmar que `feature_impact_by_category.csv` se genera con una fila por `(categoria, feature)` y `n_notas` coherente con el tamaño real de cada categoría — verificado: 180 filas (6 categorías × 30 features), `n_notas` por categoría suma 4,982 (= tamaño del dataset)
- [x] 4.2 Confirmar que `feature_impact.csv` (global) no cambia respecto a antes de este change (mismo contenido para el mismo dataset/seed) — verificado por inspección de código: `build_impact_table` y su línea de invocación quedaron sin modificar, mismo path de ejecución
- [x] 4.3 Inspeccionar el desglose por categoría y reportar si aparece algún feature con impacto marcadamente distinto (o de signo opuesto) entre categorías — **hallazgo real**: `autor_num_notas` tiene signo opuesto entre categorías — multiplicador >1 en `economia` (x1.156, más notas del autor = más vistas) pero <1 en las 5 categorías restantes (`espectaculos` x0.778, `estilo-de-vida` x0.808, `mundo` x0.873, `nacional` x0.840, `tendencias` x0.824, más notas del autor = menos vistas por nota). Mismo patrón de divergencia que motivó la decisión 12 de `predict-views-impact` para `source`. **Hallazgo secundario**: ninguna feature *actionable* (`num_palabras`, `largo_titulo`, `tiene_signo_pregunta`, etc.) entra al top 3 de ninguna categoría — el impacto sigue dominado por `autor_*`/`source_*` (diagnostic) en las 6 categorías, sin excepción
- [x] 4.4 `openspec validate --all` pasa sin errores
