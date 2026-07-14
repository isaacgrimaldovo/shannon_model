"""Limpieza y normalización de reportes de analytics crudos."""

from __future__ import annotations

import re

import pandas as pd

_ARTICULO_ID_RE = re.compile(r"-(\d+)\.html$")


def _extract_articulo_id(url) -> str | None:
    match = _ARTICULO_ID_RE.search(str(url))
    return match.group(1) if match else None


def clean_reports(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Limpia reportes crudos de analytics.

    Quita el footer "Total" del export, tipa columnas, marca landing pages y
    descarta filas donde `fecha_reporte` es anterior a `publishDate` (artefacto
    del cruce de datos de Marfeel — casi siempre con 0 vistas).

    Devuelve (df_limpio, stats) con los conteos de filas descartadas en cada paso.
    """
    df = df.copy()

    rows_before = len(df)
    df = df[df["url"].notna()].copy()
    df = df[df["date"].str.strip().str.lower() != "total"].copy()
    dropped_footer = rows_before - len(df)

    df["pageViewsTotal"] = pd.to_numeric(df["pageViewsTotal"], errors="coerce").fillna(0).astype(int)
    df["publishDate_dt"] = pd.to_datetime(df["publishDate"], errors="coerce", utc=False)
    # `date` puede traer sufijo " UTC" (ej. "2026-07-06 00:00:00 UTC") — se parsea como UTC
    # y se descarta el tz para poder comparar contra `publishDate_dt` (tz-naive).
    df["fecha_reporte"] = pd.to_datetime(df["date"], errors="coerce", utc=True).dt.tz_localize(None)
    df["es_landing"] = df["publishDate"].astype(str).str.strip() == "-"

    mask_previa = (df["fecha_reporte"] < df["publishDate_dt"]) & (~df["es_landing"])
    dropped_previa = int(mask_previa.sum())
    dropped_previa_con_vistas = (
        int((df.loc[mask_previa, "pageViewsTotal"] > 0).sum()) if dropped_previa else 0
    )
    if dropped_previa:
        df = df[~mask_previa].copy()

    df["categoria"] = df["folder"].astype(str).str.strip("/")
    df["articulo_id"] = df["url"].apply(_extract_articulo_id)

    stats = {
        "rows_before": rows_before,
        "dropped_footer": dropped_footer,
        "dropped_previa": dropped_previa,
        "dropped_previa_con_vistas": dropped_previa_con_vistas,
        "rows_after": len(df),
    }
    return df, stats


def split_notes_landings(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa filas de nota individual de filas de landing page (portada de sección)."""
    return df[~df["es_landing"]].copy(), df[df["es_landing"]].copy()
