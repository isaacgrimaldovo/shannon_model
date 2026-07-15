"""Orquesta descarga HTML en data/raw/ y dataset estructurado en data/processed/."""

from __future__ import annotations

import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm

# Category slug after strip("/"): e.g. deportes, estilo-de-vida.
# Rejects broken CSV rows that put a path/slug remnant into `folder`
# (e.g. "deportejuegue-hoy-844907.html").
_FOLDER_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

from shannon_model.scraping.extract import NoNewsArticleError, extract_note_fields
from shannon_model.scraping.fetch import RateLimiter, fetch_html
from shannon_model.scraping.index import (
    load_index,
    make_nota_id,
    now_iso,
    pending_urls,
    record_error,
    save_index,
    upsert_record,
)

STRUCTURED_COLUMNS = [
    "nota_id",
    "url",
    "titulo",
    "largo_titulo",
    "autor_nombre",
    "autor_slug",
    "fecha_publicacion",
    "hora_del_dia",
    "hora_sin",
    "hora_cos",
    "dia_semana",
    "dia_sin",
    "dia_cos",
    "es_fin_de_semana",
    "mes",
    "mes_sin",
    "mes_cos",
    "num_palabras",
    "num_letras",
    "tiene_img_principal",
    "num_imagenes",
    "num_imagenes_real",
    "num_etiquetas",
    "categoria_nota",
    "tiene_signo_pregunta",
    "tiene_numero",
    "tiene_mayusculas_excesivas",
    "num_parrafos",
    "tiene_subtitulos",
    "tiene_video_embed",
    "cuerpo_texto",
]


@dataclass
class ScrapeConfig:
    urls_xlsx: Path
    html_dir: Path
    index_path: Path
    structured_path: Path
    delay: float = 1.5
    timeout: float = 15.0
    max_retries: int = 2
    limit: int | None = None
    workers: int = 1
    max_attempts: int = 3


def load_url_folder_map(urls_xlsx: Path) -> dict[str, str]:
    df = pd.read_excel(urls_xlsx, usecols=["url", "folder"])
    df["folder"] = df["folder"].str.strip("/")
    df = df.drop_duplicates(subset="url")
    return dict(zip(df["url"], df["folder"]))


def _is_valid_folder_slug(folder: object) -> bool:
    """True if `folder` looks like a section slug, not a broken CSV remnant."""
    if not isinstance(folder, str) or not folder:
        return False
    return _FOLDER_SLUG_RE.fullmatch(folder.lower()) is not None


def load_url_folder_map_from_csv_urls(csv_urls_dir: Path) -> dict[str, str]:
    """Deriva `url -> folder` desde `data/raw/csv_urls/` (mismo esquema que el xlsx viejo,
    pero con más URLs y categorías). Excluye los mismos archivos "raros" que
    `impact_model.dataset._load_daily_views` (formato viejo / duplicado del proxy).

    Drops rows whose `folder` is not a category slug (malformed exports that splice
    path fragments into that column). Still raises if a URL keeps two *valid* folders.
    """
    csv_dir = Path(csv_urls_dir)
    files = [
        f for f in csv_dir.glob("*.csv") if "report" not in f.name and f.name != "ehm-90-google-economia.csv"
    ]
    frames = [pd.read_csv(f, usecols=["url", "folder"]) for f in files]
    df = pd.concat(frames, ignore_index=True).dropna(subset=["url"])
    df["folder"] = df["folder"].astype("string").str.strip("/")
    df = df[df["folder"].map(_is_valid_folder_slug)]

    dedup = df.drop_duplicates(subset=["url", "folder"])
    counts = dedup.groupby("url").size()
    conflicts = counts[counts > 1]
    if not conflicts.empty:
        conflicting_url = conflicts.index[0]
        values = sorted(dedup.loc[dedup["url"] == conflicting_url, "folder"].tolist())
        raise ValueError(f"folder inconsistente para url={conflicting_url!r}: {values}")

    return dict(zip(dedup["url"], dedup["folder"]))


def load_structured(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=STRUCTURED_COLUMNS)
    return pd.read_parquet(path)


