## Context

`cv.py` hoy tiene `RandomForestRegressor` hardcodeado en 3 lugares: `cross_validate` (modelo A), `cross_validate_content_model` (modelo B), y `pipeline.py::run_content_only_pipeline` (fit final del modelo B). `train.py::fit_final_model` (fit final del modelo A) también lo hardcodea. Los cuatro comparten la misma estructura: instanciar `RandomForestRegressor(random_state=seed, **model_params)`, fit, predict/evaluar. Cambiar de algoritmo hoy implicaría duplicar las 4 funciones solo para cambiar una línea de instanciación en cada una.

`configs/views_impact.yaml` ya tiene precedente de secciones paralelas por modelo (`cv.param_grid` para A, `content_model.param_grid` para B) — el patrón para agregar GBR es extender ese mismo esquema, no inventar uno nuevo.

## Goals / Non-Goals

**Goals:**
- Entrenar y evaluar GBR sobre modelo A y modelo B con el mismo dataset/CV/target que RandomForest, para tener una comparación de R² apples-to-apples.
- Reusar `cross_validate`/`cross_validate_content_model`/`grid_search_cv`/`grid_search_content_model`/`fit_final_model` sin duplicarlas — parametrizar el estimador, no reescribir la lógica de CV.
- Persistir artefactos de GBR separados de los de RandomForest (ambos algoritmos conviven, nada se sobreescribe).

**Non-Goals:**
- No se decide todavía si GBR reemplaza a RandomForest en producción — eso es una decisión posterior, con los R² de ambos ya en mano.
- No se prueban XGBoost/LightGBM (dependencia nueva, fuera de alcance de este change).
- No se cambian features, target, dataset ni esquema de CV — solo el estimador.
- No se agrega early stopping ni tuning fino de GBR más allá del grid explícito en config (ej. no se usa `n_iter_no_change`) — mantenerlo comparable en complejidad al grid actual de RandomForest.

## Decisions

**1. Parametrizar el estimador con un argumento `model_cls` (default `RandomForestRegressor`) en vez de duplicar las funciones de CV/fit.**
`cross_validate`, `cross_validate_content_model`, `grid_search_cv`, `grid_search_content_model` y `fit_final_model` reciben un nuevo parámetro `model_cls: type` con default `RandomForestRegressor` — el comportamiento actual (llamadas existentes sin ese argumento) no cambia. Internamente, `model = model_cls(random_state=seed, **model_params)` reemplaza la instanciación hardcodeada.
Alternativa descartada: crear `cross_validate_gbr`/`cross_validate_content_model_gbr` como funciones espejo. Se descarta porque duplicaría 100% de la lógica de CV fold-safe (incluyendo el manejo de `fit_author_stats`/`apply_author_stats` del modelo A) solo para cambiar una línea — cualquier fix futuro al esquema de CV tendría que aplicarse dos veces.

**2. `run_pipeline`/`run_content_only_pipeline` reciben `model_cls` y `artifact_suffix` (default `RandomForestRegressor`, `""`), en vez de nuevas funciones `run_gbr_pipeline`.**
Mismo criterio que la decisión 1: la orquestación (dataset → grid search → fit final → impact table → persistir) es idéntica entre algoritmos, solo cambian el estimador y el nombre de archivo de salida. `artifact_suffix` se inserta antes de la extensión (`model.joblib` → `model_gbr.joblib`, `feature_impact.csv` → `feature_impact_gbr.csv`, etc.).
Alternativa descartada: funciones separadas por algoritmo — mismo problema de duplicación que la decisión 1, y además duplicaría el manejo de paths de artefactos.

**3. Grid de hiperparámetros de GBR en secciones nuevas del mismo `views_impact.yaml`: `gbr_model.param_grid` (modelo A) y `content_gbr_model.param_grid` (modelo B).**
Seguir el patrón ya establecido (`cv.param_grid` / `content_model.param_grid`) en vez de un YAML separado — no fragmentar la config de algo que se corre junto. Los hiperparámetros de GBR son distintos a los de RandomForest (`learning_rate`, `subsample`, sin `min_samples_leaf` obligatorio), así que necesitan su propia sección, no reusar `cv.param_grid`.

