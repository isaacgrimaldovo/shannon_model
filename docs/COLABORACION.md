# Shannon Model - Colaboracion en equipo

## Flujo Git recomendado

1. Trabaja siempre en una rama propia: feature/corto o experiment/nombre.
2. No subas datos grandes, checkpoints ni archivos .env.
3. Abre un PR hacia main cuando el cambio este listo para revisar.
4. Al menos una persona del equipo revisa el PR antes de merge.

## Secrets

- Copia .env.example a .env (solo local).
- En Colab, usa Secrets (icono llave). No dejes tokens en notebooks versionados.
- Repos privados: Personal Access Token con minimo privilegio.

## Artefactos

- Checkpoints: carpeta checkpoints/ (gitignored) o Google Drive.
- Datos: `data/raw/` (html, csv_urls, scrape_index) y `data/processed/` (notes_structured.parquet) — gitignored.
- Resultados de experimento: resume metricas y config en el PR.

## Colab

Pasos de clone, Drive, extract/scrape y trains reales: ver **`docs/COLAB.md`**.

## Convenciones

- Codigo Python en src/shannon_model/.
- Notebooks solo orquestan (setup + CLIs); la logica vive en src/scripts.
- Cambios de hiperparametros en configs/ con un YAML nuevo.
