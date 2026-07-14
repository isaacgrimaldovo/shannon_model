## ADDED Requirements

### Requirement: Modelo de impacto solo con features accionables (modelo B)
El sistema SHALL entrenar un segundo modelo de regresión (`RandomForestRegressor`) usando exclusivamente las features accionables (`feature_kinds.ACTIONABLE_FEATURES`) más `categoria_nota` como contexto, excluyendo `autor_avg_views`, `autor_num_notas` y `source_*`, para aislar la señal de contenido del efecto de autor/canal.

#### Scenario: Entrenamiento a nivel nota, no nota×canal
- **WHEN** se construye el dataset de entrenamiento del modelo B
- **THEN** cada nota aparece una sola vez (target = `views_7d` real sumado entre todos sus canales), no una fila por combinación nota×source

#### Scenario: Sin features de autor ni canal
- **WHEN** se entrena o evalúa el modelo B
- **THEN** ninguna columna `autor_*` ni `source_*` está presente entre sus features de entrada

#### Scenario: Modelo A no se modifica
- **WHEN** se agrega el modelo B
- **THEN** el modelo A (features completas, dataset nota×source) y sus artefactos existentes (`model.joblib`, `feature_impact.csv`, `feature_impact_by_category.csv`) siguen generándose exactamente igual que antes

### Requirement: Validación cruzada temporal sin ajuste de estadísticas de autor
El sistema SHALL evaluar el modelo B con `TimeSeriesSplit` sobre las notas ordenadas por fecha de publicación, sin recalcular estadísticas de autor por fold (no aplica, autor no es feature del modelo B).

#### Scenario: CV reporta media y desvío estándar
- **WHEN** termina la validación cruzada del modelo B
- **THEN** el sistema reporta MAE y R² como media ± desvío estándar entre los folds, mismo formato que el modelo A

### Requirement: Reporte de impacto SHAP del modelo B, global y por categoría
El sistema SHALL generar, para el modelo B, una tabla de impacto SHAP global y una desglosada por `categoria_nota`, reusando la misma lógica de `build_impact_table`/`build_impact_table_by_category` ya usada para el modelo A.

#### Scenario: Reporte persistido en artefactos separados del modelo A
- **WHEN** el entrenamiento del modelo B completa exitosamente
- **THEN** sus tablas de impacto (global y por categoría) quedan persistidas en archivos separados de los del modelo A, sin sobrescribirlos
