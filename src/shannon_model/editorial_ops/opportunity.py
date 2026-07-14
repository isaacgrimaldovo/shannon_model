"""Mayor oportunidad (gap x impacto, método `compliance_gap_v0`) + KPIs del scope."""

from __future__ import annotations

from typing import Any

import pandas as pd

from shannon_model.editorial_ops.data import NOTE_VIEWS_COLUMN


def _rule_impact_views(notes: pd.DataFrame, satisfies: pd.Series) -> float:
    with_views = notes.loc[satisfies, NOTE_VIEWS_COLUMN]
    without_views = notes.loc[~satisfies, NOTE_VIEWS_COLUMN]
    if with_views.empty or without_views.empty:
        return 0.0
    return float(with_views.mean() - without_views.mean())


def find_mayor_oportunidad(
    notes: pd.DataFrame, recipe: dict[str, Any], compliance: dict[str, Any]
) -> dict[str, Any] | None:
    """Regla con mayor `score = (1 - rule_compliance_pct) * rule_impact_views`. `None` si ninguna
    regla tiene gap (scope ya cumple todo) o no hay reglas."""
    rule_matches = compliance.get("rule_matches")
    if rule_matches is None or rule_matches.empty:
        return None

    candidates = []
    for rule in recipe["rules"]:
        feature_id = rule["feature_id"]
        col = rule_matches[feature_id]
        notes_not_matching = int((~col).sum())
        if notes_not_matching == 0:
            continue

        rule_compliance_frac = float(col.mean())
        impact_views = _rule_impact_views(notes, col)
        score = (1 - rule_compliance_frac) * impact_views

        candidates.append(
            {
                "feature_id": feature_id,
                "lever_label": rule["lever_label"],
                "rule_compliance_pct": round(100 * rule_compliance_frac, 2),
                "estimated_upside_views": round(notes_not_matching * impact_views, 1),
                "method": "compliance_gap_v0",
                "n_notes": notes_not_matching,
                "_score": score,
            }
        )

    if not candidates:
        return None
    best = max(candidates, key=lambda c: c["_score"])
    best.pop("_score")
    return best


def compute_kpis(notes_usable: pd.DataFrame, notes_total_scope: int, compliance: dict[str, Any]) -> dict[str, Any]:
    """`indice_shannon` v0 = `compliance_pct` (fórmula provisional, ver design.md open questions)."""
    views_seccion = float(notes_usable[NOTE_VIEWS_COLUMN].sum()) if len(notes_usable) else 0.0
    notas_analizadas_pct = round(100 * len(notes_usable) / notes_total_scope, 2) if notes_total_scope else 0.0
    return {
        "views_seccion": views_seccion,
        "notas_analizadas_pct": notas_analizadas_pct,
        "compliance_pct": compliance["compliance_pct"],
        "indice_shannon": compliance["compliance_pct"],
        "indice_shannon_definition": "provisional_recipe_compliance_v0",
    }
