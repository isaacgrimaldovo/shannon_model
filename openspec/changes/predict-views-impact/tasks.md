## 1. Setup

- [x] 1.1 Agregar `shap` a `requirements.txt`
- [x] 1.2 Crear módulo `src/shannon_model/impact_model/`
- [x] 1.3 Crear `configs/views_impact.yaml` (paths de entrada, hiperparámetros del `RandomForestRegressor`, seed, test_split)
- [x] 1.4 Crear script CLI `scripts/train_views_model.py`

## 2. Dataset de entrenamiento

- [x] 2.1 Implementar agregación de `pageViewsTotal` por url desde `ehm_3months_filtered.xlsx` (suma) + `log1p`
- [x] 2.2 Implementar join entre `notes_structured.parquet` y el target agregado por url
- [x] 2.3 Implementar features derivadas de autor (`autor_avg_views` leave-one-out, `autor_num_notas`)
- [x] 2.4 Implementar selección de columnas de entrada (excluir `nota_id`, `url`, `titulo`, `autor_nombre`, `autor_slug`, `fecha_publicacion` crudos)
- [x] 2.5 Implementar split train/test aleatorio con semilla desde config

## 3. Entrenamiento del modelo baseline

- [x] 3.1 Implementar entrenamiento de `RandomForestRegressor` con hiperparámetros desde config
- [x] 3.2 Calcular y reportar métricas de validación (MAE/R² en escala log) por consola
- [x] 3.3 Persistir modelo entrenado (`joblib`) bajo `checkpoints/views_impact/`

## 4. Reporte de impacto (SHAP)

- [x] 4.1 Calcular valores SHAP sobre el modelo entrenado (`TreeExplainer`)
- [x] 4.2 Convertir SHAP promedio por feature a multiplicador de vistas (`exp(shap)`)
- [x] 4.3 Persistir tabla de impacto por feature bajo `checkpoints/views_impact/`

## 5. Verificación

- [x] 5.1 Correr `scripts/train_views_model.py` end-to-end sobre las notas ya scrapeadas disponibles y confirmar que termina sin error
- [x] 5.2 Confirmar que el tamaño del dataset usado y las métricas quedan reportadas en la salida de consola
- [x] 5.3 Revisar que la tabla de impacto por feature tenga valores coherentes — hallazgo: `tiene_img_principal`/`num_imagenes` salen constantes (el JSON-LD del sitio siempre reporta 3 variantes de la imagen hero, no el conteo real de imágenes del cuerpo), documentado como limitación conocida en vez de ignorado
- [x] 5.4 Confirmar que `checkpoints/views_impact/` no queda trackeado por git

## 6. Nuevas features (depende de scrape-news-content 6.1-6.5)

- [x] 6.1 Actualizar `FEATURE_COLUMNS` en `src/shannon_model/impact_model/dataset.py`: quitar `tiene_img_principal`/`num_imagenes`, agregar `num_imagenes_real`, `largo_titulo`, `num_letras`
- [x] 6.2 Re-entrenar con `scripts/train_views_model.py` y confirmar que `num_imagenes_real` ya no sale constante en la tabla de impacto — confirmado: rango real 0-15 imágenes, mean_abs_shap=0.018 (ya no es 0)
- [x] 6.3 Revisar si `largo_titulo`/`num_letras` aportan señal (mean_abs_shap > 0) o son redundantes con `num_palabras` — aportan señal débil, similar magnitud a `num_palabras` (0.007-0.012), no redundante pero tampoco fuerte

## 7. Evaluación por k-fold fold-safe (sin fuga de autor)

- [x] 7.1 Refactorizar `add_author_features` en `src/shannon_model/impact_model/dataset.py`: separar en `fit_author_stats(train_df) -> stats` y `apply_author_stats(df, stats) -> df`
- [x] 7.2 Implementar loop de `KFold(5, shuffle=True, random_state=seed)`: por cada fold, `fit_author_stats` solo con las filas de train de ese fold, `apply_author_stats` a train y validación
- [x] 7.3 Entrenar un `RandomForestRegressor` por fold y calcular MAE/R² de validación de ese fold
- [x] 7.4 Reportar métricas como media ± desvío estándar entre los 5 folds (no un solo número)
- [x] 7.5 Comparar el R² medio del CV fold-safe contra el R² del split único actual (0.533) — **CONFIRMADO**: R² fold-safe cae a ~0.03±0.02 (vs 0.533 con fuga). El modelo anterior memorizaba autor, no generalizaba. Señal real de las features actuales es prácticamente nula.
- [x] 7.6 Grid chico de hiperparámetros (`n_estimators`, `max_depth`, `min_samples_leaf`) evaluado sobre el mismo esquema de CV fold-safe; elegir la combinación con mejor media de R²/MAE — ganador: `n_estimators=300, max_depth=10, min_samples_leaf=3` (r2_mean=0.031), pero todas las combinaciones del grid quedan en el mismo rango (0.02-0.03) — el cuello de botella es señal de features, no hiperparámetros
- [x] 7.7 Modelo final para el reporte SHAP: fit sobre el 100% del dataset con los mejores hiperparámetros encontrados (separado de los modelos de CV)
- [x] 7.8 Actualizar `configs/views_impact.yaml` con los hiperparámetros ganadores y (si aplica) un parámetro para el número de folds — `cv.n_splits` y `cv.param_grid` agregados, grid incluye el combo ganador

