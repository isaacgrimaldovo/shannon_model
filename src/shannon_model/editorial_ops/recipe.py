"""Receta editorial v0 (`top_views_profile_v0`): perfil de features accionables del subconjunto
de alto desempeño por views dentro del scope. Autor/canal nunca entran (ver feature_kinds)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from shannon_model.editorial_ops.data import NOTE_TARGET_COLUMN
from shannon_model.impact_model.feature_kinds import LEVER_LABELS, RECIPE_FEATURES


def _numeric_rule(top: pd.Series) -> dict[str, Any] | None:
    values = top.dropna()
    if values.empty:
        return None
    return {"operator": "between", "range": [float(values.quantile(0.25)), float(values.quantile(0.75))]}


def _binary_rule(top: pd.Series, prevalence_threshold: float) -> dict[str, Any] | None:
    values = top.dropna()
    if values.empty:
        return None
    mode = values.mode().iloc[0]
    prevalence = float((values == mode).mean())
    if prevalence < prevalence_threshold:
        return None
    return {"operator": "equals", "value": int(mode), "prevalence": round(prevalence, 3)}


def _hour_rule(top: pd.Series, window: int) -> dict[str, Any] | None:
    values = top.dropna().astype(int)
    if values.empty:
        return None
    mode_hour = int(values.mode().iloc[0])
    bins = sorted({(mode_hour + offset) % 24 for offset in range(-window, window + 1)})
    return {"operator": "hour_in", "bins": bins}


def build_recipe(
    notes: pd.DataFrame,
    top_quantile: float,
    prevalence_threshold: float,
    hour_window: int,
) -> dict[str, Any]:
    """Reglas sobre features accionables del top de vistas del scope (cuantil configurable)."""
    threshold = notes[NOTE_TARGET_COLUMN].quantile(1 - top_quantile)
    top = notes[notes[NOTE_TARGET_COLUMN] >= threshold]

    rules: list[dict[str, Any]] = []
    for feature_id, kind in RECIPE_FEATURES.items():
        if feature_id not in top.columns:
            continue

        if kind == "numeric":
            criterion = _numeric_rule(top[feature_id])
        elif kind == "binary":
            criterion = _binary_rule(top[feature_id], prevalence_threshold)
        elif kind == "hour":
            criterion = _hour_rule(top[feature_id], hour_window)
        else:
            criterion = None

        if criterion is None:
            continue

        rules.append(
            {
                "feature_id": feature_id,
                "kind": kind,
                "lever_label": LEVER_LABELS.get(feature_id, feature_id),
                "support": int(top[feature_id].notna().sum()),
                **criterion,
            }
        )

    return {
        "method": "top_views_profile_v0",
        "top_quantile": top_quantile,
        "n_top_notes": int(len(top)),
        "n_scope_notes": int(len(notes)),
        "rules": rules,
    }
