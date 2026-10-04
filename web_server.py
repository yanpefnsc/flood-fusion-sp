"""Local, read-only dashboard for the existing Flood Fusion datasets.

Run: python web_server.py --port 8765
No extra packages are required. The pipeline remains independent.
"""
from __future__ import annotations

import argparse
import csv
import json
import mimetypes
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "frontend"
DATA = ROOT / "data"


def load_dashboard(data_dir: Path = DATA) -> dict:
    warnings = []
    inventory = []
    articles = {}
    cge = []
    collections = {}
    for path in sorted(data_dir.rglob("*")):
        if not path.is_file() or path.suffix not in {".csv", ".jsonl", ".geojson"}:
            continue
        relative = path.relative_to(data_dir).as_posix()
        entry = {"path": relative, "name": path.name, "size": path.stat().st_size,
                 "modified": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                 "count": 0, "available": True}
        inventory.append(entry)
        try:
            if path.suffix == ".csv":
                with path.open(encoding="utf-8-sig", newline="") as source:
                    rows = list(csv.DictReader(source))
                entry["count"] = len(rows)
                if path.name == "cge_itaquera.csv":
                    cge = rows
            elif path.suffix == ".jsonl":
                rows = []
                for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                        if not isinstance(row, dict):
                            raise ValueError("registro deve ser um objeto")
                        rows.append(row)
                    except (ValueError, TypeError) as exc:
                        warnings.append(f"{relative}, linha {number}: {exc}")
                entry["count"] = len(rows)
                for row in rows:
                    key = row.get("id") or row.get("article_id") or row.get("source_url") or row.get("url") or f"{relative}:{len(articles)}"
                    existing = articles.setdefault(key, {"files": [], "raw": {}})
                    existing["files"].append(relative)
                    # Keep enrichment even when the raw file is read afterwards.
                    existing["raw"].update(row)
            else:
                collection = json.loads(path.read_text(encoding="utf-8-sig"))
                if collection.get("type") != "FeatureCollection" or not isinstance(collection.get("features"), list):
                    raise ValueError("GeoJSON deve ser uma FeatureCollection")
                entry["count"] = len(collection["features"])
                collections[path.name] = collection
        except (ValueError, OSError, TypeError, AttributeError) as exc:
            entry["available"] = False
            warnings.append(f"Não foi possível ler {relative}: {exc}")

    final = collections.get("intransitabilidade_itaquera_final.geojson")
    records = []
    for index, row in enumerate(cge):
        records.append({"id": f"cge-{index}", "kind": "cge", "logradouro": row.get("via_registrada", "Via não informada"),
                        "inicio_evento": row.get("data_hora_inicio"), "fim_evento": row.get("data_hora_fim"),
                        "status_via": row.get("status_intransitabilidade", "Não informado"),
                        "status_fusao": "NAO_PROCESSADO", "fontes": "CGE / SAISP", "confianca_geral": None,
                        "referencia": row.get("ponto_referencia", ""), "sentido": row.get("sentido", ""),
                        "source_url": row.get("fonte_url", ""), "geometry": None, "original": row})
    fused = []
    if final is not None:
        for index, feature in enumerate(final["features"]):
            props = feature.get("properties") or {}
            fused.append({**props, "id": f"fusion-{index}", "kind": "fusion", "status_via": "Intransitável",
                          "geometry": feature.get("geometry"), "original": props})
    return {"records": records, "fused": fused, "fusion_available": final is not None,
            "articles": [{"id": key, **value} for key, value in articles.items()],
            "layers": collections, "files": inventory, "warnings": warnings,
            "loaded_at": datetime.now(timezone.utc).isoformat()}


class DashboardHandler(BaseHTTPRequestHandler):
    def respond(self, body: bytes, content_type: str, status: int = 200, filename: str | None = None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = unquote(urlparse(self.path).path)
        if route == "/api/dashboard":
            try:
                self.respond(json.dumps(load_dashboard(), ensure_ascii=False).encode(), "application/json; charset=utf-8")
            except OSError:
                self.respond(b'{"error":"Falha ao ler os arquivos locais."}', "application/json", 500)
            return
        if route.startswith("/api/files/"):
            relative = route.removeprefix("/api/files/")
            path = (DATA / relative).resolve()
            if not path.is_relative_to(DATA.resolve()) or path.suffix not in {".csv", ".jsonl", ".geojson"} or not path.is_file():
                self.send_error(404)
                return
            self.respond(path.read_bytes(), "application/octet-stream", filename=path.name)
            return
        path = (WEB / (route.lstrip("/") or "index.html")).resolve()
        if not path.is_relative_to(WEB.resolve()) or not path.is_file():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix == ".js":
            content_type = "text/javascript"
        self.respond(path.read_bytes(), content_type + ("; charset=utf-8" if path.suffix in {".html", ".css", ".js"} else ""))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), DashboardHandler)
    print(f"Flood Fusion SP: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
