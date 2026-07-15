## ADDED Requirements

### Requirement: Persistencia del texto del cuerpo
El sistema SHALL persistir el texto plano del cuerpo de cada nota (`cuerpo_texto`) en `notes_structured.parquet`, extraído del mismo bloque HTML (`itemprop="articleBody"` o `div.texto-noticia`) que ya se usa para calcular `num_palabras`/`num_parrafos`.

#### Scenario: Extracción exitosa incluye el texto del cuerpo
- **WHEN** se extraen los campos de una nota cuyo HTML tiene un bloque de cuerpo reconocible
- **THEN** el resultado incluye `cuerpo_texto` con el texto plano del cuerpo (mismo texto usado para `num_palabras`), sin HTML ni scripts

#### Scenario: Cuerpo no reconocible
- **WHEN** el HTML de una nota no tiene ningún bloque de cuerpo reconocible (mismo caso que hoy da `num_palabras=0`)
- **THEN** `cuerpo_texto` es una cadena vacía, consistente con el resto de señales de cuerpo en ese caso

### Requirement: Backfill de HTML faltante para notas ya scrapeadas
El sistema SHALL poder re-descargar el HTML de URLs ya marcadas `ok` en el índice de scraping cuando el archivo HTML referenciado (`html_path`) ya no exista en disco, reusando el mismo `RateLimiter` y política de reintentos que el scraping normal, para poder re-extraer campos (incluyendo `cuerpo_texto`) sin perder el registro de qué ya se procesó exitosamente.

#### Scenario: HTML faltante se re-descarga
- **WHEN** se corre el backfill sobre una URL con estado `ok` en el índice cuyo `html_path` no existe en disco
- **THEN** el sistema vuelve a descargar el HTML de esa URL, lo guarda en `html_path`, re-extrae los campos (incluyendo `cuerpo_texto`) y actualiza la fila correspondiente en `notes_structured.parquet`

#### Scenario: HTML ya presente se omite
- **WHEN** se corre el backfill sobre una URL con estado `ok` cuyo `html_path` sí existe en disco
- **THEN** el sistema no vuelve a descargarla — reprocesa desde el HTML ya guardado (mismo comportamiento que `reprocess_existing`)

#### Scenario: Re-descarga falla
- **WHEN** el backfill intenta re-descargar una URL y la descarga falla (mismo criterio de reintentos/timeout que el scraping normal)
- **THEN** la fila existente en `notes_structured.parquet` para esa nota no se modifica, y el error queda registrado igual que un error de scraping normal
