"""Extract street and landmark entities from Portuguese news text.

The deterministic rules cover the CGE's common address patterns. If a
Portuguese spaCy model is installed, its LOC/GPE/FAC predictions are added as
supporting candidates; the rule path remains available on its own.
"""

from __future__ import annotations

import re
from typing import Any


STREET_RE = re.compile(
    r"\b(?:avenida|av\.?|rua|r\.?|estrada|est\.?|rodovia|rod\.?|"
    r"alameda|al\.?|travessa|trv\.?|pra[cç]a|p[cç]\.?|marginal|"
    r"via|viaduto|ponte|largo|viela)\s+"
    r"[\wÀ-ÖØ-öø-ÿ'’.-]+(?:\s+(?!sentido\b|refer[eê]ncia\b|"
    r"subprefeitura\b|zona\b|bairro\b)[\wÀ-ÖØ-öø-ÿ'’.-]+){0,6}",
    re.IGNORECASE,
)
LANDMARK_RE = re.compile(
    r"\b(?:esta[cç][aã]o|terminal|shopping|hospital|parque|pra[cç]a|"
    r"ponte|viaduto|aeroporto|rio|c[oó]rrego|metr[oô]|mercado|universidade)\s+"
    r"[\wÀ-ÖØ-öø-ÿ]+(?:[-'’][\wÀ-ÖØ-öø-ÿ]+)*"
    r"(?:\s+(?:de|do|da|dos|das|e)\s+[\wÀ-ÖØ-öø-ÿ]+(?:[-'’][\wÀ-ÖØ-öø-ÿ]+)*"
    r"|\s+[\wÀ-ÖØ-öø-ÿ]+(?:[-'’][\wÀ-ÖØ-öø-ÿ]+)*){0,4}",
    re.IGNORECASE,
)
REFERENCE_CUE_RE = re.compile(
    r"\b(?:refer[eê]ncia|pr[oó]xim[oa]s?\s+(?:de|da|do|a|ao|à)|"
    r"perto\s+(?:de|da|do)|em\s+frente\s+(?:a|ao|à|da|do)|"
    r"ao\s+lado\s+(?:de|da|do)|na\s+altura\s+(?:de|da|do))\s+"
    r"(?P<place>[\wÀ-ÖØ-öø-ÿ'’.-]+(?:\s+[\wÀ-ÖØ-öø-ÿ'’.-]+){0,5})",
    re.IGNORECASE,
)
STREET_PREFIX_RE = re.compile(
    r"\b(?:avenida|av\.?|rua|r\.?|estrada|rodovia|alameda|travessa|"
    r"pra[cç]a|marginal|viaduto|ponte|largo|viela)\b\s*$",
    re.IGNORECASE,
)
LANDMARK_WORD_RE = re.compile(
    r"\b(?:esta[cç][aã]o|terminal|shopping|hospital|parque|pra[cç]a|"
    r"ponte|viaduto|aeroporto|rio|c[oó]rrego|metr[oô]|mercado|universidade)\b",
    re.IGNORECASE,
)


def load_portuguese_model(model_name: str = "pt_core_news_sm") -> tuple[Any | None, str | None]:
    """Load an optional installed spaCy Portuguese model without downloading it."""
    try:
        import spacy
    except ImportError:
        return None, None
    try:
        model = spacy.load(model_name)
    except (OSError, IOError):
        return None, None
    return model, model_name


def _entity(
    text: str, label: str, start: int, end: int, method: str, confidence: float
) -> dict[str, Any]:
    return {
        "text": text.strip(" ,.;:-"),
        "label": label,
        "start_char": start,
        "end_char": end,
        "method": method,
        "confidence": confidence,
    }


def extract_entities(text: str, nlp: Any | None = None) -> dict[str, list[dict[str, Any]]]:
    """Return [LOGRADOURO] and [PONTO_DE_REFERENCIA] spans."""
    entities: list[dict[str, Any]] = []
    occupied: set[tuple[int, int, str]] = set()

    def add(match: re.Match[str], label: str, method: str, confidence: float, start: int | None = None, end: int | None = None) -> None:
        entity_start = match.start() if start is None else start
        entity_end = match.end() if end is None else end
        key = (entity_start, entity_end, label)
        if key not in occupied:
            entities.append(_entity(text[entity_start:entity_end], label, entity_start, entity_end, method, confidence))
            occupied.add(key)

    for match in STREET_RE.finditer(text):
        add(match, "LOGRADOURO", "heuristica_endereco", 0.94)

    for match in LANDMARK_RE.finditer(text):
        add(match, "PONTO_DE_REFERENCIA", "heuristica_marco_geografico", 0.88)

    for match in REFERENCE_CUE_RE.finditer(text):
        place_start, place_end = match.span("place")
        place = text[place_start:place_end].rstrip(" ,.;:-")
        place_end = place_start + len(place)
        if place and not STREET_PREFIX_RE.search(text[max(0, place_start - 20) : place_start]):
            add(match, "PONTO_DE_REFERENCIA", "heuristica_contextual", 0.91, place_start, place_end)

    if nlp is not None:
        document = nlp(text)
        for predicted in getattr(document, "ents", []):
            if predicted.label_ not in {"LOC", "GPE", "FAC"}:
                continue
            left_context = text[max(0, predicted.start_char - 20) : predicted.start_char]
            if STREET_PREFIX_RE.search(left_context):
                prefix = STREET_PREFIX_RE.search(left_context)
                start = predicted.start_char - len(prefix.group(0))
                add(predicted, "LOGRADOURO", "spacy+heuristica", 0.82, start, predicted.end_char)
            elif LANDMARK_WORD_RE.search(predicted.text) or re.search(r"\b(?:pr[oó]ximo|perto|refer[eê]ncia)\b", left_context, re.I):
                add(
                    predicted,
                    "PONTO_DE_REFERENCIA",
                    "spacy+heuristica",
                    0.82,
                    predicted.start_char,
                    predicted.end_char,
                )

    entities.sort(key=lambda item: (item["start_char"], item["end_char"], item["label"]))
    return {
        "LOGRADOURO": [item for item in entities if item["label"] == "LOGRADOURO"],
        "PONTO_DE_REFERENCIA": [item for item in entities if item["label"] == "PONTO_DE_REFERENCIA"],
    }


__all__ = ["extract_entities", "load_portuguese_model"]
