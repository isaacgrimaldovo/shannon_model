## Context

`build_impact_table()` (`impact_model/explain.py:11`) corre `shap.TreeExplainer(model).shap_values(x_train)` una vez sobre todo `x_train` y promedia `mean_abs_shap`/`views_multiplier` por feature a través de TODAS las filas (todas las categorías mezcladas). `x_train` es el `training_frame` de `dataset.py`, una fila por combinación nota×source, con `categoria_nota` ya one-hot (`categoria_nacional`, `categoria_economia`, etc., ver `build_base_frame`).

Decisión 12 de `predict-views-impact/design.md` mostró, con evidencia concreta, que mezclar `source` en un solo target escondía correlaciones opuestas por canal — motivó modelar url×source explícitamente. El mismo riesgo conceptual aplica a `categoria_nota`: nunca se verificó si el impacto de, por ejemplo, `largo_titulo` o `num_palabras` es distinto (o incluso opuesto) entre secciones.

## Goals / Non-Goals

**Goals:**
- Calcular el impacto SHAP por feature desglosado por `categoria_nota`, usando el modelo final ya entrenado (mismo objeto, sin reentrenar).
- Persistir el desglose sin tocar ni reemplazar el reporte global existente.

**Non-Goals:**
- No se reentrena un modelo por categoría — sería un cambio de arquitectura mayor (7 modelos en vez de 1) y no es lo que se pidió; se reusa el mismo modelo y se recalculan/filtran los valores SHAP ya explicables por él.
- No se decide todavía si hace falta actuar sobre lo que el desglose muestre (ej. features distintas por sección) — eso es una decisión posterior del equipo, esta iteración solo genera el reporte.
- No cambia el dataset, el target, el CV fold-safe ni el grid de hiperparámetros de `predict-views-impact`.

## Decisions

**1. Filtrar `x_train` por columna one-hot de categoría, no recalcular SHAP desde cero por categoría.**
`shap.TreeExplainer(model).shap_values(x_train)` ya se puede llamar una sola vez sobre todo `x_train` (barato con `TreeExplainer`, exacto y rápido para árboles). Se calculan los SHAP values una única vez sobre el dataset completo, y luego se agrupan las filas por qué columna `categoria_*` tiene valor 1, promediando `mean_abs_shap`/`views_multiplier` dentro de cada grupo. Evita llamar `TreeExplainer` N veces (una por categoría) de forma redundante.
Alternativa descartada: correr `explainer.shap_values(x_train_categoria)` por separado para cada subconjunto — mismo resultado final, pero recalcula sobre datos que ya se explicaron en la corrida global; más lento sin necesidad.

**2. Nueva función `build_impact_table_by_category`, no modificar `build_impact_table`.**
Función separada en `explain.py` que recibe el modelo, `x_train` y la lista de columnas one-hot de categoría (`categoria_*`), y devuelve un DataFrame con columnas `categoria`, `feature`, `mean_abs_shap`, `views_multiplier`. `build_impact_table` (global) queda intacta — ambas conviven, se llaman ambas desde `run_pipeline`.

**3. Categorías con pocas filas se reportan igual, sin umbral mínimo.**
No se excluye ninguna categoría por tener pocas notas — el diccionario de datos no define un mínimo, y ocultar categorías chicas escondería justamente el tipo de sección que más se beneficiaría de saber qué feature le importa. Se deja como nota en el reporte (no como filtro) que categorías con pocas filas tienen más varianza esperada.

**4. Artefacto nuevo `feature_impact_by_category.csv`, mismo directorio que el resto.**
Se persiste junto a `model.joblib` y `feature_impact.csv` en `config.output_dir` (`checkpoints/views_impact/`), ya excluido de git. No requiere nuevo patrón de `.gitignore`.

## Risks / Trade-offs

- [Riesgo] Categorías con pocas notas (ej. `tendencias`, 110 notas en el xlsx actual) dan SHAP con alta varianza, potencialmente ruidoso → **Mitigación**: se documenta como limitación conocida en el output del script (tamaño de muestra por categoría se reporta junto a la tabla), no se oculta ni se filtra.
- [Trade-off] Reusar el mismo modelo global (entrenado con todas las categorías mezcladas) para el desglose por categoría, en vez de un modelo por categoría, significa que el desglose muestra "qué aprendió el modelo global sobre esta categoría", no "el mejor modelo posible para esta categoría sola". Suficiente para el objetivo (ver si hay señales opuestas por sección, como se hizo con `source`), no para optimizar por categoría — eso sería una iteración futura si el desglose muestra necesidad real.

## Open Questions

- Si el desglose muestra features con impacto opuesto entre categorías (mismo patrón que se vio con `source`), ¿vale la pena modelar por categoría de forma explícita (ej. `categoria_nota` × feature como interacción forzada, o modelos separados)? Se deja para una iteración futura basada en lo que el reporte muestre.
