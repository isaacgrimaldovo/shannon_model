## 1. Loader de URLs desde csv_urls

- [x] 1.1 Implementar `load_url_folder_map_from_csv_urls(csv_urls_dir: Path) -> dict[str, str]` en `src/shannon_model/scraping/pipeline.py`, junto a `load_url_folder_map` existente (no la reemplaza)
- [x] 1.2 Excluir `ehm-90-google-economia.csv` y cualquier archivo `ehm_report-*.csv` del glob de entrada (mismo criterio que `dataset.py::_load_daily_views`)
- [x] 1.3 Filtrar filas con `date == "Total"` / equivalente artefacto de export si aplica al esquema leído (`usecols=["url", "folder"]` puede no necesitar la columna `date`; confirmar que no haga falta leerla para este propósito) — confirmado: la fila `"Total"` viene con `url`/`folder` vacíos, `dropna(subset=["url"])` la descarta sin leer `date`
- [x] 1.4 Deduplicar por `url` agrupando `folder`; si un grupo tiene más de un valor único de `folder`, lanzar `ValueError` con la URL y los valores en conflicto (decisión 2 de design.md)
- [x] 1.5 Normalizar `folder` igual que `load_url_folder_map` (`.str.strip("/")`) para mantener el mismo formato que consume `extract_note_fields`

## 2. Integración en ScrapeConfig / scripts/scrape_news.py

- [x] 2.1 Cambiar default de `--urls-xlsx` en `scripts/scrape_news.py` de `data/raw/ehm_3months_filtered.xlsx` a `data/raw/csv_urls`
- [x] 2.2 En `run_scrape` y `reprocess_existing` (`src/shannon_model/scraping/pipeline.py:149,237`), detectar si `config.urls_xlsx` apunta a un directorio (usar `load_url_folder_map_from_csv_urls`) o a un archivo (usar `load_url_folder_map` existente, para permitir pasar explícito el xlsx si hace falta) — vía helper `_load_url_folder_map`
- [x] 2.3 Actualizar el docstring/help del argumento `--urls-xlsx` para reflejar que ahora acepta un directorio de CSVs por default

## 3. Verificación

- [x] 3.1 Correr `load_url_folder_map_from_csv_urls("data/raw/csv_urls")` en una sesión local y confirmar el conteo total de URLs únicas y las 9 categorías (`folder`) presentes — **corrección del estimado de design.md**: 53,220 URLs únicas (no ~14,200 — ese número era el subset con `views_7d` completamente observable, no el total de URLs descubribles). Categorías: `deportes` 6101, `economia` 6908, `edicion-impresa` 7179, `espectaculos` 5000, `estilo-de-vida` 6892, `mundo` 5000, `nacional` 5000, `tecnologia` 3323, `tendencias` 7817
- [x] 3.2 Confirmar que `ehm-90-google-economia.csv` y `ehm_report-*.csv` no contribuyen URLs al resultado (comparar conteo con/sin esos archivos) — 7,784 URLs viven en esos 2 archivos, de las cuales 81 NO aparecen en ningún otro archivo de `csv_urls` y por lo tanto se pierden por la exclusión. Trade-off aceptado: mismo criterio ya usado por `dataset.py` para el target, consistente con decisión 14 de `predict-views-impact`; no es un problema nuevo introducido por este change
- [x] 3.3 Confirmar que ninguna URL dispara el error de `folder` inconsistente sobre el dataset real actual — corrida completa sobre las 53,220 URLs no lanzó `ValueError`, sin conflictos de `folder` en los datos reales
- [x] 3.4 Correr `scripts/scrape_news.py --limit 5` (sin flags de xlsx, usando el nuevo default) y confirmar que toma URLs del set expandido de `csv_urls` (no las 3,408 del xlsx viejo) y que el índice/dataset estructurado se actualizan igual que antes — confirmado: `{'total_urls': 53220, 'processed': 5, 'ok': 5, 'error': 0}`, índice pasó de 3,409 a 3,414 filas con URLs nuevas de `deportes`/`tendencias` (categorías que no existían en el xlsx viejo)
- [x] 3.5 Confirmar que pasar explícito `--urls-xlsx data/raw/ehm_3months_filtered.xlsx` sigue funcionando (compatibilidad hacia atrás del path viejo) — **no verificable end-to-end en este entorno**: el archivo xlsx nunca se copió a este clone local (se trae de Drive en Colab, ver `docs/COLAB.md`). Verificado por lectura de código: el branching nuevo (`_load_url_folder_map`) solo agrega un chequeo `is_dir()` antes de delegar, sin tocar `load_url_folder_map` — el mismo comportamiento (y el mismo error si el archivo no existe) que antes de este change
