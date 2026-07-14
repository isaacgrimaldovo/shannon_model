# Backlog de features candidatas — modelo de impacto en vistas

Lista de referencia para cuando el modelo baseline (`predict-views-impact`) no dé los resultados esperados. Ordenada por esfuerzo de implementación, no por impacto esperado.

Estado actual del modelo (ver `openspec/changes/predict-views-impact/`): `RandomForestRegressor` sobre features estructurales scrapeadas + target proxy (`log1p` de `pageViewsTotal` sumado por url). Primeras 3 features de este backlog (`largo_titulo`, `num_imagenes_real`, `num_letras`) ya están en implementación — ver `openspec/changes/scrape-news-content/tasks.md` grupo 6 y `openspec/changes/predict-views-impact/tasks.md` grupo 6.

## Tier 1 — ya en el HTML scrapeado, solo falta parsear

Sin nueva dependencia ni etapa nueva del pipeline. Se calculan desde `data/raw/html/<nota_id>.html` (ya descargado) durante la extracción en `src/shannon_model/scraping/extract.py`.

| Feature | Fuente | Por qué importa |
|---|---|---|
| `largo_titulo` (caracteres) | `titulo` | Títulos muy largos/cortos afectan CTR — **en implementación** |
| `num_imagenes_real` | contar `<img>` en `div.texto-noticia` | El JSON-LD da siempre 3 (variantes de la imagen hero, sin señal) — **en implementación**, corrige ese bug |
| `num_letras` | `div.texto-noticia` | Complemento a `num_palabras` — **en implementación** |
| `tiene_signo_pregunta` | `titulo` | Proxy barato de "categoria_titulo=pregunta" sin NLP |
| `tiene_numero` (ej. "5 ofertas", "2026") | `titulo` | Listas/números en título suben CTR (patrón conocido) |
| `tiene_mayusculas_excesivas` | `titulo` | Señal de sensacionalismo, sin modelo de tono |
| `num_parrafos`, `longitud_parrafo_promedio` | HTML crudo (`<p>` dentro del cuerpo) | Estructura del cuerpo, no solo cantidad de palabras |
| `tiene_video_embed`, `tiene_subtitulos` (h2/h3) | HTML crudo | Formato rico correlaciona con tiempo en página |
| `source` (Facebook/Google/Discover/dark social) | ya está en `ehm_3months_filtered.xlsx`, sin usar como feature | Hoy solo se usa para sumar el target proxy, no como predictor |

## Tier 2 — necesita NLP (nueva etapa, nueva dependencia)

| Feature | Requiere |
|---|---|
| `tono`/`polaridad` | Modelo de sentimiento en español (ej. pysentimiento) — el diccionario de datos lo marca como una de las features más fuertes |
| `categoria_titulo` fina (pregunta/top/descriptiva) | Clasificador; versión barata ya cubierta en Tier 1 con reglas simples |
| Entidades mencionadas (personas/marcas/lugares) | NER — correlaciona con interés/búsqueda del tema |

## Tier 3 — necesita Google Analytics (etapa Analytics, fuera de alcance actual)

| Feature | Requiere |
|---|---|
| `views_1h`, `es_breaking` | Analytics API a la hora 1 de publicación |
| `views_7d` real (reemplaza el target proxy actual) | Analytics API a día 7 |

## Tier 4 — contexto externo (más especulativo)

| Feature | Requiere |
|---|---|
| Google Trends del tema el día de publicación | API externa nueva |
| Competencia editorial (cuántas notas de la misma categoría se publicaron esa hora) | Derivable del propio dataset, sin API externa |

## Cómo usar esta lista

Si el modelo baseline no mejora al reentrenar con las features del Tier 1 (`predict-views-impact` tasks 6.2-6.3), el siguiente paso natural es completar el resto de Tier 1 (barato, sin nueva dependencia) antes de saltar a Tier 2 (NLP, requiere nueva change OpenSpec + dependencia nueva).
