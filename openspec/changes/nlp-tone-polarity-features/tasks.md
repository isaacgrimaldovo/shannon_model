## 1. Persistir cuerpo del texto en el scraper

- [x] 1.1 En `src/shannon_model/scraping/extract.py`, `body_stats()` retorna también `cuerpo_texto` (el mismo `text` ya calculado, sin cambiar ninguna de las señales existentes)
- [x] 1.2 Agregar `cuerpo_texto` a `STRUCTURED_COLUMNS` en `src/shannon_model/scraping/pipeline.py`

## 2. Backfill de HTML faltante

- [x] 2.1 En `src/shannon_model/scraping/pipeline.py`, agregar `backfill_missing_html(config: ScrapeConfig) -> dict[str, int]`: itera filas `status=ok` del índice, si `html_path` no existe en disco re-descarga (mismo `RateLimiter`/`fetch_html`/reintentos que `run_scrape`) y re-extrae con `extract_note_fields`; si `html_path` sí existe, reprocesa desde disco (mismo criterio que `reprocess_existing`)
- [x] 2.2 Actualizar `notes_structured.parquet` por nota backfillada (misma lógica de `drop_duplicates(subset="nota_id", keep="last")` que ya usa `run_scrape`/`reprocess_existing`)
- [x] 2.3 Agregar flag `--backfill-html` a `scripts/scrape_news.py` que llama a `backfill_missing_html`
- [ ] 2.4 Correr el backfill sobre las 3,411 URLs reales y confirmar cuántas quedaron con `cuerpo_texto` no vacío vs. cuántas fallaron (documentar el conteo en el resumen de la corrida)

## 3. Dependencia y módulo de scoring NLP

- [x] 3.1 Agregar `pysentimiento` a `requirements.txt`
- [x] 3.2 Nuevo módulo `src/shannon_model/impact_model/nlp_tone.py` con función `score_tone(texts: pd.Series) -> pd.DataFrame` que carga el analizador de sentiment (`pysentimiento.create_analyzer(task="sentiment", lang="es")`) una sola vez y devuelve por fila: `tono` (POS/NEG/NEU), `polaridad_score` (`P(POS) − P(NEG)`)
- [x] 3.3 Truncar `cuerpo_texto` al máximo de tokens soportado por el modelo antes de inferir (documentar el límite usado) — el tokenizer de `robertuito-sentiment-analysis` trunca automáticamente a `model_max_length=128` (confirmado localmente), documentado en `nlp_tone.py` y `configs/views_impact.yaml::nlp_tone.max_length`

## 4. Cache de resultados NLP

- [x] 4.1 En `nlp_tone.py`, agregar `load_or_compute_tone(df: pd.DataFrame, cache_path: Path) -> pd.DataFrame`: lee `checkpoints/views_impact/nlp_tone_cache.parquet` si existe, calcula tono/polaridad solo para `nota_id` nuevos o con `cuerpo_texto` cambiado (hash simple), persiste el cache actualizado
- [x] 4.2 Agregar ruta de cache a `configs/views_impact.yaml` (sección nueva, ej. `nlp_tone.cache_path`, `nlp_tone.model_name`)

## 5. Integrar features al dataset de impacto

- [x] 5.1 En `src/shannon_model/impact_model/dataset.py`, `build_base_frame` (modelo A) y `build_content_frame` (modelo B) hacen join de `cuerpo_texto` (desde `notes_structured.parquet`) con el resultado de `load_or_compute_tone`, agregando `polaridad_score` y one-hot `tono_POS`/`tono_NEG`/`tono_NEU` al frame
- [x] 5.2 `polaridad_score` agregado a `FEATURE_COLUMNS` (continuo, mismo trato que `num_palabras` etc). `tono_POS`/`tono_NEG`/`tono_NEU` se agregan como dummies dinámicos vía `pd.get_dummies`, mismo patrón que `categoria_*`/`source_*` (no literales en `FEATURE_COLUMNS`, que nunca lista dummies existentes tampoco)
- [x] 5.3 Notas con `cuerpo_texto` vacío (backfill fallido) se excluyen del dataset de entrenamiento vía `dropna(subset=[..., "polaridad_score", ...])` — filtro explícito, no imputación

## 6. Verificación

- [ ] 6.1 Correr `python scripts/train_views_model.py --config configs/views_impact.yaml` con las features nuevas sobre modelo A y modelo B, confirmar que entrena sin error
- [ ] 6.2 Reportar en el resumen (o `design.md`, sección Resultados) el R² con vs. sin features de tono/polaridad para ambos modelos, y dónde caen `tono_*`/`polaridad_score` en la tabla de impacto SHAP — la pregunta que motiva el change
- [ ] 6.3 Confirmar que ninguna feature/target/CV existente cambió de comportamiento (mismo criterio de no-regresión que `compare-gbr-vs-random-forest`)
- [ ] 6.4 `openspec validate --all` pasa sin errores
