"""Download CGE flood records from SAISP's public historical rain reports.

The SAISP archive embeds the CGE/PMSP flood-point bulletin in each report.
Times are local to São Paulo and are written as ISO 8601 with the UTC offset.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date, datetime, time, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ARCHIVE_URL = "https://www.saisp.br/historic"
SAO_PAULO = ZoneInfo("America/Sao_Paulo")
CSV_FIELDS = [
    "data_hora_inicio",
    "data_hora_fim",
    "via_registrada",
    "sentido",
    "status_intransitabilidade",
    "ponto_referencia",
    "subprefeitura",
    "fonte_url",
]
RECORD_RE = re.compile(
    r"Local:\s*(?P<via>.*?)\s+"
    r"Refer.ncia:\s*(?P<referencia>.*?)\s+"
    r"Sentido:\s*(?P<sentido>.*?)\s+"
    r"In.cio:\s*(?P<inicio>\d{2}:\d{2}:\d{2})\s+"
    r"T.rmino:\s*(?P<fim>.*?)\s+"
    r"Observa..o:\s*(?P<status>.+)$",
    re.IGNORECASE,
)
DATE_PREFIX_RE = re.compile(r"^(?P<date>\d{2}/\d{2}/\d{4})\s+(?P<area>.*?)\s+Local:", re.I)


class _ParagraphParser(HTMLParser):
    """Collect paragraph text without needing a browser or HTML dependency."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paragraphs: list[str] = []
        self._current: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "p":
            self._current = []
        elif tag.lower() == "br" and self._current is not None:
            self._current.append(" ")

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._current.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "p" and self._current is not None:
            self.paragraphs.append(" ".join("".join(self._current).split()))
            self._current = None


def _iso_local(day: date, clock: str) -> datetime:
    parsed_time = time.fromisoformat(clock)
    return datetime.combine(day, parsed_time, tzinfo=SAO_PAULO)


def parse_report(html: str, source_url: str) -> list[dict[str, str]]:
    """Extract Itaquera records from the report's embedded CGE bulletin."""
    parser = _ParagraphParser()
    parser.feed(html)
    records: list[dict[str, str]] = []

    for paragraph in parser.paragraphs:
        prefix = DATE_PREFIX_RE.match(paragraph)
        if not prefix or not prefix.group("area").casefold().startswith("itaquera"):
            continue

        match = RECORD_RE.search(paragraph)
        if not match:
            raise ValueError(f"Formato inesperado no registro do CGE: {paragraph}")

        occurrence_date = datetime.strptime(prefix.group("date"), "%d/%m/%Y").date()
        start = _iso_local(occurrence_date, match.group("inicio"))
        end_text = match.group("fim").strip()
        end = _iso_local(occurrence_date, end_text) if end_text else None
        if end and end < start:
            end += timedelta(days=1)

        records.append(
            {
                "data_hora_inicio": start.isoformat(timespec="seconds"),
                "data_hora_fim": end.isoformat(timespec="seconds") if end else "",
                "via_registrada": match.group("via").strip(),
                "sentido": match.group("sentido").strip(),
                "status_intransitabilidade": match.group("status").strip(),
                "ponto_referencia": match.group("referencia").strip(),
                "subprefeitura": "Itaquera",
                "fonte_url": source_url,
            }
        )

    return records


def _report_url(day: date) -> str:
    return f"{ARCHIVE_URL}/{day:%Y%m}/dia{day.day:02d}/"


def fetch_day(day: date, timeout: int = 45) -> list[dict[str, str]]:
    url = _report_url(day)
    request = Request(url, headers={"User-Agent": "flood-fusion-sp/1.0 (public data research)"})
    try:
        with urlopen(request, timeout=timeout) as response:
            html = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        if exc.code == 404:
            return []
        raise
    return parse_report(html, url)


def download_period(start: date, end: date) -> list[dict[str, str]]:
    if end < start:
        raise ValueError("A data final precisa ser igual ou posterior à data inicial.")

    records: list[dict[str, str]] = []
    day = start
    while day <= end:
        for row in fetch_day(day):
            occurrence_day = date.fromisoformat(row["data_hora_inicio"][:10])
            if start <= occurrence_day <= end:
                records.append(row)
        day += timedelta(days=1)

    # Archived pages may repeat a point across successive report editions.
    unique: dict[tuple[str, str, str, str, str], dict[str, str]] = {}
    for row in records:
        key = (
            row["data_hora_inicio"],
            row["data_hora_fim"],
            row["via_registrada"],
            row["ponto_referencia"],
            row["status_intransitabilidade"],
        )
        unique[key] = row
    return sorted(unique.values(), key=lambda row: (row["data_hora_inicio"], row["via_registrada"]))


def write_csv(rows: list[dict[str, str]], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2024, 1, 17), help="Data inicial (AAAA-MM-DD)")
    parser.add_argument("--end", type=date.fromisoformat, default=date(2024, 1, 18), help="Data final (AAAA-MM-DD)")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/cge_itaquera.csv"),
        help="Caminho do CSV de saída",
    )
    args = parser.parse_args()

    try:
        rows = download_period(args.start, args.end)
        write_csv(rows, args.output)
    except Exception as exc:  # Report network and source format failures clearly to the CLI user.
        print(f"Falha ao obter os dados do CGE: {exc}", file=sys.stderr)
        return 1

    print(f"{len(rows)} ocorrência(s) gravada(s) em {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
