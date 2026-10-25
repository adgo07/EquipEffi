from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import tools.enrich_motor_source_pages as source_page_tool
from tools.enrich_motor_source_pages import (
    HV_TABLE_PAGES,
    enrich_hv_payload,
    run,
)

ROOT = Path(__file__).resolve().parents[2]


class MotorSourcePagesTests(unittest.TestCase):
    def test_high_voltage_page_mapping_is_explicit_and_idempotent(self):
        hv = json.loads(
            (ROOT / "src/equipeffi/resources/standards/motor_hv.json")
            .read_text(encoding="utf-8"))
        original_values = copy.deepcopy(hv["tables"])
        first = enrich_hv_payload(hv)
        second = enrich_hv_payload(hv)
        self.assertEqual(first["added"], 0)
        self.assertEqual(first["unknown_table"], 0)
        self.assertEqual(second["unchanged"], len(HV_TABLE_PAGES))
        self.assertEqual(
            [table["source_pages"] for table in hv["tables"]],
            list(HV_TABLE_PAGES.values()),
        )
        for before, after in zip(original_values, hv["tables"]):
            after = dict(after)
            before = dict(before)
            after.pop("source_pages", None)
            before.pop("source_pages", None)
            self.assertEqual(after, before)

    def test_current_tool_only_updates_high_voltage_pack(self):
        result = run()
        self.assertFalse(result["high_voltage"]["payload_changed"])
        self.assertNotIn("low_voltage", result)
        self.assertFalse(hasattr(source_page_tool, "enrich_lv_payload"))


if __name__ == "__main__":
    unittest.main()