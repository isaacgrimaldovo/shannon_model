## 1. Documentación de la decisión

- [ ] 1.1 Actualizar `docs/FEATURES_BACKLOG.md` (Tier 3) reemplazando `views_1h`/`es_breaking` por la definición día-1, con nota de que `views_1h`/`zscore_views_1h` no existen en el diccionario actualizado
- [ ] 1.2 Marcar la open question correspondiente en `openspec/changes/predict-views-impact/design.md` como resuelta (referenciar este change)

## 2. Cálculo (si el equipo decide incorporarlo ya al modelo)

- [ ] 2.1 Confirmar con el equipo si `es_breaking` se incorpora como feature en esta iteración o queda solo documentado (ver Open Questions de design.md)
- [ ] 2.2 Si se incorpora: agregar cálculo de `zscore_views_dia1` a `src/shannon_model/impact_model/dataset.py`, a partir de `data/raw/csv_urls/` (vistas del día 1 posterior a `fecha_publicacion`)
- [ ] 2.3 Si se incorpora: notas sin ventana día-1 completa quedan con `es_breaking` como valor faltante (no `False`), mismo criterio que `views_7d`
- [ ] 2.4 Si se incorpora: agregar `es_breaking` a `FEATURE_COLUMNS` y verificar que aparece en la tabla de impacto SHAP

## 3. Verificación

- [ ] 3.1 `openspec validate --all` pasa sin errores
- [ ] 3.2 Si se incorporó el cálculo: correr sobre una muestra de notas con ventana día-1 completa y confirmar que el z-score se calcula sobre esa muestra, no sobre notas con ventana incompleta
