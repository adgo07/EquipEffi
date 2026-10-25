"""Verify the motor profile's common-core numeric conformance vectors."""
from __future__ import annotations

import copy
import json
from decimal import ROUND_CEILING, localcontext
from pathlib import Path
import unittest

from equipeffi.domain.devices.motor.calculator import Gb18613MotorCalculator, MotorPackError


ROOT = Path(__file__).resolve().parents[2]
PACK_FILE = ROOT / "src/equipeffi/resources/standards/gb18613_2020.json"
VECTORS_FILE = ROOT / "specs/equipment_efficiency/numeric/equipeffi_motor_exact_linear_conformance_v1.json"
ALLOWED_CATEGORIES = {
    "exact_comparison",
    "business_boundary",
    "display_separation",
    "unit_conversion",
    "input_rejection",
    "ambient_independence",
    "profile_mismatch_rejection",
}


class MotorNumericConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK_FILE.read_text(encoding="utf-8"))
        cls.conformance = json.loads(VECTORS_FILE.read_text(encoding="utf-8"))
        cls.calculator = Gb18613MotorCalculator()

    def test_common_core_vector_shape_and_unique_case_ids(self):
        vectors = self.conformance["vectors"]
        self.assertTrue(vectors)
        self.assertEqual(len({item["case_id"] for item in vectors}), len(vectors))
        for vector in vectors:
            with self.subTest(case_id=vector.get("case_id")):
                for key in (
                    "case_id",
                    "category",
                    "numeric_contract_version",
                    "numeric_profile_id",
                    "authority_scope",
                    "inputs",
                    "provenance",
                ):
                    self.assertIn(key, vector)
                self.assertIn(vector["category"], ALLOWED_CATEGORIES)
                expected_count = sum(
                    key in vector
                    for key in (
                        "expected_error",
                        "expected_business_result",
                        "expected_reference_value",
                    )
                )
                self.assertEqual(expected_count, 1)

    def test_vectors_match_calculator_outputs(self):
        for vector in self.conformance["vectors"]:
            with self.subTest(case_id=vector["case_id"]):
                category = vector["category"]
                if category == "profile_mismatch_rejection":
                    pack = copy.deepcopy(self.pack)
                    pack["numeric_profile_id"] = "UNEXPECTED_PROFILE"
                    with self.assertRaises(MotorPackError) as caught:
                        self.calculator.evaluate(vector["inputs"], pack)
                    self.assertEqual(
                        type(caught.exception).__name__,
                        vector["expected_error"]["error_type"],
                    )
                    continue

                result = self.calculator.evaluate(vector["inputs"], self.pack)
                if "expected_error" in vector:
                    expected = vector["expected_error"]
                    self.assertEqual(result.evaluation_status, expected["evaluation_status"])
                    self.assertIn(expected["reason_code"], result.reason_codes)
                    self.assertIn(expected["field_id"], result.invalid_fields)
                    continue

                expected = vector["expected_business_result"]
                self.assertEqual(result.evaluation_status, expected["evaluation_status"])
                self.assertEqual(result.grade, expected["grade"])
                trace = result.trace[0]
                for field in (
                    "table_id",
                    "branch_id",
                    "method",
                    "normalized_power_w",
                    "speed_band_label",
                ):
                    if field in expected:
                        self.assertEqual(trace[field], expected[field])
                if "ui_conclusion" in expected:
                    self.assertEqual(result.ui_conclusion, expected["ui_conclusion"])
                for level in (1, 2, 3):
                    exact_key = f"grade_{level}_exact"
                    display_key = f"grade_{level}_display"
                    if exact_key in expected:
                        self.assertEqual(result.thresholds[f"grade_{level}"]["exact"], expected[exact_key])
                    if display_key in expected:
                        self.assertEqual(result.thresholds[f"grade_{level}"]["display_text"], expected[display_key])
                if "comparison_policy" in expected:
                    self.assertEqual(trace["comparison"]["policy"], expected["comparison_policy"])
                if "business_epsilon" in expected:
                    self.assertFalse(expected["business_epsilon"])
                if expected.get("context_invariant"):
                    with localcontext() as context:
                        context.prec = 2
                        context.rounding = ROUND_CEILING
                        altered = self.calculator.evaluate(vector["inputs"], self.pack)
                    self.assertEqual(altered.grade, result.grade)
                    self.assertEqual(altered.thresholds, result.thresholds)
                    self.assertEqual(altered.trace, result.trace)


if __name__ == "__main__":
    unittest.main()
