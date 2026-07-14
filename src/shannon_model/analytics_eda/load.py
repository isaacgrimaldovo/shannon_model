"""Carga de reportes de analytics (xlsx único o carpeta de CSVs "reportes Marfeel")."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

COLUMNAS_MINIMAS = {"url", "folder", "source", "publishDate", "publishTime", "date", "pageViewsTotal"}


def find_csv_files(folder: str | Path) -> list[str]:
    """Busca archivos .csv sin usar `glob`.

    Rutas con corchetes (ej. "[2] Desarrollo") rompen los patrones de `glob`
    porque "[2]" se interpreta como una clase de caracteres.
    """
    folder = str(folder)
    if not os.path.isdir(folder):
        return []

    direct = [
        os.path.join(folder, name)
        for name in os.listdir(folder)
        if name.lower().endswith(".csv") and os.path.isfile(os.path.join(folder, name))
    ]
    if direct:
        return sorted(direct)

    nested = []
    for root, _dirs, names in os.walk(folder):
        for name in names:
            if name.lower().endswith(".csv"):
                nested.append(os.path.join(root, name))
    return sorted(nested)


def _load_single_csv(path: str) -> tuple[pd.DataFrame | None, dict]:
    name = os.path.basename(path)
    try:
        df = pd.read_csv(path, encoding="utf-8-sig", dtype=str, low_memory=False)
    except Exception as exc:
        return None, {"archivo": name, "filas": 0, "estado": f"ERROR de lectura: {exc}"}

    missing = COLUMNAS_MINIMAS - set(df.columns)
    if missing:
        return None, {
            "archivo": name,
            "filas": len(df),
            "estado": f"OMITIDO — faltan columnas {sorted(missing)}",
        }

    df["archivo_origen"] = name
    return df, {"archivo": name, "filas": len(df), "estado": "OK"}


def load_reports(source: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carga reportes desde un xlsx único o una carpeta de CSVs (reportes Marfeel).

    Devuelve (df_concatenado, resumen_de_carga). El resumen sirve para detectar
    rápidamente si algún archivo vino con un esquema distinto o falló al leerse.
    """
    source = Path(source)

    if source.is_dir():
        csv_paths = find_csv_files(source)
        if not csv_paths:
            raise FileNotFoundError(f"No se encontraron .csv en: {source}")

        frames, summary = [], []
        for path in csv_paths:
            df, entry = _load_single_csv(path)
            summary.append(entry)
            if df is not None:
                frames.append(df)

        if not frames:
            raise ValueError("Ningún archivo pasó la validación de columnas mínimas.")

        return pd.concat(frames, ignore_index=True), pd.DataFrame(summary)

    df = pd.read_excel(source, dtype=str)
    missing = COLUMNAS_MINIMAS - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas mínimas en {source}: {sorted(missing)}")
    df["archivo_origen"] = source.name
    summary = pd.DataFrame([{"archivo": source.name, "filas": len(df), "estado": "OK"}])
    return df, summary
