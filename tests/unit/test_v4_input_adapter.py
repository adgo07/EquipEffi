from __future__ import annotations

import unittest
from pathlib import Path
from decimal import Decimal

from equipeffi.application.services.evaluation_service import EvaluationService
from equipeffi.application.services.v4_input_adapter import V4AdaptationError, V4InputAdapter
from equipeffi.domain.common.enums import Conclusion
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository


ROOT = Path(__file__).resolve().parents[2]


class V4InputAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = EvaluationService(JsonStandardRepository(ROOT))

    def test_v4_motor_sheet_routes_to_low_voltage(self):
        adapted = V4InputAdapter.adapt("V4-LV", "电动机", {
            "category": "三相异步电动机（一般用途）",
            "rated_voltage": "0.4",
            "rated_power": 7.5,
            "poles": 4,
            "rated_speed": 1480,
            "efficiency": 98,
        })
        self.assertEqual(adapted.internal_device_type, "motor_lv")
        result = self.service.evaluate(adapted.draft)
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.trace[0]["step_type"], "V4工作表适配")

    def test_v4_motor_sheet_routes_to_pmsm(self):
        adapted = V4InputAdapter.adapt("V4-PMSM", "电动机", {
            "category": "变频调速永磁同步电动机",
            "rated_voltage": "0.38",
            "rated_power": 5.5,
            "poles": 4,
            "rated_speed": 1500,
            "efficiency": 94,
        })
        self.assertEqual(adapted.internal_device_type, "motor_pmsm")
        result = self.service.evaluate(adapted.draft)
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)

    def test_v4_generic_synchronous_motor_does_not_route_to_pmsm(self):
        adapted = V4InputAdapter.adapt("V4-SYNC", "电动机", {
            "category": "低压同步电动机",
            "rated_voltage": "0.4",
        })
        self.assertEqual(adapted.internal_device_type, "motor_lv")

    def test_v4_motor_voltage_with_v_suffix_is_interpreted_as_volts(self):
        adapted = V4InputAdapter.adapt("V4-LV-V", "电动机", {
            "category": "三相异步电动机（一般用途）",
            "rated_voltage": "380V",
        })
        self.assertEqual(adapted.internal_device_type, "motor_lv")

    def test_v4_pump_sheet_routes_water_and_chemical(self):
        water = V4InputAdapter.adapt("V4-W", "离心泵", {"category": "单级单吸清水离心泵"})
        chemical = V4InputAdapter.adapt("V4-C", "离心泵", {"category": "单级石油化工离心泵"})
        self.assertEqual(water.internal_device_type, "pump_water")
        self.assertEqual(chemical.internal_device_type, "pump_chemical")

    def test_v4_fan_sheets_route_to_common_evaluator_with_sheet_trace(self):
        centrifugal = V4InputAdapter.adapt("V4-CF", "离心通风机", {"category": "离心通风机"})
        axial = V4InputAdapter.adapt("V4-AF", "轴流通风机", {"category": "轴流通风机"})
        self.assertEqual(centrifugal.internal_device_type, "fan")
        self.assertEqual(axial.internal_device_type, "fan")
        self.assertEqual(axial.draft.metadata["v4_sheet"], "轴流通风机")

    def test_v4_submersible_category_preserves_pump_form_for_appendix_calculation(self):
        adapted = V4InputAdapter.adapt("V4-SUB", "潜水电泵", {
            "category": "小型潜水电泵（QDX）",
            "flow": 20,
            "head": 30,
            "rated_power": 1.5,
            "efficiency": 50,
            "tolerance": 2,
            "specific_speed": 50,
            "motor_efficiency": 71,
        })
        result = self.service.evaluate(adapted.draft)
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.calculated_metrics["规定效率ηDB_%"], Decimal("42.165"))
        # V4模板不含泵型显示列，接口仍应保留自动识别的下泵式，
        # 并可在附加参数齐全时进入附录A计算路径。
        normalized = next(item for item in result.trace if item.get("step_type") == "输入规范化")
        self.assertTrue(any(change.get("target_field") == "subtype" for change in normalized["changes"]))

    def test_conflicting_v4_fan_sheet_and_category_is_rejected(self):
        with self.assertRaises(V4AdaptationError):
            V4InputAdapter.adapt("V4-BAD", "离心通风机", {"category": "轴流通风机"})

    def test_unknown_v4_motor_route_is_not_guessed(self):
        with self.assertRaises(V4AdaptationError):
            V4InputAdapter.adapt("V4-UNKNOWN", "电动机", {"category": "未知电机"})


if __name__ == "__main__":
    unittest.main()
