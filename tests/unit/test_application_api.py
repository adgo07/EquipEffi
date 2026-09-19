from __future__ import annotations

import unittest
import json
from pathlib import Path

from equipeffi.application.services.evaluation_facade import EvaluationFacade
from equipeffi.application.services.evaluation_service import EvaluationService
from equipeffi.application.services.batch_evaluation_service import BatchEvaluationService
from equipeffi.application.bootstrap import create_application_api
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository
from equipeffi.infrastructure.excel.v4_reader import V4WorkbookReaderImpl
from equipeffi.presentation.api.application_api import ApplicationApi, ApiRequestError


ROOT = Path(__file__).resolve().parents[2]


class ApplicationApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = ApplicationApi(EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT))))

    def test_public_type_list_is_fifteen(self):
        self.assertEqual(len(self.api.device_types()), 15)

    def test_schema_exposes_device_specific_conclusion_values(self):
        ordinary = self.api.schema("motor")["allowed_conclusions"]
        self.assertEqual(ordinary, ["不在范围", "无法判定", "淘汰", "未达标", "3级", "2级", "1级"])
        self.assertNotIn("4级", ordinary)
        self.assertEqual(
            self.api.schema("blower")["allowed_conclusions"],
            ["不在范围", "无法判定", "淘汰", "未达标", "节能评价值", "能效限定值"],
        )
        self.assertEqual(
            self.api.schema("鼓风机")["allowed_conclusions"],
            ["不在范围", "无法判定", "淘汰", "未达标", "节能评价值", "能效限定值"],
        )
        self.assertEqual(
            self.api.schema("heat_treatment")["allowed_conclusions"][-3:],
            ["一等", "二等", "三等"],
        )
        self.assertEqual(self.api.schema("heat_pump_water_heater")["allowed_conclusions"][-5:], ["1级", "2级", "3级", "4级", "5级"])

    def test_all_public_types_expose_only_their_allowed_conclusion_set(self):
        """公共15类接口的结论集合必须与设备族规则保持一致。"""

        common = ["不在范围", "无法判定", "淘汰", "未达标"]
        ordinary = common + ["3级", "2级", "1级"]
        expected = {
            "blower": common + ["节能评价值", "能效限定值"],
            "heat_treatment": common + ["一等", "二等", "三等"],
            "heat_pump_water_heater": common + ["1级", "2级", "3级", "4级", "5级"],
        }
        for item in self.api.device_types():
            public_type = item["code"]
            with self.subTest(public_type=public_type):
                self.assertEqual(
                    self.api.schema(public_type)["allowed_conclusions"],
                    expected.get(public_type, ordinary),
                )

    def test_schema_exposes_device_specific_conclusion_field_label(self):
        self.assertEqual(self.api.schema("blower")["conclusion_field"], "能效结论")
        self.assertEqual(self.api.schema("鼓风机")["conclusion_field"], "能效结论")
        self.assertEqual(self.api.schema("heat_treatment")["conclusion_field"], "评价等级")
        self.assertEqual(self.api.schema("热处理设备")["conclusion_field"], "评价等级")
        self.assertEqual(self.api.schema("motor")["conclusion_field"], "能效等级")

    def test_blower_schema_exposes_multistage_efficiency_extension(self):
        extension = next(item for item in self.api.schema("blower")["extensions"] if item["field_id"] == "stage_efficiencies")
        self.assertTrue(extension["editable"])
        self.assertEqual(extension["unit"], "%")
        self.assertIn("数量必须等于级数", extension["validation"])
        self.assertEqual(self.api.schema("motor")["extensions"], [])

    def test_schema_without_v4_contract_uses_profile_fallback_fields(self):
        fan_fields = {item["field_id"] for item in self.api.schema("centrifugal_fan")["fields"]}
        self.assertTrue({"machine_no", "flow_m3h", "fan_pressure_pa", "impeller_power_kw"}.issubset(fan_fields))
        blower_fields = {item["field_id"] for item in self.api.schema("blower")["fields"]}
        self.assertTrue({"stages", "stage_efficiencies", "inlet_absolute_pressure_kpa", "outlet_temperature_k"}.issubset(blower_fields))
        self.assertIn("回退字段", self.api.schema("motor")["note"])
        result_fields = {item["field_id"] for item in self.api.schema("motor")["result_fields"]}
        self.assertTrue({"seq", "standard_code", "standard_table", "conclusion", "explanation", "missing_fields"}.issubset(result_fields))
        self.assertIn("auto_note", result_fields)
        self.assertTrue({"grade1", "grade2", "grade3"}.issubset(result_fields))
        self.assertTrue(all(item["editable"] is False for item in self.api.schema("motor")["result_fields"]))

    def test_v4_schema_projection_uses_metadata_for_all_fifteen_public_types(self):
        template = ROOT / "src" / "equipeffi" / "resources" / "templates" / "设备能效分析空白模板_重构版V4_20260825.xlsx"
        contract = V4WorkbookReaderImpl().read_contract(template)
        api = ApplicationApi(self.api.facade, contract=contract)
        for item in api.device_types():
            public_code = item["code"]
            with self.subTest(public_type=public_code):
                schema = api.schema(public_code)
                expected = contract.fields_for_public_type(public_code, editable_only=True)
                self.assertEqual(
                    [field["field_id"] for field in schema["fields"]],
                    [field.field_id for field in expected],
                )
                self.assertEqual(
                    [(field["display_name"], field["unit"]) for field in schema["fields"]],
                    [(field.display_name, field.unit) for field in expected],
                )

    def test_fallback_motor_cooling_schema_exposes_all_standard_options(self):
        field = next(
            item for item in self.api.schema("motor")["fields"]
            if item["field_id"] == "cooling_method"
        )
        self.assertEqual(field["enum_name"], "EV_COOLING_MOTOR_HV")
        self.assertTrue({"IC86W", "IC71W(IC3W7)", "IC416", "IC666"}.issubset(field["enum_values"]))
        self.assertEqual(len(field["enum_values"]), 16)

    def test_fallback_motor_schema_exposes_standard_category_options(self):
        field = next(item for item in self.api.schema("motor")["fields"] if item["field_id"] == "category")
        self.assertEqual(field["enum_name"], "EV_MOTOR_CATEGORY")
        self.assertEqual(tuple(field["enum_values"]), (
            "三相异步电动机", "电容起动异步电动机", "电容运转异步电动机", "双值电容异步电动机",
            "空调器风扇用无刷直流电动机", "空调器风扇用电容运转电动机", "高压三相笼型异步电动机",
            "异步起动三相永磁同步电动机", "变频调速永磁同步电动机", "电梯用永磁同步电动机",
            "其他（请备注说明）",
        ))

    def test_fallback_motor_schema_exposes_standard_rated_voltage_options(self):
        field = next(item for item in self.api.schema("motor")["fields"] if item["field_id"] == "rated_voltage_v")
        self.assertEqual(field["enum_name"], "EV_MOTOR_VOLTAGE")
        self.assertEqual(tuple(field["enum_values"]), ("0.2", "0.4", "3（3.3）", "6", "其他（请备注说明）", "10"))

    def test_fallback_motor_schema_exposes_standard_poles_options(self):
        field = next(item for item in self.api.schema("motor")["fields"] if item["field_id"] == "poles")
        self.assertEqual(field["enum_name"], "EV_POLES_PMSM")
        self.assertEqual(tuple(field["enum_values"]), ("2", "4", "6", "8", "12", "10", "16", "20", "24", "32", "40", "48", "其他（请备注说明）"))

    def test_fallback_motor_schema_exposes_rated_speed_numeric_constraint(self):
        field = next(item for item in self.api.schema("motor")["fields"] if item["field_id"] == "rated_speed_rpm")
        self.assertEqual(field["display_name"], "额定转速")
        self.assertEqual(field["unit"], "r/min")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])
        self.assertEqual(field["enum_values"], [])

    def test_fallback_stage_count_schema_exposes_positive_integer_constraint(self):
        for public_type in ("centrifugal_pump", "blower", "submersible_pump"):
            with self.subTest(public_type=public_type):
                field = next(
                    item for item in self.api.schema(public_type)["fields"]
                    if item["field_id"] == "stages"
                )
                self.assertEqual(field["data_type"], "整数")
                self.assertEqual(field["unit"], "级")
                self.assertEqual(field["minimum"], 1)
                self.assertIsNone(field["maximum"])
                self.assertIn("正整数", field["validation"])

    def test_fallback_heat_treatment_temperature_schema_uses_metadata_positive_hint(self):
        field = next(
            item for item in self.api.schema("heat_treatment")["fields"]
            if item["field_id"] == "rated_temperature_c"
        )
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "℃")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_fan_machine_no_schema_allows_decimal_positive_value(self):
        for public_type in ("centrifugal_fan", "axial_fan"):
            with self.subTest(public_type=public_type):
                field = next(
                    item for item in self.api.schema(public_type)["fields"]
                    if item["field_id"] == "machine_no"
                )
                self.assertEqual(field["data_type"], "数值")
                self.assertEqual(field["unit"], "No.")
                self.assertEqual(field["minimum"], 0)
                self.assertIsNone(field["maximum"])
                self.assertIn("数值>0", field["validation"])

    def test_fallback_result_fields_follow_special_device_levels(self):
        heat_pump_fields = {item["field_id"] for item in self.api.schema("heat_pump_water_heater")["result_fields"]}
        self.assertTrue({"cop1", "cop2", "cop3", "cop4", "cop5", "auto_note"}.issubset(heat_pump_fields))
        blower_fields = {item["field_id"] for item in self.api.schema("blower")["result_fields"]}
        self.assertTrue({"b2_d2", "limit_value", "saving_value", "auto_note"}.issubset(blower_fields))
        multi_fields = {item["field_id"] for item in self.api.schema("multi_split_ac")["result_fields"]}
        self.assertTrue({"primary_l1", "primary_l2", "primary_l3", "eer_min_l1", "cop_minus12_limit"}.issubset(multi_fields))

    def test_fallback_result_field_ids_are_unique_for_all_public_types(self):
        for device_type in self.api.device_types():
            code = device_type["code"]
            with self.subTest(device_type=code):
                field_ids = [item["field_id"] for item in self.api.schema(code)["result_fields"]]
                self.assertEqual(len(field_ids), len(set(field_ids)))

    def test_fallback_schema_keeps_common_identity_and_attachment_fields(self):
        fields = {item["field_id"]: item for item in self.api.schema("motor")["fields"]}
        self.assertTrue({"device_name", "model", "quantity", "category", "location", "photo"}.issubset(fields))
        self.assertEqual(fields["quantity"]["data_type"], "整数")
        self.assertEqual(fields["quantity"]["minimum"], 1)
        self.assertEqual(fields["photo"]["data_type"], "图片")

    def test_fallback_schema_reuses_v4_numeric_boundaries(self):
        motor = {item["field_id"]: item for item in self.api.schema("motor")["fields"]}
        self.assertEqual(motor["rated_efficiency"]["minimum"], 1)
        self.assertEqual(motor["rated_efficiency"]["maximum"], 100)
        self.assertEqual(motor["poles"]["minimum"], 1)

        boiler = {item["field_id"]: item for item in self.api.schema("industrial_boiler")["fields"]}
        self.assertEqual(boiler["design_efficiency"]["minimum"], 1)
        self.assertEqual(boiler["design_efficiency"]["maximum"], 110)
        self.assertEqual(
            boiler["design_efficiency"]["conditional_limits"][1]["maximum"],
            100,
        )

        multi = {item["field_id"]: item for item in self.api.schema("multi_split_ac")["fields"]}
        self.assertEqual(multi["external_static_pressure_pa"]["minimum"], 0)
        self.assertIn("数值≥0", multi["external_static_pressure_pa"]["validation"])

    def test_fallback_multi_split_external_static_schema_uses_metadata_non_negative_hint(self):
        field = next(item for item in self.api.schema("multi_split_ac")["fields"]
                     if item["field_id"] == "external_static_pressure_pa")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "Pa")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值≥0", field["validation"])

    def test_fallback_chiller_primary_metric_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("heat_pump_chiller")["fields"]
                     if item["field_id"] == "primary_metric_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "-")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_chiller_aux_metric1_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("heat_pump_chiller")["fields"]
                     if item["field_id"] == "aux_metric1_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "-")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_chiller_aux_metric2_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("heat_pump_chiller")["fields"]
                     if item["field_id"] == "aux_metric2_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "-")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_compressor_schema_exposes_standard_category_options(self):
        field = next(item for item in self.api.schema("compressor")["fields"] if item["field_id"] == "category")
        self.assertEqual(field["enum_name"], "EV_COMPRESSOR_CATEGORY")
        self.assertEqual(len(field["enum_values"]), 7)

    def test_fallback_compressor_schema_exposes_standard_cooling_options(self):
        field = next(item for item in self.api.schema("compressor")["fields"] if item["field_id"] == "cooling_method")
        self.assertEqual(field["enum_name"], "EV_COMPRESSOR_COOLING")
        self.assertEqual(tuple(field["enum_values"]), ("风冷", "液冷", "不适用", "其他（请备注说明）"))

    def test_fallback_compressor_input_power_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("compressor")["fields"] if item["field_id"] == "input_power_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_compressor_volume_flow_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("compressor")["fields"] if item["field_id"] == "volume_flow_m3min")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "m³/min")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_compressor_discharge_pressure_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("compressor")["fields"] if item["field_id"] == "discharge_pressure_mpa")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "MPa")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_compressor_specific_power_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("compressor")["fields"] if item["field_id"] == "specific_power")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW/(m³/min)")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_pump_schema_exposes_standard_category_options(self):
        field = next(item for item in self.api.schema("centrifugal_pump")["fields"] if item["field_id"] == "category")
        self.assertEqual(field["enum_name"], "EV_PUMP_CATEGORY")
        self.assertEqual(len(field["enum_values"]), 9)

    def test_fallback_pump_schema_exposes_standard_suction_options(self):
        field = next(item for item in self.api.schema("centrifugal_pump")["fields"] if item["field_id"] == "suction")
        self.assertEqual(field["enum_name"], "EV_SUCTION")
        self.assertEqual(tuple(field["enum_values"]), ("单吸", "双吸", "不适用", "其他（请备注说明）"))

    def test_fallback_submersible_schema_exposes_standard_device_form_options(self):
        field = next(item for item in self.api.schema("submersible_pump")["fields"] if item["field_id"] == "subtype")
        self.assertEqual(field["enum_name"], "EV_SUB_FORM_ALL")
        self.assertEqual(len(field["enum_values"]), 20)

    def test_fallback_submersible_schema_exposes_standard_category_options(self):
        field = next(item for item in self.api.schema("submersible_pump")["fields"] if item["field_id"] == "category")
        self.assertEqual(field["enum_name"], "EV_SUBMERSIBLE_CATEGORY")
        self.assertEqual(tuple(field["enum_values"]), (
            "小型潜水电泵", "大中型潜水电泵", "污水污物潜水电泵",
            "井用潜水电泵", "其他（请备注说明）", "混流潜水电泵",
        ))

    def test_fallback_boiler_schema_exposes_standard_category_options(self):
        field = next(item for item in self.api.schema("industrial_boiler")["fields"] if item["field_id"] == "category")
        self.assertEqual(field["enum_name"], "EV_BOILER_CATEGORY")
        self.assertEqual(len(field["enum_values"]), 9)

    def test_fallback_boiler_schema_exposes_standard_fuel_options(self):
        field = next(item for item in self.api.schema("industrial_boiler")["fields"] if item["field_id"] == "fuel")
        self.assertEqual(field["enum_name"], "EV_FUEL")
        self.assertEqual(tuple(field["enum_values"]), (
            "烟煤", "贫煤", "无烟煤", "褐煤", "天然气",
            "生物质", "燃油", "煤（室燃）", "电力", "其他（请备注说明）",
        ))

    def test_fallback_boiler_volatile_matter_schema_uses_metadata_range(self):
        field = next(item for item in self.api.schema("industrial_boiler")["fields"] if item["field_id"] == "volatile_matter_percent")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "%")
        self.assertEqual(field["minimum"], 0)
        self.assertEqual(field["maximum"], 100)
        self.assertIn("0～100", field["validation"])

    def test_fallback_boiler_evaporation_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("industrial_boiler")["fields"] if item["field_id"] == "evaporation_tph")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "t/h")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_boiler_thermal_power_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("industrial_boiler")["fields"] if item["field_id"] == "thermal_power_mw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "MW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_boiler_lhv_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("industrial_boiler")["fields"] if item["field_id"] == "lower_heating_value_kjkg")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kJ/kg")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_heat_treatment_schema_exposes_standard_category_options(self):
        field = next(item for item in self.api.schema("heat_treatment")["fields"] if item["field_id"] == "category")
        self.assertEqual(field["enum_name"], "EV_HEAT_TREAT_CATEGORY")
        self.assertEqual(tuple(field["enum_values"]), (
            "传送式连续炉", "震底式连续炉", "推送式连续炉", "滚筒式连续炉",
            "井式炉-中温炉", "箱式多用炉", "井式炉-回火炉", "井式炉-气体渗碳(氮)炉",
            "箱式炉", "台车炉", "热处理电热浴炉", "辊底炉", "罩式炉", "其他（请备注说明）",
        ))

    def test_fallback_heat_treatment_schema_exposes_standard_energy_type_options(self):
        field = next(item for item in self.api.schema("heat_treatment")["fields"] if item["field_id"] == "energy_type")
        self.assertEqual(field["enum_name"], "EV_ENERGY_TYPE")
        self.assertEqual(tuple(field["enum_values"]), (
            "燃料油", "发生炉煤气（1250kcal/m³～1350kcal/m³）",
            "发生炉煤气（1400kcal/m³～2200kcal/m³）", "城市煤气/焦炉煤气",
            "电力", "天然气", "其他（请备注说明）",
        ))

    def test_fallback_hpwh_schema_exposes_standard_heating_method_options(self):
        field = next(item for item in self.api.schema("heat_pump_water_heater")["fields"] if item["field_id"] == "heating_method")
        self.assertEqual(field["enum_name"], "EV_HEATING_METHOD")
        self.assertEqual(len(field["enum_values"]), 5)

    def test_fallback_hpwh_schema_exposes_standard_category_options(self):
        field = next(item for item in self.api.schema("heat_pump_water_heater")["fields"] if item["field_id"] == "category")
        self.assertEqual(field["enum_name"], "EV_HPWH_CATEGORY")
        self.assertEqual(tuple(field["enum_values"]), ("普通型", "低温型", "其他（请备注说明）"))

    def test_fallback_hpwh_schema_exposes_standard_with_pump_options(self):
        field = next(item for item in self.api.schema("heat_pump_water_heater")["fields"] if item["field_id"] == "with_pump")
        self.assertEqual(field["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(field["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_hpwh_heating_capacity_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("heat_pump_water_heater")["fields"] if item["field_id"] == "heating_capacity_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_hpwh_rated_power_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("heat_pump_water_heater")["fields"] if item["field_id"] == "rated_power_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_hpwh_cop_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("heat_pump_water_heater")["fields"] if item["field_id"] == "cop")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "W/W")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_chiller_rated_power_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("heat_pump_chiller")["fields"] if item["field_id"] == "rated_power_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_chiller_cooling_capacity_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("heat_pump_chiller")["fields"] if item["field_id"] == "cooling_capacity_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_chiller_heating_capacity_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("heat_pump_chiller")["fields"] if item["field_id"] == "heating_capacity_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_duct_cooling_capacity_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("duct_ac")["fields"] if item["field_id"] == "cooling_capacity_w")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "W")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_duct_rated_power_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("duct_ac")["fields"] if item["field_id"] == "rated_power_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        # This V4-only fallback column has no legacy note; the metadata lower
        # bound is still exposed while the service enforces strict > 0.

    def test_fallback_duct_indicator_value_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("duct_ac")["fields"] if item["field_id"] == "indicator_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "按指标")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_unitary_cooling_capacity_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("unitary_ac")["fields"] if item["field_id"] == "cooling_capacity_w")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "W")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_unitary_rated_power_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("unitary_ac")["fields"] if item["field_id"] == "rated_power_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        # This V4-only fallback column has no legacy note; the metadata lower
        # bound is still exposed while the service enforces strict > 0.

    def test_fallback_unitary_indicator_value_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("unitary_ac")["fields"] if item["field_id"] == "indicator_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "按指标")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_multi_split_cooling_capacity_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("multi_split_ac")["fields"] if item["field_id"] == "cooling_capacity_w")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "W")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_multi_split_heating_capacity_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("multi_split_ac")["fields"] if item["field_id"] == "heating_capacity_w")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "W")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("低温类别条件必填", field["validation"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_multi_split_rated_power_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("multi_split_ac")["fields"] if item["field_id"] == "rated_power_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        # This V4-only fallback column has no legacy note; the metadata lower
        # bound is still exposed while the service enforces strict > 0.

    def test_fallback_multi_split_primary_metric_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("multi_split_ac")["fields"]
                     if item["field_id"] == "primary_metric_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "无量纲")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_multi_split_eer_min_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("multi_split_ac")["fields"]
                     if item["field_id"] == "eer_min_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "W/W")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertEqual(field["required"], "可选")
        self.assertIn("风冷式且制冷量≤14kW时必填", field["validation"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_multi_split_cop_minus12_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("multi_split_ac")["fields"]
                     if item["field_id"] == "cop_minus12_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "W/W")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertEqual(field["required"], "可选")
        self.assertIn("低温多联机条件必填", field["validation"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_multi_split_cop_minus20_schema_uses_metadata_positive_hint(self):
        field = next(item for item in self.api.schema("multi_split_ac")["fields"]
                     if item["field_id"] == "cop_minus20_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "W/W")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertEqual(field["required"], "可选")
        self.assertIn("低温多联机条件必填", field["validation"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_heat_pump_chiller_schema_exposes_standard_category_options(self):
        field = next(item for item in self.api.schema("heat_pump_chiller")["fields"] if item["field_id"] == "category")
        self.assertEqual(field["enum_name"], "EV_HP_CHILLER_CATEGORY")
        self.assertEqual(tuple(field["enum_values"]), (
            "蒸气压缩循环冷水（热泵）机组-舒适型",
            "蒸气压缩循环冷水（热泵）机组-数据中心专用型",
            "低环境温度空气源热泵（冷水）机组",
            "水（地）源热泵机组",
            "蒸气压缩循环高温热泵机组",
            "溴化锂吸收式冷（温）水机组",
            "间接蒸发冷却冷水机组",
            "一体式冷水（热泵）机组",
            "其他（请备注说明）",
        ))

    def test_fallback_centrifugal_fan_schema_exposes_standard_transmission_options(self):
        field = next(item for item in self.api.schema("centrifugal_fan")["fields"] if item["field_id"] == "transmission")
        self.assertEqual(field["enum_name"], "EV_TRANSMISSION")
        self.assertEqual(tuple(field["enum_values"]), (
            "A式传动（普通电动机直联）", "外转子电机直联", "其他传动", "不适用", "其他（请备注说明）",
        ))

    def test_fallback_axial_fan_schema_exposes_standard_transmission_options(self):
        field = next(item for item in self.api.schema("axial_fan")["fields"] if item["field_id"] == "transmission")
        self.assertEqual(field["enum_name"], "EV_TRANSMISSION")
        self.assertEqual(tuple(field["enum_values"]), (
            "A式传动（普通电动机直联）", "外转子电机直联", "其他传动", "不适用", "其他（请备注说明）",
        ))

    def test_fallback_centrifugal_fan_schema_exposes_standard_suction_options(self):
        field = next(item for item in self.api.schema("centrifugal_fan")["fields"] if item["field_id"] == "suction")
        self.assertEqual(field["enum_name"], "EV_SUCTION")
        self.assertEqual(tuple(field["enum_values"]), ("单吸", "双吸", "不适用", "其他（请备注说明）"))

    def test_fallback_centrifugal_fan_schema_exposes_standard_hvac_use_options(self):
        field = next(item for item in self.api.schema("centrifugal_fan")["fields"] if item["field_id"] == "hvac_use")
        self.assertEqual(field["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(field["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_centrifugal_fan_schema_exposes_standard_inlet_box_options(self):
        field = next(item for item in self.api.schema("centrifugal_fan")["fields"] if item["field_id"] == "inlet_box")
        self.assertEqual(field["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(field["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_axial_fan_schema_exposes_standard_inlet_box_options(self):
        field = next(item for item in self.api.schema("axial_fan")["fields"] if item["field_id"] == "inlet_box")
        self.assertEqual(field["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(field["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_axial_fan_schema_exposes_standard_diffuser_options(self):
        field = next(item for item in self.api.schema("axial_fan")["fields"] if item["field_id"] == "diffuser")
        self.assertEqual(field["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(field["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_axial_fan_schema_exposes_standard_variable_blade_options(self):
        field = next(item for item in self.api.schema("axial_fan")["fields"] if item["field_id"] == "variable_blade")
        self.assertEqual(field["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(field["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_axial_fan_schema_exposes_standard_reversible_options(self):
        field = next(item for item in self.api.schema("axial_fan")["fields"] if item["field_id"] == "reversible")
        self.assertEqual(field["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(field["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_heat_pump_chiller_schema_exposes_standard_product_standard_options(self):
        field = next(item for item in self.api.schema("heat_pump_chiller")["fields"] if item["field_id"] == "product_standard")
        self.assertEqual(field["enum_name"], "EV_HP_STD_ALL")
        self.assertEqual(tuple(field["enum_values"]), (
            "GB/T 18430.1", "GB/T 18430.2", "GB/T 25127.1", "GB/T 25127.2",
            "GB/T 18431", "GB/T 19409", "GB/T 18362", "GB/T 25861",
            "JB/T 12840", "JB/T 14642", "JB/T 14640", "JB/T 12839",
            "其他（请备注说明）",
        ))

    def test_fallback_heat_pump_chiller_schema_exposes_standard_unit_type_options(self):
        field = next(item for item in self.api.schema("heat_pump_chiller")["fields"] if item["field_id"] == "unit_type")
        self.assertEqual(field["enum_name"], "EV_HP_UNIT_ALL")
        self.assertEqual(tuple(field["enum_values"]), (
            "舒适型", "数据中心专用型", "地板采暖型", "风机盘管型", "冷热风型-热泵型",
            "散热器型", "冷热水型-单热型", "冷热水型-热泵型", "饱和蒸汽压力0.4MPa",
            "饱和蒸汽压力0.6MPa", "饱和蒸汽压力0.8MPa", "直燃型机组", "H1a", "H2a",
            "H3a", "H4a", "H5a", "H1b", "H2b", "H3b", "H4b", "H5b",
            "循环供水式热泵高温热水机组", "外冷式", "内冷式", "内外冷串联式", "风冷式",
            "蒸发冷却式冷却塔式", "其他（请备注说明）",
        ))

    def test_fallback_heat_pump_chiller_schema_exposes_standard_source_options(self):
        field = next(item for item in self.api.schema("heat_pump_chiller")["fields"] if item["field_id"] == "source")
        self.assertEqual(field["enum_name"], "EV_HP_SOURCE_ALL")
        self.assertEqual(tuple(field["enum_values"]), (
            "水冷式", "风冷式", "蒸发冷却式", "空气源", "地下水式", "水环式",
            "地埋管式", "地表水式", "饱和蒸汽", "直燃", "不适用", "其他（请备注说明）",
        ))

    def test_fallback_heat_pump_chiller_schema_exposes_standard_evaluation_system_options(self):
        field = next(item for item in self.api.schema("heat_pump_chiller")["fields"] if item["field_id"] == "evaluation_system")
        self.assertEqual(field["enum_name"], "EV_HP_EVAL_SYSTEM")
        self.assertEqual(tuple(field["enum_values"]), (
            "综合部分负荷/季节性能指标体系（表1）",
            "制冷性能系数COPc指标体系（表2）",
            "对应产品类别指标体系（表3～表8）",
            "其他（请备注说明）",
        ))

    def test_fallback_centrifugal_fan_schema_exposes_standard_category_options(self):
        field = next(item for item in self.api.schema("centrifugal_fan")["fields"] if item["field_id"] == "category")
        self.assertEqual(field["enum_name"], "EV_CENTRIFUGAL_FAN_CATEGORY")
        self.assertEqual(tuple(field["enum_values"]), (
            "离心通风机", "外转子电机直联前向多翼离心风机", "其他（请备注说明）",
        ))

    def test_fallback_axial_fan_schema_exposes_standard_category_options(self):
        field = next(item for item in self.api.schema("axial_fan")["fields"] if item["field_id"] == "category")
        self.assertEqual(field["enum_name"], "EV_AXIAL_FAN_CATEGORY")
        self.assertEqual(tuple(field["enum_values"]), ("轴流通风机", "其他（请备注说明）"))

    def test_fallback_blower_schema_exposes_standard_category_options(self):
        field = next(item for item in self.api.schema("blower")["fields"] if item["field_id"] == "category")
        self.assertEqual(field["enum_name"], "EV_BLOWER_CATEGORY")
        self.assertEqual(tuple(field["enum_values"]), (
            "单级双支撑低速离心鼓风机", "多级低速离心鼓风机",
            "单级双支撑高速离心鼓风机", "多级高速离心鼓风机",
            "其他（请备注说明）",
        ))

    def test_fallback_blower_schema_exposes_inlet_pressure_numeric_constraint(self):
        field = next(item for item in self.api.schema("blower")["fields"] if item["field_id"] == "inlet_absolute_pressure_kpa")
        self.assertEqual(field["display_name"], "进口绝对压力")
        self.assertEqual(field["unit"], "kPa")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_blower_schema_exposes_outlet_pressure_numeric_constraint(self):
        field = next(item for item in self.api.schema("blower")["fields"] if item["field_id"] == "outlet_absolute_pressure_kpa")
        self.assertEqual(field["display_name"], "出口绝对压力")
        self.assertEqual(field["unit"], "kPa")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_blower_schema_exposes_inlet_temperature_numeric_constraint(self):
        field = next(item for item in self.api.schema("blower")["fields"] if item["field_id"] == "inlet_temperature_k")
        self.assertEqual(field["display_name"], "进口温度")
        self.assertEqual(field["unit"], "K")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_blower_schema_exposes_outlet_temperature_numeric_constraint(self):
        field = next(item for item in self.api.schema("blower")["fields"] if item["field_id"] == "outlet_temperature_k")
        self.assertEqual(field["display_name"], "出口温度")
        self.assertEqual(field["unit"], "K")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_blower_schema_exposes_impeller_width_numeric_constraint(self):
        field = next(item for item in self.api.schema("blower")["fields"] if item["field_id"] == "impeller_width_mm")
        self.assertEqual(field["display_name"], "叶轮出口宽度b₂")
        self.assertEqual(field["unit"], "mm")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_blower_schema_exposes_impeller_diameter_numeric_constraint(self):
        field = next(item for item in self.api.schema("blower")["fields"] if item["field_id"] == "impeller_diameter_mm")
        self.assertEqual(field["display_name"], "叶轮出口直径D₂")
        self.assertEqual(field["unit"], "mm")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_blower_schema_exposes_polytropic_efficiency_percentage_constraint(self):
        field = next(item for item in self.api.schema("blower")["fields"] if item["field_id"] == "polytropic_efficiency")
        self.assertEqual(field["display_name"], "多变效率")
        self.assertEqual(field["unit"], "%")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["minimum"], 1)
        self.assertEqual(field["maximum"], 100)
        self.assertIn("百分数本值1～100", field["validation"])

    def test_fallback_fan_and_blower_schema_exposes_isentropic_k_numeric_range(self):
        for public_type in ("centrifugal_fan", "axial_fan", "blower"):
            with self.subTest(public_type=public_type):
                field = next(
                    item
                    for item in self.api.schema(public_type)["fields"]
                    if item["field_id"] == "isentropic_k"
                )
                self.assertEqual(field["data_type"], "数值")
                self.assertEqual(field["unit"], "-")
                self.assertEqual(field["minimum"], 1)
                self.assertEqual(field["maximum"], 2)
                self.assertIn("1～2", field["validation"])

    def test_fallback_axial_fan_schema_exposes_hub_ratio_numeric_range(self):
        field = next(item for item in self.api.schema("axial_fan")["fields"] if item["field_id"] == "hub_ratio")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "-")
        self.assertEqual(field["minimum"], 0)
        self.assertEqual(field["maximum"], 1)
        self.assertIn("0～1", field["validation"])

    def test_fallback_centrifugal_fan_schema_keeps_hub_ratio_internal_text(self):
        field = next(item for item in self.api.schema("centrifugal_fan")["fields"] if item["field_id"] == "hub_ratio")
        self.assertEqual(field["data_type"], "文本")
        self.assertIsNone(field["minimum"])
        self.assertIsNone(field["maximum"])

    def test_fallback_submersible_schema_exposes_temperature_numeric_range(self):
        field = next(item for item in self.api.schema("submersible_pump")["fields"] if item["field_id"] == "working_temperature_c")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "℃")
        self.assertEqual(field["minimum"], 0)
        self.assertEqual(field["maximum"], 100)
        self.assertIn("0～100", field["validation"])

    def test_fallback_blower_schema_exposes_standard_multi_impeller_options(self):
        field = next(item for item in self.api.schema("blower")["fields"] if item["field_id"] == "multi_impeller")
        self.assertEqual(field["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(field["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_blower_schema_exposes_standard_cantilever_options(self):
        field = next(item for item in self.api.schema("blower")["fields"] if item["field_id"] == "cantilever")
        self.assertEqual(field["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(field["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_blower_schema_exposes_standard_three_dimensional_options(self):
        field = next(item for item in self.api.schema("blower")["fields"] if item["field_id"] == "three_dimensional")
        self.assertEqual(field["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(field["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_duct_schema_exposes_standard_category_options(self):
        field = next(item for item in self.api.schema("duct_ac")["fields"] if item["field_id"] == "category")
        self.assertEqual(field["enum_name"], "EV_DUCT_CATEGORY")
        self.assertEqual(tuple(field["enum_values"]), (
            "风管送风式空调（热泵）机组",
            "直接蒸发式全新风空气处理机组",
            "其他（请备注说明）",
        ))

    def test_fallback_duct_schema_exposes_standard_cooling_options(self):
        field = next(item for item in self.api.schema("duct_ac")["fields"] if item["field_id"] == "cooling_source")
        self.assertEqual(field["enum_name"], "EV_AC_COOLING_DUCT")
        self.assertEqual(tuple(field["enum_values"]), ("风冷式", "水冷式（水环式）", "不适用", "其他（请备注说明）"))

    def test_fallback_duct_schema_exposes_standard_mode_options(self):
        field = next(item for item in self.api.schema("duct_ac")["fields"] if item["field_id"] == "mode")
        self.assertEqual(field["enum_name"], "EV_AC_MODE")
        self.assertEqual(tuple(field["enum_values"]), ("单冷型", "热泵型", "不适用", "其他（请备注说明）"))

    def test_fallback_duct_schema_exposes_standard_enthalpy_options(self):
        field = next(item for item in self.api.schema("duct_ac")["fields"] if item["field_id"] == "enthalpy_difference")
        self.assertEqual(field["enum_name"], "EV_ENTHALPY")
        self.assertEqual(tuple(field["enum_values"]), ("小焓差", "大焓差", "不适用", "其他（请备注说明）"))

    def test_fallback_unitary_schema_exposes_standard_category_options(self):
        field = next(item for item in self.api.schema("unitary_ac")["fields"] if item["field_id"] == "category")
        self.assertEqual(field["enum_name"], "EV_UNITARY_CATEGORY")
        self.assertEqual(tuple(field["enum_values"]), (
            "普通单元式空调机",
            "计算机和数据处理机房用单元式空调机",
            "通讯基站用单元式空气调节机",
            "恒温恒湿型单元式空调机",
            "其他（请备注说明）",
        ))

    def test_fallback_unitary_schema_exposes_standard_cooling_options(self):
        field = next(item for item in self.api.schema("unitary_ac")["fields"] if item["field_id"] == "cooling_source")
        self.assertEqual(field["enum_name"], "EV_AC_COOLING_UNITARY")
        self.assertEqual(tuple(field["enum_values"]), (
            "风冷式", "水冷式", "乙二醇经济冷却式", "风冷双冷源式",
            "不适用", "水冷双冷源式", "其他（请备注说明）",
        ))

    def test_fallback_unitary_schema_exposes_standard_mode_options(self):
        field = next(item for item in self.api.schema("unitary_ac")["fields"] if item["field_id"] == "mode")
        self.assertEqual(field["enum_name"], "EV_AC_MODE")
        self.assertEqual(tuple(field["enum_values"]), ("单冷型", "热泵型", "不适用", "其他（请备注说明）"))

    def test_fallback_multi_split_schema_exposes_standard_water_source_options(self):
        field = next(item for item in self.api.schema("multi_split_ac")["fields"] if item["field_id"] == "cooling_source")
        self.assertEqual(field["enum_name"], "EV_WATER_SOURCE")
        self.assertEqual(tuple(field["enum_values"]), ("水环式", "地埋管式", "地下水式", "不适用", "其他（请备注说明）"))

    def test_fallback_multi_split_schema_exposes_standard_category_options(self):
        field = next(item for item in self.api.schema("multi_split_ac")["fields"] if item["field_id"] == "category")
        self.assertEqual(field["enum_name"], "EV_MULTI_CATEGORY")
        self.assertEqual(tuple(field["enum_values"]), (
            "风冷式单冷型多联机", "风冷式热泵型多联机", "水冷式多联机",
            "低温多联机", "其他（请备注说明）",
        ))

    def test_all_fallback_schemas_are_json_serializable(self):
        for item in self.api.device_types():
            with self.subTest(device_type=item["code"]):
                json.dumps(self.api.schema(item["code"]), ensure_ascii=False)

    def test_schema_rejects_unknown_public_type_even_without_v4_contract(self):
        with self.assertRaises(ApiRequestError):
            self.api.schema("not-a-device")

    def test_schema_exposes_internal_profile_activation_status(self):
        profiles = self.api.schema("motor")["internal_profiles"]
        self.assertEqual([item["device_type"] for item in profiles], ["motor_lv", "motor_hv", "motor_pmsm"])
        pmsm = next(item for item in profiles if item["device_type"] == "motor_pmsm")
        self.assertEqual(pmsm["status"], "active")
        self.assertEqual(pmsm.get("unavailable_reason", ""), "")
        self.assertEqual([item["device_type"] for item in self.api.schema("鼓风机")["internal_profiles"]], ["blower"])

    def test_status_exposes_standard_gate_and_catalog_capability(self):
        status = self.api.status()
        self.assertEqual(status["public_device_type_count"], 15)
        self.assertTrue(status["elimination"]["has_industry_catalog"])
        self.assertFalse(status["elimination"]["industry_catalog_complete"])
        self.assertGreater(status["elimination"]["entry_count"], 0)
        self.assertEqual(status["elimination"]["source_entry_count"], 413)
        self.assertEqual(status["elimination"]["industry_source_item_count"], 11)
        self.assertEqual(status["elimination"]["industry_resource_rule_count"], 13)
        self.assertEqual(status["elimination"]["review_only_entry_count"], 291)
        self.assertEqual(status["elimination"]["catalog_status"], "normalized_pdf_verified_subset")
        self.assertEqual(status["elimination"]["industry_catalog_status"], "normalized_pdf_verified_subset")
        self.assertEqual(status["elimination"]["default_scope"], "高耗能落后机电设备淘汰目录第一至第四批")
        self.assertEqual(len(status["elimination"]["scope_options"]), 3)
        self.assertIn("仅产业结构调整指导目录", status["elimination"]["scope_options"])
        pmsm = next(item for item in status["standard_packs"] if item["device_type"] == "motor_pmsm")
        self.assertEqual(pmsm["status"], "active")
        transformer = next(item for item in status["standard_packs"] if item["device_type"] == "transformer")
        self.assertEqual(transformer["standard_code"], "GB 20052-2024")
        self.assertTrue(transformer["effective_date"])

    def test_api_evaluate_accepts_public_type(self):
        result = self.api.evaluate({
            "record_id": "API-1",
            "device_type": "motor",
            "values": {
                "category": "三相异步电动机（一般用途）",
                "rated_voltage": "0.4",
                "rated_power": 7.5,
                "poles": 4,
                "rated_speed": 1480,
                "efficiency": 98,
            },
        })
        self.assertEqual(result["conclusion"], "1级")
        self.assertEqual(result["public_device_type"], "motor")
        self.assertEqual(result["standard_reference"]["effective_date"], "2021-06-01")

    def test_public_motor_route_preserves_pmsm_no_data_lookup(self):
        from copy import deepcopy

        service = EvaluationService(JsonStandardRepository(ROOT))
        pack = deepcopy(service.standards.get_pack("motor_pmsm"))
        pack["status"] = "active"  # 模拟29张表已完成全部人工复核
        service._pack_cache["motor_pmsm"] = pack
        api = ApplicationApi(EvaluationFacade(service))
        result = api.evaluate({
            "record_id": "API-PMSM-NODATA",
            "device_type": "motor",
            "values": {
                "category": "异步起动永磁同步电动机",
                "rated_voltage": "0.4",
                "rated_power": 55,
                "poles": 12,
                "efficiency": 95,
            },
        })
        self.assertEqual(result["conclusion"], "不在范围")
        self.assertEqual(result["internal_device_type"], "motor_pmsm")
        self.assertEqual(result["standard_reference"]["table"], "表1")
        self.assertTrue(result["lookups"][0]["no_data"])
        standard_step = next(item for item in result["trace"] if item.get("step_type") == "标准查询结果")
        self.assertIn(result["lookups"][0]["data_id"], standard_step["data_ids"])

    def test_api_evaluate_chinese_sheet_name_attaches_quality_issues(self):
        result = self.api.evaluate({
            "record_id": "API-CN-QUALITY",
            "device_type": "电动机",
            "values": {
                "category": "三相异步电动机（一般用途）",
                "rated_voltage": "0.4",
                "rated_power": 7.5,
                "poles": 4,
                "rated_speed": 1480,
                "efficiency": 0.98,
            },
        })
        self.assertEqual(result["public_device_type"], "motor")
        self.assertTrue(any(item["code"] == "percent_range" for item in result["data_quality_issues"]))

    def test_api_evaluate_v4_accepts_sheet_and_values(self):
        result = self.api.evaluate_v4({
            "sheet": "电动机",
            "values": {
                "category": "三相异步电动机（一般用途）",
                "rated_voltage": "0.4",
                "rated_power": 7.5,
                "poles": 4,
                "rated_speed": 1480,
                "efficiency": 98,
            },
        })
        self.assertEqual(result["internal_device_type"], "motor_lv")

    def test_api_passes_explicit_as_of_into_trace(self):
        result = self.api.evaluate({
            "record_id": "API-DATE",
            "device_type": "motor",
            "as_of": "2027-01-02",
            "values": {
                "category": "三相异步电动机（一般用途）",
                "rated_voltage": "0.4",
                "rated_power": 7.5,
                "poles": 4,
                "rated_speed": 1480,
                "efficiency": 98,
            },
        })
        normalization = next(item for item in result["trace"] if item.get("step_type") == "输入规范化")
        self.assertEqual(normalization["as_of"], "2027-01-02")
        self.assertEqual(result["trace_schema_version"], "1.0")
        self.assertEqual(result["trace"][0]["step_sequence"], 1)
        self.assertTrue(result["trace"][0]["rule_id"])

    def test_api_rejects_invalid_as_of(self):
        with self.assertRaises(ApiRequestError):
            self.api.evaluate({"device_type": "motor", "as_of": "2027/01/02", "values": {}})

    def test_as_of_before_standard_effective_date_is_structured_unable(self):
        result = self.api.evaluate({
            "record_id": "DATE-BEFORE-STANDARD",
            "device_type": "motor",
            "as_of": "2020-01-01",
            "values": {
                "category": "三相异步电动机（一般用途）",
                "rated_voltage": "0.4",
                "rated_power": 7.5,
                "poles": 4,
                "rated_speed": 1480,
                "efficiency": 98,
            },
        })
        self.assertEqual(result["conclusion"], "无法判定")
        self.assertIn("早于标准实施日期", result["explanation"])
        effective_step = next(item for item in result["trace"] if item.get("step_type") == "标准生效日期")
        self.assertEqual(effective_step["effective_date"], "2021-06-01")

    def test_trace_rule_ids_cover_pmsm_and_fixed_gate_steps(self):
        trace = BatchEvaluationService._normalize_trace([
            {"step_type": "精确查表/区间查表"},
            {"step_type": "功率线性插值"},
            {"step_type": "转速线性插值"},
            {"step_type": "固定门槛"},
            {"step_type": "标准生效日期"},
        ])
        self.assertEqual(
            [item["rule_id"] for item in trace],
            ["STANDARD.LOOKUP", "STANDARD.INTERPOLATE", "STANDARD.INTERPOLATE", "STANDARD.GATE", "STANDARD.EFFECTIVE_DATE"],
        )

    def test_batch_record_can_override_global_as_of(self):
        values = {
            "category": "三相异步电动机（一般用途）",
            "rated_voltage": "0.4",
            "rated_power": 7.5,
            "poles": 4,
            "rated_speed": 1480,
            "efficiency": 98,
        }
        results = self.api.evaluate_batch({
            "as_of": "2027-01-01",
            "records": [
                {"record_id": "DATE-1", "device_type": "motor", "as_of": "2027-02-03", "values": values},
                {"record_id": "DATE-2", "device_type": "motor", "values": values},
            ],
        })
        first = next(item for item in results[0]["trace"] if item.get("step_type") == "输入规范化")
        second = next(item for item in results[1]["trace"] if item.get("step_type") == "输入规范化")
        self.assertEqual(first["as_of"], "2027-02-03")
        self.assertEqual(second["as_of"], "2027-01-01")

    def test_api_rejects_invalid_payload(self):
        with self.assertRaises(ApiRequestError):
            self.api.evaluate({"values": {}})

    def test_api_fan_public_type_conflict_is_structured_unable(self):
        result = self.api.evaluate({
            "record_id": "API-FAN-CONFLICT",
            "device_type": "centrifugal_fan",
            "values": {"category": "轴流通风机"},
        })
        self.assertEqual(result["conclusion"], "无法判定")
        self.assertIn("轴流", result["explanation"])

    def test_canonical_fallback_fields_feed_v4_quality_checks(self):
        result = self.api.evaluate({
            "record_id": "API-CANONICAL-QUALITY",
            "device_type": "motor",
            "values": {
                "category": "三相异步电动机",
                "rated_voltage_v": 400,
                "rated_power_kw": 0,
                "poles": 4,
                "rated_efficiency": 0.98,
            },
        })
        codes = {item["code"] for item in result["data_quality_issues"]}
        self.assertIn("positive", codes)
        self.assertIn("percent_range", codes)

    def test_api_evaluate_batch_preserves_order_and_ids(self):
        results = self.api.evaluate_batch({
            "records": [
                {
                    "record_id": "B-1",
                    "device_type": "motor",
                    "values": {
                        "category": "三相异步电动机（一般用途）",
                        "rated_voltage": "0.4",
                        "rated_power": 7.5,
                        "poles": 4,
                        "rated_speed": 1480,
                        "efficiency": 98,
                    },
                },
                {"record_id": "B-2", "device_type": "motor", "values": {}},
            ],
        })
        self.assertEqual([item["record_id"] for item in results], ["B-1", "B-2"])
        self.assertEqual(results[0]["conclusion"], "1级")
        self.assertEqual(results[1]["conclusion"], "无法判定")

    def test_api_evaluate_batch_rejects_malformed_record(self):
        with self.assertRaises(ApiRequestError):
            self.api.evaluate_batch({"records": [{"device_type": "motor", "values": []}]})

    def test_transformer_schema_metadata_pilot_is_v4_field_for_field_compatible(self):
        api, contract, _resource_manager = create_application_api(
            project_root=ROOT, load_template=True
        )
        self.assertIsNotNone(contract)
        expected = contract.schema_for_public_type("transformer")
        actual = api.schema("transformer")
        # The pilot must not change the public JSON schema.  The contract
        # remains the presentation source for exact validation text and enum
        # values; the metadata adapter proves identity, order and V4 mapping.
        self.assertEqual(actual["fields"], expected["fields"])
        self.assertEqual(actual["result_fields"], expected["result_fields"])
        self.assertEqual(actual["device_type"], expected["device_type"])
        self.assertEqual(actual["sheet"], expected["sheet"])

    def test_transformer_fallback_schema_remains_legacy_compatible(self):
        fields = self.api.schema("transformer")["fields"]
        self.assertEqual(
            [item["field_id"] for item in fields],
            [
                "device_name", "model", "quantity", "category", "location",
                "photo", "production_year", "capacity_kva", "core_material",
                "insulation", "connection", "no_load_loss_w", "load_loss_w",
            ],
        )
        self.assertEqual(fields[1]["display_name"], "型号")
        self.assertEqual(fields[7]["unit"], "kVA")
        by_id = {item["field_id"]: item for item in fields}
        self.assertEqual(by_id["category"]["enum_name"], "EV_TRANSFORMER_CATEGORY")
        self.assertEqual(len(by_id["category"]["enum_values"]), 36)
        self.assertEqual(by_id["core_material"]["enum_name"], "EV_CORE_MATERIAL")
        self.assertEqual(by_id["insulation"]["enum_name"], "EV_INSULATION")
        self.assertEqual(by_id["connection"]["enum_name"], "EV_CONNECTION")


if __name__ == "__main__":
    unittest.main()
