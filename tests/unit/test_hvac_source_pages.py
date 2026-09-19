from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.enrich_hvac_source_pages import DEVICE_TABLE_PAGES, enrich_payload, run


class HvacSourcePageTests(unittest.TestCase):
    def test_table_pages_are_added_without_changing_thresholds(self):
        payload = {"devices": {
            "heat_pump_water_heater": {"records": [{"data_id": "H1", "table": "表1", "thresholds": [4.6]}]},
            "duct_ac": {"records": [{"data_id": "D1", "table": "表2", "thresholds": [3.4]}]},
            "unitary_ac": {"records": [{"data_id": "U1", "table": "表1", "source_page": "old", "thresholds": [4.5]}]},
            "multi_split_ac": {"records": [{"data_id": "M1", "table": "表4", "thresholds": [3.4]}]},
        }}
        before = json.loads(json.dumps(payload, ensure_ascii=False))
        self.assertEqual(enrich_payload(payload), {"added": 3, "unchanged": 1, "unknown": 0})
        self.assertEqual(payload["devices"]["heat_pump_water_heater"]["records"][0]["source_page"], "PDF第4页")
        self.assertEqual(payload["devices"]["duct_ac"]["records"][0]["source_page"], "PDF第4页")
        self.assertEqual(payload["devices"]["multi_split_ac"]["records"][0]["source_page"], "PDF第5页")
        for device in DEVICE_TABLE_PAGES:
            for index, row in enumerate(payload["devices"][device]["records"]):
                self.assertEqual(row.get("thresholds"), before["devices"][device]["records"][index].get("thresholds"))

    def test_preview_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hvac_thresholds.json"
            path.write_text(json.dumps({"devices": {"heat_pump_water_heater": {"records": [{"data_id": "H1", "table": "表1"}]}}}), encoding="utf-8")
            before = path.read_text(encoding="utf-8")
            result = run(path)
            self.assertEqual(result["added"], 1)
            self.assertFalse(result["payload_changed"])
            self.assertEqual(path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
