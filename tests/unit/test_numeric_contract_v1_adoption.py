from __future__ import annotations

import json
import unittest
from decimal import Decimal, ROUND_DOWN, ROUND_UP, localcontext
from pathlib import Path

from equipeffi.domain.common.enums import ComparisonDirection
from equipeffi.domain.evaluation.evaluators.pump import (
    PUMP_DECIMAL_CONTEXT,
    PUMP_NUMERIC_PRECISION,
    WaterPumpEvaluator,
    _strict_pump_decimal,
)
from equipeffi.domain.evaluation.grading import grade_three
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository
from tools.qzc_n01_b_reference import PROFILE_ID

ROOT = Path(__file__).resolve().parents[2]
CENTRAL_SHA = "ee5feb0cc34dbd99790500fadd0c4c932e202a20"
FROZEN_NUMERIC_PATH = "contracts/numeric/NUMERIC_CONTRACT_V1_FROZEN.md"
PROFILE_PATH = ROOT / "specs/equipment_efficiency/numeric/equipeffi_pump_numeric_profile_v1.json"


class NumericContractV1AdoptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads((ROOT / "platform-lock.json").read_text(encoding="utf-8"))
        cls.profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        cls.water = JsonStandardRepository(ROOT).get_pack("pump_water")

    def test_platform_lock_adopts_only_frozen_numeric_v1(self):
        self.assertEqual(self.lock["commit_sha"], CENTRAL_SHA)
        self.assertEqual(
            self.lock["numeric_contract"],
            {"version": "v1", "status": "FROZEN", "path": FROZEN_NUMERIC_PATH},
        )
        self.assertEqual(self.lock["architecture_status"], "FROZEN")
        for key in (
            "unit_contract",
            "module_capability_contract",
            "record_contract",
            "package_contract",
        ):
            with self.subTest(contract=key):
                self.assertEqual(self.lock[key]["version"], "draft-v1")
                self.assertEqual(self.lock[key]["status"], "DRAFT")

    def test_pump_profile_declaration_matches_frozen_mechanism(self):
        profile = self.profile
        self.assertEqual(profile["numeric_profile_id"], "EQUIPEFFI_PUMP_DECIMAL50_V2")
        self.assertEqual(profile["numeric_contract_version"], "v1")
        self.assertEqual(profile["numeric_contract_status"], "FROZEN")
        self.assertEqual(profile["numeric_contract_source"]["commit_sha"], CENTRAL_SHA)
        self.assertEqual(profile["numeric_contract_source"]["path"], FROZEN_NUMERIC_PATH)
        self.assertEqual(profile["authoritative_scopes"], ["pump_water", "pump_chemical"])
        self.assertEqual(profile["representation"], "strict Decimal text / Decimal / exact integer")
        self.assertEqual(profile["working_precision"], 50)
        self.assertEqual(profile["rounding_mode"], "ROUND_HALF_EVEN")
        self.assertIn("full-value exact", profile["comparison_policy"])
        self.assertIn("PUMP-RP-0.1", profile["transcendental_policy"]["reference_procedure"])
        self.assertEqual(profile["transcendental_policy"]["functions"], ["sqrt", "ln", "fractional_pow"])
        self.assertIn("conformance", profile["tolerance_policy"]["numerical_conformance"])
        self.assertEqual(profile["tolerance_policy"]["business_mismatch_within_numerical_tolerance"], "FAIL")
        self.assertFalse(profile["platform_default"])
        self.assertEqual(profile["rule_version"], "GB19762-2025")
        self.assertEqual(profile["trace_reference"]["platform_lock"], "platform-lock.json")

    def test_pump_profile_is_effectively_consumed_and_not_platform_default(self):
        self.assertEqual(PUMP_NUMERIC_PRECISION, self.profile["working_precision"])
        self.assertEqual(PUMP_DECIMAL_CONTEXT.prec, self.profile["working_precision"])
        self.assertEqual(PUMP_DECIMAL_CONTEXT.rounding, self.profile["rounding_mode"])
        self.assertEqual(PROFILE_ID, self.profile["transcendental_policy"]["reference_procedure"])
        notes = "\n".join(self.lock.get("notes", []))
        self.assertIn("Pump-profile-specific", notes)
        self.assertIn("not a platform-wide default", notes)
        self.assertIn("do not inherit Decimal50", self.profile["other_device_policy"])

    def test_authoritative_binary_float_and_nonfinite_are_rejected(self):
        with self.assertRaises(ValueError):
            _strict_pump_decimal(100.1)
        with self.assertRaises(ValueError):
            _strict_pump_decimal("NaN")
        with self.assertRaises(ValueError):
            _strict_pump_decimal("Infinity")
        self.assertEqual(_strict_pump_decimal("100.10"), Decimal("100.10"))

    def test_declared_profile_is_ambient_independent(self):
        values = {
            "product_type": "单级单吸清水离心泵",
            "suction": "单吸",
            "stages": "1",
            "QBEP": "100",
            "HBEP": "50",
            "speed": "2900",
            "efficiency": "90",
        }
        snapshots = []
        for precision, rounding in ((9, ROUND_DOWN), (17, ROUND_UP), (60, ROUND_DOWN)):
            with self.subTest(ambient_precision=precision, ambient_rounding=rounding):
                with localcontext() as ambient:
                    ambient.prec = precision
                    ambient.rounding = rounding
                    result = WaterPumpEvaluator().evaluate(values, self.water)
                snapshots.append(
                    (
                        result.evaluation_status,
                        result.grade,
                        str(result.calculated_metrics["ns_raw"]),
                    )
                )
        self.assertEqual(len(set(snapshots)), 1, snapshots)

    def test_business_boundary_uses_full_value_not_conformance_tolerance(self):
        threshold = Decimal("80.12345678901234567890123456789012345678901234567")
        delta = Decimal("1E-48")
        thresholds = [threshold, Decimal("70"), Decimal("60")]
        with localcontext(PUMP_DECIMAL_CONTEXT):
            below_value = threshold - delta
            above_value = threshold + delta
            below = grade_three(
                below_value,
                thresholds,
                ComparisonDirection.GREATER_OR_EQUAL,
            )[0].value
            equal = grade_three(
                threshold,
                thresholds,
                ComparisonDirection.GREATER_OR_EQUAL,
            )[0].value
            above = grade_three(
                above_value,
                thresholds,
                ComparisonDirection.GREATER_OR_EQUAL,
            )[0].value
        self.assertNotEqual(below_value, threshold)
        self.assertNotEqual(above_value, threshold)
        self.assertNotEqual(below, equal)
        self.assertEqual(equal, above)


if __name__ == "__main__":
    unittest.main()
