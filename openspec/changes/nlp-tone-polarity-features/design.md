## Context

`data/processed/notes_structured.parquet` tiene 3,411 notas con features estructurales (forma del título, temporales, autor, canal) pero ninguna señal de contenido real — `extract.py::body_stats()` calcula `num_palabras`/`num_parrafos`/etc. sobre el texto del cuerpo y lo descarta sin persistirlo. El HTML crudo (`data/raw/html/*.html`) tampoco sobrevive: de 3,411 notas con `status=ok` en `scrape_index.csv`, solo 5 tienen su archivo HTML todavía en disco — no hay forma de reprocesar sin re-descargar.

`compare-gbr-vs-random-forest` ya descartó que el techo sea de algoritmo. El diccionario de datos original siempre marcó `tono`/`polaridad` como etapa NLP pendiente (non-goal explícito en `predict-views-impact` y `content-only-impact-model`) — este change la aborda.

`scraper-reliability` ya resolvió reintentos/rate-limiting/índice idempotente — este change reusa esa infraestructura, no la reemplaza.

## Goals / Non-Goals

**Goals:**
- Persistir `cuerpo_texto` (texto plano del cuerpo) para las 3,411 notas ya conocidas, vía backfill de HTML faltante.
- Calcular tono (categórico) y polaridad (continuo) sobre `cuerpo_texto` con un modelo de sentiment pre-entrenado en español, sin fine-tuning.
- Sumar esas features al dataset de los modelos A y B ya existentes (`RandomForestRegressor`, vigente tras descartar GBR), sin tocar target, CV ni features actuales.
- Cachear el resultado de sentiment por nota para no re-inferir en cada entrenamiento.

**Non-Goals:**
- `categoria_titulo` (clasificación de tema vía NLP) — redundante con `categoria_nota` (ya viene del `folder` de origen), fuera de alcance.
- Fine-tuning o entrenamiento propio del modelo de sentiment — se usa pre-entrenado tal cual.
- Expandir a las ~11,377 URLs nuevas de `expand-url-source-csv` — ese dataset crece en un change aparte; este trabaja sobre las 3,411 notas ya scrapeadas.
- Cambiar de algoritmo (GBR) — ya descartado con evidencia en `compare-gbr-vs-random-forest`.
- Chunking/promediado de texto largo por sección — se acepta truncamiento simple en v0 (ver Riesgos).

## Decisions

**1. Backfill de HTML faltante como función nueva en `pipeline.py`, no un scraper aparte.**
`run_scrape` ya no vuelve a tocar URLs con `status=ok` (via `pending_urls`) — por diseño, para no re-descargar lo ya hecho. Se agrega `backfill_missing_html(config)`: itera las URLs `ok` del índice, si `html_path` no existe en disco re-descarga (mismo `RateLimiter`/`fetch_html`/reintentos que `run_scrape`), re-extrae campos con `extract_note_fields` (que ahora incluye `cuerpo_texto`) y actualiza la fila en `notes_structured.parquet`. Si el HTML sí existe, se comporta como `reprocess_existing` (no re-descarga).
Alternativa descartada: borrar el índice y correr `run_scrape` de cero — perdería el registro de qué URLs ya fallaron permanentemente (`status=exhausted`) y forzaría re-decidir reintentos ya agotados.

**2. `cuerpo_texto` se persiste como columna nueva en `notes_structured.parquet`, no en un archivo separado.**
3,411 notas de texto plano (no HTML) son del orden de unos pocos MB — no justifica fragmentar el dataset en dos archivos que hay que mantener sincronizados. Se agrega a `STRUCTURED_COLUMNS` en `pipeline.py`.
Alternativa descartada: archivo de texto separado indexado por `nota_id` — más complejidad de sincronización sin beneficio real a este volumen.

**3. Modelo de sentiment: `pysentimiento` (RoBERTuito fine-tuned para sentiment en español), no léxico ni API externa.**
`pysentimiento` da un modelo pre-entrenado específico para español (entrenado sobre TASS, corpus de tono en español latinoamericano/rioplatense), corre 100% local sobre `torch` (ya dependencia del proyecto), sin llamadas a red en inferencia ni costo por request. Devuelve `POS`/`NEG`/`NEU` con probabilidades.
Alternativas descartadas:
- Léxico de palabras positivas/negativas — descartado explícitamente por el usuario: menos preciso en español periodístico informal, sin capturar negación/contexto.
- API externa (OpenAI/Anthropic) — rompe la reproducibilidad offline del pipeline (Colab + local), agrega costo por nota y dependencia de red en cada re-entrenamiento; no es necesario para un modelo de sentiment, tarea ya bien cubierta por modelos chicos especializados.
- Modelo multilingüe genérico (ej. `nlptown/bert-base-multilingual-uncased-sentiment`) — entrenado sobre reviews de producto (Amazon), no sobre español periodístico/social; RoBERTuito es específico del idioma y dominio más cercano al del proyecto.

