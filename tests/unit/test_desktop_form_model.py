from __future__ import annotations

import unittest
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

from equipeffi.domain.common.enums import EliminationScope
from equipeffi.domain.evaluation.device_types import PUBLIC_DEVICE_TYPES
from equipeffi.application.services.evaluation_facade import EvaluationFacade
from equipeffi.application.services.evaluation_service import EvaluationService
from equipeffi.infrastructure.excel.v4_reader import V4WorkbookReaderImpl
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository
from equipeffi.presentation.desktop.main_window import (
    capability_status_text,
    conclusion_field_label,
    download_builtin_template,
    elimination_scope_options,
    form_fields_for_public_type,
    result_summary,
    EquipmentEfficiencyWindow,
)


ROOT = Path(__file__).resolve().parents[2]


class DesktopFormModelTests(unittest.TestCase):
    def test_conclusion_field_label_matches_v4_wording(self):
        self.assertEqual(conclusion_field_label("blower"), "能效结论")
        self.assertEqual(conclusion_field_label("heat_treatment"), "评价等级")
        self.assertEqual(conclusion_field_label("motor"), "能效等级")

    def test_all_fifteen_public_types_have_renderable_fallback_fields(self):
        for public_type in PUBLIC_DEVICE_TYPES:
            with self.subTest(public_type=public_type):
                fields = form_fields_for_public_type(public_type)
                self.assertTrue(fields)
                self.assertTrue(all(field["field_id"] for field in fields))

    def test_fallback_form_preserves_units(self):
        fields = form_fields_for_public_type("transformer")
        field_units = {field["field_id"]: field["unit"] for field in fields}
        self.assertEqual(field_units["capacity_kva"], "kVA")
        self.assertEqual(field_units["no_load_loss_w"], "W")

    def test_fallback_transformer_form_exposes_standard_enum_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("transformer")}
        self.assertEqual(fields["category"]["enum_name"], "EV_TRANSFORMER_CATEGORY")
        self.assertEqual(len(fields["category"]["enum_values"]), 36)
        self.assertEqual(fields["core_material"]["enum_name"], "EV_CORE_MATERIAL")
        self.assertEqual(fields["insulation"]["enum_name"], "EV_INSULATION")
        self.assertEqual(fields["connection"]["enum_name"], "EV_CONNECTION")

    def test_fallback_compressor_form_exposes_standard_category_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("compressor")}
        self.assertEqual(fields["category"]["enum_name"], "EV_COMPRESSOR_CATEGORY")
        self.assertEqual(len(fields["category"]["enum_values"]), 7)

    def test_fallback_compressor_form_exposes_standard_cooling_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("compressor")}
        self.assertEqual(fields["cooling_method"]["enum_name"], "EV_COMPRESSOR_COOLING")
        self.assertEqual(tuple(fields["cooling_method"]["enum_values"]), ("风冷", "液冷", "不适用", "其他（请备注说明）"))

    def test_fallback_compressor_input_power_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("compressor") if item["field_id"] == "input_power_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_compressor_volume_flow_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("compressor") if item["field_id"] == "volume_flow_m3min")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "m³/min")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_compressor_discharge_pressure_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("compressor") if item["field_id"] == "discharge_pressure_mpa")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "MPa")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_compressor_specific_power_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("compressor") if item["field_id"] == "specific_power")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW/(m³/min)")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_pump_form_exposes_standard_category_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("centrifugal_pump")}
        self.assertEqual(fields["category"]["enum_name"], "EV_PUMP_CATEGORY")
        self.assertEqual(len(fields["category"]["enum_values"]), 9)

    def test_fallback_pump_form_exposes_standard_suction_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("centrifugal_pump")}
        self.assertEqual(fields["suction"]["enum_name"], "EV_SUCTION")
        self.assertEqual(tuple(fields["suction"]["enum_values"]), ("单吸", "双吸", "不适用", "其他（请备注说明）"))

    def test_fallback_submersible_form_exposes_standard_device_form_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("submersible_pump")}
        self.assertEqual(fields["subtype"]["enum_name"], "EV_SUB_FORM_ALL")
        self.assertEqual(len(fields["subtype"]["enum_values"]), 20)

    def test_fallback_submersible_form_exposes_standard_category_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("submersible_pump")}
        self.assertEqual(fields["category"]["enum_name"], "EV_SUBMERSIBLE_CATEGORY")
        self.assertEqual(tuple(fields["category"]["enum_values"]), (
            "小型潜水电泵", "大中型潜水电泵", "污水污物潜水电泵",
            "井用潜水电泵", "其他（请备注说明）", "混流潜水电泵",
        ))

    def test_fallback_boiler_form_exposes_standard_category_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("industrial_boiler")}
        self.assertEqual(fields["category"]["enum_name"], "EV_BOILER_CATEGORY")
        self.assertEqual(len(fields["category"]["enum_values"]), 9)

    def test_fallback_boiler_form_exposes_standard_fuel_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("industrial_boiler")}
        self.assertEqual(fields["fuel"]["enum_name"], "EV_FUEL")
        self.assertEqual(tuple(fields["fuel"]["enum_values"]), (
            "烟煤", "贫煤", "无烟煤", "褐煤", "天然气",
            "生物质", "燃油", "煤（室燃）", "电力", "其他（请备注说明）",
        ))

    def test_fallback_heat_treatment_form_exposes_standard_category_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("heat_treatment")}
        self.assertEqual(fields["category"]["enum_name"], "EV_HEAT_TREAT_CATEGORY")
        self.assertEqual(tuple(fields["category"]["enum_values"]), (
            "传送式连续炉", "震底式连续炉", "推送式连续炉", "滚筒式连续炉",
            "井式炉-中温炉", "箱式多用炉", "井式炉-回火炉", "井式炉-气体渗碳(氮)炉",
            "箱式炉", "台车炉", "热处理电热浴炉", "辊底炉", "罩式炉", "其他（请备注说明）",
        ))

    def test_fallback_heat_treatment_form_exposes_standard_energy_type_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("heat_treatment")}
        self.assertEqual(fields["energy_type"]["enum_name"], "EV_ENERGY_TYPE")
        self.assertEqual(tuple(fields["energy_type"]["enum_values"]), (
            "燃料油", "发生炉煤气（1250kcal/m³～1350kcal/m³）",
            "发生炉煤气（1400kcal/m³～2200kcal/m³）", "城市煤气/焦炉煤气",
            "电力", "天然气", "其他（请备注说明）",
        ))

    def test_fallback_hpwh_form_exposes_standard_heating_method_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("heat_pump_water_heater")}
        self.assertEqual(fields["heating_method"]["enum_name"], "EV_HEATING_METHOD")
        self.assertEqual(len(fields["heating_method"]["enum_values"]), 5)

    def test_fallback_hpwh_form_exposes_standard_category_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("heat_pump_water_heater")}
        self.assertEqual(fields["category"]["enum_name"], "EV_HPWH_CATEGORY")
        self.assertEqual(tuple(fields["category"]["enum_values"]), ("普通型", "低温型", "其他（请备注说明）"))

    def test_fallback_hpwh_form_exposes_standard_with_pump_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("heat_pump_water_heater")}
        self.assertEqual(fields["with_pump"]["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(fields["with_pump"]["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_heat_pump_chiller_form_exposes_standard_category_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("heat_pump_chiller")}
        self.assertEqual(fields["category"]["enum_name"], "EV_HP_CHILLER_CATEGORY")
        self.assertEqual(tuple(fields["category"]["enum_values"]), (
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

    def test_fallback_heat_pump_chiller_form_exposes_standard_product_standard_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("heat_pump_chiller")}
        self.assertEqual(fields["product_standard"]["enum_name"], "EV_HP_STD_ALL")
        self.assertEqual(tuple(fields["product_standard"]["enum_values"]), (
            "GB/T 18430.1", "GB/T 18430.2", "GB/T 25127.1", "GB/T 25127.2",
            "GB/T 18431", "GB/T 19409", "GB/T 18362", "GB/T 25861",
            "JB/T 12840", "JB/T 14642", "JB/T 14640", "JB/T 12839",
            "其他（请备注说明）",
        ))

    def test_fallback_heat_pump_chiller_form_exposes_standard_unit_type_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("heat_pump_chiller")}
        self.assertEqual(fields["unit_type"]["enum_name"], "EV_HP_UNIT_ALL")
        self.assertEqual(tuple(fields["unit_type"]["enum_values"]), (
            "舒适型", "数据中心专用型", "地板采暖型", "风机盘管型", "冷热风型-热泵型",
            "散热器型", "冷热水型-单热型", "冷热水型-热泵型", "饱和蒸汽压力0.4MPa",
            "饱和蒸汽压力0.6MPa", "饱和蒸汽压力0.8MPa", "直燃型机组", "H1a", "H2a",
            "H3a", "H4a", "H5a", "H1b", "H2b", "H3b", "H4b", "H5b",
            "循环供水式热泵高温热水机组", "外冷式", "内冷式", "内外冷串联式", "风冷式",
            "蒸发冷却式冷却塔式", "其他（请备注说明）",
        ))

    def test_fallback_heat_pump_chiller_form_exposes_standard_source_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("heat_pump_chiller")}
        self.assertEqual(fields["source"]["enum_name"], "EV_HP_SOURCE_ALL")
        self.assertEqual(tuple(fields["source"]["enum_values"]), (
            "水冷式", "风冷式", "蒸发冷却式", "空气源", "地下水式", "水环式",
            "地埋管式", "地表水式", "饱和蒸汽", "直燃", "不适用", "其他（请备注说明）",
        ))

    def test_fallback_heat_pump_chiller_form_exposes_standard_evaluation_system_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("heat_pump_chiller")}
        self.assertEqual(fields["evaluation_system"]["enum_name"], "EV_HP_EVAL_SYSTEM")
        self.assertEqual(tuple(fields["evaluation_system"]["enum_values"]), (
            "综合部分负荷/季节性能指标体系（表1）",
            "制冷性能系数COPc指标体系（表2）",
            "对应产品类别指标体系（表3～表8）",
            "其他（请备注说明）",
        ))

    def test_fallback_centrifugal_fan_form_exposes_standard_category_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("centrifugal_fan")}
        self.assertEqual(fields["category"]["enum_name"], "EV_CENTRIFUGAL_FAN_CATEGORY")
        self.assertEqual(tuple(fields["category"]["enum_values"]), (
            "离心通风机", "外转子电机直联前向多翼离心风机", "其他（请备注说明）",
        ))

    def test_fallback_axial_fan_form_exposes_standard_category_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("axial_fan")}
        self.assertEqual(fields["category"]["enum_name"], "EV_AXIAL_FAN_CATEGORY")
        self.assertEqual(tuple(fields["category"]["enum_values"]), ("轴流通风机", "其他（请备注说明）"))

    def test_fallback_blower_form_exposes_standard_category_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("blower")}
        self.assertEqual(fields["category"]["enum_name"], "EV_BLOWER_CATEGORY")
        self.assertEqual(tuple(fields["category"]["enum_values"]), (
            "单级双支撑低速离心鼓风机", "多级低速离心鼓风机",
            "单级双支撑高速离心鼓风机", "多级高速离心鼓风机",
            "其他（请备注说明）",
        ))

    def test_fallback_blower_form_exposes_inlet_pressure_numeric_constraint(self):
        field = next(field for field in form_fields_for_public_type("blower") if field["field_id"] == "inlet_absolute_pressure_kpa")
        self.assertEqual(field["display_name"], "进口绝对压力")
        self.assertEqual(field["unit"], "kPa")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_blower_form_exposes_outlet_pressure_numeric_constraint(self):
        field = next(field for field in form_fields_for_public_type("blower") if field["field_id"] == "outlet_absolute_pressure_kpa")
        self.assertEqual(field["display_name"], "出口绝对压力")
        self.assertEqual(field["unit"], "kPa")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_blower_form_exposes_inlet_temperature_numeric_constraint(self):
        field = next(field for field in form_fields_for_public_type("blower") if field["field_id"] == "inlet_temperature_k")
        self.assertEqual(field["display_name"], "进口温度")
        self.assertEqual(field["unit"], "K")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_blower_form_exposes_outlet_temperature_numeric_constraint(self):
        field = next(field for field in form_fields_for_public_type("blower") if field["field_id"] == "outlet_temperature_k")
        self.assertEqual(field["display_name"], "出口温度")
        self.assertEqual(field["unit"], "K")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_blower_form_exposes_impeller_width_numeric_constraint(self):
        field = next(field for field in form_fields_for_public_type("blower") if field["field_id"] == "impeller_width_mm")
        self.assertEqual(field["display_name"], "叶轮出口宽度b₂")
        self.assertEqual(field["unit"], "mm")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_blower_form_exposes_impeller_diameter_numeric_constraint(self):
        field = next(field for field in form_fields_for_public_type("blower") if field["field_id"] == "impeller_diameter_mm")
        self.assertEqual(field["display_name"], "叶轮出口直径D₂")
        self.assertEqual(field["unit"], "mm")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_blower_form_exposes_polytropic_efficiency_percentage_constraint(self):
        field = next(field for field in form_fields_for_public_type("blower") if field["field_id"] == "polytropic_efficiency")
        self.assertEqual(field["display_name"], "多变效率")
        self.assertEqual(field["unit"], "%")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["minimum"], 1)
        self.assertEqual(field["maximum"], 100)
        self.assertIn("百分数本值1～100", field["validation"])

    def test_fallback_fan_and_blower_form_exposes_isentropic_k_numeric_range(self):
        for public_type in ("centrifugal_fan", "axial_fan", "blower"):
            with self.subTest(public_type=public_type):
                field = next(
                    field
                    for field in form_fields_for_public_type(public_type)
                    if field["field_id"] == "isentropic_k"
                )
                self.assertEqual(field["data_type"], "数值")
                self.assertEqual(field["unit"], "-")
                self.assertEqual(field["minimum"], 1)
                self.assertEqual(field["maximum"], 2)
                self.assertIn("1～2", field["validation"])

    def test_fallback_axial_fan_form_exposes_hub_ratio_numeric_range(self):
        field = next(field for field in form_fields_for_public_type("axial_fan") if field["field_id"] == "hub_ratio")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "-")
        self.assertEqual(field["minimum"], 0)
        self.assertEqual(field["maximum"], 1)
        self.assertIn("0～1", field["validation"])

    def test_fallback_centrifugal_fan_form_keeps_hub_ratio_internal_text(self):
        field = next(field for field in form_fields_for_public_type("centrifugal_fan") if field["field_id"] == "hub_ratio")
        self.assertEqual(field["data_type"], "文本")
        self.assertIsNone(field["minimum"])
        self.assertIsNone(field["maximum"])

    def test_fallback_submersible_form_exposes_temperature_numeric_range(self):
        field = next(field for field in form_fields_for_public_type("submersible_pump") if field["field_id"] == "working_temperature_c")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "℃")
        self.assertEqual(field["minimum"], 0)
        self.assertEqual(field["maximum"], 100)
        self.assertIn("0～100", field["validation"])

    def test_fallback_blower_form_exposes_standard_multi_impeller_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("blower")}
        self.assertEqual(fields["multi_impeller"]["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(fields["multi_impeller"]["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_blower_form_exposes_standard_cantilever_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("blower")}
        self.assertEqual(fields["cantilever"]["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(fields["cantilever"]["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_blower_form_exposes_standard_three_dimensional_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("blower")}
        self.assertEqual(fields["three_dimensional"]["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(fields["three_dimensional"]["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_duct_form_exposes_standard_category_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("duct_ac")}
        self.assertEqual(fields["category"]["enum_name"], "EV_DUCT_CATEGORY")
        self.assertEqual(tuple(fields["category"]["enum_values"]), (
            "风管送风式空调（热泵）机组",
            "直接蒸发式全新风空气处理机组",
            "其他（请备注说明）",
        ))

    def test_fallback_duct_form_exposes_standard_cooling_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("duct_ac")}
        self.assertEqual(fields["cooling_source"]["enum_name"], "EV_AC_COOLING_DUCT")
        self.assertEqual(tuple(fields["cooling_source"]["enum_values"]), ("风冷式", "水冷式（水环式）", "不适用", "其他（请备注说明）"))

    def test_fallback_duct_form_exposes_standard_mode_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("duct_ac")}
        self.assertEqual(fields["mode"]["enum_name"], "EV_AC_MODE")
        self.assertEqual(tuple(fields["mode"]["enum_values"]), ("单冷型", "热泵型", "不适用", "其他（请备注说明）"))

    def test_fallback_duct_form_exposes_standard_enthalpy_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("duct_ac")}
        self.assertEqual(fields["enthalpy_difference"]["enum_name"], "EV_ENTHALPY")
        self.assertEqual(tuple(fields["enthalpy_difference"]["enum_values"]), ("小焓差", "大焓差", "不适用", "其他（请备注说明）"))

    def test_fallback_duct_indicator_value_form_uses_metadata_positive_hint(self):
        field = next(field for field in form_fields_for_public_type("duct_ac")
                     if field["field_id"] == "indicator_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "按指标")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_unitary_form_exposes_standard_category_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("unitary_ac")}
        self.assertEqual(fields["category"]["enum_name"], "EV_UNITARY_CATEGORY")
        self.assertEqual(tuple(fields["category"]["enum_values"]), (
            "普通单元式空调机",
            "计算机和数据处理机房用单元式空调机",
            "通讯基站用单元式空气调节机",
            "恒温恒湿型单元式空调机",
            "其他（请备注说明）",
        ))

    def test_fallback_unitary_form_exposes_standard_cooling_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("unitary_ac")}
        self.assertEqual(fields["cooling_source"]["enum_name"], "EV_AC_COOLING_UNITARY")
        self.assertEqual(tuple(fields["cooling_source"]["enum_values"]), (
            "风冷式", "水冷式", "乙二醇经济冷却式", "风冷双冷源式",
            "不适用", "水冷双冷源式", "其他（请备注说明）",
        ))

    def test_fallback_unitary_indicator_value_form_uses_metadata_positive_hint(self):
        field = next(field for field in form_fields_for_public_type("unitary_ac")
                     if field["field_id"] == "indicator_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "按指标")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_unitary_form_exposes_standard_mode_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("unitary_ac")}
        self.assertEqual(fields["mode"]["enum_name"], "EV_AC_MODE")
        self.assertEqual(tuple(fields["mode"]["enum_values"]), ("单冷型", "热泵型", "不适用", "其他（请备注说明）"))

    def test_fallback_multi_split_form_exposes_standard_water_source_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("multi_split_ac")}
        self.assertEqual(fields["cooling_source"]["enum_name"], "EV_WATER_SOURCE")
        self.assertEqual(tuple(fields["cooling_source"]["enum_values"]), ("水环式", "地埋管式", "地下水式", "不适用", "其他（请备注说明）"))

    def test_fallback_multi_split_form_exposes_standard_category_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("multi_split_ac")}
        self.assertEqual(fields["category"]["enum_name"], "EV_MULTI_CATEGORY")
        self.assertEqual(tuple(fields["category"]["enum_values"]), (
            "风冷式单冷型多联机", "风冷式热泵型多联机", "水冷式多联机",
            "低温多联机", "其他（请备注说明）",
        ))

    def test_fallback_multi_split_external_static_form_uses_metadata_non_negative_hint(self):
        field = next(field for field in form_fields_for_public_type("multi_split_ac")
                     if field["field_id"] == "external_static_pressure_pa")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "Pa")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值≥0", field["validation"])

    def test_fallback_multi_split_primary_metric_form_uses_metadata_positive_hint(self):
        field = next(field for field in form_fields_for_public_type("multi_split_ac")
                     if field["field_id"] == "primary_metric_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "无量纲")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_multi_split_eer_min_form_uses_metadata_positive_hint(self):
        field = next(field for field in form_fields_for_public_type("multi_split_ac")
                     if field["field_id"] == "eer_min_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "W/W")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertEqual(field["required"], "可选")
        self.assertIn("风冷式且制冷量≤14kW时必填", field["validation"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_multi_split_cop_minus12_form_uses_metadata_positive_hint(self):
        field = next(field for field in form_fields_for_public_type("multi_split_ac")
                     if field["field_id"] == "cop_minus12_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "W/W")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertEqual(field["required"], "可选")
        self.assertIn("低温多联机条件必填", field["validation"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_multi_split_cop_minus20_form_uses_metadata_positive_hint(self):
        field = next(field for field in form_fields_for_public_type("multi_split_ac")
                     if field["field_id"] == "cop_minus20_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "W/W")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertEqual(field["required"], "可选")
        self.assertIn("低温多联机条件必填", field["validation"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_chiller_primary_metric_form_uses_metadata_positive_hint(self):
        field = next(field for field in form_fields_for_public_type("heat_pump_chiller")
                     if field["field_id"] == "primary_metric_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "-")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_chiller_aux_metric1_form_uses_metadata_positive_hint(self):
        field = next(field for field in form_fields_for_public_type("heat_pump_chiller")
                     if field["field_id"] == "aux_metric1_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "-")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_chiller_aux_metric2_form_uses_metadata_positive_hint(self):
        field = next(field for field in form_fields_for_public_type("heat_pump_chiller")
                     if field["field_id"] == "aux_metric2_value")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "-")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_form_keeps_v4_common_input_prefix(self):
        fields = form_fields_for_public_type("motor")
        field_ids = [field["field_id"] for field in fields]
        self.assertEqual(field_ids[:6], ["device_name", "model", "quantity", "category", "location", "photo"])
        self.assertEqual(len(field_ids), len(set(field_ids)))
        self.assertEqual(next(field for field in fields if field["field_id"] == "quantity")["minimum"], 1)
        self.assertEqual(next(field for field in fields if field["field_id"] == "photo")["data_type"], "图片")

    def test_fallback_motor_form_exposes_complete_cooling_enum(self):
        field = next(field for field in form_fields_for_public_type("motor") if field["field_id"] == "cooling_method")
        self.assertEqual(field["enum_name"], "EV_COOLING_MOTOR_HV")
        self.assertEqual(len(field["enum_values"]), 16)
        self.assertTrue({"IC86W", "IC71W(IC3W7)", "IC416", "IC666"}.issubset(field["enum_values"]))

    def test_fallback_motor_form_exposes_standard_category_options(self):
        field = next(field for field in form_fields_for_public_type("motor") if field["field_id"] == "category")
        self.assertEqual(field["enum_name"], "EV_MOTOR_CATEGORY")
        self.assertEqual(tuple(field["enum_values"]), (
            "三相异步电动机", "电容起动异步电动机", "电容运转异步电动机", "双值电容异步电动机",
            "空调器风扇用无刷直流电动机", "空调器风扇用电容运转电动机", "高压三相笼型异步电动机",
            "异步起动三相永磁同步电动机", "变频调速永磁同步电动机", "电梯用永磁同步电动机",
            "其他（请备注说明）",
        ))

    def test_fallback_motor_form_exposes_standard_rated_voltage_options(self):
        field = next(field for field in form_fields_for_public_type("motor") if field["field_id"] == "rated_voltage_v")
        self.assertEqual(field["enum_name"], "EV_MOTOR_VOLTAGE")
        self.assertEqual(tuple(field["enum_values"]), ("0.2", "0.4", "3（3.3）", "6", "其他（请备注说明）", "10"))

    def test_fallback_motor_form_exposes_standard_poles_options(self):
        field = next(field for field in form_fields_for_public_type("motor") if field["field_id"] == "poles")
        self.assertEqual(field["enum_name"], "EV_POLES_PMSM")
        self.assertEqual(tuple(field["enum_values"]), ("2", "4", "6", "8", "12", "10", "16", "20", "24", "32", "40", "48", "其他（请备注说明）"))

    def test_fallback_motor_form_exposes_rated_speed_numeric_constraint(self):
        field = next(field for field in form_fields_for_public_type("motor") if field["field_id"] == "rated_speed_rpm")
        self.assertEqual(field["display_name"], "额定转速")
        self.assertEqual(field["unit"], "r/min")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertEqual(field["validation"], "数值>0")
        self.assertEqual(field["enum_values"], [])

    def test_fallback_fan_form_exposes_design_calculation_and_structure_inputs(self):
        field_ids = {field["field_id"] for field in form_fields_for_public_type("centrifugal_fan")}
        self.assertTrue({
            "transmission", "flow_m3h", "fan_pressure_pa", "impeller_power_kw",
            "compression_correction", "pressure_coefficient", "specific_speed",
            "unit_efficiency", "motor_efficiency", "inlet_box",
        }.issubset(field_ids))

    def test_fallback_centrifugal_fan_form_exposes_standard_transmission_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("centrifugal_fan")}
        self.assertEqual(fields["transmission"]["enum_name"], "EV_TRANSMISSION")
        self.assertEqual(tuple(fields["transmission"]["enum_values"]), (
            "A式传动（普通电动机直联）", "外转子电机直联", "其他传动", "不适用", "其他（请备注说明）",
        ))

    def test_fallback_axial_fan_form_exposes_standard_transmission_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("axial_fan")}
        self.assertEqual(fields["transmission"]["enum_name"], "EV_TRANSMISSION")
        self.assertEqual(tuple(fields["transmission"]["enum_values"]), (
            "A式传动（普通电动机直联）", "外转子电机直联", "其他传动", "不适用", "其他（请备注说明）",
        ))

    def test_fallback_centrifugal_fan_form_exposes_standard_suction_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("centrifugal_fan")}
        self.assertEqual(fields["suction"]["enum_name"], "EV_SUCTION")
        self.assertEqual(tuple(fields["suction"]["enum_values"]), ("单吸", "双吸", "不适用", "其他（请备注说明）"))

    def test_fallback_centrifugal_fan_form_exposes_standard_hvac_use_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("centrifugal_fan")}
        self.assertEqual(fields["hvac_use"]["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(fields["hvac_use"]["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_centrifugal_fan_form_exposes_standard_inlet_box_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("centrifugal_fan")}
        self.assertEqual(fields["inlet_box"]["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(fields["inlet_box"]["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_axial_fan_form_exposes_standard_inlet_box_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("axial_fan")}
        self.assertEqual(fields["inlet_box"]["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(fields["inlet_box"]["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_axial_fan_form_exposes_standard_diffuser_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("axial_fan")}
        self.assertEqual(fields["diffuser"]["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(fields["diffuser"]["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_axial_fan_form_exposes_standard_variable_blade_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("axial_fan")}
        self.assertEqual(fields["variable_blade"]["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(fields["variable_blade"]["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_axial_fan_form_exposes_standard_reversible_options(self):
        fields = {field["field_id"]: field for field in form_fields_for_public_type("axial_fan")}
        self.assertEqual(fields["reversible"]["enum_name"], "EV_YES_NO")
        self.assertEqual(tuple(fields["reversible"]["enum_values"]), ("是", "否", "不适用", "其他（请备注说明）"))

    def test_fallback_blower_form_exposes_stage_and_pressure_temperature_inputs(self):
        field_ids = {field["field_id"] for field in form_fields_for_public_type("blower")}
        self.assertTrue({
            "stages", "multi_impeller", "stage_efficiencies", "flow_m3h", "rated_power_kw", "inlet_absolute_pressure_kpa",
            "outlet_absolute_pressure_kpa", "inlet_temperature_k", "outlet_temperature_k",
            "isentropic_k", "three_dimensional", "cantilever",
        }.issubset(field_ids))

    def test_fallback_submersible_form_exposes_appendix_a_inputs(self):
        field_ids = {field["field_id"] for field in form_fields_for_public_type("submersible_pump")}
        self.assertTrue({"flow_m3h", "head_m", "rated_speed_rpm", "stages", "pump_form", "specific_speed", "motor_phase", "motor_structure"}.issubset(field_ids))

    def test_fallback_stage_count_form_exposes_positive_integer_constraint(self):
        for public_type in ("centrifugal_pump", "blower", "submersible_pump"):
            with self.subTest(public_type=public_type):
                field = next(
                    item for item in form_fields_for_public_type(public_type)
                    if item["field_id"] == "stages"
                )
                self.assertEqual(field["data_type"], "整数")
                self.assertEqual(field["unit"], "级")
                self.assertEqual(field["minimum"], 1)
                self.assertIsNone(field["maximum"])
                self.assertIn("正整数", field["validation"])

    def test_fallback_heat_treatment_temperature_form_uses_metadata_positive_hint(self):
        field = next(
            item for item in form_fields_for_public_type("heat_treatment")
            if item["field_id"] == "rated_temperature_c"
        )
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "℃")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_fan_machine_no_form_allows_decimal_positive_value(self):
        for public_type in ("centrifugal_fan", "axial_fan"):
            with self.subTest(public_type=public_type):
                field = next(
                    item for item in form_fields_for_public_type(public_type)
                    if item["field_id"] == "machine_no"
                )
                self.assertEqual(field["data_type"], "数值")
                self.assertEqual(field["unit"], "No.")
                self.assertEqual(field["minimum"], 0)
                self.assertIsNone(field["maximum"])
                self.assertIn("数值>0", field["validation"])

    def test_fallback_heat_treatment_form_exposes_specification_inputs(self):
        field_ids = {field["field_id"] for field in form_fields_for_public_type("heat_treatment")}
        self.assertTrue({"rated_power_kw", "rated_temperature_c", "equivalent_weight_t"}.issubset(field_ids))

    def test_fallback_boiler_volatile_matter_form_uses_metadata_range(self):
        field = next(item for item in form_fields_for_public_type("industrial_boiler") if item["field_id"] == "volatile_matter_percent")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "%")
        self.assertEqual(field["minimum"], 0)
        self.assertEqual(field["maximum"], 100)
        self.assertIn("0～100", field["validation"])

    def test_fallback_boiler_evaporation_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("industrial_boiler") if item["field_id"] == "evaporation_tph")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "t/h")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_boiler_thermal_power_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("industrial_boiler") if item["field_id"] == "thermal_power_mw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "MW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_boiler_lhv_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("industrial_boiler") if item["field_id"] == "lower_heating_value_kjkg")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kJ/kg")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_hpwh_heating_capacity_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("heat_pump_water_heater") if item["field_id"] == "heating_capacity_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_hpwh_rated_power_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("heat_pump_water_heater") if item["field_id"] == "rated_power_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_hpwh_cop_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("heat_pump_water_heater") if item["field_id"] == "cop")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "W/W")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_chiller_rated_power_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("heat_pump_chiller") if item["field_id"] == "rated_power_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_chiller_cooling_capacity_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("heat_pump_chiller") if item["field_id"] == "cooling_capacity_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_chiller_heating_capacity_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("heat_pump_chiller") if item["field_id"] == "heating_capacity_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_duct_cooling_capacity_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("duct_ac") if item["field_id"] == "cooling_capacity_w")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "W")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_duct_rated_power_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("duct_ac") if item["field_id"] == "rated_power_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        # This V4-only fallback column has no legacy note; the metadata lower
        # bound is still exposed while the service enforces strict > 0.

    def test_fallback_unitary_cooling_capacity_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("unitary_ac") if item["field_id"] == "cooling_capacity_w")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "W")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_unitary_rated_power_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("unitary_ac") if item["field_id"] == "rated_power_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        # This V4-only fallback column has no legacy note; the metadata lower
        # bound is still exposed while the service enforces strict > 0.

    def test_fallback_multi_split_cooling_capacity_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("multi_split_ac") if item["field_id"] == "cooling_capacity_w")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "W")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_multi_split_heating_capacity_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("multi_split_ac") if item["field_id"] == "heating_capacity_w")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "W")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        self.assertIn("低温类别条件必填", field["validation"])
        self.assertIn("数值>0", field["validation"])

    def test_fallback_multi_split_rated_power_form_uses_metadata_positive_hint(self):
        field = next(item for item in form_fields_for_public_type("multi_split_ac") if item["field_id"] == "rated_power_kw")
        self.assertEqual(field["data_type"], "数值")
        self.assertEqual(field["unit"], "kW")
        self.assertEqual(field["minimum"], 0)
        self.assertIsNone(field["maximum"])
        # This V4-only fallback column has no legacy note; the metadata lower
        # bound is still exposed while the service enforces strict > 0.

    def test_v4_contract_drives_motor_form_fields(self):
        template = ROOT / "src" / "equipeffi" / "resources" / "templates" / "设备能效分析空白模板_重构版V4_20260825.xlsx"
        contract = V4WorkbookReaderImpl().read_contract(template)
        fields = form_fields_for_public_type("motor", contract)
        field_ids = {field["field_id"] for field in fields}
        self.assertIn("rated_voltage", field_ids)
        self.assertIn("efficiency", field_ids)
        self.assertNotIn("grade1", field_ids)

    def test_transformer_form_uses_metadata_projection_without_changing_v4_fields(self):
        template = ROOT / "src" / "equipeffi" / "resources" / "templates" / "设备能效分析空白模板_重构版V4_20260825.xlsx"
        contract = V4WorkbookReaderImpl().read_contract(template)
        fields = form_fields_for_public_type("transformer", contract)
        expected = contract.fields_for_public_type("transformer", editable_only=True)
        self.assertEqual(
            [field["field_id"] for field in fields],
            [field.field_id for field in expected],
        )
        self.assertEqual(
            [(field["display_name"], field["unit"]) for field in fields],
            [(field.display_name, field.unit) for field in expected],
        )
        self.assertNotIn("production_year", {field["field_id"] for field in fields})

    def test_v4_contract_drives_all_fifteen_forms_without_locked_result_fields(self):
        template = ROOT / "src" / "equipeffi" / "resources" / "templates" / "设备能效分析空白模板_重构版V4_20260825.xlsx"
        contract = V4WorkbookReaderImpl().read_contract(template)
        for public_type in PUBLIC_DEVICE_TYPES:
            with self.subTest(public_type=public_type):
                fields = form_fields_for_public_type(public_type, contract)
                self.assertTrue(fields)
                self.assertTrue(all(field["field_id"] not in {"grade1", "grade2", "grade3", "conclusion", "auto_note"} for field in fields))
                self.assertTrue(any(field["field_id"] == "photo" for field in fields))

    def test_v4_contract_form_includes_presentation_extensions_and_conditional_limits(self):
        template = ROOT / "src" / "equipeffi" / "resources" / "templates" / "设备能效分析空白模板_重构版V4_20260825.xlsx"
        contract = V4WorkbookReaderImpl().read_contract(template)
        blower_fields = {field["field_id"]: field for field in form_fields_for_public_type("blower", contract)}
        self.assertIn("stage_efficiencies", blower_fields)
        self.assertTrue(blower_fields["stage_efficiencies"]["editable"])
        self.assertTrue(blower_fields["stage_efficiencies"].get("extension"))
        boiler_fields = {field["field_id"]: field for field in form_fields_for_public_type("industrial_boiler", contract)}
        self.assertEqual(boiler_fields["design_efficiency"]["conditional_limits"][0]["maximum"], 110)

    def test_elimination_scope_options_match_public_enum(self):
        self.assertEqual(elimination_scope_options(), tuple(item.value for item in EliminationScope))

    def test_capability_status_text_uses_core_repository_state(self):
        facade = EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT)))
        text = capability_status_text(facade)
        self.assertIn("标准包：17", text)
        self.assertIn("PMSM：active", text)
        self.assertIn("淘汰目录规则：124条", text)
        self.assertIn("产业目录：已加载（非全文）", text)

    def test_builtin_template_download_is_available_without_excel_callbacks(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "空白模板.xlsx"
            output = download_builtin_template(destination)
            self.assertEqual(output, destination)
            self.assertTrue(destination.is_file())
            validation = V4WorkbookReaderImpl().read_contract(destination)
            self.assertEqual(validation.template_id, "v4_20260825")

    def test_result_summary_keeps_quality_separate_from_detail_result(self):
        facade = EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT)))
        result = facade.evaluate_v4(
            "DESKTOP-SUMMARY",
            "电动机",
            {
                "category": "三相异步电动机（一般用途）",
                "rated_voltage": "0.4",
                "rated_power": 7.5,
                "poles": 4,
                "rated_speed": 1480,
                "efficiency": 0.98,
            },
        )
        summary = result_summary(result)
        self.assertEqual(summary["standard"], "GB 18613-2020")
        self.assertIn("1～100", summary["quality"])
        self.assertIn("额定效率", summary["missing"])
        self.assertEqual(result_summary(None)["standard"], "—")

    def test_window_converts_evaluation_exception_to_error_dialog(self):
        class Value:
            def __init__(self, value):
                self.value = value

            def get(self):
                return self.value

        facade = SimpleNamespace(evaluate=Mock(side_effect=ValueError("日期格式无效")))
        window = SimpleNamespace(
            _variables={},
            _elimination_scope=Value(EliminationScope.MOTOR_BATCHES_1_4.value),
            _as_of=Value("bad-date"),
            _public_type=lambda: "motor",
            facade=facade,
            contract=None,
        )
        with patch("equipeffi.presentation.desktop.main_window.messagebox.showerror") as showerror:
            EquipmentEfficiencyWindow._evaluate(window)
        showerror.assert_called_once_with("判定失败", "日期格式无效")


if __name__ == "__main__":
    unittest.main()
