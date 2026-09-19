from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.enrich_standard_data_ids import enrich_manifest, enrich_payload


class StandardDataIdTests(unittest.TestCase):
    def test_enrich_payload_only_adds_ids_and_preserves_values(self):
        payload = {
            "standard_code": "GB 12345-2024",
            "rows": [
                {"power_kw": 1.5, "efficiency": [90, 91, 92]},
                {"power_kw": 3.0, "efficiency": [93, 94, 95], "data_id": "existing"},
            ],
        }
        before = json.loads(json.dumps(payload, ensure_ascii=False))
        self.assertEqual(enrich_payload(payload, "GB 12345-2024", Path("example.json")), 1)
        self.assertEqual(payload["rows"][1]["data_id"], "existing")
        self.assertEqual(payload["rows"][0]["efficiency"], before["rows"][0]["efficiency"])
        self.assertTrue(payload["rows"][0]["data_id"].startswith("GB12345-R"))

    def test_manifest_preview_does_not_write_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "pack.json"
            source.write_text(json.dumps({"standard_code": "GB 12345-2024", "rows": [{"efficiency": 1}]}), encoding="utf-8")
            manifest = root / "standard_manifest.json"
            manifest.write_text(json.dumps({"packs": [{"device_type": "demo", "standard_code": "GB 12345-2024", "source": "pack.json"}]}), encoding="utf-8")
            before = source.read_text(encoding="utf-8")
            result = enrich_manifest(manifest, apply=False)
            self.assertEqual(result["total_added"], 1)
            self.assertEqual(source.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
