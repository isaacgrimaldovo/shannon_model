## Context

`docs/COLAB.md` ya documenta el orden completo para correr el pipeline real (extract → views → editorial) en Colab, pero como celdas para copiar a mano. `notebooks/colab_train.ipynb` (trackeado) solo cubre train sintetico + su propio poll loop (`git pull` → filtro paths → `scripts/train.py`), implementado en el change `colab-git-poll-loop`. No existe un notebook versionado que ejecute el pipeline de negocio, y el usuario necesita verlo correr de punta a punta en Colab ahora, con los pasos rapidos (views + editorial) reaccionando solos a cada push.

## Goals / Non-Goals

**Goals:**
- Notebook nuevo y trackeado (`notebooks/colab_pipeline.ipynb`) que ejecute clone/install, mount Drive + copia de datos, extract (manual), `train_views_model.py`, `report_editorial_opportunities.py`, y copia de resultados a Drive — siguiendo el orden de `docs/COLAB.md`.
- Poll loop propio en este notebook, mismo patron que `colab_train.ipynb` (SHA tracking + `git diff --name-only` + filtro de paths), pero que dispare `train_views_model.py` + `report_editorial_opportunities.py` en vez de `scripts/train.py`.
- Extract queda fuera del poll loop: celda manual separada, documentado el porque (latencia + dependencia de red).

**Non-Goals:**
- No se toca `Shannon_EDA_y_Scraping_3.ipynb` ni se migra su motor de scraping/EDA a `src/shannon_model/`.
- No se modifica `notebooks/colab_train.ipynb` ni su poll loop existente (smoke train sintetico).
- No se agregan nuevos scripts ni flags — el notebook solo invoca `scripts/scrape_news.py`, `scripts/train_views_model.py`, `scripts/report_editorial_opportunities.py` tal como estan.
- No se automatiza el extract; sigue siendo decision manual del usuario cuando correrlo.

## Decisions

**Notebook separado en vez de extender `colab_train.ipynb`**: `docs/COLAB.md` ya distingue explicitamente "smoke train sintetico" de "pipeline real de negocio". Mezclar ambos flujos en un solo notebook obligaria a comentar/descomentar celdas segun el objetivo de la sesion. Alternativa considerada: agregar secciones al notebook existente — descartada porque duplicaria la logica de poll loop con distinto trigger action, complicando el toggle.

**Poll loop reutiliza el mismo patron (no una libreria compartida)**: el poll loop de `colab_train.ipynb` (`_current_sha`, comparacion de SHA, `subprocess`, `try/except KeyboardInterrupt`) se copia y adapta en `colab_pipeline.ipynb` cambiando solo el comando disparado. No se extrae a un modulo compartido en `src/` porque el poll loop es infraestructura de notebook (Colab-only), no logica de dominio — mantenerlo inline en cada notebook es consistente con "notebooks solo orquestan" y evita una dependencia cruzada entre dos notebooks independientes.

**Extract excluido del auto-trigger**: `scrape_news.py` fetch+extract puede tardar horas y depende de red/sitio externo. Disparar eso automaticamente ante cualquier push que toque `scripts/` (incluyendo un cambio a `train_views_model.py`) generaria corridas de scraping no deseadas. El filtro de paths ya distingue por carpeta pero no por archivo especifico dentro de `scripts/`; mantener extract 100% manual es mas simple y seguro que afinar el filtro a nivel de archivo.

**Datos asumidos pre-existentes para el poll loop**: el poll loop de views/editorial asume que `data/processed/notes_structured.parquet` y `data/raw/csv_urls/` ya fueron copiados (celda 2 del notebook, corrida una vez por sesion). Si faltan, el script fallara con su error existente (ya cubierto por `docs/COLAB.md` en "Problemas frecuentes") — el notebook no agrega validacion extra de precondiciones.

## Risks / Trade-offs

- **Runtime de Colab se reinicia** → se pierde `data/` y el estado del poll loop (SHA de referencia). Mitigacion: igual que `colab_train.ipynb`, el usuario debe re-montar Drive y re-copiar datos; el poll loop retoma desde el HEAD actual al reiniciar la celda.
- **Duplicacion de codigo de poll loop entre los dos notebooks** → mantenimiento manual si cambia el patron base. Mitigacion aceptada: bajo volumen de cambio esperado en ese patron, y mantiene cada notebook auto-contenido (sin imports cruzados entre notebooks).
- **Push que toca `scripts/scrape_news.py` no dispara nada util** (extract excluido, y ese archivo no afecta views/editorial) → el loop actualiza SHA y no corre nada, lo cual es el comportamiento esperado, pero puede sorprender si el usuario esperaba feedback. Mitigacion: log explicito de "motivo: cambio en extract, no se dispara pipeline automatico" en esa iteracion del loop.

## Open Questions

Ninguna pendiente — alcance y comportamiento confirmados con el usuario durante `/opsx:explore`.
