from __future__ import annotations

import json
import unittest
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path

from equipeffi.domain.common.enums import ComparisonDirection, Conclusion
from equipeffi.domain.evaluation.decimal_math import rounded
from equipeffi.domain.evaluation.evaluators.pump import (
    PUMP_DECIMAL_CONTEXT,
    PUMP_NUMERIC_PRECISION,
    ChemicalPumpEvaluator,
    WaterPumpEvaluator,
    _strict_pump_decimal,
)
from equipeffi.domain.evaluation.grading import grade_three
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository
from tests.reference.pump_rp_0_1 import (
    RP_ID,
    chemical_ns_bucket,
    chemical_thresholds,
    decimal_input,
    fractional_power_ref,
    grade_gte,
    ln_ref,
    specific_speed,
    sqrt_ref,
    tolerance_seed,
    water_thresholds,
    within_seed,
)


ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = ROOT / "specs/equipment_efficiency/golden/pump_water"
VECTOR_PATH = ROOT / "specs/equipment_efficiency/conformance/qzc_n01_b_pump_vectors_v0_1.json"
PRECISIONS = (28, 34, 40, 50, 60)
PRECISION_STRESS_SPEED = (
    "1854.54399111109819797925934852904259002949226287668605052340414462252949882422036898621942325043170362951874863911956290"
)
ORDER_STRESS_SPEED = (
    "1854.54399111109819797925934852904259002949535378321426608766003684157842993863514863914042912335007065954525766019462533"
)


