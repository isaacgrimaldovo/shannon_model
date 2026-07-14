## Context

`scrape-news-content` ya está implementado en `src/shannon_model/scraping/` (`index.py`, `fetch.py`, `pipeline.py`, `extract.py`) con un motor secuencial: un `requests.Session`, un `RateLimiter` que espera `delay` segundos entre requests, y un índice CSV (`data/raw/scrape_index.csv`) con columnas `url, nota_id, status, http_status, error_msg, scraped_at, html_path`. `pending_urls()` (`index.py:51-54`) filtra únicamente por `status != 'ok'`, sin ningún límite de reintentos.

Un compañero, en paralelo y sin ver este código, reimplementó su propio scraper en un notebook (`Shannon_EDA_y_Scraping_3.ipynb`) con dos capacidades que el motor actual no tiene: descarte permanente de URLs tras N intentos fallidos, y concurrencia vía thread pool. Este change lleva esas dos capacidades al motor ya existente, sin adoptar el resto de la implementación del notebook (que usa jsonl en vez de CSV+parquet, y no tiene idempotencia por hash de URL).

## Goals / Non-Goals

**Goals:**
- Evitar que URLs con fallo permanente (404, dominio caído, sin JSON-LD) se reintenten en cada corrida indefinidamente.
- Reducir el tiempo total de una corrida completa (3,408 URLs) paralelizando el fetch, sin violar el rate limiting acordado por request.
- Mantener compatibilidad con índices existentes generados por el motor actual (sin columna `attempts`).

**Non-Goals:**
- No se cambia el formato de `notes_structured.parquet` ni la lógica de extracción (`extract.py`).
- No se reemplaza CSV+parquet por jsonl ni se adopta ninguna otra decisión de arquitectura del notebook.
- No se agrega backoff exponencial nuevo más allá del que ya existe en `fetch.py` (`max_retries` por request individual) — el límite de intentos acá es a nivel de corridas completas, no de reintentos HTTP dentro de una misma llamada.

## Decisions

**1. Conteo de intentos como columna nueva del índice (`attempts`), no un archivo separado.**
Se agrega `attempts` a `INDEX_COLUMNS` en `index.py`. Un índice viejo sin esa columna se carga con `attempts=0` por defecto (vía `fillna` o default en `load_index`). Evita mantener dos fuentes de verdad (índice + tabla de fallos aparte, como hace el notebook con `notas_fallidas.csv`).
Alternativa descartada: archivo separado de intentos (patrón del notebook) — fragmenta el estado en dos archivos que pueden desincronizarse; el índice ya es la fuente única de verdad de status por URL.

**2. Nuevo status `exhausted`, distinto de `error`.**
`error` sigue significando "el intento más reciente falló, puede reintentarse". `exhausted` significa "se agotaron los intentos, no se vuelve a tocar". `pending_urls()` excluye tanto `ok` como `exhausted`. Esto hace explícito en el índice mismo cuáles URLs quedaron descartadas, auditable sin lógica adicional.
Alternativa descartada: mantener `error` y solo chequear `attempts >= max` en `pending_urls()` — funciona, pero esconde la razón en una comparación numérica en vez de en el status mismo; menos legible al inspeccionar el CSV a mano.

**3. Concurrencia con `concurrent.futures.ThreadPoolExecutor`, no `threading` manual.**
El notebook usa threads manuales + locks explícitos. Se prefiere `ThreadPoolExecutor` (stdlib) por manejo de pool más simple y directo con `submit`/`as_completed`, evitando reimplementar la gestión de hilos.
Alternativa descartada: `asyncio` + `httpx` — requiere reescribir `fetch.py` a async y agregar dependencia nueva (`httpx`); no aporta ventaja real para I/O-bound con pocos workers (2-6) sobre `requests` + threads.

**3bis. Rate limiting por worker (`threading.local`), no una única `RateLimiter` global compartida.**
**Corrección post-diseño inicial**: la decisión 5 original (una sola `RateLimiter` compartida con lock) serializa el arranque de requests a nivel global — con lock, `wait()` sigue forzando "un request cada `delay` segundos" en total sin importar cuántos workers haya, anulando por completo la ganancia de velocidad que es el objetivo de este change. Se corrige a: cada hilo del pool obtiene su propia instancia de `RateLimiter` (vía `threading.local`, creada perezosamente la primera vez que ese hilo la usa). Así, el ritmo de "delay entre requests" se respeta por hilo individual (mismo criterio que `PAUSA_MIN/PAUSA_MAX` del notebook, aplicado por thread), y el throughput total escala con la cantidad de workers — que es exactamente lo que se buscaba con la concurrencia.
Alternativa descartada: una `RateLimiter` compartida con lock (diseño original) — thread-safe pero sin beneficio de velocidad, contradice el objetivo del change.

**4. Escritura del índice serializada, no por worker.**
Cada worker devuelve su resultado (éxito/error) a un loop principal en el hilo coordinador, que es el único que llama `save_index`/`save_structured` — evita condiciones de carrera al escribir el CSV/parquet desde múltiples hilos simultáneamente (patrón similar al `threading.Lock` del notebook, pero centralizado en vez de repartido en cada worker).
Alternativa descartada: cada worker escribe su propio resultado con lock (como el notebook) — funciona pero multiplica los puntos de escritura a disco; centralizar en el hilo coordinador es más simple de razonar y de testear.

**5. `RateLimiter.wait()` se hace thread-safe con un lock interno de todas formas.**
Aunque con la decisión 3bis cada worker usa su propia instancia (sin compartir estado entre hilos), se agrega igual un `threading.Lock` interno a `RateLimiter.wait()` — hardening barato que evita una condición de carrera si en el futuro alguna instancia se comparte entre hilos por error o por un uso distinto (ej. `reprocess_existing` u otro llamador).

## Risks / Trade-offs

- [Riesgo] Índices existentes en disco (de corridas previas del motor actual) no tienen columna `attempts` → **Mitigación**: `load_index` completa `attempts=0` para filas sin esa columna; no requiere migración manual.
- [Riesgo] Concurrencia mal configurada (workers muy alto) podría disparar rate-limit del sitio pese al `RateLimiter` por request, si el delay efectivo por worker resulta menor al pretendido → **Mitigación**: default conservador (2-4 workers, igual que el notebook), documentado en `scripts/scrape_news.py --help`.
- [Trade-off] Centralizar la escritura en el hilo coordinador limita el paralelismo real a la parte de I/O de red (fetch), no a la escritura en disco — aceptable porque el fetch (red + delay) es el cuello de botella real, no la escritura de CSV/parquet.

## Open Questions

- ¿`max_attempts` default = 3 (igual que el notebook) o distinto? Se deja como parámetro configurable con default 3 salvo objeción.
- ¿Vale la pena exponer `exhausted` en algún reporte/resumen de corrida (ej. "N URLs descartadas permanentemente") o basta con poder filtrarlas del CSV a mano? Se deja para tasks.md si hace falta.
