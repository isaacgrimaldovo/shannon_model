## ADDED Requirements

### Requirement: Limpieza y normalización de reportes de analytics
El sistema SHALL limpiar los reportes crudos de analytics antes de cualquier análisis: eliminar filas de "Total" del footer del export, convertir `pageViewsTotal` a numérico, parsear fechas de publicación y de reporte, y distinguir filas de landing page (sección) de filas de nota real.

#### Scenario: Filtrado de fila de Total del footer
- **WHEN** un archivo de reporte trae una fila cuya columna `date` es "Total" (case-insensitive)
- **THEN** esa fila se excluye del dataset limpio

#### Scenario: Filas con fecha de reporte anterior a la publicación
- **WHEN** una fila de nota (no landing) tiene `fecha_reporte` anterior a `publishDate`
- **THEN** esa fila se excluye del dataset limpio por ser ruido del cruce de datos del export
- **AND** el sistema reporta cuántas filas se excluyeron y cuántas de ellas tenían vistas distintas de cero

#### Scenario: Distinción landing page vs nota
- **WHEN** el campo `publishDate` de una fila es `"-"`
- **THEN** esa fila se marca como landing page (`es_landing=True`), no como nota individual

### Requirement: Reporte de calidad y cobertura de datos
El sistema SHALL reportar, sobre el dataset ya limpio: rango de fechas de publicación y de reporte, filas por fuente de tráfico, filas por archivo de origen, porcentaje de valores faltantes en campos clave (`url`, `categoria`, `publishDate`, `articulo_id`), y URLs que aparecen repetidas en más de un archivo de origen.

#### Scenario: Detección de URLs repetidas entre archivos
- **WHEN** se agregan las filas por `url`
- **THEN** el reporte indica cuántas URLs únicas aparecen en más de un archivo CSV de origen

### Requirement: Reporte de distribución de vistas
El sistema SHALL reportar estadísticos descriptivos de `pageViews_total` por nota única, y el porcentaje de vistas totales concentrado en el 10% de notas más vistas (long-tail).

#### Scenario: Cálculo de concentración long-tail
- **WHEN** se ordenan las notas únicas por `pageViews_total` descendente
- **THEN** el sistema calcula qué porcentaje del total de vistas corresponde al top 10% de notas

### Requirement: Reporte por sección y patrones temporales
El sistema SHALL reportar cantidad de notas y vistas totales/promedio agrupadas por `categoria`, y vistas promedio agrupadas por hora de publicación y por día de la semana.

#### Scenario: Agregación por sección
- **WHEN** se agrupan las notas únicas por `categoria`
- **THEN** el reporte incluye cantidad de notas, vistas totales y vistas promedio por nota, por cada sección

### Requirement: Top notas y notas sin vistas
El sistema SHALL reportar las N notas con más vistas y la cantidad/porcentaje de notas con `pageViews_total` igual a cero.

#### Scenario: Notas con cero vistas
- **WHEN** se calcula `pageViews_total` por nota única
- **THEN** el reporte indica cuántas notas (y qué porcentaje del total) tienen exactamente 0 vistas registradas

### Requirement: Resumen ejecutivo persistido
El sistema SHALL generar un resumen ejecutivo en texto plano con las métricas clave del EDA (archivos cargados, filas totales/limpias, URLs únicas, rango de fechas, sección con más vistas, concentración long-tail, notas sin vistas) y persistirlo en disco.

#### Scenario: Resumen se guarda en cada corrida
- **WHEN** el reporte termina de ejecutarse
- **THEN** el resumen ejecutivo se escribe a un archivo de texto en el directorio de salida configurado, sobrescribiendo el de la corrida anterior
