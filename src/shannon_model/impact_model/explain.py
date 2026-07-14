"""Reporte de impacto de features vía SHAP, en escala de multiplicador de vistas."""

from __future__ import annotations

import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestRegressor


def build_impact_table(model: RandomForestRegressor, x_train: pd.DataFrame) -> pd.DataFrame:
    """SHAP promedio por feature convertido a multiplicador de vistas (exp(shap))."""
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(x_train)

    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    mean_shap = shap_values.mean(axis=0)

    table = pd.DataFrame(
        {
            "feature": x_train.columns,
            "mean_abs_shap": mean_abs_shap,
            "views_multiplier": np.exp(mean_shap),
        }
    ).sort_values("mean_abs_shap", ascending=False)
    return table.reset_index(drop=True)


def build_impact_table_by_category(
    model: RandomForestRegressor, x_train: pd.DataFrame, category_columns: list[str]
) -> pd.DataFrame:
    """SHAP promedio por feature, desglosado por `categoria_nota` (una fila por categoria x feature).

    Calcula los valores SHAP una sola vez sobre todo `x_train` (mismo `TreeExplainer` que
    `build_impact_table`) y agrupa las filas según cuál columna one-hot `categoria_*` está
    activa, en vez de reentrenar o re-explicar el modelo por categoría. No excluye categorías
    con pocas notas — se reportan igual, con `n_notas` para juzgar la varianza esperada.
    """
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(x_train)

    rows = []
    for col in category_columns:
        mask = x_train[col].to_numpy(dtype=bool)
        n_notas = int(mask.sum())
        if n_notas == 0:
            continue

        categoria = col.removeprefix("categoria_")
        mean_abs_shap = np.abs(shap_values[mask]).mean(axis=0)
        mean_shap = shap_values[mask].mean(axis=0)

        rows.append(
            pd.DataFrame(
                {
                    "categoria": categoria,
                    "feature": x_train.columns,
                    "mean_abs_shap": mean_abs_shap,
                    "views_multiplier": np.exp(mean_shap),
                    "n_notas": n_notas,
                }
            )
        )

    table = pd.concat(rows, ignore_index=True)
    return table.sort_values(["categoria", "mean_abs_shap"], ascending=[True, False]).reset_index(drop=True)
