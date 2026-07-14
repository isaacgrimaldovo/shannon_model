## Why

El notebook `Shannon_EDA_y_Scraping_3.ipynb` de un compañero incluye un EDA sobre `data/raw/ehm_3months_filtered.xlsx` (limpieza, calidad de datos, distribución de vistas, patrones temporales, long-tail) que hoy solo vive como celdas de notebook, sin equivalente reusable en `src/`. Esto es análisis exploratorio real y valioso, pero no reproducible fuera del notebook, no versionado como código, y desconectado del resto del pipeline (`scrape-news-content`, `predict-views-impact`) que ya corre como scripts + módulos.

## What Changes

- Nuevo módulo/script que reproduce el EDA del notebook como código ejecutable: limpieza y normalización de reportes de analytics (footer "Total", filas "imposibles" con fecha de reporte anterior a publicación, distinción landing pages vs notas), y las métricas de calidad/cobertura (rango de fechas, % faltantes, URLs repetidas entre archivos de origen).
- Reporte de distribución de vistas: estadísticos descriptivos, histograma (recortado a percentil 99) y en log1p, % de vistas concentrado en el top 10% de notas (long-tail).
- Reporte por sección: cantidad de notas y vistas totales/promedio por `categoria`.
- Reporte temporal: vistas promedio por hora de publicación y por día de la semana.
- Top N notas más vistas y conteo de notas con 0 vistas registradas.
- Resumen ejecutivo en texto plano (`resumen_eda.txt`), igual al que ya genera el notebook.
- Se asume el mismo esquema de entrada (`url, folder, source, publishDate, publishTime, date, pageViewsTotal`, más columnas de reportes Marfeel) — no se resuelve acá si esta fuente reemplaza o complementa `ehm_3months_filtered.xlsx`.

## Capabilities

### New Capabilities
- `analytics-data-quality`: limpieza, validación de calidad/cobertura y reporte exploratorio (distribución de vistas, patrones temporales, long-tail, resumen por sección) sobre los reportes de analytics crudos, como script reusable en `src/`.

### Modified Capabilities
(ninguna)

## Impact

- Código nuevo: módulo `src/shannon_model/analytics_eda/` (o similar) + script CLI `scripts/data_quality_report.py`.
- Sin dependencias nuevas: usa `pandas`/`matplotlib`, ya presentes en el proyecto.
- Datos: consume `data/raw/ehm_3months_filtered.xlsx` (o carpeta de reportes CSV, a confirmar). Produce reporte/resumen bajo un directorio de salida no versionado (ej. `checkpoints/eda/` o `data/raw/eda/`).
- Sin impacto en `scraping/` ni `impact_model/` — es una capability paralela e independiente, aunque puede alimentar decisiones futuras de ambos (ej. detectar URLs repetidas o notas con 0 vistas antes de entrenar).
