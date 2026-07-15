"""Extracción de campos estructurados (etapa 1 del diccionario) desde el HTML de una nota."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

_LD_JSON_RE = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
_UPPERCASE_WORD_RE = re.compile(r"\b[A-ZÁÉÍÓÚÑ]{3,}\b")
_VIDEO_DOMAINS = ("youtube.com", "facebook.com/plugins/video")


class NoNewsArticleError(ValueError):
    """El HTML no trae un bloque JSON-LD NewsArticle utilizable."""


def _find_news_article(html: str) -> dict[str, Any]:
    for raw in _LD_JSON_RE.findall(html):
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            continue
        candidates = data if isinstance(data, list) else [data]
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("@type") == "NewsArticle":
                return candidate
    raise NoNewsArticleError("no JSON-LD found")


def _cyclical(value: float, period: float) -> tuple[float, float]:
    angle = 2 * math.pi * value / period
    return math.sin(angle), math.cos(angle)


def temporal_features(dt: datetime) -> dict[str, Any]:
    hora_sin, hora_cos = _cyclical(dt.hour, 24)
    dia_semana = dt.weekday()  # 0=lunes ... 6=domingo, igual que dt.weekday()
    dia_sin, dia_cos = _cyclical(dia_semana, 7)
    mes_sin, mes_cos = _cyclical(dt.month - 1, 12)
    return {
        "fecha_publicacion": dt.isoformat(),
        "hora_del_dia": dt.hour,
        "hora_sin": hora_sin,
        "hora_cos": hora_cos,
        "dia_semana": dia_semana,
        "dia_sin": dia_sin,
        "dia_cos": dia_cos,
        "es_fin_de_semana": int(dia_semana >= 5),
        "mes": dt.month,
        "mes_sin": mes_sin,
        "mes_cos": mes_cos,
    }


def title_signals(titulo: str) -> dict[str, int]:
    """Señales baratas de forma del título, sin NLP: pregunta, número, mayúsculas excesivas."""
    return {
        "tiene_signo_pregunta": int("?" in titulo),
        "tiene_numero": int(any(ch.isdigit() for ch in titulo)),
        "tiene_mayusculas_excesivas": int(bool(_UPPERCASE_WORD_RE.search(titulo))),
    }


def body_stats(html: str) -> dict[str, Any]:
    """Señales del cuerpo (`div.texto-noticia`), no del JSON-LD."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find(attrs={"itemprop": "articleBody"}) or soup.find("div", class_="texto-noticia")
    if body is None:
        return {
            "num_palabras": 0,
            "num_letras": 0,
            "num_imagenes_real": 0,
            "num_parrafos": 0,
            "tiene_subtitulos": 0,
            "tiene_video_embed": 0,
            "cuerpo_texto": "",
        }

    text = body.get_text(separator=" ", strip=True)
    iframe_srcs = [tag.get("src", "") or "" for tag in body.find_all("iframe")]
    # Solo cuenta como video embed real si el iframe es de youtube/facebook video,
    # para no confundir con iframes de ads (ej. slots de Google Publisher Tag).
    tiene_video_embed = int(
        bool(body.find("video"))
        or any(domain in src for src in iframe_srcs for domain in _VIDEO_DOMAINS)
    )

    return {
        "num_palabras": len(text.split()),
        "num_letras": len(text),
        "num_imagenes_real": len(body.find_all("img")),
        "num_parrafos": len(body.find_all("p")),
        "tiene_subtitulos": int(bool(body.find(["h2", "h3"]))),
        "tiene_video_embed": tiene_video_embed,
        "cuerpo_texto": text,
    }


def extract_note_fields(html: str, url: str, categoria_nota: str) -> dict[str, Any]:
    """Extrae campos de la etapa 1 del diccionario. Levanta NoNewsArticleError si falta el JSON-LD."""
    article = _find_news_article(html)

    # `image` del JSON-LD son variantes de resolución de la imagen hero, no el
    # conteo real de imágenes del cuerpo (por eso num_imagenes_real se calcula aparte).
    images = article.get("image", [])
    if isinstance(images, str):
        images = [images]
    num_imagenes = len(images)

    keywords = article.get("keywords", "") or ""
    etiquetas = [k.strip() for k in keywords.split(",") if k.strip()]

    author = article.get("author", {})
    if isinstance(author, list):
        author = author[0] if author else {}

    published = datetime.fromisoformat(article["datePublished"])
    titulo = article.get("headline", "")

    fields: dict[str, Any] = {
        "url": url,
        "titulo": titulo,
        "largo_titulo": len(titulo),
        "autor_nombre": author.get("name", ""),
        "autor_slug": author.get("url", ""),
        "num_imagenes": num_imagenes,
        "tiene_img_principal": int(num_imagenes > 0),
        "num_etiquetas": len(etiquetas),
        "categoria_nota": categoria_nota,
    }
    fields.update(body_stats(html))
    fields.update(title_signals(titulo))
    fields.update(temporal_features(published))
    return fields
