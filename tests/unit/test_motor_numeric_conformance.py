"""Verify the motor profile's common-core numeric conformance vectors."""
from __future__ import annotations

import copy
import decimal
import hashlib
import json
from decimal import localcontext
from fractions import Fraction
from pathlib import Path
import unittest

import jsonschema

from equipeffi.domain.devices.motor.calculator import Gb18613MotorCalculator, MotorPackError


ROOT = Path(__file__).resolve().parents[2]
PACK_FILE = ROOT / "src/equipeffi/resources/standards/gb18613_2020.json"
PROFILE_FILE = ROOT / "specs/equipment_efficiency/numeric/equipeffi_motor_numeric_profile_v1.json"
VECTORS_FILE = ROOT / "specs/equipment_efficiency/numeric/equipeffi_motor_exact_linear_conformance_v1.json"
SCHEMA_FILE = ROOT / "tests/fixtures/numeric/conformance_vector_v1.schema.json"
LOCKED_SCHEMA_REPOSITORY = "https://github.com/adgo07/Qingzhou-contracts.git"
LOCKED_SCHEMA_COMMIT = "ee5feb0cc34dbd99790500fadd0c4c932e202a20"
LOCKED_SCHEMA_SOURCE_PATH = "conformance/common/numeric/conformance_vector_v1.schema.json"
LOCKED_SCHEMA_SHA256 = "bf7e5a4c2723376d3b20921c12298dbd42ab7e4ca46326b78df6bdf9697d4629"
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
        cls.profile = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        cls.conformance = json.loads(VECTORS_FILE.read_text(encoding="utf-8"))
        cls.calculator = Gb18613MotorCalculator()

    def test_vectors_validate_against_locked_json_schema(self):
        schema_bytes = SCHEMA_FILE.read_bytes()
        self.assertEqual(
            hashlib.sha256(schema_bytes).hexdigest(),
            LOCKED_SCHEMA_SHA256,
            f"{LOCKED_SCHEMA_REPOSITORY}@{LOCKED_SCHEMA_COMMIT}:{LOCKED_SCHEMA_SOURCE_PATH}",
        )
        schema = json.loads(schema_bytes)
        validator_class = jsonschema.validators.validator_for(schema)
        validator_class.check_schema(schema)
        validator = validator_class(schema)

        for vector in self.conformance["vectors"]:
            with self.subTest(case_id=vector.get("case_id")):
                errors = list(validator.iter_errors(vector))
                self.assertFalse(
                    errors,
                    "; ".join(error.message for error in errors),
                )

    def test_common_core_vector_shape_and_unique_case_ids(self):
        self.assertEqual(
            self.profile["numeric_profile_id"],
            self.conformance["numeric_profile_id"],
        )
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
                    self.assertEqual(
                        vector["requested_profile"],
                        vector["numeric_profile_id"],
                    )
                    self.assertIsNone(vector["effective_profile"])
                    self.assertNotEqual(
                        vector["requested_profile"],
                        vector["conflicting_profile"],
                    )
                    pack = copy.deepcopy(self.pack)
                    pack["numeric_profile_id"] = vector["conflicting_profile"]
                    with self.assertRaises(MotorPackError) as caught:
                        self.calculator.evaluate(vector["inputs"], pack)
                    self.assertEqual(
                        type(caught.exception).__name__,
                        vector["expected_error"]["error_type"],
                    )
                    continue

                if vector.get("effective_profile") is not None:
                    self.assertEqual(
                        vector["requested_profile"],
                        vector["effective_profile"],
                    )
                    self.assertEqual(
                        vector["effective_profile"],
                        self.pack["numeric_profile_id"],
                    )

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

                if "calculation_value" in vector:
                    self.assertEqual(
                        result.thresholds["grade_3"]["exact"],
                        vector["calculation_value"],
                    )
                if "comparison_value" in vector:
                    self.assertEqual(
                        vector["comparison_value"],
                        vector["inputs"]["measured_efficiency_pct"],
                    )
                if "threshold" in vector:
                    self.assertEqual(
                        result.thresholds["grade_3"]["exact"],
                        vector["threshold"],
                    )
                if {"operator", "comparison_value", "threshold"}.issubset(vector):
                    comparison_value = Fraction(vector["comparison_value"])
                    threshold_value = Fraction(
                        int(vector["threshold"]["numerator"]),
                        int(vector["threshold"]["denominator"]),
                    )
                    comparisons = {
                        "lt": comparison_value < threshold_value,
                        "lte": comparison_value <= threshold_value,
                        "eq": comparison_value == threshold_value,
                        "gte": comparison_value >= threshold_value,
                        "gt": comparison_value > threshold_value,
                    }
                    self.assertTrue(comparisons[vector["operator"]])
                if "display_value" in vector:
                    self.assertEqual(
                        result.thresholds["grade_3"]["display_text"],
                        vector["display_value"],
                    )
                    self.assertEqual(
                        expected["grade_3_display"],
                        vector["display_value"],
                    )
                if "rounding" in vector:
                    rounding = vector["rounding"]
                    display_policy = self.profile["display_policy"]
                    self.assertEqual(rounding["stage"], "display")
                    self.assertEqual(rounding["purpose"], "display")
                    self.assertEqual(
                        rounding["mode"],
                        display_policy["rounding_mode"],
                    )
                    self.assertEqual(
                        rounding["places"],
                        display_policy["interpolated_places"],
                    )
                if "comparison_policy" in expected:
                    self.assertEqual(trace["comparison"]["policy"], expected["comparison_policy"])
                if "business_epsilon" in expected:
                    self.assertFalse(expected["business_epsilon"])
                if expected.get("context_invariant"):
                    ambient = vector["ambient_profile"]
                    with localcontext() as context:
                        context.prec = ambient["precision"]
                        context.rounding = getattr(decimal, ambient["rounding_mode"])
                        altered = self.calculator.evaluate(vector["inputs"], self.pack)
                    self.assertEqual(altered.grade, result.grade)
                    self.assertEqual(altered.thresholds, result.thresholds)
                    self.assertEqual(altered.trace, result.trace)


if __name__ == "__main__":
    unittest.main()
