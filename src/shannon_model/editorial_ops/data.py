"""Frame de notas (nivel nota, no nota×source) para la capa de receta editorial."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from shannon_model.impact_model.dataset import load_real_views_targets
from shannon_model.impact_model.feature_kinds import ACTIONABLE_FEATURES
from shannon_model.scraping.pipeline import load_structured

NOTE_TARGET_COLUMN = "views_7d_log"
NOTE_VIEWS_COLUMN = "views_7d"


def build_notes_frame(structured_path: str | Path, csv_urls_dir: str | Path) -> pd.DataFrame:
    """Una fila por nota con columnas actionable + categoria_nota + target `views_7d` real.

    Distinto de `impact_model.build_base_frame` (que explota a nota×source para el modelo de
    regresión) — acá el scope es por nota completa, no por canal.
    """
    structured = load_structured(Path(structured_path))
    structured["fecha_publicacion"] = pd.to_datetime(structured["fecha_publicacion"])
    _, note_target = load_real_views_targets(csv_urls_dir)
    note_target = note_target.rename(NOTE_TARGET_COLUMN)

    df = structured.join(note_target, on="url", how="inner")
    df[NOTE_VIEWS_COLUMN] = np.expm1(df[NOTE_TARGET_COLUMN])

    keep_cols = (
        ["url", "categoria_nota", "fecha_publicacion"]
        + list(ACTIONABLE_FEATURES)
        + [NOTE_TARGET_COLUMN, NOTE_VIEWS_COLUMN]
    )
    df = df[keep_cols].dropna(subset=list(ACTIONABLE_FEATURES) + [NOTE_TARGET_COLUMN])
    return df.reset_index(drop=True)


def filter_scope(notes: pd.DataFrame, scope: str) -> pd.DataFrame:
    if scope == "all":
        return notes
    return notes[notes["categoria_nota"] == scope]


def count_scope_notes(structured_path: str | Path, scope: str) -> int:
    """Total de notas del scope en `notes_structured.parquet`, sin exigir target disponible
    (denominador de `notas_analizadas_pct`, distinto del pool con target usable)."""
    structured = load_structured(Path(structured_path))
    if scope == "all":
        return len(structured)
    return int((structured["categoria_nota"] == scope).sum())
