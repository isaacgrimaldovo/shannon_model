## Context

`scrape-news-content` produce `data/raw/notes_structured.parquet` (features estructurales por nota). El target de entrenamiento pasó por dos versiones: primero un proxy (`ehm_3months_filtered.xlsx`, suma de `pageViewsTotal` sobre una ventana arbitraria de 3 meses), y luego `views_7d` real (ver decisión 14) calculado desde `data/raw/csv_urls/` (granularidad diaria, ventana fija de 90 días) — ya no hace falta esperar integración con Google Analytics. No hay `tono`/`polaridad` (etapa NLP) — sigue pendiente. El diccionario de datos ya especifica qué hacer con lo que sí existe: variables numéricas van sin scaling si el modelo es de árboles, `autor_id` no debe ir one-hot (usar `autor_avg_views`/`autor_num_notas` derivadas), y el resultado final se reporta como SHAP values convertidos a multiplicador de vistas (`exp(shap)`).

El scraping (`scrape-news-content`) puede seguir corriendo en paralelo — este modelo debe poder entrenarse con el subconjunto de notas ya scrapeadas en cualquier momento, sin exigir el dataset completo.

## Goals / Non-Goals

**Goals:**
- Construir un dataset de entrenamiento uniendo features estructurales scrapeadas con un target real de vistas (`views_7d`, ver decisión 14).
- Entrenar un modelo baseline de regresión que sirva como primera señal de impacto de features en vistas.
- Reportar impacto por feature vía SHAP, en el formato multiplicador de vistas que el diccionario define para editores.
- Correr con cualquier tamaño de `notes_structured.parquet` disponible (no bloquear en que el scraping termine).
- Medir generalización real sin fuga de datos de autor entre train/validación (5-fold CV fold-safe).

**Non-Goals:**
- Incorporar `tono`, `polaridad`, `categoria_titulo` (NLP) — no existen todavía.
- Excluir notas breaking (`es_breaking`) — no calculable sin `views_1h`.
- Comparación de arquitecturas distintas (XGBoost, LightGBM, redes) o selección automática de modelo — sigue siendo un único tipo de modelo (`RandomForestRegressor`); solo se ajustan sus hiperparámetros vía grid chico sobre el CV fold-safe.
- Servir el modelo (API/inferencia online) — solo entrenamiento + reporte offline.
- Tocar `scripts/train.py`, `configs/default.yaml` o el flujo Colab existente.

## Decisions

**1. Target proxy: suma de `pageViewsTotal` por url, transformado con `log1p`.**
`ehm_3months_filtered.xlsx` tiene una fila por url x source x fecha; sumar `pageViewsTotal` agrupando por url da el total de vistas observadas en la ventana de 3 meses del export. No es `views_7d` (ventana fija de 7 días desde publicación) pero es la señal de vistas más cercana disponible sin integrar Analytics.
Alternativa descartada: esperar a implementar la integración con Google Analytics antes de tener cualquier modelo — bloquea indefinidamente el objetivo final de Shannon (identificar impacto de features) por una pieza que no depende de este change.
**Actualización — ver decisión 12:** sumar todas las fuentes en un solo target resultó ser parte del problema, no solo una simplificación inocente. Se reemplaza por un target por combinación url×source.

**2. Modelo baseline: `RandomForestRegressor` (scikit-learn), no red neuronal.**
`scikit-learn` ya es dependencia del proyecto. El diccionario mismo recomienda árboles para este tipo de tabular pequeño/mediano (no requieren scaling, manejan bien variables mixtas) y son compatibles con SHAP `TreeExplainer` (rápido, exacto, sin aproximaciones). Con pocas features y un dataset que puede ser chico (mientras el scraping avanza), un MLP no aporta ventaja y complica el pipeline.
Alternativa descartada: reusar `ShannonBaseline` (MLP de `src/shannon_model/model.py`) — ese modelo es para el pipeline de clasificación sintético de `training-pipeline`, no para este dataset tabular de regresión; forzarlo mezclaría responsabilidades de dos capabilities distintas.

**3. Features de autor: `autor_avg_views` y `autor_num_notas`, no one-hot.**
Siguiendo la guía de encoding del diccionario. Se calculan sobre el propio set de entrenamiento (media histórica de vistas del autor, conteo de notas). Riesgo de leakage documentado abajo.

**4. Módulo nuevo `src/shannon_model/impact_model/`, script nuevo `scripts/train_views_model.py`, config nueva `configs/views_impact.yaml`.**
Mismo patrón que `scripts/train.py` (config YAML + entrypoint CLI), pero completamente separado del pipeline de `training-pipeline` — evita mezclar este baseline exploratorio con el roadmap de arquitectura final que ya cubre `training-foundation-next`.

