from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.enrich_submersible_source_pages import TABLE_PAGES, enrich_payload, run


class SubmersibleSourcePageTests(unittest.TestCase):
    def test_table_pages_are_added_without_changing_record_values(self):
        payload = {"tables": [
            {"name": "表1", "offsets": {"1": [2]}},
            {"name": "表2", "offsets": {"1": [3]}},
            {"name": "表6", "source_pages": "old", "offsets": {"1": [4]}},
        ]}
        before = json.loads(json.dumps(payload, ensure_ascii=False))
        self.assertEqual(enrich_payload(payload), {"added": 2, "unchanged": 1, "unknown": 0})
        self.assertEqual(payload["tables"][0]["source_pages"], "4")
        self.assertEqual(payload["tables"][1]["source_pages"], "4-5")
        self.assertEqual(payload["tables"][2]["source_pages"], "old")
        for index, row in enumerate(payload["tables"]):
            self.assertEqual(row["offsets"], before["tables"][index]["offsets"])
        self.assertEqual(set(TABLE_PAGES), {"表1", "表2", "表3", "表4", "表6"})

    def test_preview_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "submersible.json"
            path.write_text(json.dumps({"tables": [{"name": "表1"}]}), encoding="utf-8")
            before = path.read_text(encoding="utf-8")
            result = run(path)
            self.assertEqual(result["added"], 1)
            self.assertFalse(result["payload_changed"])
            self.assertEqual(path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