**4. `scripts/train_views_model.py` corre los 4 pipelines (RF-A, RF-B, GBR-A, GBR-B) y los reporta en una sola tabla comparativa (R² mean±std, MAE mean±std por combinación).**
Permite ver de un vistazo si GBR mueve la aguja en A, en B, en ninguno o en ambos — la pregunta que motiva el change (¿el techo es del algoritmo o de las features?) se responde directamente de esa tabla.

**5. `ImpactModelConfig` gana dos campos nuevos: `gbr_param_grid` y `content_gbr_param_grid` (mismo patrón que `param_grid`/`content_model_param_grid` existentes).**
Consistente con cómo ya se cargan los grids de RandomForest desde YAML a la dataclass — no se introduce un mecanismo de config distinto para GBR.

## Risks / Trade-offs

- [Riesgo] Si GBR da R² similar o peor que RandomForest en ambos modelos, confirma que el techo es de las features (no del algoritmo) — empuja a features NLP/texto como siguiente paso. Se documenta como resultado esperado a reportar, no como fallo del change.
- [Trade-off] `GradientBoostingRegressor` de scikit-learn no soporta paralelización nativa (`n_jobs`) como `RandomForestRegressor` — el grid search de GBR puede tardar más en correr. Aceptable: el dataset es chico (miles de notas, no millones) y el grid es acotado (mismo orden de magnitud que el de RandomForest).
- [Riesgo] Agregar `model_cls` como parámetro con default cambia la firma pública de 5 funciones (`cross_validate`, `cross_validate_content_model`, `grid_search_cv`, `grid_search_content_model`, `fit_final_model`). Mitigación: default preserva el comportamiento actual exacto, ninguna llamada existente (modelo A/B actuales) necesita cambiar.

## Resultados

Corrida completa (`python scripts/train_views_model.py --config configs/views_impact.yaml`, dataset modelo A: 5,002 filas nota×source, modelo B: 2,828 notas):

| Combinación | R² mean±std | MAE (log) mean±std |
|---|---|---|
| RandomForest — modelo A | 0.4476±0.0842 | 1.0877±0.0482 |
| RandomForest — modelo B | 0.5852±0.0555 | 0.8737±0.0496 |
| GradientBoosting — modelo A | 0.3959±0.0928 | 1.1318±0.0460 |
| GradientBoosting — modelo B | 0.5324±0.0653 | 0.9288±0.0274 |

**GBR pierde contra RandomForest en ambos modelos** (R² menor y MAE mayor en A y en B, con el grid de hiperparámetros de la decisión 3). Se confirma el riesgo documentado arriba: el techo no es del algoritmo, es de las features disponibles — RandomForest sigue siendo el modelo vigente, GBR no se promueve a producción. Empuja a evaluar NLP/texto (`tono`, `polaridad`, `categoria_titulo`, tier 2 pendiente en `predict-views-impact`) como próxima palanca, no a seguir iterando sobre algoritmos de árbol.

Verificación de no-regresión en RandomForest (task 5.2): se corrió el código pre-change (`git stash`) sobre el mismo dataset de hoy y se comparó contra la corrida post-change — resultados idénticos byte a byte (mismo `r2_mean`, mismo SHAP por feature). El diff inicial contra los artefactos ya versionados en `checkpoints/views_impact/` (generados en una corrida anterior) se debía a drift de datos (apareció una categoría `deportes` nueva con 20 notas que no existía en esa corrida vieja), no a un efecto del cambio de código.

## Open Questions

- Si GBR mejora R² claramente en modelo A o B, ¿vale la pena correr un grid más amplio antes de decidir migrar a producción, o alcanza con esta comparación inicial para justificar una iteración posterior dedicada a GBR? Se resuelve con los resultados de este change en mano.
- **Resuelta**: GBR no mejora en ninguno de los dos modelos (ver Resultados) — no aplica correr un grid más amplio, el algoritmo no es la palanca. Foco pasa a features NLP.
