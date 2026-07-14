## Context

El modelo A (`predict-views-impact`, ya completo) entrena `RandomForestRegressor` sobre un dataset nota×source con ~30 features, incluyendo `autor_avg_views`/`autor_num_notas`/`source_*`. `category-impact-breakdown` (recién hecho) mostró que esas features de autor/canal concentran casi todo el peso SHAP en las 6 categorías — ninguna feature de contenido (título, cuerpo, imágenes, estructura) entra al top 3 de ninguna. Hipótesis de trabajo: masking, no ausencia de señal — el árbol prioriza autor/canal (señal más limpia y fuerte) y deja poco residuo de varianza para que el contenido lo explique, incluso si el contenido tiene algo de efecto real.

`feature_kinds.py` (ya existe, de `section-editorial-opportunities`) ya clasifica qué features son `actionable` (13: `num_palabras`, `num_letras`, `largo_titulo`, `num_imagenes_real`, `num_etiquetas`, `num_parrafos`, `tiene_signo_pregunta`, `tiene_numero`, `tiene_mayusculas_excesivas`, `tiene_subtitulos`, `tiene_video_embed`, `es_fin_de_semana`, `hora_del_dia`) vs `diagnostic` (`autor_*`, `source`). Este change reusa esa clasificación tal cual, no inventa una lista paralela.

`dataset.py::load_real_views_targets` ya calcula, en la misma pasada que arma el target nota×source del modelo A, un target a nivel **nota** (`by_note`, `views_7d` sumado entre canales, usado hoy solo para `fit_author_stats`). Ese mismo valor es exactamente el target que necesita el modelo B — no hace falta un cálculo nuevo, solo exponerlo como dataset de entrenamiento en vez de usarlo solo como insumo interno de las estadísticas de autor.

## Goals / Non-Goals

**Goals:**
- Aislar la señal de contenido del efecto de autor/canal, entrenando un modelo sin esas features.
- Confirmar o descartar la hipótesis de masking: si el modelo B muestra SHAP con más peso en features de contenido que el modelo A, confirma masking; si sigue casi plano, el problema es falta de señal real en las features actuales (empuja a Tier 2 NLP, no a este approach).
- Reusar al máximo infraestructura ya existente (`feature_kinds.ACTIONABLE_FEATURES`, `load_real_views_targets`, `build_impact_table`/`build_impact_table_by_category`).

**Non-Goals:**
- No se construye todavía el entrypoint de scoring de una nota nueva (extracción de features de texto plano + contrafactual) — ese es un change posterior que consume el modelo B ya entrenado.
- No se residualiza el target por autor/canal (alternativa más rigurosa, mencionada en la exploración) — se opta por la versión más simple (excluir esas columnas) primero; residualizar queda como mejora futura si excluir no alcanza.
- No se reemplaza ni se deprecia el modelo A — conviven, cada uno con su propósito (A: mejor predicción posible + reporte general; B: señal de contenido aislada para recomendaciones).
- No se modela por categoría por separado (6 modelos) — se mantiene un solo modelo B con `categoria_nota` one-hot como feature de contexto, igual que hace el modelo A; separar por categoría queda como pregunta abierta si el desglose por categoría del modelo B muestra necesidad real.

## Decisions

**1. Dataset a nivel nota, reusando `by_note` de `load_real_views_targets` en vez de fragmentar por canal.**
Sin `source` como feature, tener varias filas por nota (una por canal) no aporta información nueva al modelo B — serían filas casi idénticas en features con distinto target, puro ruido. Se usa el target ya calculado a nivel nota (`by_note`, log1p de `views_7d` sumado entre canales) como target único por URL.
Alternativa descartada: mantener granularidad nota×source y solo quitar `source` de las features — dejaría filas duplicadas en features con targets distintos, degradando el modelo sin necesidad.

