"""Índice idempotente url -> nota_id para el scraper de noticias."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

INDEX_COLUMNS = [
    "url",
    "nota_id",
    "status",
    "http_status",
    "error_msg",
    "scraped_at",
    "html_path",
    "attempts",
]


def make_nota_id(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return f"nota_{digest[:8]}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_index(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=INDEX_COLUMNS)
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    if "attempts" not in df.columns:
        df["attempts"] = "0"
    return df


def save_index(df: pd.DataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _attempts_of(df: pd.DataFrame, url: str) -> int:
    prev = df[df["url"] == url]
    if not len(prev):
        return 0
    value = prev["attempts"].iloc[0]
    return int(value) if str(value).strip() else 0


def upsert_record(df: pd.DataFrame, record: dict) -> pd.DataFrame:
    """Reemplaza (por url) o agrega una fila del índice.

    Si `record` no trae `attempts`, se completa con el valor previo para esa
    URL (0 si es nueva). Si `status='error'`, se incrementa sobre el previo.
    """
    if "attempts" not in record:
        prev_attempts = _attempts_of(df, record["url"])
        if record.get("status") == "error":
            prev_attempts += 1
        record = {**record, "attempts": str(prev_attempts)}
    df = df[df["url"] != record["url"]]
    new_row = pd.DataFrame([record], columns=INDEX_COLUMNS)
    return pd.concat([df, new_row], ignore_index=True)


def record_error(
    df: pd.DataFrame,
    url: str,
    nota_id: str,
    http_status: int | None,
    error_msg: str,
    html_path: str,
    max_attempts: int,
) -> pd.DataFrame:
    """Registra un intento fallido; marca `status='exhausted'` al alcanzar `max_attempts`."""
    df = upsert_record(
        df,
        {
            "url": url,
            "nota_id": nota_id,
            "status": "error",
            "http_status": http_status if http_status is not None else "",
            "error_msg": error_msg,
            "scraped_at": now_iso(),
            "html_path": html_path,
        },
    )
    if _attempts_of(df, url) >= max_attempts:
        df = upsert_record(
            df,
            {
                "url": url,
                "nota_id": nota_id,
                "status": "exhausted",
                "http_status": http_status if http_status is not None else "",
                "error_msg": error_msg,
                "scraped_at": now_iso(),
                "html_path": html_path,
            },
        )
    return df


def pending_urls(index_df: pd.DataFrame, all_urls: list[str]) -> list[str]:
    """URLs sin intento o con status distinto de 'ok'/'exhausted'."""
    done_urls = set(index_df.loc[index_df["status"].isin(["ok", "exhausted"]), "url"])
    return [u for u in all_urls if u not in done_urls]
