## Context

`data/raw/ehm_3months_filtered.xlsx` tiene 251,199 filas (analytics por url x source x fecha) pero solo 3,408 URLs únicas, todas en `heraldodemexico.com.mx`, repartidas en 6 categorías (`folder`): `/nacional/`, `/espectaculos/`, `/economia/`, `/mundo/`, `/estilo-de-vida/`, `/tendencias/`.

Validación hecha durante exploración (muestra real, 1 URL):
- `curl` simple trae el HTML completo (200 OK, ~120KB), sin JS rendering.
- `robots.txt` no tiene `Disallow`.
- Cada nota trae un bloque `<script type="application/ld+json">` con `@type: NewsArticle`: `headline`, `image` (array de URLs), `datePublished`, `author.name` + `author.url` (slug), `articleSection`, `keywords` (string separado por comas).
- El cuerpo de texto vive en `<div class="texto-noticia" itemprop="articleBody">`.

No existe código de scraping en el repo (`src/shannon_model/` solo tiene `config.py`, `model.py`, `train.py`). Este es un capability nuevo, greenfield.

## Goals / Non-Goals

**Goals:**
- Descargar y persistir el HTML crudo de las 3,408 notas conocidas.
- Extraer campos estructurados de la etapa 1 del diccionario de datos a partir del JSON-LD + `texto-noticia`.
- Idempotencia: re-correr el scraper no debe re-descargar ni duplicar notas ya obtenidas con éxito.
- Resumible: si se interrumpe a mitad de corrida, la siguiente corrida retoma desde donde quedó.
- Trazabilidad de errores: notas que fallan (404, timeout, HTML sin JSON-LD) quedan registradas con su causa, no silenciadas.

**Non-Goals:**
- Descubrimiento de notas nuevas (crawling de portada/categoría) — el input de URLs es fijo, viene del xlsx existente.
- Pipeline NLP (tono, polaridad, categoria_titulo) — etapa posterior del diccionario.
- Analytics hora1/día7 (views_1h, views_7d, log_views) — etapa posterior, requiere Google Analytics.
- `autor_id` categórico (`autor_01`...`autor_15`) — se guarda `autor_nombre`/`autor_slug` crudo; la categorización es feature-engineering posterior.
- Soporte multi-dominio — el scraper puede asumir la estructura de heraldodemexico.com.mx (JSON-LD NewsArticle + `div.texto-noticia`).

## Decisions

**1. Índice persistente `url → nota_id` con estado, separado del dataset estructurado.**
Un archivo `data/raw/scrape_index.csv` (o parquet) con columnas `url, nota_id, status (pending|ok|error), http_status, error_msg, scraped_at, html_path`. El scraper primero carga este índice, salta URLs ya `ok`, y solo reintenta `pending`/`error`. Esto separa "qué se intentó" de "qué se extrajo" — si mañana cambia la lógica de extracción, se puede reprocesar el HTML ya descargado sin volver a pegarle al sitio.
Alternativa descartada: usar el nombre de archivo HTML como única fuente de verdad (sin índice) — no permite registrar errores ni distinguir "nunca intentado" de "falló".

**2. `nota_id` determinístico por hash de URL, no autoincremental.**
`nota_id = "nota_" + sha1(url)[:8]` (o similar). Evita colisiones de numeración si el scraper corre en paralelo o se reinicia el índice, y es reproducible entre corridas sin depender de orden de procesamiento.
Alternativa descartada: contador autoincremental — frágil si el índice se corrompe o se corre en paralelo.

**3. HTML crudo y dataset estructurado en archivos separados.**
- `data/raw/html/<nota_id>.html`: HTML completo tal cual se descargó.
- `data/raw/notes_structured.parquet`: una fila por nota con los campos de la etapa 1 (`nota_id`, `url`, `titulo`, `autor_nombre`, `autor_slug`, `fecha_publicacion`, `hora_del_dia`, `hora_sin`, `hora_cos`, `dia_semana`, `dia_sin`, `dia_cos`, `es_fin_de_semana`, `mes`, `mes_sin`, `mes_cos`, `num_palabras`, `num_letras`, `largo_titulo`, `tiene_img_principal`, `num_imagenes`, `num_imagenes_real`, `num_etiquetas`, `categoria_nota`, `tiene_signo_pregunta`, `tiene_numero`, `tiene_mayusculas_excesivas`, `num_parrafos`, `tiene_subtitulos`, `tiene_video_embed`).
`categoria_nota` se toma directo de la columna `folder` de `ehm_3months_filtered.xlsx` (no requiere NLP ni parsing adicional).
Alternativa descartada: extraer directo del HTML en cada uso (sin dataset materializado) — obliga a re-parsear HTML cada vez que se entrena, más lento y frágil a cambios de parser.

**4. Extracción vía JSON-LD como fuente primaria, `div.texto-noticia` solo para `num_palabras`.**
El JSON-LD ya cubre título, autor, fecha, imágenes y etiquetas de forma estructurada y estable (contrato `schema.org`, menos propenso a romperse que parsear clases CSS). Solo el conteo de palabras requiere el body de texto plano.
Riesgo: si el sitio deja de emitir JSON-LD en notas viejas o de otras secciones, esos campos quedan nulos — se maneja como fila con campos faltantes + entrada en el índice de errores, no como fallo total del scraper.