**5. Split train/test aleatorio (no temporal) para el baseline.**
Simplicidad: con dataset chico y target proxy (no una ventana temporal real de 7 días), un split temporal no aporta rigor adicional todavía. Se deja como pregunta abierta para cuando exista `views_7d` real.

**6. Artefactos de salida bajo `checkpoints/views_impact/` (ya cubierto por `.gitignore: checkpoints/*`).**
Reutiliza la exclusión de git existente en vez de crear un patrón nuevo en `.gitignore`. Contiene: modelo serializado (`joblib`), tabla de métricas, tabla de impacto por feature (SHAP → `exp(shap)`).

**7. `num_imagenes`/`tiene_img_principal` salen del set de features; se reemplazan por `num_imagenes_real`.**
La primera corrida del baseline (658 notas) mostró SHAP=0 para ambas — son constantes porque vienen del JSON-LD (siempre 3 variantes de la imagen hero, ver decisión 7 de `scrape-news-content`). No aportan señal ni la van a aportar con más datos, porque el problema es la fuente, no el tamaño de muestra. `num_imagenes_real` (conteo real de `<img>` en el cuerpo, agregado en `scrape-news-content`) las reemplaza en `FEATURE_COLUMNS`.
Alternativa descartada: dejar las tres — `num_imagenes`/`tiene_img_principal` no aportan nada al modelo, solo ruido en la tabla de impacto.

**8. `largo_titulo` y `num_letras` se agregan a `FEATURE_COLUMNS` sin transformación.**
Mismo criterio que `num_palabras`/`num_etiquetas`: modelo de árboles, no requieren scaling. Se suman directo a la lista de features numéricas existente.

**9. Evaluación por 5-fold CV fold-safe, separada del modelo de explicación.**
La corrida con dataset completo (3,406 notas) mostró `autor_avg_views` + `autor_num_notas` concentrando 67% del peso SHAP total (0.428 + 0.245 vs 0.085 del resto de 10 features) — con 128 autores y el top 10 cubriendo 55% del dataset, esto es consistente con el modelo memorizando "quién firma la nota" en vez de aprender señal editorial. La causa raíz: `autor_avg_views` (leave-one-out, decisión 3) hoy se calcula sobre el dataset COMPLETO, no por fold — filtra información de lo que sería el fold de validación hacia el de entrenamiento.
Fix: reemplazar `add_author_features` (una sola función que opera sobre todo el dataframe) por un par `fit_author_stats(train_df) -> stats` / `apply_author_stats(df, stats) -> df`. En cada una de las 5 iteraciones de `KFold`, `stats` se calcula solo con las filas de train de esa iteración; las filas de validación (y autores nunca vistos en train) usan esos stats sin verlos directamente. Métricas (MAE/R²) se reportan como media ± desvío estándar entre los 5 folds, no un número único — un solo split (como el actual) no distingue "buen modelo" de "split con suerte".
El modelo que se usa para el reporte SHAP final sigue siendo un fit sobre el 100% de los datos (decisión 2/3 sin cambios) — son dos modelos con propósitos distintos: el CV mide generalización real, el fit completo maximiza señal para la explicación. No se reusa el mismo objeto entrenado para ambos propósitos.
Alternativa descartada: seguir con un solo split 80/20 — ya demostró ser insuficiente para detectar el problema de fuga (recién se vio al tener el dataset completo).

**10. Grid de hiperparámetros del RandomForest, evaluado después del CV fold-safe, no antes.**
`n_estimators`, `max_depth`, `min_samples_leaf` se prueban sobre el mismo esquema de 5-fold fold-safe de la decisión 9, comparando la media de CV entre combinaciones. Tunear hiperparámetros sobre el split actual (con fuga) optimizaría un modelo que hace trampa — el orden importa.

**11. Tier 1 restante (`tiene_signo_pregunta`, `tiene_numero`, `tiene_mayusculas_excesivas`, `num_parrafos`, `tiene_subtitulos`, `tiene_video_embed`) se suman a `FEATURE_COLUMNS`.**
El CV fold-safe confirmó R²≈0.03 con las features actuales — casi sin señal. Estas 6 (ver decisión 9 de `scrape-news-content`) son la extensión barata de parsing de título/cuerpo antes de evaluar `source` como feature o NLP (`tono`). Sin transformación, mismo criterio que el resto de features numéricas/binarias del modelo de árboles.
**Resultado (post-implementación):** no aportó nada — r2_mean idéntico (0.031) antes y después, las 6 features quedaron últimas en la tabla de impacto SHAP. Confirma que el cuello de botella no era "falta esta feature barata en particular".

