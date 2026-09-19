from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from tools.enrich_motor_source_pages import (
    HV_TABLE_PAGES,
    LV_SOURCE_PAGE,
    enrich_hv_payload,
    enrich_lv_payload,
    run,
)


ROOT = Path(__file__).resolve().parents[2]


class MotorSourcePagesTests(unittest.TestCase):
    def test_explicit_page_mappings_are_idempotent_and_do_not_change_values(self):
        lv = json.loads((ROOT / "src/equipeffi/resources/standards/motor_lv.json").read_text(encoding="utf-8"))
        hv = json.loads((ROOT / "src/equipeffi/resources/standards/motor_hv.json").read_text(encoding="utf-8"))
        lv_values = copy.deepcopy(lv["rows"])
        hv_values = copy.deepcopy(hv["tables"])
        self.assertEqual(enrich_lv_payload(lv)["source_page"], LV_SOURCE_PAGE)
        hv_result = enrich_hv_payload(hv)
        self.assertEqual(hv_result["unknown_table"], 0)
        self.assertEqual(
            [table["source_pages"] for table in hv["tables"]],
            list(HV_TABLE_PAGES.values()),
        )
        self.assertEqual(lv["rows"], lv_values)
        # 只允许增加来源上下文，不得修改表格的值行。
        for before, after in zip(hv_values, hv["tables"]):
            after = dict(after)
            after.pop("source_pages", None)
            before = dict(before)
            before.pop("source_pages", None)
            self.assertEqual(after, before)
        self.assertEqual(enrich_lv_payload(lv)["unchanged"], 1)
        self.assertEqual(enrich_hv_payload(hv)["unchanged"], len(HV_TABLE_PAGES))

    def test_current_resources_need_no_additional_page_changes(self):
        result = run()
        self.assertFalse(result["low_voltage"]["payload_changed"])
        self.assertFalse(result["high_voltage"]["payload_changed"])
        self.assertEqual(result["high_voltage"]["unknown_table"], 0)


if __name__ == "__main__":
    unittest.main()
