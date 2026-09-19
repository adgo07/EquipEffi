from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.enrich_compressor_source_pages import TABLE_PAGES, enrich_payload, run


class CompressorSourcePageTests(unittest.TestCase):
    def test_page_ranges_cover_machine_tables_without_changing_values(self):
        payload = {"rows": [
            {"table": "表1", "power_kw": 1.5, "specific_power": 5.8},
            {"table": "表4", "power_kw": 4, "specific_power": 8.6},
            {"table": "表1", "power_kw": 3, "source_pages": "old", "specific_power": 6.5},
        ]}
        before = [(r["power_kw"], r["specific_power"]) for r in payload["rows"]]
        self.assertEqual(set(TABLE_PAGES), {"表1", "表2", "表3", "表4"})
        self.assertEqual(enrich_payload(payload), {"added": 2, "unchanged": 1, "unknown_table": 0})
        self.assertEqual(payload["rows"][0]["source_pages"], "5-7")
        self.assertEqual(payload["rows"][1]["source_pages"], "12-13")
        self.assertEqual(before, [(r["power_kw"], r["specific_power"]) for r in payload["rows"]])

    def test_preview_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "compressor.json"
            path.write_text(json.dumps({"rows": [{"table": "表1", "power_kw": 1.5}]}), encoding="utf-8")
            before = path.read_text(encoding="utf-8")
            result = run(path)
            self.assertEqual(result["added"], 1)
            self.assertFalse(result["payload_changed"])
            self.assertEqual(path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
