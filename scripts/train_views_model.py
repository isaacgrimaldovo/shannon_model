#!/usr/bin/env python3
"""Entrypoint: python scripts/train_views_model.py --config configs/views_impact.yaml"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

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
    )

    result_a = run_pipeline(config)
    _print_result("MODELO A — features completas (autor + canal + contenido)", result_a)

    result_b = run_content_only_pipeline(config)
    _print_result("MODELO B — solo features accionables (sin autor/canal)", result_b)


if __name__ == "__main__":
    main()
