## Why

`scripts/scrape_news.py` sigue tomando la lista de URLs a scrapear desde `data/raw/ehm_3months_filtered.xlsx` (3,408 URLs, 6 categorías), mientras `data/raw/csv_urls/` — mismo esquema `url/folder/source/date/pageViewsTotal`, ~14,200 URLs únicas, 9 categorías — ya reemplazó al xlsx como fuente del target real `views_7d` en `predict-views-impact` (decisión 14), pero nunca como fuente de descubrimiento de URLs. Resolver esto responde a la open question ya anotada en `predict-views-impact/design.md:97`: habilita expandir el dataset de entrenamiento de ~2,823 a ~14,200 notas con target limpio.

## What Changes

- Nuevo loader `load_url_folder_map_from_csv_urls` (o similar) que deriva lista única `(url, folder)` desde `data/raw/csv_urls/*.csv`, para reemplazar `load_url_folder_map(urls_xlsx)` (`src/shannon_model/scraping/pipeline.py:74`) como fuente real del scraper.
- Reusa el mismo criterio de exclusión de archivos ya validado en `dataset.py::_load_daily_views` (`src/shannon_model/impact_model/dataset.py:45-59`): descarta fila `"Total"`, excluye `ehm-90-google-economia.csv` (formato viejo, sin `date` diaria) y `ehm_report-*.csv` (duplicado del proxy viejo).
- Regla de desambiguación de `folder` por URL: si la misma URL aparece con `folder` distinto entre archivos/fuentes, falla explícito (no silencioso) — mismo principio que el resto del pipeline (errores trazables, no aproximados).
- `scripts/scrape_news.py --urls-xlsx` cambia su default para apuntar al nuevo loader basado en `data/raw/csv_urls/`. **BREAKING**: el xlsx deja de ser el input real del scraper; sigue existiendo en disco pero ya no es la fuente activa.
- No dispara la corrida de scraping de las ~11,377 URLs nuevas — este change entrega el mecanismo únicamente; correr el scraping masivo queda como decisión/task separada.
- No toca `docs/COLAB.md`, `notebooks/colab_pipeline.ipynb` ni `scripts/data_quality_report.py`.

## Capabilities

### New Capabilities
(ninguna)

### Modified Capabilities
- `news-scraping`: el requirement de origen de URLs (hoy: "el sistema SHALL descargar el HTML completo de cada URL única listada en `data/raw/ehm_3months_filtered.xlsx`") cambia su fuente a `data/raw/csv_urls/`. Nota: `news-scraping` es la capability de `scrape-news-content` (aún no sincronizada a `openspec/specs/`); este change agrega su propio delta sobre la misma capability.

## Impact

- `src/shannon_model/scraping/pipeline.py`: nuevo loader de URLs, `ScrapeConfig` deja de depender exclusivamente de un xlsx.
- `scripts/scrape_news.py`: cambia default de `--urls-xlsx`.
- Sin impacto en `src/shannon_model/impact_model/dataset.py` (ya usa `csv_urls` para el target, no se toca).
- Sin impacto en docs/notebook de Colab (fuera de alcance explícito).
- Volumen: el índice de scraping (`data/raw/scrape_index.csv`) pasa a poder crecer de 3,408 a ~14,200 URLs candidatas (la corrida real queda fuera de este change).

## Fuera de alcance

- Actualizar `docs/COLAB.md`, `notebooks/colab_pipeline.ipynb`, `scripts/data_quality_report.py`.
- Correr el scraping masivo de las URLs nuevas.
- Cambiar la lógica de `categoria_nota` más allá de tomar el `folder` correcto (mismo criterio, solo cambia la fuente de datos).
- Deprecar o eliminar `ehm_3months_filtered.xlsx` del repo.