**12. Modelar granularidad url×source, con `source` como feature, en vez de agregar todas las fuentes en un solo target.**
Evidencia concreta (no solo intuición): separar el target por `source` y recalcular correlaciones mostró patrones más fuertes y a veces **opuestos** por canal — `largo_titulo` correlaciona 0.196 con vistas en Google Discover pero -0.065 en dark social; `num_palabras` correlaciona ~0 mezclado pero ~0.08 en Facebook/dark social. Mezclar los 4 canales en una sola suma promedia señales contradictorias entre sí y las cancela parcialmente. Esto explica en gran parte por qué el R² fold-safe seguía en 0.03 incluso después de sumar 9 features nuevas (decisiones 7, 8, 11): no faltaban features, faltaba dejar de promediar 4 fenómenos distintos en un solo número.
Cambio: el dataset de entrenamiento pasa de "una fila por nota" a "una fila por combinación nota×source" (hasta 4 filas por nota, una por canal donde tuvo tráfico). Target = `log1p(pageViewsTotal sumado para esa combinación url+source)`. `source` se agrega como one-hot (`source_facebook`, `source_google`, `source_google_discover`, `source_dark_social`), dejando que el árbol aprenda interacciones feature×canal (ej. título largo ayuda en Discover, no en dark social) vía sus splits.
`autor_avg_views`/`autor_num_notas` se mantienen calculados a nivel nota (no por combinación nota×source) — evita fragmentar la estadística de autor entre 128 autores x 4 canales, que dejaría muy poca data por celda. Efectos autor×canal quedan como pregunta abierta, no se modelan en esta iteración.
Alternativa descartada: 4 modelos separados (uno por canal) — algunos canales tienen pocas filas (dark social n=669, Discover n=699 en el dataset actual) y entrenar por separado reduce aún más el N disponible para cada uno. Un solo modelo con `source` como feature deja que el árbol aprenda las interacciones específicas de canal sin sacrificar tamaño de muestra total.

**13. El CV fold-safe debe agrupar por `url` (`GroupKFold`), no por fila suelta, para no repetir a nivel nota el mismo tipo de fuga ya corregido a nivel autor.**
Con la granularidad url×source de la decisión 12, la misma nota aparece hasta 4 veces. Si el split de folds fuera sobre filas sueltas, una nota podría tener su fila "Facebook" en train y su fila "Google" en validación dentro del mismo fold — el modelo vería las mismas features estructurales y el mismo autor en ambos lados, la misma clase de fuga que la decisión 9 corrigió para autor, pero ahora a nivel nota. Fix: `GroupKFold` (o `KFold` sobre urls únicas, expandido a filas después) agrupando por `url`, para que todas las filas de una nota queden del mismo lado del split.

**14. Target real `views_7d` desde `data/raw/csv_urls/`, reemplaza el proxy de `ehm_3months_filtered.xlsx`.**
Evidencia: un experimento aislado (mismas features, mismo esquema de CV, mismos hiperparámetros) comparando el proxy actual contra `views_7d` real dio r2_mean 0.098 → **0.480** (subset comparable de ~2,823 notas). Verificado que no es un artefacto: correlación entre el target viejo y el nuevo es 0.45 (moderada, no un duplicado disfrazado), y el ranking de features en la tabla de impacto sigue siendo coherente (autor/canal arriba, igual que antes, sin ninguna feature sospechosa dominando).
`data/raw/csv_urls/` trae granularidad diaria por nota sobre una ventana fija de 90 días (2026-04-13 a 2026-07-11). Para cada nota se calcula `views_7d` = suma de `pageViewsTotal` de los 7 días posteriores a `fecha_publicacion`, solo si esa ventana de 7 días cae completa dentro del rango de 90 días trackeado (si no, no es un `views_7d` real, es una ventana censurada — se excluye en vez de aproximar). Se calcula por combinación (url, source) para el target de entrenamiento (consistente con la granularidad de la decisión 12), y por nota (sumando todos los canales) para `autor_avg_views`/`autor_num_notas` (mismo criterio de la decisión 12: no fragmentar la estadística de autor, pero ahora con una fuente limpia en vez de la ruidosa).
Limpieza de datos necesaria: cada CSV diario trae una fila `"Total"` al final (artefacto de export de Analytics, se filtra); `ehm-90-google-economia.csv` está en el formato viejo (sin columna `date` diaria, con fila `"Total"` propia) y se excluye del cálculo — es redundante con `ehm-90-google-economia_II.csv`, que sí tiene granularidad diaria.
Trade-off aceptado: el dataset de entrenamiento se achica de 3,406 a ~2,823 notas (las que caen dentro de la ventana de 90 días con `views_7d` completamente observable) — se prioriza calidad de target sobre cantidad de filas. `ehm_3months_filtered.xlsx` deja de usarse en este capability (sigue siendo la fuente de `categoria_nota` en `scrape-news-content`, eso no cambia).
Alternativa descartada: mantener el proxy y solo agregar más features — ya se probó (Tier 1, decisión 11) y no alcanzó; el techo real estaba en la calidad del target, no en las features disponibles.

