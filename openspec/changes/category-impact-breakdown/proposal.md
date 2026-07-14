## Why

`build_impact_table()` (`impact_model/explain.py`) hoy calcula un único SHAP promedio por feature, mezclando todas las notas sin importar `categoria_nota`. Decisión 12 de `predict-views-impact/design.md` ya probó, para `source` (canal), que mezclar fenómenos distintos en un solo número esconde correlaciones opuestas entre sí (`largo_titulo` +0.196 en Discover vs -0.065 en dark social). `categoria_nota` (nacional/economía/espectáculos/etc.) nunca recibió ese mismo chequeo — puede tener el mismo problema (ej. título largo ayuda en `economia` pero no en `espectaculos`) sin que hoy se vea, porque el reporte lo promedia todo junto.

## What Changes

- Nueva función que calcula la tabla de impacto SHAP **por separado para cada `categoria_nota`**, reusando el mismo modelo final ya entrenado (sin reentrenar, sin cambiar el dataset ni su granularidad nota×source).
- El pipeline de entrenamiento (`run_pipeline`) persiste un artefacto adicional (`feature_impact_by_category.csv`) junto al `feature_impact.csv` global existente — el reporte global no se modifica ni se reemplaza.
- Sin cambios al modelo, al target, al CV fold-safe ni al dataset de entrenamiento — esto es una vista adicional sobre el mismo modelo/SHAP ya calculado.

## Capabilities

### New Capabilities
(ninguna)

### Modified Capabilities
- `views-impact-model`: agrega reporte de impacto de features desglosado por `categoria_nota`, además del reporte global existente.

## Impact

- Código: `src/shannon_model/impact_model/explain.py` (nueva función), `src/shannon_model/impact_model/pipeline.py` (persistir artefacto nuevo), `scripts/train_views_model.py` (mostrar resumen del desglose).
- Sin dependencias nuevas (reusa `shap`, ya presente).
- Datos: nuevo artefacto `checkpoints/views_impact/feature_impact_by_category.csv`, mismo directorio ya excluido de git.
- Sin impacto en `scrape-news-content` ni en `scraper-reliability`/`data-quality-eda`.