**5. Rate limiting fijo + user-agent identificable, sin concurrencia alta.**
Delay configurable entre requests (ej. 1–2s) y un único proceso secuencial (o concurrencia baja, 2–4 workers) para las 3,408 URLs. Con robots.txt abierto no hay bloqueo legal, pero el volumen justifica ser buen ciudadano del sitio.
Alternativa descartada: scraping masivo concurrente sin límite — mayor riesgo de rate-limit/ban del lado del sitio, sin necesidad real (3,408 notas es volumen chico, corre en minutos incluso con delay).

**6. Script CLI nuevo, no integrado a `scripts/train.py`.**
`scripts/scrape_news.py` (o `scripts/collect_data.py`), invocado por separado del entrenamiento — el scraping es una etapa de recolección de datos, no de training. Reutiliza `configs/` solo si hace falta parametrizar (ej. delay, paths de salida); no reemplaza ni modifica `scripts/train.py`.

**7. `num_imagenes_real` cuenta `<img>` del cuerpo, no del JSON-LD.**
El uso real (`predict-views-impact`) detectó que `num_imagenes`/`tiene_img_principal` (derivados del array `image` del JSON-LD) salen constantes (=3 siempre) porque ese array son variantes de resolución de la misma imagen hero, no imágenes distintas del cuerpo. `num_imagenes_real` cuenta tags `<img>` reales dentro de `div.texto-noticia` (mismo nodo que ya se parsea para `num_palabras`/`num_letras`), dando la señal que el diccionario espera.
`num_imagenes` y `tiene_img_principal` se mantienen sin cambios por compatibilidad — quedan documentados como "conteo de variantes de la imagen hero", no como conteo real de imágenes del cuerpo.
Alternativa descartada: reemplazar/eliminar `num_imagenes`/`tiene_img_principal` — rompería filas ya persistidas y consumidores existentes sin necesidad; más simple sumar una columna nueva.

**8. `largo_titulo` y `num_letras` como complemento a `num_palabras`.**
`largo_titulo`: longitud en caracteres de `titulo` (ya extraído del JSON-LD, solo falta la derivada). `num_letras`: conteo de caracteres del texto de `div.texto-noticia` (mismo nodo ya usado para `num_palabras`). Señal barata adicional sobre longitud/formato, sin nueva dependencia ni re-fetch.

**9. Tier 1 restante del backlog: 6 features de parsing simple sobre título/cuerpo.**
El CV fold-safe de `predict-views-impact` mostró R²≈0.03 con las features actuales — casi sin señal. Antes de saltar a NLP (dependencia nueva) se agota el parsing barato:
- `tiene_signo_pregunta`: 1 si `titulo` contiene `"?"`.
- `tiene_numero`: 1 si `titulo` contiene al menos un dígito.
- `tiene_mayusculas_excesivas`: 1 si el título tiene alguna palabra de 3+ letras completamente en mayúsculas (heurística de sensacionalismo, sin modelo de tono).
- `num_parrafos`: cantidad de tags `<p>` dentro de `div.texto-noticia` (confirmado en HTML real: 9 `<p>` en la muestra inspeccionada).
- `tiene_subtitulos`: 1 si hay al menos un `<h2>`/`<h3>` dentro del cuerpo.
- `tiene_video_embed`: 1 si hay un `<iframe>` cuyo `src` contiene `youtube.com` o `facebook.com/plugins/video` (o un tag `<video>`) — se distingue por dominio para no confundir con iframes de ads (`div-gpt-ad`, visto en la misma muestra).
Todas se calculan desde el HTML ya guardado (mismo patrón que decisión 7/8: reprocesable sin re-fetch).

**10. `source` (Facebook/Google/Discover/dark social) queda fuera de esta iteración.**
Usarlo como feature real requeriría cambiar la granularidad de `notes_structured.parquet` de "una fila por nota" a "una fila por nota x source" — un cambio de arquitectura mayor, no un parsing adicional. Se evalúa como opción separada (ver open questions de `predict-views-impact`), no se mezcla con este grupo de features baratas.

## Risks / Trade-offs

- [Riesgo] El sitio cambia su template HTML o deja de emitir JSON-LD → extracción estructurada falla silenciosamente para notas nuevas. **Mitigación**: el índice registra `error` con mensaje específico (ej. "no JSON-LD found") en vez de dejar campos vacíos sin marca; se puede auditar `status=error` después de cada corrida.
- [Riesgo] 3,408 requests al mismo dominio pueden disparar rate-limiting o bloqueo temporal del sitio. **Mitigación**: delay configurable entre requests + backoff con reintentos limitados en errores 429/5xx.
- [Riesgo] HTML crudo son ~120KB x 3,408 ≈ 400MB en disco. **Mitigación**: ya excluido de git vía `data/raw/*`; documentar el tamaño esperado en el proposal/README para que el usuario no se sorprenda.
- [Trade-off] Guardar HTML completo (no solo el extract) infla espacio en disco, pero permite re-extraer campos nuevos sin re-scrapear si el diccionario de datos crece (ej. si más adelante se necesita otro campo del HTML que hoy no se captura) — este es exactamente el caso de `num_imagenes_real`/`largo_titulo`/`num_letras`: se reprocesan desde el HTML ya guardado, sin volver a pegarle al sitio.

## Open Questions

- ¿`autor_slug` alcanza como identificador estable de autor para la futura categorización `autor_01..autor_15`, o hace falta normalizar nombres con acentos/variantes? (No bloquea este change — se resuelve en la etapa de feature-engineering.)
- ¿Formato final del dataset estructurado: parquet o csv? Parquet es más eficiente para el volumen esperado a futuro (crawling de notas nuevas), pero csv es más simple de inspeccionar a mano. A definir en tasks/implementación si no hay preferencia fuerte del equipo.
