# Delta for training-pipeline

## ADDED Requirements

### Requirement: Fuente de datos configurable

El sistema SHALL permitir seleccionar la fuente de datos desde la configuracion YAML, incluyendo al menos el modo sintetico de bootstrap y un modo de dataset real acordado por el equipo.

#### Scenario: Default sigue siendo sintetico
- GIVEN una config sin fuente real configurada (o `data.source: synthetic`)
- WHEN se ejecuta el entrenamiento
- THEN se usan loaders sinteticos y el run completa sin requerir archivos en `data/raw`

#### Scenario: Dataset real local
- GIVEN `data.source` apunta al modo real y existen archivos validos en la ruta configurada
- WHEN se ejecuta el entrenamiento
- THEN el pipeline carga el dataset real y produce loaders de train/val

### Requirement: Seleccion de arquitectura por config

El sistema SHALL seleccionar la arquitectura del modelo segun un identificador en la config (p. ej. `model.name`), sin exigir cambios en el entrypoint CLI.

#### Scenario: Baseline por nombre
- GIVEN `model.name` corresponde al baseline MLP
- WHEN se inicia el entrenamiento
- THEN se instancia `ShannonBaseline` (o equivalente registrado)

#### Scenario: Arquitectura final por nombre
- GIVEN `model.name` corresponde a la arquitectura final registrada
- WHEN se inicia el entrenamiento
- THEN se instancia esa arquitectura con hiperparametros del YAML

### Requirement: Experiment tracking opcional

El sistema SHALL soportar logging de experimentos a un backend externo de forma opcional. Un entrenamiento MUST completarse con exito sin tracker configurado.

#### Scenario: Run sin tracker
- GIVEN no hay API key ni flag de tracking habilitado
- WHEN termina el entrenamiento
- THEN el proceso sale con exito y reporta metricas en consola (o log local)

#### Scenario: Run con tracker habilitado
- GIVEN las variables/config de tracking estan presentes y validas
- WHEN corre el entrenamiento
- THEN se registran al menos config del run y metricas de validacion en el backend
