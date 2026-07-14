## 1. Setup

- [x] 1.1 Agregar dependencias a `requirements.txt` (cliente HTTP + parser HTML, ej. `requests`/`httpx` + `beautifulsoup4` o `lxml`)
- [x] 1.2 Crear módulo `src/shannon_model/scraping/` (o similar) para el código reutilizable del scraper
- [x] 1.3 Crear script CLI `scripts/scrape_news.py`

## 2. Índice idempotente url → nota_id

- [x] 2.1 Implementar generación de `nota_id` determinístico por hash de la URL
- [x] 2.2 Implementar lectura/escritura del índice `data/raw/scrape_index.csv` (columnas: `url, nota_id, status, http_status, error_msg, scraped_at, html_path`)
- [x] 2.3 Implementar lógica de resume: cargar URLs únicas desde `data/raw/ehm_3months_filtered.xlsx`, saltar las que ya están `status: ok` en el índice

## 3. Descarga de HTML

- [x] 3.1 Implementar fetch HTTP con user-agent identificable y manejo de timeout/errores 4xx/5xx
- [x] 3.2 Implementar rate limiting (delay configurable entre requests consecutivas)
- [x] 3.3 Guardar HTML crudo en `data/raw/html/<nota_id>.html`
- [x] 3.4 Actualizar el índice con `status: ok` o `status: error` + motivo según resultado de cada request

## 4. Extracción estructurada

- [x] 4.1 Implementar parsing del bloque `application/ld+json` (`NewsArticle`) para extraer `titulo`, `autor_nombre`, `autor_slug`, `fecha_publicacion`, `num_imagenes`, `num_etiquetas`
- [x] 4.2 Implementar cálculo de derivados temporales desde `fecha_publicacion` (`hora_del_dia`, `hora_sin`, `hora_cos`, `dia_semana`, `dia_sin`, `dia_cos`, `es_fin_de_semana`, `mes`, `mes_sin`, `mes_cos`)
- [x] 4.3 Implementar conteo de `num_palabras` desde `div.texto-noticia`
- [x] 4.4 Implementar `tiene_img_principal` a partir de la lista de imágenes del JSON-LD
- [x] 4.5 Asignar `categoria_nota` directo desde la columna `folder` de `ehm_3months_filtered.xlsx` (join por URL)
- [x] 4.6 Manejar caso de nota sin JSON-LD válido: marcar `status: error` en el índice con motivo, no escribir fila incompleta
- [x] 4.7 Persistir dataset estructurado en `data/raw/notes_structured.parquet`

## 5. Verificación

- [x] 5.1 Correr el scraper end-to-end sobre las 3,408 URLs y confirmar que el índice llega a 3,408 filas con `status` resuelto (`ok` o `error`) — 3,406 ok / 2 error
- [x] 5.2 Re-correr el scraper sobre el mismo índice y confirmar que no se re-descargan notas `ok` ni se duplican `nota_id` — 0 urls duplicadas, 0 nota_id duplicados en la corrida completa
- [x] 5.3 Confirmar que `data/raw/html/` y `data/raw/notes_structured.parquet` no quedan trackeados por git (`git status` limpio) — confirmado
- [x] 5.4 Revisar manualmente una muestra de notas con `status: error` para confirmar que el motivo registrado es correcto y accionable — ambos errores son HTTP 404 (links muertos reales), motivo correcto y accionable

## 6. Features adicionales (largo_titulo, num_imagenes_real, num_letras)

- [x] 6.1 Implementar `largo_titulo` (longitud en caracteres de `titulo`)
- [x] 6.2 Implementar `num_letras` (conteo de caracteres de `div.texto-noticia`)
- [x] 6.3 Implementar `num_imagenes_real` (conteo de tags `<img>` dentro de `div.texto-noticia`)
- [x] 6.4 Agregar las 3 columnas nuevas a `STRUCTURED_COLUMNS` en `src/shannon_model/scraping/pipeline.py`
- [x] 6.5 Reprocesar las notas ya scrapeadas usando el HTML ya guardado en `data/raw/html/` (sin re-fetch al sitio) para completar las columnas nuevas en `notes_structured.parquet` — 3,406/3,406 actualizadas, 0 saltadas (tardó ~12 min: `reprocess_existing` concatena fila por fila, O(n²) en pandas — anotar como mejora futura, no bloqueante)

## 7. Tier 1 restante: señales de título y estructura del cuerpo

- [x] 7.1 Implementar `tiene_signo_pregunta` (`"?"` en `titulo`)
- [x] 7.2 Implementar `tiene_numero` (algún dígito en `titulo`)
- [x] 7.3 Implementar `tiene_mayusculas_excesivas` (palabra de 3+ letras en mayúsculas en `titulo`)
- [x] 7.4 Implementar `num_parrafos` (tags `<p>` dentro de `div.texto-noticia`)
- [x] 7.5 Implementar `tiene_subtitulos` (tags `<h2>`/`<h3>` dentro del cuerpo)
- [x] 7.6 Implementar `tiene_video_embed` (iframe con `src` de youtube.com/facebook.com/plugins/video, o tag `<video>`) — no confundir con iframes de ads
- [x] 7.7 Agregar las 6 columnas nuevas a `STRUCTURED_COLUMNS` en `src/shannon_model/scraping/pipeline.py`
- [x] 7.8 Reprocesar las notas ya scrapeadas usando el HTML ya guardado (sin re-fetch) para completar las columnas nuevas en `notes_structured.parquet` — 3,406/3,406, 0 duplicados, aprovechado para arreglar el O(n²) del reprocess (~10 min en vez de escalar cuadráticamente)
