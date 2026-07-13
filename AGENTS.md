# AGENTS.md

Guia breve para agentes (Cursor / Claude Code) en shannon_model.

## Antes de codigo de app

1. Leer `CLAUDE.md` y `openspec/config.yaml`.
2. Features nuevas: `/opsx:propose` — no implementar sin change OpenSpec.
3. Cursor: planificar/revisar artefacts. Claude Code: `/opsx:apply`.

## Dominios spec actuales

- `openspec/specs/training-pipeline/`
- `openspec/specs/colab-integration/`
- `openspec/specs/collaboration/`

## Change activa de ejemplo

`openspec/changes/training-foundation-next/` — dataset real, arquitectura final, tracking opcional.

## No hacer

- Commits salvo pedido explicito del usuario
- Subir secrets, datos o checkpoints
- Reescribir logica de train sin delta spec aprobada
