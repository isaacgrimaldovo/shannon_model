## Context

El notebook del compañero (`Shannon_EDA_y_Scraping_3.ipynb`, secciones 3-5) implementa limpieza y EDA sobre reportes de analytics ("reportes Marfeel", carpeta de CSVs con columnas mínimas `url, folder, source, publishDate, publishTime, date, pageViewsTotal`) que hoy no existe como código reusable — vive solo en celdas ejecutadas manualmente en Colab. `scrape-news-content` y `predict-views-impact` ya usan `data/raw/ehm_3months_filtered.xlsx` (mismo tipo de datos, formato xlsx en vez de carpeta de CSVs) como fuente de analytics.

Este change no resuelve si "reportes Marfeel" reemplaza `ehm_3months_filtered.xlsx` — eso es una decisión de datos pendiente de confirmar con el equipo. Se diseña el reporte para aceptar cualquiera de los dos como input, mientras el esquema de columnas mínimo se respete.

## Goals / Non-Goals

**Goals:**
- Portar la lógica de limpieza y EDA del notebook a un módulo/script reusable, testeable y ejecutable fuera de Colab.
- Mantener las mismas métricas y reporte ejecutivo que ya produce el notebook, para que sea un reemplazo directo (no una reinterpretación).
- Aceptar como input tanto un xlsx único como una carpeta de CSVs (reportes Marfeel), reutilizando la lógica de carga tolerante a errores del notebook (`_buscar_csv`/`cargar_reportes_marfeel`).

**Non-Goals:**
- No decide si "reportes Marfeel" reemplaza `ehm_3months_filtered.xlsx` como fuente de verdad del resto del pipeline.
- No genera gráficos como artefactos persistidos (PNG) en esta iteración — el notebook los muestra inline; acá basta con las tablas/números del reporte. Graficar queda como mejora futura si se necesita para un dashboard.
- No integra este reporte al CLI de scraping ni al de `impact_model` — corre independiente.

## Decisions

**1. Módulo `src/shannon_model/analytics_eda/` con funciones puras + script CLI fino.**
Mismo patrón que `scraping/` e `impact_model/`: lógica testeable en el módulo (`clean.py`, `report.py`), CLI (`scripts/data_quality_report.py`) que solo parsea args y llama al módulo.

**2. Carga de reportes: reutilizar patrón `_buscar_csv` (sin `glob`) del notebook.**
El notebook documenta que rutas de Drive con corchetes (ej. `"[2] Desarrollo"`) rompen `glob` porque `[2]` se interpreta como character class. Se porta la misma lógica (`os.listdir`/`os.walk` con comparación literal de extensión) en vez de usar `glob`, para que el módulo funcione igual en Drive/Colab si se necesita ahí también.

**3. Filas "fecha de reporte anterior a publicación" se descartan con conteo reportado, no silenciosamente.**
Mismo criterio que el notebook: es ruido del cruce de datos de Marfeel, casi siempre con 0 vistas, pero se cuenta cuántas filas se descartan y cuántas tenían vistas > 0, para que quede auditable si el patrón cambia con datos nuevos.

**4. Reporte devuelve un objeto estructurado (dict/dataclass) además de imprimir texto.**
El notebook solo imprime/muestra en celdas. Acá conviene que la función principal devuelva un dict con todas las métricas (no solo texto), para poder testearlo con asserts y para que otros scripts (ej. un futuro dashboard) lo consuman sin parsear texto.

**5. Sin gráficos persistidos en esta iteración.**
Generar y guardar PNGs agrega superficie (backend de matplotlib sin display en CI, paths de salida adicionales) sin necesidad clara todavía — el consumo hoy es interactivo (notebook) o de números (reporte). Se deja como Open Question / mejora futura.

## Risks / Trade-offs

- [Riesgo] Esquema de "reportes Marfeel" (carpeta CSV) puede diferir del xlsx único en columnas exactas más allá de las mínimas documentadas → **Mitigación**: el loader solo exige `COLUMNAS_MINIMAS`, igual que el notebook; columnas extra se ignoran, columnas faltantes producen archivo "OMITIDO" en vez de crash.
- [Trade-off] No hay gráficos persistidos → reporte es menos visual que el notebook original. Aceptable porque el objetivo es tener las métricas como código reusable/testeable, no reemplazar el notebook como herramienta de exploración visual.

## Open Questions

- ¿"Reportes Marfeel" (carpeta CSV) reemplaza `ehm_3months_filtered.xlsx` como fuente de analytics del pipeline completo, o son datasets distintos/complementarios? No bloquea este change (el loader acepta ambos formatos), pero sí a `scrape-news-content`/`predict-views-impact` si cambia la fuente de verdad.
- ¿Vale la pena, en una iteración futura, persistir los gráficos como PNG para un reporte no interactivo (ej. CI o dashboard)?
