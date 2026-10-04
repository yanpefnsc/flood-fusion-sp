"""Read-only integration contracts for the dashboard's data adapter."""
import json
import tempfile
import unittest
from pathlib import Path

from web_server import load_dashboard


class DashboardDataTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "raw").mkdir()
        (self.root / "processed").mkdir()

    def write(self, relative, value):
        (self.root / relative).write_text(value, encoding="utf-8")

    def test_missing_outputs_do_not_fabricate_fusion_or_geometry(self):
        self.write("processed/cge_itaquera.csv", "via_registrada,status_intransitabilidade,data_hora_inicio,data_hora_fim\nR TESTE,Transitável,2024-01-18T16:30:00-03:00,\n")
        result = load_dashboard(self.root)
        self.assertEqual(len(result["records"]), 1)
        self.assertEqual(result["records"][0]["status_via"], "Transitável")
        self.assertIsNone(result["records"][0]["geometry"])
        self.assertIsNone(result["records"][0]["confianca_geral"])
        self.assertFalse(result["fusion_available"])
        self.assertEqual(result["fused"], [])

    def test_article_stages_merge_without_losing_annotations(self):
        self.write("raw/news.jsonl", json.dumps({"id": "same", "title": "Title"}))
        self.write("processed/noticias_anotadas.jsonl", json.dumps({"id": "same", "entities": {"LOGRADOURO": [{"text": "Rua X"}]}}))
        result = load_dashboard(self.root)
        self.assertEqual(len(result["articles"]), 1)
        self.assertEqual(len(result["articles"][0]["files"]), 2)
        self.assertEqual(result["articles"][0]["raw"]["entities"]["LOGRADOURO"][0]["text"], "Rua X")

    def test_malformed_line_does_not_hide_other_sources(self):
        self.write("raw/news.jsonl", '{bad json}\n'+json.dumps({"id": "valid", "body": "Text"}))
        result = load_dashboard(self.root)
        self.assertEqual(len(result["articles"]), 1)
        self.assertEqual(len(result["warnings"]), 1)
        self.assertEqual(result["files"][0]["count"], 1)

    def test_new_geojson_is_read_without_server_restart(self):
        self.assertFalse(load_dashboard(self.root)["fusion_available"])
        geometry = {"type": "LineString", "coordinates": [[-46.45, -23.54], [-46.46, -23.55]]}
        collection = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": geometry, "properties": {"logradouro": "Rua X", "status_fusao": "APENAS_CGE", "confianca_geral": 0.85}}]}
        self.write("processed/intransitabilidade_itaquera_final.geojson", json.dumps(collection))
        result = load_dashboard(self.root)
        self.assertTrue(result["fusion_available"])
        self.assertEqual(result["fused"][0]["geometry"], geometry)
        self.assertEqual(result["fused"][0]["confianca_geral"], 0.85)

    def test_invalid_geojson_is_reported_as_unavailable(self):
        self.write("processed/intransitabilidade_itaquera_final.geojson", '{"type":"Point","coordinates":[0,0]}')
        result = load_dashboard(self.root)
        self.assertFalse(result["fusion_available"])
        self.assertFalse(result["files"][0]["available"])
        self.assertTrue(result["warnings"])


if __name__ == "__main__":
    unittest.main()
