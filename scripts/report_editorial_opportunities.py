#!/usr/bin/env python3
"""Entrypoint: python scripts/report_editorial_opportunities.py --config configs/editorial_opportunities.yaml"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shannon_model.config import load_config  # noqa: E402
from shannon_model.editorial_ops.pipeline import EditorialOpportunityConfig, run_report  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Reporte de oportunidades editoriales por sección")
    parser.add_argument("--config", default="configs/editorial_opportunities.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    recipe_cfg = cfg["recipe"]
    config = EditorialOpportunityConfig(
        structured_path=Path(cfg["data"]["structured_path"]),
        csv_urls_dir=Path(cfg["data"]["csv_urls_dir"]),
        scopes=cfg["scopes"],
        min_notes=int(recipe_cfg["min_notes"]),
        recipe_top_quantile=float(recipe_cfg["top_quantile"]),
        recipe_match_threshold=float(recipe_cfg["match_threshold"]),
        recipe_prevalence_threshold=float(recipe_cfg["prevalence_threshold"]),
        recipe_hour_window=int(recipe_cfg["hour_window"]),
        compliance_period=cfg.get("compliance_period"),
        target_kind=cfg["target_kind"],
    )

    result = run_report(config)

    output_dir = Path(cfg["output"]["dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "report.json"
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print(f"Reporte persistido en {output_path}")
    for scope, scope_result in result.items():
        if scope_result["status"] == "insufficient_data":
            print(f"  {scope}: insufficient_data (n={scope_result['n_notes_usable']} < {scope_result['min_notes']})")
            continue
        kpis = scope_result["kpis"]
        print(
            f"  {scope}: compliance={kpis['compliance_pct']}% "
            f"views_seccion={kpis['views_seccion']:.0f} "
            f"analizadas={kpis['notas_analizadas_pct']}%"
        )
        mo = scope_result["mayor_oportunidad"]
        if mo:
            print(f"    mayor oportunidad: {mo['lever_label']} (+{mo['estimated_upside_views']:.0f} vistas est.)")


if __name__ == "__main__":
    main()
