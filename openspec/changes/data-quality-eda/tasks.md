## 1. Carga y limpieza

- [x] 1.1 Crear `src/shannon_model/analytics_eda/load.py` con `find_csv_files(folder)` (sin `glob`, igual patrón que `_buscar_csv` del notebook) y `load_reports(source)` que acepta xlsx único o carpeta de CSVs
- [x] 1.2 `load_reports` valida `COLUMNAS_MINIMAS` por archivo y devuelve `(df_concatenado, resumen_de_carga)`, marcando archivos "OMITIDO"/"ERROR" sin abortar la corrida completa
- [x] 1.3 Crear `src/shannon_model/analytics_eda/clean.py` con `clean_reports(df)`: quita filas "Total" del footer, convierte `pageViewsTotal` a numérico, parsea `publishDate`/`date`, marca `es_landing`
- [x] 1.4 `clean_reports` descarta filas con `fecha_reporte < publishDate` (excluyendo landings) y devuelve conteo de filas descartadas + cuántas tenían vistas > 0

## 2. Reporte de calidad y cobertura

- [x] 2.1 Crear `src/shannon_model/analytics_eda/report.py` con `quality_report(df)`: rango de fechas, filas por fuente, filas por archivo de origen, % de faltantes en `url`/`categoria`/`publishDate`/`articulo_id`
- [x] 2.2 `quality_report` detecta URLs únicas presentes en más de un archivo de origen

## 3. Distribución de vistas, sección y patrones temporales

- [x] 3.1 `views_distribution(vistas_por_url)`: `describe()` + % de vistas concentrado en el top 10% de notas
- [x] 3.2 `section_report(vistas_por_url)`: notas y vistas totales/promedio por `categoria`
- [x] 3.3 `temporal_report(vistas_por_url)`: vistas promedio por hora de publicación y por día de la semana

## 4. Top notas y resumen ejecutivo

- [x] 4.1 `top_notes(vistas_por_url, n=15)` y conteo/porcentaje de notas con `pageViews_total == 0`
- [x] 4.2 `build_summary(...)`: arma dict con todas las métricas de 1-4 (para tests) y su representación en texto plano
- [x] 4.3 `save_summary(summary, output_dir)`: persiste el resumen ejecutivo en texto en el directorio de salida

## 5. CLI y verificación

- [x] 5.1 Crear `scripts/data_quality_report.py` (args: `--source`, `--output-dir`) que orquesta carga → limpieza → reportes → resumen
- [x] 5.2 Correr el script sobre `data/raw/ehm_3months_filtered.xlsx` y comparar cifras clave (URLs únicas, rango de fechas, top 15) contra las que muestra el notebook — el notebook corrió contra "reportes Marfeel" completo (29 CSVs, 7.2M filas, 53,157 URLs únicas), no contra este xlsx (3,408 URLs), así que no hay match numérico 1:1 esperado. Validación cruzada lograda: la nota #1 en vistas (`no-tires-los-paraguas-rotos...`, 625,399 vistas) coincide en ambos — mismo orden por vistas descendente, misma lógica de agregación. **Hallazgo relevante**: el xlsx actual es ~15x más chico que los reportes Marfeel completos (3,408 vs 53,157 URLs) — confirma la open question de design.md sobre si Marfeel reemplaza al xlsx, con más urgencia de lo esperado
- [x] 5.3 `openspec validate --all` pasa sin errores
