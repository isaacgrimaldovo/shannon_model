## MODIFIED Requirements

### Requirement: Descarga de HTML crudo por nota
El sistema SHALL descargar el HTML completo de cada URL única listada en `data/raw/csv_urls/` y persistirlo bajo `data/raw/html/`, un archivo por nota.

#### Scenario: Descarga exitosa
- **WHEN** se ejecuta el scraper sobre una URL válida y accesible
- **THEN** el HTML completo de la respuesta queda guardado en `data/raw/html/<nota_id>.html`
- **AND** el índice de scraping marca esa URL como `status: ok`

#### Scenario: URL inaccesible
- **WHEN** una URL responde con error HTTP (4xx/5xx) o timeout
- **THEN** el índice de scraping marca esa URL como `status: error` con el código o motivo del fallo
- **AND** el scraper continúa con las URLs restantes sin detenerse

#### Scenario: Deduplicación de URLs entre archivos CSV
- **WHEN** la misma URL aparece en más de un archivo de `data/raw/csv_urls/` (distintas fuentes o fechas)
- **THEN** el sistema la trata como una sola entrada en la lista de URLs a scrapear, sin duplicar el trabajo

#### Scenario: Archivos de analytics excluidos de la lista de URLs
- **WHEN** el sistema construye la lista de URLs desde `data/raw/csv_urls/`
- **THEN** excluye `ehm-90-google-economia.csv` (formato viejo, redundante con `ehm-90-google-economia_II.csv`) y cualquier archivo `ehm_report-*.csv` (duplicado del proxy viejo)
- **AND** excluye la fila `"Total"` que cada archivo trae al final (artefacto de export de Analytics)

#### Scenario: Folder inconsistente para la misma URL
- **WHEN** la misma URL aparece con un valor de `folder` distinto en dos archivos o filas de `data/raw/csv_urls/`
- **THEN** el sistema falla explícito para esa URL (no aproxima ni descarta la inconsistencia en silencio)

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
- **WHEN** se procesa una nota cuya URL aparece en `data/raw/csv_urls/`
- **THEN** el campo `categoria_nota` del dataset estructurado se asigna directo desde la columna `folder` de esos archivos, sin requerir procesamiento NLP
