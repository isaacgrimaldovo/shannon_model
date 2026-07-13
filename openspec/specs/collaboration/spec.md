# collaboration

## Purpose

Practicas de colaboracion en equipo via GitHub para shannon_model.

## Requirements

### Requirement: Flujo por ramas y PR

El equipo SHALL trabajar en ramas `feature/*` o `experiment/*` y mergear a `main` mediante pull request con al menos una revision.

#### Scenario: Cambio listo para main
- GIVEN un cambio de codigo o config en una rama de feature/experimento
- WHEN el autor abre un PR hacia `main`
- THEN al menos una persona del equipo revisa antes del merge

### Requirement: Secretos fuera del repositorio

Credenciales, tokens y `.env` MUST NOT versionarse. El repositorio SHALL proporcionar `.env.example` documentado sin secretos reales.

#### Scenario: Setup local de env
- GIVEN un clone fresco del repositorio
- WHEN un colaborador necesita variables de entorno
- THEN copia `.env.example` a `.env` y completa valores localmente
- AND `.env` permanece ignorado por git

### Requirement: Artefactos pesados no versionados

Datos crudos/procesados, checkpoints y runs de tracking MUST permanecer fuera de git (ignorados via `.gitignore`).

#### Scenario: Commit limpio
- GIVEN archivos en `data/raw/`, `data/processed/` o `checkpoints/`
- WHEN se ejecuta `git status`
- THEN esos contenidos no aparecen como tracked (salvo placeholders `.gitkeep`)

### Requirement: Hiperparametros en YAML versionables

Cambios experimentales de hiperparametros SHALL vivir en archivos YAML bajo `configs/` (p. ej. `configs/exp_*.yaml`) y documentarse en el PR.

#### Scenario: Nuevo experimento
- GIVEN un colaborador que prueba otro learning rate
- WHEN crea `configs/exp_lr_bajo.yaml` y abre PR
- THEN el PR incluye el YAML y un resumen breve de metricas/resultado

### Requirement: Documentacion de colaboracion

El repositorio SHALL mantener una guia de equipo (`docs/COLABORACION.md`) alineada con estas practicas.

#### Scenario: Onboarding
- GIVEN un nuevo colaborador
- WHEN lee `docs/COLABORACION.md` y el README
- THEN encuentra el flujo Git, manejo de secrets y convenciones de artefactos
