#!/usr/bin/env python3
"""Entrypoint: python scripts/data_quality_report.py --source data/raw/ehm_3months_filtered.xlsx"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shannon_model.analytics_eda.clean import clean_reports, split_notes_landings  # noqa: E402
from shannon_model.analytics_eda.load import load_reports  # noqa: E402
from shannon_model.analytics_eda.report import (  # noqa: E402
    aggregate_by_url,
    build_summary,
    quality_report,
    save_summary,
    section_report,
    temporal_report,
    top_notes,
    views_distribution,
    zero_view_notes,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reporte de calidad de datos y EDA de analytics")
    parser.add_argument(
        "--source",
        default="data/raw/ehm_3months_filtered.xlsx",
        help="xlsx único o carpeta de CSVs (reportes Marfeel)",
    )
    parser.add_argument("--output-dir", default="checkpoints/eda")
    parser.add_argument("--top-n", type=int, default=15)
    args = parser.parse_args()

    df_raw, resumen_carga = load_reports(args.source)
    print(f"Archivos procesados: {len(resumen_carga)} | Filas totales cargadas: {len(df_raw):,}")

    problemas = resumen_carga[resumen_carga["estado"] != "OK"]
    if len(problemas):
        print("Archivos con problemas:")
        print(problemas.to_string(index=False))

    df_clean, clean_stats = clean_reports(df_raw)
    notas, landings = split_notes_landings(df_clean)
    print(f"Filas de notas reales: {len(notas):,}  |  Filas de landing pages: {len(landings):,}")
    if clean_stats["dropped_previa"]:
        print(
            f"Filas descartadas por fecha_reporte < publishDate: {clean_stats['dropped_previa']:,} "
            f"({clean_stats['dropped_previa_con_vistas']:,} con vistas > 0)"
        )

    vistas_por_url = aggregate_by_url(notas)
    quality = quality_report(notas)
    distribution = views_distribution(vistas_por_url)
    sections = section_report(vistas_por_url)
    temporal = temporal_report(vistas_por_url)
    top = top_notes(vistas_por_url, n=args.top_n)
    zero_views = zero_view_notes(vistas_por_url)

    print("\nCalidad y cobertura:")
    print(f"  URLs únicas: {quality['urls_unicas']:,}")
    print(f"  URLs repetidas entre archivos: {quality['urls_repetidas_entre_archivos']:,}")

    print("\nDistribución de vistas por nota:")
    print(f"  {distribution['describe']}")
    print(f"  % de vistas en el top 10% de notas: {distribution['pct_vistas_top10pct_notas']:.1f}%")

    print("\nPor sección:")
    print(sections.to_string())

    print("\nVistas promedio por hora de publicación:")
    print(temporal["vistas_por_hora"])
    print("\nVistas promedio por día de la semana:")
    print(temporal["vistas_por_dia_semana"])

    print(f"\nTop {args.top_n} notas más vistas:")
    print(top.to_string(index=False))

    print(
        f"\nNotas con 0 vistas: {zero_views['count']:,} de {len(vistas_por_url):,} "
        f"({zero_views['pct']:.1f}%)"
    )

    summary = build_summary(
        resumen_carga, clean_stats, notas, landings, vistas_por_url, distribution, sections, zero_views
    )
    print("\n" + summary["text"])

    out_path = save_summary(summary, args.output_dir)
    print(f"Resumen guardado en: {out_path}")


if __name__ == "__main__":
    main()