def save_structured(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def _fetch_and_extract(
    url: str,
    nota_id: str,
    url_folder: dict[str, str],
    config: ScrapeConfig,
    session: requests.Session,
    thread_limiters: threading.local,
) -> dict:
    """Corre en un worker: descarga + extrae, sin tocar estado compartido (índice/dataset).

    Cada hilo obtiene su propia `RateLimiter` (vía `thread_limiters`), perezosamente
    creada la primera vez que ese hilo la usa — así el ritmo de "delay entre requests"
    se respeta por hilo, y el throughput total escala con la cantidad de workers.
    """
    if not hasattr(thread_limiters, "limiter"):
        thread_limiters.limiter = RateLimiter(config.delay)
    limiter = thread_limiters.limiter

    result = fetch_html(url, session, limiter, timeout=config.timeout, max_retries=config.max_retries)

    if not result.ok:
        return {
            "url": url,
            "nota_id": nota_id,
            "ok": False,
            "http_status": result.http_status,
            "error_msg": result.error_msg,
            "html_path": "",
        }

    html_path = config.html_dir / f"{nota_id}.html"
    html_path.write_text(result.html, encoding="utf-8")

    try:
        fields = extract_note_fields(result.html, url, categoria_nota=url_folder[url])
    except NoNewsArticleError as exc:
        return {
            "url": url,
            "nota_id": nota_id,
            "ok": False,
            "http_status": result.http_status,
            "error_msg": str(exc),
            "html_path": str(html_path),
        }

    fields["nota_id"] = nota_id
    return {
        "url": url,
        "nota_id": nota_id,
        "ok": True,
        "http_status": result.http_status,
        "html_path": str(html_path),
        "fields": fields,
    }


def _load_url_folder_map(urls_source: Path) -> dict[str, str]:
    """`urls_source` puede ser un directorio (`csv_urls`, default) o un archivo xlsx (compatibilidad)."""
    if urls_source.is_dir():
        return load_url_folder_map_from_csv_urls(urls_source)
    return load_url_folder_map(urls_source)


def run_scrape(config: ScrapeConfig) -> dict[str, int]:
    url_folder = _load_url_folder_map(config.urls_xlsx)
    all_urls = list(url_folder.keys())

    index_df = load_index(config.index_path)
    structured_df = load_structured(config.structured_path)

    to_process = pending_urls(index_df, all_urls)
    if config.limit is not None:
        to_process = to_process[: config.limit]
    config.html_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    thread_limiters = threading.local()

    ok_count = 0
    error_count = 0

    # Los workers solo hacen fetch+extract (I/O y CPU aisladas por URL); la
    # escritura de índice/dataset queda serializada acá, en el hilo coordinador,
    # que consume resultados a medida que terminan.
    with ThreadPoolExecutor(max_workers=max(1, config.workers)) as executor:
        futures = {
            executor.submit(
                _fetch_and_extract,
                url,
                make_nota_id(url),
                url_folder,
                config,
                session,
                thread_limiters,
            ): url
            for url in to_process
        }

        for future in tqdm(as_completed(futures), total=len(futures), desc="scraping"):
            outcome = future.result()

            if not outcome["ok"]:
                index_df = record_error(
                    index_df,
                    outcome["url"],
                    outcome["nota_id"],
                    outcome["http_status"],
                    outcome["error_msg"],
                    outcome["html_path"],
                    config.max_attempts,
                )
                error_count += 1
                save_index(index_df, config.index_path)
                continue

            structured_df = pd.concat(
                [structured_df, pd.DataFrame([outcome["fields"]], columns=STRUCTURED_COLUMNS)],
                ignore_index=True,
            ).drop_duplicates(subset="nota_id", keep="last")

            index_df = upsert_record(
                index_df,
                {
                    "url": outcome["url"],
                    "nota_id": outcome["nota_id"],
                    "status": "ok",
                    "http_status": outcome["http_status"],
                    "error_msg": "",
                    "scraped_at": now_iso(),
                    "html_path": outcome["html_path"],
                },
            )
            ok_count += 1
            # Guardar índice y dataset estructurado tras cada nota: si la corrida
            # se interrumpe, no queda una URL "ok" en el índice sin su fila persistida.
            save_index(index_df, config.index_path)
            save_structured(structured_df, config.structured_path)

    return {
        "total_urls": len(all_urls),
        "processed": len(to_process),
        "ok": ok_count,
        "error": error_count,
    }


def _backfill_one(
    url: str,
    nota_id: str,
    html_path: Path,
    url_folder: dict[str, str],
    config: ScrapeConfig,
    session: requests.Session,
    thread_limiters: threading.local,
) -> dict:
    """Corre en un worker: si `html_path` ya existe, reprocesa desde disco (sin red);
    si no, re-descarga (mismo `RateLimiter`/reintentos que `_fetch_and_extract`)."""
    if html_path.exists():
        html = html_path.read_text(encoding="utf-8")
        http_status = None
    else:
        if not hasattr(thread_limiters, "limiter"):
            thread_limiters.limiter = RateLimiter(config.delay)
        limiter = thread_limiters.limiter

        result = fetch_html(url, session, limiter, timeout=config.timeout, max_retries=config.max_retries)
        if not result.ok:
            return {
                "url": url,
                "nota_id": nota_id,
                "ok": False,
                "fetch_failed": True,
                "http_status": result.http_status,
                "error_msg": result.error_msg,
                "html_path": str(html_path),
            }
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(result.html, encoding="utf-8")
        html = result.html
        http_status = result.http_status

    try:
        fields = extract_note_fields(html, url, categoria_nota=url_folder.get(url, ""))
    except NoNewsArticleError as exc:
        # Falla de parseo, no de red/disco: la URL sigue siendo alcanzable (o el HTML
        # en disco es válido), así que no se marca como error en el índice — mismo
        # criterio conservador que `reprocess_existing` (skip silencioso).
        return {
            "url": url,
            "nota_id": nota_id,
            "ok": False,
            "fetch_failed": False,
            "http_status": http_status,
            "error_msg": str(exc),
            "html_path": str(html_path),
        }

    fields["nota_id"] = nota_id
    return {
        "url": url,
        "nota_id": nota_id,
        "ok": True,
        "http_status": http_status,
        "html_path": str(html_path),
        "fields": fields,
    }


def backfill_missing_html(config: ScrapeConfig) -> dict[str, int]:
    """Para URLs con `status=ok` en el índice: re-descarga el HTML si `html_path` ya no
    existe en disco (reusando `RateLimiter`/reintentos), o reprocesa desde disco si sí existe.
    En ambos casos re-extrae campos (incluyendo `cuerpo_texto`, ausente en corridas viejas) y
    actualiza `notes_structured.parquet`. No toca URLs con `status` distinto de `ok`."""
    url_folder = _load_url_folder_map(config.urls_xlsx)
    index_df = load_index(config.index_path)
    structured_df = load_structured(config.structured_path)

    ok_rows = index_df[index_df["status"] == "ok"]

    session = requests.Session()
    thread_limiters = threading.local()

    refetched = 0
    reprocessed_from_disk = 0
    error_count = 0
    skipped = 0

    with ThreadPoolExecutor(max_workers=max(1, config.workers)) as executor:
        futures = {
            executor.submit(
                _backfill_one,
                row["url"],
                row["nota_id"],
                Path(row["html_path"]),
                url_folder,
                config,
                session,
                thread_limiters,
            ): row["nota_id"]
            for _, row in ok_rows.iterrows()
        }

        for future in tqdm(as_completed(futures), total=len(futures), desc="backfill"):
            outcome = future.result()
            # `http_status is None` significa que `_backfill_one` leyó del disco en vez de
            # re-descargar (ver `_backfill_one`) — a esta altura `html_path` ya existe en
            # ambos casos, así que no sirve para distinguir fetch de disco.
            read_from_disk = outcome["ok"] and outcome["http_status"] is None

            if not outcome["ok"]:
                if outcome["fetch_failed"]:
                    index_df = record_error(
                        index_df,
                        outcome["url"],
                        outcome["nota_id"],
                        outcome["http_status"],
                        outcome["error_msg"],
                        outcome["html_path"],
                        config.max_attempts,
                    )
                    error_count += 1
                    save_index(index_df, config.index_path)
                else:
                    skipped += 1
                continue

            structured_df = pd.concat(
                [structured_df, pd.DataFrame([outcome["fields"]], columns=STRUCTURED_COLUMNS)],
                ignore_index=True,
            ).drop_duplicates(subset="nota_id", keep="last")

            if read_from_disk:
                reprocessed_from_disk += 1
            else:
                refetched += 1
                index_df = upsert_record(
                    index_df,
                    {
                        "url": outcome["url"],
                        "nota_id": outcome["nota_id"],
                        "status": "ok",
                        "http_status": outcome["http_status"],
                        "error_msg": "",
                        "scraped_at": now_iso(),
                        "html_path": outcome["html_path"],
                    },
                )
                save_index(index_df, config.index_path)
            # Guardar tras cada nota: mismo criterio que run_scrape, si la corrida
            # se interrumpe no se pierde el trabajo ya hecho.
            save_structured(structured_df, config.structured_path)

    return {
        "total_ok": len(ok_rows),
        "refetched": refetched,
        "reprocessed_from_disk": reprocessed_from_disk,
        "error": error_count,
        "skipped": skipped,
    }


def reprocess_existing(config: ScrapeConfig) -> dict[str, int]:
    """Re-extrae campos desde el HTML ya guardado (sin re-fetch) para notas con status ok.

    Correr solo cuando no haya un scrape en curso escribiendo los mismos archivos
    (índice y dataset estructurado no tienen locking entre procesos).
    """
    url_folder = _load_url_folder_map(config.urls_xlsx)
    index_df = load_index(config.index_path)
    structured_df = load_structured(config.structured_path)

    ok_rows = index_df[index_df["status"] == "ok"]
    new_rows: list[dict] = []
    skipped = 0

    for _, row in tqdm(ok_rows.iterrows(), total=len(ok_rows), desc="reprocessing"):
        url = row["url"]
        html_path = Path(row["html_path"])
        if not html_path.exists():
            skipped += 1
            continue

        html = html_path.read_text(encoding="utf-8")
        try:
            fields = extract_note_fields(html, url, categoria_nota=url_folder.get(url, ""))
        except NoNewsArticleError:
            skipped += 1
            continue

        fields["nota_id"] = row["nota_id"]
        new_rows.append(fields)

    # Concatenar una sola vez al final: reprocesar no tiene el riesgo de crash-a-mitad-de-red
    # que justificaba el guardado incremental de run_scrape (todo el HTML ya está en disco).
    if new_rows:
        structured_df = pd.concat(
            [structured_df, pd.DataFrame(new_rows, columns=STRUCTURED_COLUMNS)],
            ignore_index=True,
        ).drop_duplicates(subset="nota_id", keep="last")
    save_structured(structured_df, config.structured_path)
    return {"total_ok": len(ok_rows), "updated": len(new_rows), "skipped": skipped}
