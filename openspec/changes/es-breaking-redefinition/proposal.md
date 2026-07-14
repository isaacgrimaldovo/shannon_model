## Why

El diccionario de datos de Shannon define `es_breaking` como `zscore_views_1h > 2.0`, pero el compañero confirmó (notebook `Shannon_EDA_y_Scraping_3.ipynb`, sección 11) que `views_1h`/`zscore_views_1h` se eliminaron del diccionario — consistente con que la fuente de analytics (reportes Marfeel/Google Analytics export usado hoy) trae granularidad diaria, no horaria. Sin reemplazo, `es_breaking` queda indefinido y bloquea cualquier feature o filtro que dependa de él en `views-impact-model`.

## What Changes

- Redefinir `es_breaking` usando granularidad diaria: `zscore_views_dia1 > 2.0` (z-score de las vistas del día 1 posterior a publicación, calculado sobre la distribución de vistas día-1 de todas las notas), en vez de `zscore_views_1h`.
- Documentar explícitamente que `views_1h`/`zscore_views_1h` no existen como columnas y no se calculan con la fuente de datos actual.
- Dejar constancia de la alternativa evaluada y descartada por ahora: integrar Google Analytics en tiempo real (API) para recuperar granularidad horaria — fuera de alcance de esta iteración.
- **BREAKING** (a nivel de spec, no de código en producción): cualquier definición previa de `es_breaking` basada en `views_1h` queda obsoleta; no hay código existente que la implemente todavía, así que no hay migración de datos.

## Capabilities

### New Capabilities
(ninguna)

### Modified Capabilities
- `views-impact-model`: agrega definición de `es_breaking` (feature derivada, granularidad día-1) como requisito nuevo dentro de esta capability, resolviendo el non-goal pendiente documentado en `predict-views-impact/design.md`.

## Impact

- Documentación/specs: actualiza el entendimiento de `views-impact-model` respecto a `es_breaking`.
- Código: si se decide incluir `es_breaking` como feature del modelo baseline, afecta `src/shannon_model/impact_model/dataset.py` (cálculo de `zscore_views_dia1`) — a definir en tasks si el equipo quiere incorporarlo ya al modelo o solo dejar la definición documentada para una iteración posterior.
- Sin impacto en `scrape-news-content` ni en el motor de scraping.
