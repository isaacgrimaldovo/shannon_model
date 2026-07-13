# training-pipeline

## Purpose

Baseline de entrenamiento reproducible para validar el entorno (local y Colab) antes del dataset y arquitectura finales.

## Requirements

### Requirement: Entrenamiento local por CLI

El sistema SHALL permitir ejecutar un entrenamiento completo desde la raiz del repositorio con un archivo YAML de configuracion.

#### Scenario: Entrypoint por defecto
- GIVEN el repositorio clonado con dependencias instaladas
- WHEN el usuario ejecuta `python scripts/train.py --config configs/default.yaml`
- THEN el pipeline de entrenamiento termina sin error fatal
- AND se reporta un resultado de metricas (p. ej. loss/accuracy de validacion)

#### Scenario: Config YAML personalizada
- GIVEN un archivo `configs/exp_*.yaml` valido
- WHEN el usuario pasa `--config` apuntando a ese archivo
- THEN el entrenamiento usa los hiperparametros de ese YAML

### Requirement: Datos sinteticos de bootstrap

Mientras no exista dataset real, el pipeline SHALL poder entrenar con datos sinteticos generados en memoria para validar el flujo extremo a extremo.

#### Scenario: Bootstrap sin archivos en data/
- GIVEN `data/raw/` y `data/processed/` vacios (solo placeholders)
- WHEN se ejecuta el entrenamiento con la config por defecto
- THEN el sistema genera loaders sinteticos y completa al menos una epoca

### Requirement: Modelo baseline configurable

El sistema SHALL entrenar un modelo baseline (`ShannonBaseline` / MLP) cuyos hiperparametros principales (hidden size, dropout, epochs, batch size, learning rate) se lean desde la config YAML.

#### Scenario: Cambio de hiperparametro en YAML
- GIVEN `configs/default.yaml` con `train.epochs` modificado
- WHEN se ejecuta el entrenamiento
- THEN el numero de epocas ejecutadas coincide con el valor configurado

### Requirement: Checkpoints locales

El sistema SHALL guardar pesos/checkpoints bajo el directorio configurado (por defecto `checkpoints/`) y ese directorio MUST permanecer fuera del control de versiones de git.

#### Scenario: Persistencia de checkpoint
- GIVEN un entrenamiento que completa al menos una epoca con `save_every_epoch: true`
- WHEN termina una epoca
- THEN existe al menos un artefacto de checkpoint en el directorio configurado

### Requirement: Reproducibilidad por semilla

El sistema SHALL fijar la semilla aleatoria desde la configuracion para permitir corridas reproductibles del bootstrap.

#### Scenario: Semilla desde config
- GIVEN `seed: 42` en la config
- WHEN se inicia el entrenamiento
- THEN la semilla se aplica antes de generar datos y de inicializar el modelo
