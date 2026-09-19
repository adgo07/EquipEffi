from __future__ import annotations

import unittest
from pathlib import Path

from equipeffi.application.services.evaluation_service import EvaluationService
from equipeffi.application.services.v4_input_adapter import V4InputAdapter
from equipeffi.domain.common.enums import Conclusion
from equipeffi.domain.common.models import DeviceDraft
from equipeffi.domain.evaluation.device_types import (
    PUBLIC_DEVICE_TYPES,
    PUBLIC_DEVICE_NAMES,
    resolve_device_type,
)
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository


ROOT = Path(__file__).resolve().parents[2]


class PublicDeviceTypeTests(unittest.TestCase):
    def test_public_contract_contains_exactly_v4_fifteen_types(self):
        self.assertEqual(len(PUBLIC_DEVICE_TYPES), 15)
        self.assertEqual(PUBLIC_DEVICE_NAMES["motor"], "电动机")
        self.assertEqual(PUBLIC_DEVICE_NAMES["centrifugal_pump"], "离心泵")
        self.assertEqual(PUBLIC_DEVICE_NAMES["centrifugal_fan"], "离心通风机")
        self.assertEqual(PUBLIC_DEVICE_NAMES["axial_fan"], "轴流通风机")

    def test_public_motor_routes_to_internal_profiles(self):
        self.assertEqual(
            resolve_device_type("motor", {"category": "三相异步电动机（一般用途）", "rated_voltage": "0.4"}).internal_device_type,
            "motor_lv",
        )
        self.assertEqual(
            resolve_device_type("motor", {"category": "变频调速永磁同步电动机", "rated_voltage": "0.38"}).internal_device_type,
            "motor_pmsm",
        )
        self.assertEqual(
            resolve_device_type("motor", {"category": "高压三相异步电动机", "rated_voltage": "6"}).internal_device_type,
            "motor_hv",
        )

    def test_public_pump_and_fan_routes_are_not_ambiguous(self):
        self.assertEqual(resolve_device_type("centrifugal_pump", {"category": "单级单吸清水离心泵"}).internal_device_type, "pump_water")
        self.assertEqual(resolve_device_type("centrifugal_pump", {"category": "单级石油化工离心泵"}).internal_device_type, "pump_chemical")
        self.assertEqual(resolve_device_type("centrifugal_fan", {}).internal_device_type, "fan")
        self.assertEqual(resolve_device_type("axial_fan", {}).internal_device_type, "fan")

    def test_public_fan_type_rejects_conflicting_category(self):
        with self.assertRaises(ValueError):
            resolve_device_type("centrifugal_fan", {"category": "轴流通风机"})
        with self.assertRaises(ValueError):
            resolve_device_type("axial_fan", {"category": "离心通风机"})

    def test_public_device_type_can_be_evaluated_without_v4_adapter(self):
        service = EvaluationService(JsonStandardRepository(ROOT))
        result = service.evaluate(DeviceDraft(
            record_id="PUBLIC-MOTOR",
            device_type="motor",
            raw_values={
                "category": "三相异步电动机（一般用途）",
                "rated_voltage": "0.4",
                "rated_power": 7.5,
                "poles": 4,
                "rated_speed": 1480,
                "efficiency": 98,
            },
        ))
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.public_device_type, "motor")
        self.assertEqual(result.internal_device_type, "motor_lv")
        self.assertTrue(any(item["step_type"] == "公共设备类型路由" for item in result.trace))

    def test_v4_adapter_exposes_public_type_in_result(self):
        service = EvaluationService(JsonStandardRepository(ROOT))
        adapted = V4InputAdapter.adapt("V4-PUBLIC", "电动机", {
            "category": "三相异步电动机（一般用途）",
            "rated_voltage": "0.4",
            "rated_power": 7.5,
            "poles": 4,
            "rated_speed": 1480,
            "efficiency": 98,
        })
        result = service.evaluate(adapted.draft)
        self.assertEqual(result.public_device_type, "motor")
        self.assertEqual(result.internal_device_type, "motor_lv")


if __name__ == "__main__":
    unittest.main()
