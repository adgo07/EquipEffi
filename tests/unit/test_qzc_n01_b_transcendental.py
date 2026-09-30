from __future__ import annotations

import json
import unittest
from decimal import Decimal, localcontext
from pathlib import Path

from equipeffi.domain.common.enums import ComparisonDirection
from equipeffi.domain.evaluation.evaluators.pump import (
    PUMP_DECIMAL_CONTEXT,
    PUMP_NUMERIC_PRECISION,
    WaterPumpEvaluator,
    _specific_speed,
)
from equipeffi.domain.evaluation.grading import grade_three
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository
from tools.qzc_n01_b_reference import (
    PROFILE_ID,
    clean_thresholds,
    clean_thresholds_alt,
    exact_decimal,
    make_context,
    polynomial_current,
    polynomial_horner,
    specific_speed,
    specific_speed_alt,
    tolerance_limit,
)

ROOT = Path(__file__).resolve().parents[2]
PRECISIONS = (28, 34, 40, 50, 60)


class QZCN01BTranscendentalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo = JsonStandardRepository(ROOT)
        cls.water = repo.get_pack("pump_water")
        cls.chemical = repo.get_pack("pump_chemical")

    def test_profile_characterization(self):
        self.assertEqual(PROFILE_ID, "PUMP-RP-0.1")
        self.assertEqual(PUMP_NUMERIC_PRECISION, 50)
        self.assertEqual(PUMP_DECIMAL_CONTEXT.prec, 50)
        self.assertEqual(PUMP_DECIMAL_CONTEXT.rounding, "ROUND_HALF_EVEN")
        with self.assertRaises(ValueError):
            exact_decimal(100.1)
        with self.assertRaises(ValueError):
            exact_decimal("NaN")

    def test_exact_atomic_and_specific_speed_cases(self):
        with localcontext(make_context(50)):
            self.assertEqual(Decimal("16").sqrt(), Decimal("4"))
            self.assertEqual(Decimal("1").ln(), Decimal("0"))
            self.assertEqual(make_context(50).power(Decimal("16"), Decimal("0.75")), Decimal("8"))
        inputs = {"QBEP": "7200", "HBEP": "32", "speed": "10", "suction": "双吸", "stages": "2"}
        for precision in PRECISIONS:
            with self.subTest(precision=precision):
                out = specific_speed(inputs, precision)
                self.assertEqual(out["q_ns_m3s"], Decimal("1"))
                self.assertEqual(out["h_ns"], Decimal("16"))
                self.assertEqual(out["sqrt_q_ns"], Decimal("1"))
                self.assertEqual(out["h_pow_0_75"], Decimal("8"))
                self.assertEqual(out["ns_raw"], Decimal("4.5625"))
        impl, _ = _specific_speed(inputs)
        self.assertEqual(impl, Decimal("4.5625"))

    def test_precision_sensitivity_business_results(self):
        cases = (
            {"category": "单级单吸", "product_type": "单级单吸清水离心泵", "QBEP": "100", "HBEP": "50", "speed": "2900", "suction": "单吸", "stages": "1", "efficiency": "80"},
            {"category": "多级", "product_type": "多级清水离心泵", "QBEP": "100", "HBEP": "150", "speed": "2900", "suction": "双吸", "stages": "3", "efficiency": "80"},
            {"category": "轻型多级卧式", "product_type": "轻型多级清水离心泵（卧式）", "QBEP": "250", "HBEP": "180", "speed": "2900", "suction": "单吸", "stages": "4", "efficiency": "75"},
        )
        rows = self.water["water"]["ci"]
        for case in cases:
            matching = [r for r in rows if r["type"] == case["category"] and Decimal(str(r["q_min"])) <= Decimal(case["QBEP"]) <= Decimal(str(r["q_max"]))]
            self.assertTrue(matching)
            row = matching[0]
            kind = "多级" if "多级" in case["category"] else "单级"
            coeff = self.water["water"]["formulas"][kind]
            outputs = []
            for precision in PRECISIONS:
                ns = specific_speed(case, precision)["ns_raw"]
                thresholds = clean_thresholds(ns, case["QBEP"], coeff, row["ci"], precision)
                with localcontext(make_context(precision)):
                    grade, _ = grade_three(Decimal(case["efficiency"]), thresholds, ComparisonDirection.GREATER_OR_EQUAL)
                outputs.append((precision, ns, thresholds, grade.value))
            self.assertEqual(len({item[3] for item in outputs}), 1, outputs)
            ns50 = next(item[1] for item in outputs if item[0] == 50)
            ns60 = next(item[1] for item in outputs if item[0] == 60)
            self.assertLessEqual(abs(ns50 - ns60), tolerance_limit(ns60, "T-NL-COMPOSITE"))

    def test_operation_order_sensitivity_is_measured_not_hidden(self):
        case = {"QBEP": "100", "HBEP": "50", "speed": "2900", "suction": "单吸", "stages": "1"}
        row = next(r for r in self.water["water"]["ci"] if r["type"] == "单级单吸" and Decimal(str(r["q_min"])) <= Decimal("100") <= Decimal(str(r["q_max"])))
        coeff = self.water["water"]["formulas"]["单级"]
        saw_numeric_difference = False
        for precision in PRECISIONS:
            current = specific_speed(case, precision)
            alternate = specific_speed_alt(case, precision)
            if current["ns_raw"] != alternate["ns_raw"] or current["h_pow_0_75"] != alternate["h_pow_0_75"]:
                saw_numeric_difference = True
            t_current = clean_thresholds(current["ns_raw"], case["QBEP"], coeff, row["ci"], precision)
            t_alt = clean_thresholds_alt(alternate["ns_raw"], case["QBEP"], coeff, row["ci"], precision)
            if t_current != t_alt:
                saw_numeric_difference = True
            if precision == 50:
                for left, right in zip(t_current, t_alt):
                    self.assertLessEqual(abs(left - right), tolerance_limit(left, "T-NL-COMPOSITE"))
        self.assertTrue(saw_numeric_difference, "sensitivity experiment must expose finite-precision operation-order difference")

    def test_chemical_polynomial_order_sensitivity(self):
        q = Decimal("100")
        with localcontext(make_context(50)):
            ln_q = q.ln()
        coeff = self.chemical["chemical"]["eta_b"]["单级"]
        current50 = polynomial_current(ln_q, coeff, 50)
        horner50 = polynomial_horner(ln_q, coeff, 50)
        self.assertLessEqual(abs(current50 - horner50), tolerance_limit(current50, "T-NL-COMPOSITE"))
        differences = []
        for precision in PRECISIONS:
            with localcontext(make_context(precision)):
                x = q.ln()
            differences.append(abs(polynomial_current(x, coeff, precision) - polynomial_horner(x, coeff, precision)))
        self.assertTrue(any(d != 0 for d in differences))

    def test_full_value_threshold_comparison_t_minus_equal_plus(self):
        threshold = Decimal("80.12345678901234567890123456789012345678901234567")
        delta = Decimal("1E-48")
        thresholds = [threshold, Decimal("70"), Decimal("60")]
        below = grade_three(threshold - delta, thresholds, ComparisonDirection.GREATER_OR_EQUAL)[0].value
        equal = grade_three(threshold, thresholds, ComparisonDirection.GREATER_OR_EQUAL)[0].value
        above = grade_three(threshold + delta, thresholds, ComparisonDirection.GREATER_OR_EQUAL)[0].value
        self.assertNotEqual(below, equal)
        self.assertEqual(equal, above)

    def test_reference_matches_current_water_evaluator_for_representative_case(self):
        values = {"product_type": "单级单吸清水离心泵", "suction": "单吸", "stages": "1", "QBEP": "100", "HBEP": "50", "speed": "2900", "efficiency": "90"}
        result = WaterPumpEvaluator().evaluate(values, self.water)
        ref = specific_speed(values, 50)
        self.assertEqual(result.calculated_metrics["ns_raw"], ref["ns_raw"])
        self.assertEqual(result.evaluation_status, "SUCCESS")
        self.assertEqual(result.grade, "1")

    def test_multiple_approved_golden_water_cases_replay(self):
        golden_dir = ROOT / "specs/equipment_efficiency/golden/pump_water"
        files = sorted(golden_dir.glob("*.json"))
        self.assertGreaterEqual(len(files), 3)
        checked = 0
        for path in files[:6]:
            payload = json.loads(path.read_text(encoding="utf-8"))
            raw = payload.get("raw_inputs", {})
            expected = payload.get("expected_result", {})
            if expected.get("evaluation_status") != "SUCCESS":
                continue
            result = WaterPumpEvaluator().evaluate(raw, self.water)
            with self.subTest(case_id=payload.get("case_id")):
                self.assertEqual(result.evaluation_status, expected["evaluation_status"])
                self.assertEqual(result.grade, expected["grade"])
                trace = payload.get("expected_calculation_trace", {}).get("derived", {})
                if trace.get("ns_raw"):
                    self.assertEqual(result.calculated_metrics["ns_raw"], Decimal(trace["ns_raw"]))
            checked += 1
        self.assertGreaterEqual(checked, 3)


if __name__ == "__main__":
    unittest.main()
