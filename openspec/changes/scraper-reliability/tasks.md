## 1. Índice: conteo de intentos y status `exhausted`

- [x] 1.1 Agregar columna `attempts` a `INDEX_COLUMNS` en `src/shannon_model/scraping/index.py`
- [x] 1.2 `load_index` completa `attempts=0` para índices existentes en disco sin esa columna
- [x] 1.3 `upsert_record` incrementa `attempts` cuando el nuevo registro tiene `status='error'` para una URL que ya existía en el índice
- [x] 1.4 Agregar `max_attempts` como parámetro de `pending_urls()` (o función auxiliar): al alcanzar el máximo, la fila pasa a `status='exhausted'` en vez de `'error'` — implementado como función auxiliar `record_error()` en `index.py`
- [x] 1.5 `pending_urls()` excluye tanto `status='ok'` como `status='exhausted'`

## 2. Rate limiting thread-safe

- [x] 2.1 Agregar `threading.Lock` interno a `RateLimiter` en `src/shannon_model/scraping/fetch.py`, protegiendo lectura/escritura de `_last_start` en `wait()`

## 3. Concurrencia en el pipeline

- [x] 3.1 Agregar parámetro `workers: int = 1` a `ScrapeConfig` en `src/shannon_model/scraping/pipeline.py`
- [x] 3.2 Paralelizar `run_scrape` con `concurrent.futures.ThreadPoolExecutor(max_workers=config.workers)`: cada worker llama `fetch_html` + `extract_note_fields` para una URL y devuelve el resultado (sin escribir a disco directamente)
- [x] 3.3 El hilo coordinador consume resultados vía `as_completed`, actualiza `index_df`/`structured_df` y llama `save_index`/`save_structured` de forma serializada (un solo punto de escritura)
- [x] 3.4 Con `workers=1`, el comportamiento observable es idéntico al actual (secuencial) — usar como caso de regresión

## 4. CLI

- [x] 4.1 Agregar flags `--max-attempts` (default 3) y `--workers` (default 2) a `scripts/scrape_news.py`
- [x] 4.2 Pasar ambos valores a `ScrapeConfig`

## 5. Verificación

- [x] 5.1 Test manual: forzar una URL a fallar 3 veces (ej. URL inválida a propósito) y confirmar que queda `status='exhausted'` y ya no aparece en `pending_urls()` en la corrida siguiente — verificado: 3 corridas seguidas contra URL 404 real dejaron `status=exhausted, attempts=3`; 4ta corrida `processed=0`
- [x] 5.2 Test manual: correr con URLs reales y confirmar que el índice resultante tiene filas consistentes (sin duplicados ni filas a medio escribir) — verificado con `--limit 8 --workers 4`: 8 filas, 0 duplicados en índice y en `structured.parquet`
- [x] 5.3 Comparar tiempo de corrida `--workers 1` vs `--workers 4` sobre el mismo lote de URLs y confirmar reducción de tiempo total — verificado: `--workers 1` ~1.1 it/s vs `--workers 4` ~3.1 it/s sobre el mismo lote de 8 URLs (delay=1.0s)
- [x] 5.4 `openspec validate --all` pasa sin errores
