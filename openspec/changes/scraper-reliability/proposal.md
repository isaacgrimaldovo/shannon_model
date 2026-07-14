## Why

`scrape-news-content` ya está implementado y completo, pero un compañero trabajando en paralelo en un notebook (sin ver este código) reimplementó su propio motor de scraping y en el camino resolvió dos problemas reales que el motor actual no tiene: reintentos sin límite en URLs muertas y ejecución estrictamente secuencial. Conviene llevar esas dos mejoras al motor ya existente antes de correr el scraper contra el dataset completo, en vez de dejar que el notebook paralelo siga siendo la única implementación con esas capacidades.

## What Changes

- `pending_urls()` deja de considerar pendiente para siempre una URL en `status='error'`: se agrega conteo de intentos al índice y, tras un máximo configurable, la URL pasa a `status='exhausted'` y no se vuelve a intentar.
- `run_scrape` deja de ser estrictamente secuencial: se agrega un pool de workers configurable (concurrencia baja, 2-6) que respeta el mismo rate limiting por request, en vez de un único hilo con `RateLimiter` global.
- El índice (`data/raw/scrape_index.csv`) gana una columna nueva (`attempts`) — cambio de esquema aditivo, no rompe filas existentes con status `ok`/`error` sin esa columna (se asume `attempts=0` si falta).
- Sin cambios en la extracción (`extract.py`), el formato del dataset estructurado (`notes_structured.parquet`) ni el CLI existente (`scripts/scrape_news.py`) más allá de nuevos flags opcionales (ej. `--max-attempts`, `--workers`).

## Capabilities

### New Capabilities
(ninguna)

### Modified Capabilities
- `news-scraping`: agrega comportamiento de descarte permanente tras N reintentos fallidos y ejecución concurrente (worker pool) manteniendo el mismo rate limiting por request.

## Impact

- Código: `src/shannon_model/scraping/index.py` (columna `attempts`, nuevo status `exhausted`, lógica de `pending_urls`), `src/shannon_model/scraping/fetch.py` (sin cambios de contrato, se reutiliza tal cual por cada worker), `src/shannon_model/scraping/pipeline.py` (paralelizar `run_scrape`).
- CLI: `scripts/scrape_news.py` gana flags opcionales, con defaults que preservan el comportamiento actual si no se usan.
- Datos: `data/raw/scrape_index.csv` cambia de esquema (columna nueva) — no versionado en git (`data/raw/*` en `.gitignore`), sin migración necesaria en producción.
- Sin impacto en `predict-views-impact`/`impact_model/` (consumen `notes_structured.parquet`, que no cambia de formato).
