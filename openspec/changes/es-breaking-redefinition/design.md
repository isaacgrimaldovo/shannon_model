## Context

El diccionario de datos original define `es_breaking = zscore_views_1h > 2.0`. `predict-views-impact/design.md` ya documentaba esto como no calculable ("Analytics API a la hora 1 de publicación", Tier 3 del backlog) pero lo dejaba como pendiente sin resolver, no como definitivamente descartado. El notebook del compañero confirma algo más fuerte: `views_1h`/`zscore_views_1h` se **eliminaron del diccionario de datos**, no solo "no calculables por ahora" — la fuente de analytics (reportes Marfeel / export usado hoy) es diaria, no horaria, así que ni siquiera con Analytics API estándar se recuperaría esa granularidad sin cambiar de fuente.

`data/raw/csv_urls/` (mencionado en open question de `predict-views-impact/design.md`) ya trae granularidad diaria y permite calcular `views_7d` real — la misma fuente sirve para calcular vistas del día 1 específicamente.

## Goals / Non-Goals

**Goals:**
- Dar una definición operacional de `es_breaking` que sea calculable con la granularidad de datos real disponible hoy (diaria).
- Dejar documentado, sin ambigüedad, que `views_1h`/`zscore_views_1h` no se usan ni se reintroducen mientras la fuente de datos sea diaria.

**Non-Goals:**
- No se integra Google Analytics en tiempo real ni ninguna API nueva para recuperar granularidad horaria — evaluado y descartado para esta iteración (el notebook lo deja como pregunta abierta, no como decisión tomada).
- No se decide en este change si `es_breaking` se incorpora ya como feature del modelo baseline (`impact_model/dataset.py`) — esta iteración solo fija la definición; incorporarla al modelo es una decisión de scope separada (ver Open Questions).
- No se recalculan métricas ya reportadas de `predict-views-impact` (esa capability no usa `es_breaking` hoy).

## Decisions

**1. `zscore_views_dia1` en vez de `zscore_views_1h`, manteniendo el mismo umbral (2.0).**
El notebook propone esta alternativa directamente. Se mantiene el umbral `> 2.0` del diccionario original — cambia la ventana temporal (día 1 en vez de hora 1), no el criterio estadístico. Alternativa descartada: bajar el umbral para compensar que un día acumula más vistas que una hora — el z-score ya normaliza por la distribución de esa misma métrica (día-1) entre notas, no hace falta ajustar el número solo por cambiar la ventana.

**2. Notas sin ventana día-1 completa quedan con `es_breaking` no calculable, no `False`.**
Igual criterio que otras features derivadas de ventanas temporales incompletas en el diccionario (evita que "no tengo dato" se confunda con "confirmado que no es breaking"). Consistente con el patrón ya usado en `predict-views-impact` para `views_7d` (notas sin ventana completa se excluyen, no se rellenan con 0/False).

**3. Calculable desde `data/raw/csv_urls/`, misma fuente que `views_7d` real.**
No se introduce una fuente de datos nueva — se reutiliza la granularidad diaria ya identificada como disponible para `views_7d` (ver open question de `predict-views-impact/design.md`), tomando solo el primer día de esa serie en vez de sumar 7.

## Risks / Trade-offs

- [Riesgo] Un z-score de vistas día-1 puede marcar como "breaking" notas que simplemente tuvieron una promoción fuerte (paid/push), no necesariamente noticia de último momento — mismo riesgo conceptual que ya tenía la definición original por hora, solo que a otra escala temporal. **Mitigación**: ninguna nueva; se documenta como limitación conocida heredada del diccionario original.
- [Trade-off] Cambiar la ventana de hora a día hace que `es_breaking` capture "tuvo un día fuerte" en vez de "explotó en la primera hora" — son conceptos distintos aunque compartan nombre. Se documenta explícitamente en la spec para que quien use la feature entienda la diferencia frente al diccionario original.

## Open Questions

- ¿Se incorpora `es_breaking` (día-1) como feature real del modelo baseline en esta iteración, o queda solo documentado como definición hasta una iteración posterior que sí la implemente en `impact_model/dataset.py`? A resolver en tasks.md según lo que decida el equipo.
- ¿Vale la pena, más adelante, revisar si Google Analytics en tiempo real (API) es una fuente viable para recuperar granularidad horaria real y descartar `zscore_views_dia1` por el `zscore_views_1h` original? Queda abierto, no bloquea esta definición.
