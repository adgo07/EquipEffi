"""批准映射候选案例与全六表机械回归；不冒称Approved Golden。"""
import copy
from decimal import Decimal, localcontext, ROUND_DOWN, ROUND_UP
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import unittest

from equipeffi.domain.devices.motor_hv.calculator import Gb30254MotorCalculator, HvPackError, PROFILE_ID
from tools.build_gb30254_motor_pack import build_pack, OUTPUT, WORKBOOK, WORKBOOK_SHA, MAPPING, MAPPING_SHA

ROOT = Path(__file__).resolve().parents[2]
BASE = dict(category_id="gb30254_cage_induction", rated_voltage_v="3000", rated_frequency_hz="50",
            cooling_method="IC01", rated_output_power_kw="200", poles="2", rated_efficiency_pct="94")


class MotorHvCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads((ROOT / OUTPUT).read_text(encoding="utf-8"))
        cls.calculator = Gb30254MotorCalculator()

    def evaluate(self, **changes):
        return self.calculator.evaluate(BASE | changes, self.pack)

    def test_rebuild_and_protected_source_hashes(self):
        self.assertEqual(build_pack(ROOT), self.pack)
        for path, digest in ((WORKBOOK, WORKBOOK_SHA), (MAPPING, MAPPING_SHA)):
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest)
        self.assertEqual(self.pack["counts"], dict(numeric=3093, horizontal_dash=285, rows=204))

    def test_c01_to_c07_and_no_display_rounding_feedback(self):
        for efficiency, grade in (("94", "1"), ("93.999", "2"), ("93.1", "2"), ("92.3", "3"), ("92.299", None)):
            with self.subTest(efficiency=efficiency):
                result = self.evaluate(rated_efficiency_pct=efficiency)
                self.assertEqual((result.evaluation_status, result.grade), ("SUCCESS", grade))
        interpolated = self.evaluate(rated_output_power_kw="210", rated_efficiency_pct="94.05")
        self.assertEqual(interpolated.grade, "1")
        self.assertEqual([x["display"] for x in interpolated.thresholds.values()], ["94.05", "93.20", "92.40"])
        self.assertEqual(interpolated.thresholds["grade_1"]["exact"]["numerator"], "1881")
        self.assertEqual(self.evaluate(rated_output_power_kw="210", rated_efficiency_pct="94.049999999999999999999999999").grade, "2")
        self.assertEqual(self.evaluate(rated_output_power_kw="220", rated_efficiency_pct="94.1").references["method"], "DIRECT")

    def test_all_six_routes_c08_to_c13(self):
        for voltage, cooling, table, thresholds in (
            ("3300", "IC81W", 1, ("94", "93.1", "92.3")),
            ("6000", "IC81W", 1, ("94", "93.1", "92.3")),
            ("10000", "IC01", 2, ("93.7", "92.8", "92")),
            ("6000", "IC611", 3, ("93.4", "92.6", "91.7")),
            ("10000", "IC516", 4, ("93.1", "92.3", "91.5")),
            ("6000", "IC411", 5, ("94.4", "93.5", "92.7")),
            ("10000", "IC411", 6, ("94.1", "93.2", "92.4")),
        ):
            result = self.evaluate(rated_voltage_v=voltage, cooling_method=cooling)
            self.assertEqual(result.references["table_number"], table)
            for i, expected in enumerate(thresholds, 1):
                actual = result.thresholds[f"grade_{i}"]["exact"]
                self.assertEqual(Fraction(int(actual["numerator"]), int(actual["denominator"])), Fraction(expected))

    def test_branch_boundaries_c14_to_c25(self):
        for changes in (
            dict(rated_output_power_kw="11200"), dict(poles="12", rated_output_power_kw="6000"),
            dict(rated_voltage_v="10000", poles="12", rated_output_power_kw="5600"),
            dict(cooling_method="IC611", poles="8", rated_output_power_kw="6500"),
            dict(cooling_method="IC411", poles="10"), dict(cooling_method="IC411", poles="12"),
            dict(rated_output_power_kw="199"), dict(rated_output_power_kw="25001", poles="4"),
            dict(rated_voltage_v="10000", cooling_method="IC411", rated_output_power_kw="2800.1"),
            dict(rated_frequency_hz="60"), dict(rated_frequency_hz="5～120"), dict(rated_voltage_v="3000.1"),
            dict(rated_frequency_hz="变频"), dict(rated_frequency_hz="50/60"), dict(rated_frequency_hz="50 Hz"),
            dict(rated_voltage_v="3"), dict(cooling_method="IC999"),
        ):
            with self.subTest(changes=changes):
                self.assertEqual(self.evaluate(**changes).evaluation_status, "OUT_OF_STANDARD_SCOPE")
        for changes in (dict(poles="4", rated_output_power_kw="25000"),
                        dict(rated_voltage_v="10000", cooling_method="IC516", poles="12", rated_output_power_kw="10000"),
                        dict(rated_voltage_v="10000", cooling_method="IC411", rated_output_power_kw="2800")):
            self.assertEqual(self.evaluate(**changes).evaluation_status, "SUCCESS")
        self.assertIn("B法", self.evaluate(rated_output_power_kw="2000").references["test_method_reference"])
        self.assertIn("H法", self.evaluate(rated_output_power_kw="2000.1").references["test_method_reference"])

    def test_input_missing_invalid_and_explicit_category(self):
        for name in BASE:
            with self.subTest(missing=name):
                result = self.evaluate(**{name: None})
                self.assertEqual(result.evaluation_status, "INSUFFICIENT_DATA")
                self.assertIn(name, result.missing_fields)
        for value in (True, 94.0, "NaN", "Infinity", "1e999", "1,000", "94%", "0.94", "100.1", "-1", 10**200):
            with self.subTest(value=value):
                self.assertEqual(self.evaluate(rated_efficiency_pct=value).evaluation_status, "INVALID_INPUT")
        for value in ("3", "2.1", "0"):
            self.assertEqual(self.evaluate(poles=value).evaluation_status, "INVALID_INPUT")
        for value in ("NaN", "Infinity", "1e+", "=50", "#VALUE!", "1,000", "1e999", True, 50.0):
            self.assertEqual(self.evaluate(rated_frequency_hz=value).evaluation_status, "INVALID_INPUT")
        self.assertEqual(self.evaluate(category_id="three_phase_induction").evaluation_status, "INVALID_INPUT")
        self.assertEqual(self.evaluate(category_id="OTHER_CATEGORY").evaluation_status, "OUT_OF_STANDARD_SCOPE")
        self.assertEqual(self.evaluate(category_id="UNCERTAIN_CATEGORY").evaluation_status, "INSUFFICIENT_DATA")

    def test_profile_ambient_and_corrupt_pack(self):
        expected = self.evaluate(rated_output_power_kw="210", rated_efficiency_pct="94.05")
        for rounding in (ROUND_DOWN, ROUND_UP):
            with localcontext() as context:
                context.prec, context.rounding = 2, rounding
                self.assertEqual(self.evaluate(rated_output_power_kw=Decimal("210"), rated_efficiency_pct=Decimal("94.05")), expected)
        with self.assertRaises(HvPackError):
            self.calculator.evaluate(BASE, self.pack, numeric_profile_id="EQUIPEFFI_MOTOR_EXACT_LINEAR_V1")
        bad = copy.deepcopy(self.pack)
        bad["tables"][0]["rows"][0]["branches"]["2"][0]["value"] = "93"
        with self.assertRaises(HvPackError):
            self.calculator.evaluate(BASE, bad)
        bad["integrity_sha256"] = hashlib.sha256(json.dumps({k: v for k, v in bad.items() if k != "integrity_sha256"}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        with self.assertRaises(HvPackError):
            self.calculator.evaluate(BASE, bad)

    def test_every_source_cell_and_adjacent_midpoint(self):
        routes = (("3000", "IC01"), ("10000", "IC01"), ("3000", "IC611"), ("10000", "IC611"), ("3000", "IC411"), ("10000", "IC411"))
        for table, (voltage, cooling) in zip(self.pack["tables"], routes):
            for pole in table["poles"]:
                for index, row in enumerate(table["rows"]):
                    branch = row["branches"][str(pole)]
                    changes = dict(rated_voltage_v=voltage, cooling_method=cooling, poles=str(pole), rated_output_power_kw=row["power_kw"])
                    result = self.evaluate(**changes)
                    if any(x["value"] is None for x in branch):
                        self.assertEqual(result.evaluation_status, "OUT_OF_STANDARD_SCOPE")
                    else:
                        for grade, cell in enumerate(branch, 1):
                            equality = self.evaluate(**changes, rated_efficiency_pct=cell["value"])
                            self.assertEqual(equality.grade, str(grade))
                    if index == 0:
                        continue
                    previous = table["rows"][index - 1]
                    total = int(previous["power_kw"]) + int(row["power_kw"])
                    midpoint = str(total // 2) + (".5" if total % 2 else "")
                    interpolation = self.evaluate(**(changes | dict(rated_output_power_kw=midpoint)))
                    prior = previous["branches"][str(pole)]
                    if any(x["value"] is None for x in branch + prior):
                        self.assertEqual(interpolation.evaluation_status, "OUT_OF_STANDARD_SCOPE")
                    else:
                        for i in range(3):
                            expected = (Fraction(prior[i]["value"]) + Fraction(branch[i]["value"])) / 2
                            actual = interpolation.thresholds[f"grade_{i + 1}"]["exact"]
                            self.assertEqual(Fraction(int(actual["numerator"]), int(actual["denominator"])), expected)

    def test_source_display_precision(self):
        self.assertEqual(self.evaluate().thresholds["grade_1"]["display"], "94.0")
        result = self.evaluate(poles="6", rated_output_power_kw="5000")
        self.assertEqual(result.thresholds["grade_1"]["display"], "97")

    def test_frozen_common_core_conformance_vectors(self):
        import jsonschema
        schema_path = ROOT / "tests/fixtures/numeric/conformance_vector_v1.schema.json"
        self.assertEqual(hashlib.sha256(schema_path.read_bytes()).hexdigest(), "bf7e5a4c2723376d3b20921c12298dbd42ab7e4ca46326b78df6bdf9697d4629")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        path = ROOT / "specs/equipment_efficiency/numeric/equipeffi_motor_hv_conformance_v1.json"
        vectors = json.loads(path.read_text(encoding="utf-8"))
        for vector in vectors:
            with self.subTest(case_id=vector["case_id"]):
                jsonschema.validate(vector, schema)
                self.assertEqual(vector["numeric_profile_id"], PROFILE_ID)
                self.assertEqual(vector["authority_scope"], "motor_hv")
                if vector["category"] == "profile_mismatch_rejection":
                    with self.assertRaises(HvPackError):
                        self.calculator.evaluate(vector["inputs"], self.pack, numeric_profile_id=vector["requested_profile"])
                    continue
                with localcontext() as context:
                    context.prec, context.rounding = 2, ROUND_UP
                    actual = self.calculator.evaluate(vector["inputs"], self.pack)
                expected = vector["expected_business_result"]
                self.assertEqual(actual.evaluation_status, expected["evaluation_status"])
                self.assertEqual(actual.grade, expected["grade"])
                self.assertEqual(actual.references["numeric_profile_id"], PROFILE_ID)
                if "expected_reference_value" in vector:
                    self.assertEqual(actual.thresholds["grade_1"]["exact"], vector["expected_reference_value"])
                if "display_value" in vector:
                    self.assertEqual(actual.thresholds["grade_1"]["display"], vector["display_value"])


if __name__ == "__main__":
    unittest.main()
