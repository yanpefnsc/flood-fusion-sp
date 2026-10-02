from __future__ import annotations

import json
from pathlib import Path
import re
import unicodedata
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo


SAO_PAULO = ZoneInfo("America/Sao_Paulo")
WEEKDAYS = {
    "segunda": 0,
    "terca": 1,
    "quarta": 2,
    "quinta": 3,
    "sexta": 4,
    "sabado": 5,
    "domingo": 6,
}
MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

_CLOCK = r"\d{1,2}(?:h\d{2}|:\d{2}|h)"
_WEEKDAY = r"(?:segunda|ter[cç]a|quarta|quinta|sexta|s[aá]bado|domingo)(?:-feira)?"
_DATE_WORD = (
    r"(?:hoje|ontem|anteontem|amanh[aã]|"
    r"(?:(?:na|no|desta|deste|nesta|neste)\s+)?"
    r"(?:(?:[uú]ltima|[uú]ltimo|passada|passado|pr[oó]xima|pr[oó]ximo)\s+)?"
    + _WEEKDAY
    + r"(?:\s*\(\s*\d{1,2}\s*\))?|"
    r"\d{1,2}/\d{1,2}/\d{2,4}|"
    r"\d{1,2}\s+de\s+[a-zçãé]+(?:\s+de\s+\d{4})?)"
)
_DAYPART_LEAD = r"(?:(?:no|na)\s+)?(?:(?:fim|in[ií]cio)\s+da\s+)?(?:de\s+)?(?:madrugada|manh[aã]|tarde|noite)\s+(?:de|do|da|desta|deste|nesta|neste)\s+"
_DAYPART_SUFFIX = r"(?:\s+(?:pela\s+)?(?:de\s+)?(?:manh[aã]|madrugada)|\s+(?:a|à)\s+(?:tarde|noite))?"
_RANGE_RE = re.compile(rf"\b(?:das?\s+)?(?P<start>{_CLOCK})\s+à?s\s+(?P<end>{_CLOCK})\b", re.I)
_DATE_RE = re.compile(
    rf"\b(?:{_DAYPART_LEAD})?{_DATE_WORD}{_DAYPART_SUFFIX}"
    rf"(?:\s+(?:às?|por\s+volta\s+das?)\s+{_CLOCK})?(?=$|[^\w])",
    re.I,
)
_TIME_RE = re.compile(rf"\b(?:às?|por\s+volta\s+das?)\s+(?P<clock>{_CLOCK})\b", re.I)
_ANY_CLOCK_RE = re.compile(_CLOCK, re.I)


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _anchor_datetime(anchor: str | date | datetime) -> datetime:
    if isinstance(anchor, str):
        value = datetime.fromisoformat(anchor.replace("Z", "+00:00"))
    elif isinstance(anchor, datetime):
        value = anchor
    else:
        value = datetime.combine(anchor, time.min)
    if value.tzinfo is None:
        return value.replace(tzinfo=SAO_PAULO)
    return value.astimezone(SAO_PAULO)


def _resolve_date(expression: str, anchor: datetime) -> date:
    folded = _fold(expression)
    if "anteontem" in folded:
        return anchor.date() - timedelta(days=2)
    if re.search(r"\bontem\b", folded):
        return anchor.date() - timedelta(days=1)
    if re.search(r"\bhoje\b", folded):
        return anchor.date()
    if re.search(r"\bamanha\b", folded):
        return anchor.date() + timedelta(days=1)

    numeric_date = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", folded)
    if numeric_date:
        day, month, year = (int(part) for part in numeric_date.groups())
        if year < 100:
            year += 2000
        return date(year, month, day)

    written_date = re.search(r"\b(\d{1,2})\s+de\s+([a-z]+)(?:\s+de\s+(\d{4}))?", folded)
    if written_date and written_date.group(2) in MONTHS:
        year = int(written_date.group(3) or anchor.year)
        return date(year, MONTHS[written_date.group(2)], int(written_date.group(1)))

    weekday_match = re.search(
        r"\b(segunda|terca|quarta|quinta|sexta|sabado|domingo)(?:-feira)?\b", folded
    )
    if weekday_match:
        explicit_day = re.search(r"\(\s*(\d{1,2})\s*\)", folded)
        if explicit_day:
            day_number = int(explicit_day.group(1))
            candidate = date(anchor.year, anchor.month, day_number)
            if candidate > anchor.date():
                previous_month = (anchor.month - 2) % 12 + 1
                previous_year = anchor.year - (1 if anchor.month == 1 else 0)
                candidate = date(previous_year, previous_month, day_number)
            return candidate

        target_weekday = WEEKDAYS[weekday_match.group(1)]
        if re.search(r"\b(?:ultima|ultimo|passada|passado|anterior)\b", folded):
            offset = (anchor.weekday() - target_weekday) % 7 or 7
            return anchor.date() - timedelta(days=offset)
        if re.search(r"\b(?:proxima|proximo)\b", folded):
            offset = (target_weekday - anchor.weekday()) % 7 or 7
            return anchor.date() + timedelta(days=offset)
        offset = (anchor.weekday() - target_weekday) % 7
        return anchor.date() - timedelta(days=offset)

    try:
        import dateparser

        parsed = dateparser.parse(
            expression,
            languages=["pt"],
            settings={"RELATIVE_BASE": anchor.replace(tzinfo=None)},
        )
        if parsed:
            return parsed.date()
    except ImportError:
        pass
    return anchor.date()