**2. Reusar `feature_kinds.ACTIONABLE_FEATURES` como lista de features del modelo B, sin crear una lista paralela.**
Ya es la clasificación canónica que usa `editorial_ops` para decidir qué entra a la receta editorial. Evita que compañero y este change mantengan dos taxonomías de "qué es contenido accionable" que puedan divergir con el tiempo.
Nota: `ACTIONABLE_FEATURES` usa `hora_del_dia` (columna cruda), no la codificación cíclica (`hora_sin`/`hora_cos`) que usa el modelo A — se sigue el criterio de `feature_kinds.py` tal cual, no se fuerza la codificación cíclica del modelo A sobre esta lista.

**3. `categoria_nota` se mantiene como feature (one-hot), un solo modelo B (no 6 modelos por categoría).**
Mismo criterio que el modelo A: una categoría chica (`tendencias`, ~250 notas a nivel nota×source, menos aún a nivel nota) tendría muy poca data para un modelo separado. Se deja como pregunta abierta si el desglose por categoría (reusando `build_impact_table_by_category`) muestra que vale la pena separar.

**4. CV: `TimeSeriesSplit` sobre notas ordenadas por fecha, sin `fit_author_stats`/`apply_author_stats`.**
El modelo A necesita esa lógica porque `autor_avg_views` se recalcula por fold para evitar fuga (decisión 9 de `predict-views-impact`). El modelo B no tiene esa feature, así que esa complejidad no aplica — el CV se simplifica a entrenar/evaluar directo por fold, manteniendo el mismo esquema temporal (evitar look-ahead) por consistencia con el modelo A.
Alternativa descartada: reusar `cross_validate()` de `cv.py` tal cual (que sí llama `fit_author_stats`) — fallaría o sería trabajo muerto sin la columna de autor; se justifica una función separada, más simple.

**5. Reusar `build_impact_table`/`build_impact_table_by_category` sin cambios.**
Ambas funciones ya son genéricas (reciben modelo + `x_train` + columnas de categoría) — no hace falta ninguna modificación para que funcionen sobre el modelo B, solo llamarlas con el modelo/dataset correctos.

**6. Grid de hiperparámetros propio para el modelo B, en la misma config (`views_impact.yaml`).**
El modelo B tiene menos features y dataset más chico (nivel nota, no nota×source) — puede necesitar un grid distinto (ej. `max_depth`/`min_samples_leaf` más conservador para no sobreajustar con menos filas). Se agrega como sección nueva en el mismo YAML en vez de un archivo separado, para no fragmentar la configuración de algo que se corre junto.

## Risks / Trade-offs

- [Riesgo] Si el modelo B sigue mostrando SHAP casi plano en features de contenido, confirma que el problema es falta de señal real (no masking) — empujaría a Tier 2 NLP antes de invertir más en este modelo. Se documenta como resultado esperado a reportar, no como fallo del change.
- [Trade-off] Dataset a nivel nota es más chico que nota×source (menos filas para entrenar) — aceptable porque sin `source` como feature, más filas por canal no aportarían señal nueva, solo ruido.
- [Riesgo] `categoria_nota` sigue siendo la única "agrupación" en el modelo B — si el efecto de contenido varía fuerte por categoría (como ya se vio con `autor_num_notas` en `category-impact-breakdown`), un solo modelo B podría seguir promediando señales opuestas entre secciones. Mitigación parcial: el desglose por categoría (`build_impact_table_by_category`) permite ver esto sin necesidad de separar el modelo todavía.

## Open Questions

- Si el modelo B confirma masking (SHAP de contenido sube claramente respecto al modelo A) pero sigue siendo débil en términos absolutos, ¿vale la pena residualizar por autor/canal en vez de solo excluir esas columnas? Se deja para una iteración futura si hace falta.
- ¿El scoring de una nota nueva (siguiente change) debería usar el modelo A, el modelo B, o ambos combinados (ej. modelo B para "qué cambiar", modelo A para "vistas totales esperadas incluyendo quién firma y por qué canal")? Se resuelve cuando se proponga ese change, con los resultados de este ya disponibles.