**15. CV temporal (`TimeSeriesSplit` por ventana expansiva) reemplaza `GroupKFold` aleatorio.**
Con target real `views_7d` (decisión 14), medir generalización a notas futuras es más relevante que un split aleatorio del pasado — el uso real del modelo es predecir impacto de una nota ANTES de publicarla o poco después, no interpolar entre notas ya mezcladas en el tiempo. Se ordenan las notas únicas (`url`) por `fecha_publicacion`, se aplica `TimeSeriesSplit(n_splits=5)` sobre esa secuencia de urls (no sobre filas sueltas, mismo cuidado que decisión 13: todas las filas de una nota quedan del mismo lado), y cada fold entrena con notas más viejas, valida con notas más nuevas (ventana expansiva, no rotativa).
Alternativa descartada: mantener `GroupKFold` aleatorio — no distingue si el modelo generaliza hacia el futuro o solo interpola dentro de la misma distribución temporal ya vista.

## Risks / Trade-offs

- [Riesgo] Leakage en `autor_avg_views`: si se calcula sobre el mismo set de train sin protección, el modelo puede sobreajustar a la historia de views del autor. **Mitigación**: calcular con media *leave-one-out* (excluir la nota actual del promedio de su autor) en vez de media global simple.
- [Riesgo] Target proxy (`pageViewsTotal` sumado) mezcla tráfico de fuentes muy distintas (Facebook, Google, Discover, dark social) que no se comportan igual editorialmente. **Mitigación actualizada**: confirmado con evidencia (correlaciones por canal opuestas entre sí) — decisión 12 modela por combinación url×source en vez de sumar todo, en vez de solo documentarlo como limitación conocida.
- [Riesgo] Dataset chico mientras el scraping no termine (ej. cientos de notas en vez de miles) — baseline con alta varianza. **Mitigación**: el script reporta tamaño del dataset usado y métricas de validación; no se oculta la limitación.
- [Riesgo] Sesgo de selección al restringir a notas con `views_7d` completamente observable (decisión 14): se excluyen notas publicadas muy cerca del final de la ventana de 90 días (todavía acumulando) y notas publicadas antes del inicio de la ventana (vida parcial, no hay señal de los primeros días). El subset resultante no es un muestreo aleatorio de todas las notas — podría sesgar hacia cierto rango de fechas de publicación. **Mitigación**: no aplicada todavía; queda como limitación conocida a revisar si el modelo se usa para notas muy recientes o muy viejas específicamente.
- [Trade-off] `RandomForestRegressor` es más simple de explicar y ya trae SHAP soportado nativamente, pero probablemente tenga menor techo de performance que gradient boosting (XGBoost/LightGBM, mencionados en el diccionario). Se documenta como mejora futura, no se agrega una dependencia nueva de ML pesada para un baseline v0.
- [Riesgo] Fuga de autor no detectada hasta correr con el dataset completo: con muestras chicas (658 notas) el problema no era visible porque el número de autores repetidos era menor; con 3,406 notas y 128 autores se hizo evidente. **Mitigación**: decisión 9 (CV fold-safe) — features de autor recalculadas por fold, no sobre el dataset completo.

## Open Questions

- ¿Vale la pena scrapear las ~11,377 URLs nuevas de `data/raw/csv_urls/` con `views_7d` real computable que todavía no están en `notes_structured.parquet` (~4.7hs de scraping)? Expandiría el dataset de ~2,823 a ~14,200 notas con target limpio.
- ¿Se agrega XGBoost/LightGBM como upgrade del baseline una vez validado que el enfoque de features tiene señal?
- ¿Interacción autor×canal (ej. un autor que rinde mejor en Facebook que en Discover)? Fuera de alcance de la decisión 12 — autor se mantiene a nivel nota, no por combinación nota×source.
- ¿Cómo mitigar el sesgo de selección de la decisión 14 (notas muy nuevas/viejas excluidas) si el dataset crece con las URLs nuevas?
