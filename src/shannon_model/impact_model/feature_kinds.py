"""Clasificación actionable vs diagnostic de features del engine de impacto en vistas.

Consumida por `editorial_ops` para filtrar qué features pueden aparecer en una receta
editorial (`actionable`) vs cuáles son atribución/identidad y quedan fuera (`diagnostic`).
"""

from __future__ import annotations

# feature_id -> tipo de valor para la capa de receta editorial.
ACTIONABLE_FEATURES: dict[str, str] = {
    "num_palabras": "numeric",
    "num_letras": "numeric",
    "largo_titulo": "numeric",
    "num_imagenes_real": "numeric",
    "num_etiquetas": "numeric",
    "num_parrafos": "numeric",
    "tiene_signo_pregunta": "binary",
    "tiene_numero": "binary",
    "tiene_mayusculas_excesivas": "binary",
    "tiene_subtitulos": "binary",
    "tiene_video_embed": "binary",
    "es_fin_de_semana": "binary",
    "hora_del_dia": "hour",
}

# Subconjunto de ACTIONABLE_FEATURES que entra a la receta v0 (editorial_ops.recipe).
# Título: una sola regla (largo_titulo) en vez de 4 — tiene_signo_pregunta/tiene_numero/
# tiene_mayusculas_excesivas siguen siendo actionable (no diagnostic) pero no se usan como
# reglas independientes de la receta, para no multiplicar condiciones simultáneas del título.
RECIPE_FEATURES: dict[str, str] = {
    "num_palabras": "numeric",
    "num_letras": "numeric",
    "largo_titulo": "numeric",
    "num_imagenes_real": "numeric",
    "num_etiquetas": "numeric",
    "num_parrafos": "numeric",
    "tiene_subtitulos": "binary",
    "tiene_video_embed": "binary",
    "es_fin_de_semana": "binary",
    "hora_del_dia": "hour",
}

# Atribución/identidad: nunca entran a la receta ni al tip.
DIAGNOSTIC_FEATURES = ("autor_nombre", "autor_avg_views", "autor_num_notas", "source")

LEVER_LABELS: dict[str, str] = {
    "num_palabras": "Longitud del cuerpo",
    "num_letras": "Caracteres del cuerpo",
    "largo_titulo": "Longitud del título",
    "num_imagenes_real": "Imágenes en el cuerpo",
    "num_etiquetas": "Etiquetas",
    "num_parrafos": "Párrafos",
    "tiene_signo_pregunta": "Título con pregunta",
    "tiene_numero": "Título con número",
    "tiene_mayusculas_excesivas": "Título en mayúsculas",
    "tiene_subtitulos": "Subtítulos en el cuerpo",
    "tiene_video_embed": "Video embebido",
    "es_fin_de_semana": "Publicar en fin de semana",
    "hora_del_dia": "Hora de publicación",
}


def feature_kind(feature_id: str) -> str:
    """'actionable' o 'diagnostic' para un feature_id del training frame o del dataset de notas."""
    if feature_id in ACTIONABLE_FEATURES:
        return "actionable"
    if feature_id in DIAGNOSTIC_FEATURES or feature_id.startswith("source_") or feature_id.startswith("autor_"):
        return "diagnostic"
    return "diagnostic"
