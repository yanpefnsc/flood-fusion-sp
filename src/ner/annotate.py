"""Enrich news JSONL with normalized times and location entities."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.ner.entities import extract_entities, load_portuguese_model
from src.temporal.normalize import extract_temporal_mentions


def annotate_news(record: dict[str, Any], nlp: Any | None = None, model_name: str | None = None) -> dict[str, Any]:
    body = str(record.get("body", ""))
    published_at = record.get("published_at") or record.get("date")
    if not published_at:
        raise ValueError(f"Notícia sem published_at/date: {record.get('id', '<sem id>')}")
    result = dict(record)
    result["temporal_mentions"] = extract_temporal_mentions(body, published_at)
    result["entities"] = extract_entities(body, nlp=nlp)
    result["ner_model"] = model_name or "regras_portuguesas"
    return result


def annotate_jsonl(source: Path, destination: Path, model_name: str | None) -> int:
    nlp, loaded_model = load_portuguese_model(model_name) if model_name else load_portuguese_model()
    destination.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with source.open("r", encoding="utf-8-sig") as input_file, destination.open(
        "w", encoding="utf-8", newline="\n"
    ) as output_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                annotated = annotate_news(item, nlp=nlp, model_name=loaded_model)
            except Exception as exc:
                raise ValueError(f"Erro na linha {line_number} de {source}: {exc}") from exc
            output_file.write(json.dumps(annotated, ensure_ascii=False) + "\n")
            written += 1
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/raw/noticias_cge.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/noticias_anotadas.jsonl"))
    parser.add_argument("--spacy-model", default=None, help="Modelo spaCy português instalado (ex.: pt_core_news_lg)")
    args = parser.parse_args()
    try:
        count = annotate_jsonl(args.input, args.output, args.spacy_model)
    except Exception as exc:
        print(f"Falha ao anotar as notícias: {exc}", file=sys.stderr)
        return 1
    print(f"{count} notícia(s) anotada(s) em {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
