"""Cumplimiento de la receta sobre notas actuales del scope."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _rule_matches(row: pd.Series, rule: dict[str, Any]) -> bool:
    value = row.get(rule["feature_id"])
    if pd.isna(value):
        return False
    if rule["operator"] == "between":
        low, high = rule["range"]
        return low <= value <= high
    if rule["operator"] == "equals":
        return int(value) == int(rule["value"])
    if rule["operator"] == "hour_in":
        return int(value) in set(rule["bins"])
    raise ValueError(f"operador de regla desconocido: {rule['operator']}")


def evaluate_compliance(notes: pd.DataFrame, recipe: dict[str, Any], match_threshold: float) -> dict[str, Any]:
    """`notes_matching`/`notes_total`/`compliance_pct` + cumplimiento por-nota y por-regla.

    Una nota cuenta como matching si su fracción de reglas satisfechas >= `match_threshold`
    (default 1.0 = todas las reglas).
    """
    rules = recipe["rules"]
    notes_total = len(notes)

    if not rules or notes_total == 0:
        return {
            "notes_matching": 0,
            "notes_total": notes_total,
            "compliance_pct": 0.0,
            "per_rule": [],
            "rule_matches": pd.DataFrame(index=notes.index),
        }

    rule_matches = pd.DataFrame(
        {rule["feature_id"]: notes.apply(lambda row, r=rule: _rule_matches(row, r), axis=1) for rule in rules}
    )
    match_scores = rule_matches.mean(axis=1)
    matching = match_scores >= match_threshold
    notes_matching = int(matching.sum())

    per_rule = [
        {
            "feature_id": rule["feature_id"],
            "lever_label": rule["lever_label"],
            "rule_compliance_pct": round(100 * float(rule_matches[rule["feature_id"]].mean()), 2),
            "notes_matching_rule": int(rule_matches[rule["feature_id"]].sum()),
        }
        for rule in rules
    ]

    return {
        "notes_matching": notes_matching,
        "notes_total": notes_total,
        "compliance_pct": round(100 * notes_matching / notes_total, 2),
        "per_rule": per_rule,
        "rule_matches": rule_matches,
    }
