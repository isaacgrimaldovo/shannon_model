## ADDED Requirements

### Requirement: Descarga de HTML crudo por nota
El sistema SHALL descargar el HTML completo de cada URL única listada en `data/raw/ehm_3months_filtered.xlsx` y persistirlo bajo `data/raw/html/`, un archivo por nota.

#### Scenario: Descarga exitosa
- **WHEN** se ejecuta el scraper sobre una URL válida y accesible
- **THEN** el HTML completo de la respuesta queda guardado en `data/raw/html/<nota_id>.html`
- **AND** el índice de scraping marca esa URL como `status: ok`

#### Scenario: URL inaccesible
- **WHEN** una URL responde con error HTTP (4xx/5xx) o timeout
- **THEN** el índice de scraping marca esa URL como `status: error` con el código o motivo del fallo
- **AND** el scraper continúa con las URLs restantes sin detenerse

### Requirement: Índice idempotente url → nota_id
El sistema SHALL mantener un índice persistente que asocie cada URL a un `nota_id` estable y a su estado de scraping (`pending`, `ok`, `error`), de forma que correr el scraper múltiples veces sobre el mismo conjunto de URLs no vuelva a descargar ni duplicar notas ya obtenidas con éxito.

#### Scenario: Re-ejecución sobre notas ya scrapeadas
- **WHEN** se ejecuta el scraper y una URL ya tiene `status: ok` en el índice
- **THEN** el scraper no vuelve a descargar esa URL
- **AND** no se genera un `nota_id` duplicado para la misma URL

#### Scenario: Re-ejecución sobre notas con error previo
- **WHEN** se ejecuta el scraper y una URL tiene `status: error` en el índice
- **THEN** el scraper reintenta la descarga de esa URL
- **AND** actualiza su estado según el resultado del nuevo intento

### Requirement: Extracción de campos estructurados de la etapa 1
El sistema SHALL extraer, a partir del HTML descargado, los campos de la etapa 1 del diccionario de datos (`titulo`, `autor_nombre`, `autor_slug`, `fecha_publicacion` y sus derivados temporales, `num_palabras`, `num_letras`, `largo_titulo`, `tiene_img_principal`, `num_imagenes`, `num_imagenes_real`, `num_etiquetas`, `categoria_nota`, `tiene_signo_pregunta`, `tiene_numero`, `tiene_mayusculas_excesivas`, `num_parrafos`, `tiene_subtitulos`, `tiene_video_embed`) y persistirlos en un dataset tabular bajo `data/raw/`.

#### Scenario: Nota con JSON-LD NewsArticle presente
- **WHEN** el HTML descargado contiene un bloque `application/ld+json` de tipo `NewsArticle`
- **THEN** el sistema extrae `titulo`, `autor_nombre`, `autor_slug`, `fecha_publicacion`, `num_imagenes` y `num_etiquetas` de ese bloque
- **AND** agrega una fila al dataset estructurado con esos campos más los derivados temporales calculados a partir de `fecha_publicacion`

#### Scenario: Conteo real de imágenes y longitud de texto desde el cuerpo
- **WHEN** el sistema parsea `div.texto-noticia` para calcular `num_palabras`
- **THEN** también calcula `num_letras` (caracteres del cuerpo) y `num_imagenes_real` (cantidad de tags `<img>` dentro de ese mismo nodo)
- **AND** calcula `largo_titulo` como la longitud en caracteres de `titulo`

#### Scenario: Señales de título y estructura del cuerpo
- **WHEN** el sistema parsea `titulo` y `div.texto-noticia`
- **THEN** calcula `tiene_signo_pregunta`, `tiene_numero` y `tiene_mayusculas_excesivas` a partir de `titulo`
- **AND** calcula `num_parrafos` (tags `<p>`) y `tiene_subtitulos` (tags `<h2>`/`<h3>`) dentro del cuerpo

#### Scenario: Detección de video embed por dominio, no por presencia de iframe
- **WHEN** el cuerpo contiene uno o más tags `<iframe>`
- **THEN** `tiene_video_embed` es 1 solo si el `src` de algún iframe contiene `youtube.com` o `facebook.com/plugins/video` (o hay un tag `<video>`)
- **AND** iframes de otros dominios (ej. slots de publicidad) no activan `tiene_video_embed`

#### Scenario: Nota sin JSON-LD NewsArticle
- **WHEN** el HTML descargado no contiene un bloque `application/ld+json` de tipo `NewsArticle` válido
- **THEN** el sistema registra esa nota como `status: error` en el índice con el motivo ("no JSON-LD found")
- **AND** no agrega una fila incompleta o inconsistente al dataset estructurado

#### Scenario: categoria_nota desde analytics existente
- **WHEN** se procesa una nota cuya URL aparece en `data/raw/ehm_3months_filtered.xlsx`
- **THEN** el campo `categoria_nota` del dataset estructurado se asigna directo desde la columna `folder` de ese archivo, sin requerir procesamiento NLP

### Requirement: Rate limiting en las requests de scraping
El sistema SHALL aplicar un delay configurable entre requests HTTP consecutivas al mismo dominio y SHALL identificar sus requests con un user-agent propio, evitando ráfagas de tráfico sin control hacia el sitio fuente.

#### Scenario: Corrida completa respeta el delay configurado
- **WHEN** se ejecuta el scraper con un delay configurado de N segundos
- **THEN** el tiempo entre el inicio de dos requests HTTP consecutivas es de al menos N segundos
