"""Orquesta dataset -> CV fold-safe -> modelo final -> reporte de impacto de vistas."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
from sklearn.ensemble import RandomForestRegressor

from shannon_model.impact_model.cv import grid_search_content_model, grid_search_cv
from shannon_model.impact_model.dataset import (
    CONTENT_TARGET_COLUMN,
    DEFAULT_NLP_CACHE_PATH,
    build_base_frame,
    build_content_frame,
    build_training_frame,
)
from shannon_model.impact_model.explain import build_impact_table, build_impact_table_by_category
from shannon_model.impact_model.nlp_tone import DEFAULT_MODEL_NAME
from shannon_model.impact_model.train import fit_final_model

_CONTENT_NON_FEATURE_COLUMNS = ("url", "fecha_publicacion", CONTENT_TARGET_COLUMN)


@dataclass
class ImpactModelConfig:
    structured_path: Path
    csv_urls_dir: Path
    output_dir: Path
    seed: int = 42
    n_splits: int = 5
    param_grid: list[dict[str, Any]] = field(default_factory=list)
    content_model_param_grid: list[dict[str, Any]] = field(default_factory=list)
    gbr_param_grid: list[dict[str, Any]] = field(default_factory=list)
    content_gbr_param_grid: list[dict[str, Any]] = field(default_factory=list)
    nlp_cache_path: Path = Path(DEFAULT_NLP_CACHE_PATH)
    nlp_model_name: str = DEFAULT_MODEL_NAME


def run_pipeline(
    config: ImpactModelConfig, model_cls: type = RandomForestRegressor, artifact_suffix: str = ""
) -> dict[str, Any]:
    base_df = build_base_frame(
        config.structured_path, config.csv_urls_dir, config.nlp_cache_path, config.nlp_model_name
    )
    if base_df.empty:
        raise ValueError("dataset de entrenamiento vacío: no hay notas scrapeadas con target válido")

    best_params, cv_results = grid_search_cv(
        base_df, config.seed, config.n_splits, config.param_grid, model_cls
    )
    best_cv = max(cv_results, key=lambda r: r["r2_mean"])

    training_frame = build_training_frame(
        config.structured_path, config.csv_urls_dir, config.nlp_cache_path, config.nlp_model_name
    )
    model = fit_final_model(training_frame, config.seed, best_params, model_cls)
    feature_cols = [c for c in training_frame.columns if c != "log_views_proxy"]
    impact_table = build_impact_table(model, training_frame[feature_cols])

    category_columns = [c for c in feature_cols if c.startswith("categoria_")]
    impact_table_by_category = build_impact_table_by_category(
        model, training_frame[feature_cols], category_columns
    )

    config.output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, config.output_dir / f"model{artifact_suffix}.joblib")
    impact_table.to_csv(config.output_dir / f"feature_impact{artifact_suffix}.csv", index=False)
    impact_table_by_category.to_csv(
        config.output_dir / f"feature_impact{artifact_suffix}_by_category.csv", index=False
    )

    return {
        "dataset_size": len(base_df),
        "best_params": best_params,
        "best_cv": best_cv,
        "cv_results": cv_results,
        "impact_table": impact_table,
        "impact_table_by_category": impact_table_by_category,
    }


def run_content_only_pipeline(
    config: ImpactModelConfig, model_cls: type = RandomForestRegressor, artifact_suffix: str = ""
) -> dict[str, Any]:
    """Modelo B: solo features accionables (sin autor/canal), para aislar señal de contenido.

    Dataset a nivel nota (no nota×source, ver `build_content_frame`). Conviven con el modelo A
    (`run_pipeline`) — no lo modifica ni reusa su dataset/CV, ambos tienen propósitos distintos.
    """
    content_df = build_content_frame(
        config.structured_path, config.csv_urls_dir, config.nlp_cache_path, config.nlp_model_name
    )
    if content_df.empty:
        raise ValueError("dataset de entrenamiento (modelo B) vacío: no hay notas con target válido")

    best_params, cv_results = grid_search_content_model(
        content_df, config.seed, config.n_splits, config.content_model_param_grid, model_cls
    )
    best_cv = max(cv_results, key=lambda r: r["r2_mean"])

    feature_cols = [c for c in content_df.columns if c not in _CONTENT_NON_FEATURE_COLUMNS]
    model = model_cls(random_state=config.seed, **best_params)
    model.fit(content_df[feature_cols], content_df[CONTENT_TARGET_COLUMN])

    impact_table = build_impact_table(model, content_df[feature_cols])
    category_columns = [c for c in feature_cols if c.startswith("categoria_")]
    impact_table_by_category = build_impact_table_by_category(model, content_df[feature_cols], category_columns)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, config.output_dir / f"model_content_only{artifact_suffix}.joblib")
    impact_table.to_csv(config.output_dir / f"feature_impact_content_only{artifact_suffix}.csv", index=False)
    impact_table_by_category.to_csv(
        config.output_dir / f"feature_impact_content_only{artifact_suffix}_by_category.csv", index=False
    )

    return {
        "dataset_size": len(content_df),
        "best_params": best_params,
        "best_cv": best_cv,
        "cv_results": cv_results,
        "impact_table": impact_table,
        "impact_table_by_category": impact_table_by_category,
    }
