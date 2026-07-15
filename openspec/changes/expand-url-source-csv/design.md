## Context

`scripts/scrape_news.py` toma su lista de URLs a scrapear desde `data/raw/ehm_3months_filtered.xlsx` vía `load_url_folder_map(urls_xlsx)` (`src/shannon_model/scraping/pipeline.py:74`): un `dict[url, folder]` construido con `pd.read_excel(usecols=["url", "folder"])`. Esa lista tiene 3,408 URLs únicas en 6 categorías.

`data/raw/csv_urls/` (29 archivos, mismo esquema `url,folder,source,publishDate,publishTime,date,pageViewsTotal`) ya es la fuente del target real `views_7d` en `predict-views-impact` (decisión 14), vía `src/shannon_model/impact_model/dataset.py::_load_daily_views` (líneas 45-59). Esa función ya resuelve:
- exclusión de la fila `"Total"` (artefacto de export)
- exclusión de `ehm-90-google-economia.csv` (formato viejo, sin `date` diaria — redundante con `ehm-90-google-economia_II.csv`)
- exclusión de `ehm_report-*.csv` (duplicado del proxy viejo, ventana de fechas distinta)

Pero `_load_daily_views` lee daily analytics para calcular views, no construye un mapa `url -> folder` deduplicado para descubrimiento de URLs. Este change necesita una función nueva y más chica, no puede reusar `_load_daily_views` tal cual (esa carga `usecols=["url","source","publishDate","date","pageViewsTotal"]`, sin necesidad de leer todas las filas por fecha para el propósito de este change).

`csv_urls` trae 9 categorías (`folder`) — 3 más que el xlsx (`deportes`, `edicion-impresa`, `tecnologia`).

## Goals / Non-Goals

**Goals:**
- Nuevo loader que produce `dict[url, folder]` deduplicado desde `data/raw/csv_urls/`, con el mismo criterio de exclusión de archivos ya validado en `dataset.py`.
- `ScrapeConfig`/`scripts/scrape_news.py` usan este loader como fuente real por default.
- Falla explícita (no silenciosa) si una URL tiene `folder` inconsistente entre archivos.

**Non-Goals:**
- Correr el scraping de las ~11,377 URLs nuevas (queda como task/decisión posterior — el índice `data/raw/scrape_index.csv` simplemente tendrá más candidatas `pending`, la corrida real es aparte).
- Tocar `dataset.py` / `views_impact` (ya usa `csv_urls` correctamente, sin cambios).
- Actualizar `docs/COLAB.md`, `notebooks/colab_pipeline.ipynb`, `scripts/data_quality_report.py`.
- Deprecar o borrar `data/raw/ehm_3months_filtered.xlsx` del repo — sigue existiendo como archivo, solo deja de ser el input activo del scraper.
- Extraer una función 100% compartida entre `dataset.py` y el nuevo loader — se duplica el criterio de exclusión de archivos (lista corta y estable, ver decisión 3) en vez de crear un acoplamiento nuevo entre `impact_model` y `scraping`.

## Decisions

**1. Nuevo loader `load_url_folder_map_from_csv_urls(csv_urls_dir)` en `src/shannon_model/scraping/pipeline.py`, no reemplaza `load_url_folder_map(urls_xlsx)`.**
Se agrega la función nueva y `ScrapeConfig`/`scripts/scrape_news.py` la usan por default. `load_url_folder_map(urls_xlsx)` se mantiene sin tocar (permite pasar explícito `--urls-xlsx` si hace falta reprocesar/comparar contra el snapshot viejo), pero deja de ser el default.
Alternativa descartada: modificar `load_url_folder_map` para aceptar xlsx o directorio de CSVs con branching interno — mezcla dos formatos de entrada muy distintos (un excel vs un glob de CSVs) en una sola función, complica el tipo de retorno y los tests.

**2. Deduplicación: `groupby("url")["folder"].agg` con validación de consistencia, no `drop_duplicates` simple.**
`drop_duplicates(subset="url")` tomaría el primer valor de `folder` visto y ocultaría una inconsistencia real si existiera. En cambio: agrupar por `url`, tomar el set de valores únicos de `folder` por URL, y si algún grupo tiene más de un valor, lanzar error con la URL y los valores en conflicto — mismo principio que decisión 4 de `scrape-news-content` (errores trazables, no aproximados).
Alternativa descartada: tomar el primer valor y loguear un warning — un folder incorrecto para `categoria_nota` es silencioso (no rompe el scraping, pero contamina una feature del dataset de entrenamiento sin que nadie lo note).

