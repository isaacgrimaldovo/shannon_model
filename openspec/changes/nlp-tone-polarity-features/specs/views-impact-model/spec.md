## ADDED Requirements

### Requirement: Features de tono y polaridad sobre el cuerpo de la nota
El sistema SHALL calcular tono (categórico: positivo/negativo/neutral) y polaridad (score continuo) del texto del cuerpo de cada nota (`cuerpo_texto`), usando un modelo de análisis de sentiment pre-entrenado en español, y agregarlos como features del dataset de entrenamiento de los modelos A y B, sin modificar ninguna feature, target ni esquema de CV existente.

#### Scenario: Nota con cuerpo disponible
- **WHEN** una nota tiene `cuerpo_texto` no vacío
- **THEN** el dataset incluye para esa fila `polaridad_score` (continuo, `P(POS) − P(NEG)` del modelo) y el one-hot `tono_POS`/`tono_NEG`/`tono_NEU` correspondiente a la clase de mayor probabilidad

#### Scenario: Nota sin cuerpo disponible
- **WHEN** una nota no tiene `cuerpo_texto` (vacío, o todavía no pasó por el backfill de `news-scraping`)
- **THEN** esa nota se excluye del dataset de entrenamiento en vez de imputar un tono/polaridad arbitrario — mismo criterio que el resto del pipeline (fallar explícito, no aproximar)

### Requirement: Resultados de tono/polaridad cacheados en disco
El sistema SHALL cachear en disco el resultado de tono/polaridad por nota (keyed por `nota_id`), para no re-ejecutar la inferencia del modelo de sentiment en cada corrida de entrenamiento.

#### Scenario: Cache hit
- **WHEN** se entrena el dataset y ya existe un cache con el resultado de tono/polaridad para una nota cuyo `cuerpo_texto` no cambió
- **THEN** se reusa el valor cacheado en vez de volver a correr el modelo de sentiment sobre esa nota

#### Scenario: Cache miss (nota nueva o cuerpo actualizado)
- **WHEN** una nota no tiene entrada en el cache, o su `cuerpo_texto` cambió respecto a lo cacheado
- **THEN** se corre el modelo de sentiment sobre esa nota y se actualiza el cache con el resultado nuevo
