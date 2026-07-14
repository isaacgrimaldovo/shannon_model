## Why

Con base en las **views** de las notas, Shannon debe identificar **patrones** de cómo las características editoriales se asocian a más o menos vistas, traducirlos a una **receta** accionable por sección, y después medir **cuántas de las notas actuales cumplen esa receta**.

Eso es mejora continua de contenido — no atribución de tráfico. El dashboard (filtro por sección, % por sección tipo 71% Deportes, Índice Shannon, Mayor oportunidad) encaja con: *receta aprendida → cumplimiento → gap = oportunidad*.

El change `predict-views-impact` aporta el motor (dataset, modelo, SHAP), pero su salida priorizó autor/canal. Falta la capa de producto: **receta → compliance → tip**.

## What Changes

- Nueva capability `section-editorial-opportunities` con pipeline en dos tiempos:
  1. **Calcular la receta** del scope (patrones de features accionables ligados a mayor views).
  2. **Medir cumplimiento**: % (y conteo) de notas actuales del scope que cumplen la receta.
- Emisión de KPIs dashboard: cumplimiento / Índice Shannon (alineado a receta+compliance), views de sección, **Mayor oportunidad** = regla de la receta con mayor gap de cumplimiento × impacto en views.
- Solo features **accionables** en la receta y en el tip (horario, título/forma, imágenes, estructura…). Autor y canal quedan fuera de la receta de tip (diagnóstico opcional).
- Reutiliza `views-impact-model` + scraping/analytics; no archiva `predict-views-impact`.
- Target preferido: `views_7d` desde `csv_urls` (prerrequisito de cableado documentado).

## Capabilities

### New Capabilities
- `section-editorial-opportunities`: receta editorial por sección + compliance de notas actuales + Mayor oportunidad / KPIs.

### Modified Capabilities
- `views-impact-model` (mínimo): inventario `actionable` vs `diagnostic` consumible por la capa de receta.

## Impact

- Código nuevo: módulo (ej. `editorial_ops/`) + CLI + YAML + artefactos en `checkpoints/` (gitignored).
- Consume features estructuradas + target de views (+ opcional modelo/SHAP del engine).
- Sin UI del dashboard, sin NLP v0, sin API online, sin tips de autor/canal.
- “Notas” (= piezas publicadas del scope); no “botas”.