**4. Encoding de features: `tono_POS`/`tono_NEG`/`tono_NEU` one-hot + `polaridad_score` continuo (`P(POS) − P(NEG)`).**
Mismo patrón ya usado para `source_*`/`categoria_*` (one-hot, modelo de árboles no necesita scaling). `polaridad_score` da una señal continua de intensidad que el one-hot de la clase ganadora por sí solo no captura (una nota `POS` con probabilidad 0.51 no es igual de "positiva" que una con 0.95).
Alternativa descartada: un solo score continuo sin one-hot — pierde la interpretabilidad SHAP de "esta nota es tono X" que el diccionario pide para reportar a editores.

**5. Resultados de sentiment cacheados en `checkpoints/views_impact/nlp_tone_cache.parquet`, keyed por `nota_id`.**
La inferencia del modelo (aunque corre local) no es gratis — cachear evita recalcular tono/polaridad de las mismas 3,411 notas en cada corrida de entrenamiento/grid-search. Cache inválida solo si `cuerpo_texto` cambió (backfill nuevo, hash simple del texto).
Alternativa descartada: recalcular siempre — desperdicia tiempo de CPU en cada corrida sin necesidad, dado que `cuerpo_texto` no cambia salvo backfill nuevo.

**6. Inferencia en batch, un solo proceso, no dentro del `ThreadPoolExecutor` del scraping.**
Cargar el modelo de sentiment (~500MB) por hilo de scraping sería redundante y contencioso (inferencia es CPU-bound, compite por GIL con los hilos de I/O de red). El scoring de tono/polaridad corre como paso posterior y separado, sobre el `cuerpo_texto` ya persistido — carga el modelo una sola vez, procesa todas las notas pendientes de cache en un batch.
Alternativa descartada: inferencia dentro de `_fetch_and_extract` (por nota, durante el scraping) — mezclaría dos preocupaciones con perfiles de recursos opuestos (I/O de red vs CPU de inferencia) en el mismo hilo.

**7. Notas sin `cuerpo_texto` se excluyen del dataset, no se imputa tono/polaridad neutro por default.**
Mismo criterio que el resto del pipeline (decisión 14 de `predict-views-impact`: fallar explícito en vez de aproximar). Aplica solo a fallos de backfill (HTML no recuperable) — se espera que sea un número chico de las 3,411.

## Risks / Trade-offs

- [Riesgo] RoBERTuito fue entrenado sobre texto corto (tweets, ~128 tokens), pero `cuerpo_texto` de una nota completa puede ser mucho más largo. **Mitigación v0**: truncar al máximo de tokens del modelo (se pierde señal del final del cuerpo). Se documenta como limitación conocida — si el impacto SHAP de tono/polaridad sale plano, esto es sospechoso #1 antes de descartar la hipótesis NLP completa.
- [Riesgo] Backfill de HTML implica re-descargar 3,411 URLs por red — puede fallar parcialmente (sitio caído, URL removida, rate limit). **Mitigación**: reusa reintentos/índice de `scraper-reliability`; notas que no se puedan recuperar quedan excluidas (decisión 7), no bloquean el resto.
- [Riesgo] Nueva dependencia pesada (`pysentimiento` + `transformers`, descarga de pesos ~500MB desde HuggingFace Hub en la primera corrida) — requiere red la primera vez, incluso si la inferencia después es offline. **Mitigación**: documentar el requisito en README/COLABORACION; no bloquea Colab (ya tiene red).
- [Trade-off] Cache por `nota_id`+hash de texto agrega un archivo más a `checkpoints/views_impact/` para mantener sincronizado con `notes_structured.parquet` — aceptable, mismo patrón que los artefactos de modelo ya cacheados ahí.

## Open Questions

- Si `polaridad_score`/`tono_*` salen con SHAP casi plano igual que las features de contenido actuales (`content-only-impact-model`), ¿confirma que el problema no es "falta NLP" sino algo más profundo (ej. el target `views_7d` está dominado por factores fuera del control editorial — autor/canal/timing) y no queda más palanca de features barata por probar?
- ¿Vale la pena, si tono/polaridad sí aporta señal, extender el mismo pipeline de NLP a las ~11,377 URLs nuevas de `expand-url-source-csv` antes de scrapearlas solo por features estructurales?
