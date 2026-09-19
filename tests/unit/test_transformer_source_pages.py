from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.enrich_transformer_source_pages import TABLE_PAGE, enrich_payload, run


class TransformerSourcePageTests(unittest.TestCase):
    def test_mapping_covers_all_transformer_tables_without_changing_values(self):
        payload = {
            "rows": [
                {"table": "表1", "capacity_kva": 30, "no_load_kw": [1, 2, 3]},
                {"table": "表35", "capacity_kva": 3150, "no_load_kw": [4, 5, 6]},
                {"table": "表1", "capacity_kva": 50, "source_page": 99, "no_load_kw": [7, 8, 9]},
            ]
        }
        before_values = [(r["capacity_kva"], r["no_load_kw"]) for r in payload["rows"]]
        counts = enrich_payload(payload)
        self.assertEqual(len(TABLE_PAGE), 35)
        self.assertEqual(counts, {"added": 2, "unchanged": 1, "unknown_table": 0})
        self.assertEqual(payload["rows"][0]["source_page"], 7)
        self.assertEqual(payload["rows"][1]["source_page"], 26)
        self.assertEqual(payload["rows"][2]["source_page"], 99)
        self.assertEqual(before_values, [(r["capacity_kva"], r["no_load_kw"]) for r in payload["rows"]])

    def test_preview_does_not_write_resource(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transformer.json"
            path.write_text(json.dumps({"rows": [{"table": "表1", "capacity_kva": 30}]}), encoding="utf-8")
            before = path.read_text(encoding="utf-8")
            result = run(path, apply=False)
            self.assertEqual(result["added"], 1)
            self.assertFalse(result["payload_changed"])
            self.assertEqual(path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
