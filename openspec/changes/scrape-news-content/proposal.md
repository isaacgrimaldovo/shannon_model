## Why

El pipeline Shannon (ver `shannon_diccionario_datos.xlsx`) necesita, como primer insumo, el contenido completo de cada nota periodística (título, cuerpo, autor, imágenes, etiquetas, fecha). Hoy `data/raw/` solo tiene `ehm_3months_filtered.xlsx`, que es analytics puro (url, folder, source, fecha, pageViewsTotal) — no hay contenido de nota. Sin este dato no se puede avanzar a la etapa NLP ni al dataset real de entrenamiento (bloquea `training-foundation-next`). El sitio fuente (heraldodemexico.com.mx) ya se validó como scrapeable sin fricción (HTML estático, robots.txt sin restricciones, JSON-LD `NewsArticle` con la mayoría de los campos necesarios).

## What Changes

- Nuevo scraper que toma las 3,408 URLs únicas de `data/raw/ehm_3months_filtered.xlsx` y descarga el HTML completo de cada nota.
- Guardar HTML crudo por nota bajo `data/raw/html/` (un archivo por nota).
- Extraer y persistir campos estructurados de la etapa 1 del diccionario (título, autor_nombre/autor_slug, fecha_publicacion + derivados temporales, num_palabras, tiene_img_principal, num_imagenes, num_etiquetas, categoria_nota) en un dataset tabular bajo `data/raw/`.
- Índice persistente `url → nota_id` con estado de scraping (pendiente/ok/error) para permitir resumir corridas sin duplicar ni re-descargar notas ya obtenidas.
- Rate limiting y user-agent identificable en las requests (mismo dominio, ~3,408 requests).
- autor_id categórico (`autor_01`...`autor_15`), pipeline NLP (tono/polaridad/categoria_titulo) y analytics hora1/día7 (views_1h/views_7d/log_views) quedan **fuera de alcance** — son etapas posteriores del pipeline Shannon.
- Descubrimiento de notas nuevas (crawling de portada/categoría) queda **fuera de alcance** de esta iteración; el diseño no debe cerrar la puerta a agregarlo después.

## Capabilities

### New Capabilities
- `news-scraping`: obtención de contenido completo de notas periodísticas (HTML crudo + extracción estructurada) a partir de una lista conocida de URLs, con índice idempotente y salida en `data/raw/`.

### Modified Capabilities
(ninguna — no se tocan `training-pipeline`, `colab-integration` ni `collaboration` en este change)

## Impact

- Código nuevo: módulo de scraping en `src/shannon_model/` (o paquete separado, a definir en design.md) + script CLI en `scripts/`.
- Dependencias nuevas: cliente HTTP (`requests` o `httpx`) + parser HTML (`beautifulsoup4` o `lxml`) — agregar a `requirements.txt`.
- Datos: nuevos artefactos en `data/raw/html/` y `data/raw/<dataset estructurado>` — ya cubiertos por `.gitignore` (`data/raw/*`), no se commitean.
- Prerequisito de `training-foundation-next` (fuente real de datos) — no modifica esa change, solo la desbloquea.
- Sin impacto en `scripts/train.py`, Colab ni configs existentes.
