## ADDED Requirements

### Requirement: Deteccion automatica de cambios via poll de git

El notebook Colab SHALL incluir un loop que haga `git pull` periodicamente y dispare el entrenamiento (`scripts/train.py`) automaticamente cuando detecte un commit nuevo cuyo diff toque paths relevantes (`src/`, `scripts/`, `configs/`), sin requerir que el usuario re-ejecute manualmente la celda de entrenamiento.

#### Scenario: Push local con cambio relevante dispara run automatico
- **WHEN** el usuario hace commit y push local de un cambio que toca `src/`, `scripts/` o `configs/`, y el loop de poll ya esta corriendo en Colab
- **THEN** dentro del intervalo de poll configurado, el loop detecta el commit nuevo via `git pull` y dispara `scripts/train.py` con la config vigente

#### Scenario: Cambio irrelevante no dispara run
- **WHEN** el commit nuevo detectado solo toca paths fuera de `src/`, `scripts/` y `configs/` (por ejemplo `README.md` o `docs/`)
- **THEN** el loop actualiza el SHA de referencia pero no dispara un nuevo entrenamiento

#### Scenario: Interrupcion manual corta el loop de forma limpia
- **WHEN** el usuario presiona "Interrupt execution" en Colab mientras el loop esta corriendo
- **THEN** el loop captura la interrupcion y termina sin dejar el proceso de entrenamiento en un estado colgado