def _clock_value(expression: str) -> time | None:
    match = _ANY_CLOCK_RE.search(expression)
    if not match:
        return None
    token = match.group(0).casefold().replace(":", "h")
    hour_text, _, minute_text = token.partition("h")
    hour = int(hour_text)
    minute = int(minute_text) if minute_text else 0
    if hour > 23 or minute > 59:
        return None
    return time(hour, minute)


def _daypart_time(expression: str) -> tuple[time, time] | None:
    folded = _fold(expression)
    if "madrugada" in folded:
        return time(0, 0), time(5, 59, 59)
    if "manha" in folded:
        return time(6, 0), time(11, 59, 59)
    if "tarde" in folded:
        return time(12, 0), time(17, 59, 59)
    if "noite" in folded:
        return time(18, 0), time(23, 59, 59)
    return None


def _iso_local(day: date, clock: time) -> str:
    return datetime.combine(day, clock, tzinfo=SAO_PAULO).isoformat(timespec="seconds")


def normalize_temporal_expression(
    expression: str, anchor: str | date | datetime
) -> dict[str, Any]:
    anchor_dt = _anchor_datetime(anchor)
    day = _resolve_date(expression, anchor_dt)
    time_range = _RANGE_RE.search(expression)
    if time_range:
        start_clock = _clock_value(time_range.group("start"))
        end_clock = _clock_value(time_range.group("end"))
        if start_clock and end_clock:
            start = datetime.combine(day, start_clock, tzinfo=SAO_PAULO)
            end = datetime.combine(day, end_clock, tzinfo=SAO_PAULO)
            if end < start:
                end += timedelta(days=1)
            return {
                "text": expression,
                "kind": "interval",
                "start": start.isoformat(timespec="seconds"),
                "end": end.isoformat(timespec="seconds"),
                "precision": "minute" if ":" in time_range.group("start") or ("h" in time_range.group("start").lower() and len(time_range.group("start").split("h")[-1]) == 2) else "hour",
                "estimated": False,
                "normalizer": "portuguese_rules",
            }

    explicit_clock = _TIME_RE.search(expression)
    clock = _clock_value(explicit_clock.group("clock")) if explicit_clock else None

    if clock:
        start = datetime.combine(day, clock, tzinfo=SAO_PAULO)
        end = start + timedelta(hours=1)
        precision = "minute" if explicit_clock and (":" in explicit_clock.group("clock") or len(explicit_clock.group("clock").split("h")[-1]) == 2) else "hour"
        return {
            "text": expression,
            "kind": "point",
            "start": start.isoformat(timespec="seconds"),
            "end": end.isoformat(timespec="seconds"),
            "value": _iso_local(day, clock),
            "precision": precision,
            "estimated": False,
            "normalizer": "portuguese_rules",
        }

    daypart = _daypart_time(expression)
    if daypart:
        start_clock, end_clock = daypart
        start = datetime.combine(day, start_clock, tzinfo=SAO_PAULO)
        end = datetime.combine(day, end_clock, tzinfo=SAO_PAULO)
        return {
            "text": expression,
            "kind": "interval",
            "start": start.isoformat(timespec="seconds"),
            "end": end.isoformat(timespec="seconds"),
            "value": _iso_local(day, time(15) if "tarde" in _fold(expression) else time(9) if "manha" in _fold(expression) else time(21) if "noite" in _fold(expression) else time(5)),
            "precision": "part_of_day",
            "estimated": True,
            "normalizer": "portuguese_rules",
        }

    start = datetime.combine(day, time.min, tzinfo=SAO_PAULO)
    end = datetime.combine(day, time.max, tzinfo=SAO_PAULO)
    return {
        "text": expression,
        "kind": "point",
        "start": start.isoformat(timespec="seconds"),
        "end": end.isoformat(timespec="seconds"),
        "value": _iso_local(day, time.min),
        "precision": "date",
        "estimated": True,
        "normalizer": "portuguese_rules",
    }


