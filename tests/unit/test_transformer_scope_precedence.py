"""Regression coverage for transformer scope facts that precede missing fields."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from equipeffi.domain.devices.transformer import TransformerCalculator


ROOT = Path(__file__).resolve().parents[2]
PACK_PATH = ROOT / "src" / "equipeffi" / "resources" / "standards" / "gb20052_2024_v21.json"


class TransformerScopePrecedenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
        cls.calculator = TransformerCalculator()

    def test_known_outside_renewable_voltage_precedes_missing_fields(self) -> None:
        cases = (
            {"hv_rated_voltage_kv": "8", "lv_rated_voltage_kv": "0.4"},
            {"hv_rated_voltage_kv": "6", "lv_rated_voltage_kv": "1.2"},
            {"hv_rated_voltage_kv": "8"},
        )
        for voltage_values in cases:
            with self.subTest(voltage_values=voltage_values):
                result = self.calculator.evaluate({
                    "category_id": "GB20052-T29",
                    "capacity_kva": "500",
                    **voltage_values,
                }, self.pack)
                self.assertEqual(result.evaluation_status, "OUT_OF_STANDARD_SCOPE")
                self.assertEqual(result.reason_codes, ("OUTSIDE_VOLTAGE_RANGE",))
                self.assertEqual(result.missing_fields, ())

    def test_partial_in_range_voltage_remains_missing_data(self) -> None:
        result = self.calculator.evaluate({
            "category_id": "GB20052-T29",
            "capacity_kva": "500",
            "hv_rated_voltage_kv": "6",
        }, self.pack)
        self.assertEqual(result.evaluation_status, "INSUFFICIENT_DATA")
        self.assertEqual(result.missing_fields, ("lv_rated_voltage_kv",))

    def test_in_range_voltage_does_not_hide_missing_renewable_type(self) -> None:
        result = self.calculator.evaluate({
            "category_id": "GB20052-T29",
            "capacity_kva": "500",
            "hv_rated_voltage_kv": "6",
            "lv_rated_voltage_kv": "0.4",
        }, self.pack)
        self.assertEqual(result.evaluation_status, "INSUFFICIENT_DATA")
        self.assertEqual(result.missing_fields, ("renewable_type",))

    def test_capacity_above_every_table1_branch_precedes_missing_conditions(self) -> None:
        result = self.calculator.evaluate({
            "category_id": "GB20052-T01",
            "capacity_kva": "3000",
        }, self.pack)
        self.assertEqual(result.evaluation_status, "OUT_OF_STANDARD_SCOPE")
        self.assertEqual(result.reason_codes, ("OUTSIDE_TABLE_CAPACITY_RANGE",))
        self.assertEqual(result.missing_fields, ())

    def test_capacity_at_table1_overall_boundary_keeps_missing_conditions(self) -> None:
        result = self.calculator.evaluate({
            "category_id": "GB20052-T01",
            "capacity_kva": "2500",
        }, self.pack)
        self.assertEqual(result.evaluation_status, "INSUFFICIENT_DATA")
        self.assertEqual(result.missing_fields, ("core_material", "vector_group"))

    def test_table15_missing_selector_does_not_cross_branch_boundaries(self) -> None:
        base = {"category_id": "GB20052-T15", "capacity_kva": "100000"}
        missing_voltage = self.calculator.evaluate(base, self.pack)
        special_branch = self.calculator.evaluate({**base, "lv_rated_voltage_kv": "66"}, self.pack)
        ordinary_branch = self.calculator.evaluate({**base, "lv_rated_voltage_kv": "35"}, self.pack)
        missing_voltage_at_200000 = self.calculator.evaluate({
            **base, "capacity_kva": "200000",
        }, self.pack)
        ordinary_branch_at_200000 = self.calculator.evaluate({
            **base, "capacity_kva": "200000", "lv_rated_voltage_kv": "35",
        }, self.pack)

        self.assertEqual(missing_voltage.evaluation_status, "INSUFFICIENT_DATA")
        self.assertEqual(missing_voltage.missing_fields, ("lv_rated_voltage_kv",))
        self.assertEqual(special_branch.evaluation_status, "OUT_OF_STANDARD_SCOPE")
        self.assertEqual(special_branch.reason_codes, ("OUTSIDE_TABLE_CAPACITY_RANGE",))
        self.assertEqual(ordinary_branch.evaluation_status, "INSUFFICIENT_DATA")
        self.assertEqual(set(ordinary_branch.missing_fields), {"no_load_loss_w", "load_loss_w"})
        self.assertTrue(ordinary_branch.thresholds)
        self.assertIn("loss_group=ordinary", ordinary_branch.trace[0]["branch_id"])
        self.assertEqual(missing_voltage_at_200000.evaluation_status, "INSUFFICIENT_DATA")
        self.assertEqual(missing_voltage_at_200000.missing_fields, ("lv_rated_voltage_kv",))
        self.assertEqual(ordinary_branch_at_200000.evaluation_status, "OUT_OF_STANDARD_SCOPE")
        self.assertIn("31500～180000kVA", ordinary_branch_at_200000.explanation)

    def test_table15_capacity_below_all_branches_is_out_without_selector(self) -> None:
        result = self.calculator.evaluate({
            "category_id": "GB20052-T15",
            "capacity_kva": "20000",
        }, self.pack)
        self.assertEqual(result.evaluation_status, "OUT_OF_STANDARD_SCOPE")
        self.assertEqual(result.reason_codes, ("OUTSIDE_TABLE_CAPACITY_RANGE",))

    def test_capacity_above_every_autotransformer_branch_precedes_missing_impedances(self) -> None:
        missing_impedances = (
            "uk_hm_rated_percent",
            "uk_hl_rated_percent",
            "uk_ml_rated_percent",
        )
        for table_no in (27, 28):
            with self.subTest(table=table_no):
                outside = self.calculator.evaluate({
                    "category_id": f"GB20052-T{table_no:02d}",
                    "capacity_kva": "500000",
                }, self.pack)
                inside = self.calculator.evaluate({
                    "category_id": f"GB20052-T{table_no:02d}",
                    "capacity_kva": "400000",
                }, self.pack)
                self.assertEqual(outside.evaluation_status, "OUT_OF_STANDARD_SCOPE")
                self.assertEqual(outside.reason_codes, ("OUTSIDE_TABLE_CAPACITY_RANGE",))
                self.assertEqual(inside.evaluation_status, "INSUFFICIENT_DATA")
                self.assertEqual(inside.missing_fields, missing_impedances)

    def test_capacity_above_t02_all_branches_precedes_missing_conditions(self) -> None:
        result = self.calculator.evaluate({
            "category_id": "GB20052-T02",
            "capacity_kva": "3000",
        }, self.pack)
        self.assertEqual(result.evaluation_status, "OUT_OF_STANDARD_SCOPE")
        self.assertEqual(result.reason_codes, ("OUTSIDE_TABLE_CAPACITY_RANGE",))

    def test_route_conflict_remains_invalid_even_when_capacity_is_out(self) -> None:
        result = self.calculator.evaluate({
            "category_id": "GB20052-T08",
            "capacity_kva": "300000",
            "lv_rated_voltage_kv": "34.9",
        }, self.pack)
        self.assertEqual(result.evaluation_status, "INVALID_INPUT")
        self.assertEqual(result.reason_codes, ("ROUTE_CONFLICT",))


if __name__ == "__main__":
    unittest.main()
