# Shannon Model — Google Colab

Guia para clonar el repo en Colab, cargar datos, **extraer** features de notas y correr los pipelines reales (impacto en vistas + reporte editorial).

> El notebook `notebooks/colab_train.ipynb` por defecto solo corre el **train sintetico** (`scripts/train.py` + `configs/default.yaml`). Eso valida GPU/PyTorch; **no** usa notas reales. Para vistas/receta seguí esta guia.

## Orden recomendado

```
1. Runtime → GPU
2. Clonar repo + pip install
3. Montar Drive y copiar datos a data/raw y data/processed
4. (Opcional) Extract / scrape
5. train_views_model + report_editorial_opportunities
6. (Opcional) Copiar checkpoints de vuelta a Drive
```

---

## 1. Clonar e instalar

```python
REPO_URL = "https://github.com/isaacgrimaldovo/shannon_model.git"
BRANCH = "main"
REPO_DIR = "shannon_model"

# Repo privado: Secret GITHUB_TOKEN en Colab (icono llave)
# from google.colab import userdata
# TOKEN = userdata.get("GITHUB_TOKEN")
# REPO_URL = f"https://{TOKEN}@github.com/isaacgrimaldovo/shannon_model.git"

import os
from pathlib import Path

# Clonar en /content (evita shannon_model/shannon_model anidado)
%cd /content
if Path(REPO_DIR).exists():
    %cd {REPO_DIR}
    !git fetch origin
    !git checkout {BRANCH}
    !git pull origin {BRANCH}
else:
    !git clone --branch {BRANCH} {REPO_URL} {REPO_DIR}
    %cd {REPO_DIR}

!pip install -q -r requirements.txt

import sys
sys.path.insert(0, str(Path("src").resolve()))
print("cwd:", os.getcwd())
```

Secrets y convenciones de equipo: ver `docs/COLABORACION.md`.

---

## 2. Layout de datos (gitignored)

Los datos **no** viven en git. En Colab hay que copiarlos (Drive recomendado).

| Path | Contenido | Rol |
|------|-----------|-----|
| `data/raw/csv_urls/` | CSVs diarios Marfeel/Analytics | Target `views_7d` |
| `data/raw/html/` | HTML scrapeado por nota | Input del extract / reprocess |
| `data/raw/scrape_index.csv` | Estado del scraper | Resume / reprocess |
| `data/raw/ehm_3months_filtered.xlsx` | Lista URL + folder | Fetch nuevo / categorias |
| `data/processed/notes_structured.parquet` | Features estructuradas | Train views + receta |

Ejemplo en Drive (una sola vez desde tu PC):

```
MyDrive/shannon_model_data/
  raw/
    csv_urls/
    html/                    # opcional si vas a reprocess o scrape
    scrape_index.csv         # opcional
    ehm_3months_filtered.xlsx
  processed/
    notes_structured.parquet # si ya extrajiste en local, alcanza con esto + csv_urls
```

Copiar a la raiz del repo clonado:

```python
from google.colab import drive
drive.mount("/content/drive")

SRC = "/content/drive/MyDrive/shannon_model_data"
!mkdir -p data/raw data/processed
!cp -r {SRC}/raw/csv_urls data/raw/
!cp {SRC}/processed/notes_structured.parquet data/processed/  # si ya existe

# Solo si vas a extract/reprocess:
# !cp -r {SRC}/raw/html data/raw/
# !cp {SRC}/raw/scrape_index.csv data/raw/
# !cp {SRC}/raw/ehm_3months_filtered.xlsx data/raw/
```

---

## 3. Extract (features desde HTML)

El entrypoint es `scripts/scrape_news.py`. El dataset estructurado se escribe en **`data/processed/notes_structured.parquet`** (default). HTML e indice quedan en `data/raw/`.

### 3a. Solo extract (reprocess) — recomendado si ya tenes `html/`

No pega al sitio; re-parsea HTML en disco.

```python
!python scripts/scrape_news.py --reprocess \
  --html-dir data/raw/html \
  --index-path data/raw/scrape_index.csv \
  --urls-xlsx data/raw/ehm_3months_filtered.xlsx \
  --structured-path data/processed/notes_structured.parquet
```

### 3b. Fetch + extract (bajar del sitio)

Lento (~horas si son miles de URLs). Proba primero con `--limit`.

```python
# Prueba
!python scripts/scrape_news.py --limit 50 --workers 2 \
  --urls-xlsx data/raw/ehm_3months_filtered.xlsx \
  --html-dir data/raw/html \
  --index-path data/raw/scrape_index.csv \
  --structured-path data/processed/notes_structured.parquet

# Corrida completa (sin --limit) cuando estes listo
# !python scripts/scrape_news.py --workers 2 ...
```

Flags utiles: `--delay` (segundos entre requests), `--max-attempts`, `--workers`.

---

## 4. Pipelines de negocio (views + editorial)

Requiere `data/processed/notes_structured.parquet` + `data/raw/csv_urls/`.

```python
# Modelo A/B de impacto en vistas + SHAP (+ por categoria)
!python scripts/train_views_model.py --config configs/views_impact.yaml

# Receta por seccion → cumplimiento → mayor oportunidad + KPIs
!python scripts/report_editorial_opportunities.py --config configs/editorial_opportunities.yaml
```

Salidas (gitignored):

- `checkpoints/views_impact/model.joblib`
- `checkpoints/views_impact/feature_impact.csv`
- `checkpoints/views_impact/feature_impact_by_category.csv`
- `checkpoints/editorial_opportunities/report.json`

Persistir en Drive:

```python
!mkdir -p /content/drive/MyDrive/shannon_model/checkpoints
!cp -r checkpoints/views_impact /content/drive/MyDrive/shannon_model/checkpoints/
!cp -r checkpoints/editorial_opportunities /content/drive/MyDrive/shannon_model/checkpoints/
!cp data/processed/notes_structured.parquet /content/drive/MyDrive/shannon_model_data/processed/
```

---

## 5. Train sintetico (smoke test)

Solo para validar stack Colab. **No** usa dataset real.

```python
from shannon_model.train import run_training
result = run_training("configs/default.yaml")
result
```

Esperado: `val_acc` ~0.5 y overfitting (datos random). Si ves eso, el pipeline CUDA/torch esta OK — no es el modelo editorial.

---

## Checklist rapido

| Objetivo | Datos minimos | Comando |
|----------|---------------|---------|
| Smoke CUDA | ninguno | `scripts/train.py` / `run_training` |
| Solo extract | `html/` + `scrape_index` + xlsx | `scrape_news.py --reprocess` |
| Scrapear de cero | xlsx de URLs | `scrape_news.py` (+ `--limit` al inicio) |
| Impacto vistas | parquet + `csv_urls/` | `train_views_model.py` |
| Receta / indice | parquet + `csv_urls/` | `report_editorial_opportunities.py` |

---

## Problemas frecuentes

- **`shannon_model/shannon_model` anidado**: clona desde `/content`, no desde dentro de otra carpeta con el mismo nombre.
- **Falta parquet / csv_urls**: el train de views falla o dataset vacio — volve a copiar desde Drive.
- **Runtime se reinicia**: `data/` y `checkpoints/` se pierden — remonta Drive y vuelve a copiar.
- **Confundir smoke train con modelo de noticias**: `configs/default.yaml` = sintetico; views = `configs/views_impact.yaml`.