## 8. Tier 1 restante (depende de scrape-news-content 7.1-7.8)

- [x] 8.1 Agregar `tiene_signo_pregunta`, `tiene_numero`, `tiene_mayusculas_excesivas`, `num_parrafos`, `tiene_subtitulos`, `tiene_video_embed` a `FEATURE_COLUMNS` en `src/shannon_model/impact_model/dataset.py`
- [x] 8.2 Re-correr CV fold-safe + grid de hiperparámetros con las 6 features nuevas — r2_mean=0.031±0.024 (idéntico al baseline de 0.031)
- [x] 8.3 Comparar r2_mean nuevo contra el baseline (0.031) — **CONFIRMADO: no mueve la aguja.** Las 6 features Tier 1 quedaron últimas en la tabla de impacto (mean_abs_shap 0.0004-0.004, por debajo de `es_fin_de_semana`). El cuello de botella no es "falta esta o aquella feature barata" — la familia completa de señales estructurales/de forma está agotada. Siguiente paso real: `source` como feature (granularidad por canal) o NLP (`tono`)

## 9. Granularidad url×source (depende de análisis de correlación por canal — ver design.md decisión 12)

- [x] 9.1 Implementar construcción del dataset a nivel url×source: join `notes_structured.parquet` con `pageViewsTotal` agrupado por (url, source) en vez de por url — 3,406 notas → 4,983 filas url×source
- [x] 9.2 Agregar `source` como feature one-hot (Facebook, Google, Google Discover, dark social)
- [x] 9.3 Mantener `autor_avg_views`/`autor_num_notas` a nivel nota (no por combinación nota×source) — `fit_author_stats` dedupe por `url` antes de agrupar
- [x] 9.4 Reemplazar `KFold` por `GroupKFold` (o equivalente) agrupando por `url` en el CV fold-safe, para que todas las filas de una nota queden del mismo lado del split
- [x] 9.5 Re-correr CV fold-safe + grid de hiperparámetros con la nueva granularidad
- [x] 9.6 Comparar r2_mean nuevo contra el baseline agregado (0.031) — **CONFIRMADO Y GRANDE: r2_mean 0.031→0.098 (~3x), r2_std 0.024→0.015 (más estable, no es ruido).** Modelar por canal recuperó la señal real que la mezcla cancelaba.
- [x] 9.7 Revisar en la tabla de impacto si aparecen interacciones feature×`source` con multiplicador de vistas distinto por canal — `source_Google`, `source_Facebook`, `source_dark social`, `source_Google Discover` aparecen 2do-5to lugar en impacto (por debajo solo de `autor_avg_views`), confirmando que el canal en sí es una de las señales más fuertes del modelo

## 10. Target real views_7d desde data/raw/csv_urls (ver design.md decisión 14)

- [x] 10.1 Mover a `dataset.py` de producción la lógica de carga de `data/raw/csv_urls/` (concatenar CSVs diarios, filtrar filas `"Total"`, excluir `ehm-90-google-economia.csv` por formato viejo, excluir el archivo `ehm_report-*.csv`)
- [x] 10.2 Implementar cálculo de ventana observada (min/max `date`) y filtro de notas con `views_7d` completamente observable (`publishDate >= window_start` y `publishDate + 7d <= window_end`)
- [x] 10.3 Implementar `views_7d` real por combinación (url, source) — reemplaza `load_views_target_by_source` (proxy) como target de entrenamiento
- [x] 10.4 Implementar `views_7d` real por nota (suma sobre todos los canales) — reemplaza `load_views_target` (proxy) para `fit_author_stats`/`autor_avg_views`
- [x] 10.5 Actualizar `configs/views_impact.yaml`: agregar `data.csv_urls_dir`, quitar `data.analytics_xlsx` (ya no se usa en este capability)
- [x] 10.6 Re-correr el pipeline de producción end-to-end y confirmar r2_mean ≈ 0.48 (vs 0.098 con el proxy anterior) — **confirmado: r2_mean=0.490±0.058**, consistente con el experimento aislado (0.480)
- [x] 10.7 Confirmar que el dataset de producción cae a ~2,823 notas (de las 3,406 scrapeadas) y que eso queda reportado en la salida de consola, no oculto — confirmado: 4,982 filas / 2,823 notas únicas, impreso en la salida de `train_views_model.py`

## 11. CV temporal reemplaza GroupKFold aleatorio (ver design.md decisión 15)

- [x] 11.1 Mantener `fecha_publicacion` disponible en `base_df` (bookkeeping, excluida de features) para poder ordenar por fecha
- [x] 11.2 Reemplazar `GroupKFold` por `TimeSeriesSplit` sobre urls únicas ordenadas por `fecha_publicacion`, expandido a filas después (mismo cuidado que 9.4: ninguna nota partida entre train/validación)
- [x] 11.3 Re-correr el pipeline de producción con CV temporal y comparar r2_mean contra el CV aleatorio (0.490) — **r2_mean=0.459±0.071** (vs 0.490±0.058 aleatorio). Baja poco (~6% relativo) y el desvío sube algo — el modelo generaliza razonablemente a notas futuras, no es un caso de overfitting a interpolación aleatoria
