from __future__ import annotations

import unittest
from pathlib import Path

from equipeffi.application.services.evaluation_facade import EvaluationFacade, EvaluationRequest
from equipeffi.application.services.evaluation_service import EvaluationService
from equipeffi.application.services.v4_template_contract import V4TemplateContract, V4_DEVICE_SHEETS
from equipeffi.domain.common.enums import Conclusion
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository


ROOT = Path(__file__).resolve().parents[2]


class V4ContractAndFacadeTests(unittest.TestCase):
    def test_contract_accepts_v4_config_column_aliases(self):
        rows = [
            {"sheet": sheet, "id": "device_name", "name": "设备名称", "group": "基础信息", "type": "文本", "unit": "-", "editable": "是", "required": "必填", "validation": "无"}
            for sheet in V4_DEVICE_SHEETS
        ]
        rows.append({"sheet": "变压器", "id": "rated_capacity", "name": "额定容量", "group": "设备参数", "type": "数值", "unit": "kVA", "editable": "是", "required": "必填", "validation": "数值>0", "min": 0})
        contract = V4TemplateContract.from_config_rows(rows)
        self.assertEqual(contract.validate(), [])
        fields = contract.fields_for_public_type("transformer", editable_only=True)
        self.assertEqual(fields[1].field_id, "rated_capacity")
        self.assertEqual(contract.schema_for_public_type("transformer")["sheet"], "变压器")

    def test_facade_manual_request_and_v4_request_share_result_contract(self):
        facade = EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT)))
        values = {
            "category": "三相异步电动机（一般用途）",
            "rated_voltage": "0.4",
            "rated_power": 7.5,
            "poles": 4,
            "rated_speed": 1480,
            "efficiency": 98,
        }
        manual = facade.evaluate(EvaluationRequest("MANUAL", "motor", values))
        v4 = facade.evaluate_v4("V4", "电动机", values)
        self.assertEqual(manual.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(v4.conclusion, manual.conclusion)
        self.assertEqual(manual.public_device_type, "motor")
        self.assertEqual(v4.public_device_type, "motor")
        self.assertEqual(facade.to_record(v4)["internal_device_type"], "motor_lv")

    def test_v4_quality_issues_are_separate_from_conclusion(self):
        facade = EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT)))
        result = facade.evaluate_v4(
            "V4-QUALITY",
            "电动机",
            {
                "device_name": " 电机 ",
                "model": "M-1",
                "quantity": "0",
                "category": "三相异步电动机（一般用途）",
                "rated_voltage": "0.4",
                "rated_power": 7.5,
                "poles": 4,
                "rated_speed": 1480,
                "efficiency": 98,
            },
        )
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        codes = {item["code"] for item in result.data_quality_issues}
        self.assertIn("required", codes)  # 铭牌照片缺失
        self.assertIn("positive_integer", codes)
        self.assertTrue(any("首尾空格" in item["message"] for item in result.data_quality_issues))

    def test_v4_axial_fan_calculates_pressure_coefficient_from_design_fields(self):
        facade = EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT)))
        result = facade.evaluate_v4(
            "V4-FAN",
            "轴流通风机",
            {
                "category": "轴流通风机",
                "machine_no": 3,
                "flow": 1000,
                "fan_pressure": 50,
                "inlet_stag_pressure": 101325,
                "impeller_power": 0.02,
                "isentropic_k": 1.4,
                "density": 1.2,
                "speed": 1000,
                "hub_ratio": 0.2,
                "design_efficiency": 78,
            },
        )
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertIn("压力系数", result.calculated_metrics)
        self.assertTrue(any(item.get("step_type") == "公式计算" for item in result.lookups))


if __name__ == "__main__":
    unittest.main()
