## Why

El propósito final de Shannon (ver `shannon_diccionario_datos.xlsx`, hoja "Portada") es identificar qué características editoriales de una nota impactan más en las vistas. Ya existen dos insumos reales suficientes para un primer modelo: `data/raw/notes_structured.parquet` (features estructurales scrapeadas por `scrape-news-content`) y `data/raw/ehm_3months_filtered.xlsx` (`pageViewsTotal` por url). No hace falta esperar a la etapa NLP (tono/polaridad) ni a integrar Google Analytics para tener un baseline útil que ya empiece a mostrar impacto relativo de features en vistas.

## What Changes

- Nuevo dataset de entrenamiento: join de `notes_structured.parquet` (features) con `pageViewsTotal` agregado por url desde `ehm_3months_filtered.xlsx` (target proxy, no es el `views_7d` exacto del diccionario).
- Nuevo modelo baseline de regresión (árbol, ej. `RandomForestRegressor` de scikit-learn — ya es dependencia del proyecto) que predice `log(views_totales_proxy + 1)` a partir de features estructurales (`num_palabras`, `num_imagenes`, `num_etiquetas`, `tiene_img_principal`, derivados temporales, `categoria_nota`, features derivadas de autor).
- Explicabilidad con SHAP: valores SHAP convertidos a multiplicador de vistas (`exp(shap)`) por feature, siguiendo la etapa 6 del diccionario ("Resultados a editores").
- Features de autor derivadas (`autor_avg_views`, `autor_num_notas`) en vez de one-hot, según la guía de encoding del diccionario.
- Script CLI nuevo y módulo nuevo — no modifica `scripts/train.py`, `configs/default.yaml` ni el pipeline de entrenamiento sintético existente.
- **Fuera de alcance**: features de NLP (`tono`, `polaridad`, `categoria_titulo`) — no existen todavía. `views_7d`/`log_views` reales vía Analytics — se usa un proxy (suma de `pageViewsTotal`). Exclusión de notas breaking (`es_breaking`) — no calculable sin `views_1h`. Tuning de hiperparámetros o comparación de arquitecturas — solo baseline. Serving/API de predicción — solo entrenamiento + reporte de impacto.

## Capabilities

### New Capabilities
- `views-impact-model`: dataset de entrenamiento (join scraping + analytics), modelo baseline de regresión sobre vistas, y reporte de impacto de features vía SHAP.

### Modified Capabilities
(ninguna — no se toca `training-pipeline` para no mezclar con el roadmap de `training-foundation-next`)

## Impact

- Código nuevo: módulo `src/shannon_model/impact_model/` + script `scripts/train_views_model.py`.
- Dependencia nueva: `shap` (agregar a `requirements.txt`). `scikit-learn` ya está.
- Datos: consume `data/raw/notes_structured.parquet` (de `scrape-news-content`) y `data/raw/ehm_3months_filtered.xlsx`. Produce artefactos de modelo/reporte bajo un directorio nuevo, no versionado (ej. `checkpoints/views_impact/` o `models/`, a definir en design).
- Depende de `scrape-news-content`: mientras más notas tenga `notes_structured.parquet`, más robusto el baseline — puede correr con un subconjunto parcial.
- Sin impacto en `scripts/train.py`, Colab ni el pipeline sintético de `ShannonBaseline`.
