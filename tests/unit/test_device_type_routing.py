from __future__ import annotations

import unittest
from pathlib import Path

from equipeffi.domain.common.enums import Conclusion
from equipeffi.domain.evaluation.device_types import (
    PUBLIC_DEVICE_NAMES, PUBLIC_DEVICE_TYPES, profiles_for_public_type, resolve_device_type,
)
from equipeffi.domain.evaluation.evaluator_registry import EVALUATOR_FACTORIES
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository

ROOT = Path(__file__).resolve().parents[2]


class DeviceTypeRoutingTests(unittest.TestCase):
    def test_registry_contains_fifteen_public_device_types(self):
        self.assertEqual(len(PUBLIC_DEVICE_TYPES), 15)
        self.assertEqual(PUBLIC_DEVICE_NAMES["motor"], "电动机")
        self.assertEqual(PUBLIC_DEVICE_NAMES["centrifugal_pump"], "离心泵")
        self.assertEqual(PUBLIC_DEVICE_NAMES["centrifugal_fan"], "离心通风机")
        self.assertEqual(PUBLIC_DEVICE_NAMES["axial_fan"], "轴流通风机")

    def test_motor_routes_to_internal_profiles(self):
        self.assertEqual(resolve_device_type("motor", {
            "category": "三相异步电动机（一般用途）", "rated_voltage": "0.4"}).internal_device_type,
            "motor_lv")
        self.assertEqual(resolve_device_type("motor", {
            "category": "变频调速永磁同步电动机", "rated_voltage": "0.38"}).internal_device_type,
            "motor_pmsm")
        self.assertEqual(resolve_device_type("motor", {
            "category": "高压三相异步电动机", "rated_voltage": "6"}).internal_device_type,
            "motor_hv")
        self.assertEqual(profiles_for_public_type("motor"), ("motor_lv", "motor_hv", "motor_pmsm"))

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

    def test_motor_candidate_calculator_preserves_lookup_result(self):
        repository = JsonStandardRepository(ROOT)
        result = EVALUATOR_FACTORIES["motor_lv"]().evaluate({
            "record_id": "MOTOR-CANDIDATE", "category": "三相异步电动机（一般用途）",
            "rated_voltage_v": 400, "rated_power_kw": 7.5, "poles": 4,
            "rated_speed_rpm": 1480, "rated_efficiency": 98,
        }, repository.get_pack("motor_lv"))
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.actual_metrics["额定效率_%"], 98)
        self.assertTrue(result.lookups)


if __name__ == "__main__":
    unittest.main()
