"""Tono/polaridad sobre `cuerpo_texto` vía modelo de sentiment pre-entrenado en español
(`pysentimiento`/RoBERTuito). El tokenizer del modelo trunca automáticamente a su
`model_max_length` (128 tokens en `robertuito-sentiment-analysis`) — cuerpos largos pierden
señal del final del texto, ver design.md de `nlp-tone-polarity-features`."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

DEFAULT_MODEL_NAME = "pysentimiento/robertuito-sentiment-analysis"
TONE_LABELS = ("POS", "NEG", "NEU")
_CACHE_COLUMNS = ["nota_id", "text_hash", "tono", "polaridad_score"]
# Notas por lote antes de persistir el cache. Corre en Colab, donde la sesión se puede cortar a
# mitad de una corrida larga — guardar cada CHUNK_SIZE notas (en vez de una sola vez al final)
# limita lo que se pierde si eso pasa a un lote, no al progreso completo.
CHUNK_SIZE = 300


def _text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _load_analyzer(model_name: str):
    from pysentimiento import create_analyzer

    return create_analyzer(task="sentiment", lang="es")


def score_tone(texts: pd.Series, model_name: str = DEFAULT_MODEL_NAME, analyzer=None) -> pd.DataFrame:
    """Corre el analizador de sentiment sobre `texts` (indexado por `nota_id`). Notas con texto
    vacío se omiten (quedan fuera del resultado) — no se les asigna un tono/polaridad arbitrario.

    `analyzer` opcional: pasarlo cuando se llama en lotes (`load_or_compute_tone`) para no
    recargar el modelo en cada lote — instanciar `create_analyzer` no es gratis."""
    non_empty = texts[texts.str.strip() != ""]
    if non_empty.empty:
        return pd.DataFrame(columns=["tono", "polaridad_score"]).rename_axis("nota_id")

    if analyzer is None:
        analyzer = _load_analyzer(model_name)
    predictions = analyzer.predict(non_empty.tolist())

    rows = [
        {
            "nota_id": nota_id,
            "tono": pred.output,
            "polaridad_score": pred.probas.get("POS", 0.0) - pred.probas.get("NEG", 0.0),
        }
        for nota_id, pred in zip(non_empty.index, predictions)
    ]
    return pd.DataFrame(rows).set_index("nota_id")


def load_or_compute_tone(
    df: pd.DataFrame,
    cache_path: str | Path,
    model_name: str = DEFAULT_MODEL_NAME,
    chunk_size: int = CHUNK_SIZE,
) -> pd.DataFrame:
    """`df` debe tener columnas `nota_id`/`cuerpo_texto` (una fila por nota). Devuelve
    `nota_id`/`tono`/`polaridad_score`, reusando `cache_path` para notas cuyo `cuerpo_texto`
    no cambió desde la última corrida (hash del texto) y calculando solo lo nuevo.

    Lo pendiente se procesa en lotes de `chunk_size`, persistiendo el cache después de cada
    lote — si la corrida se interrumpe a mitad (ej. desconexión de Colab), lo ya cacheado no
    se pierde y la próxima corrida retoma desde ahí en vez de recalcular todo de nuevo.
    """
    cache_path = Path(cache_path)
    cache = pd.read_parquet(cache_path) if cache_path.exists() else pd.DataFrame(columns=_CACHE_COLUMNS)

    work = df[["nota_id", "cuerpo_texto"]].drop_duplicates(subset="nota_id").copy()
    work["cuerpo_texto"] = work["cuerpo_texto"].fillna("")
    work["text_hash"] = work["cuerpo_texto"].map(_text_hash)

    merged = work.merge(cache[["nota_id", "text_hash", "tono", "polaridad_score"]], on=["nota_id", "text_hash"], how="left")
    pending = merged[merged["tono"].isna() & (merged["cuerpo_texto"].str.strip() != "")]

    if not pending.empty:
        pending_ids = pending["nota_id"].tolist()
        total_chunks = (len(pending_ids) + chunk_size - 1) // chunk_size
        pending_texts = pending.set_index("nota_id")["cuerpo_texto"]
        analyzer = _load_analyzer(model_name)

        for i in range(0, len(pending_ids), chunk_size):
            chunk_ids = pending_ids[i : i + chunk_size]
            print(
                f"[nlp_tone] lote {i // chunk_size + 1}/{total_chunks} "
                f"({len(chunk_ids)} notas, {i + len(chunk_ids)}/{len(pending_ids)} acumuladas)"
            )
            scored = score_tone(pending_texts.loc[chunk_ids], model_name=model_name, analyzer=analyzer).reset_index()
            scored = scored.merge(work[["nota_id", "text_hash"]], on="nota_id", how="left")

            stale = cache[~cache["nota_id"].isin(scored["nota_id"])]
            cache = scored[_CACHE_COLUMNS] if stale.empty else pd.concat(
                [stale, scored[_CACHE_COLUMNS]], ignore_index=True
            )
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache.to_parquet(cache_path, index=False)

        merged = work.merge(cache[["nota_id", "text_hash", "tono", "polaridad_score"]], on=["nota_id", "text_hash"], how="left")

    return merged[["nota_id", "tono", "polaridad_score"]]
