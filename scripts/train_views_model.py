#!/usr/bin/env python3
"""Entrypoint: python scripts/train_views_model.py --config configs/views_impact.yaml"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sklearn.ensemble import GradientBoostingRegressor  # noqa: E402

from shannon_model.config import load_config  # noqa: E402
from shannon_model.impact_model.pipeline import (  # noqa: E402
    ImpactModelConfig,
    run_content_only_pipeline,
    run_pipeline,
)


def _print_result(label: str, result: dict) -> None:
    print(f"\n{'=' * 60}\n{label}\n{'=' * 60}")
    print(f"Dataset: {result['dataset_size']} notas")
    print("CV por combinación de hiperparámetros:")
    for r in result["cv_results"]:
        print(
            f"  {r['params']} -> r2={r['r2_mean']:.4f}±{r['r2_std']:.4f} "
            f"mae_log={r['mae_mean']:.4f}±{r['mae_std']:.4f}"
        )
    print("Mejores hiperparámetros:", result["best_params"])
    print("CV del mejor combo:", result["best_cv"])
    print("Top features por impacto (modelo final, fit 100% del dataset):")
    print(result["impact_table"].head(10).to_string(index=False))

    print("\nTop 3 features por impacto, por categoría de nota:")
    by_category = result["impact_table_by_category"]
    for categoria, group in by_category.groupby("categoria", sort=False):
        n_notas = int(group["n_notas"].iloc[0])
        print(f"  {categoria} (n={n_notas}):")
        for _, row in group.nlargest(3, "mean_abs_shap").iterrows():
            print(
                f"    {row['feature']}: mean_abs_shap={row['mean_abs_shap']:.4f} "
                f"x{row['views_multiplier']:.3f}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Entrenar modelos de impacto en vistas (A: completo, B: solo contenido)")
    parser.add_argument("--config", default="configs/views_impact.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    config = ImpactModelConfig(
        structured_path=Path(cfg["data"]["structured_path"]),
        csv_urls_dir=Path(cfg["data"]["csv_urls_dir"]),
        output_dir=Path(cfg["output"]["dir"]),
        seed=int(cfg["seed"]),
        n_splits=int(cfg["cv"]["n_splits"]),
        param_grid=cfg["cv"]["param_grid"],
        content_model_param_grid=cfg["content_model"]["param_grid"],
        gbr_param_grid=cfg["gbr_model"]["param_grid"],
        content_gbr_param_grid=cfg["content_gbr_model"]["param_grid"],
        nlp_cache_path=Path(cfg["nlp_tone"]["cache_path"]),
        nlp_model_name=cfg["nlp_tone"]["model_name"],
    )

    result_rf_a = run_pipeline(config)
    _print_result("MODELO A — RandomForest (autor + canal + contenido)", result_rf_a)

    result_rf_b = run_content_only_pipeline(config)
    _print_result("MODELO B — RandomForest (solo features accionables)", result_rf_b)

    result_gbr_a = run_pipeline(config, model_cls=GradientBoostingRegressor, artifact_suffix="_gbr")
    _print_result("MODELO A — GradientBoosting (autor + canal + contenido)", result_gbr_a)

    result_gbr_b = run_content_only_pipeline(
        config, model_cls=GradientBoostingRegressor, artifact_suffix="_gbr"
    )
    _print_result("MODELO B — GradientBoosting (solo features accionables)", result_gbr_b)

    print(f"\n{'=' * 60}\nCOMPARACIÓN R² POR ALGORITMO×MODELO\n{'=' * 60}")
    for label, result in (
        ("RandomForest — modelo A", result_rf_a),
        ("RandomForest — modelo B", result_rf_b),
        ("GradientBoosting — modelo A", result_gbr_a),
        ("GradientBoosting — modelo B", result_gbr_b),
    ):
        r2 = result["best_cv"]
        print(
            f"  {label:<28} r2={r2['r2_mean']:.4f}±{r2['r2_std']:.4f} "
            f"mae_log={r2['mae_mean']:.4f}±{r2['mae_std']:.4f}"
        )


if __name__ == "__main__":
    main()
