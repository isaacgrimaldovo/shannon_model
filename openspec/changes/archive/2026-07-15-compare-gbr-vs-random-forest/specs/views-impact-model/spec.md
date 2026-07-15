## ADDED Requirements

### Requirement: Comparación de algoritmos alternativos (GradientBoostingRegressor) sobre modelo A y modelo B
El sistema SHALL entrenar y evaluar `GradientBoostingRegressor` sobre el mismo dataset, features, target y esquema de validación cruzada que el modelo A (`RandomForestRegressor`, dataset nota×source) y el modelo B (`RandomForestRegressor`, dataset a nivel nota, content-only), sin modificar el dataset, las features, el target ni el algoritmo vigente de ninguno de los dos modelos.

#### Scenario: Mismo dataset y features que el modelo vigente
- **WHEN** se entrena la variante GBR del modelo A o del modelo B
- **THEN** usa exactamente el mismo dataset de entrada, las mismas columnas de features y el mismo target (`log1p(views_7d)`) que la variante `RandomForestRegressor` correspondiente

#### Scenario: Mismo esquema de validación cruzada
- **WHEN** se evalúa la variante GBR del modelo A
- **THEN** usa `TimeSeriesSplit` sobre notas ordenadas por fecha con `fit_author_stats`/`apply_author_stats` recalculados por fold, igual que la variante RandomForest del modelo A

#### Scenario: Modelos RandomForest existentes no cambian
- **WHEN** se agrega la variante GBR de modelo A y modelo B
- **THEN** los artefactos existentes de RandomForest (`model.joblib`, `model_content_only.joblib`, `feature_impact.csv`, `feature_impact_content_only.csv` y sus versiones `_by_category`) siguen generándose exactamente igual que antes, sin sobrescribirse

### Requirement: Artefactos de GBR persistidos por separado
El sistema SHALL persistir los artefactos de la variante GBR (modelo entrenado y tablas de impacto SHAP, global y por categoría) en archivos separados de los de RandomForest, para el modelo A y el modelo B.

#### Scenario: Nombres de archivo distintos por algoritmo
- **WHEN** termina el entrenamiento de la variante GBR del modelo A
- **THEN** persiste `model_gbr.joblib`, `feature_impact_gbr.csv` y `feature_impact_gbr_by_category.csv`, sin sobrescribir los artefactos de RandomForest

#### Scenario: Mismo patrón para modelo B
- **WHEN** termina el entrenamiento de la variante GBR del modelo B
- **THEN** persiste `model_content_only_gbr.joblib`, `feature_impact_content_only_gbr.csv` y `feature_impact_content_only_gbr_by_category.csv`, sin sobrescribir los artefactos de RandomForest del modelo B

### Requirement: Reporte comparativo de R² entre algoritmos
El sistema SHALL reportar, en una misma corrida de entrenamiento, el R² (media ± desvío estándar entre folds) de las cuatro combinaciones algoritmo×modelo (RandomForest-A, RandomForest-B, GBR-A, GBR-B), para permitir comparar si un algoritmo alternativo mejora el resultado sobre las mismas features.

#### Scenario: Tabla comparativa en la salida del script de entrenamiento
- **WHEN** `scripts/train_views_model.py` termina de correr los cuatro pipelines
- **THEN** muestra el R² mean±std de cada combinación algoritmo×modelo, identificando claramente cuál es cuál
