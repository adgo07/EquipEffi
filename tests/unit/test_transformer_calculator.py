"""Standard-backed boundary tests for the independent transformer calculator."""

from __future__ import annotations

import copy
import json
import unittest
from decimal import Decimal, localcontext
from pathlib import Path

from equipeffi.domain.devices.transformer import (
    TransformerCalculator,
    TransformerPackError,
    condition_options,
)


ROOT = Path(__file__).resolve().parents[2]
PACK_PATH = ROOT / "src" / "equipeffi" / "resources" / "standards" / "gb20052_2024_v21.json"


class TransformerCalculatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
        cls.calculator = TransformerCalculator()

    @staticmethod
    def condition_id(table_no: int, **expected: str) -> str:
        return next(
            option.condition_id
            for option in condition_options(f"GB20052-T{table_no:02d}")
            if all(option.values.get(key) == value for key, value in expected.items())
        )

    @staticmethod
    def source_capacities(result) -> set[str]:
        return {
            str(source["capacity_kva"])
            for branch in result.trace
            for source in branch["sources"]
        }

    @staticmethod
    def grade_from_source_row(row, no_load_loss: Decimal, load_loss: Decimal) -> str:
        thresholds = row["thresholds_w"]
        for level in ("1", "2", "3"):
            if (
                no_load_loss <= Decimal(thresholds[f"grade_{level}"]["no_load_loss"])
                and load_loss <= Decimal(thresholds[f"grade_{level}"]["load_loss"])
            ):
                return level
        return "BELOW_MINIMUM"

    @staticmethod
    def physical_input_for_row(table, row) -> dict[str, str]:
        """Build real input fields from a source row's physical branch facts."""
        table_no = table["table_no"]
        category_id = table["table_id"]
        values = {"category_id": category_id, "capacity_kva": row["capacity_kva"]}

        row_conditions = row["conditions"]
        normalized_condition_keys = {
            "core_material", "vector_group", "thermal_class", "renewable_type",
        }
        physical_conditions = {
            key: value for key, value in row_conditions.items()
            if key in normalized_condition_keys and value is not None
        }
        options = condition_options(category_id)
        if options:
            option = next(
                candidate for candidate in options
                if all(candidate.values.get(key) == value for key, value in physical_conditions.items())
            )
            values["standard_conditions"] = option.condition_id

        if table_no == 2:
            values["uk_rated_percent"] = (
                "4" if row_conditions["uk_group"] == "uk_4_0" else "7"
            )
        elif table_no == 15:
            values["lv_rated_voltage_kv"] = (
                "66" if row_conditions["loss_group"] == "lv_66_69_special" else "35"
            )
        elif table_no in {8, 14}:
            values["lv_rated_voltage_kv"] = "35" if table_no == 8 else "66"

        if table_no in {27, 28}:
            group = row_conditions["uk_group"]
            impedances = {
                (27, "A"): ("12", "36", "21"),
                (27, "B"): ("12", "44", "29"),
                (27, "C"): ("18", "50", "35"),
                (28, "A"): ("12", "36", "21"),
                (28, "B"): ("12", "44", "29"),
                (28, "C"): ("14.5", "44", "29"),
            }
            hm, hl, ml = impedances[(table_no, group)]
            values.update({
                "uk_hm_rated_percent": hm,
                "uk_hl_rated_percent": hl,
                "uk_ml_rated_percent": ml,
            })

        if table_no >= 29:
            hv_by_class = {29: "6", 30: "6", 31: "10", 32: "10", 33: "35", 34: "35", 35: "66"}
            values["hv_rated_voltage_kv"] = hv_by_class[table_no]
            values["lv_rated_voltage_kv"] = "0.4"
        return values

    def test_other_uncertain_and_invalid_category_have_distinct_business_meaning(self) -> None:
        other = self.calculator.evaluate({"category_id": "OTHER_CATEGORY"}, {})
        uncertain = self.calculator.evaluate({"category_id": "UNCERTAIN_CATEGORY"}, {})
        invalid = self.calculator.evaluate({"category_id": "not-a-transformer"}, self.pack)
        self.assertEqual((other.evaluation_status, other.ui_conclusion), ("OUT_OF_STANDARD_SCOPE", "不在范围"))
        self.assertIsNone(uncertain.evaluation_status)
        self.assertEqual(uncertain.ui_conclusion, "无法判定")
        self.assertEqual((invalid.evaluation_status, invalid.ui_conclusion), ("INVALID_INPUT", "输入无效"))

    def test_missing_category_and_loss_are_insufficient_with_available_thresholds(self) -> None:
        missing_category = self.calculator.evaluate({}, self.pack)
        self.assertEqual(missing_category.evaluation_status, "INSUFFICIENT_DATA")
        self.assertEqual(missing_category.missing_fields, ("category_id",))

        partial = self.calculator.evaluate({
            "category_id": "GB20052-T01",
            "capacity_kva": "30",
            "standard_conditions": self.condition_id(
                1, core_material="electrical_steel", vector_group="dyn11_yzn11",
            ),
            "load_loss_w": "455",
        }, self.pack)
        self.assertEqual(partial.evaluation_status, "INSUFFICIENT_DATA")
        self.assertEqual(partial.missing_fields, ("no_load_loss_w",))
        self.assertEqual(partial.thresholds["no_load_loss_1"], Decimal("65"))
        self.assertEqual(partial.thresholds["load_loss_1"], Decimal("455"))
        self.assertTrue(partial.trace)
        self.assertIn("空载损耗", partial.explanation)
        self.assertNotIn("no_load_loss_w", partial.explanation)

    def test_table1_keeps_two_connections_and_the_shared_pk_source(self) -> None:
        results = []
        for vector in ("dyn11_yzn11", "yyn0"):
            values = {
                "category_id": "GB20052-T01",
                "capacity_kva": "630",
                "standard_conditions": self.condition_id(1, core_material="electrical_steel", vector_group=vector),
                "no_load_loss_w": "460",
                "load_loss_w": "4460",
            }
            result = self.calculator.evaluate(values, self.pack)
            results.append(result)
            self.assertEqual(result.grade, "1")
            self.assertEqual(result.thresholds["load_loss_1"], Decimal("4460"))
            self.assertEqual(result.trace[0]["sources"][0]["shared_source_label"], "Pk合并原格共享")
        self.assertEqual(results[0].thresholds, results[1].thresholds)
        self.assertNotEqual(results[0].trace[0]["branch_id"], results[1].trace[0]["branch_id"])

    def test_table2_630_impedance_branches_have_different_outcomes(self) -> None:
        expected = (("4.0", "3"), ("6.0", "2"))
        for impedance, grade in expected:
            result = self.calculator.evaluate({
                "category_id": "GB20052-T02",
                "capacity_kva": "630",
                "standard_conditions": self.condition_id(2, core_material="electrical_steel", thermal_class="B"),
                "uk_rated_percent": impedance,
                "no_load_loss_w": "800",
                "load_loss_w": "5000",
            }, self.pack)
            self.assertEqual(result.evaluation_status, "SUCCESS")
            self.assertEqual(result.grade, grade)
            self.assertIn("uk_group=uk_4_0" if impedance == "4.0" else "uk_group=uk_6_0_to_8_0", result.trace[0]["branch_id"])

    def test_table2_630_impedance_tolerance_edges_are_inclusive(self) -> None:
        condition = self.condition_id(2, core_material="electrical_steel", thermal_class="B")
        expected_groups = {
            "3.6": "uk_4_0", "4.4": "uk_4_0",
            "5.4": "uk_6_0_to_8_0", "8.8": "uk_6_0_to_8_0",
        }
        for impedance, expected_group in expected_groups.items():
            with self.subTest(impedance=impedance):
                result = self.calculator.evaluate({
                    "category_id": "GB20052-T02", "capacity_kva": "630",
                    "standard_conditions": condition, "uk_rated_percent": impedance,
                    "no_load_loss_w": "800", "load_loss_w": "5000",
                }, self.pack)
                self.assertEqual(result.evaluation_status, "SUCCESS")
                self.assertEqual(len(result.trace), 1)
                self.assertIn(f"uk_group={expected_group}", result.trace[0]["branch_id"])

        for impedance in ("3.5999", "4.4001", "5.3999", "8.8001"):
            with self.subTest(outside_impedance=impedance):
                result = self.calculator.evaluate({
                    "category_id": "GB20052-T02", "capacity_kva": "630",
                    "standard_conditions": condition, "uk_rated_percent": impedance,
                    "no_load_loss_w": "800", "load_loss_w": "5000",
                }, self.pack)
                self.assertEqual(result.evaluation_status, "INSUFFICIENT_DATA")
                self.assertEqual(result.reason_codes, ("IMPEDANCE_NO_MATCH",))

    def test_table2_interpolates_within_impedance_group_and_does_not_require_unrelated_uk(self) -> None:
        values = {
            "category_id": "GB20052-T02", "capacity_kva": "565",
            "standard_conditions": self.condition_id(2, core_material="electrical_steel", thermal_class="B"),
            "uk_rated_percent": "4.2",
        }
        result = self.calculator.evaluate(values, self.pack)
        self.assertEqual(result.evaluation_status, "INSUFFICIENT_DATA")
        self.assertEqual(result.trace[0]["lookup_method"], "interpolated")
        self.assertEqual(self.source_capacities(result), {"500", "630"})
        self.assertEqual(result.thresholds["no_load_loss_1"], Decimal("722.5"))

        unique_branch = self.calculator.evaluate({
            **values, "capacity_kva": "500", "uk_rated_percent": None,
        }, self.pack)
        self.assertEqual(unique_branch.evaluation_status, "INSUFFICIENT_DATA")
        self.assertNotIn("uk_rated_percent", unique_branch.missing_fields)
        self.assertTrue(unique_branch.thresholds)

    def test_table2_non630_ignores_provided_impedance_for_branch_and_grade(self) -> None:
        condition = self.condition_id(2, core_material="electrical_steel", thermal_class="B")
        expected_groups = {
            "500": "uk_4_0",
            "565": "uk_4_0",
            "629.999": "uk_4_0",
            "630.001": "uk_6_0_to_8_0",
            "715": "uk_6_0_to_8_0",
            "800": "uk_6_0_to_8_0",
        }
        for capacity, expected_group in expected_groups.items():
            results = []
            for impedance in (None, "4.0", "7.0"):
                values = {
                    "category_id": "GB20052-T02",
                    "capacity_kva": capacity,
                    "standard_conditions": condition,
                    "no_load_loss_w": "1",
                    "load_loss_w": "1",
                }
                if impedance is not None:
                    values["uk_rated_percent"] = impedance
                result = self.calculator.evaluate(values, self.pack)
                results.append(result)
                self.assertEqual(result.evaluation_status, "SUCCESS")
                self.assertEqual(result.grade, "1")
                self.assertIn(f"uk_group={expected_group}", result.trace[0]["branch_id"])

            self.assertEqual(results[0].thresholds, results[1].thresholds)
            self.assertEqual(results[0].thresholds, results[2].thresholds)
            self.assertEqual(results[0].trace, results[1].trace)
            self.assertEqual(results[0].trace, results[2].trace)

    def test_table15_uses_low_voltage_group_before_capacity(self) -> None:
        base = {
            "category_id": "GB20052-T15", "capacity_kva": "120000",
            "no_load_loss_w": "44000", "load_loss_w": "302000",
        }
        ordinary = self.calculator.evaluate({**base, "lv_rated_voltage_kv": "35"}, self.pack)
        special_66 = self.calculator.evaluate({**base, "lv_rated_voltage_kv": "66"}, self.pack)
        special_69 = self.calculator.evaluate({**base, "lv_rated_voltage_kv": "69"}, self.pack)
        self.assertEqual(ordinary.grade, "2")
        self.assertEqual(special_66.grade, "1")
        self.assertEqual(special_69.grade, "1")
        self.assertNotEqual(ordinary.thresholds, special_66.thresholds)
        self.assertEqual(special_66.thresholds, special_69.thresholds)
        self.assertIn("loss_group=lv_66_69_special", special_69.trace[0]["branch_id"])

        no_fallback = self.calculator.evaluate({
            **base, "capacity_kva": "100000", "lv_rated_voltage_kv": "66",
        }, self.pack)
        self.assertEqual(no_fallback.evaluation_status, "OUT_OF_STANDARD_SCOPE")
        self.assertEqual(no_fallback.reason_codes, ("OUTSIDE_TABLE_CAPACITY_RANGE",))
        missing_voltage = self.calculator.evaluate({"category_id": "GB20052-T15", "capacity_kva": "120000"}, self.pack)
        self.assertEqual(missing_voltage.missing_fields, ("lv_rated_voltage_kv",))

    def test_dedicated_tables_do_not_fall_back_to_general_voltage_table(self) -> None:
        table8 = self.calculator.evaluate({
            "category_id": "GB20052-T08", "capacity_kva": "75000", "lv_rated_voltage_kv": "35",
        }, self.pack)
        table14 = self.calculator.evaluate({
            "category_id": "GB20052-T14", "capacity_kva": "300000", "lv_rated_voltage_kv": "66",
        }, self.pack)
        self.assertEqual(table8.evaluation_status, "OUT_OF_STANDARD_SCOPE")
        self.assertEqual(table14.evaluation_status, "OUT_OF_STANDARD_SCOPE")
        conflict = self.calculator.evaluate({
            "category_id": "GB20052-T07", "capacity_kva": "6300", "lv_rated_voltage_kv": "35",
        }, self.pack)
        table12_conflict = self.calculator.evaluate({
            "category_id": "GB20052-T12", "capacity_kva": "160000", "lv_rated_voltage_kv": "66",
        }, self.pack)
        self.assertEqual(conflict.evaluation_status, "INVALID_INPUT")
        self.assertEqual(conflict.reason_codes, ("ROUTE_CONFLICT",))
        self.assertEqual(table12_conflict.evaluation_status, "INVALID_INPUT")
        self.assertEqual(table12_conflict.reason_codes, ("ROUTE_CONFLICT",))

    def test_t27_and_t28_same_threshold_impedance_multimatch_preserves_both_sources(self) -> None:
        for table_no in (27, 28):
            with self.subTest(table=table_no):
                result = self.calculator.evaluate({
                    "category_id": f"GB20052-T{table_no:02d}", "capacity_kva": "120000",
                    "uk_hm_rated_percent": "12.9", "uk_hl_rated_percent": "44", "uk_ml_rated_percent": "29",
                    "no_load_loss_w": "28000", "load_loss_w": "215000",
                }, self.pack)
                self.assertEqual(result.evaluation_status, "SUCCESS")
                self.assertEqual(result.grade, "1")
                self.assertEqual({branch["branch_id"] for branch in result.trace}, {
                    f"GB20052-T{table_no:02d}/uk_group=B",
                    f"GB20052-T{table_no:02d}/uk_group=C",
                })
                self.assertEqual(len(result.trace), 2)
                traced_ids = {
                    source["source_row_id"]
                    for branch in result.trace for source in branch["sources"]
                }
                source_ids = {
                    row["source_row_id"] for row in self.pack["tables"][table_no - 1]["rows"]
                    if row["capacity_kva"] == "120000"
                    and row["conditions"]["uk_group"] in {"B", "C"}
                }
                self.assertEqual(traced_ids, source_ids)
                source_row = next(
                    row for row in self.pack["tables"][table_no - 1]["rows"]
                    if row["capacity_kva"] == "120000" and row["conditions"]["uk_group"] == "B"
                )
                expected_thresholds = {
                    f"{metric}_{level}": Decimal(source_row["thresholds_w"][f"grade_{level}"][metric])
                    for level in ("1", "2", "3")
                    for metric in ("no_load_loss", "load_loss")
                }
                self.assertEqual(result.thresholds, expected_thresholds)

    def test_t27_different_threshold_multimatch_is_not_resolved_by_first_row(self) -> None:
        pack = copy.deepcopy(self.pack)
        table = pack["tables"][26]
        row_c = next(
            row for row in table["rows"]
            if row["capacity_kva"] == "120000" and row["conditions"]["uk_group"] == "C"
        )
        row_c["thresholds_w"]["grade_1"]["load_loss"] = "999999"
        result = self.calculator.evaluate({
            "category_id": "GB20052-T27", "capacity_kva": "120000",
            "uk_hm_rated_percent": "12.9", "uk_hl_rated_percent": "44", "uk_ml_rated_percent": "29",
            "no_load_loss_w": "28000", "load_loss_w": "215000",
        }, pack)
        self.assertEqual(result.evaluation_status, "INSUFFICIENT_DATA")
        self.assertEqual(result.reason_codes, ("BRANCH_AMBIGUOUS",))
        self.assertEqual(len(result.trace), 2)

    def test_t27_and_t28_impedance_tolerance_edges_use_all_three_values(self) -> None:
        cases = {
            "A_lower": (("10.8", "30.6", "18"), {"A"}),
            "A_upper": (("13.2", "41.8", "24.2"), {"A"}),
            "C_lower_overlaps_B": (("12.6", "37.8", "25.2"), {"B", "C"}),
            "B_upper_overlaps_C": (("13.2", "50.6", "33"), {"B", "C"}),
        }
        for table_no in (27, 28):
            c_upper = ("24.2", "70.4", "44") if table_no == 27 else ("16.5", "50.6", "33")
            table_cases = {**cases, "C_upper": (c_upper, {"C"})}
            for label, (impedances, expected_groups) in table_cases.items():
                with self.subTest(table=table_no, edge=label):
                    hm, hl, ml = impedances
                    result = self.calculator.evaluate({
                        "category_id": f"GB20052-T{table_no:02d}", "capacity_kva": "120000",
                        "uk_hm_rated_percent": hm, "uk_hl_rated_percent": hl,
                        "uk_ml_rated_percent": ml,
                        "no_load_loss_w": "1", "load_loss_w": "1",
                    }, self.pack)
                    self.assertEqual(result.evaluation_status, "SUCCESS")
                    self.assertEqual(
                        {branch["branch_id"].rsplit("=", 1)[-1] for branch in result.trace},
                        expected_groups,
                    )

            outside_hm = "24.2001" if table_no == 27 else "16.5001"
            no_match = self.calculator.evaluate({
                "category_id": f"GB20052-T{table_no:02d}", "capacity_kva": "120000",
                "uk_hm_rated_percent": outside_hm, "uk_hl_rated_percent": c_upper[1],
                "uk_ml_rated_percent": c_upper[2],
                "no_load_loss_w": "1", "load_loss_w": "1",
            }, self.pack)
            self.assertEqual(no_match.evaluation_status, "INSUFFICIENT_DATA")
            self.assertEqual(no_match.reason_codes, ("IMPEDANCE_NO_MATCH",))

    def test_new_energy_inputs_use_actual_voltage_and_decimal_interpolation(self) -> None:
        table29 = self.calculator.evaluate({
            "category_id": "GB20052-T29", "capacity_kva": "565",
            "standard_conditions": self.condition_id(29, renewable_type="wind"),
            "hv_rated_voltage_kv": "6", "lv_rated_voltage_kv": "0.4",
        }, self.pack)
        self.assertEqual(table29.evaluation_status, "INSUFFICIENT_DATA")
        self.assertEqual(table29.thresholds["no_load_loss_1"], Decimal("422.5"))
        self.assertEqual(table29.thresholds["load_loss_1"], Decimal("4180"))
        self.assertEqual(self.source_capacities(table29), {"500", "630"})

        table32 = self.calculator.evaluate({
            "category_id": "GB20052-T32", "capacity_kva": "3000",
            "standard_conditions": self.condition_id(32, renewable_type="photovoltaic", thermal_class="F"),
            "hv_rated_voltage_kv": "10", "lv_rated_voltage_kv": "0.4",
        }, self.pack)
        self.assertEqual(table32.evaluation_status, "INSUFFICIENT_DATA")
        with localcontext() as context:
            context.prec = 50
            self.assertEqual(table32.thresholds["no_load_loss_1"], Decimal(31440) / Decimal(13))
            self.assertEqual(table32.thresholds["load_loss_1"], Decimal(237285) / Decimal(13))
        self.assertEqual(self.source_capacities(table32), {"2500", "3150"})

        outside = self.calculator.evaluate({
            "category_id": "GB20052-T33", "capacity_kva": "1000",
            "standard_conditions": self.condition_id(33, renewable_type="storage"),
            "hv_rated_voltage_kv": "34.9", "lv_rated_voltage_kv": "0.4",
        }, self.pack)
        self.assertEqual(outside.evaluation_status, "OUT_OF_STANDARD_SCOPE")

    def test_full_decimal_comparison_and_temperature_evidence_are_not_gates(self) -> None:
        base = {
            "category_id": "GB20052-T01", "capacity_kva": "30",
            "standard_conditions": self.condition_id(1, core_material="electrical_steel", vector_group="dyn11_yzn11"),
            "no_load_loss_w": "65", "load_loss_w": "455",
        }
        equal = self.calculator.evaluate(base, self.pack)
        above = self.calculator.evaluate({**base, "load_loss_w": "455.0000000000000001"}, self.pack)
        self.assertEqual(equal.grade, "1")
        self.assertEqual(above.grade, "2")
        self.assertFalse(any("temperature" in field or "test" in field for field in above.missing_fields))

    def test_bad_numbers_are_invalid_and_pack_corruption_raises(self) -> None:
        valid = {
            "category_id": "GB20052-T01", "capacity_kva": "30",
            "standard_conditions": self.condition_id(1, core_material="electrical_steel", vector_group="dyn11_yzn11"),
            "no_load_loss_w": 65.0, "load_loss_w": "455",
        }
        invalid = self.calculator.evaluate(valid, self.pack)
        self.assertEqual(invalid.evaluation_status, "INVALID_INPUT")
        self.assertIn("空载损耗", invalid.explanation)
        self.assertNotIn("no_load_loss_w", invalid.explanation)
        self.assertEqual(invalid.reason_codes, ("INPUT_INVALID",))
        broken = copy.deepcopy(self.pack)
        broken["tables"][0]["rows"][0]["thresholds_w"]["grade_1"]["no_load_loss"] = "NaN"
        with self.assertRaises(TransformerPackError):
            self.calculator.evaluate({**valid, "no_load_loss_w": "65"}, broken)

    def test_every_source_row_routes_from_physical_inputs_and_checks_grade1_edges(self) -> None:
        source_rows = [
            (table, row)
            for table in self.pack["tables"]
            for row in table["rows"]
        ]
        self.assertEqual(len(source_rows), 589)

        for table, row in source_rows:
            with self.subTest(table=table["table_id"], source=row["source_row_id"]):
                values = self.physical_input_for_row(table, row)
                grade1 = row["thresholds_w"]["grade_1"]
                exact_no_load = Decimal(grade1["no_load_loss"])
                exact_load = Decimal(grade1["load_loss"])

                equal_result = self.calculator.evaluate({
                    **values,
                    "no_load_loss_w": str(exact_no_load),
                    "load_loss_w": str(exact_load),
                }, self.pack)
                self.assertEqual(equal_result.evaluation_status, "SUCCESS")
                self.assertEqual(equal_result.grade, "1")
                self.assertEqual(equal_result.thresholds, {
                    f"no_load_loss_{level}": Decimal(row["thresholds_w"][f"grade_{level}"]["no_load_loss"])
                    for level in ("1", "2", "3")
                } | {
                    f"load_loss_{level}": Decimal(row["thresholds_w"][f"grade_{level}"]["load_loss"])
                    for level in ("1", "2", "3")
                })
                self.assertEqual(copy.deepcopy(equal_result).thresholds, equal_result.thresholds)
                traced_sources = [
                    source for candidate in equal_result.trace for source in candidate["sources"]
                ]
                self.assertTrue(any(
                    source["source_row_id"] == row["source_row_id"]
                    and source["source_sheet"] == table["source_sheet"]
                    and source["source_row"] == row["source"]["row"]
                    for source in traced_sources
                ))

                for field, incremented_no_load, incremented_load in (
                    ("no_load_loss_w", exact_no_load + 1, exact_load),
                    ("load_loss_w", exact_no_load, exact_load + 1),
                ):
                    with self.subTest(overflow=field):
                        overflow_result = self.calculator.evaluate({
                            **values,
                            "no_load_loss_w": str(incremented_no_load),
                            "load_loss_w": str(incremented_load),
                        }, self.pack)
                        self.assertEqual(overflow_result.evaluation_status, "SUCCESS")
                        self.assertEqual(
                            overflow_result.grade,
                            self.grade_from_source_row(row, incremented_no_load, incremented_load),
                        )


if __name__ == "__main__":
    unittest.main()
