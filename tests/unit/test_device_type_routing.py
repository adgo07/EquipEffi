from __future__ import annotations

import unittest
from pathlib import Path

from equipeffi.domain.common.enums import Conclusion
from equipeffi.domain.evaluation.device_types import (
    PUBLIC_DEVICE_NAMES, PUBLIC_DEVICE_TYPES, profiles_for_public_type, resolve_device_type,
)
from equipeffi.domain.evaluation.evaluator_registry import EVALUATOR_FACTORIES
from equipeffi.domain.evaluation.evaluators.motor import MotorEvaluator
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository

ROOT = Path(__file__).resolve().parents[2]


class DeviceTypeRoutingTests(unittest.TestCase):
    def test_registry_contains_fifteen_public_device_types(self):
        self.assertEqual(len(PUBLIC_DEVICE_TYPES), 15)
        self.assertEqual(PUBLIC_DEVICE_NAMES["motor"], "电动机")
        self.assertEqual(PUBLIC_DEVICE_NAMES["centrifugal_pump"], "离心泵")
        self.assertEqual(PUBLIC_DEVICE_NAMES["centrifugal_fan"], "离心通风机")
        self.assertEqual(PUBLIC_DEVICE_NAMES["axial_fan"], "轴流通风机")

    def test_gb18613_requires_explicit_standard_and_category(self):
        with self.assertRaisesRegex(ValueError, "明确选择"):
            resolve_device_type("motor", {
                "category": "三相异步电动机（一般用途）", "rated_voltage": "0.4"})
        routed = resolve_device_type("motor", {
            "standard_code": "GB 18613-2020", "category_id": "three_phase_induction"})
        self.assertEqual(routed.internal_device_type, "motor_lv")
        with self.assertRaisesRegex(ValueError, "明确选择标准"):
            resolve_device_type("motor", {"category_id": "three_phase_induction"})
        self.assertEqual(profiles_for_public_type("motor"), ("motor_lv", "motor_hv", "motor_pmsm"))

    def test_existing_high_voltage_and_pmsm_routes_remain_intact(self):
        self.assertEqual(resolve_device_type("motor", {
            "category": "变频调速永磁同步电动机", "rated_voltage": "0.38"}).internal_device_type,
            "motor_pmsm")
        self.assertEqual(resolve_device_type("motor", {
            "category": "高压三相异步电动机", "rated_voltage": "6"}).internal_device_type,
            "motor_hv")

    def test_pump_and_fan_profiles_route_without_ambiguity(self):
        self.assertEqual(resolve_device_type("centrifugal_pump", {
            "category": "单级单吸清水离心泵"}).internal_device_type, "pump_water")
        self.assertEqual(resolve_device_type("centrifugal_pump", {
            "category": "单级石油化工离心泵"}).internal_device_type, "pump_chemical")
        self.assertEqual(resolve_device_type("centrifugal_fan", {}).internal_device_type, "fan")
        self.assertEqual(resolve_device_type("axial_fan", {}).internal_device_type, "fan")

    def test_fan_type_rejects_conflicting_category(self):
        with self.assertRaises(ValueError):
            resolve_device_type("centrifugal_fan", {"category": "轴流通风机"})
        with self.assertRaises(ValueError):
            resolve_device_type("axial_fan", {"category": "离心通风机"})

    def test_motor_registry_adapter_uses_new_calculator_and_pack(self):
        repository = JsonStandardRepository(ROOT)
        pack = repository.get_pack("motor_lv")
        result = EVALUATOR_FACTORIES["motor_lv"]().evaluate({
            "record_id": "MOTOR-CANDIDATE", "category_id": "three_phase_induction",
            "rated_voltage_kv": "0.38", "rated_frequency_hz": "50",
            "rated_output_power_kw": "0.14", "poles": "4",
            "measured_efficiency_pct": "71.43",
        }, pack)
        self.assertEqual(result.conclusion, Conclusion.LEVEL_3)
        self.assertEqual(result.grade, "3")
        self.assertEqual(result.standard_reference["pack_id"], "gb18613_2020_v2")
        self.assertTrue(result.lookups)
        self.assertEqual(result.lookups[0]["table_id"], "GB18613-T01")

    def test_retired_legacy_motor_evaluator_rejects_gb18613(self):
        repository = JsonStandardRepository(ROOT)
        with self.assertRaisesRegex(RuntimeError, "Gb18613MotorCalculator"):
            MotorEvaluator("motor_lv").evaluate({"category": "三相异步电动机"},
                                                  repository.get_pack("motor_lv"))


if __name__ == "__main__":
    unittest.main()