from __future__ import annotations

import unittest
from decimal import Decimal, getcontext, localcontext
from pathlib import Path
from unittest.mock import patch

from equipeffi.domain.common.enums import ComparisonDirection, Conclusion
from equipeffi.domain.evaluation.evaluators.pump import (
    PUMP_DECIMAL_CONTEXT,
    PUMP_NUMERIC_PRECISION,
    ChemicalPumpEvaluator,
    WaterPumpEvaluator,
    _specific_speed,
)
from equipeffi.domain.evaluation.grading import grade_three
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository


ROOT = Path(__file__).resolve().parents[2]


class PumpNumericContractV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo = JsonStandardRepository(ROOT)
        cls.water_pack = repo.get_pack("pump_water")
        cls.chemical_pack = repo.get_pack("pump_chemical")

    def test_decimal50_context_is_local_and_formula_constants_are_decimal_text(self):
        ambient = getcontext().prec
        self.assertEqual(PUMP_NUMERIC_PRECISION, 50)
        self.assertEqual(Decimal("3.65"), Decimal("3.65"))
        ns, derived = _specific_speed({
            "QBEP": "7200", "HBEP": "32", "speed": "10",
            "product_type": "多级清水离心泵", "suction": "双吸", "stages": "2",
        })
        self.assertEqual(ns, Decimal("4.5625"))
        self.assertEqual(derived["suction_factor"], Decimal("2"))
        self.assertEqual(derived["stage_count"], 2)
        self.assertEqual(derived["q_for_ns_m3s"], Decimal("1"))
        self.assertEqual(derived["h_for_ns_m"], Decimal("16"))
        self.assertEqual(getcontext().prec, ambient)

    def test_decimal_ln_sqrt_and_three_quarter_power_are_stable_at_precision50(self):
        with localcontext(PUMP_DECIMAL_CONTEXT):
            self.assertEqual(Decimal("1").ln(), Decimal("0"))
            self.assertEqual(Decimal("16").sqrt(), Decimal("4"))
            self.assertEqual(PUMP_DECIMAL_CONTEXT.power(Decimal("16"), Decimal("0.75")), Decimal("8"))
            irrational = Decimal("2").ln()
            self.assertEqual(len(irrational.as_tuple().digits), 50)

    def test_efficiency_comparison_uses_same_decimal_threshold_without_epsilon(self):
        delta = Decimal("0.000000000000000000000000000000000000000000000001")
        thresholds = [Decimal("90.12345678901234567890123456789012345678901234567"),
                      Decimal("80.12345678901234567890123456789012345678901234567"),
                      Decimal("70.12345678901234567890123456789012345678901234567")]
        expected = [
            (0, Conclusion.LEVEL_2, Conclusion.LEVEL_1, Conclusion.LEVEL_1),
            (1, Conclusion.LEVEL_3, Conclusion.LEVEL_2, Conclusion.LEVEL_2),
            (2, Conclusion.NOT_COMPLIANT, Conclusion.LEVEL_3, Conclusion.LEVEL_3),
        ]
        for index, below, equal, above in expected:
            with self.subTest(level=index + 1):
                threshold = thresholds[index]
                with localcontext(PUMP_DECIMAL_CONTEXT):
                    self.assertEqual(grade_three(threshold - delta, thresholds, ComparisonDirection.GREATER_OR_EQUAL)[0], below)
                    self.assertEqual(grade_three(threshold, thresholds, ComparisonDirection.GREATER_OR_EQUAL)[0], equal)
                    self.assertEqual(grade_three(threshold + delta, thresholds, ComparisonDirection.GREATER_OR_EQUAL)[0], above)

    def test_raw_binary_float_is_rejected_before_any_pump_formula(self):
        values = {
            "category": "单级单吸", "suction": "单吸", "stages": "1",
            "flow_m3h": 100.1, "head_m": "50", "rated_speed_rpm": "2900", "pump_efficiency": "80",
        }
        result = WaterPumpEvaluator().evaluate(values, self.water_pack)
        self.assertEqual(result.evaluation_status, "INVALID_INPUT")
        self.assertIn("binary float", result.explanation)
        self.assertIsNone(result.grade)
        self.assertFalse(result.calculated_metrics)

    def test_chemical_eta_b_and_delta_eta_use_decimal50_formula_inputs(self):
        values = {
            "product_type": "单级石油化工离心泵", "suction": "单吸", "stages": "1",
            "QBEP": "100", "HBEP": "50", "speed": "2900", "efficiency": "80",
        }
        ns = Decimal("90")
        derived = {
            "suction_factor": Decimal("1"), "stage_count": 1,
            "q_for_ns_m3s": Decimal("0.027777777777777777777777777777777777777777777777778"),
            "h_for_ns_m": Decimal("50"), "ns_raw": ns, "比转速": ns,
        }
        with localcontext(PUMP_DECIMAL_CONTEXT):
            ln_q = Decimal("100").ln()
            eta_b_coefficients = self.chemical_pack["chemical"]["eta_b"]["单级"]
            expected_eta_b = sum(
                coefficient * ln_q ** (6 - index)
                for index, coefficient in enumerate(eta_b_coefficients)
            )
            delta_coefficients = self.chemical_pack["chemical"]["delta_eta"]["ns_20_120"]
            expected_delta = sum(
                coefficient * ns ** (6 - index)
                for index, coefficient in enumerate(delta_coefficients)
            )
            expected_eta0 = expected_eta_b - expected_delta
            with patch(
                "equipeffi.domain.evaluation.device_evaluators._specific_speed",
                return_value=(ns, derived),
            ):
                result = ChemicalPumpEvaluator().evaluate(values, self.chemical_pack)
        self.assertEqual(result.calculated_metrics["基准效率_%"], expected_eta_b)
        self.assertEqual(result.calculated_metrics["效率修正值_%"], expected_delta)
        self.assertEqual(result.calculated_metrics["规定点效率_%"], expected_eta0)

    def test_missing_suction_or_stages_never_receives_implicit_default(self):
        base = {
            "category": "多级", "flow_m3h": "100", "head_m": "120",
            "rated_speed_rpm": "2900", "stages": "3", "suction": "单吸", "pump_efficiency": "80",
        }
        for field, issue in (("suction", "SUCTION_MISSING"), ("stages", "STAGES_MISSING")):
            values = dict(base)
            values.pop(field)
            result = WaterPumpEvaluator().evaluate(values, self.water_pack)
            with self.subTest(field=field):
                self.assertEqual(result.evaluation_status, "INSUFFICIENT_DATA")
                self.assertIn(issue, result.issue_codes)
                self.assertIsNone(result.grade)
                self.assertNotIn("ns_raw", result.calculated_metrics)

    def test_present_invalid_values_are_invalid_not_missing(self):
        base = {
            "category": "单级单吸", "suction": "单吸", "stages": "1",
            "flow_m3h": "100", "head_m": "50", "rated_speed_rpm": "2900", "pump_efficiency": "80",
        }
        invalid_cases = (
            ("suction", "bogus", "SUCTION_INVALID"),
            ("stages", "0", "STAGES_INVALID"),
            ("stages", "1.5", "STAGES_INVALID"),
            ("flow_m3h", "-1", "FLOW_INVALID"),
            ("head_m", "-1", "HEAD_INVALID"),
            ("pump_efficiency", "101", "EFFICIENCY_INVALID"),
        )
        for field, value, issue_code in invalid_cases:
            values = dict(base)
            values[field] = value
            with self.subTest(field=field, value=value):
                result = WaterPumpEvaluator().evaluate(values, self.water_pack)
                self.assertEqual(result.evaluation_status, "INVALID_INPUT")
                self.assertEqual(result.issue_codes, [issue_code])
                self.assertFalse(result.missing_fields)
                self.assertIsNone(result.grade)
                self.assertNotIn("ns_raw", result.calculated_metrics)

    def test_suction_or_stage_conflict_stops_before_ns_formula(self):
        water = WaterPumpEvaluator().evaluate({
            "category": "单级单吸", "suction": "双吸", "stages": "1",
            "flow_m3h": "100", "head_m": "50", "rated_speed_rpm": "2900", "pump_efficiency": "80",
        }, self.water_pack)
        chemical = ChemicalPumpEvaluator().evaluate({
            "category": "单级石油化工离心泵", "suction": "单吸", "stages": "2",
            "flow_m3h": "100", "head_m": "50", "rated_speed_rpm": "2900", "pump_efficiency": "80",
        }, self.chemical_pack)
        self.assertEqual(water.evaluation_status, "INVALID_INPUT")
        self.assertIn("SUCTION_CATEGORY_CONFLICT", water.issue_codes)
        self.assertNotIn("ns_raw", water.calculated_metrics)
        self.assertEqual(chemical.evaluation_status, "INVALID_INPUT")
        self.assertIn("STAGE_CATEGORY_CONFLICT", chemical.issue_codes)
        self.assertNotIn("ns_raw", chemical.calculated_metrics)

    def test_unknown_and_other_categories_are_distinct_and_never_calculate(self):
        unknown = WaterPumpEvaluator().evaluate({
            "category": "未知泵型", "suction": "单吸", "stages": "1",
            "flow_m3h": "100", "head_m": "50", "rated_speed_rpm": "2900", "pump_efficiency": "80",
        }, self.water_pack)
        other = WaterPumpEvaluator().evaluate({"category": "其他类别"}, self.water_pack)
        self.assertEqual(unknown.category_status, "UNRESOLVED")
        self.assertEqual(unknown.evaluation_status, "INVALID_INPUT")
        self.assertIn("CATEGORY_UNRESOLVED", unknown.issue_codes)
        self.assertEqual(other.category_status, "NOT_APPLICABLE")
        self.assertEqual(other.evaluation_status, "OUT_OF_STANDARD_SCOPE")
        self.assertEqual(other.conclusion, Conclusion.NOT_APPLICABLE)
        self.assertFalse(unknown.calculated_metrics)
        self.assertFalse(other.calculated_metrics)


if __name__ == "__main__":
    unittest.main()
