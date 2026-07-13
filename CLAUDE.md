# shannon_model

Entrenamiento de modelo ML reproducible (local + Google Colab) con colaboración en GitHub.

## Stack

- Python >= 3.10, PyTorch, YAML configs
- Package: `src/shannon_model/`
- Entrypoint: `python scripts/train.py --config configs/default.yaml`
- Colab: `notebooks/colab_train.ipynb`
- Estado: datos sintéticos + MLP baseline (`ShannonBaseline`)

## Comandos

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/train.py --config configs/default.yaml
```

OpenSpec (terminal):

```bash
openspec list
openspec show <change>
openspec validate --all
openspec doctor
```

## Doc-first

Antes de implementar o configurar stack: consultar docs oficiales (no improvisar APIs deprecadas).

Referencias:

- OpenSpec: https://github.com/Fission-AI/OpenSpec
- PyTorch training: https://pytorch.org/tutorials/
- Colab: https://colab.research.google.com/

## OpenSpec / SDD

Siempre `/opsx:propose` (o explore → propose) antes de features nuevas.

Flujo core:

1. `/opsx:explore` (opcional)
2. `/opsx:propose <nombre>`
3. Revisar artefacts en `openspec/changes/<nombre>/`
4. `/opsx:apply` (Claude Code) / implementar según `tasks.md`
5. `/opsx:sync` si hace falta mergear specs sin archivar
6. `/opsx:archive` al cerrar

Roles: Cursor planifica/revisa artefacts; Claude Code aplica con `/opsx:apply`.

## Caveman

- Claude Code: plugin `caveman` (auto)
- Cursor: skills en `.agents/skills/` + regla `.cursor/rules/caveman.mdc`
- Localizar código → investigator / explore
- Fix ≤2 archivos → builder / edición directa
- Review diff → reviewer / `/caveman-review`
- Feature 3+ archivos o nueva → hilo principal + `/opsx:propose`

## Estructura clave

```
openspec/specs/     # verdad actual
openspec/changes/   # propuestas activas
configs/            # hiperparámetros YAML
src/shannon_model/  # código
notebooks/          # Colab orquesta
docs/COLABORACION.md
```

## Convenciones

- Código aplicación: inglés (nombres, docsstrings, logs)
- Docs / OpenSpec / chat equipo: español
- No commitear `.env`, datos crudos, checkpoints
