"""Frozen-mapping regressions for transformer rated-voltage scope edges."""

from __future__ import annotations

import json
import unittest
from decimal import Decimal
from pathlib import Path

from equipeffi.domain.devices.transformer import TransformerCalculator, condition_options


ROOT = Path(__file__).resolve().parents[2]
PACK_PATH = ROOT / "src" / "equipeffi" / "resources" / "standards" / "gb20052_2024_v21.json"

# Table 19 in the frozen GB20052 V2.1 mapping gives inclusive HV/LV limits and
# the first valid capacity for each renewable-transformer table.
VOLTAGE_SCOPE = {
    29: ("6", "7.2", "0.4", "1.14", "500"),
    30: ("6", "7.2", "0.4", "1.14", "500"),
    31: ("10", "12", "0.4", "1.14", "500"),
    32: ("10", "12", "0.4", "1.14", "500"),
    33: ("35", "38.5", "0.4", "1.14", "1000"),
    34: ("35", "38.5", "0.4", "1.14", "1000"),
    35: ("66", "72.5", "0.4", "1.14", "3150"),
}


class TransformerVoltageBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
        cls.calculator = TransformerCalculator()

    @staticmethod
    def values(table_no: int, capacity: str) -> dict[str, str]:
        category_id = f"GB20052-T{table_no:02d}"
        option = condition_options(category_id)[0]
        return {
            "category_id": category_id,
            "capacity_kva": capacity,
            "standard_conditions": option.condition_id,
        }

    def test_all_renewable_voltage_interval_endpoints_are_in_scope(self) -> None:
        for table_no, (hv_min, hv_max, lv_min, lv_max, capacity) in VOLTAGE_SCOPE.items():
            base = self.values(table_no, capacity)
            hv_mid = str((Decimal(hv_min) + Decimal(hv_max)) / 2)
            lv_mid = str((Decimal(lv_min) + Decimal(lv_max)) / 2)
            endpoints = (
                ("hv_min", {"hv_rated_voltage_kv": hv_min, "lv_rated_voltage_kv": lv_mid}),
                ("hv_max", {"hv_rated_voltage_kv": hv_max, "lv_rated_voltage_kv": lv_mid}),
                ("lv_min", {"hv_rated_voltage_kv": hv_mid, "lv_rated_voltage_kv": lv_min}),
                ("lv_max", {"hv_rated_voltage_kv": hv_mid, "lv_rated_voltage_kv": lv_max}),
            )
            for edge, voltages in endpoints:
                with self.subTest(table=table_no, edge=edge):
                    result = self.calculator.evaluate({**base, **voltages}, self.pack)
                    self.assertEqual(result.evaluation_status, "INSUFFICIENT_DATA")
                    self.assertEqual(result.missing_fields, ("no_load_loss_w", "load_loss_w"))

    def test_each_winding_range_is_checked_independently_before_missing_data(self) -> None:
        epsilon = Decimal("0.0001")
        for table_no, (hv_min, hv_max, lv_min, lv_max, capacity) in VOLTAGE_SCOPE.items():
            base = self.values(table_no, capacity)
            hv_mid = str((Decimal(hv_min) + Decimal(hv_max)) / 2)
            lv_mid = str((Decimal(lv_min) + Decimal(lv_max)) / 2)
            out_of_range = (
                ("hv_below_lv_missing", {"hv_rated_voltage_kv": str(Decimal(hv_min) - epsilon)}),
                ("hv_above_lv_missing", {"hv_rated_voltage_kv": str(Decimal(hv_max) + epsilon)}),
                ("lv_below_hv_missing", {"lv_rated_voltage_kv": str(Decimal(lv_min) - epsilon)}),
                ("lv_above_hv_missing", {"lv_rated_voltage_kv": str(Decimal(lv_max) + epsilon)}),
            )
            for case, voltages in out_of_range:
                with self.subTest(table=table_no, case=case):
                    result = self.calculator.evaluate({**base, **voltages}, self.pack)
                    self.assertEqual(result.evaluation_status, "OUT_OF_STANDARD_SCOPE")
                    self.assertEqual(result.reason_codes, ("OUTSIDE_VOLTAGE_RANGE",))

            missing_hv = self.calculator.evaluate({
                **base, "lv_rated_voltage_kv": lv_mid,
            }, self.pack)
            missing_lv = self.calculator.evaluate({
                **base, "hv_rated_voltage_kv": hv_mid,
            }, self.pack)
            missing_both = self.calculator.evaluate(base, self.pack)
            with self.subTest(table=table_no, case="in_range_hv_missing"):
                self.assertEqual(missing_hv.evaluation_status, "INSUFFICIENT_DATA")
                self.assertIn("hv_rated_voltage_kv", missing_hv.missing_fields)
            with self.subTest(table=table_no, case="in_range_lv_missing"):
                self.assertEqual(missing_lv.evaluation_status, "INSUFFICIENT_DATA")
                self.assertIn("lv_rated_voltage_kv", missing_lv.missing_fields)
            with self.subTest(table=table_no, case="both_missing"):
                self.assertEqual(missing_both.evaluation_status, "INSUFFICIENT_DATA")
                self.assertIn("hv_rated_voltage_kv", missing_both.missing_fields)
                self.assertIn("lv_rated_voltage_kv", missing_both.missing_fields)


if __name__ == "__main__":
    unittest.main()
