## ADDED Requirements

### Requirement: Definición de es_breaking sobre granularidad día-1
El sistema SHALL definir `es_breaking` como `zscore_views_dia1 > 2.0`, donde `zscore_views_dia1` es el z-score de las vistas acumuladas durante el día 1 posterior a la publicación de una nota, calculado sobre la distribución de ese valor en el conjunto de notas disponible. El sistema NO SHALL depender de `views_1h`/`zscore_views_1h`, columnas eliminadas del diccionario de datos y no calculables con la granularidad diaria de la fuente de analytics actual.

#### Scenario: Nota con vistas día-1 muy por encima del promedio
- **WHEN** las vistas del día 1 de una nota superan en más de 2 desvíos estándar el promedio de vistas día-1 del conjunto de notas
- **THEN** `es_breaking` se marca como verdadero para esa nota

#### Scenario: Ventana de día 1 no observable completa
- **WHEN** la ventana de 24 horas posteriores a la publicación de una nota no cae completa dentro del rango de fechas trackeado por la fuente de analytics
- **THEN** `es_breaking` para esa nota se marca como no calculable (valor faltante), no como falso por defecto

#### Scenario: views_1h no se reintroduce
- **WHEN** se documenta o implementa cualquier feature relacionada a `es_breaking`
- **THEN** ninguna columna o cálculo depende de `views_1h`/`zscore_views_1h`
