"""Validación cruzada fold-safe: features de autor recalculadas por fold, sin fuga de datos."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

from shannon_model.impact_model.dataset import (
    CONTENT_TARGET_COLUMN,
    TARGET_COLUMN,
    apply_author_stats,
    fit_author_stats,
)

_EXCLUDE_FROM_FEATURES = ("url", "autor_nombre", "fecha_publicacion", "_autor_target", TARGET_COLUMN)
_CONTENT_EXCLUDE_FROM_FEATURES = ("url", "fecha_publicacion", CONTENT_TARGET_COLUMN)


def cross_validate(
    base_df: pd.DataFrame,
    seed: int,
    n_splits: int,
    model_params: dict[str, Any],
    model_cls: type = RandomForestRegressor,
) -> dict[str, Any]:
    """CV temporal (decisión 15 de design.md): ordena notas únicas por `fecha_publicacion` y aplica
    `TimeSeriesSplit` (ventana expansiva) sobre esa secuencia de urls, no sobre filas sueltas — todas
    las filas de una nota (una por `source` con tráfico) quedan del mismo lado del split, y cada fold
    entrena con notas más viejas y valida con notas más nuevas. `autor_avg_views`/`autor_num_notas`
    se ajustan solo con el fold de train de cada iteración."""
    ordered_urls = base_df.drop_duplicates(subset="url").sort_values("fecha_publicacion")["url"].to_numpy()
    time_split = TimeSeriesSplit(n_splits=n_splits)
    fold_mae: list[float] = []
    fold_r2: list[float] = []

    for train_url_idx, val_url_idx in time_split.split(ordered_urls):
        train_urls = set(ordered_urls[train_url_idx])
        val_urls = set(ordered_urls[val_url_idx])
        train_df = base_df[base_df["url"].isin(train_urls)]
        val_df = base_df[base_df["url"].isin(val_urls)]

        stats = fit_author_stats(train_df)
        train_feat = apply_author_stats(train_df, stats, leave_one_out=True)
        val_feat = apply_author_stats(val_df, stats, leave_one_out=False)

        feature_cols = [c for c in train_feat.columns if c not in _EXCLUDE_FROM_FEATURES]
        model = model_cls(random_state=seed, **model_params)
        model.fit(train_feat[feature_cols], train_feat[TARGET_COLUMN])

        pred = model.predict(val_feat[feature_cols])
        fold_mae.append(mean_absolute_error(val_feat[TARGET_COLUMN], pred))
        fold_r2.append(r2_score(val_feat[TARGET_COLUMN], pred))

    return {
        "n_splits": n_splits,
        "mae_mean": float(np.mean(fold_mae)),
        "mae_std": float(np.std(fold_mae)),
        "r2_mean": float(np.mean(fold_r2)),
        "r2_std": float(np.std(fold_r2)),
    }


def grid_search_cv(
    base_df: pd.DataFrame,
    seed: int,
    n_splits: int,
    param_grid: list[dict[str, Any]],
    model_cls: type = RandomForestRegressor,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Evalúa cada combinación de hiperparámetros sobre el mismo esquema de CV fold-safe."""
    results = [
        {"params": params, **cross_validate(base_df, seed, n_splits, params, model_cls)}
        for params in param_grid
    ]
    best = max(results, key=lambda r: r["r2_mean"])
    return best["params"], results


def cross_validate_content_model(
    content_df: pd.DataFrame,
    seed: int,
    n_splits: int,
    model_params: dict[str, Any],
    model_cls: type = RandomForestRegressor,
) -> dict[str, Any]:
    """CV temporal para el modelo B (solo features accionables, sin autor/canal).

    Mismo esquema `TimeSeriesSplit` que `cross_validate` (evita look-ahead: entrena con notas
    más viejas, valida con las más nuevas), pero sin `fit_author_stats`/`apply_author_stats` —
    no aplica, el modelo B no tiene features de autor.
    """
    ordered = content_df.sort_values("fecha_publicacion")
    time_split = TimeSeriesSplit(n_splits=n_splits)
    fold_mae: list[float] = []
    fold_r2: list[float] = []

    feature_cols = [c for c in content_df.columns if c not in _CONTENT_EXCLUDE_FROM_FEATURES]

    for train_idx, val_idx in time_split.split(ordered):
        train_df = ordered.iloc[train_idx]
        val_df = ordered.iloc[val_idx]

        model = model_cls(random_state=seed, **model_params)
        model.fit(train_df[feature_cols], train_df[CONTENT_TARGET_COLUMN])

        pred = model.predict(val_df[feature_cols])
        fold_mae.append(mean_absolute_error(val_df[CONTENT_TARGET_COLUMN], pred))
        fold_r2.append(r2_score(val_df[CONTENT_TARGET_COLUMN], pred))

    return {
        "n_splits": n_splits,
        "mae_mean": float(np.mean(fold_mae)),
        "mae_std": float(np.std(fold_mae)),
        "r2_mean": float(np.mean(fold_r2)),
        "r2_std": float(np.std(fold_r2)),
    }


def grid_search_content_model(
    content_df: pd.DataFrame,
    seed: int,
    n_splits: int,
    param_grid: list[dict[str, Any]],
    model_cls: type = RandomForestRegressor,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Evalúa cada combinación de hiperparámetros del modelo B sobre el mismo esquema de CV temporal."""
    results = [
        {
            "params": params,
            **cross_validate_content_model(content_df, seed, n_splits, params, model_cls),
        }
        for params in param_grid
    ]
    best = max(results, key=lambda r: r["r2_mean"])
    return best["params"], results
