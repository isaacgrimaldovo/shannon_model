# colab-integration

## Purpose

Integracion con Google Colab para que el equipo ejecute el mismo pipeline de entrenamiento que en local.

## Requirements

### Requirement: Notebook de orquestacion

El repositorio SHALL incluir un notebook Colab que orqueste clonado/instalacion y delegue el entrenamiento al entrypoint de Python del proyecto (no reimplementar el loop de train dentro del notebook).

#### Scenario: Pipeline via notebook
- GIVEN acceso a Google Colab y al repositorio en GitHub
- WHEN el usuario ejecuta las celdas de `notebooks/colab_train.ipynb` en orden
- THEN se instalan dependencias del proyecto
- AND se invoca el mismo flujo de entrenamiento (`scripts/train.py` / `run_training`)

### Requirement: Misma fuente de verdad de codigo

El entrenamiento en Colab MUST usar el codigo versionado en el repositorio (clon o sync), no una copia divergente del loop de entrenamiento.

#### Scenario: Codigo desde repo
- GIVEN el notebook tras clonar `isaacgrimaldovo/shannon_model`
- WHEN se inicia el entrenamiento
- THEN el codigo ejecutado proviene de `src/shannon_model/` del clone

### Requirement: Artefactos fuera de git en Colab

Los checkpoints y datos generados en Colab SHALL guardarse en rutas locales del runtime (y opcionalmente Drive) y MUST NOT versionarse en git.

#### Scenario: Checkpoints en runtime
- GIVEN un entrenamiento completo en Colab
- WHEN finaliza el run
- THEN los pesos quedan bajo `checkpoints/` (o ruta Drive configurada en el notebook)
- AND no se anaden automaticamente al repositorio remoto