class QZCN01BTranscendentalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo = JsonStandardRepository(ROOT)
        cls.water_pack = repo.get_pack("pump_water")
        cls.chemical_pack = repo.get_pack("pump_chemical")

    def test_characterize_current_pump_profile(self):
        self.assertEqual(PUMP_NUMERIC_PRECISION, 50)
        self.assertEqual(PUMP_DECIMAL_CONTEXT.prec, 50)
        self.assertEqual(PUMP_DECIMAL_CONTEXT.rounding, ROUND_HALF_EVEN)
        self.assertEqual(_strict_pump_decimal("1.25"), Decimal("1.25"))
        with self.assertRaises(ValueError):
            _strict_pump_decimal(1.25)
        for coefficient in self.water_pack["water"]["formulas"]["单级"].values():
            self.assertIsInstance(coefficient, Decimal)
        self.assertEqual(rounded(Decimal("1.2345675")), Decimal("1.234568"))

    def test_reference_procedure_exact_cases(self):
        self.assertEqual(RP_ID, "PUMP-RP-0.1")
        self.assertEqual(sqrt_ref("16"), Decimal("4"))
        self.assertEqual(ln_ref("1"), Decimal("0"))
        self.assertEqual(fractional_power_ref("16", "0.75"), Decimal("8"))
        exact = specific_speed(
            QBEP="7200", HBEP="32", speed="10", suction="双吸", stages="2"
        )
        self.assertEqual(exact["q_for_ns_m3s"], Decimal("1"))
        self.assertEqual(exact["h_for_ns_m"], Decimal("16"))
        self.assertEqual(exact["head_power_0_75"], Decimal("8"))
        self.assertEqual(exact["ns_raw"], Decimal("4.5625"))

    def test_reference_rejects_binary_float_and_invalid_domains(self):
        with self.assertRaises(ValueError):
            decimal_input(1.1)
        with self.assertRaises(ValueError):
            decimal_input("NaN")
        with self.assertRaises(ValueError):
            sqrt_ref("-1")
        with self.assertRaises(ValueError):
            ln_ref("0")
        with self.assertRaises(ValueError):
            fractional_power_ref("0", "0.75")
        with self.assertRaises(ValueError):
            specific_speed(QBEP="100", HBEP="50", speed="2900", suction="unknown", stages="1")

    def test_full_value_threshold_compare_is_exact_without_epsilon(self):
        threshold = Decimal("79.78616520331852907378831138801700817769648093823")
        delta = Decimal("1E-48")
        thresholds = [threshold, Decimal("77"), Decimal("72")]
        below = grade_three(threshold - delta, thresholds, ComparisonDirection.GREATER_OR_EQUAL)[0]
        equal = grade_three(threshold, thresholds, ComparisonDirection.GREATER_OR_EQUAL)[0]
        above = grade_three(threshold + delta, thresholds, ComparisonDirection.GREATER_OR_EQUAL)[0]
        self.assertEqual(below, Conclusion.LEVEL_2)
        self.assertEqual(equal, Conclusion.LEVEL_1)
        self.assertEqual(above, Conclusion.LEVEL_1)
        self.assertEqual(grade_gte(threshold - delta, thresholds), "2")
        self.assertEqual(grade_gte(threshold, thresholds), "1")

    def test_display_rounding_does_not_flow_back_into_business_grade(self):
        values = {
            "product_type": "单级单吸清水离心泵", "suction": "单吸", "stages": "1",
            "QBEP": "100", "HBEP": "50", "speed": "2900", "efficiency": "79.786165",
        }
        result = WaterPumpEvaluator().evaluate(values, self.water_pack)
        self.assertEqual(result.grade, "2")
        self.assertEqual(result.limits["1级效率_%"], Decimal("79.786165"))
        full_threshold = Decimal(result.calculated_metrics["grade_thresholds_internal"][0])
        self.assertLess(Decimal("79.786165"), full_threshold)

    def test_reference_matches_multiple_approved_water_golden_traces(self):
        names = (
            "GC-PUMP-V4-WATER-SINGLE-SUCTION-L1.json",
            "GC-PUMP-V4-WATER-SINGLE-L2.json",
            "GC-PUMP-V4-WATER-SINGLE-L3.json",
            "GC-PUMP-V4-WATER-LIGHT-VERTICAL-L2.json",
            "GC-PUMP-V4-WATER-PIPELINE-L1.json",
        )
        aliases = {
            "单级单吸清水离心泵": "单级单吸",
            "单级双吸清水离心泵": "单级双吸",
            "管道清水离心泵": "管道",
            "多级清水离心泵": "多级",
            "轻型多级清水离心泵（立式）": "轻型多级立式",
            "轻型多级清水离心泵（卧式）": "轻型多级卧式",
        }
        rows = self.water_pack["water"]["ci"]
        for name in names:
            case = json.loads((GOLDEN_DIR / name).read_text(encoding="utf-8"))
            raw = case["raw_inputs"]
            expected = case["expected_calculation_trace"]
            ss = specific_speed(
                QBEP=raw["QBEP"], HBEP=raw["HBEP"], speed=raw["speed"],
                suction=raw["suction"], stages=raw["stages"],
            )
            short_type = aliases[raw["product_type"]]
            row = next(r for r in rows if r["data_id"] == expected["matched_rule_id"])
            kind = "多级" if "多级" in short_type else "单级"
            formula = water_thresholds(
                ns_raw=ss["ns_raw"], QBEP=raw["QBEP"],
                coefficients=self.water_pack["water"]["formulas"][kind], ci=row["ci"],
            )
            with self.subTest(case=case["case_id"]):
                self.assertEqual(str(ss["ns_raw"]), expected["derived"]["ns_raw"])
                self.assertEqual([str(x) for x in formula["thresholds"]], expected["grade_thresholds_internal"])
                if case["expected_result"]["evaluation_status"] == "SUCCESS":
                    self.assertEqual(grade_gte(raw["efficiency"], formula["thresholds"]), case["expected_result"]["grade"])

    def test_reference_matches_production_chemical_typical_and_high_flow(self):
        cases = (
            {"QBEP": "100", "HBEP": "50", "speed": "2900", "efficiency": "80"},
            {"QBEP": "3500", "HBEP": "400", "speed": "2900", "efficiency": "90"},
        )
        for raw in cases:
            values = {
                "product_type": "单级石油化工离心泵", "suction": "单吸", "stages": "1", **raw,
            }
            production = ChemicalPumpEvaluator().evaluate(values, self.chemical_pack)
            ns = specific_speed(QBEP=raw["QBEP"], HBEP=raw["HBEP"], speed=raw["speed"], suction="单吸", stages="1")["ns_raw"]
            row = next(
                r for r in self.chemical_pack["chemical"]["level_offsets"]
                if r["pump"] == "单级"
                and (Decimal(str(r["q_min"])) < Decimal(raw["QBEP"]) if r["q_min"] == 300 else Decimal(str(r["q_min"])) < Decimal(raw["QBEP"]) <= Decimal(str(r["q_max"])))
                and Decimal(str(r["ns_min"])) <= ns
                and (r["ns_max"] is None or ns <= Decimal(str(r["ns_max"])))
            )
            delta_key = "ns_20_120" if ns < Decimal("120") else "ns_210_300"
            ref = chemical_thresholds(
                ns_raw=ns,
                QBEP=raw["QBEP"],
                eta_coefficients=self.chemical_pack["chemical"]["eta_b"]["单级"],
                delta_coefficients=(self.chemical_pack["chemical"]["delta_eta"][delta_key] if row["eta0_uses_delta"] else None),
                offsets=row["offsets"],
            )
            with self.subTest(Q=raw["QBEP"]):
                self.assertEqual(production.calculated_metrics["ns_raw"], ns)
                self.assertEqual(production.calculated_metrics["基准效率_%"], ref["eta_b"])
                self.assertEqual(production.calculated_metrics["效率修正值_%"], ref["delta_eta"])
                self.assertEqual(production.calculated_metrics["规定点效率_%"], ref["eta_0"])
                self.assertEqual(production.calculated_metrics["grade_thresholds_internal"], [str(x) for x in ref["thresholds"]])

    def test_precision_sensitivity_natural_cases_keep_business_output(self):
        coefficients = self.water_pack["water"]["formulas"]["单级"]
        ci = self.water_pack["water"]["ci"][0]["ci"]
        grades = []
        values = []
        for precision in PRECISIONS:
            ss = specific_speed(QBEP="100", HBEP="50", speed="2900", suction="单吸", stages="1", precision=precision)
            formula = water_thresholds(ns_raw=ss["ns_raw"], QBEP="100", coefficients=coefficients, ci=ci, precision=precision)
            grades.append(grade_gte("78", formula["thresholds"]))
            values.append((ss["ns_raw"], formula["thresholds"][0]))
        self.assertEqual(grades, ["2"] * len(PRECISIONS))
        self.assertTrue(all(values[i] != values[i + 1] for i in range(len(values) - 1)))

    def test_precision_sensitivity_stress_can_change_ns_bucket(self):
        buckets = {}
        for precision in PRECISIONS:
            ns = specific_speed(
                QBEP="100", HBEP="50", speed=PRECISION_STRESS_SPEED,
                suction="单吸", stages="1", precision=precision,
            )["ns_raw"]
            buckets[precision] = chemical_ns_bucket(ns)
        self.assertEqual(buckets[28], "60<=ns<120")
        self.assertEqual(buckets[34], "60<=ns<120")
        self.assertEqual(buckets[40], "60<=ns<120")
        self.assertEqual(buckets[50], "20<=ns<60")
        self.assertEqual(buckets[60], "20<=ns<60")

    def test_operation_order_natural_difference_is_last_digit_only(self):
        current = specific_speed(QBEP="100", HBEP="50", speed="2900", suction="单吸", stages="1", variant="current")
        equivalent = specific_speed(QBEP="100", HBEP="50", speed="2900", suction="单吸", stages="1", variant="equivalent")
        difference = abs(current["ns_raw"] - equivalent["ns_raw"])
        self.assertGreater(difference, Decimal("0"))
        self.assertLess(difference, Decimal("1E-40"))
        self.assertEqual(chemical_ns_bucket(current["ns_raw"]), chemical_ns_bucket(equivalent["ns_raw"]))
        self.assertTrue(within_seed(equivalent["ns_raw"], current["ns_raw"], "T-NL-COMPOSITE"))

    def test_operation_order_stress_can_change_ns_bucket_at_precision50(self):
        current = specific_speed(
            QBEP="100", HBEP="50", speed=ORDER_STRESS_SPEED,
            suction="单吸", stages="1", precision=50, variant="current",
        )["ns_raw"]
        equivalent = specific_speed(
            QBEP="100", HBEP="50", speed=ORDER_STRESS_SPEED,
            suction="单吸", stages="1", precision=50, variant="equivalent",
        )["ns_raw"]
        self.assertEqual(chemical_ns_bucket(current), "20<=ns<60")
        self.assertEqual(chemical_ns_bucket(equivalent), "60<=ns<120")
        self.assertTrue(within_seed(equivalent, current, "T-NL-COMPOSITE"))
        self.assertNotEqual(chemical_ns_bucket(current), chemical_ns_bucket(equivalent))

    def test_eta_and_threshold_operation_order_sensitivity_is_small_for_realistic_cases(self):
        ns = specific_speed(QBEP="100", HBEP="50", speed="2900", suction="单吸", stages="1")["ns_raw"]
        chemical = self.chemical_pack["chemical"]
        row = next(r for r in chemical["level_offsets"] if r["data_id"] == "GB19762-R000012")
        current = chemical_thresholds(
            ns_raw=ns, QBEP="100", eta_coefficients=chemical["eta_b"]["单级"],
            delta_coefficients=chemical["delta_eta"]["ns_20_120"], offsets=row["offsets"], variant="current",
        )
        equivalent = chemical_thresholds(
            ns_raw=ns, QBEP="100", eta_coefficients=chemical["eta_b"]["单级"],
            delta_coefficients=chemical["delta_eta"]["ns_20_120"], offsets=row["offsets"], variant="equivalent",
        )
        for key in ("eta_b", "delta_eta", "eta_0"):
            self.assertLessEqual(abs(current[key] - equivalent[key]), Decimal("1E-44"), key)
        for a, b in zip(current["thresholds"], equivalent["thresholds"]):
            self.assertLessEqual(abs(a - b), Decimal("1E-44"))
            self.assertTrue(within_seed(b, a, "T-NL-COMPOSITE"))

    def test_tolerance_seeds_are_conformance_only_and_wider_than_python_observed_delta(self):
        atom_reference = ln_ref("100")
        self.assertGreater(tolerance_seed(atom_reference, "T-NL-ATOM"), Decimal("1E-13"))
        current = specific_speed(QBEP="100", HBEP="50", speed="2900", suction="单吸", stages="1", variant="current")["ns_raw"]
        alternative = specific_speed(QBEP="100", HBEP="50", speed="2900", suction="单吸", stages="1", variant="equivalent")["ns_raw"]
        observed = abs(current - alternative)
        self.assertGreater(tolerance_seed(current, "T-NL-COMPOSITE"), observed * Decimal("1E20"))
        # A numerical tolerance pass cannot override a business mismatch.
        stress_current = specific_speed(QBEP="100", HBEP="50", speed=ORDER_STRESS_SPEED, suction="单吸", stages="1", variant="current")["ns_raw"]
        stress_alt = specific_speed(QBEP="100", HBEP="50", speed=ORDER_STRESS_SPEED, suction="单吸", stages="1", variant="equivalent")["ns_raw"]
        self.assertTrue(within_seed(stress_alt, stress_current, "T-NL-COMPOSITE"))
        self.assertNotEqual(chemical_ns_bucket(stress_current), chemical_ns_bucket(stress_alt))

    def test_vector_file_has_required_categories_and_fields(self):
        payload = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
        self.assertEqual(payload["reference_procedure_id"], "PUMP-RP-0.1")
        required_categories = {
            "Exact", "Nonlinear atomic", "Composite", "Business boundary",
            "Precision sensitivity", "Operation-order sensitivity",
            "Invalid input/domain", "Real Pump E2E",
        }
        categories = {vector["category"] for vector in payload["vectors"]}
        self.assertTrue(required_categories.issubset(categories))
        required = {"id", "category", "profile", "operation", "inputs", "reference", "acceptance_mode", "tolerance_purpose", "business_output"}
        for vector in payload["vectors"]:
            with self.subTest(vector=vector["id"]):
                self.assertTrue(required.issubset(vector))


if __name__ == "__main__":
    unittest.main()