def extract_temporal_mentions(text: str, anchor: str | date | datetime) -> list[dict[str, Any]]:
    candidates: list[tuple[int, int, str]] = []
    for match in _RANGE_RE.finditer(text):
        candidates.append((match.start(), match.end(), match.group(0)))
    for match in _DATE_RE.finditer(text):
        candidates.append((match.start(), match.end(), match.group(0)))
    for match in _TIME_RE.finditer(text):
        candidates.append((match.start(), match.end(), match.group(0)))

    candidates.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    accepted: list[tuple[int, int, str]] = []
    for candidate in candidates:
        if any(candidate[0] < end and candidate[1] > start for start, end, _ in accepted):
            continue
        accepted.append(candidate)
    return [normalize_temporal_expression(raw, anchor) for _, _, raw in accepted]


def normalizar_expressao_tempo(expressao: str, t0: datetime) -> tuple[datetime, datetime]:
    res = normalize_temporal_expression(expressao, t0)
    return datetime.fromisoformat(res["start"]), datetime.fromisoformat(res["end"])


def processar_noticias_temporais(
    input_path: str = "data/processed/noticias_anotadas.jsonl",
    output_path: str = "data/processed/noticias_temporais.jsonl",
) -> None:
    src = Path(input_path)
    dst = Path(output_path)
    dst.parent.mkdir(parents=True, exist_ok=True)

    with src.open("r", encoding="utf-8") as f_in, dst.open("w", encoding="utf-8") as f_out:
        for line in f_in:
            if not line.strip():
                continue
            item = json.loads(line)

            pub_raw = item.get("published_at") or item.get("data_coleta")
            anchor = _anchor_datetime(pub_raw) if pub_raw else datetime.now(SAO_PAULO)

            entidades_raw = item.get("entities", [])
            entidades_tempo = []

            for ent in entidades_raw:
                if isinstance(ent, dict):
                    if ent.get("type") == "TEMPO" or ent.get("label") == "TEMPO":
                        texto = ent.get("text") or ent.get("entity") or ""
                        if texto:
                            entidades_tempo.append(str(texto))
                elif isinstance(ent, (list, tuple)) and len(ent) >= 2:
                    if "TEMPO" in str(ent):
                        entidades_tempo.append(str(ent[0]))
                elif isinstance(ent, str) and ent.strip():
                    entidades_tempo.append(ent.strip())

            janelas = []
            if entidades_tempo:
                for texto_ent in entidades_tempo:
                    norm = normalize_temporal_expression(texto_ent, anchor)
                    janelas.append({
                        "inicio_evento": norm["start"],
                        "fim_evento": norm["end"],
                        "texto": texto_ent,
                        "detalhes": norm,
                    })

            if not janelas:
                corpo = item.get("body") or item.get("corpo_texto") or ""
                mencoes = extract_temporal_mentions(corpo, anchor)
                if mencoes:
                    for m in mencoes:
                        janelas.append({
                            "inicio_evento": m["start"],
                            "fim_evento": m["end"],
                            "texto": m["text"],
                            "detalhes": m,
                        })
                else:
                    ini = anchor - timedelta(hours=2)
                    fim = anchor
                    janelas.append({
                        "inicio_evento": ini.isoformat(timespec="seconds"),
                        "fim_evento": fim.isoformat(timespec="seconds"),
                        "texto": "fallback_publicacao",
                    })

            item["janelas_temporais"] = janelas
            item["inicio_evento"] = janelas[0]["inicio_evento"]
            item["fim_evento"] = janelas[0]["fim_evento"]

            f_out.write(json.dumps(item, ensure_ascii=False) + "\n")


__all__ = [
    "extract_temporal_mentions",
    "normalize_temporal_expression",
    "normalizar_expressao_tempo",
    "processar_noticias_temporais",
]

if __name__ == "__main__":
    processar_noticias_temporais()