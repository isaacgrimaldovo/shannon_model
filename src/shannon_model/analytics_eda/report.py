"""Reportes de calidad, distribución de vistas y patrones temporales sobre notas limpias."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def aggregate_by_url(notas: pd.DataFrame) -> pd.DataFrame:
    """Agrega filas (fuente x día) a una fila por URL única de nota."""
    return notas.groupby("url", as_index=False).agg(
        pageViews_total=("pageViewsTotal", "sum"),
        categoria=("categoria", "first"),
        articulo_id=("articulo_id", "first"),
        publishDate=("publishDate_dt", "first"),
        n_filas=("pageViewsTotal", "size"),
        n_archivos_origen=("archivo_origen", "nunique"),
        n_fuentes=("source", "nunique"),
    )


def quality_report(notas: pd.DataFrame) -> dict:
    """Calidad y cobertura: rango de fechas, filas por fuente/archivo, % faltantes, URLs repetidas."""
    vistas_por_url = aggregate_by_url(notas)
    faltantes_pct = (
        notas[["url", "categoria", "publishDate_dt", "articulo_id"]].isna().mean() * 100
    ).round(2)

    return {
        "rango_publicacion": (notas["publishDate_dt"].min(), notas["publishDate_dt"].max()),
        "rango_reporte": (notas["fecha_reporte"].min(), notas["fecha_reporte"].max()),
        "filas_por_fuente": notas["source"].value_counts(dropna=False).to_dict(),
        "filas_por_archivo": notas.groupby("archivo_origen").size().to_dict(),
        "pct_faltantes": faltantes_pct.to_dict(),
        "urls_unicas": int(len(vistas_por_url)),
        "urls_repetidas_entre_archivos": int((vistas_por_url["n_archivos_origen"] > 1).sum()),
    }


def views_distribution(vistas_por_url: pd.DataFrame) -> dict:
    """Estadísticos descriptivos + concentración long-tail (top 10% de notas)."""
    describe = vistas_por_url["pageViews_total"].describe().to_dict()

    top = vistas_por_url.sort_values("pageViews_total", ascending=False)
    n_top10 = max(1, int(len(top) * 0.10))
    total_views = top["pageViews_total"].sum()
    pct_top10 = (top.head(n_top10)["pageViews_total"].sum() / total_views * 100) if total_views else 0.0

    return {"describe": describe, "pct_vistas_top10pct_notas": round(float(pct_top10), 1)}


def section_report(vistas_por_url: pd.DataFrame) -> pd.DataFrame:
    """Cantidad de notas y vistas totales/promedio por sección (categoria)."""
    notas_por_seccion = vistas_por_url["categoria"].value_counts()
    vistas_por_seccion = vistas_por_url.groupby("categoria")["pageViews_total"].sum()

    return pd.DataFrame(
        {
            "notas": notas_por_seccion,
            "vistas_totales": vistas_por_seccion,
            "vistas_promedio_por_nota": vistas_por_seccion / notas_por_seccion,
        }
    ).sort_values("vistas_totales", ascending=False)


def temporal_report(vistas_por_url: pd.DataFrame) -> dict:
    """Vistas promedio por hora de publicación y por día de la semana."""
    notas_unicas = vistas_por_url.dropna(subset=["publishDate"]).copy()
    notas_unicas["hora"] = notas_unicas["publishDate"].dt.hour
    notas_unicas["dia_semana"] = notas_unicas["publishDate"].dt.dayofweek

    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    vistas_por_dia = notas_unicas.groupby("dia_semana")["pageViews_total"].mean()
    vistas_por_dia.index = [dias[i] for i in vistas_por_dia.index]

    return {
        "vistas_por_hora": notas_unicas.groupby("hora")["pageViews_total"].mean().to_dict(),
        "vistas_por_dia_semana": vistas_por_dia.to_dict(),
    }


def top_notes(vistas_por_url: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    """Top N notas más vistas."""
    return vistas_por_url.sort_values("pageViews_total", ascending=False).head(n)[
        ["url", "categoria", "publishDate", "pageViews_total"]
    ]


def zero_view_notes(vistas_por_url: pd.DataFrame) -> dict:
    """Cantidad y porcentaje de notas con 0 vistas registradas."""
    sin_vistas = vistas_por_url[vistas_por_url["pageViews_total"] == 0]
    total = len(vistas_por_url)
    return {
        "count": int(len(sin_vistas)),
        "pct": round(len(sin_vistas) / total * 100, 1) if total else 0.0,
    }


def build_summary(
    resumen_carga: pd.DataFrame,
    clean_stats: dict,
    notas: pd.DataFrame,
    landings: pd.DataFrame,
    vistas_por_url: pd.DataFrame,
    distribution: dict,
    sections: pd.DataFrame,
    zero_views: dict,
) -> dict:
    """Arma el resumen ejecutivo: dict con métricas clave + su representación en texto plano."""
    seccion_top = sections.index[0] if len(sections) else None
    seccion_top_vistas = int(sections["vistas_totales"].iloc[0]) if len(sections) else 0

    fecha_min = notas["publishDate_dt"].min()
    fecha_max = notas["publishDate_dt"].max()

    metrics = {
        "archivos_cargados": len(resumen_carga),
        "filas_crudas": clean_stats["rows_before"],
        "filas_notas": len(notas),
        "filas_landing": len(landings),
        "urls_unicas": int(vistas_por_url["url"].nunique()),
        "rango_publicacion": (fecha_min, fecha_max),
        "seccion_top": seccion_top,
        "seccion_top_vistas": seccion_top_vistas,
        "pct_vistas_top10pct": distribution["pct_vistas_top10pct_notas"],
        "notas_sin_vistas": zero_views["count"],
        "notas_sin_vistas_pct": zero_views["pct"],
    }

    rango_txt = (
        f"{fecha_min:%Y-%m-%d} a {fecha_max:%Y-%m-%d}"
        if pd.notna(fecha_min) and pd.notna(fecha_max)
        else "sin datos"
    )

    text = (
        "RESUMEN EDA\n"
        "--------------------------------------------------\n"
        f"Archivos cargados         : {metrics['archivos_cargados']}\n"
        f"Filas totales (crudas)    : {metrics['filas_crudas']:,}\n"
        f"Filas de notas (limpias)  : {metrics['filas_notas']:,}\n"
        f"Filas de landing pages    : {metrics['filas_landing']:,}\n"
        f"URLs únicas de notas      : {metrics['urls_unicas']:,}\n"
        f"Rango de publicación      : {rango_txt}\n"
        f"Sección con más vistas    : {metrics['seccion_top']} ({metrics['seccion_top_vistas']:,} pageViews)\n"
        f"% vistas en top 10% notas : {metrics['pct_vistas_top10pct']:.1f}%\n"
        f"Notas con 0 vistas        : {metrics['notas_sin_vistas']:,} ({metrics['notas_sin_vistas_pct']:.1f}%)\n"
    )

    return {"metrics": metrics, "text": text}


def save_summary(summary: dict, output_dir: str | Path) -> Path:
    """Persiste el resumen ejecutivo en texto plano bajo `output_dir`."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "resumen_eda.txt"
    path.write_text(summary["text"], encoding="utf-8")
    return path
