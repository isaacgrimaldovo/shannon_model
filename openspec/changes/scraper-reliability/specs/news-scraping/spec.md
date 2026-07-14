## MODIFIED Requirements

### Requirement: Índice idempotente url → nota_id
El sistema SHALL mantener un índice persistente que asocie cada URL a un `nota_id` estable, a su estado de scraping (`pending`, `ok`, `error`, `exhausted`) y a un conteo de intentos fallidos, de forma que correr el scraper múltiples veces sobre el mismo conjunto de URLs no vuelva a descargar ni duplicar notas ya obtenidas con éxito, y no reintente indefinidamente URLs que fallan de forma persistente.

#### Scenario: Re-ejecución sobre notas ya scrapeadas
- **WHEN** se ejecuta el scraper y una URL ya tiene `status: ok` en el índice
- **THEN** el scraper no vuelve a descargar esa URL
- **AND** no se genera un `nota_id` duplicado para la misma URL

#### Scenario: Re-ejecución sobre notas con error previo, por debajo del límite de intentos
- **WHEN** se ejecuta el scraper y una URL tiene `status: error` con un conteo de intentos menor al máximo configurado
- **THEN** el scraper reintenta la descarga de esa URL
- **AND** incrementa el conteo de intentos y actualiza su estado según el resultado del nuevo intento

#### Scenario: URL alcanza el máximo de intentos fallidos
- **WHEN** una URL falla y su conteo de intentos alcanza el máximo configurado (`max_attempts`)
- **THEN** el índice marca esa URL como `status: exhausted`
- **AND** corridas posteriores del scraper no vuelven a intentar esa URL ni la cuentan como pendiente

## ADDED Requirements

### Requirement: Ejecución concurrente respetando rate limiting por request
El sistema SHALL poder procesar múltiples URLs pendientes en paralelo mediante un pool de workers configurable, aplicando el mismo rate limiting (delay mínimo entre requests) de forma independiente por request, sin que la concurrencia lo viole.

#### Scenario: Corrida con concurrencia mayor a 1
- **WHEN** se ejecuta el scraper con un número de workers configurado mayor a 1
- **THEN** múltiples URLs se procesan simultáneamente
- **AND** el tiempo entre el inicio de dos requests HTTP consecutivas, medido por request individual, respeta el delay mínimo configurado

#### Scenario: Escritura concurrente del índice sin corrupción
- **WHEN** dos o más workers terminan de procesar URLs al mismo tiempo
- **THEN** las actualizaciones al índice persistente no se pisan ni corrompen entre sí
- **AND** el índice resultante refleja el estado final correcto de todas las URLs procesadas en esa corrida
