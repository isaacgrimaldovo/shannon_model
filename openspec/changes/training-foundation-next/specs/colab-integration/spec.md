# Delta for colab-integration

## ADDED Requirements

### Requirement: Acceso a dataset real desde Colab

Cuando el dataset real dependa de Drive u otra fuente remota, el notebook Colab SHALL documentar las celdas necesarias para montar o descargar esos datos antes de invocar el entrypoint de entrenamiento.

#### Scenario: Preparacion de datos en Colab
- GIVEN un dataset real cuya fuente esta documentada (p. ej. Drive)
- WHEN el usuario sigue las celdas del notebook
- THEN los datos quedan accesibles en la ruta esperada por la config
- AND el entrenamiento se lanza con el mismo `scripts/train.py`
