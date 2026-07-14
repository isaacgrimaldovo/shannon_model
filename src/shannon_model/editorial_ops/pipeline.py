"""Orquesta: notas del scope -> receta -> cumplimiento -> mayor oportunidad -> KPIs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from shannon_model.editorial_ops.compliance import evaluate_compliance
from shannon_model.editorial_ops.data import build_notes_frame, count_scope_notes, filter_scope
from shannon_model.editorial_ops.opportunity import compute_kpis, find_mayor_oportunidad
from shannon_model.editorial_ops.recipe import build_recipe


@dataclass
class EditorialOpportunityConfig:
    structured_path: Path
    csv_urls_dir: Path
    scopes: list[str]
    min_notes: int = 30
    recipe_top_quantile: float = 0.25
    recipe_match_threshold: float = 1.0
    recipe_prevalence_threshold: float = 0.6
    recipe_hour_window: int = 1
    compliance_period: dict[str, str] | None = None
    target_kind: str = "views_7d"


def _filter_compliance_period(notes: pd.DataFrame, period: dict[str, str] | None) -> pd.DataFrame:
    if not period:
        return notes
    mask = pd.Series(True, index=notes.index)
    if period.get("start"):
        mask &= notes["fecha_publicacion"] >= pd.Timestamp(period["start"])
    if period.get("end"):
        mask &= notes["fecha_publicacion"] <= pd.Timestamp(period["end"])
    return notes[mask]


def run_scope(config: EditorialOpportunityConfig, scope: str, all_notes: pd.DataFrame) -> dict[str, Any]:
    scope_notes = filter_scope(all_notes, scope)
    notes_total_scope = count_scope_notes(config.structured_path, scope)

    if len(scope_notes) < config.min_notes:
        return {
            "scope": scope,
            "status": "insufficient_data",
            "n_notes_usable": len(scope_notes),
            "min_notes": config.min_notes,
        }

    recipe = build_recipe(
        scope_notes,
        config.recipe_top_quantile,
        config.recipe_prevalence_threshold,
        config.recipe_hour_window,
    )

    compliance_notes = _filter_compliance_period(scope_notes, config.compliance_period)
    compliance = evaluate_compliance(compliance_notes, recipe, config.recipe_match_threshold)
    mayor_oportunidad = find_mayor_oportunidad(compliance_notes, recipe, compliance)
    kpis = compute_kpis(compliance_notes, notes_total_scope, compliance)

    return {
        "scope": scope,
        "status": "ok",
        "target_kind": config.target_kind,
        "recipe": recipe,
        "compliance": {
            "notes_matching": compliance["notes_matching"],
            "notes_total": compliance["notes_total"],
            "compliance_pct": compliance["compliance_pct"],
            "per_rule": compliance["per_rule"],
        },
        "mayor_oportunidad": mayor_oportunidad,
        "kpis": kpis,
    }


def run_report(config: EditorialOpportunityConfig) -> dict[str, Any]:
    all_notes = build_notes_frame(config.structured_path, config.csv_urls_dir)
    return {scope: run_scope(config, scope, all_notes) for scope in config.scopes}
