## 1. Notebook base — clone, drive, datos

- [x] 1.1 Crear `notebooks/colab_pipeline.ipynb` con celda markdown de intro (referencia a `docs/COLAB.md` como fuente de detalle, orden de ejecucion, distincion vs `colab_train.ipynb`)
- [x] 1.2 Celda de clone/install (`REPO_URL`, `BRANCH`, `REPO_DIR`, `git clone`/`pull`, `pip install -r requirements.txt`, `sys.path.insert` a `src/`) — mismo patron que `colab_train.ipynb`
- [x] 1.3 Celda de mount Drive + copia de datos a `data/raw/` y `data/processed/` (siguiendo layout de `docs/COLAB.md` seccion 2)

## 2. Extract (manual)

- [x] 2.1 Celda markdown explicando que extract es manual (lento / depende de red) y no forma parte del poll loop
- [x] 2.2 Celda de extract con toggle `REPROCESS_ONLY = True/False`: `True` invoca `scripts/scrape_news.py --reprocess` (usa `html/` ya bajado), `False` invoca fetch+extract con `--limit` configurable

## 3. Pipelines de negocio

- [x] 3.1 Celda que invoca `scripts/train_views_model.py --config configs/views_impact.yaml`
- [x] 3.2 Celda que invoca `scripts/report_editorial_opportunities.py --config configs/editorial_opportunities.yaml`
- [x] 3.3 Celda de copia de resultados a Drive (`checkpoints/views_impact/`, `checkpoints/editorial_opportunities/`, `data/processed/notes_structured.parquet`)

## 4. Poll loop acotado a views + editorial

- [x] 4.1 Celda markdown explicando el flujo del poll loop (push a `src/`/`scripts/`/`configs/` -> Colab detecta -> corre views+editorial; extract queda fuera)
- [x] 4.2 Celda de codigo con poll loop: `git pull`, comparar SHA de HEAD contra ultimo SHA corrido, `poll_interval` configurable (mismo patron que `colab_train.ipynb`)
- [x] 4.3 Filtro de paths (`git diff --name-only <sha_anterior> <sha_nuevo>` contra `src/`, `scripts/`, `configs/`) — si aprueba, disparar `train_views_model.py` + `report_editorial_opportunities.py` (nunca `scrape_news.py`)
- [x] 4.4 Loguear cada iteracion: SHA detectado, si disparo run o no, motivo (path filtrado / sin cambios / run ejecutado)
- [x] 4.5 Envolver el loop en `try/except KeyboardInterrupt` para terminar limpio ante "Interrupt execution" de Colab sin dejar `subprocess` colgado

## 5. Verificacion manual

- [ ] 5.1 Correr el notebook completo en Colab de punta a punta (clone -> drive -> extract manual -> views -> editorial) con datos reales y confirmar que genera `checkpoints/views_impact/model.joblib`, `checkpoints/views_impact/feature_impact.csv` y `checkpoints/editorial_opportunities/report.json`
- [ ] 5.2 Con el poll loop corriendo, hacer push local que toque `configs/views_impact.yaml` y confirmar que dispara `train_views_model.py` + `report_editorial_opportunities.py` dentro del intervalo de poll, sin ejecutar `scrape_news.py`
- [ ] 5.3 Hacer push que solo toque `docs/` o `README.md` y confirmar que el loop NO dispara ningun run
- [ ] 5.4 Interrumpir el loop manualmente desde Colab y confirmar que corta sin dejar proceso colgado ni traceback confuso
