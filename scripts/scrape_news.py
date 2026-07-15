#!/usr/bin/env python3
"""Entrypoint: python scripts/scrape_news.py --delay 1.5"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shannon_model.scraping.pipeline import (  # noqa: E402
    ScrapeConfig,
    backfill_missing_html,
    reprocess_existing,
    run_scrape,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrapear notas de heraldodemexico.com.mx")
    parser.add_argument(
        "--urls-xlsx",
        default="data/raw/csv_urls",
        help="Directorio con los CSVs de URLs (default) o, por compatibilidad, un archivo xlsx del formato viejo",
    )
    parser.add_argument("--html-dir", default="data/raw/html")
    parser.add_argument("--index-path", default="data/raw/scrape_index.csv")
    parser.add_argument("--structured-path", default="data/processed/notes_structured.parquet")
    parser.add_argument("--delay", type=float, default=1.5, help="Segundos entre requests")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--limit", type=int, default=None, help="Procesar solo N URLs pendientes")
    parser.add_argument("--workers", type=int, default=2, help="Concurrencia (hilos) del scraping")
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Intentos fallidos antes de descartar una URL definitivamente (status=exhausted)",
    )
    parser.add_argument(
        "--reprocess",
        action="store_true",
        help="Re-extraer campos desde el HTML ya guardado, sin re-fetch al sitio",
    )
    parser.add_argument(
        "--backfill-html",
        action="store_true",
        help=(
            "Para URLs ya 'ok': re-descarga el HTML si ya no está en disco "
            "(ej. para recuperar cuerpo_texto en notas viejas), o reprocesa desde disco si sigue estando"
        ),
    )
    args = parser.parse_args()

    config = ScrapeConfig(
        urls_xlsx=Path(args.urls_xlsx),
        html_dir=Path(args.html_dir),
        index_path=Path(args.index_path),
        structured_path=Path(args.structured_path),
        delay=args.delay,
        timeout=args.timeout,
        max_retries=args.max_retries,
        limit=args.limit,
        workers=args.workers,
        max_attempts=args.max_attempts,
    )
    if args.backfill_html:
        result = backfill_missing_html(config)
        print("Backfill terminado:", result)
    elif args.reprocess:
        result = reprocess_existing(config)
        print("Reprocesamiento terminado:", result)
    else:
        result = run_scrape(config)
        print("Scraping terminado:", result)


if __name__ == "__main__":
    main()
