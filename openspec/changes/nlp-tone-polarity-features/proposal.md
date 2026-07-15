## Why

`compare-gbr-vs-random-forest` confirmó (evidencia, no intuición) que el techo actual de R² (~0.45 modelo A, ~0.59 modelo B) no es del algoritmo — GBR entrenado sobre las mismas features perdió contra RandomForest en ambos modelos. El próximo candidato documentado como pendiente desde `predict-views-impact` (non-goal explícito) es la señal de contenido real de la nota: tono y polaridad del cuerpo completo, no solo señales de forma (`num_palabras`, `tiene_numero`, etc.). Ninguna feature actual mide DE QUÉ TRATA o CÓMO SUENA la nota — solo su forma estructural.

## What Changes

- **BREAKING (dato)**: el texto del cuerpo (`cuerpo_texto`) nunca se persistió — `body_stats()` lo descarta tras contar palabras/párrafos. El HTML crudo tampoco sobrevive en disco para el 99.8% de las 3,411 notas ya scrapeadas (`data/raw/html/` solo tiene 5 archivos; el índice las marca `ok` pero el archivo ya no existe). Se necesita re-descargar esas 3,411 URLs para poder extraer el cuerpo.
- Nuevo mecanismo de backfill en `scraping/pipeline.py` que re-descarga HTML para URLs ya marcadas `ok` en el índice cuyo `html_path` no exista en disco, reusando el mismo `RateLimiter`/reintentos de `scraper-reliability` — no un scraper nuevo.
- `extract.py::body_stats` gana un campo nuevo `cuerpo_texto` (texto plano del cuerpo, ya extraído hoy pero descartado) — se agrega a `notes_structured.parquet`, no reemplaza ninguna feature existente.
- Nuevo módulo de scoring NLP (tono/polaridad) sobre `cuerpo_texto`, usando un modelo de sentiment pre-entrenado en español (`pysentimiento`/RoBERTuito, dependencia nueva vía `transformers`, ya compatible con `torch` que el proyecto ya trae). Corre en batch, una sola vez, con resultados cacheados en disco (no se re-infiere en cada entrenamiento).
- Dos features nuevas para el dataset de impacto (`impact_model/dataset.py`): `polaridad_score` (continua, `P(POS) − P(NEG)`) y `tono` one-hot (`tono_POS`/`tono_NEG`/`tono_NEU`, mismo patrón que `source_*`/`categoria_*`).
- Sin cambios en `dataset.py::FEATURE_COLUMNS` existentes, target, esquema de CV (`TimeSeriesSplit`) ni en los modelos A/B ya vigentes — las features nuevas se suman, no reemplazan nada.

## Capabilities

### New Capabilities
(ninguna — se modela como extensión de `news-scraping` y `views-impact-model`, no una capability nueva)

### Modified Capabilities
- `news-scraping`: agrega persistencia del texto del cuerpo (`cuerpo_texto`) y mecanismo de backfill de HTML faltante para URLs ya `ok`.
- `views-impact-model`: agrega features de tono/polaridad (NLP sobre `cuerpo_texto`) al dataset de entrenamiento de los modelos A y B.

## Impact

- Código: `src/shannon_model/scraping/extract.py` (persistir `cuerpo_texto`), `src/shannon_model/scraping/pipeline.py` (backfill de HTML faltante, nueva columna en `STRUCTURED_COLUMNS`), módulo nuevo `src/shannon_model/impact_model/nlp_tone.py` (scoring de tono/polaridad, cacheado), `src/shannon_model/impact_model/dataset.py` (join de features nuevas, `FEATURE_COLUMNS` extendido).
- Datos: re-scraping de red de las 3,411 URLs ya conocidas (backfill de HTML, no las ~11,377 nuevas de `expand-url-source-csv` — eso es scope de otro change). Nuevo artefacto cacheado `checkpoints/views_impact/nlp_tone_cache.parquet` (o similar), excluido de git igual que el resto de `checkpoints/`.
- Dependencias: `pysentimiento` (y transitivamente `transformers`) nuevas en `requirements.txt`. Descarga de pesos del modelo pre-entrenado (~500MB) desde HuggingFace Hub en la primera corrida — requiere red, no se vendorea en el repo.
- Config: `configs/views_impact.yaml` gana sección para nombre/ruta del modelo de sentiment y ruta del cache.
- Fuera de alcance: `categoria_titulo` (clasificación de tema vía NLP — redundante con `categoria_nota` ya existente, se evalúa aparte si hace falta), fine-tuning del modelo de sentiment, GBR (ya descartado), expandir a las ~11,377 URLs nuevas de `expand-url-source-csv` (dataset de este change se limita a las 3,411 notas ya scrapeadas).
- Sin impacto en `training-pipeline` (MLP baseline sintético, capability distinta) ni en `training-foundation-next`.
