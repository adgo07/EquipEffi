from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.enrich_pump_source_pages import CHEMICAL_PAGE, WATER_PAGE, enrich_payload, run


class PumpSourcePageTests(unittest.TestCase):
    def test_water_and_chemical_pages_are_added_without_value_changes(self):
        payload = {
            "water": {"ci": [{"data_id": "W1", "ci": [1, 2, 3]}, {"data_id": "W2", "source_pages": "old", "ci": [4, 5, 6]}]},
            "chemical": {"level_offsets": [{"data_id": "C1", "offsets": [1, 2, 3]}]},
        }
        before = json.loads(json.dumps(payload, ensure_ascii=False))
        self.assertEqual(enrich_payload(payload), {"added": 2, "unchanged": 1, "unknown": 0})
        self.assertEqual(payload["water"]["ci"][0]["source_pages"], WATER_PAGE)
        self.assertEqual(payload["chemical"]["level_offsets"][0]["source_pages"], CHEMICAL_PAGE)
        for scope, key in (("water", "ci"), ("chemical", "level_offsets")):
            for index, row in enumerate(payload[scope][key]):
                self.assertEqual(row.get("ci", row.get("offsets")), before[scope][key][index].get("ci", before[scope][key][index].get("offsets")))

    def test_preview_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pump.json"
            path.write_text(json.dumps({"water": {"ci": [{"data_id": "W1"}]}, "chemical": {"level_offsets": []}}), encoding="utf-8")
            before = path.read_text(encoding="utf-8")
            result = run(path)
            self.assertEqual(result["added"], 1)
            self.assertFalse(result["payload_changed"])
            self.assertEqual(path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
