from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.enrich_heat_treatment_source_pages import TABLE8_PAGE, enrich_payload, run


class HeatTreatmentSourcePageTests(unittest.TestCase):
    def test_table8_page_is_added_without_changing_values(self):
        payload = {"table8": [
            {"furnace": "传送式连续炉", "level": [330, 390, 470]},
            {"furnace": "辊底炉", "source_page": 77, "level": [300, 400, 520]},
        ]}
        before = [row["level"] for row in payload["table8"]]
        self.assertEqual(enrich_payload(payload), {"added": 1, "unchanged": 1})
        self.assertEqual(payload["table8"][0]["source_page"], TABLE8_PAGE)
        self.assertEqual(payload["table8"][1]["source_page"], 77)
        self.assertEqual(before, [row["level"] for row in payload["table8"]])

    def test_preview_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "heat_treatment.json"
            path.write_text(json.dumps({"table8": [{"furnace": "传送式连续炉"}]}), encoding="utf-8")
            before = path.read_text(encoding="utf-8")
            result = run(path)
            self.assertEqual(result["added"], 1)
            self.assertFalse(result["payload_changed"])
            self.assertEqual(path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
