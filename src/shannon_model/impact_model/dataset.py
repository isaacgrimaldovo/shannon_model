"""Dataset de entrenamiento: join de features scrapeadas con target real de vistas (views_7d)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from shannon_model.impact_model.feature_kinds import ACTIONABLE_FEATURES
from shannon_model.scraping.pipeline import load_structured

FEATURE_COLUMNS = [
    "num_palabras",
    "num_letras",
    "largo_titulo",
    "num_imagenes_real",
    "num_etiquetas",
    "hora_sin",
    "hora_cos",
    "dia_sin",
    "dia_cos",
    "es_fin_de_semana",
    "mes_sin",
    "mes_cos",
    "autor_avg_views",
    "autor_num_notas",
    "tiene_signo_pregunta",
    "tiene_numero",
    "tiene_mayusculas_excesivas",
    "num_parrafos",
    "tiene_subtitulos",
    "tiene_video_embed",
]

TARGET_COLUMN = "log_views_proxy"
# Target auxiliar a nivel nota (agregado sobre todas las fuentes), usado solo para
# calcular autor_avg_views/autor_num_notas sin fragmentar la estadística por canal.
AUTHOR_TARGET_COLUMN = "_autor_target"

_BOOKKEEPING_COLUMNS = ("url", "autor_nombre", "fecha_publicacion", AUTHOR_TARGET_COLUMN, TARGET_COLUMN)


def _load_daily_views(csv_urls_dir: str | Path) -> pd.DataFrame:
    """Concatena los CSVs diarios de `data/raw/csv_urls/` (granularidad diaria por nota, ventana
    fija de 90 días). Filtra la fila `"Total"` que cada archivo trae al final (artefacto de export
    de Analytics) y excluye `ehm-90-google-economia.csv` (formato viejo, sin columna `date` diaria
    — redundante con `ehm-90-google-economia_II.csv`) y `ehm_report-*.csv` (duplicado del proxy viejo)."""
    csv_dir = Path(csv_urls_dir)
    files = [
        f for f in csv_dir.glob("*.csv") if "report" not in f.name and f.name != "ehm-90-google-economia.csv"
    ]
    frames = [pd.read_csv(f, usecols=["url", "source", "publishDate", "date", "pageViewsTotal"]) for f in files]
    all_df = pd.concat(frames, ignore_index=True)
    all_df = all_df[all_df["date"] != "Total"]
    all_df["date"] = pd.to_datetime(all_df["date"])
    all_df["publishDate"] = pd.to_datetime(all_df["publishDate"], errors="coerce")
    return all_df


def _views_in_publish_window(daily: pd.DataFrame) -> pd.DataFrame:
    """Filas dentro de los 7 días posteriores a publicación, solo para notas cuya ventana de
    7 días cae completa dentro del rango trackeado (si no, se excluye en vez de aproximar)."""
    window_start, window_end = daily["date"].min(), daily["date"].max()
    pub_per_url = daily.groupby("url")["publishDate"].first()
    computable = pub_per_url[(pub_per_url >= window_start) & (pub_per_url + pd.Timedelta(days=7) <= window_end)]

    sub = daily[daily["url"].isin(computable.index)].merge(computable.rename("_pub"), on="url")
    return sub[(sub["date"] >= sub["_pub"]) & (sub["date"] < sub["_pub"] + pd.Timedelta(days=7))]


def load_real_views_targets(csv_urls_dir: str | Path) -> tuple[pd.DataFrame, pd.Series]:
    """views_7d real: por combinación (url, source) para el target de entrenamiento, y por nota
    (sumando todas las fuentes) para las estadísticas de autor. Una sola pasada sobre los CSVs."""
    daily = _load_daily_views(csv_urls_dir)
    in_window = _views_in_publish_window(daily)

    by_source = in_window.groupby(["url", "source"])["pageViewsTotal"].sum().reset_index()
    by_source[TARGET_COLUMN] = np.log1p(by_source["pageViewsTotal"])
    by_source = by_source[["url", "source", TARGET_COLUMN]]

    by_note = np.log1p(in_window.groupby("url")["pageViewsTotal"].sum()).rename(AUTHOR_TARGET_COLUMN)
    return by_source, by_note


def fit_author_stats(train_df: pd.DataFrame) -> dict[str, Any]:
    """Estadísticas de autor a nivel NOTA (no por combinación nota×source), calculadas SOLO sobre `train_df`.

    Deduplica por `url` antes de agrupar: una nota con tráfico en varios canales no debe
    contarse varias veces en el promedio/conteo de su autor.
    """
    notes = train_df.drop_duplicates(subset="url")
    group = notes.groupby("autor_nombre")[AUTHOR_TARGET_COLUMN]
    return {
        "sums": group.sum(),
        "counts": group.count(),
        "global_mean": notes[AUTHOR_TARGET_COLUMN].mean(),
    }


def apply_author_stats(df: pd.DataFrame, stats: dict[str, Any], leave_one_out: bool) -> pd.DataFrame:
    """Aplica `autor_avg_views`/`autor_num_notas` usando estadísticas ya ajustadas (`fit_author_stats`).

    `leave_one_out=True` cuando `df` es el mismo set usado para ajustar `stats` (excluye la nota
    propia del promedio de su autor). `leave_one_out=False` para un set que no participó del ajuste
    (ej. fold de validación) — ahí no hay leakage, se usa el promedio de train tal cual, con fallback
    a la media global de train para autores nunca vistos en `stats`. Filas de la misma nota (varias
    por `source`) reciben el mismo valor, porque `autor_avg_views` es una propiedad de la nota/autor,
    no del canal.
    """
    df = df.copy()
    sums = df["autor_nombre"].map(stats["sums"])
    counts = df["autor_nombre"].map(stats["counts"])
    global_mean = stats["global_mean"]

    if leave_one_out:
        loo_counts = counts - 1
        loo_sums = sums - df[AUTHOR_TARGET_COLUMN]
        safe_denom = loo_counts.mask(loo_counts <= 0, 1)
        avg_views = (loo_sums / safe_denom).mask(loo_counts <= 0, global_mean)
        num_notas = counts
    else:
        avg_views = (sums / counts).where(counts.notna(), global_mean)
        num_notas = counts.fillna(0)

    df["autor_avg_views"] = avg_views.fillna(global_mean)
    df["autor_num_notas"] = num_notas
    return df


def build_base_frame(structured_path: str | Path, csv_urls_dir: str | Path) -> pd.DataFrame:
    """Una fila por combinación nota×source (decisión 12 de design.md), con one-hot de categoria_nota y source.
    Target = views_7d real (decisión 14), solo para notas con esa ventana completamente observable.

    Mantiene `url`/`autor_nombre`/`AUTHOR_TARGET_COLUMN` (sin `autor_avg_views`/`autor_num_notas`
    todavía) para que el CV fold-safe pueda agrupar por `url` (GroupKFold) y ajustar las
    estadísticas de autor por fold en vez de sobre el dataset completo.
    """
    structured = load_structured(Path(structured_path))
    structured["fecha_publicacion"] = pd.to_datetime(structured["fecha_publicacion"])
    source_targets, note_target = load_real_views_targets(csv_urls_dir)

    df = structured.merge(source_targets, on="url", how="inner")
    df = df.join(note_target, on="url")

    categoria_dummies = pd.get_dummies(df["categoria_nota"], prefix="categoria")
    source_dummies = pd.get_dummies(df["source"], prefix="source")
    df = pd.concat([df, categoria_dummies, source_dummies], axis=1)

    base_feature_cols = [c for c in FEATURE_COLUMNS if c not in ("autor_avg_views", "autor_num_notas")]
    keep_cols = (
        ["url", "autor_nombre", "fecha_publicacion", AUTHOR_TARGET_COLUMN]
        + base_feature_cols
        + list(categoria_dummies.columns)
        + list(source_dummies.columns)
    )
    df = df[keep_cols + [TARGET_COLUMN]].dropna(subset=base_feature_cols + [TARGET_COLUMN])
    return df.reset_index(drop=True)


def build_training_frame(structured_path: str | Path, csv_urls_dir: str | Path) -> pd.DataFrame:
    """Dataset completo (nota×source) con autor LOO ajustado sobre el 100% — usado por el modelo final de SHAP."""
    base = build_base_frame(structured_path, csv_urls_dir)
    stats = fit_author_stats(base)
    df = apply_author_stats(base, stats, leave_one_out=True)

    feature_cols = [c for c in df.columns if c not in _BOOKKEEPING_COLUMNS]
    return df[feature_cols + [TARGET_COLUMN]]


CONTENT_TARGET_COLUMN = "log_views_note"
# Una fila por nota (no por nota×source): sin `autor_*`/`source_*` como features, tener una fila
# por canal solo duplicaría features casi idénticas con distinto target — puro ruido, no señal.


def build_content_frame(structured_path: str | Path, csv_urls_dir: str | Path) -> pd.DataFrame:
    """Dataset a nivel nota, solo con features accionables (`feature_kinds.ACTIONABLE_FEATURES`) +
    `categoria_nota` one-hot — sin autor ni canal, para aislar la señal de contenido (modelo B).

    Reusa el target por nota (`by_note`) que `load_real_views_targets` ya calcula internamente
    para las estadísticas de autor del modelo A — mismo valor, expuesto acá como target de
    entrenamiento en vez de insumo interno.
    """
    structured = load_structured(Path(structured_path))
    structured["fecha_publicacion"] = pd.to_datetime(structured["fecha_publicacion"])
    _, note_target = load_real_views_targets(csv_urls_dir)

    df = structured.join(note_target.rename(CONTENT_TARGET_COLUMN), on="url", how="inner")

    categoria_dummies = pd.get_dummies(df["categoria_nota"], prefix="categoria")
    df = pd.concat([df, categoria_dummies], axis=1)

    actionable_cols = list(ACTIONABLE_FEATURES)
    keep_cols = (
        ["url", "fecha_publicacion"] + actionable_cols + list(categoria_dummies.columns) + [CONTENT_TARGET_COLUMN]
    )
    df = df[keep_cols].dropna(subset=actionable_cols + [CONTENT_TARGET_COLUMN])
    return df.reset_index(drop=True)
