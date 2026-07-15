"""Entrenamiento del modelo final (RandomForestRegressor) de impacto en vistas.

La evaluación de generalización vive en `cv.py` (5-fold fold-safe). Este módulo solo
entrena el modelo que se usa para el reporte SHAP, con fit sobre el 100% del dataset
(decisión 9 de design.md: son dos modelos con propósitos distintos).
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from shannon_model.impact_model.dataset import TARGET_COLUMN


def fit_final_model(
    df: pd.DataFrame, seed: int, model_params: dict[str, Any], model_cls: type = RandomForestRegressor
) -> Any:
    feature_cols = [c for c in df.columns if c != TARGET_COLUMN]
    model = model_cls(random_state=seed, **model_params)
    model.fit(df[feature_cols], df[TARGET_COLUMN])
    return model