**3. Reusar la lista de exclusión de archivos (`"Total"`, `ehm-90-google-economia.csv`, `ehm_report-*.csv`) por duplicación explícita, no por import cruzado entre `impact_model` y `scraping`.**
Ambos módulos (`dataset.py` y el nuevo loader) leen el mismo directorio `csv_urls` pero con propósitos distintos (target de vistas vs descubrimiento de URLs) y viven en capabilities distintas (`predict-views-impact` / `news-scraping`). Duplicar 3 nombres de archivo hardcodeados es más barato que crear un módulo `shared`/dependencia entre `impact_model` y `scraping` para 3 líneas de exclusión que rara vez cambian.
Alternativa descartada: extraer `EXCLUDED_CSV_FILES` a un módulo compartido (ej. `src/shannon_model/data_sources.py`) — sobre-ingeniería para una lista de 3 nombres que hoy solo cambiaría si aparecen más archivos de export "raros", caso que ya se maneja igual (falla/exclusión explícita) en ambos lugares.

**4. `--urls-xlsx` de `scripts/scrape_news.py` se renombra conceptualmente pero el flag CLI se mantiene por compatibilidad, apuntando ahora a un directorio.**
Para minimizar el diff en `scripts/scrape_news.py` y `ScrapeConfig`, se reusa el mismo flag (ahora recibe un path de directorio en vez de un archivo xlsx) en vez de introducir un flag nuevo (`--urls-csv-dir`) y mantener dos flags simultáneos. El default cambia de `data/raw/ehm_3months_filtered.xlsx` a `data/raw/csv_urls`.
Alternativa descartada: agregar un flag nuevo `--urls-source-dir` y dejar `--urls-xlsx` deprecado — dos flags para una sola responsabilidad (fuente de URLs) es confuso sin necesidad real de mantener ambos simultáneamente (nadie corre el scraper con las dos fuentes a la vez).

## Risks / Trade-offs

- [Riesgo] Inconsistencia de `folder` entre archivos de `csv_urls` para la misma URL, si el export de Analytics tiene URLs re-categorizadas entre corridas. **Mitigación**: decisión 2 — falla explícita en vez de tomar un valor arbitrario.
- [Riesgo] Cambiar el default de `--urls-xlsx` es un cambio breaking para cualquier invocación existente que dependía del comportamiento implícito (xlsx). **Mitigación**: el flag sigue existiendo, solo cambia qué recibe por default; documentado como **BREAKING** en el proposal.
- [Trade-off] Duplicar el criterio de exclusión de archivos entre `dataset.py` y el nuevo loader (decisión 3) — riesgo de que diverjan si cambia el criterio en un solo lugar. Aceptado por ser 3 líneas estables; revisar si en el futuro aparece un tercer consumidor del mismo directorio (ahí sí valdría extraer a un módulo compartido).
- [Riesgo] El volumen de URLs candidatas sube de 3,408 a ~14,200 — el índice de scraping (`data/raw/scrape_index.csv`) y el HTML descargado (`data/raw/html/`) pueden crecer ~4x en disco cuando eventualmente se corra el scraping completo (fuera de alcance de este change, pero afecta el dimensionamiento futuro).

## Open Questions

- ¿Cuándo se corre el scraping del resto de URLs nuevas? **Corrección post-implementación**: el total real de URLs únicas descubribles en `csv_urls` es 53,220 (9 categorías), no ~14,200 — ese número era el subset de `predict-views-impact` con `views_7d` completamente observable (una ventana temporal, no el total de URLs). Con 3,414 ya scrapeadas (incluyendo 5 de esta verificación), quedan ~49,800 candidatas pendientes — el estimado de ~4.7hs de `predict-views-impact` queda obsoleto y debe recalcularse sobre el volumen real antes de decidir si se corre completo. Queda pendiente, no bloquea este change.
- ¿Vale la pena extraer la lista de exclusión de archivos a un módulo compartido si en el futuro un tercer consumidor lee `csv_urls` (ej. un reporte de calidad de datos)? No se resuelve acá (ver decisión 3).
