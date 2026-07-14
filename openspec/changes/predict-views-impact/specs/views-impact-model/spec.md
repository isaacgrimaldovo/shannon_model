## ADDED Requirements

### Requirement: Dataset de entrenamiento por combinación nota×canal con views_7d real
El sistema SHALL construir un dataset de entrenamiento con una fila por combinación única de nota y canal de distribución (`source`), uniendo `data/raw/notes_structured.parquet` con un target real `views_7d` calculado desde `data/raw/csv_urls/` (suma de `pageViewsTotal` de los 7 días posteriores a `fecha_publicacion`), e incluyendo `source` como feature categórica.

#### Scenario: Una nota con tráfico en múltiples canales genera múltiples filas
- **WHEN** una nota tiene `pageViewsTotal` > 0 en más de un `source` durante su ventana de 7 días (ej. Facebook y Google)
- **THEN** el dataset de entrenamiento incluye una fila por cada combinación url+source con tráfico, cada una con su propio target `log1p(views_7d de esa combinación)` y las mismas features estructurales de la nota

#### Scenario: Solo notas con views_7d completamente observable
- **WHEN** la ventana de 7 días posteriores a la publicación de una nota no cae completa dentro del rango de fechas trackeado por `data/raw/csv_urls/`
- **THEN** esa nota se excluye del dataset de entrenamiento, en vez de usar una suma parcial/censurada como si fuera `views_7d` completo

#### Scenario: source como feature categórica
- **WHEN** se construyen las features de entrada para el modelo
- **THEN** `source` se representa como one-hot (una columna por canal: Facebook, Google, Google Discover, dark social)

#### Scenario: Dataset parcial mientras el scraping continúa
- **WHEN** `notes_structured.parquet` contiene solo un subconjunto de las URLs totales (scraping en progreso)
- **THEN** el sistema construye el dataset de entrenamiento igual, usando únicamente las notas disponibles al momento de ejecutar

### Requirement: Modelo baseline de regresión sobre vistas
El sistema SHALL entrenar un modelo de regresión que prediga `views_7d` real a partir de las features estructurales disponibles (temporales, longitud de cuerpo y título, imágenes reales del cuerpo, etiquetas, categoría, autor, canal).

#### Scenario: Entrenamiento completa con métricas reportadas
- **WHEN** se ejecuta el entrenamiento sobre el dataset construido
- **THEN** el proceso termina sin error y reporta al menos una métrica de error de validación (ej. MAE en escala log)

#### Scenario: Features de autor sin one-hot
- **WHEN** se construyen las features de entrada para el modelo
- **THEN** el autor se representa mediante `autor_avg_views` y `autor_num_notas` derivadas, no mediante one-hot encoding directo de `autor_nombre`

#### Scenario: Conteo real de imágenes en vez de variantes del JSON-LD
- **WHEN** se construyen las features de entrada para el modelo
- **THEN** el modelo usa `num_imagenes_real` (conteo de imágenes del cuerpo) en vez de `num_imagenes`/`tiene_img_principal` (constantes, derivadas de variantes de la imagen hero del JSON-LD)

### Requirement: Evaluación por k-fold sin fuga de datos de autor
El sistema SHALL evaluar el modelo con validación cruzada de 5 particiones, recalculando `autor_avg_views` y `autor_num_notas` en cada partición usando únicamente las filas de entrenamiento de esa partición, y SHALL reportar las métricas de validación como media y desvío estándar entre las 5 particiones.

#### Scenario: Features de autor sin fuga entre particiones
- **WHEN** se calcula `autor_avg_views`/`autor_num_notas` para la partición de validación de un fold
- **THEN** esos valores se derivan exclusivamente de las filas de entrenamiento de ese mismo fold, no del dataset completo

#### Scenario: Métricas reportadas como media y desvío estándar
- **WHEN** termina la validación cruzada de 5 particiones
- **THEN** el sistema reporta MAE y R² como media ± desvío estándar entre los 5 folds, no como un único valor de un solo split

#### Scenario: Modelo final de explicación separado de la evaluación
- **WHEN** se genera el reporte de impacto de features (SHAP)
- **THEN** ese reporte usa un modelo entrenado sobre el 100% del dataset, no uno de los modelos entrenados durante la validación cruzada

#### Scenario: Sin fuga de la misma nota entre canales
- **WHEN** una nota tiene filas en el dataset para más de un `source`
- **THEN** todas las filas de esa nota (todas sus combinaciones url+source) quedan del mismo lado del split (todas en train o todas en validación) dentro de cada fold, nunca repartidas entre ambos

#### Scenario: Split temporal, no aleatorio
- **WHEN** se arma cada fold de la validación cruzada
- **THEN** todas las notas del fold de entrenamiento tienen `fecha_publicacion` anterior a todas las notas del fold de validación de ese mismo fold

### Requirement: Reporte de impacto de features vía SHAP
El sistema SHALL calcular valores SHAP sobre el modelo entrenado y reportar, por feature, el multiplicador de vistas equivalente (`exp(shap)`), en línea con la etapa "Resultados a editores" del diccionario de datos.

#### Scenario: Reporte de impacto generado tras el entrenamiento
- **WHEN** el entrenamiento del modelo baseline completa exitosamente
- **THEN** el sistema genera una tabla de impacto por feature con su multiplicador de vistas asociado
- **AND** esa tabla queda persistida junto al modelo entrenado, fuera de control de versiones
