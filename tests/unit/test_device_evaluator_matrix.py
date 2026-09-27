from __future__ import annotations

import unittest
from pathlib import Path
from decimal import Decimal
import json
from unittest.mock import patch

from equipeffi.application.services.evaluation_service import EvaluationService
from equipeffi.domain.common.enums import Conclusion
from equipeffi.domain.common.models import DeviceDraft
from equipeffi.domain.evaluation.device_specs import list_device_specs
from equipeffi.domain.evaluation.device_evaluators import BlowerEvaluator, ChemicalPumpEvaluator, HeatTreatmentEvaluator, HvacEvaluator, MotorEvaluator, PmsmEvaluator, _interval_hit
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository


ROOT = Path(__file__).resolve().parents[2]


class DeviceEvaluatorMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = EvaluationService(JsonStandardRepository(ROOT))
        cls.specs = list_device_specs()

    def evaluate(self, device_type: str, values: dict):
        # pump_chemical is in V1 target scope but remains gated from public
        # release; legacy formula regressions exercise its profile evaluator
        # directly. The public NOT_IN_RELEASE_SCOPE gate is tested separately.
        if device_type == "pump_chemical":
            return ChemicalPumpEvaluator().evaluate(values, self.service.standards.get_pack("pump_chemical"))
        return self.service.evaluate(
            DeviceDraft(record_id=f"TEST-{device_type}", device_type=device_type, raw_values=values)
        )

    def test_all_17_examples_return_structured_result(self):
        expected = {
            "transformer": Conclusion.LEVEL_1,
            "motor_lv": Conclusion.LEVEL_1,
            "motor_hv": Conclusion.LEVEL_1,
            "motor_pmsm": Conclusion.LEVEL_1,
            "compressor": Conclusion.LEVEL_1,
            "pump_water": Conclusion.LEVEL_1,
            "pump_chemical": Conclusion.LEVEL_1,
            "fan": Conclusion.LEVEL_3,
            # GB 28381-2012表1/表5：单级双支撑低速、D₂>801、b₂/D₂=0.1
            # 的评价值为75.5%，示例ηpol=80%应判为节能评价值。
            "blower": Conclusion.SAVING_VALUE,
            "submersible": Conclusion.LEVEL_1,
            "boiler": Conclusion.LEVEL_1,
            "heat_treatment": Conclusion.FIRST_CLASS,
            "heat_pump_chiller": Conclusion.LEVEL_1,
            "heat_pump_water_heater": Conclusion.LEVEL_1,
            "duct_ac": Conclusion.LEVEL_1,
            "unitary_ac": Conclusion.LEVEL_1,
            "multi_split_ac": Conclusion.LEVEL_3,
        }
        self.assertEqual(len(self.specs), 17)
        for device_type, spec in self.specs.items():
            with self.subTest(device_type=device_type):
                result = self.evaluate(device_type, spec["example"])
                self.assertEqual(result.conclusion, expected[device_type])
                self.assertTrue(result.standard_reference.get("standard_code") or result.standard_reference.get("pack_id"))
                self.assertTrue(result.trace)

    def test_successful_lookup_results_expose_stable_standard_data_ids(self):
        """每个已启用示例都能把实际使用的标准记录传给跨端消费者。"""
        all_ids = []
        for device_type, spec in self.specs.items():
            with self.subTest(device_type=device_type):
                result = self.evaluate(device_type, spec["example"])
                if result.conclusion == Conclusion.UNABLE_TO_JUDGE:
                    continue
                standard_step = next(
                    (item for item in result.trace if item.get("step_type") == "标准查询结果"),
                    None,
                )
                self.assertIsNotNone(standard_step)
                self.assertTrue(standard_step.get("data_ids"), result.trace)
                all_ids.extend(standard_step["data_ids"])
        self.assertEqual(len(all_ids), len(set(all_ids)), all_ids)

    def test_boiler_lookup_preserves_standard_pack_data_id(self):
        """锅炉表行已有稳定ID时，查表结果不得重新生成临时ID。"""
        result = self.evaluate("boiler", dict(self.specs["boiler"]["example"]))
        self.assertEqual(result.lookups[0]["data_id"], "GB24500-R000001")
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], ["GB24500-R000001"])

    def test_boiler_normal_lookup_preserves_query_context(self):
        """锅炉正常查表应保留D/Q、燃料条件和冷凝条件。"""
        result = self.evaluate("boiler", dict(self.specs["boiler"]["example"]))
        lookup = result.lookups[0]
        self.assertEqual(lookup["query_conditions"], {
            "combustion_method": "层状燃烧燃煤",
            "fuel": "烟煤",
            "fuel_class": "Ⅱ类",
            "evaporation_tph": "10",
            "thermal_power_mw": "",
            "lower_heating_value_kjkg": "19000",
            "volatile_matter_percent": "25",
            "condensing": "",
        })

    def test_boiler_normal_lookup_marks_standard_row_as_matched(self):
        """工业锅炉正常标准行查表应显式标记命中状态。"""
        result = self.evaluate("boiler", dict(self.specs["boiler"]["example"]))
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "命中")

    def test_transformer_lookup_preserves_standard_pack_data_id(self):
        """变压器精确查表优先返回标准包记录ID。"""
        result = self.evaluate("transformer", dict(self.specs["transformer"]["example"]))
        self.assertEqual(result.lookups[0]["data_id"], "GB20052-R000017")
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], ["GB20052-R000017"])

    def test_transformer_exact_lookup_preserves_matching_context(self):
        """变压器精确查表应保留分类轴、查询条件和标准条款。"""
        result = self.evaluate("transformer", dict(self.specs["transformer"]["example"]))
        lookup = result.lookups[0]
        self.assertEqual(lookup["matching"], "类别+铁芯材质+绝缘耐热等级+连接组标号+额定容量")
        self.assertEqual(lookup["query_conditions"], {
            "category": "10kV油浸式三相双绕组无励磁调压配电变压器",
            "core_material": "电工钢带",
            "insulation": "",
            "connection": "Dyn11/Yzn11",
            "capacity_kva": "100",
        })
        self.assertEqual(lookup["source_clause"], "表1")

    def test_transformer_exact_lookup_preserves_standard_source_page(self):
        """变压器精确查表应保留标准包记录的PDF来源页。"""
        result = self.evaluate("transformer", dict(self.specs["transformer"]["example"]))
        self.assertEqual(result.lookups[0]["source_page"], 7)

    def test_transformer_exact_lookup_marks_standard_row_as_matched(self):
        """变压器正常精确标准行查表应显式标记命中状态。"""
        result = self.evaluate("transformer", dict(self.specs["transformer"]["example"]))
        self.assertEqual(result.lookups[0]["match_status"], "命中")

    def test_transformer_normal_result_preserves_standard_table_clause(self):
        """变压器正常结果和轨迹都应保留命中的标准表号。"""
        result = self.evaluate("transformer", dict(self.specs["transformer"]["example"]))
        self.assertEqual(result.standard_reference["clause"], result.standard_reference["table"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["clause"], result.standard_reference["table"])

    def test_transformer_missing_no_load_loss_retains_lookup_limits_and_load_loss(self):
        """缺少空载损耗时仍保留已填负载损耗、三级阈值和查表追溯。"""
        values = dict(self.specs["transformer"]["example"])
        values.pop("no_load_loss_w", None)
        result = self.evaluate("transformer", values)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("空载损耗", result.explanation)
        self.assertEqual(result.missing_fields, ["空载损耗"])
        self.assertNotIn("空载损耗_W", result.actual_metrics)
        self.assertEqual(result.actual_metrics["负载损耗_W"], Decimal("1140"))
        self.assertEqual(result.limits, {
            "空载损耗-1级_W": Decimal("120"),
            "空载损耗-2级_W": Decimal("135"),
            "空载损耗-3级_W": Decimal("150"),
            "负载损耗-1级_W": Decimal("1140"),
            "负载损耗-2级_W": Decimal("1265"),
            "负载损耗-3级_W": Decimal("1580"),
        })
        self.assertEqual(result.comparisons, [])
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表1")
        self.assertEqual(lookup["match_status"], "命中")
        self.assertEqual(lookup["data_id"], "GB20052-R000017")
        self.assertEqual(lookup["source_page"], 7)
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], ["GB20052-R000017"])

    def test_transformer_filter_miss_keeps_category_candidates(self):
        """类别命中但分类参数组合未命中时仍保留候选行和来源。"""
        result = self.evaluate("transformer", {
            "category": "10kV油浸式三相双绕组无励磁调压配电变压器",
            "capacity_kva": 100,
            "core_material": "未知铁芯",
            "insulation": "",
            "connection": "Dyn11/Yzn11",
            "no_load_loss_w": 120,
            "load_loss_w": 1140,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("分类参数组合", result.explanation)
        self.assertEqual(result.actual_metrics["空载损耗_W"], Decimal("120"))
        self.assertEqual(result.actual_metrics["负载损耗_W"], Decimal("1140"))
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "分类条件组合未命中")
        self.assertEqual(lookup["query_conditions"]["category"], "10kV油浸式三相双绕组无励磁调压配电变压器")
        self.assertEqual(lookup["query_conditions"]["core_material"], "未知铁芯")
        self.assertEqual(lookup["candidate_count"], 62)
        self.assertEqual(lookup["candidate_rows"][0]["data_id"], "GB20052-R000001")
        self.assertEqual(lookup["candidate_rows"][-1]["data_id"], "GB20052-R000062")
        self.assertIn("电工钢带", lookup["available_core_materials"])
        self.assertIn("非晶合金", lookup["available_core_materials"])
        self.assertEqual(lookup["source_pages"], ["7"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertIn("GB20052-R000001", standard_step["data_ids"])
        self.assertIn("GB20052-R000062", standard_step["data_ids"])

    def test_chemical_pump_lookup_preserves_standard_pack_data_id(self):
        """石油化工离心泵表2规则行优先返回标准包记录ID。"""
        result = self.evaluate("pump_chemical", dict(self.specs["pump_chemical"]["example"]))
        self.assertEqual(result.lookups[0]["data_id"], "GB19762-R000012")
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], ["GB19762-R000012"])

    def test_chemical_pump_normal_lookup_preserves_standard_source_pages(self):
        """石化泵正常公式查表应保留GB 19762表2的PDF来源页。"""
        result = self.evaluate("pump_chemical", dict(self.specs["pump_chemical"]["example"]))
        self.assertEqual(result.lookups[0]["source_pages"], "8-9")

    def test_chemical_pump_normal_lookup_preserves_table_and_clause(self):
        """石化泵正常公式查表应保留表2和公式条款上下文。"""
        result = self.evaluate("pump_chemical", dict(self.specs["pump_chemical"]["example"]))
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表2")
        self.assertEqual(lookup["source_clause"], "表2/公式(4)~(7)")

    def test_chemical_pump_normal_lookup_preserves_query_context_and_match_status(self):
        """石化泵正常公式查表应保留泵型、流量、比转速和命中状态。"""
        result = self.evaluate("pump_chemical", dict(self.specs["pump_chemical"]["example"]))
        lookup = result.lookups[0]
        self.assertEqual(lookup["matching"], "泵级数类型+流量+比转速")
        conditions = lookup["query_conditions"]
        self.assertEqual(conditions["category"], "单级石油化工离心泵")
        self.assertEqual(conditions["pump_kind"], "单级")
        self.assertEqual(conditions["flow_m3h"], "100")
        self.assertEqual(conditions["head_m"], "50")
        self.assertEqual(conditions["rated_speed_rpm"], "2900")
        self.assertEqual(conditions["stages"], "1")
        self.assertEqual(conditions["suction"], "单吸")
        self.assertEqual(conditions["pump_efficiency"], "80")
        self.assertEqual(conditions["specific_speed"], str(result.calculated_metrics["比转速"]))
        self.assertEqual(lookup["match_status"], "命中")
        self.assertEqual(lookup["source_clause"], "表2/公式(4)~(7)")

    def test_chemical_pump_missing_efficiency_retains_calculation_and_lookup(self):
        """石化泵缺少泵效率时仍保留公式计算、三级阈值和查表来源。"""
        values = dict(self.specs["pump_chemical"]["example"])
        values.pop("pump_efficiency")
        result = self.evaluate("pump_chemical", values)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["泵效率"])
        self.assertEqual(result.actual_metrics, {})
        self.assertEqual(result.comparisons, [])
        self.assertEqual(result.calculated_metrics["计算流量_m3/h"], Decimal("100"))
        self.assertEqual(result.calculated_metrics["单级扬程_m"], Decimal("50"))
        self.assertEqual(result.calculated_metrics["输出功率_kW"], Decimal("13.6250"))
        self.assertEqual(
            result.calculated_metrics["基准效率_%"],
            Decimal("72.994964439329567466446659598229238364944975446517"),
        )
        self.assertEqual(
            result.calculated_metrics["效率修正值_%"],
            Decimal("1.60640509593763907460258422095108102009021526342"),
        )
        self.assertEqual(
            result.calculated_metrics["规定点效率_%"],
            Decimal("71.388559343391928391844075377278157344854760183097"),
        )
        self.assertEqual(result.limits, {
            "1级效率_%": Decimal("75.388559"),
            "2级效率_%": Decimal("72.388559"),
            "3级效率_%": Decimal("65.388559"),
        })
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表2")
        self.assertEqual(lookup["data_id"], "GB19762-R000012")
        self.assertEqual(lookup["match_status"], "命中")
        self.assertEqual(lookup["query_conditions"]["pump_efficiency"], "")
        self.assertEqual(lookup["eta0_formula"], "η0=ηb-Δη")
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], ["GB19762-R000012"])

    def test_chemical_multistage_missing_stage_retains_flow_candidates_and_context(self):
        """多级石化泵缺级数时保留已确定流量对应的表2比转速候选。"""
        result = self.evaluate("pump_chemical", {
            "category": "多级石油化工离心泵",
            "suction": "单吸",
            "flow_m3h": 100,
            "head_m": 100,
            "rated_speed_rpm": 2900,
            "pump_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["级数"])
        self.assertEqual(result.actual_metrics, {"泵效率_%": Decimal("80")})
        self.assertEqual(result.calculated_metrics, {"输出功率_kW": Decimal("27.2500")})
        self.assertEqual(result.comparisons, [])
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表2")
        self.assertEqual(lookup["matching"], "泵级数类型+流量+比转速（级数缺失）")
        self.assertEqual(lookup["match_status"], "级数未提供")
        self.assertEqual(lookup["category"], "多级")
        self.assertEqual(lookup["candidate_count"], 4)
        self.assertEqual(lookup["data_ids"], [
            "GB19762-R000019", "GB19762-R000020",
            "GB19762-R000021", "GB19762-R000022",
        ])
        self.assertEqual(lookup["query_conditions"], {
            "category": "多级石油化工离心泵",
            "pump_kind": "多级",
            "flow_m3h": "100",
            "head_m": "100",
            "rated_speed_rpm": "2900",
            "stages": "",
            "suction": "单吸",
            "pump_efficiency": "80",
            "specific_speed": "",
        })
        self.assertEqual(
            [(row["data_id"], row["ns_min"], row["ns_max"]) for row in lookup["candidate_rows"]],
            [
                ("GB19762-R000019", "20", "60"),
                ("GB19762-R000020", "60", "120"),
                ("GB19762-R000021", "120", "210"),
                ("GB19762-R000022", "210", "300"),
            ],
        )
        self.assertTrue(lookup["no_interpolation"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_chemical_multistage_missing_stage_q300_retains_closed_flow_boundary(self):
        """多级石化泵缺级数时Q=300仍保留5<Q≤300的开闭边界。"""
        result = self.evaluate("pump_chemical", {
            "category": "多级石油化工离心泵",
            "flow_m3h": 300,
            "head_m": 100,
            "rated_speed_rpm": 2900,
            "pump_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["级数"])
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "级数未提供")
        self.assertEqual(lookup["candidate_count"], 4)
        self.assertEqual(lookup["query_conditions"]["flow_m3h"], "300")
        self.assertTrue(all(
            row["flow_boundary"] == {
                "min": 5,
                "max": 300,
                "min_inclusive": False,
                "max_inclusive": True,
            }
            for row in lookup["candidate_rows"]
        ))
        self.assertEqual(lookup["data_ids"], [
            "GB19762-R000019", "GB19762-R000020",
            "GB19762-R000021", "GB19762-R000022",
        ])

    def test_water_multistage_missing_stage_retains_flow_candidate_and_context(self):
        """多级清水泵缺级数时保留表3流量候选和已填参数。"""
        result = self.evaluate("pump_water", {
            "category": "多级",
            "suction": "单吸",
            "flow_m3h": 100,
            "head_m": 100,
            "rated_speed_rpm": 2900,
            "pump_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["级数"])
        self.assertEqual(result.actual_metrics, {"泵效率_%": Decimal("80")})
        self.assertEqual(result.calculated_metrics, {"输出功率_kW": Decimal("27.2500")})
        self.assertEqual(result.limits, {})
        self.assertEqual(result.comparisons, [])
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表3")
        self.assertEqual(lookup["matching"], "泵型+流量+级数（级数缺失）")
        self.assertEqual(lookup["match_status"], "级数未提供")
        self.assertEqual(lookup["category"], "多级")
        self.assertEqual(lookup["candidate_count"], 1)
        self.assertEqual(lookup["data_ids"], ["GB19762-T3-07"])
        self.assertEqual(lookup["query_conditions"], {
            "category": "多级",
            "flow_m3h": "100",
            "head_m": "100",
            "rated_speed_rpm": "2900",
            "stages": "",
            "suction": "单吸",
            "pump_efficiency": "80",
            "specific_speed": "",
        })
        self.assertEqual(lookup["candidate_rows"], [{
            "data_id": "GB19762-T3-07",
            "type": "多级",
            "q_min": "5",
            "q_max": "100",
            "flow_boundary": {
                "min": 5,
                "max": 100,
                "min_inclusive": True,
                "max_inclusive": True,
            },
            "ci": ["139.33", "142.33", "150.33"],
        }])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_low_voltage_motor_normal_lookup_preserves_matching_context(self):
        """低压电动机表1查表应保留功率+极数轴及条款上下文。"""
        result = self.evaluate("motor_lv", dict(self.specs["motor_lv"]["example"]))
        lookup = result.lookups[0]
        self.assertEqual(lookup["matching"], "功率+极数")
        self.assertEqual(lookup["query_conditions"], {
            "power_kw": "7.5",
            "dimension": "4",
            "dimension_name": "poles",
        })
        self.assertEqual(lookup["source_clause"], "表1")

    def test_low_voltage_motor_exact_lookup_marks_standard_row_as_matched(self):
        """低压电动机正常精确功率档查表应显式标记命中状态。"""
        result = self.evaluate("motor_lv", dict(self.specs["motor_lv"]["example"]))
        self.assertEqual(result.lookups[0]["match_status"], "命中")

    def test_compressor_lookup_preserves_standard_pack_data_ids(self):
        """空压机各等级查表行优先返回标准包记录ID。"""
        result = self.evaluate("compressor", dict(self.specs["compressor"]["example"]))
        self.assertEqual(result.lookups[0]["data_ids"], [
            "GB19153-R000001", "GB19153-R000013", "GB19153-R000025",
        ])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], result.lookups[0]["data_ids"])

    def test_compressor_normal_lookup_preserves_query_context(self):
        """空压机正常查表应保留型式、功率、压力和冷却条件。"""
        result = self.evaluate("compressor", dict(self.specs["compressor"]["example"]))
        lookup = result.lookups[0]
        self.assertEqual(lookup["query_conditions"], {
            "type": "一般用喷油回转（工频）",
            "power_kw": "1.5",
            "pressure_mpa": "0.3",
            "cooling": "风冷",
        })

    def test_compressor_normal_lookup_marks_standard_rows_as_matched(self):
        """空压机正常标准行查表应显式标记命中状态。"""
        result = self.evaluate("compressor", dict(self.specs["compressor"]["example"]))
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "命中")

    def test_compressor_variable_speed_type_routes_to_its_own_standard_rows(self):
        """GB 19153-2019变转速喷油回转型式应使用独立的0.3 MPa风冷档。"""
        result = self.evaluate("compressor", {
            "category": "一般用变转速喷油回转",
            "input_power_kw": 2.2,
            "discharge_pressure_mpa": 0.3,
            "cooling_method": "风冷",
            "specific_power": 6.1,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表2")
        self.assertEqual(lookup["query_conditions"], {
            "type": "一般用变转速喷油回转",
            "power_kw": "2.2",
            "pressure_mpa": "0.3",
            "cooling": "风冷",
        })
        self.assertEqual(lookup["data_ids"], [
            "GB19153-R001009", "GB19153-R001021", "GB19153-R001033",
        ])
        self.assertEqual(lookup["source_pages"], ["8-10"])
        self.assertEqual(result.limits["1级机组比功率"], 6.1)
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_compressor_variable_speed_upper_pressure_125mpa_is_in_scope(self):
        """变转速喷油回转1.25 MPa合法上档应查表，不得按压力越界处理。"""
        result = self.evaluate("compressor", {
            "category": "一般用变转速喷油回转",
            "input_power_kw": 2.2,
            "discharge_pressure_mpa": 1.25,
            "cooling_method": "风冷",
            "specific_power": 12.8,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表2")
        self.assertEqual(lookup["query_conditions"]["pressure_mpa"], "1.25")
        self.assertEqual(lookup["data_ids"], [
            "GB19153-R001019", "GB19153-R001031", "GB19153-R001043",
        ])
        self.assertEqual(lookup["source_pages"], ["8-10"])
        self.assertEqual(result.limits["1级机组比功率"], 12.8)

    def test_compressor_reciprocating_first_row_does_not_require_cooling(self):
        """GB 19153表3往复活塞型式冷却栏为空时不应被误报为缺失。"""
        result = self.evaluate("compressor", {
            "category": "一般用往复活塞",
            "input_power_kw": 0.75,
            "discharge_pressure_mpa": 0.25,
            "specific_power": 7.2,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表3")
        self.assertEqual(lookup["matching"], "型式+功率+压力")
        self.assertEqual(lookup["query_conditions"], {
            "type": "一般用往复活塞",
            "power_kw": "0.75",
            "pressure_mpa": "0.25",
            "cooling": "",
        })
        self.assertEqual(lookup["data_ids"], [
            "GB19153-R001765", "GB19153-R001773", "GB19153-R001781",
        ])
        self.assertEqual(lookup["source_pages"], ["11-12"])
        self.assertEqual(result.limits["1级机组比功率"], 7.2)

    def test_compressor_oilless_reciprocating_first_row_uses_table4_without_cooling(self):
        """GB 19153表4全无油润滑往复活塞首档同样不要求冷却方式。"""
        result = self.evaluate("compressor", {
            "category": "全无油润滑往复活塞",
            "input_power_kw": 0.55,
            "discharge_pressure_mpa": 0.4,
            "specific_power": 10.0,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表4")
        self.assertEqual(lookup["matching"], "型式+功率+压力")
        self.assertEqual(lookup["query_conditions"]["cooling"], "")
        self.assertEqual(lookup["data_ids"], [
            "GB19153-R002197", "GB19153-R002204", "GB19153-R002211",
        ])
        self.assertEqual(lookup["source_pages"], ["12-13"])
        self.assertEqual(result.limits["1级机组比功率"], 10.0)

    def test_fan_lookup_preserves_standard_pack_data_id(self):
        """通风机精确查表优先返回标准包记录ID。"""
        result = self.evaluate("fan", dict(self.specs["fan"]["example"]))
        self.assertEqual(result.lookups[0]["data_id"], "GB19761-R000016")
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], ["GB19761-R000016"])

    def test_fan_normal_lookup_preserves_query_context(self):
        """通风机正常查表应保留型式、压力系数、次轴和机号条件。"""
        result = self.evaluate("fan", dict(self.specs["fan"]["example"]))
        lookup = result.lookups[0]
        self.assertEqual(lookup["query_conditions"], {
            "category": "离心通风机",
            "pressure_coefficient": "0.5",
            "specific_speed": "40",
            "machine_no": "10",
        })
        self.assertEqual(lookup["source_clause"], "表1～表4")

    def test_fan_normal_lookup_marks_standard_row_as_matched(self):
        """通风机正常标准行查表应显式标记命中状态。"""
        result = self.evaluate("fan", dict(self.specs["fan"]["example"]))
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "命中")

    def test_fan_unknown_category_does_not_default_to_centrifugal(self):
        """未知或兜底类别不得静默落入离心表族并输出等级。"""
        for category in ("未知类别", "其他（请备注说明）"):
            with self.subTest(category=category):
                result = self.evaluate("fan", {
                    "category": category,
                    "machine_no": 10,
                    "pressure_coefficient": 0.5,
                    "specific_speed": 40,
                    "compression_correction": 1,
                    "fan_efficiency": 80,
                })
                self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
                self.assertIn("不能默认按离心通风机判定", result.explanation)
                self.assertFalse(result.lookups)

    def test_blower_lookup_preserves_standard_pack_data_ids(self):
        """鼓风机限定值和节能评价值查表均优先返回标准包记录ID。"""
        result = self.evaluate("blower", dict(self.specs["blower"]["example"]))
        self.assertEqual([item["data_id"] for item in result.lookups], [
            "GB28381-R000008", "GB28381-R000056",
        ])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], ["GB28381-R000008", "GB28381-R000056"])

    def test_blower_normal_lookup_preserves_query_context(self):
        """鼓风机正常查表应保留类别、尺寸、b₂/D₂和级数条件。"""
        result = self.evaluate("blower", dict(self.specs["blower"]["example"]))
        lookup = result.lookups[0]
        self.assertEqual(lookup["query_conditions"], {
            "category": "单级双支撑低速离心鼓风机",
            "impeller_width_mm": "100",
            "impeller_diameter_mm": "1000",
            "b2_d2": "0.1",
            "stages": "",
        })
        self.assertEqual(lookup["source_clause"], "5.3.2")

    def test_blower_normal_result_preserves_standard_clause(self):
        """鼓风机正常结果和轨迹都应保留标准条款来源。"""
        result = self.evaluate("blower", dict(self.specs["blower"]["example"]))
        self.assertTrue(result.standard_reference["clause"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["clause"], result.standard_reference["clause"])

    def test_all_17_empty_inputs_return_unable_instead_of_raising(self):
        for device_type in self.specs:
            with self.subTest(device_type=device_type):
                self.assertEqual(self.evaluate(device_type, {}).conclusion, Conclusion.UNABLE_TO_JUDGE)

    def test_hvac_early_exit_keeps_device_specific_standard_reference(self):
        """共享HVAC标准JSON的早停分支也必须返回当前设备的标准编号。"""
        expected = {
            "heat_pump_water_heater": "GB 29541-2013",
            "duct_ac": "GB 37479-2019",
            "unitary_ac": "GB 19576-2019",
            "multi_split_ac": "GB 21454-2021",
        }
        for device_type, standard_code in expected.items():
            with self.subTest(device_type=device_type):
                result = self.evaluate(device_type, {})
                self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
                self.assertEqual(result.standard_reference["standard_code"], standard_code)

    def test_percent_efficiency_fields_reject_fractional_percent(self):
        fields = {
            "motor_lv": "rated_efficiency",
            "motor_hv": "rated_efficiency",
            "motor_pmsm": "efficiency_at_90pct_speed",
            "pump_water": "pump_efficiency",
            "pump_chemical": "pump_efficiency",
            "fan": "fan_efficiency",
            "blower": "polytropic_efficiency",
            "submersible": "pump_efficiency",
            "boiler": "design_efficiency",
        }
        for device_type, field in fields.items():
            values = dict(self.specs[device_type]["example"])
            values[field] = "0.98" if device_type in {"pump_water", "pump_chemical"} else 0.98
            with self.subTest(device_type=device_type, field=field):
                result = self.evaluate(device_type, values)
                self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
                self.assertIn("1~", result.explanation)

    def test_pmsm_speed_interpolation_propagates_no_data_endpoint(self):
        """转速插值端点为标准无数据时不得把空值当作数值计算。"""
        evaluator = PmsmEvaluator("motor_pmsm")
        table = {
            "table_no": 9,
            "table": "表9",
            "dims": ["300", "500"],
            "rows": [
                {"power_kw": 10, "efficiency": {"2": [None, 90]}, "no_data_cells": [0]},
            ],
        }
        result = evaluator._speed_lookup(table, Decimal("10"), Decimal("400"), "2")
        self.assertIsNotNone(result)
        self.assertTrue(result["no_data"])
        self.assertTrue(result["trace"][-1]["no_data"])

    def test_pmsm_table1_55kw_12pole_is_explicit_no_data(self):
        """用户确认的表1/55 kW/12极三档效率按标准无数据处理。"""
        pack_path = ROOT / "src" / "equipeffi" / "resources" / "standards" / "gb30253_2024_pdf_verified_v1.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        # Marking a private copy active keeps this test independent of the
        # production manifest while exercising the confirmed no-data cell.
        pack["status"] = "active"
        pack["unavailable_reason"] = ""
        result = PmsmEvaluator("motor_pmsm").evaluate(
            {
                "record_id": "TEST-PMSM-NODATA",
                "category": "异步起动永磁同步电动机",
                "voltage_group": "≤1140V",
                "cooling_group": "通用",
                "rated_power_kw": 55,
                "poles": 12,
                "rated_efficiency": 95,
            },
            pack,
        )
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertIn("55", result.explanation)
        self.assertIn("12", result.explanation)
        self.assertIn("无数据", result.explanation)
        self.assertEqual(result.calculated_metrics["标准无数据等级"], ["1级", "2级", "3级"])
        lookup_steps = [item for item in result.trace if item.get("step_type") == "精确查表/区间查表"]
        self.assertEqual(len(lookup_steps), 3)
        self.assertTrue(all(item.get("no_data") for item in lookup_steps))

    def test_pmsm_table1_55kw_10pole_remains_valid_adjacent_to_12pole_dash(self):
        """表1 55 kW仅12极三档为“—”，10极仍应按有效阈值判级。"""
        result = self.evaluate("motor_pmsm", {
            "category": "异步起动永磁同步电动机",
            "voltage_group": "≤1140V",
            "cooling_group": "通用",
            "rated_power_kw": 55,
            "poles": 10,
            "rated_efficiency": Decimal("95.9"),
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.actual_metrics["额定效率_%"], Decimal("95.9"))
        self.assertEqual(result.limits["1级效率_%"], Decimal("95.900000"))
        self.assertEqual(result.limits["2级效率_%"], Decimal("94.900000"))
        self.assertEqual(result.limits["3级效率_%"], Decimal("93.700000"))
        self.assertEqual(
            [item["data_id"] for item in result.lookups],
            [
                "GB30253-T01-R017-D04-L01",
                "GB30253-T01-R017-D04-L02",
                "GB30253-T01-R017-D04-L03",
            ],
        )
        self.assertTrue(all(item.get("no_data") is not True for item in result.lookups))

    def test_pmsm_voltage_just_above_1140v_does_not_default_to_low_voltage_table(self):
        """1140 V以上且未命中3/6/10 kV离散组时必须范围外，不能默认低压表。"""
        result = self.evaluate("motor_pmsm", {
            "category": "异步起动永磁同步电动机",
            "rated_voltage": Decimal("1140.1"),
            "rated_power": 5.5,
            "poles": 4,
            "rated_efficiency": 94,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertIn("额定电压", result.explanation)
        self.assertNotEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertTrue(result.lookups)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "额定电压未命中")
        self.assertEqual(lookup["query_conditions"]["rated_voltage_v"], "1140.1")
        self.assertEqual(lookup["candidate_count"], 29)
        self.assertEqual(
            sum(item["row_count"] for item in lookup["candidate_tables"]),
            len(lookup["data_ids"]),
        )
        self.assertGreater(len(lookup["data_ids"]), 0)

    def test_pmsm_voltage_1140v_closed_upper_boundary_keeps_lookup_context(self):
        """标准表1的≤1140 V闭上限应正常命中，并保留电压查询上下文。"""
        result = self.evaluate("motor_pmsm", {
            "category": "异步起动永磁同步电动机",
            "rated_voltage": Decimal("1140"),
            "rated_power": 5.5,
            "poles": 4,
            "rated_efficiency": Decimal("94.0"),
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(len(result.lookups), 3)
        for lookup, level in zip(result.lookups, ("1", "2", "3")):
            with self.subTest(level=level):
                self.assertEqual(lookup["table"], "表1")
                self.assertEqual(lookup["level"], level)
                self.assertEqual(lookup["query_conditions"]["rated_voltage_v"], "1140")
                self.assertEqual(lookup["query_conditions"]["voltage_group"], "≤1140V")
                self.assertEqual(lookup["query_conditions"]["product"], "异步起动")
                self.assertEqual(lookup["query_conditions"]["rated_power_kw"], "5.5")
                self.assertEqual(lookup["query_conditions"]["poles"], "4")
                self.assertEqual(lookup["match_status"], "命中")

    def test_pmsm_3kv_ic86w_routes_table2_and_keeps_cooling_alias_context(self):
        """3 kV与IC86W应命中表2，不得回退其他冷却组，并保留原始冷却方式。"""
        result = self.evaluate("motor_pmsm", {
            "category": "异步起动永磁同步电动机",
            "rated_voltage": Decimal("3000"),
            "cooling_method": "IC86W",
            "rated_power": 200,
            "poles": 4,
            "rated_efficiency": Decimal("94.6"),
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(len(result.lookups), 3)
        for lookup, level in zip(result.lookups, ("1", "2", "3")):
            with self.subTest(level=level):
                self.assertEqual(lookup["table"], "表2")
                self.assertEqual(lookup["level"], level)
                self.assertEqual(lookup["query_conditions"]["rated_voltage_v"], "3000")
                self.assertEqual(lookup["query_conditions"]["voltage_group"], "3kV(3.3kV)/6kV")
                self.assertEqual(lookup["query_conditions"]["cooling_method"], "IC86W")
                self.assertEqual(lookup["query_conditions"]["cooling_group"], "IC81W/IC86W/IC71W(IC3W7)")
                self.assertEqual(lookup["query_conditions"]["product"], "异步起动")
                self.assertEqual(lookup["query_conditions"]["rated_power_kw"], "200")
                self.assertEqual(lookup["query_conditions"]["poles"], "4")
                self.assertEqual(lookup["match_status"], "命中")

    def test_pmsm_6kv_ic416_routes_table3_and_preserves_source_clause(self):
        """6 kV与IC416应命中表3，并保留表号、页码和冷却分组证据。"""
        result = self.evaluate("motor_pmsm", {
            "category": "异步起动永磁同步电动机",
            "rated_voltage": Decimal("6000"),
            "cooling_method": "IC416",
            "rated_power": 200,
            "poles": 4,
            "rated_efficiency": Decimal("95.0"),
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(len(result.lookups), 3)
        for lookup, level in zip(result.lookups, ("1", "2", "3")):
            with self.subTest(level=level):
                self.assertEqual(lookup["table"], "表3")
                self.assertEqual(lookup["source_clause"], "表3")
                self.assertEqual(lookup["source_pages"], [10])
                self.assertEqual(lookup["query_conditions"]["rated_voltage_v"], "6000")
                self.assertEqual(lookup["query_conditions"]["voltage_group"], "3kV(3.3kV)/6kV")
                self.assertEqual(lookup["query_conditions"]["cooling_method"], "IC416")
                self.assertEqual(lookup["query_conditions"]["cooling_group"], "IC411/IC416")
                self.assertEqual(lookup["query_conditions"]["product"], "异步起动")
                self.assertEqual(lookup["query_conditions"]["rated_power_kw"], "200")
                self.assertEqual(lookup["query_conditions"]["poles"], "4")
                self.assertEqual(lookup["match_status"], "命中")

    def test_high_voltage_motor_dash_cell_is_retained_without_decimal_error(self):
        """高压电动机标准表“—”单元格应保留查表记录而非丢失为格式异常。"""
        result = self.evaluate("motor_hv", {
            "category": "卧式",
            "rated_voltage_v": 6000,
            "cooling_method": "IC01",
            "rated_power_kw": 6300,
            "poles": 12,
            "rated_efficiency": 95,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("—", result.explanation)
        self.assertEqual(result.actual_metrics["额定效率_%"], Decimal("95"))
        self.assertTrue(result.lookups)
        self.assertTrue(result.lookups[0]["no_data"])
        self.assertEqual(result.lookups[0]["standard_marker"], "—")
        self.assertEqual(result.lookups[0]["no_data_levels"], ["1级", "2级", "3级"])
        self.assertEqual(result.lookups[0]["data_ids"], ["GB30254-R000031"])

    def test_transformer_range_miss_retains_reported_losses(self):
        result = self.evaluate("transformer", {
            **self.specs["transformer"]["example"],
            "capacity_kva": 999999,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(result.actual_metrics["空载损耗_W"], Decimal("120"))
        self.assertEqual(result.actual_metrics["负载损耗_W"], Decimal("1140"))

    def test_transformer_forbidden_capacity_extrapolation_retains_candidate_rows(self):
        """允许插值的变压器表在容量外推时仍保留端点候选和来源证据。"""
        result = self.evaluate("transformer", {
            "category": "6kV油浸式三相双绕组无励磁调压新能源发电侧光伏用、风电用、储能用变压器（6kV~7.2kV/0.4kV~1.14kV）",
            "capacity_kva": 400,
            "core_material": "",
            "insulation": "",
            "connection": "",
            "no_load_loss_w": 300,
            "load_loss_w": 3000,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(result.actual_metrics["空载损耗_W"], Decimal("300"))
        self.assertEqual(result.actual_metrics["负载损耗_W"], Decimal("3000"))
        self.assertTrue(result.lookups)
        lookup = result.lookups[0]
        self.assertEqual(lookup["step_type"], "线性插值")
        self.assertEqual(lookup["match_status"], "容量插值端点未命中")
        self.assertEqual(lookup["query_conditions"]["capacity_kva"], "400")
        self.assertEqual(lookup["candidate_count"], 7)
        self.assertEqual(lookup["available_capacity_kva"], ["500.0", "630.0", "800.0", "1000.0", "1250.0", "1600.0", "2000.0"])
        self.assertEqual(lookup["data_ids"], [
            "GB20052-R000419", "GB20052-R000420", "GB20052-R000421",
            "GB20052-R000422", "GB20052-R000423", "GB20052-R000424",
            "GB20052-R000425",
        ])
        self.assertEqual(lookup["source_pages"], ["20"])
        self.assertIn("禁止外推", lookup["standard_rule"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_transformer_table29_capacity_interpolation_keeps_endpoints_and_factor(self):
        """GB 20052表29允许在500/630 kVA端点之间插值并保留证据。"""
        result = self.evaluate("transformer", {
            "category": "6kV油浸式三相双绕组无励磁调压新能源发电侧光伏用、风电用、储能用变压器（6kV~7.2kV/0.4kV~1.14kV）",
            "capacity_kva": 565,
            "core_material": "",
            "insulation": "",
            "connection": "",
            "no_load_loss_w": 400,
            "load_loss_w": 4000,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.actual_metrics["空载损耗_W"], Decimal("400"))
        self.assertEqual(result.actual_metrics["负载损耗_W"], Decimal("4000"))
        self.assertEqual(result.limits["空载损耗-1级_W"], Decimal("422.5"))
        self.assertEqual(result.limits["负载损耗-1级_W"], Decimal("4180"))
        self.assertTrue(any(
            item["level"] == "1级" and item["passed"]
            and item["no_load_passed"] and item["load_passed"]
            for item in result.comparisons
        ))
        lookup = result.lookups[0]
        self.assertEqual(lookup["step_type"], "线性插值")
        self.assertEqual(lookup["table"], "表29")
        self.assertEqual(lookup["endpoints"], [500.0, 630.0])
        self.assertEqual(lookup["factor"], "0.5")
        self.assertEqual(lookup["data_ids"], ["GB20052-R000419", "GB20052-R000420"])
        self.assertEqual(lookup["source_pages"], ["20"])
        self.assertIn("仅标准明确允许", lookup["standard_rule"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_transformer_interpolation_marks_standard_rows_as_matched(self):
        """变压器允许容量插值成功后应显式标记端点查表命中。"""
        result = self.evaluate("transformer", {
            "category": "6kV油浸式三相双绕组无励磁调压新能源发电侧光伏用、风电用、储能用变压器（6kV~7.2kV/0.4kV~1.14kV）",
            "capacity_kva": 565,
            "core_material": "",
            "insulation": "",
            "connection": "",
            "no_load_loss_w": 400,
            "load_loss_w": 4000,
        })
        self.assertEqual(result.lookups[0]["match_status"], "命中")

    def test_motor_range_miss_retains_reported_efficiency(self):
        result = self.evaluate("motor_lv", {
            **self.specs["motor_lv"]["example"],
            "rated_power_kw": 99999,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(result.actual_metrics["额定效率_%"], Decimal("98"))

    def test_low_voltage_motor_unsupported_category_does_not_use_three_phase_table(self):
        """GB 18613-2020表1仅为三相异步电动机，不能套用到电容类电机。"""
        result = self.evaluate("motor_lv", {
            "category": "电容起动异步电动机",
            "rated_power_kw": 7.5,
            "poles": 4,
            "rated_efficiency": 98,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(result.actual_metrics["额定效率_%"], Decimal("98"))
        self.assertFalse(result.limits)
        self.assertFalse(result.comparisons)
        self.assertTrue(result.lookups)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "设备类别未命中")
        self.assertEqual(lookup["category"], "电容起动异步电动机")
        self.assertEqual(lookup["candidate_count"], 42)
        self.assertEqual(lookup["source_page"], 4)
        self.assertIn("三相异步电动机", lookup["supported_categories"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(len(standard_step["data_ids"]), 42)

    def test_motor_power_extrapolation_retains_candidate_rows_and_source(self):
        """电动机功率超出表格时禁止外推，并保留功率档候选证据。"""
        result = self.evaluate("motor_lv", {
            **self.specs["motor_lv"]["example"],
            "rated_power_kw": 99999,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(result.actual_metrics["额定效率_%"], Decimal("98"))
        self.assertTrue(result.lookups)
        lookup = result.lookups[0]
        self.assertEqual(lookup["step_type"], "线性插值")
        self.assertEqual(lookup["match_status"], "功率档未命中")
        self.assertEqual(lookup["query_conditions"]["power_kw"], "99999")
        self.assertEqual(lookup["query_conditions"]["dimension"], "4")
        self.assertEqual(lookup["candidate_count"], 42)
        self.assertEqual(lookup["available_power_kw"][0], "0.12")
        self.assertEqual(lookup["available_power_kw"][-1], "1000.0")
        self.assertEqual(lookup["data_ids"][0], "GB18613-R000001")
        self.assertEqual(lookup["data_ids"][-1], "GB18613-R000042")
        self.assertEqual(lookup["source_pages"], ["4"])
        self.assertIn("禁止外推", lookup["standard_rule"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_motor_unresolved_table_retains_reported_efficiency(self):
        result = self.evaluate("motor_hv", {
            "rated_power_kw": 200,
            "rated_efficiency": 94,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.actual_metrics["额定效率_%"], Decimal("94"))

    def test_motor_interpolation_refuses_dash_endpoint_and_keeps_endpoints(self):
        pack = {
            "status": "active", "standard_code": "TEST", "standard_name": "测试标准",
            "tables": [{
                "title": "表1", "mode": "poles", "dims": [2],
                "rows": [
                    {"power_kw": 1, "efficiency": {"1": [90], "2": [89], "3": [88]}},
                    {"power_kw": 10, "efficiency": {"1": [None], "2": [None], "3": [None]}},
                ],
            }],
        }
        result = MotorEvaluator("motor_hv").evaluate({
            "record_id": "HV-DASH-INTERPOLATION", "rated_voltage_v": 6000,
            "cooling_method": "IC01", "rated_power_kw": 5, "poles": 2,
            "rated_efficiency": 95,
        }, pack)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertTrue(result.lookups[0]["no_data"])
        self.assertEqual(result.lookups[0]["endpoints"], [1, 10])
        self.assertIn("插值端点", result.lookups[0]["interpolation_blocked"])

    def test_motor_partial_dash_interpolation_keeps_other_grade_thresholds(self):
        """功率插值仅某一等级为“—”时，其他等级仍按标准比较。"""
        pack = {
            "status": "active", "standard_code": "TEST", "standard_name": "测试标准",
            "tables": [{
                "title": "表1", "mode": "poles", "dims": [2],
                "rows": [
                    {"power_kw": 1, "efficiency": {"1": [None], "2": [90], "3": [88]}},
                    {"power_kw": 10, "efficiency": {"1": [None], "2": [89], "3": [87]}},
                ],
            }],
        }
        result = MotorEvaluator("motor_hv").evaluate({
            "record_id": "HV-PARTIAL-DASH", "rated_voltage_v": 6000,
            "cooling_method": "IC01", "rated_power_kw": 5, "poles": 2,
            "rated_efficiency": 89.6,
        }, pack)
        self.assertEqual(result.conclusion, Conclusion.LEVEL_2)
        self.assertEqual(result.lookups[0]["no_data_levels"], ["1级"])
        self.assertEqual(result.lookups[0]["factor"], "0.4444444444444444444444444444")
        self.assertEqual(result.limits["2级效率_%"], Decimal("89.555556"))
        self.assertIsNone(next(item for item in result.comparisons if item["level"] == "1级")["passed"])

    def test_compressor_dash_combination_keeps_lookup_and_returns_unable(self):
        result = self.evaluate("compressor", {
            "category": "一般用喷油回转（工频）",
            "input_power_kw": 1.5,
            "discharge_pressure_mpa": 0.3,
            "cooling_method": "液冷",
            "specific_power": 5.8,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("—", result.explanation)
        self.assertEqual(result.actual_metrics["机组比功率_kW/(m3/min)"], Decimal("5.8"))
        self.assertTrue(result.lookups[0]["no_data"])
        self.assertEqual(result.lookups[0]["no_data_levels"], ["1级", "2级", "3级"])
        self.assertTrue(all(item.startswith("GB19153-") for item in result.lookups[0]["data_ids"]))

    def test_compressor_missing_specific_power_retains_limits_and_lookup(self):
        """缺少机组比功率时仍保留已命中的标准行和三级阈值。"""
        result = self.evaluate("compressor", {
            "category": "一般用喷油回转（工频）",
            "input_power_kw": 1.5,
            "discharge_pressure_mpa": 0.3,
            "cooling_method": "风冷",
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("机组比功率", result.explanation)
        self.assertEqual(result.missing_fields, ["机组比功率"])
        self.assertEqual(result.actual_metrics, {})
        self.assertEqual(result.limits, {
            "1级机组比功率": 5.8,
            "2级机组比功率": 6.5,
            "3级机组比功率": 7.4,
        })
        self.assertEqual(result.comparisons, [])
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表1")
        self.assertEqual(lookup["match_status"], "命中")
        self.assertEqual(lookup["query_conditions"], {
            "type": "一般用喷油回转（工频）",
            "power_kw": "1.5",
            "pressure_mpa": "0.3",
            "cooling": "风冷",
        })
        self.assertEqual(lookup["data_ids"], [
            "GB19153-R000001", "GB19153-R000013", "GB19153-R000025",
        ])
        self.assertEqual(lookup["source_pages"], ["5-7"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_compressor_range_miss_retains_reported_specific_power(self):
        result = self.evaluate("compressor", {
            "category": "一般用喷油回转（工频）",
            "input_power_kw": 1.6,
            "discharge_pressure_mpa": 0.3,
            "cooling_method": "风冷",
            "specific_power": 5.8,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(result.actual_metrics["机组比功率_kW/(m3/min)"], Decimal("5.8"))
        self.assertEqual(result.lookups[0]["match_status"], "精确档位未命中")
        self.assertEqual(result.lookups[0]["query_conditions"]["power_kw"], "1.6")
        self.assertEqual(result.lookups[0]["query_conditions"]["pressure_mpa"], "0.3")
        self.assertTrue(result.lookups[0]["candidate_count"] > 0)
        self.assertIn("1.5", result.lookups[0]["available_power_kw"])
        self.assertEqual(result.standard_reference["clause"], "表1～表4")
        query = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertNotIn("data_ids", query)

    def test_compressor_thresholds_are_closed_and_keep_all_exact_rows(self):
        """机组比功率等于阈值时应达到对应等级，并保留三档原始查表行。"""
        base = {
            "category": "一般用喷油回转（工频）",
            "input_power_kw": 1.5,
            "discharge_pressure_mpa": 0.3,
            "cooling_method": "风冷",
        }
        expected = (
            ("5.8", Conclusion.LEVEL_1),
            ("6.5", Conclusion.LEVEL_2),
            ("7.4", Conclusion.LEVEL_3),
            ("7.41", Conclusion.NOT_COMPLIANT),
        )
        expected_ids = [
            "GB19153-R000001", "GB19153-R000013", "GB19153-R000025",
        ]
        for specific_power, conclusion in expected:
            with self.subTest(specific_power=specific_power):
                result = self.evaluate("compressor", {
                    **base,
                    "specific_power": Decimal(specific_power),
                })
                self.assertEqual(result.conclusion, conclusion)
                self.assertEqual(
                    result.actual_metrics["机组比功率_kW/(m3/min)"],
                    Decimal(specific_power),
                )
                self.assertEqual(result.lookups[0]["data_ids"], expected_ids)
                self.assertEqual(result.lookups[0]["source_pages"], ["5-7"])
                self.assertEqual(
                    [item["direction"] for item in result.comparisons],
                    ["<=", "<=", "<="],
                )
                if specific_power in {"5.8", "6.5", "7.4"}:
                    matched = next(
                        item for item in result.comparisons
                        if item["threshold"] == specific_power
                    )
                    self.assertTrue(matched["passed"])
                else:
                    self.assertFalse(result.comparisons[-1]["passed"])

    def test_compressor_unmatched_discrete_inputs_refuse_extrapolation_with_evidence(self):
        """功率或压力不在离散档位时不得取最近档或外推，且保留候选证据。"""
        base = {
            "category": "一般用喷油回转（工频）",
            "input_power_kw": 1.5,
            "discharge_pressure_mpa": 0.3,
            "cooling_method": "风冷",
            "specific_power": 5.8,
        }
        for field, value in (("input_power_kw", 1.4), ("discharge_pressure_mpa", 0.2), ("discharge_pressure_mpa", 1.3)):
            with self.subTest(field=field, value=value):
                result = self.evaluate("compressor", {**base, field: value})
                self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
                self.assertEqual(
                    result.actual_metrics["机组比功率_kW/(m3/min)"],
                    Decimal("5.8"),
                )
                lookup = result.lookups[0]
                self.assertEqual(lookup["match_status"], "精确档位未命中")
                self.assertEqual(lookup["standard_rule"], "标准未授权通用插值，不取最近档位")
                self.assertGreater(lookup["candidate_count"], 0)
                self.assertEqual(lookup["source_pages"], ["5-7"])
                query_field = {
                    "input_power_kw": "power_kw",
                    "discharge_pressure_mpa": "pressure_mpa",
                }[field]
                self.assertEqual(lookup["query_conditions"][query_field], str(value))
                standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
                self.assertNotIn("data_ids", standard_step)

    def test_blower_dash_threshold_keeps_lookup_and_returns_unable(self):
        """鼓风机标准档位为“—”时保留查表记录，不改判为范围外。"""
        evaluator = BlowerEvaluator()
        result = evaluator.evaluate({
            "record_id": "BLOWER-DASH",
            "category": "单级双支撑低速鼓风机",
            "impeller_width_mm": 100,
            "impeller_diameter_mm": 1000,
            "polytropic_efficiency": 80,
        }, {
            "status": "active",
            "standard_code": "GB 28381-2012",
            "standard_name": "离心鼓风机能效限定值及节能评价值",
            "tables": [
                {
                    "type": "单级双支撑低速", "kind": "限定值", "name": "表1",
                    "d2_ranges": ["≤1000"],
                    "rows": [{"b2_d2": "0.05~0.15", "eff": [None]}],
                },
                {
                    "type": "单级双支撑低速", "kind": "节能评价值", "name": "表5",
                    "d2_ranges": ["≤1000"],
                    "rows": [{"b2_d2": "0.05~0.15", "eff": [70]}],
                },
            ],
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("无数据", result.explanation)
        self.assertTrue(any(item.get("no_data") for item in result.lookups))
        self.assertTrue(any(item.get("standard_marker") == "—" for item in result.trace))

    def test_blower_range_miss_retains_ratio_and_efficiency(self):
        result = self.evaluate("blower", {
            "category": "单级双支撑低速离心鼓风机",
            "impeller_width_mm": 30,
            "impeller_diameter_mm": 300,
            "polytropic_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(result.actual_metrics["多变效率_%"], Decimal("80"))
        self.assertEqual(result.calculated_metrics["b2/D2"], Decimal("0.1"))
        self.assertEqual(
            [item["match_status"] for item in result.lookups],
            ["D₂档位未命中", "D₂档位未命中"],
        )
        self.assertEqual(result.standard_reference["clause"], "5.3.2")
        self.assertEqual(
            result.lookups[0]["data_ids"],
            [f"GB28381-R00000{index}" for index in range(1, 9)],
        )
        query = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(len(query["data_ids"]), 16)
        self.assertIn("GB28381-R000049", query["data_ids"])

    def test_blower_ratio_gap_retains_candidate_rows_without_threshold(self):
        result = self.evaluate("blower", {
            "category": "单级双支撑低速离心鼓风机",
            "impeller_width_mm": 45.25,
            "impeller_diameter_mm": 500,
            "polytropic_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(result.calculated_metrics["b2/D2"], Decimal("0.0905"))
        self.assertEqual(
            [item["match_status"] for item in result.lookups],
            ["b₂/D₂档位未命中", "b₂/D₂档位未命中"],
        )
        self.assertEqual(result.lookups[0]["D2_range"], "401~600")
        self.assertEqual(result.lookups[0]["b2_D2_ranges"], [
            "<0.020", "0.021~0.030", "0.031~0.040", "0.041~0.050",
            "0.051~0.060", "0.061~0.080", "0.081~0.090", ">0.091",
        ])
        self.assertTrue(all(item["data_ids"] for item in result.lookups))

    def test_multistage_blower_missing_stage_retains_both_standard_table_candidates(self):
        """多级鼓风机缺级数时保留表2/表6候选行，不默认选2~3或4~6。"""
        result = self.evaluate("blower", {
            "category": "多级低速离心鼓风机",
            "impeller_width_mm": 50,
            "impeller_diameter_mm": 500,
            "polytropic_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("级数", result.explanation)
        self.assertEqual(result.actual_metrics["多变效率_%"], Decimal("80"))
        self.assertEqual(result.calculated_metrics["b2/D2"], Decimal("0.1"))
        self.assertEqual([item["table"] for item in result.lookups], ["表2", "表6"])
        self.assertEqual([item["match_status"] for item in result.lookups], ["级数未提供", "级数未提供"])
        self.assertEqual([item["candidate_count"] for item in result.lookups], [16, 16])
        self.assertEqual(result.lookups[0]["source_page"], "4-5")
        self.assertEqual(result.lookups[1]["source_page"], "7")
        self.assertEqual(result.lookups[0]["stage_ranges"], ["2~3", "4~6"])
        self.assertEqual(result.lookups[1]["stage_ranges"], ["2~3", "4~6"])
        self.assertEqual(result.lookups[0]["data_ids"][0], "GB28381-R000009")
        self.assertEqual(result.lookups[0]["data_ids"][-1], "GB28381-R000024")
        self.assertEqual(result.lookups[1]["data_ids"][0], "GB28381-R000057")
        self.assertEqual(result.lookups[1]["data_ids"][-1], "GB28381-R000072")
        self.assertTrue(all(item["no_interpolation"] for item in result.lookups))
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(len(standard_step["data_ids"]), 32)

    def test_fan_dash_combination_keeps_lookup_and_returns_unable(self):
        result = self.evaluate("fan", {
            "category": "离心通风机",
            "machine_no": 3,
            "pressure_coefficient": 0.3,
            "specific_speed": 70,
            "compression_correction": 1,
            "fan_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("—", result.explanation)
        self.assertEqual(result.actual_metrics["最高通风机效率ηr_%"], Decimal("80"))
        self.assertTrue(result.lookups)
        self.assertEqual(result.lookups[-1]["standard_marker"], "—")
        self.assertEqual(result.lookups[-1]["no_data_levels"], ["3级", "2级", "1级"])
        self.assertEqual(result.lookups[-1]["data_id"], "GB19761-R000020")

    def test_condensing_boiler_allows_103_but_non_condensing_rejects_it(self):
        common = {
            "combustion_method": "室燃锅炉",
            "fuel": "天然气",
            "thermal_power_mw": 1,
            "design_efficiency": 103,
        }
        condensing = self.evaluate("boiler", {**common, "condensing": "冷凝"})
        self.assertEqual(condensing.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(condensing.lookups[0]["data_id"], "GB24500-R000016")
        non_condensing = self.evaluate("boiler", {**common, "condensing": "非冷凝"})
        self.assertEqual(non_condensing.conclusion, Conclusion.UNABLE_TO_JUDGE)

    def test_boiler_category_infers_condensing_when_flag_is_blank(self):
        result = self.evaluate("boiler", {
            "combustion_method": "室燃锅炉",
            "fuel": "天然气",
            "category": "室燃冷凝锅炉",
            "thermal_power_mw": 1,
            "design_efficiency": 103,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)

    def test_boiler_rejects_invalid_explicit_condensing_enum(self):
        result = self.evaluate("boiler", {
            "combustion_method": "室燃锅炉",
            "fuel": "天然气",
            "condensing": "未知",
            "thermal_power_mw": 1,
            "design_efficiency": 90,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("是否冷凝", result.missing_fields)

    def test_boiler_condensing_and_fuel_class_conflict_does_not_silently_select_row(self):
        """是否冷凝与燃料类别冲突时不得静默按其中一项判级。"""
        result = self.evaluate("boiler", {
            "combustion_method": "室燃锅炉",
            "fuel": "天然气",
            "condensing": "冷凝",
            "fuel_class": "非冷凝",
            "thermal_power_mw": 1,
            "design_efficiency": 95,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("冷凝", result.explanation)
        self.assertEqual(result.actual_metrics["设计热效率_%"], Decimal("95"))
        self.assertTrue(result.lookups)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "冷凝条件冲突")
        self.assertEqual(lookup["data_ids"], ["GB24500-R000015", "GB24500-R000016"])
        self.assertEqual(lookup["query_conditions"]["condensing"], "冷凝")
        self.assertEqual(lookup["query_conditions"]["fuel_class"], "非冷凝")
        self.assertEqual(result.standard_reference["clause"], "表1～表4")

    def test_boiler_unknown_combustion_method_retains_candidate_tables(self):
        result = self.evaluate("boiler", {
            "combustion_method": "未知燃烧方式",
            "fuel": "天然气",
            "thermal_power_mw": 1,
            "design_efficiency": 90,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(result.lookups[0]["match_status"], "燃烧方式未命中")
        self.assertEqual(len(result.lookups[0]["candidate_tables"]), 4)
        self.assertEqual(result.lookups[0]["query_conditions"]["fuel"], "天然气")
        self.assertEqual(result.standard_reference["clause"], "表1～表4")

    def test_boiler_combustion_method_with_known_name_suffix_does_not_default_to_table(self):
        """分类文本带未知后缀时不能用子串命中标准表。"""
        result = self.evaluate("boiler", {
            "combustion_method": "层状燃烧燃煤（扩展）", "fuel": "烟煤", "fuel_class": "Ⅱ类",
            "evaporation_tph": 10, "lower_heating_value_kjkg": 19000,
            "volatile_matter_percent": 25, "design_efficiency": 90,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(result.standard_reference["table"], "表1～表4")
        self.assertTrue(result.lookups)
        self.assertEqual(result.lookups[0]["match_status"], "燃烧方式未命中")
        self.assertNotIn("1级热效率_%", result.limits)

    def test_boiler_missing_fuel_conditions_retains_candidate_rows(self):
        result = self.evaluate("boiler", {
            "combustion_method": "层状燃烧燃煤",
            "fuel": "烟煤",
            "fuel_class": "Ⅱ类",
            "thermal_power_mw": 1,
            "design_efficiency": 90,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.lookups[0]["match_status"], "标准行未命中")
        self.assertEqual(result.lookups[0]["data_ids"], ["GB24500-R000001"])
        self.assertEqual(result.lookups[0]["candidate_rows"][0]["q_cond"], "17700≤Q≤21000")
        self.assertEqual(result.standard_reference["clause"], "表1～表4")

    def test_boiler_full_category_and_condensing_conflict_keeps_candidates(self):
        """完整类别与独立冷凝字段冲突时不得静默套用非冷凝标准行。"""
        result = self.evaluate("boiler", {
            "category": "室燃燃烧锅炉（燃气冷凝）",
            "fuel": "天然气",
            "condensing": "非冷凝",
            "thermal_power_mw": 1,
            "design_efficiency": 95,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("类别", result.explanation)
        self.assertIn("冷凝", result.explanation)
        self.assertEqual(result.missing_fields, ["设备类别/是否冷凝"])
        self.assertEqual(result.actual_metrics["设计热效率_%"], Decimal("95"))
        self.assertTrue(result.lookups)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "类别与是否冷凝冲突")
        self.assertEqual(lookup["category_condensing"], "冷凝")
        self.assertEqual(lookup["condensing"], "非冷凝")
        self.assertEqual(lookup["data_ids"], ["GB24500-R000015", "GB24500-R000016"])
        self.assertEqual(lookup["source_page"], 6)
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_core_evaluators_apply_explicit_physical_range_guards(self):
        fan_values = dict(self.specs["fan"]["example"], isentropic_k=2.1)
        fan_result = self.evaluate("fan", fan_values)
        self.assertEqual(fan_result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertIn("等熵指数k", fan_result.explanation)

        blower_values = dict(self.specs["blower"]["example"], isentropic_k=2.1)
        blower_result = self.evaluate("blower", blower_values)
        self.assertEqual(blower_result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertIn("绝热指数k", blower_result.explanation)

        boiler_values = dict(self.specs["boiler"]["example"], volatile_matter_percent=101)
        boiler_result = self.evaluate("boiler", boiler_values)
        self.assertEqual(boiler_result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertIn("挥发分", boiler_result.explanation)

        pump_values = dict(self.specs["submersible"]["example"], working_temperature_c=101)
        pump_result = self.evaluate("submersible", pump_values)
        self.assertEqual(pump_result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertIn("工作温度", pump_result.explanation)

        ac_values = dict(self.specs["multi_split_ac"]["example"], external_static_pressure_pa=-1)
        ac_result = self.evaluate("multi_split_ac", ac_values)
        self.assertEqual(ac_result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertIn("机外静压", ac_result.explanation)

    def test_boiler_capacity_uses_correct_unit_for_thermal_power_column(self):
        high_thermal_power = self.evaluate("boiler", {
            "combustion_method": "层状燃烧燃煤", "fuel": "烟煤", "fuel_class": "Ⅱ类",
            "thermal_power_mw": 15, "lower_heating_value_kjkg": 19000,
            "volatile_matter_percent": 25, "design_efficiency": 86,
        })
        self.assertEqual(high_thermal_power.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(high_thermal_power.calculated_metrics["容量判定基准"], "Q(MW)")
        contradictory = self.evaluate("boiler", {
            "combustion_method": "层状燃烧燃煤", "fuel": "烟煤", "fuel_class": "Ⅱ类",
            "evaporation_tph": 10, "thermal_power_mw": 15,
            "lower_heating_value_kjkg": 19000, "volatile_matter_percent": 25,
            "design_efficiency": 86,
        })
        self.assertEqual(contradictory.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("容量列不一致", contradictory.explanation)
        self.assertEqual(contradictory.actual_metrics["设计热效率_%"], Decimal("86"))
        self.assertEqual(contradictory.lookups[0]["match_status"], "容量列不一致")
        self.assertEqual(contradictory.lookups[0]["data_id"], "GB24500-R000001")

    def test_boiler_missing_both_capacity_fields_reports_the_two_choice_gate(self):
        """工业锅炉必须在蒸发量与热功率中至少填写一项，双空不得进入查表。"""
        values = dict(self.specs["boiler"]["example"])
        values["evaporation_tph"] = ""
        values["thermal_power_mw"] = ""
        result = self.evaluate("boiler", values)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["蒸发量或热功率"])
        self.assertIn("缺少工业锅炉判定参数", result.explanation)
        self.assertEqual(result.lookups, [])
        self.assertEqual(result.trace[-1]["step_type"], "终止")

    def test_boiler_capacity_thresholds_are_closed_at_standard_boundary(self):
        """GB 24500表1的≤20 t/h（≤14 MW）档在边界处不得提前切换。"""

        common = {
            "combustion_method": "层状燃烧燃煤",
            "fuel": "烟煤",
            "fuel_class": "Ⅱ类",
            "lower_heating_value_kjkg": 19000,
            "volatile_matter_percent": 25,
            # 85.5高于低容量档1级85，但低于高容量档1级86，
            # 可用结论区分是否正确选择容量列。
            "design_efficiency": 85.5,
        }
        at_boundary = self.evaluate("boiler", {**common, "evaporation_tph": 20})
        above_boundary = self.evaluate("boiler", {**common, "evaporation_tph": 20.01})
        self.assertEqual(at_boundary.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(above_boundary.conclusion, Conclusion.LEVEL_2)
        self.assertEqual(at_boundary.calculated_metrics["容量判定基准"], "D(t/h)")
        self.assertEqual(above_boundary.calculated_metrics["容量判定基准"], "D(t/h)")
        self.assertEqual(at_boundary.limits["1级热效率_%"], 85)
        self.assertEqual(above_boundary.limits["1级热效率_%"], 86)
        for result in (at_boundary, above_boundary):
            lookup = result.lookups[0]
            self.assertEqual(lookup["table"], "表1")
            self.assertEqual(lookup["source_clause"], "表1～表4")
            self.assertTrue(lookup["data_id"])

    def test_fluidized_bed_boiler_lhv_17700_switches_closed_lower_boundary(self):
        """GB 24500表2的14400≤Q<17700与17700≤Q≤21000边界必须按原文切换。"""
        common = {
            "combustion_method": "流化床燃烧燃煤",
            "fuel": "烟煤",
            "volatile_matter_percent": 25,
            # 89.5高于Ⅰ类首档1级89，但低于Ⅱ类档1级90，
            # 用结论区分Q=17700处的开闭端点。
            "design_efficiency": Decimal("89.5"),
        }
        below_boundary = self.evaluate("boiler", {
            **common,
            "fuel_class": "Ⅰ类",
            "evaporation_tph": 10,
            "lower_heating_value_kjkg": Decimal("17699.999"),
        })
        at_boundary = self.evaluate("boiler", {
            **common,
            "fuel_class": "Ⅱ类",
            "evaporation_tph": 10,
            "lower_heating_value_kjkg": Decimal("17700"),
        })
        self.assertEqual(below_boundary.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(at_boundary.conclusion, Conclusion.LEVEL_2)
        self.assertEqual(below_boundary.lookups[0]["data_id"], "GB24500-R000007")
        self.assertEqual(at_boundary.lookups[0]["data_id"], "GB24500-R000008")
        self.assertEqual(below_boundary.lookups[0]["q_condition"], "14400≤Q<17700")
        self.assertEqual(at_boundary.lookups[0]["q_condition"], "17700≤Q≤21000")
        self.assertEqual(below_boundary.standard_reference["clause"], "表1～表4")
        self.assertEqual(at_boundary.standard_reference["clause"], "表1～表4")

    def test_fluidized_bed_boiler_lhv_14400_is_closed_lower_boundary(self):
        """GB 24500表2的14400≤Q<17700档在14400处闭合，低于14400应为范围外。"""
        common = {
            "combustion_method": "流化床燃烧燃煤",
            "fuel": "烟煤",
            "fuel_class": "Ⅰ类",
            "volatile_matter_percent": 25,
            "evaporation_tph": 10,
            "design_efficiency": Decimal("89"),
        }
        at_boundary = self.evaluate("boiler", {
            **common,
            "lower_heating_value_kjkg": Decimal("14400"),
        })
        below_boundary = self.evaluate("boiler", {
            **common,
            "lower_heating_value_kjkg": Decimal("14399.999"),
        })
        self.assertEqual(at_boundary.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(at_boundary.lookups[0]["data_id"], "GB24500-R000007")
        self.assertEqual(at_boundary.lookups[0]["q_condition"], "14400≤Q<17700")
        self.assertEqual(at_boundary.limits["1级热效率_%"], 89)
        self.assertEqual(below_boundary.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(below_boundary.lookups[0]["match_status"], "标准行未命中")
        self.assertEqual(below_boundary.lookups[0]["data_ids"], ["GB24500-R000007"])

    def test_fluidized_bed_boiler_lhv_21000_is_closed_upper_boundary(self):
        """GB 24500表2的17700≤Q≤21000档在21000处闭合，超过才进入Ⅲ类档。"""
        common = {
            "combustion_method": "流化床燃烧燃煤",
            "fuel": "烟煤",
            "volatile_matter_percent": 25,
            # 90.5达到Ⅱ类档1级90，但低于Ⅲ类档1级91。
            "design_efficiency": Decimal("90.5"),
            "evaporation_tph": 10,
        }
        at_boundary = self.evaluate("boiler", {
            **common,
            "fuel_class": "Ⅱ类",
            "lower_heating_value_kjkg": Decimal("21000"),
        })
        above_boundary = self.evaluate("boiler", {
            **common,
            "fuel_class": "Ⅲ类",
            "lower_heating_value_kjkg": Decimal("21000.0001"),
        })
        self.assertEqual(at_boundary.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(above_boundary.conclusion, Conclusion.LEVEL_2)
        self.assertEqual(at_boundary.lookups[0]["data_id"], "GB24500-R000008")
        self.assertEqual(above_boundary.lookups[0]["data_id"], "GB24500-R000009")
        self.assertEqual(at_boundary.lookups[0]["q_condition"], "17700≤Q≤21000")
        self.assertEqual(above_boundary.lookups[0]["q_condition"], "Q>21000")
        self.assertEqual(at_boundary.limits["1级热效率_%"], 90)
        self.assertEqual(above_boundary.limits["1级热效率_%"], 91)

    def test_fluidized_bed_boiler_anthracite_volatile_65_switches_closed_lower_boundary(self):
        """GB 24500表2无烟煤行的V<6.5与6.5≤V≤10边界必须按原文切换。"""
        common = {
            "combustion_method": "流化床燃烧燃煤",
            "fuel": "无烟煤",
            "lower_heating_value_kjkg": Decimal("21000"),
            "evaporation_tph": 10,
            # 89.5达到Ⅱ类1级89，但低于Ⅲ类1级90，
            # 用结论区分V=6.5的闭下限归属。
            "design_efficiency": Decimal("89.5"),
        }
        below_boundary = self.evaluate("boiler", {
            **common,
            "fuel_class": "Ⅱ类",
            "volatile_matter_percent": Decimal("6.4999"),
        })
        at_boundary = self.evaluate("boiler", {
            **common,
            "fuel_class": "Ⅲ类",
            "volatile_matter_percent": Decimal("6.5"),
        })
        self.assertEqual(below_boundary.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(at_boundary.conclusion, Conclusion.LEVEL_2)
        self.assertEqual(below_boundary.lookups[0]["data_id"], "GB24500-R000011")
        self.assertEqual(at_boundary.lookups[0]["data_id"], "GB24500-R000012")
        self.assertEqual(below_boundary.lookups[0]["v_condition"], "V<6.5")
        self.assertEqual(at_boundary.lookups[0]["v_condition"], "6.5≤V≤10")
        self.assertEqual(below_boundary.limits["1级热效率_%"], 89)
        self.assertEqual(at_boundary.limits["1级热效率_%"], 90)

    def test_layered_poor_coal_volatile_matter_20_is_closed_upper_boundary(self):
        """GB 24500表1贫煤行的10<V≤20条件在20处闭合。"""
        common = {
            "combustion_method": "层状燃烧燃煤",
            "fuel": "贫煤",
            "evaporation_tph": 10,
            "lower_heating_value_kjkg": 17700,
            "design_efficiency": Decimal("85.5"),
        }
        at_boundary = self.evaluate("boiler", {**common, "volatile_matter_percent": Decimal("20")})
        above_boundary = self.evaluate("boiler", {**common, "volatile_matter_percent": Decimal("20.0001")})
        self.assertEqual(at_boundary.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(at_boundary.lookups[0]["data_id"], "GB24500-R000003")
        self.assertEqual(at_boundary.lookups[0]["v_condition"], "10<V≤20")
        self.assertEqual(at_boundary.limits["1级热效率_%"], 85)
        self.assertEqual(above_boundary.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(above_boundary.lookups[0]["match_status"], "标准行未命中")
        self.assertEqual(above_boundary.lookups[0]["data_ids"], ["GB24500-R000003"])

    def test_layered_boiler_thermal_power_14_mw_is_closed_upper_boundary(self):
        """GB 24500表1的热功率≤14 MW档在14处闭合，超过14才切换高档。"""
        common = {
            "combustion_method": "层状燃烧燃煤",
            "fuel": "烟煤",
            "fuel_class": "Ⅱ类",
            "lower_heating_value_kjkg": 19000,
            "volatile_matter_percent": 25,
            # 85.5高于低容量档1级85，但低于高容量档1级86。
            "design_efficiency": Decimal("85.5"),
        }
        at_boundary = self.evaluate("boiler", {**common, "thermal_power_mw": Decimal("14")})
        above_boundary = self.evaluate("boiler", {**common, "thermal_power_mw": Decimal("14.0001")})
        self.assertEqual(at_boundary.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(above_boundary.conclusion, Conclusion.LEVEL_2)
        self.assertEqual(at_boundary.calculated_metrics["容量判定基准"], "Q(MW)")
        self.assertEqual(above_boundary.calculated_metrics["容量判定基准"], "Q(MW)")
        self.assertEqual(at_boundary.lookups[0]["capacity_value"], "14")
        self.assertEqual(above_boundary.lookups[0]["capacity_value"], "14.0001")
        self.assertEqual(at_boundary.limits["1级热效率_%"], 85)
        self.assertEqual(above_boundary.limits["1级热效率_%"], 86)
        self.assertEqual(at_boundary.lookups[0]["data_id"], "GB24500-R000001")
        self.assertEqual(above_boundary.lookups[0]["data_id"], "GB24500-R000001")

    def test_biomass_boiler_capacity_10_tph_switches_to_high_capacity_column(self):
        """GB 24500表3的≤10 t/h档在10处闭合，超过10才使用高容量指标。"""
        common = {
            "combustion_method": "生物质锅炉",
            "fuel": "生物质",
            "design_efficiency": Decimal("89.5"),
        }
        at_boundary = self.evaluate("boiler", {**common, "evaporation_tph": Decimal("10")})
        above_boundary = self.evaluate("boiler", {**common, "evaporation_tph": Decimal("10.0001")})
        self.assertEqual(at_boundary.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(above_boundary.conclusion, Conclusion.LEVEL_2)
        self.assertEqual(at_boundary.lookups[0]["data_id"], "GB24500-R000014")
        self.assertEqual(above_boundary.lookups[0]["data_id"], "GB24500-R000014")
        self.assertEqual(at_boundary.lookups[0]["capacity_value"], "10")
        self.assertEqual(above_boundary.lookups[0]["capacity_value"], "10.0001")
        self.assertEqual(at_boundary.limits["1级热效率_%"], 88)
        self.assertEqual(above_boundary.limits["1级热效率_%"], 91)
        self.assertEqual(at_boundary.limits["2级热效率_%"], 84)
        self.assertEqual(above_boundary.limits["2级热效率_%"], 88)

    def test_electric_boiler_uses_clause_5_2_fixed_limit(self):
        passing = self.evaluate("boiler", {
            "combustion_method": "电加热锅炉", "fuel": "电力",
            "thermal_power_mw": 1, "design_efficiency": 97,
        })
        self.assertEqual(passing.conclusion, Conclusion.LEVEL_3)
        self.assertEqual(passing.standard_reference["clause"], "5.2")
        self.assertEqual(str(passing.limits["能效限定值_%"]), "97")
        self.assertEqual(passing.lookups[0]["source_page"], 6)
        failing = self.evaluate("boiler", {
            "combustion_method": "电加热锅炉", "fuel": "电力",
            "thermal_power_mw": 1, "design_efficiency": 96.9,
        })
        self.assertEqual(failing.conclusion, Conclusion.NOT_COMPLIANT)

    def test_boiler_unknown_fuel_containing_electric_does_not_default_to_electric_limit(self):
        """非法燃料文本含“电”时不能绕过燃料表直接套用5.2条。"""
        result = self.evaluate("boiler", {
            "combustion_method": "层状燃烧燃煤", "fuel": "其他电源",
            "evaporation_tph": 10, "lower_heating_value_kjkg": 19000,
            "volatile_matter_percent": 25, "design_efficiency": 98,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.standard_reference["clause"], "表1～表4")
        self.assertTrue(result.lookups)
        self.assertEqual(result.lookups[0]["match_status"], "标准行未命中")
        self.assertNotIn("电加热锅炉能效限定值_%", result.calculated_metrics)

    def test_v4_electric_boiler_category_is_split_without_fuel_heat_fields(self):
        from equipeffi.application.services.evaluation_facade import EvaluationFacade

        result = EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT))).evaluate_v4(
            "V4-BOILER-E", "工业锅炉", {
                "device_name": "电锅炉", "model": "EB-1", "quantity": 1,
                "category": "电锅炉", "fuel": "电力", "thermal_power": 1,
                "design_efficiency": 97, "photo": "photo",
            },
        )
        self.assertEqual(result.conclusion, Conclusion.LEVEL_3)
        self.assertEqual(result.standard_reference["clause"], "5.2")

    def test_v4_non_condensing_boiler_category_sets_non_condensing_class(self):
        from equipeffi.application.services.evaluation_facade import EvaluationFacade

        result = EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT))).evaluate_v4(
            "V4-BOILER-NC", "工业锅炉", {
                "category": "室燃燃烧锅炉（无冷凝）", "fuel": "天然气",
                "thermal_power": 1, "design_efficiency": 95,
            },
        )
        self.assertEqual(result.conclusion, Conclusion.LEVEL_2)
        normalized = next(item for item in result.trace if item.get("step_type") == "输入规范化")
        self.assertTrue(any(change.get("target_field") == "condensing" and change.get("value") == "非冷凝" for change in normalized["changes"]))

    def test_invalid_numeric_text_is_reported_as_unable(self):
        values = dict(self.specs["pump_water"]["example"], flow_m3h="不是数字")
        result = self.evaluate("pump_water", values)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("有效数值", result.explanation)

    def test_motor_invalid_discrete_dimension_is_reported_as_unable(self):
        """极数/转速无法解析时不得误报为标准范围外。"""
        values = dict(self.specs["motor_lv"]["example"], poles="待复核")
        result = self.evaluate("motor_lv", values)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("极数不是有效数值", result.explanation)

    def test_low_voltage_motor_missing_poles_retains_candidate_rows_and_dimensions(self):
        """缺少极数时也要保留GB 18613表1的离散维度和候选行。"""
        result = self.evaluate("motor_lv", {
            "category": "三相异步电动机",
            "rated_power_kw": 7.5,
            "rated_efficiency": 98,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("缺少极数", result.explanation)
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "极数未提供")
        self.assertEqual(lookup["table"], "表1")
        self.assertEqual(lookup["matching"], "功率+极数")
        self.assertEqual(lookup["query_conditions"], {
            "power_kw": "7.5",
            "dimension": "",
            "dimension_name": "poles",
        })
        self.assertEqual(lookup["available_dimensions"], ["2", "4", "6", "8"])
        self.assertEqual(lookup["candidate_count"], 42)
        self.assertEqual(lookup["data_ids"][0], "GB18613-R000001")
        self.assertEqual(lookup["data_ids"][-1], "GB18613-R000042")
        self.assertEqual(lookup["source_page"], 4)
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_low_voltage_motor_missing_efficiency_retains_limits_and_lookup(self):
        """表1路由和标准行已确定但额定效率缺失时应保留阈值证据。"""
        result = self.evaluate("motor_lv", {
            "category": "三相异步电动机",
            "rated_power_kw": 7.5,
            "poles": 4,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("额定效率", result.explanation)
        self.assertIn("额定效率", result.missing_fields)
        self.assertEqual(result.actual_metrics, {})
        self.assertEqual(result.comparisons, [])
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "命中")
        self.assertEqual(lookup["table"][:2], "表1")
        self.assertEqual(lookup["query_conditions"], {
            "power_kw": "7.5",
            "dimension": "4",
            "dimension_name": "poles",
        })
        self.assertEqual(lookup["data_ids"], ["GB18613-R000015"])
        self.assertEqual(lookup["source_page"], 4)
        self.assertEqual(result.limits, {
            "1级效率_%": Decimal("94.0"),
            "2级效率_%": Decimal("92.6"),
            "3级效率_%": Decimal("90.4"),
        })
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])
        self.assertEqual(standard_step["output"], result.limits)

    def test_low_voltage_motor_missing_power_retains_candidate_rows_and_actual_efficiency(self):
        """表1路由和极数已确定但额定功率缺失时应保留功率轴和已填效率。"""
        result = self.evaluate("motor_lv", {
            "category": "三相异步电动机",
            "poles": 4,
            "rated_efficiency": 98,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("额定功率", result.explanation)
        self.assertIn("额定功率", result.missing_fields)
        self.assertEqual(result.actual_metrics["额定效率_%"], Decimal("98"))
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "额定功率未提供")
        self.assertEqual(lookup["table"][:2], "表1")
        self.assertEqual(lookup["matching"], "功率+极数")
        self.assertEqual(lookup["query_conditions"], {
            "power_kw": "",
            "dimension": "4",
            "dimension_name": "poles",
        })
        self.assertEqual(lookup["available_dimensions"], ["2", "4", "6", "8"])
        self.assertEqual(lookup["available_power_kw"][0], "0.12")
        self.assertEqual(lookup["available_power_kw"][-1], "1000.0")
        self.assertEqual(lookup["candidate_count"], 42)
        self.assertEqual(lookup["data_ids"][0], "GB18613-R000001")
        self.assertEqual(lookup["data_ids"][-1], "GB18613-R000042")
        self.assertEqual(lookup["source_page"], 4)
        self.assertTrue(lookup["no_interpolation"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_low_voltage_motor_lookup_preserves_standard_pack_data_id(self):
        """低压电机查表必须沿用标准包中的稳定记录ID。"""
        result = self.evaluate("motor_lv", dict(self.specs["motor_lv"]["example"]))
        self.assertEqual(result.lookups[0]["data_ids"], ["GB18613-R000015"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], ["GB18613-R000015"])
        interpolated = self.evaluate(
            "motor_lv",
            {**self.specs["motor_lv"]["example"], "rated_power_kw": 5},
        )
        self.assertEqual(
            interpolated.lookups[0]["data_ids"],
            ["GB18613-R000013", "GB18613-R000014"],
        )

    def test_low_voltage_motor_first_power_interval_interpolates_by_poles(self):
        """GB 18613-2020表1首个功率区间应按极数保留插值端点和系数。"""
        result = self.evaluate("motor_lv", {
            "category": "三相异步电动机",
            "rated_power_kw": 0.19,
            "poles": 4,
            # 0.18/0.20 kW、4极的1级阈值为78.7/79.6，
            # 中点插值为79.15；以等值输入验证边界比较方向。
            "rated_efficiency": 79.15,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.limits["1级效率_%"], Decimal("79.15"))
        lookup = result.lookups[0]
        self.assertEqual(lookup["step_type"], "线性插值")
        self.assertEqual(lookup["matching"], "功率+极数")
        self.assertEqual(lookup["query_conditions"], {
            "power_kw": "0.19",
            "dimension": "4",
            "dimension_name": "poles",
        })
        self.assertEqual(lookup["endpoints"], [0.18, 0.2])
        self.assertEqual(lookup["factor"], "0.5")
        self.assertEqual(lookup["data_ids"], ["GB18613-R000002", "GB18613-R000003"])
        self.assertEqual(lookup["source_page"], 4)
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_low_voltage_exact_lookup_preserves_standard_source_page(self):
        """低压电动机精确查表应保留GB 18613表1的PDF来源页。"""
        result = self.evaluate("motor_lv", dict(self.specs["motor_lv"]["example"]))
        self.assertEqual(result.lookups[0]["source_page"], 4)

    def test_high_voltage_exact_lookup_preserves_standard_source_pages(self):
        """高压电动机精确查表应保留命中表族的PDF页码范围。"""
        result = self.evaluate("motor_hv", dict(self.specs["motor_hv"]["example"]))
        self.assertEqual(result.lookups[0]["source_pages"], "7-9")

    def test_water_pump_normal_lookup_preserves_standard_source_pages(self):
        """清水泵正常公式查表应保留GB 19762表3的PDF页码范围。"""
        result = self.evaluate("pump_water", dict(self.specs["pump_water"]["example"]))
        self.assertEqual(result.lookups[0]["source_pages"], "9-10")

    def test_water_pump_normal_lookup_preserves_query_context_and_match_status(self):
        """清水泵正常公式查表应保留输入条件和命中状态。"""
        result = self.evaluate("pump_water", dict(self.specs["pump_water"]["example"]))
        lookup = result.lookups[0]
        self.assertEqual(lookup["matching"], "泵型+流量")
        self.assertEqual(lookup["query_conditions"], {
            "category": "单级单吸",
            "flow_m3h": "100",
            "head_m": "50",
            "rated_speed_rpm": "2900",
            "stages": "1",
            "suction": "单吸",
            "pump_efficiency": "80",
        })
        self.assertEqual(lookup["match_status"], "命中")
        self.assertEqual(lookup["source_clause"], "6.1、6.2、表3")

    def test_water_pump_missing_efficiency_retains_calculation_and_lookup(self):
        """清水泵缺少泵效率时仍保留公式计算、三级阈值和查表来源。"""
        values = dict(self.specs["pump_water"]["example"])
        values.pop("pump_efficiency")
        result = self.evaluate("pump_water", values)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["泵效率"])
        self.assertEqual(result.actual_metrics, {})
        self.assertEqual(result.comparisons, [])
        self.assertEqual(result.calculated_metrics["计算流量_m3/h"], Decimal("100"))
        self.assertEqual(result.calculated_metrics["单级扬程_m"], Decimal("50"))
        self.assertEqual(result.calculated_metrics["输出功率_kW"], Decimal("13.6250"))
        self.assertIn("比转速", result.calculated_metrics)
        self.assertEqual(Decimal(str(result.calculated_metrics["C1"])), Decimal("161.33"))
        self.assertEqual(Decimal(str(result.calculated_metrics["C2"])), Decimal("163.33"))
        self.assertEqual(Decimal(str(result.calculated_metrics["C3"])), Decimal("168.33"))
        self.assertEqual(result.limits, {
            "1级效率_%": Decimal("79.786165"),
            "2级效率_%": Decimal("77.786165"),
            "3级效率_%": Decimal("72.786165"),
        })
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表3")
        self.assertEqual(lookup["data_id"], "GB19762-T3-01")
        self.assertEqual(lookup["match_status"], "命中")
        self.assertEqual(lookup["query_conditions"]["pump_efficiency"], "")
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], ["GB19762-T3-01"])

    def test_generic_motor_result_preserves_standard_table_clause(self):
        """通用电机结果和追踪都应保留实际命中的标准表号。"""
        result = self.evaluate("motor_lv", dict(self.specs["motor_lv"]["example"]))
        self.assertEqual(result.standard_reference["clause"], "表1")
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["clause"], "表1")

    def test_submersible_grouped_product_form_matches_table_columns(self):
        values = dict(self.specs["submersible"]["example"], subtype="QXL")
        result = self.evaluate("submersible", values)
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.standard_reference["table"], "表1")

    def test_submersible_can_calculate_eta_db_from_gbt25409_appendix_a(self):
        values = {
            "category": "小型潜水电泵",
            "subtype": "QX和Q",
            "rated_power_kw": 1.5,
            "pump_efficiency": 50,
            "efficiency_tolerance": 2,
            "flow_m3h": 20,
            "pump_form": "下泵式",
            "specific_speed": 50,
            "motor_efficiency": 71,
        }
        result = self.evaluate("submersible", values)
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.calculated_metrics["泵效率ηSP_%"], Decimal("71.5"))
        self.assertEqual(result.calculated_metrics["比转速修正Δη_%"], Decimal("10"))
        self.assertEqual(result.calculated_metrics["泵效率ηB_%"], Decimal("61.5"))
        self.assertEqual(result.calculated_metrics["规定效率ηDB_%"], Decimal("42.165"))
        self.assertTrue(any(item.get("step_type") == "标准查表+公式计算" for item in result.lookups))
        self.assertTrue(result.lookups[0].get("data_id", "").startswith("GBT25409-A1-"))

    def test_submersible_uses_gbt25409_table4_for_motor_efficiency(self):
        values = {
            "category": "小型潜水电泵", "subtype": "QX和Q", "rated_power_kw": 1.5,
            "pump_efficiency": 50, "efficiency_tolerance": 2, "flow_m3h": 20,
            "pump_form": "下泵式", "specific_speed": 50,
            "motor_phase": "三相", "motor_structure": "干式", "sync_speed_rpm": 3000,
        }
        result = self.evaluate("submersible", values)
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.calculated_metrics["电动机效率ηD_%"], Decimal("74"))
        self.assertTrue(any("表4查得" in item.get("matching", "") for item in result.lookups))
        self.assertTrue(result.lookups[0].get("motor_efficiency_lookup", {}).get("data_id", "").startswith("GBT25409-T4-P"))

    def test_submersible_table4_motor_lookup_preserves_success_trace(self):
        """自动计算ηDB时，表4成功命中也必须保留状态和来源页。"""
        values = {
            "category": "小型潜水电泵", "subtype": "QX和Q", "rated_power_kw": 1.5,
            "pump_efficiency": 50, "efficiency_tolerance": 2, "flow_m3h": 20,
            "pump_form": "下泵式", "specific_speed": 50,
            "motor_phase": "三相", "motor_structure": "干式", "sync_speed_rpm": 3000,
        }
        result = self.evaluate("submersible", values)
        auto_lookup = next(item for item in result.lookups if item.get("step_type") == "标准查表+公式计算")
        motor_lookup = auto_lookup["motor_efficiency_lookup"]
        self.assertEqual(motor_lookup["match_status"], "命中")
        self.assertEqual(motor_lookup["source_pages"], "第19、24、25页（PDF第21、26、27页）")

    def test_submersible_missing_motor_efficiency_retains_a1_a2_trace_and_calculation(self):
        """附录A流量/比转速已命中、但表4条件缺失时不得丢掉前置证据。"""
        result = self.evaluate("submersible", {
            "category": "小型潜水电泵", "subtype": "QX和Q", "rated_power_kw": 1.5,
            "pump_efficiency": 50, "efficiency_tolerance": 2, "flow_m3h": 20,
            "pump_form": "下泵式", "specific_speed": 50,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("电动机相数", result.missing_fields)
        self.assertIn("电动机结构", result.missing_fields)
        self.assertIn("同步转速", result.missing_fields)
        self.assertEqual(result.calculated_metrics["泵效率ηSP_%"], Decimal("71.5"))
        self.assertEqual(result.calculated_metrics["比转速修正Δη_%"], Decimal("10"))
        self.assertEqual(result.calculated_metrics["泵效率ηB_%"], Decimal("61.5"))
        self.assertEqual(
            [item["table"] for item in result.lookups],
            ["GB/T25409-2010附录A表A1", "GB/T25409-2010附录A表A2"],
        )
        self.assertEqual(result.lookups[0]["data_id"], "GBT25409-A1-下泵式-20")
        self.assertEqual(result.lookups[1]["data_id"], "GBT25409-A2-普通型-50")
        self.assertTrue(all(item["match_status"] == "精确命中" for item in result.lookups))
        self.assertTrue(all(item["no_interpolation"] for item in result.lookups))
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(
            standard_step["data_ids"],
            ["GBT25409-A1-下泵式-20", "GBT25409-A2-普通型-50"],
        )

    def test_submersible_motor_table_dash_preserves_failed_lookup(self):
        """GB/T25409表4组合为“—”时，无法计算ηDB也要保留查表依据。"""
        result = self.evaluate("submersible", {
            "category": "小型潜水电泵", "subtype": "QX和Q", "rated_power_kw": 1.5,
            "pump_efficiency": 50, "efficiency_tolerance": 2, "flow_m3h": 20,
            "pump_form": "下泵式", "specific_speed": 50,
            "motor_phase": "单相", "motor_structure": "干式", "sync_speed_rpm": 1500,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("GB/T25409表4", result.explanation)
        self.assertTrue(result.lookups)
        lookup = next(item for item in result.lookups if item.get("table") == "GB/T25409-2010表4")
        self.assertTrue(lookup["no_data"])
        self.assertEqual(lookup["standard_marker"], "—")
        self.assertTrue(lookup["data_id"].startswith("GBT25409-T4-P1.5"))

    def test_submersible_calculation_does_not_interpolate_unsupported_flow(self):
        values = dict(self.specs["submersible"]["example"], specified_efficiency=None, flow_m3h=21,
                      pump_form="下泵式", specific_speed=50, motor_efficiency=71)
        result = self.evaluate("submersible", values)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("未授权插值", result.explanation)
        self.assertTrue(result.lookups)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "GB/T25409-2010附录A表A1")
        self.assertEqual(lookup["match_status"], "流量档未命中")
        self.assertEqual(lookup["input_flow_m3h"], "21")
        self.assertIn("20", lookup["candidate_flow_m3h"])
        self.assertTrue(lookup["source_pages"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertIn(lookup["data_id"], standard_step["data_ids"])
        self.assertEqual(result.standard_reference["clause"], "A.1")

    def test_submersible_specific_speed_lookup_miss_retains_candidates(self):
        values = dict(self.specs["submersible"]["example"], specified_efficiency=None,
                      flow_m3h=20, pump_form="下泵式", specific_speed=55, motor_efficiency=71)
        result = self.evaluate("submersible", values)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("比转速", result.explanation)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "GB/T25409-2010附录A表A2")
        self.assertEqual(lookup["match_status"], "比转速档未命中")
        self.assertEqual(lookup["input_specific_speed"], "55")
        self.assertIn("50", lookup["candidate_specific_speed"])
        self.assertTrue(lookup["source_pages"])
        self.assertEqual(result.standard_reference["clause"], "A.2")

    def test_submersible_range_miss_retains_auto_calculated_eta_db(self):
        """ηDB已由附录A算出但产品型式未命中时，仍保留计算和查表上下文。"""
        result = self.evaluate("submersible", {
            "category": "小型潜水电泵", "subtype": "未列入标准的型式",
            "rated_power_kw": 1.5, "pump_efficiency": 50,
            "efficiency_tolerance": 2, "flow_m3h": 20,
            "pump_form": "下泵式", "specific_speed": 50, "motor_efficiency": 71,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(result.actual_metrics["电泵效率_%"], Decimal("50"))
        self.assertEqual(result.calculated_metrics["规定效率ηDB_%"], Decimal("42.165"))
        self.assertTrue(result.lookups)
        lookup = next(item for item in result.lookups if item.get("match_status") == "类别/型式未命中")
        self.assertEqual(lookup["match_status"], "类别/型式未命中")
        self.assertEqual(lookup["input_subtype"], "未列入标准的型式")
        self.assertTrue(lookup["candidate_tables"])
        self.assertIn("GB32030-R000001", lookup["candidate_data_ids"])
        self.assertEqual(lookup["source_clause"], "表1～表4、表6")
        self.assertEqual(result.standard_reference["clause"], "A.1～A.2")

    def test_submersible_dash_level_is_not_treated_as_out_of_scope(self):
        # GB/T 32030表1中3~11 kW档的1、2级为“—”，仅3级限定值适用。
        # 该档仍应按ηDB−Δη比较，而不是返回“不在范围”或“无法判定”。
        result = self.evaluate("submersible", {
            "category": "小型潜水电泵",
            "subtype": "QDX和QD",
            "rated_power_kw": 5,
            "pump_efficiency": 68,
            "specified_efficiency": 70,
            "efficiency_tolerance": 2,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_3)
        self.assertNotIn("1级效率_%", result.limits)
        self.assertNotIn("2级效率_%", result.limits)
        self.assertEqual(result.limits["3级效率_%"], Decimal("68"))
        self.assertEqual(result.comparisons[0]["applicable"], False)
        self.assertEqual(result.comparisons[0]["standard_marker"], "—")
        self.assertEqual(result.comparisons[2]["passed"], True)
        self.assertIn("1", result.lookups[-1]["standard_dash_levels"])
        self.assertIn("2", result.lookups[-1]["standard_dash_levels"])
        self.assertEqual(result.lookups[-1]["data_id"], "GB32030-表1-P02-S01")
        self.assertEqual(result.lookups[-1]["power_range"], "3<P_N≤11")

    def test_submersible_table3_dash_levels_keep_level3_tolerance_rule(self):
        """表3轴流式首档1/2级为“—”时仍按ηDB−Δη判定3级。"""
        result = self.evaluate("submersible", {
            "category": "污水污物潜水电泵",
            "subtype": "轴流式",
            "rated_power_kw": 5,
            "pump_efficiency": 70,
            "specified_efficiency": 70,
            "efficiency_tolerance": 2,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_3)
        self.assertNotIn("1级效率_%", result.limits)
        self.assertNotIn("2级效率_%", result.limits)
        self.assertEqual(result.limits["3级效率_%"], Decimal("68"))
        self.assertEqual(result.comparisons[0]["applicable"], False)
        self.assertEqual(result.comparisons[1]["applicable"], False)
        self.assertEqual(result.comparisons[2]["threshold"], "68")
        self.assertTrue(result.comparisons[2]["passed"])
        lookup = result.lookups[-1]
        self.assertEqual(lookup["source_data_id"], "GB32030-R000003")
        self.assertEqual(lookup["data_id"], "GB32030-表3-P01-S02")
        self.assertEqual(lookup["power_range"], "P_N≤7.5")
        self.assertEqual(lookup["standard_dash_levels"], ["1", "2"])
        self.assertEqual(lookup["dash_semantics"], "—表示该等级不作要求，不参与比较")

    def test_submersible_power_bins_use_table_specific_open_lower_bounds(self):
        # GB 32030-2022表2首档明确为22<P_N≤100；P_N=22不应被
        # “首档下界包含”的通用简化逻辑误纳入大中型潜水电泵。
        at_boundary = self.evaluate("submersible", {
            "category": "大中型潜水电泵", "subtype": "离心式", "rated_power_kw": 22,
            "pump_efficiency": 80, "specified_efficiency": 70, "efficiency_tolerance": 2,
        })
        above_boundary = self.evaluate("submersible", {
            "category": "大中型潜水电泵", "subtype": "离心式", "rated_power_kw": 22.01,
            "pump_efficiency": 80, "specified_efficiency": 70, "efficiency_tolerance": 2,
        })
        self.assertEqual(at_boundary.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(above_boundary.standard_reference["table"], "表2")
        lookup = at_boundary.lookups[0]
        self.assertEqual(lookup["match_status"], "功率档未命中")
        self.assertEqual(lookup["input_power_kw"], "22")
        self.assertEqual(lookup["source_data_id"], "GB32030-R000002")
        self.assertTrue(lookup["candidate_rows"])
        self.assertEqual(lookup["candidate_rows"][0]["power_range"], "22<P_N≤100")
        self.assertTrue(lookup["source_pages"])
        standard_step = next(item for item in at_boundary.trace if item.get("step_type") == "标准查询结果")
        self.assertIn(lookup["data_id"], standard_step["data_ids"])

    def test_submersible_success_lookup_contains_source_context(self):
        result = self.evaluate("submersible", dict(self.specs["submersible"]["example"]))
        lookup = result.lookups[-1]
        self.assertEqual(lookup["source_data_id"], "GB32030-R000001")
        self.assertEqual(lookup["source_pages"], "4")
        self.assertEqual(lookup["source_clause"], "表1")
        self.assertEqual(lookup["input_power_kw"], "1.5")

    def test_submersible_normal_lookup_preserves_query_context(self):
        """潜水电泵正常查表应保留型式、功率、规定效率和容差条件。"""
        result = self.evaluate("submersible", dict(self.specs["submersible"]["example"]))
        lookup = result.lookups[-1]
        self.assertEqual(lookup["query_conditions"], {
            "category": "小型潜水电泵",
            "subtype": "QDX和QD",
            "rated_power_kw": "1.5",
            "specified_efficiency": "55",
            "efficiency_tolerance": "2",
        })

    def test_submersible_normal_lookup_marks_power_row_as_matched(self):
        """潜水电泵正常功率档查表应显式标记命中状态。"""
        result = self.evaluate("submersible", dict(self.specs["submersible"]["example"]))
        lookup = result.lookups[-1]
        self.assertEqual(lookup["match_status"], "命中")

    def test_submersible_normal_result_preserves_standard_clause(self):
        """潜水电泵正常结果和轨迹都应保留标准条款来源。"""
        result = self.evaluate("submersible", dict(self.specs["submersible"]["example"]))
        self.assertTrue(result.standard_reference["clause"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["clause"], result.standard_reference["clause"])

    def test_motor_exact_boundary_interpolation_and_no_extrapolation(self):
        base = dict(self.specs["motor_lv"]["example"])
        result = self.evaluate("motor_lv", base)
        boundary = self.evaluate("motor_lv", {**base, "rated_efficiency": result.limits["1级效率_%"]})
        self.assertEqual(boundary.conclusion, Conclusion.LEVEL_1)

        interpolated = self.evaluate("motor_lv", {**base, "rated_power_kw": 5, "rated_efficiency": 98})
        self.assertEqual(interpolated.lookups[0]["step_type"], "线性插值")

        outside = self.evaluate("motor_lv", {**base, "rated_power_kw": 0.01})
        self.assertEqual(outside.conclusion, Conclusion.OUT_OF_SCOPE)

    def test_standard_intervals_preserve_open_and_closed_boundaries(self):
        self.assertTrue(_interval_hit("0.25", "0.25≤ψ<0.95"))
        self.assertFalse(_interval_hit("0.95", "0.25≤ψ<0.95"))
        self.assertTrue(_interval_hit("0.95", "0.25≤ψ≤0.95"))
        self.assertFalse(_interval_hit("3.15", "3.15<No.≤10"))
        self.assertTrue(_interval_hit("10", "3.15<No.≤10"))
        self.assertTrue(_interval_hit("17700", "17700≤Q≤21000"))
        self.assertTrue(_interval_hit("21000", "17700≤Q≤21000"))
        # 热处理标准中的“>700~1000℃”下限是开区间，700℃不得误选该档。
        self.assertFalse(_interval_hit("700", ">700~1000℃"))
        self.assertTrue(_interval_hit("700.01", ">700~1000℃"))
        self.assertTrue(_interval_hit("1000", ">700~1000℃"))
        self.assertFalse(_interval_hit("1000.01", ">700~1000℃"))

    def test_below_minimum_level_is_not_compliant(self):
        values = dict(self.specs["motor_lv"]["example"], rated_efficiency=1)
        self.assertEqual(self.evaluate("motor_lv", values).conclusion, Conclusion.NOT_COMPLIANT)

    def test_calculated_and_lookup_outputs_are_retained(self):
        water = self.evaluate("pump_water", self.specs["pump_water"]["example"])
        self.assertIn("输出功率_kW", water.calculated_metrics)
        self.assertIn("比转速", water.calculated_metrics)
        self.assertTrue(water.lookups)

        fan = self.evaluate("fan", self.specs["fan"]["example"])
        fan_lookup = next(item for item in fan.trace if item.get("step_type") == "精确查表")
        self.assertEqual(fan_lookup["data_id"], "GB19761-R000016")
        self.assertTrue(fan_lookup["machine_interval"])

        transformer = self.evaluate("transformer", self.specs["transformer"]["example"])
        self.assertIn("空载损耗-1级_W", transformer.limits)
        self.assertIn("负载损耗-3级_W", transformer.limits)
        self.assertTrue(transformer.lookups)
        standard_step = next(step for step in transformer.trace if step.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["output"]["空载损耗-1级_W"], transformer.limits["空载损耗-1级_W"])
        # 各设备即使标准资源行尚未内置显式data_id，也应在有ID的查表链
        # 中把它们汇总到标准结果步骤，供后续Excel/移动端回溯。
        self.assertIn("data_ids", next(step for step in fan.trace if step.get("step_type") == "标准查询结果"))

        treatment = self.evaluate("heat_treatment", self.specs["heat_treatment"]["example"])
        self.assertIn("可比单耗未舍入值", treatment.calculated_metrics)

    def test_multistage_pumps_require_stage_count_for_single_stage_head(self):
        for device_type, category in (("pump_water", "多级"), ("pump_chemical", "多级石油化工离心泵")):
            values = dict(self.specs[device_type]["example"])
            values.update({"category": category})
            values.pop("stages", None)
            result = self.evaluate(device_type, values)
            with self.subTest(device_type=device_type):
                self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
                self.assertIn("级数", result.missing_fields)

    def test_multistage_pumps_reject_non_integer_stage_count(self):
        for device_type, category in (("pump_water", "多级"), ("pump_chemical", "多级石油化工离心泵")):
            values = dict(self.specs[device_type]["example"])
            values.update({"category": category, "stages": "1.5"})
            result = self.evaluate(device_type, values)
            with self.subTest(device_type=device_type):
                self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
                self.assertNotIn("级数", result.missing_fields)
                self.assertEqual(result.evaluation_status, "INVALID_INPUT")
                self.assertIn("STAGES_INVALID", result.issue_codes)
                self.assertIn("正整数", result.explanation)

    def test_pump_range_miss_retains_actual_and_calculated_metrics(self):
        cases = (
            ("pump_water", {"category": "单级单吸", "suction": "单吸", "stages": "1", "flow_m3h": "0.1", "head_m": 50, "rated_speed_rpm": 2900, "pump_efficiency": 80}),
            ("pump_chemical", {"category": "单级石油化工离心泵", "suction": "单吸", "stages": "1", "flow_m3h": "0.1", "head_m": 50, "rated_speed_rpm": 2900, "pump_efficiency": 80}),
        )
        for device_type, values in cases:
            result = self.evaluate(device_type, values)
            with self.subTest(device_type=device_type):
                self.assertEqual(result.conclusion, Conclusion.NOT_APPLICABLE)
                self.assertEqual(result.actual_metrics["泵效率_%"], 80)
                self.assertIn("比转速", result.calculated_metrics)
                self.assertIn("输出功率_kW", result.calculated_metrics)
                self.assertTrue(result.lookups)
                self.assertIn("未命中", result.lookups[0]["match_status"])
                self.assertTrue(result.lookups[0]["data_ids"])
                self.assertTrue(result.standard_reference["clause"])

    def test_water_pump_flow_range_miss_preserves_standard_source_pages(self):
        """清水泵流量未命中早退仍应保留表3的PDF来源页。"""
        result = self.evaluate("pump_water", {
            "category": "单级单吸",
            "suction": "单吸",
            "stages": "1",
            "flow_m3h": "0.1",
            "head_m": 50,
            "rated_speed_rpm": 2900,
            "pump_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.NOT_APPLICABLE)
        self.assertEqual(result.lookups[0]["source_pages"], "9-10")

    def test_chemical_pump_range_miss_preserves_standard_source_pages(self):
        """石化泵流量/比转速未命中早退应保留表2的PDF来源页。"""
        result = self.evaluate("pump_chemical", {
            "category": "单级石油化工离心泵",
            "suction": "单吸",
            "stages": "1",
            "flow_m3h": "0.1",
            "head_m": 50,
            "rated_speed_rpm": 2900,
            "pump_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.NOT_APPLICABLE)
        self.assertEqual(result.lookups[0]["source_pages"], "8-9")

    def test_water_pump_category_and_suction_conflict_does_not_silently_recalculate(self):
        """类别已说明单吸时，冲突的单双吸字段不能静默折半流量。"""
        result = self.evaluate("pump_water", {
            "category": "单级单吸清水离心泵",
            "suction": "双吸",
            "stages": "1",
            "flow_m3h": 100,
            "head_m": 50,
            "rated_speed_rpm": 2900,
            "pump_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("单双吸", result.explanation)
        self.assertEqual(result.actual_metrics["泵效率_%"], Decimal("80"))
        self.assertEqual(result.calculated_metrics["输出功率_kW"], Decimal("13.6250"))
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "设备类别与单双吸冲突")
        self.assertEqual(lookup["category"], "单级单吸")
        self.assertEqual(lookup["suction"], "双吸")
        self.assertEqual(lookup["candidate_types"], ["单级单吸", "单级双吸"])
        self.assertEqual(lookup["source_pages"], "9-10")
        self.assertEqual(
            lookup["data_ids"],
            ["GB19762-T3-01", "GB19762-T3-02", "GB19762-T3-03", "GB19762-T3-04"],
        )
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_water_pump_unknown_category_does_not_default_to_single_stage(self):
        """未知清水泵型不得用默认单级/单吸计算比转速。"""
        result = self.evaluate("pump_water", {
            "category": "未知清水泵",
            "flow_m3h": 100,
            "head_m": 50,
            "rated_speed_rpm": 2900,
            "pump_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.category_status, "UNRESOLVED")
        self.assertEqual(result.evaluation_status, "INVALID_INPUT")
        self.assertIn("CATEGORY_UNRESOLVED", result.issue_codes)
        self.assertFalse(result.calculated_metrics)
        self.assertFalse(result.lookups)

    def test_water_pump_uses_pdf_open_upper_boundary_for_flow_bins(self):
        values = {
            "category": "单级单吸", "suction": "单吸", "stages": "1", "head_m": 50,
            "rated_speed_rpm": 2900, "pump_efficiency": 80,
        }
        lower = self.evaluate("pump_water", {**values, "flow_m3h": 300})
        upper = self.evaluate("pump_water", {**values, "flow_m3h": Decimal("300.0001")})
        self.assertEqual(str(lower.calculated_metrics["C1"]), "161.33")
        self.assertEqual(str(upper.calculated_metrics["C1"]), "162.33")
        lookup = next(item for item in upper.trace if item.get("step_type") == "公式计算")
        self.assertEqual(lookup["data_id"], "GB19762-T3-02")
        self.assertFalse(lookup["flow_boundary"]["min_inclusive"])
        self.assertTrue(lookup["flow_boundary"]["max_inclusive"])

    def test_water_pump_double_suction_closed_upper_flow_uses_half_flow_formula(self):
        """GB 19762-2025表3双吸600 m³/h仍属闭上限档并按半流量计算。"""
        result = self.evaluate("pump_water", {
            "category": "单级双吸",
            "suction": "双吸",
            "stages": "1",
            "flow_m3h": 600,
            "head_m": 50,
            "rated_speed_rpm": 2900,
            "pump_efficiency": 90,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.calculated_metrics["计算流量_m3/h"], Decimal("300"))
        self.assertEqual(result.calculated_metrics["C1"], Decimal("161.33"))
        self.assertEqual(result.calculated_metrics["C2"], Decimal("163.33"))
        self.assertEqual(result.calculated_metrics["C3"], Decimal("168.33"))
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19762-T3-03")
        self.assertEqual(lookup["source_pages"], "9-10")
        self.assertEqual(lookup["flow_boundary"], {
            "min": "50", "max": "600",
            "min_inclusive": True, "max_inclusive": True,
        })
        self.assertEqual(result.limits["1级效率_%"], Decimal("88.434211"))

    def test_water_pump_double_suction_flow_600_switches_to_open_upper_band(self):
        """双吸泵Q=600闭合于表3-03，超过600后进入表3-04且仍按半流量计算。"""
        common = {
            "category": "单级双吸",
            "suction": "双吸",
            "stages": "1",
            "head_m": 50,
            "rated_speed_rpm": 2900,
            "pump_efficiency": 90,
        }
        lower = self.evaluate("pump_water", {**common, "flow_m3h": Decimal("600")})
        upper = self.evaluate("pump_water", {**common, "flow_m3h": Decimal("600.0001")})
        self.assertEqual(lower.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(upper.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(lower.lookups[0]["data_id"], "GB19762-T3-03")
        self.assertEqual(upper.lookups[0]["data_id"], "GB19762-T3-04")
        self.assertEqual(upper.calculated_metrics["计算流量_m3/h"], Decimal("300.00005"))
        self.assertEqual(upper.lookups[0]["flow_boundary"], {
            "min": "600", "max": "20000",
            "min_inclusive": False, "max_inclusive": True,
        })
        self.assertEqual(
            tuple(upper.calculated_metrics[f"C{i}"] for i in range(1, 4)),
            (Decimal("162.33"), Decimal("163.33"), Decimal("168.33")),
        )
        self.assertEqual(upper.limits["1级效率_%"], Decimal("87.434212"))

    def test_water_pump_multistage_q100_closed_upper_uses_single_stage_head(self):
        """GB 19762-2025表3多级Q=100闭上限应除级数计算单级扬程。"""
        result = self.evaluate("pump_water", {
            "category": "多级",
            "suction": "单吸",
            "flow_m3h": 100,
            "head_m": 100,
            "rated_speed_rpm": 2900,
            "stages": 2,
            "pump_efficiency": 90,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.calculated_metrics["计算流量_m3/h"], Decimal("100"))
        self.assertEqual(result.calculated_metrics["单级扬程_m"], Decimal("50"))
        self.assertEqual(
            result.calculated_metrics["比转速"],
            Decimal("93.823603448604507505014701083136622423532335781578"),
        )
        self.assertEqual(result.calculated_metrics["输出功率_kW"], Decimal("27.2500"))
        self.assertEqual(
            {result.calculated_metrics[f"C{i}"] for i in range(1, 4)},
            {Decimal("139.33"), Decimal("142.33"), Decimal("150.33")},
        )
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19762-T3-07")
        self.assertEqual(lookup["flow_boundary"], {
            "min": "5", "max": "100",
            "min_inclusive": True, "max_inclusive": True,
        })
        self.assertEqual(result.limits["1级效率_%"], Decimal("75.575297"))

    def test_water_pump_light_multistage_vertical_and_horizontal_keep_distinct_rows(self):
        """轻型多级立式/卧式泵应分别命中表3-09/表3-10，且Q=300闭上限仍折算单级扬程。"""
        common = {
            "flow_m3h": 300,
            "head_m": 100,
            "rated_speed_rpm": 2900,
            "suction": "单吸",
            "stages": 2,
            "pump_efficiency": 90,
        }
        expected = {
            "轻型多级立式": ("GB19762-T3-09", (Decimal("137.33"), Decimal("139.33"), Decimal("144.33")), Decimal("85.016873")),
            "轻型多级卧式": ("GB19762-T3-10", (Decimal("140.33"), Decimal("142.33"), Decimal("147.33")), Decimal("82.016873")),
        }
        for category, (data_id, coefficients, level_one) in expected.items():
            with self.subTest(category=category):
                result = self.evaluate("pump_water", {**common, "category": category})
                self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
                self.assertEqual(result.calculated_metrics["计算流量_m3/h"], Decimal("300"))
                self.assertEqual(result.calculated_metrics["单级扬程_m"], Decimal("50"))
                self.assertEqual(
                    result.calculated_metrics["比转速"],
                    Decimal("162.50724812217753784673278280082570542858815880464"),
                )
                self.assertEqual(
                    tuple(result.calculated_metrics[f"C{i}"] for i in range(1, 4)),
                    coefficients,
                )
                lookup = result.lookups[0]
                self.assertEqual(lookup["data_id"], data_id)
                self.assertEqual(lookup["source_pages"], "9-10")
                self.assertEqual(lookup["flow_boundary"], {
                    "min": "5", "max": "300",
                    "min_inclusive": True, "max_inclusive": True,
                })
                self.assertEqual(result.limits["1级效率_%"], level_one)

    def test_water_pump_multistage_flow_100_switches_to_open_upper_band(self):
        """普通多级泵Q=100属于表3-07，超过100后才进入表3-08。"""
        common = {
            "category": "多级",
            "suction": "单吸",
            "head_m": 100,
            "rated_speed_rpm": 2900,
            "stages": 2,
            "pump_efficiency": 90,
        }
        lower = self.evaluate("pump_water", {**common, "flow_m3h": Decimal("100")})
        upper = self.evaluate("pump_water", {**common, "flow_m3h": Decimal("100.0001")})
        self.assertEqual(lower.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(upper.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(lower.lookups[0]["data_id"], "GB19762-T3-07")
        self.assertEqual(upper.lookups[0]["data_id"], "GB19762-T3-08")
        self.assertEqual(lower.lookups[0]["flow_boundary"], {
            "min": "5", "max": "100",
            "min_inclusive": True, "max_inclusive": True,
        })
        self.assertEqual(upper.lookups[0]["flow_boundary"], {
            "min": "100", "max": "3000",
            "min_inclusive": False, "max_inclusive": True,
        })
        self.assertEqual(
            tuple(lower.calculated_metrics[f"C{i}"] for i in range(1, 4)),
            (Decimal("139.33"), Decimal("142.33"), Decimal("150.33")),
        )
        self.assertEqual(
            tuple(upper.calculated_metrics[f"C{i}"] for i in range(1, 4)),
            (Decimal("140.33"), Decimal("142.33"), Decimal("150.33")),
        )

    def test_chemical_pump_uses_pdf_open_upper_boundaries_at_ns_60_and_120(self):
        values = {
            "category": "单级石油化工离心泵", "flow_m3h": 100,
            "head_m": 50, "rated_speed_rpm": 2900, "pump_efficiency": 80,
            "suction": "单吸", "stages": "1",
        }
        for ns, expected_min, expected_max, min_inclusive, max_inclusive in (
            (Decimal("60"), Decimal("60"), Decimal("120"), True, False),
            (Decimal("120"), Decimal("120"), Decimal("210"), True, True),
        ):
            with self.subTest(ns=ns), patch(
                "equipeffi.domain.evaluation.device_evaluators._specific_speed",
                return_value=(ns, {"比转速": ns}),
            ):
                result = self.evaluate("pump_chemical", values)
            self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
            boundary = result.lookups[0]["specific_speed_boundary"]
            self.assertEqual(Decimal(str(boundary["min"])), expected_min)
            self.assertEqual(Decimal(str(boundary["max"])), expected_max)
            self.assertEqual(boundary["min_inclusive"], min_inclusive)
            self.assertEqual(boundary["max_inclusive"], max_inclusive)

    def test_chemical_pump_flow_lower_boundary_is_open_at_q5(self):
        """GB 19762-2025表2第一流量档为5<Q≤300，Q=5不得被判级。"""
        result = self.evaluate("pump_chemical", {
            "category": "单级石油化工离心泵",
            "suction": "单吸",
            "stages": "1",
            "flow_m3h": Decimal("5"),
            "head_m": 50,
            "rated_speed_rpm": 2900,
            "pump_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.NOT_APPLICABLE)
        self.assertIn("要求总流量QBEP大于5", result.explanation)
        self.assertEqual(result.actual_metrics["泵效率_%"], Decimal("80"))
        self.assertEqual(result.calculated_metrics["计算流量_m3/h"], Decimal("5"))
        self.assertEqual(result.lookups[0]["match_status"], "流量档位未命中：总流量低于开区间下界")
        self.assertFalse(result.lookups[0]["flow_ranges"][0].get("min_inclusive", True))

        inside = self.evaluate("pump_chemical", {
            "category": "单级石油化工离心泵",
            "suction": "单吸",
            "stages": "1",
            "flow_m3h": Decimal("5.0001"),
            "head_m": 50,
            "rated_speed_rpm": 2900,
            "pump_efficiency": 80,
        })
        self.assertEqual(inside.conclusion, Conclusion.LEVEL_1)
        self.assertFalse(inside.lookups[0]["flow_boundary"]["min_inclusive"])

    def test_chemical_pump_flow_q300_uses_closed_upper_band_and_formula_evidence(self):
        """石化泵Q=300仍属5<Q≤300档，并保留规定点效率计算过程。"""
        result = self.evaluate("pump_chemical", {
            "category": "单级石油化工离心泵",
            "suction": "单吸",
            "stages": "1",
            "flow_m3h": 300,
            "head_m": 100,
            "rated_speed_rpm": 2900,
            "pump_efficiency": 90,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.calculated_metrics["计算流量_m3/h"], Decimal("300"))
        self.assertEqual(result.calculated_metrics["单级扬程_m"], Decimal("100"))
        self.assertEqual(
            result.calculated_metrics["比转速"],
            Decimal("96.627387853203055182367085849108176464830043275893"),
        )
        self.assertIn("基准效率_%", result.calculated_metrics)
        self.assertIn("效率修正值_%", result.calculated_metrics)
        self.assertIn("规定点效率_%", result.calculated_metrics)
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19762-R000012")
        self.assertEqual(lookup["offsets"], ["4", "1", "-6"])
        self.assertTrue(lookup["eta0_uses_delta"])
        self.assertEqual(lookup["flow_boundary"], {
            "min": 5, "max": 300,
            "min_inclusive": False, "max_inclusive": True,
        })
        self.assertEqual(lookup["specific_speed_boundary"], {
            "min": 60, "max": 120,
            "min_inclusive": True, "max_inclusive": False,
        })
        self.assertEqual(result.limits["1级效率_%"], Decimal("80.867618"))

    def test_chemical_multistage_lookup_retains_stage_count_and_single_stage_head(self):
        """多级化工泵应保留级数及除级数后的单级扬程，便于复核公式。"""
        result = self.evaluate("pump_chemical", {
            "category": "多级石油化工离心泵",
            "suction": "单吸",
            "flow_m3h": 100,
            "head_m": 100,
            "rated_speed_rpm": 2900,
            "stages": 2,
            "pump_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.calculated_metrics["单级扬程_m"], Decimal("50"))
        lookup = result.lookups[0]
        self.assertEqual(lookup["stages"], "2")
        self.assertEqual(lookup["parameters"]["单级扬程_m"], "50")
        self.assertEqual(lookup["data_id"], "GB19762-R000020")

    def test_chemical_multistage_q300_uses_eta0_without_delta_at_ns162(self):
        """石化多级泵Q=300、ns≈162.5命中闭区间并按η0=ηb计算。"""
        result = self.evaluate("pump_chemical", {
            "category": "多级石油化工离心泵",
            "suction": "单吸",
            "flow_m3h": 300,
            "head_m": 100,
            "rated_speed_rpm": 2900,
            "stages": 2,
            "pump_efficiency": 90,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.calculated_metrics["计算流量_m3/h"], Decimal("300"))
        self.assertEqual(result.calculated_metrics["单级扬程_m"], Decimal("50"))
        self.assertEqual(
            result.calculated_metrics["比转速"],
            Decimal("162.50724812217753784673278280082570542858815880464"),
        )
        self.assertEqual(result.calculated_metrics["效率修正值_%"], Decimal("0"))
        self.assertEqual(
            result.calculated_metrics["规定点效率_%"],
            result.calculated_metrics["基准效率_%"],
        )
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19762-R000021")
        self.assertEqual(lookup["stages"], "2")
        self.assertEqual(lookup["offsets"], ["1", "-1", "-5"])
        self.assertFalse(lookup["eta0_uses_delta"])
        self.assertEqual(lookup["flow_boundary"], {
            "min": 5, "max": 300,
            "min_inclusive": False, "max_inclusive": True,
        })
        self.assertEqual(lookup["specific_speed_boundary"], {
            "min": 120, "max": 210,
            "min_inclusive": True, "max_inclusive": True,
        })
        self.assertEqual(result.limits["1级效率_%"], Decimal("76.267562"))

    def test_chemical_pump_q_above_99999_is_allowed_by_open_upper_flow_range(self):
        """表2第二流量档为Q>300，无人为99999上限。"""
        result = self.evaluate("pump_chemical", {
            "category": "单级石油化工离心泵",
            "suction": "单吸",
            "stages": "1",
            "flow_m3h": Decimal("100000"),
            "head_m": 5000,
            "rated_speed_rpm": 2900,
            "pump_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_3)
        self.assertEqual(result.calculated_metrics["比转速"], Decimal("93.823603448604507505014701083136622423532335781577"))
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19762-R000016")
        self.assertIsNone(lookup["flow_boundary"]["max"])
        self.assertFalse(lookup["flow_boundary"]["min_inclusive"])

    def test_chemical_pump_prescribed_point_rule_at_ns210_retains_zero_delta_and_offsets(self):
        """表2的120≤ns≤210档应记录η0=ηb及三级偏移量。"""
        values = {
            "category": "单级石油化工离心泵",
            "suction": "单吸",
            "stages": "1",
            "flow_m3h": 100,
            "head_m": 50,
            "rated_speed_rpm": 2900,
            "pump_efficiency": 80,
        }
        with patch(
            "equipeffi.domain.evaluation.device_evaluators._specific_speed",
            return_value=(Decimal("210"), {"比转速": Decimal("210")}),
        ):
            result = self.evaluate("pump_chemical", values)
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.calculated_metrics["效率修正值_%"], Decimal("0"))
        lookup = result.lookups[0]
        self.assertFalse(lookup["eta0_uses_delta"])
        self.assertEqual(lookup["offsets"], ["3", "1", "-6"])
        self.assertEqual(lookup["data_id"], "GB19762-R000013")

    def test_chemical_pump_ns_range_miss_retains_open_closed_specific_speed_bounds(self):
        """比转速未命中时仍应保留表2各档的开闭端点。"""
        values = {
            "category": "单级石油化工离心泵",
            "suction": "单吸",
            "stages": "1",
            "flow_m3h": 100,
            "head_m": 50,
            "rated_speed_rpm": 2900,
            "pump_efficiency": 80,
        }
        with patch(
            "equipeffi.domain.evaluation.device_evaluators._specific_speed",
            return_value=(Decimal("300.0001"), {"比转速": Decimal("300.0001")}),
        ):
            result = self.evaluate("pump_chemical", values)
        self.assertEqual(result.conclusion, Conclusion.NOT_APPLICABLE)
        ranges = result.lookups[0]["specific_speed_ranges"]
        self.assertFalse(ranges[-1]["min_inclusive"])
        self.assertTrue(ranges[-1]["max_inclusive"])

    def test_chemical_pump_category_and_stage_count_conflict_does_not_silently_use_single_stage(self):
        """类别已说明单级时，级数大于1不能被忽略后继续查单级标准。"""
        result = self.evaluate("pump_chemical", {
            "category": "单级石油化工离心泵",
            "suction": "单吸",
            "flow_m3h": 100,
            "head_m": 50,
            "rated_speed_rpm": 2900,
            "stages": 2,
            "pump_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("级数", result.explanation)
        self.assertEqual(result.actual_metrics["泵效率_%"], Decimal("80"))
        self.assertEqual(result.calculated_metrics["输出功率_kW"], Decimal("13.6250"))
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "泵级数与设备类别冲突")
        self.assertEqual(lookup["category"], "单级")
        self.assertEqual(lookup["stages"], "2")
        self.assertEqual(lookup["candidate_types"], ["单级", "多级"])
        self.assertEqual(lookup["source_pages"], "8-9")
        self.assertEqual(len(lookup["data_ids"]), 16)
        self.assertEqual(lookup["data_ids"][0], "GB19762-R000011")
        self.assertEqual(lookup["data_ids"][-1], "GB19762-R000026")
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_chemical_pump_unknown_category_does_not_default_to_single_stage(self):
        """未知泵型不得静默按单级套用GB 19762-2025表2。"""
        result = self.evaluate("pump_chemical", {
            "category": "未知化工泵",
            "suction": "单吸",
            "stages": "1",
            "flow_m3h": 100,
            "head_m": 50,
            "rated_speed_rpm": 2900,
            "pump_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("类别", result.explanation)
        self.assertEqual(result.category_status, "UNRESOLVED")
        self.assertEqual(result.evaluation_status, "INVALID_INPUT")
        self.assertEqual(result.issue_codes, ["CATEGORY_UNRESOLVED"])
        self.assertEqual(result.actual_metrics, {})
        self.assertEqual(result.calculated_metrics, {})
        self.assertEqual(result.lookups, [])

    def test_blower_calculates_polytropic_efficiency_from_pressures_and_temperatures(self):
        values = {
            "category": "单级双支撑低速离心鼓风机",
            "impeller_width_mm": 100,
            "impeller_diameter_mm": 1000,
            "inlet_absolute_pressure_kpa": 100,
            "outlet_absolute_pressure_kpa": 200,
            "inlet_temperature_k": 300,
            "outlet_temperature_k": 404,
            "isentropic_k": 1.4,
        }
        result = self.evaluate("blower", values)
        self.assertIn(result.conclusion, {Conclusion.SAVING_VALUE, Conclusion.LIMIT_VALUE, Conclusion.NOT_COMPLIANT})
        self.assertIn("多变效率计算值_%", result.calculated_metrics)
        self.assertTrue(any(item.get("step_type") == "公式计算" for item in result.lookups))

    def test_blower_pdf_tables_cover_all_eight_classes_and_multistage_rows(self):
        pack = JsonStandardRepository(ROOT).get_pack("blower")
        self.assertEqual({table["name"] for table in pack["tables"]}, {f"表{i}" for i in range(1, 9)})
        self.assertEqual({(table["type"], table["kind"]) for table in pack["tables"]}, {
            ("单级双支撑低速", "限定值"), ("多级低速", "限定值"),
            ("单级双支撑高速", "限定值"), ("多级高速", "限定值"),
            ("单级双支撑低速", "节能评价值"), ("多级低速", "节能评价值"),
            ("单级双支撑高速", "节能评价值"), ("多级高速", "节能评价值"),
        })
        result = self.evaluate("blower", {
            "category": "多级低速离心鼓风机", "stages": 4,
            "polytropic_efficiency": 75, "impeller_width_mm": 25,
            "impeller_diameter_mm": 500,
        })
        self.assertEqual(result.conclusion, Conclusion.SAVING_VALUE)
        self.assertEqual(result.limits["限定值"], Decimal("69.0"))
        self.assertEqual(result.limits["节能评价值"], Decimal("74.0"))
        self.assertTrue(any(step.get("table") == "表2" for step in result.trace))
        self.assertTrue(any(step.get("table") == "表6" for step in result.trace))

    def test_blower_normal_lookup_preserves_query_context_and_match_status(self):
        """鼓风机正常查表应保留型式、D₂、b₂/D₂及命中状态。"""
        result = self.evaluate("blower", dict(self.specs["blower"]["example"]))
        self.assertEqual(result.conclusion, Conclusion.SAVING_VALUE)
        lookups = [item for item in result.lookups if item.get("kind") in {"限定值", "节能评价值"}]
        self.assertEqual({item.get("table") for item in lookups}, {"表1", "表5"})
        for lookup in lookups:
            self.assertEqual(lookup["matching"], "型式+D₂档位+b₂/D₂档位+级数（多级时）")
            self.assertEqual(lookup["match_status"], "命中")
            self.assertEqual(lookup["query_conditions"], {
                "category": "单级双支撑低速离心鼓风机",
                "impeller_width_mm": "100",
                "impeller_diameter_mm": "1000",
                "b2_d2": "0.1",
                "stages": "",
            })

    def test_blower_missing_pressure_or_temperature_retains_known_inputs_and_thresholds(self):
        """鼓风机缺出口压力/温度时仍保留已知输入、表1/表5阈值和查表轨迹。"""
        result = self.evaluate("blower", {
            "category": "单级双支撑低速离心鼓风机",
            "impeller_width_mm": 100,
            "impeller_diameter_mm": 1000,
            "inlet_absolute_pressure_kpa": 100,
            "inlet_temperature_k": 300,
            "isentropic_k": 1.4,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["多变效率", "出口绝对压力", "出口温度"])
        self.assertEqual(result.actual_metrics, {})
        self.assertEqual(result.calculated_metrics["b2/D2"], Decimal("0.1"))
        self.assertEqual(result.calculated_metrics["进口绝对压力_kPa"], Decimal("100"))
        self.assertEqual(result.calculated_metrics["进口温度_K"], Decimal("300"))
        self.assertEqual(result.calculated_metrics["绝热指数k"], Decimal("1.4"))
        self.assertEqual(result.limits, {
            "限定值": Decimal("71.5"),
            "节能评价值": Decimal("75.5"),
        })
        self.assertEqual(result.comparisons, [])
        table_lookups = [item for item in result.lookups if item.get("kind") in {"限定值", "节能评价值"}]
        self.assertEqual({item.get("table") for item in table_lookups}, {"表1", "表5"})
        self.assertTrue(all(item.get("match_status") == "命中" for item in table_lookups))
        self.assertTrue(all(item.get("data_id") for item in table_lookups))
        self.assertIn("缺少多变效率", result.explanation)

    def test_multistage_blower_stage_3_4_switches_closed_discrete_band(self):
        """GB 28381-2012表2/表6的2~3与4~6级数档必须在3/4处切换。"""
        common = {
            "category": "多级低速离心鼓风机",
            "polytropic_efficiency": Decimal("72.75"),
            "impeller_width_mm": 50,
            "impeller_diameter_mm": 500,
        }
        stage_three = self.evaluate("blower", {**common, "stages": 3})
        stage_four = self.evaluate("blower", {**common, "stages": 4})
        # D₂=500命中401~600列；72.75低于2~3级节能评价值73.0，
        # 但达到限定值69.0，因此为“能效限定值”；4~6级节能评价值为72.5，
        # 在4级闭下限命中后应升级为“节能评价值”。
        self.assertEqual(stage_three.conclusion, Conclusion.LIMIT_VALUE)
        self.assertEqual(stage_four.conclusion, Conclusion.SAVING_VALUE)
        self.assertEqual(stage_three.limits["限定值"], Decimal("69.0"))
        self.assertEqual(stage_four.limits["限定值"], Decimal("68.5"))
        self.assertEqual(stage_three.limits["节能评价值"], Decimal("73.0"))
        self.assertEqual(stage_four.limits["节能评价值"], Decimal("72.5"))
        stage_three_ids = {item.get("data_id") for item in stage_three.lookups if item.get("data_id")}
        stage_four_ids = {item.get("data_id") for item in stage_four.lookups if item.get("data_id")}
        self.assertEqual(stage_three_ids, {"GB28381-R000016", "GB28381-R000064"})
        self.assertEqual(stage_four_ids, {"GB28381-R000024", "GB28381-R000072"})
        for result, expected_stage in ((stage_three, "3"), (stage_four, "4")):
            self.assertTrue(all(
                item.get("query_conditions", {}).get("stages") == expected_stage
                for item in result.lookups
                if item.get("kind") in {"限定值", "节能评价值"}
            ))

    def test_blower_ratio_020_gap_and_021_closed_lower_boundary(self):
        """GB 28381-2012表1/表5的<0.020、0.020空档和0.021下档边界。"""
        common = {
            "category": "单级双支撑低速离心鼓风机",
            "impeller_diameter_mm": Decimal("500"),
            "polytropic_efficiency": Decimal("70"),
        }
        below_gap = self.evaluate("blower", {
            **common,
            "impeller_width_mm": Decimal("9.9995"),  # b₂/D₂=0.019999
        })
        at_gap = self.evaluate("blower", {
            **common,
            "impeller_width_mm": Decimal("10"),  # b₂/D₂=0.020，标准未给档
        })
        next_band = self.evaluate("blower", {
            **common,
            "impeller_width_mm": Decimal("10.5"),  # b₂/D₂=0.021，下一档闭下限
        })

        self.assertEqual(below_gap.conclusion, Conclusion.SAVING_VALUE)
        self.assertEqual(below_gap.limits["限定值"], Decimal("53.5"))
        self.assertEqual(below_gap.limits["节能评价值"], Decimal("57.5"))
        self.assertEqual(
            {item.get("data_id") for item in below_gap.lookups if item.get("data_id")},
            {"GB28381-R000001", "GB28381-R000049"},
        )

        self.assertEqual(at_gap.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(at_gap.calculated_metrics["b2/D2"], Decimal("0.02"))
        self.assertTrue(all(item.get("match_status") == "b₂/D₂档位未命中" for item in at_gap.lookups))
        self.assertTrue(all(item.get("data_ids") for item in at_gap.lookups))

        self.assertEqual(next_band.conclusion, Conclusion.LIMIT_VALUE)
        self.assertEqual(next_band.limits["限定值"], Decimal("68.5"))
        self.assertEqual(next_band.limits["节能评价值"], Decimal("72.5"))
        self.assertEqual(
            {item.get("data_id") for item in next_band.lookups if item.get("data_id")},
            {"GB28381-R000002", "GB28381-R000050"},
        )

    def test_blower_applies_standard_structure_adjustment_to_lookup_values(self):
        base = dict(self.specs["blower"]["example"])
        plain = self.evaluate("blower", base)
        adjusted = self.evaluate("blower", {**base, "three_dimensional": "是", "cantilever": "是"})
        self.assertEqual(adjusted.calculated_metrics["结构修正_百分点"], 6)
        self.assertEqual(
            adjusted.limits["限定值"] - plain.limits["限定值"],
            6,
        )

    def test_blower_invalid_optional_stage_or_efficiency_is_structured(self):
        base = dict(self.specs["blower"]["example"])
        invalid_efficiency = self.evaluate("blower", {**base, "polytropic_efficiency": "not-a-number"})
        self.assertEqual(invalid_efficiency.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("多变效率", invalid_efficiency.missing_fields)
        invalid_stage = self.evaluate("blower", {
            **base, "category": "多级低速离心鼓风机", "stages": "not-a-number",
        })
        self.assertEqual(invalid_stage.conclusion, Conclusion.OUT_OF_SCOPE)

    def test_multistage_blower_uses_average_of_stage_efficiencies(self):
        result = self.evaluate("blower", {
            "category": "多级低速离心鼓风机", "stages": 4,
            "stage_efficiencies": [70, 80, 90, 100],
            "impeller_width_mm": 25, "impeller_diameter_mm": 500,
        })
        self.assertEqual(result.actual_metrics["多变效率_%"], Decimal("85"))
        self.assertEqual(result.calculated_metrics["各级多变效率平均值_%"], Decimal("85"))
        self.assertEqual(result.conclusion, Conclusion.SAVING_VALUE)
        average_step = next(item for item in result.lookups if item.get("formula") == "ηp,avg=Σηp,i/n")
        self.assertEqual(average_step["inputs"]["stages"], 4)

    def test_multistage_blower_rejects_incomplete_stage_efficiency_list(self):
        result = self.evaluate("blower", {
            "category": "多级低速离心鼓风机", "stages": 4,
            "stage_efficiencies": "70,80,90",
            "impeller_width_mm": 25, "impeller_diameter_mm": 500,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("数量", result.explanation)

    def test_fan_table_values_are_reordered_to_level_one_two_three_and_adjusted(self):
        base = dict(self.specs["fan"]["example"])
        plain = self.evaluate("fan", base)
        self.assertEqual(plain.limits["1级效率_%"], 86)
        adjusted = self.evaluate("fan", {
            **base,
            "suction": "双吸",
            "hvac_use": "是",
            "inlet_box": "是",
        })
        self.assertEqual(adjusted.limits["1级效率_%"], 80)
        self.assertEqual(adjusted.limits["2级效率_%"], 75)
        self.assertEqual(adjusted.limits["3级效率_%"], 65)

    def test_fan_pdf_pressure_boundary_095_uses_table_one_upper_exclusive_table_two(self):
        common = {
            "category": "离心通风机",
            "machine_no": 10,
            "specific_speed": 10,
            "compression_correction": 1,
            "fan_efficiency": 80,
        }
        upper_table_one = self.evaluate("fan", {**common, "pressure_coefficient": 0.95})
        lower_table_two = self.evaluate("fan", {**common, "pressure_coefficient": 0.949999})
        self.assertTrue(upper_table_one.standard_reference["table"].startswith("表１"))
        self.assertTrue(lower_table_two.standard_reference["table"].startswith("表2"))

    def test_centrifugal_fan_pressure_025_is_inclusive_table_two_lower_bound(self):
        """GB 19761-2020表2的ψ=0.25为闭下限，低于0.25不得取最近档。"""
        common = {
            "category": "离心通风机",
            "machine_no": 10,
            "specific_speed": 70,
            "compression_correction": 1,
            "fan_efficiency": 90,
        }
        below = self.evaluate("fan", {**common, "pressure_coefficient": Decimal("0.249999")})
        at_boundary = self.evaluate("fan", {**common, "pressure_coefficient": Decimal("0.25")})
        self.assertEqual(below.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(at_boundary.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(below.standard_reference["clause"], "表1～表4")
        self.assertEqual(at_boundary.standard_reference["table"], "表2 离心通风机(0.25≤ψ<0.95)能效等级")
        self.assertEqual(at_boundary.lookups[-1]["data_id"], "GB19761-R000020")
        self.assertEqual(at_boundary.lookups[-1]["pressure_interval"], "0.25≤ψ<0.35")
        self.assertEqual(at_boundary.lookups[-1]["secondary_interval"], "65≤ns<85")
        self.assertEqual(at_boundary.lookups[-1]["machine_interval"], "机号≥No10")
        self.assertEqual(at_boundary.limits["1级效率_%"], Decimal("86.0"))
        self.assertEqual(at_boundary.limits["2级效率_%"], Decimal("81.0"))
        self.assertEqual(at_boundary.limits["3级效率_%"], Decimal("72.0"))

    def test_axial_fan_hub_ratio_03_switches_to_next_standard_row(self):
        """GB 19761-2020表3的γ=0.3应从γ<0.3切换到0.3≤γ<0.4。"""
        common = {
            "category": "轴流通风机",
            "machine_no": 5,
            "pressure_coefficient": Decimal("0.5"),
            "specific_speed": 10,
            "compression_correction": 1,
            "fan_efficiency": 80,
        }
        below = self.evaluate("fan", {**common, "hub_ratio": Decimal("0.299999")})
        at_boundary = self.evaluate("fan", {**common, "hub_ratio": Decimal("0.3")})
        self.assertEqual(below.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(at_boundary.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(below.standard_reference["table"], "表3 轴流通风机能效等级")
        self.assertEqual(at_boundary.standard_reference["table"], "表3 轴流通风机能效等级")
        below_lookup = below.lookups[-1]
        boundary_lookup = at_boundary.lookups[-1]
        self.assertEqual(below_lookup["data_id"], "GB19761-R000021")
        self.assertEqual(boundary_lookup["data_id"], "GB19761-R000022")
        self.assertEqual(below_lookup["secondary_interval"], "γ<0.3")
        self.assertEqual(boundary_lookup["secondary_interval"], "0.3≤γ<0.4")
        self.assertEqual(below_lookup["machine_interval"], "No5≤机号<No10")
        self.assertEqual(boundary_lookup["machine_interval"], "No5≤机号<No10")
        self.assertEqual(below.limits["1级效率_%"], Decimal("74.0"))
        self.assertEqual(at_boundary.limits["1级效率_%"], Decimal("76.0"))

    def test_axial_fan_missing_efficiency_retains_table3_thresholds_and_lookup(self):
        """轴流风机效率及式(1)参数缺失时仍保留表3阈值和查表轨迹。"""
        result = self.evaluate("fan", {
            "category": "轴流通风机",
            "machine_no": 5,
            "pressure_coefficient": 0.5,
            "hub_ratio": 0.2,
            "compression_correction": 1,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, [
            "风机效率", "流量", "叶轮功率", "风机压力（或出口/进口滞止压力）",
        ])
        self.assertEqual(result.actual_metrics, {})
        self.assertEqual(result.calculated_metrics["压力系数"], Decimal("0.5"))
        self.assertEqual(result.calculated_metrics["hub_ratio"], Decimal("0.2"))
        self.assertEqual(result.limits, {
            "1级效率_%": Decimal("74"),
            "2级效率_%": Decimal("71"),
            "3级效率_%": Decimal("60"),
        })
        self.assertEqual(result.comparisons, [])
        self.assertEqual(len(result.lookups), 2)
        self.assertEqual(result.lookups[0]["step_type"], "结构条件修正")
        lookup = next(item for item in result.lookups if item.get("step_type") == "精确查表")
        self.assertEqual(lookup["table"], "表3 轴流通风机能效等级")
        self.assertEqual(lookup["data_id"], "GB19761-R000021")
        self.assertEqual(lookup["match_status"], "命中")
        self.assertEqual(lookup["secondary_interval"], "γ<0.3")
        self.assertEqual(lookup["machine_interval"], "No5≤机号<No10")
        self.assertIn("GB19761式(1)", result.explanation)

    def test_axial_fan_machine_no_10_switches_to_inclusive_upper_machine_band(self):
        """GB 19761-2020表3机号=10应进入“机号≥No10”档，而非No5≤机号<No10。"""
        common = {
            "category": "轴流通风机",
            "hub_ratio": Decimal("0.2"),
            "pressure_coefficient": Decimal("0.5"),
            "specific_speed": 10,
            "compression_correction": 1,
            "fan_efficiency": 80,
        }
        below = self.evaluate("fan", {**common, "machine_no": Decimal("9.9999")})
        at_boundary = self.evaluate("fan", {**common, "machine_no": Decimal("10")})
        self.assertEqual(below.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(at_boundary.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(below.lookups[-1]["data_id"], "GB19761-R000021")
        self.assertEqual(at_boundary.lookups[-1]["data_id"], "GB19761-R000021")
        self.assertEqual(below.lookups[-1]["machine_interval"], "No5≤机号<No10")
        self.assertEqual(at_boundary.lookups[-1]["machine_interval"], "机号≥No10")
        self.assertEqual(below.limits["1级效率_%"], Decimal("74.0"))
        self.assertEqual(at_boundary.limits["1级效率_%"], Decimal("79.0"))

    def test_axial_fan_missing_efficiency_at_hub_ratio_03_keeps_closed_boundary_trace(self):
        """轴流风机缺效率时γ=0.3仍切换到表3的闭下限标准行。"""
        result = self.evaluate("fan", {
            "category": "轴流通风机",
            "machine_no": 5,
            "pressure_coefficient": 0.5,
            "hub_ratio": 0.3,
            "compression_correction": 1,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, [
            "风机效率", "流量", "叶轮功率", "风机压力（或出口/进口滞止压力）",
        ])
        self.assertEqual(result.actual_metrics, {})
        self.assertEqual(result.calculated_metrics["hub_ratio"], Decimal("0.3"))
        self.assertEqual(result.limits, {
            "1级效率_%": Decimal("76"),
            "2级效率_%": Decimal("73"),
            "3级效率_%": Decimal("63"),
        })
        self.assertEqual(len(result.lookups), 2)
        self.assertEqual(result.lookups[0]["step_type"], "结构条件修正")
        lookup = next(item for item in result.lookups if item.get("step_type") == "精确查表")
        self.assertEqual(lookup["data_id"], "GB19761-R000022")
        self.assertEqual(lookup["secondary_interval"], "0.3≤γ<0.4")
        self.assertEqual(lookup["machine_interval"], "No5≤机号<No10")
        self.assertEqual(lookup["match_status"], "命中")
        self.assertIn("GB19761式(1)", result.explanation)

    def test_axial_fan_missing_efficiency_at_machine_no_10_keeps_closed_machine_trace(self):
        """轴流风机缺效率时机号=10仍进入表3的闭上限机号档。"""
        result = self.evaluate("fan", {
            "category": "轴流通风机",
            "machine_no": 10,
            "pressure_coefficient": 0.5,
            "hub_ratio": 0.2,
            "compression_correction": 1,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, [
            "风机效率", "流量", "叶轮功率", "风机压力（或出口/进口滞止压力）",
        ])
        self.assertEqual(result.actual_metrics, {})
        self.assertEqual(result.limits, {
            "1级效率_%": Decimal("79"),
            "2级效率_%": Decimal("75"),
            "3级效率_%": Decimal("62"),
        })
        self.assertEqual(len(result.lookups), 2)
        self.assertEqual(result.lookups[0]["step_type"], "结构条件修正")
        lookup = next(item for item in result.lookups if item.get("step_type") == "精确查表")
        self.assertEqual(lookup["data_id"], "GB19761-R000021")
        self.assertEqual(lookup["secondary_interval"], "γ<0.3")
        self.assertEqual(lookup["machine_interval"], "机号≥No10")
        self.assertEqual(lookup["match_status"], "命中")
        self.assertIn("GB19761式(1)", result.explanation)

    def test_fan_invalid_specific_speed_returns_structured_unable_result(self):
        result = self.evaluate("fan", {
            "category": "离心通风机",
            "machine_no": 10,
            "pressure_coefficient": 0.5,
            "specific_speed": "待复核",
            "compression_correction": 1,
            "fan_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("比转速/轮毂比", result.missing_fields)

    def test_fan_primary_pressure_match_retains_candidates_when_specific_speed_is_missing(self):
        """压力系数已锁定表2时，缺少比转速仍需保留候选标准行。"""
        result = self.evaluate("fan", {
            "category": "离心通风机",
            "machine_no": 10,
            "pressure_coefficient": 0.5,
            "compression_correction": 1,
            "fan_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("比转速", result.explanation)
        self.assertEqual(result.actual_metrics["最高通风机效率ηr_%"], Decimal("80"))
        self.assertEqual(result.calculated_metrics["压力系数"], Decimal("0.5"))
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "比转速/轮毂比未提供")
        self.assertEqual(lookup["primary_value"], "0.5")
        self.assertEqual(lookup["source_page"], 4)
        self.assertEqual(lookup["data_ids"], [
            "GB19761-R000015", "GB19761-R000016", "GB19761-R000017",
        ])
        self.assertEqual(lookup["secondary_ranges"], ["10≤ns<30", "30≤ns<50", "50≤ns<70"])
        self.assertTrue(lookup["no_interpolation"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_fan_missing_efficiency_retains_standard_thresholds_and_lookup(self):
        """效率和式(1)物理参数均缺失时仍保留已命中的表2证据。"""
        result = self.evaluate("fan", {
            "category": "离心通风机",
            "machine_no": 10,
            "pressure_coefficient": 0.5,
            "specific_speed": 40,
            "compression_correction": 1,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("风机效率", result.explanation)
        self.assertEqual(
            result.missing_fields,
            ["风机效率", "流量", "叶轮功率", "风机压力（或出口/进口滞止压力）"],
        )
        self.assertEqual(result.actual_metrics, {})
        self.assertEqual(result.calculated_metrics["压力系数"], Decimal("0.5"))
        self.assertEqual(result.limits, {
            "1级效率_%": Decimal("86"),
            "2级效率_%": Decimal("81"),
            "3级效率_%": Decimal("75"),
        })
        self.assertEqual(result.comparisons, [])
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "命中")
        self.assertEqual(lookup["data_id"], "GB19761-R000016")
        self.assertEqual(lookup["source_page"], 4)
        self.assertEqual(lookup["query_conditions"], {
            "category": "离心通风机",
            "pressure_coefficient": "0.5",
            "specific_speed": "40",
            "machine_no": "10",
        })
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], ["GB19761-R000016"])

    def test_fan_range_miss_retains_calculated_pressure_and_actual_efficiency(self):
        """压力系数已解析但未命中标准表时仍保留可报告上下文。"""
        result = self.evaluate("fan", {
            "category": "离心通风机",
            "machine_no": 10,
            "pressure_coefficient": 5,
            "specific_speed": 40,
            "compression_correction": 1,
            "fan_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(result.actual_metrics["最高通风机效率ηr_%"], Decimal("80"))
        self.assertEqual(result.calculated_metrics["压力系数"], Decimal("5"))
        self.assertEqual(
            [item["match_status"] for item in result.lookups],
            ["压力系数档位未命中", "压力系数档位未命中"],
        )
        self.assertEqual(result.standard_reference["clause"], "表1～表4")
        self.assertEqual(len(result.lookups[0]["data_ids"]), 4)
        self.assertEqual(len(result.lookups[1]["data_ids"]), 16)
        query = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(len(query["data_ids"]), 20)

    def test_fan_secondary_range_miss_retains_candidate_row_ids(self):
        """压力系数命中但比转速未命中时不取相邻档位。"""
        result = self.evaluate("fan", {
            "category": "离心通风机",
            "machine_no": 10,
            "pressure_coefficient": 0.5,
            "specific_speed": 100,
            "compression_correction": 1,
            "fan_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(result.calculated_metrics["specific_speed"], Decimal("100"))
        self.assertEqual(result.lookups[0]["match_status"], "比转速/轮毂比档位未命中")
        self.assertEqual(result.lookups[0]["pressure_coefficient"], "0.5")
        self.assertEqual(result.lookups[0]["secondary_value"], "100")
        self.assertEqual(result.lookups[0]["data_ids"], [
            "GB19761-R000015", "GB19761-R000016", "GB19761-R000017",
        ])
        self.assertEqual(result.standard_reference["clause"], "表1～表4")

    def test_fan_machine_range_miss_retains_selected_standard_row(self):
        """前两轴命中而机号未命中时保留唯一标准行和机号候选区间。"""
        result = self.evaluate("fan", {
            "category": "离心通风机",
            "machine_no": 1,
            "pressure_coefficient": 0.5,
            "specific_speed": 40,
            "compression_correction": 1,
            "fan_efficiency": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(result.lookups[0]["match_status"], "机号档位未命中")
        self.assertEqual(result.lookups[0]["data_id"], "GB19761-R000016")
        self.assertEqual(result.lookups[0]["machine_no"], "1")
        self.assertEqual(len(result.lookups[0]["machine_ranges"]), 4)

    def test_fan_derives_pressure_from_stagnation_pressures_for_compressibility_path(self):
        result = self.evaluate("fan", {
            "category": "离心通风机", "machine_no": 10, "fan_efficiency": 80,
            "flow_m3h": 10000, "inlet_stagnation_pressure_pa": 101325,
            "outlet_stagnation_pressure_pa": 104500, "impeller_power_kw": 15,
            "rated_speed_rpm": 1450, "inlet_stagnation_density": 1.2,
            "isentropic_k": 1.4,
        })
        self.assertIn(result.conclusion, {Conclusion.LEVEL_1, Conclusion.LEVEL_2, Conclusion.LEVEL_3})

    def test_fan_calculates_efficiency_from_design_power_when_efficiency_is_blank(self):
        result = self.evaluate("fan", {
            "category": "离心通风机", "machine_no": 10,
            "pressure_coefficient": 0.5, "specific_speed": 40,
            "compression_correction": 1, "flow_m3h": 10000,
            "fan_pressure_pa": 2000, "impeller_power_kw": 6,
        })
        self.assertIn(result.conclusion, {Conclusion.LEVEL_1, Conclusion.LEVEL_2, Conclusion.LEVEL_3})
        self.assertAlmostEqual(float(result.calculated_metrics["最高通风机效率ηr_%"]), 92.592592, places=5)
        self.assertTrue(any(item.get("standard") == "GB 19761-2020式(1)" for item in result.lookups))
        self.assertIn("压缩性修正系数", result.calculated_metrics)
        self.assertIn("压力系数", result.calculated_metrics)

    def test_fan_converts_unit_and_motor_efficiency_for_direct_motor_drive(self):
        result = self.evaluate("fan", {
            "category": "离心通风机",
            "transmission": "A式传动（普通电动机直联）",
            "machine_no": 10,
            "pressure_coefficient": 0.5,
            "specific_speed": 40,
            "compression_correction": 1,
            "unit_efficiency": 80,
            "motor_efficiency": 95,
        })
        self.assertAlmostEqual(float(result.actual_metrics["最高通风机效率ηr_%"]), 80 / 95 * 100, places=10)
        self.assertEqual(result.conclusion, Conclusion.LEVEL_2)
        self.assertTrue(any(item.get("standard") == "GB 19761-2020式(4)" for item in result.lookups))

    def test_outer_rotor_forward_multiwing_uses_unit_efficiency_table4(self):
        values = {
            "category": "外转子电机直联前向多翼离心风机",
            "transmission": "外转子电机直联",
            "machine_no": 2,
            "pressure_coefficient": 1.05,
            "specific_speed": 60,
            "unit_efficiency": 50,
        }
        result = self.evaluate("fan", values)
        self.assertEqual(result.standard_reference["table"], "表4 外转子电机直联前向多翼离心风机能效等级")
        self.assertEqual(result.actual_metrics["机组效率ηe_%"], Decimal("50"))
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertTrue(any(item.get("table", "").startswith("表4") for item in result.lookups))

    def test_outer_rotor_can_calculate_unit_efficiency_from_motor_input_power(self):
        result = self.evaluate("fan", {
            "category": "外转子电机直联前向多翼离心风机",
            "transmission": "外转子电机直联",
            "machine_no": 2,
            "fan_pressure_pa": 300,
            "compression_correction": 1,
            "flow_m3h": 10000,
            "inlet_stagnation_density": 1.2,
            "rated_speed_rpm": 1450,
            "rated_power_kw": 1.5,
        })
        self.assertIn("机组效率ηe_%", result.calculated_metrics)
        self.assertIn("GB 19761-2020式(3)", [item.get("standard") for item in result.lookups])

    def test_outer_rotor_missing_unit_efficiency_retains_table4_thresholds_and_lookup(self):
        """外转子机组效率及式(3)参数缺失时仍保留表4阈值和查表轨迹。"""
        result = self.evaluate("fan", {
            "category": "外转子电机直联前向多翼离心风机",
            "transmission": "外转子电机直联",
            "machine_no": 2,
            "pressure_coefficient": 1.05,
            "specific_speed": 60,
            "compression_correction": 1,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, [
            "机组效率ηe", "流量", "电动机输入功率", "风机压力（或出口/进口滞止压力）",
        ])
        self.assertEqual(result.actual_metrics, {})
        self.assertEqual(result.calculated_metrics["压力系数"], Decimal("1.05"))
        self.assertEqual(result.calculated_metrics["specific_speed"], Decimal("60"))
        self.assertEqual(result.limits, {
            "1级效率_%": Decimal("46"),
            "2级效率_%": Decimal("43"),
            "3级效率_%": Decimal("36"),
        })
        self.assertEqual(result.comparisons, [])
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表4 外转子电机直联前向多翼离心风机能效等级")
        self.assertEqual(lookup["data_id"], "GB19761-R000025")
        self.assertEqual(lookup["match_status"], "命中")
        self.assertEqual(lookup["machine_interval"], "机号≤No2")
        self.assertEqual(lookup["secondary_interval"], "ns>50")
        self.assertIn("机组效率ηe", result.explanation)
        self.assertIn("GB19761式(3)", result.explanation)

    def test_outer_rotor_rejects_mismatched_transmission(self):
        result = self.evaluate("fan", {
            "category": "外转子电机直联前向多翼离心风机",
            "transmission": "A式传动（普通电动机直联）",
            "machine_no": 2,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("传动方式", result.missing_fields)

    def test_axial_fan_missing_hub_ratio_is_unable_not_out_of_scope(self):
        values = dict(self.specs["fan"]["example"], category="轴流通风机", hub_ratio=None)
        result = self.evaluate("fan", values)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("轮毂比", result.missing_fields)

    def test_heat_treatment_selects_power_or_temperature_specification_from_v4_fields(self):
        result = self.evaluate("heat_treatment", {
            "category": "箱式多用炉",
            "energy_type": "电炉",
            "rated_power_kw": 60,
            "rated_temperature_c": 800,
            "equivalent_weight_t": 1,
            "total_electricity_kwh": 600,
        })
        self.assertEqual(result.conclusion, Conclusion.SECOND_CLASS)
        self.assertEqual(result.standard_reference["table"], "表8")
        self.assertEqual(result.lookups[0]["source_page"], 11)
        self.assertEqual(result.lookups[0]["data_id"], "GB36561-R000006")
        self.assertEqual(result.lookups[0]["source_clause"], "表8")
        self.assertEqual(result.lookups[0]["inputs"]["equivalent_weight_t"], "1")
        self.assertEqual(result.lookups[0]["thresholds"], ["480", "630", "760"])
        self.assertTrue(result.lookups[0]["specification"])

    def test_heat_treatment_normal_lookup_preserves_query_context(self):
        """热处理设备正常计算记录应保留能源、能耗和炉型条件。"""
        result = self.evaluate("heat_treatment", dict(self.specs["heat_treatment"]["example"]))
        lookup = result.lookups[0]
        self.assertEqual(lookup["query_conditions"], {
            "category": "传送式连续炉",
            "energy_type": "电力",
            "equivalent_weight_t": "1",
            "total_electricity_kwh": "300",
            "fuel_consumption": "",
            "fuel_calorific_value_kjkg": "",
            "rated_power_kw": "",
            "rated_temperature_c": "",
            "specification": "",
        })

    def test_heat_treatment_normal_lookup_marks_standard_row_as_matched(self):
        """热处理设备正常炉型规格查表应显式标记命中状态。"""
        result = self.evaluate("heat_treatment", dict(self.specs["heat_treatment"]["example"]))
        self.assertEqual(result.lookups[0]["match_status"], "命中")

    def test_heat_treatment_fuel_consumption_uses_table9_fuel_coefficient(self):
        result = self.evaluate("heat_treatment", {
            "category": "辊底炉", "energy_type": "天然气",
            "equivalent_weight_t": 1, "fuel_consumption": 100,
            "fuel_calorific_value_kjkg": 34541,
        })
        self.assertIn("燃料系数α", result.calculated_metrics)
        self.assertEqual(str(result.calculated_metrics["燃料系数α"]), "1.1")
        self.assertEqual(result.lookups[0]["fuel_coefficient_source_page"], 12)
        self.assertTrue(result.lookups[0]["fuel_coefficient_data_id"].startswith("GB36561-T9-"))
        self.assertEqual(result.lookups[0]["fuel_coefficient_source_clause"], "表9")
        self.assertEqual(result.lookups[0]["inputs"]["fuel_calorific_value"], "34541")

    def test_heat_treatment_roller_fuel_path_selects_fuel_row_and_unit(self):
        """辊底炉燃料加热必须使用表8燃料加热行，并保留折标计算结果。"""
        result = self.evaluate("heat_treatment", {
            "category": "辊底炉", "energy_type": "天然气",
            "equivalent_weight_t": 1, "fuel_consumption": 100,
            "fuel_calorific_value_kjkg": 34541,
        })
        self.assertEqual(result.conclusion, Conclusion.THIRD_CLASS)
        self.assertEqual(result.actual_metrics["燃料炉可比单耗"], result.calculated_metrics["可比单耗未舍入值"])
        self.assertGreater(result.actual_metrics["燃料炉可比单耗"], Decimal("100"))
        self.assertLessEqual(result.actual_metrics["燃料炉可比单耗"], Decimal("170"))
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB36561-R000024")
        self.assertEqual(lookup["specification"], "燃料加热")
        self.assertEqual(lookup["unit"], "kgce/t")
        self.assertEqual(lookup["thresholds"], ["60", "100", "170"])
        self.assertEqual(lookup["fuel_coefficient_data_id"], "GB36561-T9-05")

    def test_heat_treatment_roller_electric_path_selects_electric_row_and_unit(self):
        """同一炉型切换到电力时必须选择表8电加热行，不能复用燃料行。"""
        result = self.evaluate("heat_treatment", {
            "category": "辊底炉", "energy_type": "电力",
            "equivalent_weight_t": 1, "total_electricity_kwh": 500,
        })
        self.assertEqual(result.conclusion, Conclusion.THIRD_CLASS)
        self.assertEqual(result.actual_metrics["电炉可比单耗"], Decimal("500"))
        self.assertNotIn("燃料系数α", result.calculated_metrics)
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB36561-R000023")
        self.assertEqual(lookup["specification"], "电加热")
        self.assertEqual(lookup["unit"], "kWh/t")
        self.assertEqual(lookup["thresholds"], ["300", "400", "520"])

    def test_heat_treatment_cover_fuel_path_selects_cover_fuel_row(self):
        """罩式炉燃料加热不能复用辊底炉阈值，且仍需联动表9系数。"""
        result = self.evaluate("heat_treatment", {
            "category": "罩式炉", "energy_type": "天然气",
            "equivalent_weight_t": 1, "fuel_consumption": 100,
            "fuel_calorific_value_kjkg": 34541,
        })
        self.assertEqual(result.conclusion, Conclusion.SECOND_CLASS)
        self.assertIn("燃料系数α", result.calculated_metrics)
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB36561-R000026")
        self.assertEqual(lookup["specification"], "燃料加热")
        self.assertEqual(lookup["unit"], "kgce/t")
        self.assertEqual(lookup["thresholds"], ["110", "140", "200"])
        self.assertEqual(lookup["fuel_coefficient_data_id"], "GB36561-T9-05")

    def test_heat_treatment_cover_electric_path_selects_cover_electric_row(self):
        """罩式炉电加热必须使用kWh/t电加热行及其独立阈值。"""
        result = self.evaluate("heat_treatment", {
            "category": "罩式炉", "energy_type": "电力",
            "equivalent_weight_t": 1, "total_electricity_kwh": 450,
        })
        self.assertEqual(result.conclusion, Conclusion.THIRD_CLASS)
        self.assertEqual(result.actual_metrics["电炉可比单耗"], Decimal("450"))
        self.assertNotIn("燃料系数α", result.calculated_metrics)
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB36561-R000025")
        self.assertEqual(lookup["specification"], "电加热")
        self.assertEqual(lookup["unit"], "kWh/t")
        self.assertEqual(lookup["thresholds"], ["330", "370", "450"])

    def test_heat_treatment_natural_gas_table9_upper_boundary_is_closed(self):
        """表9天然气热值41868为闭上限，超出后不得继续套用α。"""
        common = {
            "category": "罩式炉", "energy_type": "天然气",
            "equivalent_weight_t": 1, "fuel_consumption": 100,
        }
        at_upper = self.evaluate("heat_treatment", {
            **common, "fuel_calorific_value_kjkg": Decimal("41868"),
        })
        above_upper = self.evaluate("heat_treatment", {
            **common, "fuel_calorific_value_kjkg": Decimal("41868.0001"),
        })
        self.assertEqual(at_upper.conclusion, Conclusion.THIRD_CLASS)
        self.assertEqual(at_upper.calculated_metrics["燃料系数α"], Decimal("1.1"))
        self.assertEqual(at_upper.lookups[0]["fuel_coefficient_data_id"], "GB36561-T9-05")
        self.assertEqual(at_upper.lookups[0]["fuel_coefficient_condition"], "34541～41868 kJ/m³")
        self.assertEqual(above_upper.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(above_upper.standard_reference["table"], "表9")
        self.assertEqual(above_upper.lookups[0]["data_id"], "GB36561-T9-05")
        self.assertEqual(above_upper.lookups[0]["match_status"], "未命中")
        self.assertEqual(above_upper.lookups[0]["input_fuel_calorific_value"], "41868.0001")
        self.assertNotIn("燃料系数α", above_upper.calculated_metrics)

    def test_heat_treatment_spec_miss_retains_comparable_consumption(self):
        result = self.evaluate("heat_treatment", {
            "category": "箱式多用炉", "energy_type": "电力",
            "equivalent_weight_t": 1, "total_electricity_kwh": 600,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("可比单耗未舍入值", result.calculated_metrics)
        self.assertEqual(result.actual_metrics["电炉可比单耗"], Decimal("600"))
        self.assertTrue(result.lookups)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表8")
        self.assertEqual(lookup["match_status"], "炉型规格未命中或条件不足")
        self.assertEqual(lookup["candidate_count"], 0)
        self.assertEqual(
            [row["data_id"] for row in lookup["candidate_rows"]],
            ["GB36561-R000005", "GB36561-R000006", "GB36561-R000007"],
        )
        self.assertEqual(
            [row["spec"] for row in lookup["candidate_rows"]],
            ["额定功率≤45kW", "45<额定功率≤75kW", "额定功率>75kW"],
        )
        self.assertEqual(lookup["query_conditions"]["rated_power_kw"], "")
        self.assertEqual(lookup["source_page"], 11)
        standard_step = next(step for step in result.trace if step.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], [
            "GB36561-R000005", "GB36561-R000006", "GB36561-R000007",
        ])

    def test_heat_treatment_missing_electricity_retains_unique_standard_lookup(self):
        """缺少电炉能耗时，唯一炉型仍应保留表8阈值和查表来源。"""
        result = self.evaluate("heat_treatment", {
            "category": "传送式连续炉",
            "energy_type": "电力",
            "equivalent_weight_t": 1,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["总耗电量"])
        self.assertEqual(result.actual_metrics, {})
        self.assertEqual(result.calculated_metrics, {})
        self.assertEqual(result.limits, {
            "一等": Decimal("330"),
            "二等": Decimal("390"),
            "三等": Decimal("470"),
        })
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表8")
        self.assertEqual(lookup["match_status"], "命中")
        self.assertEqual(lookup["data_id"], "GB36561-R000001")
        self.assertEqual(lookup["thresholds"], ["330", "390", "470"])
        standard_step = next(step for step in result.trace if step.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], ["GB36561-R000001"])

    def test_heat_treatment_missing_fuel_consumption_retains_coefficient_and_lookup(self):
        """缺少燃料总耗量时，仍应保留表9燃料系数和表8阈值。"""
        result = self.evaluate("heat_treatment", {
            "category": "罩式炉",
            "energy_type": "天然气",
            "equivalent_weight_t": 1,
            "fuel_calorific_value_kjkg": 34541,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["燃料总耗量"])
        self.assertEqual(result.actual_metrics, {})
        self.assertEqual(result.calculated_metrics["燃料系数α"], Decimal("1.1"))
        self.assertEqual(result.comparisons, [])
        self.assertEqual(result.limits, {
            "一等": 110,
            "二等": 140,
            "三等": 200,
        })
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表8")
        self.assertEqual(lookup["match_status"], "命中")
        self.assertEqual(lookup["data_id"], "GB36561-R000026")
        self.assertEqual(lookup["fuel_coefficient_data_id"], "GB36561-T9-05")
        self.assertEqual(lookup["query_conditions"]["fuel_consumption"], "")
        self.assertEqual(lookup["query_conditions"]["fuel_calorific_value_kjkg"], "34541")
        self.assertEqual(lookup["thresholds"], ["110", "140", "200"])
        standard_step = next(step for step in result.trace if step.get("step_type") == "标准查询结果")
        self.assertIn("GB36561-R000026", standard_step["data_ids"])

    def test_heat_treatment_missing_fuel_heat_retains_coefficient_candidates_and_lookup(self):
        """缺少燃料热值时，保留表9候选系数和表8燃料炉阈值。"""
        result = self.evaluate("heat_treatment", {
            "category": "罩式炉",
            "energy_type": "天然气",
            "equivalent_weight_t": 1,
            "fuel_consumption": 100,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["燃料热值"])
        self.assertEqual(result.actual_metrics, {})
        self.assertEqual(result.calculated_metrics, {})
        self.assertEqual(result.comparisons, [])
        self.assertEqual(result.limits, {
            "一等": 110,
            "二等": 140,
            "三等": 200,
        })
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表8")
        self.assertEqual(lookup["match_status"], "命中")
        self.assertEqual(lookup["data_id"], "GB36561-R000026")
        self.assertEqual(lookup["query_conditions"]["fuel_consumption"], "100")
        self.assertEqual(lookup["query_conditions"]["fuel_calorific_value_kjkg"], "")
        self.assertEqual(lookup["fuel_coefficient_match_status"], "燃料热值未提供")
        self.assertEqual(lookup["fuel_coefficient_candidate_data_ids"], ["GB36561-T9-05"])
        self.assertEqual(lookup["fuel_coefficient_candidates"], [{
            "data_id": "GB36561-T9-05",
            "fuel": "天然气",
            "condition": "34541～41868 kJ/m³",
            "candidate_alpha": "1.1",
            "source_page": 12,
            "match_status": "燃料热值未提供",
        }])
        self.assertEqual(lookup["thresholds"], ["110", "140", "200"])
        standard_step = next(step for step in result.trace if step.get("step_type") == "标准查询结果")
        self.assertIn("GB36561-R000026", standard_step["data_ids"])

    def test_heat_treatment_temperature_boundaries_follow_table8_open_closed_endpoints(self):
        common = {
            "category": "热处理电热浴炉",
            "energy_type": "电力",
            "equivalent_weight_t": 1,
            "total_electricity_kwh": 100,
        }
        at_350 = self.evaluate("heat_treatment", {**common, "rated_temperature_c": 350})
        above_350 = self.evaluate("heat_treatment", {**common, "rated_temperature_c": 350.01})
        at_700 = self.evaluate("heat_treatment", {**common, "rated_temperature_c": 700})
        above_700 = self.evaluate("heat_treatment", {**common, "rated_temperature_c": 700.01})
        self.assertEqual(at_350.conclusion, Conclusion.FIRST_CLASS)
        self.assertEqual(above_350.conclusion, Conclusion.FIRST_CLASS)
        self.assertEqual(at_700.conclusion, Conclusion.FIRST_CLASS)
        self.assertEqual(above_700.conclusion, Conclusion.FIRST_CLASS)
        self.assertNotEqual(at_350.lookups[0]["data_id"], above_350.lookups[0]["data_id"])
        self.assertNotEqual(at_700.lookups[0]["data_id"], above_700.lookups[0]["data_id"])

    def test_heat_treatment_temperature_700_open_lower_boundary_changes_grade(self):
        """GB/T 36561表8的>700~1000℃档在700处不含、超过700才切换。"""
        common = {
            "category": "热处理电热浴炉",
            "energy_type": "电力",
            "equivalent_weight_t": 1,
            "total_electricity_kwh": 700,
        }
        at_700 = self.evaluate("heat_treatment", {**common, "rated_temperature_c": Decimal("700")})
        above_700 = self.evaluate("heat_treatment", {**common, "rated_temperature_c": Decimal("700.01")})
        # 700 kWh/t高于>350~700℃档的三等限值500，
        # 但在>700~1000℃档的二等限值850以内。
        self.assertEqual(at_700.conclusion, Conclusion.NOT_COMPLIANT)
        self.assertEqual(above_700.conclusion, Conclusion.SECOND_CLASS)
        self.assertEqual(at_700.lookups[0]["data_id"], "GB36561-R000021")
        self.assertEqual(above_700.lookups[0]["data_id"], "GB36561-R000020")
        self.assertEqual(at_700.lookups[0]["specification"], ">350~700℃")
        self.assertEqual(above_700.lookups[0]["specification"], ">700~1000℃")
        self.assertEqual(at_700.limits["三等"], 500)
        self.assertEqual(above_700.limits["二等"], 850)

    def test_heat_treatment_unknown_fuel_does_not_default_coefficient_to_one(self):
        result = self.evaluate("heat_treatment", {
            "category": "辊底炉", "energy_type": "其他（请备注说明）",
            "equivalent_weight_t": 1, "fuel_consumption": 100,
            "fuel_calorific_value_kjkg": 34541,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("燃料系数", result.explanation)
        self.assertTrue(result.lookups)
        self.assertEqual(result.lookups[0]["table"], "表9")
        self.assertEqual(result.lookups[0]["match_status"], "燃料品种未命中")
        standard_step = next(step for step in result.trace if step.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["clause"], "表9")

    def test_heat_treatment_unknown_energy_containing_electric_does_not_default_to_electricity(self):
        """非法能源文本含“电”时不能绕过能源枚举直接按电炉判级。"""
        result = self.evaluate("heat_treatment", {
            "category": "传送式连续炉", "energy_type": "其他电源",
            "equivalent_weight_t": 1, "total_electricity_kwh": 300,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("燃料总耗量", result.missing_fields)
        self.assertIn("燃料热值", result.missing_fields)
        self.assertNotIn("电炉可比单耗", result.actual_metrics)

    def test_heat_treatment_invalid_standard_fuel_coefficient_returns_trace_instead_of_raising(self):
        """标准表9的α损坏时返回结构化结果，不让单条输入抛异常。"""
        pack_path = ROOT / "src" / "equipeffi" / "resources" / "standards" / "heat_treatment.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        pack["status"] = "active"
        pack["fuel_coefficients"][4]["alpha"] = "不是数值"
        result = HeatTreatmentEvaluator().evaluate({
            "record_id": "TEST-HEAT-INVALID-ALPHA",
            "category": "辊底炉",
            "energy_type": "天然气",
            "equivalent_weight_t": 1,
            "fuel_consumption": 100,
            "fuel_calorific_value_kjkg": 34541,
        }, pack)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("燃料系数", result.explanation)
        self.assertTrue(result.lookups)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表9")
        self.assertEqual(lookup["match_status"], "燃料系数无效")
        self.assertEqual(lookup["data_id"], "GB36561-T9-05")
        self.assertEqual(lookup["input_fuel"], "天然气")
        self.assertEqual(lookup["candidate_alpha"], "不是数值")
        standard_step = next(step for step in result.trace if step.get("step_type") == "标准查询结果")
        self.assertIn("GB36561-T9-05", standard_step["data_ids"])

    def test_heat_treatment_rejects_fuel_heat_outside_table9_interval(self):
        result = self.evaluate("heat_treatment", {
            "category": "辊底炉", "energy_type": "天然气",
            "equivalent_weight_t": 1, "fuel_consumption": 100,
            "fuel_calorific_value_kjkg": 34540,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertIn("燃料热值", result.explanation)
        self.assertTrue(result.lookups)
        self.assertEqual(result.lookups[0]["table"], "表9")
        self.assertEqual(result.lookups[0]["match_status"], "未命中")
        self.assertEqual(result.lookups[0]["input_fuel_calorific_value"], "34540")
        standard_step = next(step for step in result.trace if step.get("step_type") == "标准查询结果")
        self.assertIn("GB36561-T9-05", standard_step["data_ids"])
        self.assertEqual(standard_step["clause"], "表9")
        self.assertEqual(result.standard_reference["clause"], "表9")
        self.assertNotIn("燃料系数α", result.calculated_metrics)

        # 标准包若出现重叠区间，不能任取一个α；但两个候选查表行仍需留在轨迹中。
        from copy import deepcopy
        ambiguous_pack = deepcopy(self.service.standards.get_pack("heat_treatment"))
        ambiguous_pack["fuel_coefficients"] = [
            {"fuel": "天然气", "alpha": 1.1, "condition": "30000～40000 kJ/m³", "source_page": 12},
            {"fuel": "天然气", "alpha": 1.2, "condition": "34000～42000 kJ/m³", "source_page": 12},
        ]
        ambiguous_service = EvaluationService(self.service.standards)
        ambiguous_service._pack_cache["heat_treatment"] = ambiguous_pack
        ambiguous = ambiguous_service.evaluate(DeviceDraft(
            record_id="TEST-heat-treatment-ambiguous-fuel",
            device_type="heat_treatment",
            raw_values={
                "category": "辊底炉", "energy_type": "天然气",
                "equivalent_weight_t": 1, "fuel_consumption": 100,
                "fuel_calorific_value_kjkg": 35000,
            },
        ))
        self.assertEqual(ambiguous.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual([item["match_status"] for item in ambiguous.lookups], ["多重命中", "多重命中"])
        ambiguous_standard = next(step for step in ambiguous.trace if step.get("step_type") == "标准查询结果")
        self.assertEqual(set(ambiguous_standard["data_ids"]), {"GB36561-T9-01", "GB36561-T9-02"})

    def test_heat_treatment_rejects_non_numeric_fuel_heat_without_raising(self):
        result = self.evaluate("heat_treatment", {
            "category": "辊底炉", "energy_type": "天然气",
            "equivalent_weight_t": 1, "fuel_consumption": 100,
            "fuel_calorific_value_kjkg": "待复核",
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("燃料热值", result.missing_fields)

    def test_heat_treatment_rejects_non_numeric_electricity_without_raising(self):
        result = self.evaluate("heat_treatment", {
            "category": "传送式连续炉", "energy_type": "电力",
            "equivalent_weight_t": 1, "total_electricity_kwh": "待复核",
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("总耗电量", result.missing_fields)

    def test_v4_transformer_field_ids_are_accepted_and_traced(self):
        canonical = self.specs["transformer"]["example"]
        v4 = {
            "model": canonical["model"],
            "category": canonical["category"],
            "rated_capacity": canonical["capacity_kva"],
            "core_material": canonical["core_material"],
            "connection": canonical["connection"],
            "no_load_loss": canonical["no_load_loss_w"],
            "load_loss": canonical["load_loss_w"],
        }
        result = self.evaluate("transformer", v4)
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        changes = result.trace[0]["changes"]
        self.assertTrue(any(item.get("target_field") == "capacity_kva" for item in changes))

    def test_v4_transformer_not_applicable_discriminators_match_blank_standard_cells(self):
        result = self.evaluate("transformer", {
            "category": "35kV油浸式三相双绕组无励磁调压电力变压器",
            "rated_capacity": 3150,
            "core_material": "不适用",
            "insulation": "不适用",
            "connection": "不适用",
            "no_load_loss": 1700,
            "load_loss": 21000,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        changes = result.trace[0]["changes"]
        self.assertTrue(any(item.get("field") == "connection" and item.get("value") == "" for item in changes))

    def test_v4_high_voltage_motor_selects_table_from_voltage_and_cooling(self):
        result = self.evaluate("motor_hv", {
            "category": "卧式电动机",
            "rated_voltage": 6,
            "cooling": "IC01",
            "rated_power": 200,
            "poles": 2,
            "rated_speed": 2980,
            "rated_efficiency": 94,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.standard_reference["table"][:2], "表1")
        voltage_change = next(item for item in result.trace[0]["changes"] if item.get("target_field") == "rated_voltage_v")
        self.assertEqual(voltage_change["value"], 6000)

    def test_high_voltage_motor_10kv_routes_to_table2_without_nearest_table_fallback(self):
        """GB 30254-2024的10 kV+IC01离散组应命中表2，而非复用表1。"""
        result = self.evaluate("motor_hv", {
            "category": "卧式电动机",
            "rated_voltage_v": 10000,
            "cooling_method": "IC01",
            "rated_power_kw": 200,
            "poles": 2,
            "rated_efficiency": 93.7,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.standard_reference["table"][:2], "表2")
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"][:2], "表2")
        self.assertEqual(lookup["query_conditions"], {
            "power_kw": "200",
            "dimension": "2",
            "dimension_name": "poles",
        })
        self.assertEqual(lookup["data_ids"], ["GB30254-R000044"])
        self.assertEqual(lookup["source_pages"], "9-11")
        self.assertEqual(result.limits["1级效率_%"], Decimal("93.7"))
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], ["GB30254-R000044"])

    def test_high_voltage_motor_6kv_ic411_routes_to_table5(self):
        """GB 30254-2024的6 kV+IC411应路由到独立的表5冷却组。"""
        result = self.evaluate("motor_hv", {
            "category": "立式电动机",
            "rated_voltage_v": 6000,
            "cooling_method": "IC411",
            "rated_power_kw": 200,
            "poles": 2,
            "rated_efficiency": 94.4,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.standard_reference["table"][:2], "表5")
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"][:2], "表5")
        self.assertEqual(lookup["query_conditions"], {
            "power_kw": "200",
            "dimension": "2",
            "dimension_name": "poles",
        })
        self.assertEqual(lookup["data_ids"], ["GB30254-R000156"])
        self.assertEqual(lookup["source_pages"], "16-17")
        self.assertEqual(result.limits["1级效率_%"], Decimal("94.4"))
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], ["GB30254-R000156"])

    def test_high_voltage_motor_3kv_ic611_routes_to_table3(self):
        """GB 30254-2024的3 kV+IC611应路由到表3冷却组。"""
        result = self.evaluate("motor_hv", {
            "category": "高压三相笼型异步电动机",
            "rated_voltage_v": 3000,
            "cooling_method": "IC611",
            "rated_power_kw": 200,
            "poles": 2,
            "rated_efficiency": 93.4,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.standard_reference["table"][:2], "表3")
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"][:2], "表3")
        self.assertEqual(lookup["query_conditions"], {
            "power_kw": "200",
            "dimension": "2",
            "dimension_name": "poles",
        })
        self.assertEqual(lookup["data_ids"], ["GB30254-R000086"])
        self.assertEqual(lookup["source_pages"], "11-13")
        self.assertEqual(result.limits["1级效率_%"], Decimal("93.4"))
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], ["GB30254-R000086"])

    def test_high_voltage_motor_10kv_ic611_routes_to_table4(self):
        """GB 30254-2024的10 kV+IC611应路由到表4冷却组。"""
        result = self.evaluate("motor_hv", {
            "category": "高压三相笼型异步电动机",
            "rated_voltage_v": 10000,
            "cooling_method": "IC611",
            "rated_power_kw": 200,
            "poles": 2,
            "rated_efficiency": 93.1,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.standard_reference["table"][:2], "表4")
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"][:2], "表4")
        self.assertEqual(lookup["query_conditions"], {
            "power_kw": "200",
            "dimension": "2",
            "dimension_name": "poles",
        })
        self.assertEqual(lookup["data_ids"], ["GB30254-R000121"])
        self.assertEqual(lookup["source_pages"], "14-15")
        self.assertEqual(result.limits["1级效率_%"], Decimal("93.1"))
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], ["GB30254-R000121"])

    def test_high_voltage_motor_10kv_ic411_routes_to_table6(self):
        """GB 30254-2024的10 kV+IC411应路由到表6冷却组。"""
        result = self.evaluate("motor_hv", {
            "category": "高压三相笼型异步电动机",
            "rated_voltage_v": 10000,
            "cooling_method": "IC411",
            "rated_power_kw": 200,
            "poles": 2,
            "rated_efficiency": 94.1,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.standard_reference["table"][:2], "表6")
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"][:2], "表6")
        self.assertEqual(lookup["query_conditions"], {
            "power_kw": "200",
            "dimension": "2",
            "dimension_name": "poles",
        })
        self.assertEqual(lookup["data_ids"], ["GB30254-R000181"])
        self.assertEqual(lookup["source_pages"], "17-18")
        self.assertEqual(result.limits["1级效率_%"], Decimal("94.1"))
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], ["GB30254-R000181"])

    def test_high_voltage_motor_unmatched_poles_keeps_table_candidates(self):
        """高压电动机表5不含12极时应保留离散极数和候选记录。"""
        result = self.evaluate("motor_hv", {
            "category": "卧式电动机",
            "rated_voltage_v": 6000,
            "cooling_method": "IC411",
            "rated_power_kw": 200,
            "poles": 12,
            "rated_efficiency": 95,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertIn("极数", result.explanation)
        self.assertEqual(result.actual_metrics["额定效率_%"], Decimal("95"))
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"][:2], "表5")
        self.assertEqual(lookup["matching"], "功率+极数")
        self.assertEqual(lookup["query_conditions"], {
            "power_kw": "200",
            "dimension": "12",
            "dimension_name": "poles",
        })
        self.assertEqual(lookup["match_status"], "极数档未命中")
        self.assertEqual(lookup["available_dimensions"], ["2", "4", "6", "8"])
        self.assertEqual(lookup["candidate_count"], 25)
        self.assertEqual(lookup["data_ids"][0], "GB30254-R000156")
        self.assertEqual(lookup["data_ids"][-1], "GB30254-R000180")
        self.assertEqual(lookup["source_pages"], "16-17")
        self.assertIn("禁止外推", lookup["standard_rule"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_high_voltage_motor_unsupported_cooling_keeps_candidate_tables(self):
        """已允许的冷却枚举若未被HV标准表覆盖，不能静默丢失查表证据。"""
        result = self.evaluate("motor_hv", {
            "category": "卧式电动机",
            "rated_voltage_v": 6000,
            "cooling_method": "IC86W",
            "rated_power_kw": 200,
            "poles": 2,
            "rated_efficiency": 94,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("冷却方式", result.explanation)
        self.assertEqual(result.actual_metrics["额定效率_%"], Decimal("94"))
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "冷却方式未命中")
        self.assertEqual(lookup["query_conditions"]["rated_voltage_v"], "6000")
        self.assertEqual(lookup["query_conditions"]["cooling_method"], "IC86W")
        self.assertEqual(lookup["candidate_count"], 3)
        self.assertEqual([item["table_no"] for item in lookup["candidate_tables"]], [1, 3, 5])
        self.assertIn("IC01", lookup["candidate_tables"][0]["available_cooling_methods"])
        self.assertIn("GB30254-R000001", lookup["data_ids"])
        self.assertIn("GB30254-R000180", lookup["data_ids"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertIn("GB30254-R000001", standard_step["data_ids"])

    def test_high_voltage_motor_missing_cooling_keeps_candidate_tables(self):
        """额定电压已知但缺少冷却方式时应保留可选表组而不默认选表。"""
        result = self.evaluate("motor_hv", {
            "category": "卧式电动机",
            "rated_voltage_v": 6000,
            "rated_power_kw": 200,
            "poles": 2,
            "rated_efficiency": 94,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("冷却方式", result.explanation)
        self.assertIn("冷却方式", result.missing_fields)
        self.assertEqual(result.actual_metrics["额定效率_%"], Decimal("94"))
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "冷却方式未提供")
        self.assertEqual(lookup["table"], "表1/表3/表5")
        self.assertEqual(lookup["query_conditions"], {
            "rated_voltage_v": "6000",
            "cooling_method": "",
        })
        self.assertEqual(lookup["candidate_count"], 3)
        self.assertEqual([item["table_no"] for item in lookup["candidate_tables"]], [1, 3, 5])
        self.assertEqual(lookup["source_pages"], ["11-13", "16-17", "7-9"])
        self.assertIn("IC01", lookup["candidate_tables"][0]["available_cooling_methods"])
        self.assertIn("GB30254-R000001", lookup["data_ids"])
        self.assertIn("GB30254-R000180", lookup["data_ids"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_high_voltage_motor_missing_poles_retains_candidate_rows_and_missing_field(self):
        """冷却方式已命中表5但缺少极数时应保留候选行并结构化提示极数。"""
        result = self.evaluate("motor_hv", {
            "category": "立式电动机",
            "rated_voltage_v": 6000,
            "cooling_method": "IC411",
            "rated_power_kw": 200,
            "rated_efficiency": 94,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("缺少极数", result.explanation)
        self.assertIn("极数", result.missing_fields)
        self.assertEqual(result.actual_metrics["额定效率_%"], Decimal("94"))
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "极数未提供")
        self.assertEqual(lookup["table"][:2], "表5")
        self.assertEqual(lookup["query_conditions"], {
            "power_kw": "200",
            "dimension": "",
            "dimension_name": "poles",
        })
        self.assertEqual(lookup["available_dimensions"], ["2", "4", "6", "8"])
        self.assertEqual(lookup["candidate_count"], 25)
        self.assertEqual(lookup["data_ids"][0], "GB30254-R000156")
        self.assertEqual(lookup["data_ids"][-1], "GB30254-R000180")
        self.assertEqual(lookup["source_pages"], "16-17")
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_high_voltage_motor_missing_power_retains_candidate_rows_and_actual_efficiency(self):
        """表5路由已确定但额定功率缺失时应保留可选功率档和已填效率。"""
        result = self.evaluate("motor_hv", {
            "category": "立式电动机",
            "rated_voltage_v": 6000,
            "cooling_method": "IC411",
            "poles": 2,
            "rated_efficiency": 94,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("额定功率", result.explanation)
        self.assertIn("额定功率", result.missing_fields)
        self.assertEqual(result.actual_metrics["额定效率_%"], Decimal("94"))
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "额定功率未提供")
        self.assertEqual(lookup["table"][:2], "表5")
        self.assertEqual(lookup["matching"], "功率+极数")
        self.assertEqual(lookup["query_conditions"], {
            "power_kw": "",
            "dimension": "2",
            "dimension_name": "poles",
        })
        self.assertEqual(lookup["available_dimensions"], ["2", "4", "6", "8"])
        self.assertEqual(lookup["available_power_kw"][0], "200.0")
        self.assertEqual(lookup["available_power_kw"][-1], "3150.0")
        self.assertEqual(lookup["candidate_count"], 25)
        self.assertEqual(lookup["data_ids"][0], "GB30254-R000156")
        self.assertEqual(lookup["data_ids"][-1], "GB30254-R000180")
        self.assertEqual(lookup["source_pages"], "16-17")
        self.assertTrue(lookup["no_interpolation"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])

    def test_high_voltage_motor_missing_efficiency_retains_limits_and_lookup(self):
        """表5路由和标准行已确定但额定效率缺失时应保留阈值证据。"""
        result = self.evaluate("motor_hv", {
            "category": "立式电动机",
            "rated_voltage_v": 6000,
            "cooling_method": "IC411",
            "rated_power_kw": 200,
            "poles": 2,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("额定效率", result.explanation)
        self.assertIn("额定效率", result.missing_fields)
        self.assertEqual(result.actual_metrics, {})
        self.assertEqual(result.comparisons, [])
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "命中")
        self.assertEqual(lookup["table"][:2], "表5")
        self.assertEqual(lookup["query_conditions"], {
            "power_kw": "200",
            "dimension": "2",
            "dimension_name": "poles",
        })
        self.assertEqual(lookup["data_ids"], ["GB30254-R000156"])
        self.assertEqual(lookup["source_pages"], "16-17")
        self.assertEqual(result.limits, {
            "1级效率_%": Decimal("94.4"),
            "2级效率_%": Decimal("93.5"),
            "3级效率_%": Decimal("92.7"),
        })
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["data_ids"], lookup["data_ids"])
        self.assertEqual(standard_step["output"], result.limits)

    def test_high_voltage_motor_unmatched_voltage_keeps_all_candidate_tables(self):
        """正数但不在GB 30254离散电压组时应范围外并保留六张候选表。"""
        result = self.evaluate("motor_hv", {
            "category": "卧式电动机",
            "rated_voltage_v": 7000,
            "cooling_method": "IC01",
            "rated_power_kw": 200,
            "poles": 2,
            "rated_efficiency": 94,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertIn("额定电压", result.explanation)
        self.assertTrue(result.lookups)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "额定电压未命中")
        self.assertEqual(lookup["query_conditions"]["rated_voltage_v"], "7000")
        self.assertEqual(lookup["candidate_count"], 6)
        self.assertEqual([item["table_no"] for item in lookup["candidate_tables"]], [1, 2, 3, 4, 5, 6])
        self.assertEqual(len(lookup["data_ids"]), 204)
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(len(standard_step["data_ids"]), 204)

    def test_v4_pmsm_fields_select_pdf_voltage_and_cooling_groups(self):
        result = self.evaluate("motor_pmsm", {
            "category": "变频调速永磁同步电动机",
            "rated_voltage": 380,
            "cooling": "不适用",
            "rated_power": 5.5,
            "poles": 4,
            "rated_speed": 1500,
            "rated_efficiency": 94,
            "efficiency_90_speed": 94,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)

    def test_pmsm_unitless_kv_voltage_selects_medium_voltage_tables(self):
        result = self.evaluate("motor_pmsm", {
            "category": "异步起动永磁同步电动机",
            "rated_voltage": 6,
            "cooling": "IC81W",
            "rated_power": 200,
            "poles": 4,
            "rated_efficiency": 95,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        normalization = next(item for item in result.trace if item.get("step_type") == "输入规范化")
        voltage_change = next(item for item in normalization["changes"] if item.get("target_field") == "voltage_group")
        self.assertEqual(voltage_change["normalized_voltage_v"], Decimal("6000"))
        self.assertEqual(voltage_change["value"], "3kV(3.3kV)/6kV")

    def test_motor_voltage_suffixes_are_not_multiplied_twice(self):
        result = self.evaluate("motor_hv", {
            "category": "卧式电动机",
            "rated_voltage": "6000V",
            "cooling": "IC01",
            "rated_power": 200,
            "poles": 2,
            "rated_speed": 2980,
            "rated_efficiency": 94,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        normalization = next(item for item in result.trace if item.get("step_type") == "输入规范化")
        voltage_change = next(item for item in normalization["changes"] if item.get("target_field") == "rated_voltage_v")
        self.assertEqual(voltage_change["value"], Decimal("6000"))

    def test_pmsm_lookup_trace_has_stable_data_ids_before_activation(self):
        """PMSM激活后也必须能追溯到表、行、维度、等级；不依赖真实包状态。"""
        table = {
            "table_no": 1,
            "table": "表1",
            "dims": ["2", "4"],
            "rows": [
                {"power_kw": 1, "efficiency": {"1": [90, 91]}},
                {"power_kw": 10, "efficiency": {"1": [92, 93]}},
            ],
        }
        result = PmsmEvaluator("motor_pmsm")._power_lookup(table, Decimal("5"), "1", 0)
        self.assertIsNotNone(result)
        trace = result["trace"]
        self.assertEqual(trace["data_ids"], [
            "GB30253-T01-R001-D00-L01",
            "GB30253-T01-R002-D00-L01",
        ])

    def test_pmsm_active_evaluator_rejects_non_numeric_inputs_structurally(self):
        pack = {
            "pack_id": "gb30253_2024_pdf_verified_v1",
            "verified_table_count": 29,
            "status": "active",
            "tables": [],
        }
        result = PmsmEvaluator("motor_pmsm").evaluate(
            {"record_id": "PMSM-BAD", "category": "异步起动", "rated_power_kw": "待复核", "rated_efficiency": 95},
            pack,
        )
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("额定功率不是有效数值", result.explanation)

    def test_pmsm_active_evaluator_rejects_non_numeric_efficiency_structurally(self):
        pack = {
            "pack_id": "gb30253_2024_pdf_verified_v1",
            "verified_table_count": 29,
            "status": "active",
            "tables": [],
        }
        result = PmsmEvaluator("motor_pmsm").evaluate(
            {"record_id": "PMSM-BAD-EFF", "category": "异步起动", "rated_power_kw": 5.5, "rated_efficiency": "待复核"},
            pack,
        )
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("额定效率不是有效数值", result.explanation)

    def test_pmsm_active_evaluator_rejects_unknown_product_category(self):
        pack = {
            "pack_id": "gb30253_2024_pdf_verified_v1",
            "verified_table_count": 29,
            "status": "active",
            "tables": [],
        }
        result = PmsmEvaluator("motor_pmsm").evaluate(
            {"record_id": "PMSM-BAD-CATEGORY", "category": "未知永磁电机", "rated_power_kw": 5.5, "rated_efficiency": 95},
            pack,
        )
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("设备类别不是GB 30253-2024规定", result.explanation)

    def test_pmsm_category_with_known_name_suffix_does_not_default_to_product(self):
        """PMSM设备类别必须精确匹配，未知后缀不得按已知产品子串判级。"""
        for category in (
            "异步起动三相永磁同步电动机（扩展）",
            "变频调速永磁同步电动机（扩展）",
            "电梯用永磁同步电动机（扩展）",
        ):
            with self.subTest(category=category):
                result = self.evaluate("motor_pmsm", {
                    "category": category,
                    "rated_power_kw": 5.5,
                    "poles": 4,
                    "rated_speed_rpm": 1500,
                    "rated_efficiency": 94,
                    "efficiency_at_90pct_speed": 94,
                })
                self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
                self.assertIn("设备类别", result.missing_fields)
                self.assertFalse(result.lookups)

    def test_pmsm_unresolved_discrete_dimension_retains_reported_efficiency(self):
        result = self.evaluate("motor_pmsm", {
            "category": "异步起动永磁同步电动机",
            "rated_power_kw": 5.5,
            "poles": 12,
            "rated_efficiency": 94,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(result.actual_metrics["额定效率_%"], Decimal("94"))

    def test_pmsm_missing_poles_retains_dimension_candidates_and_lookup(self):
        """异步起动永磁电机缺少极数时保留表1离散维度和查表证据。"""
        result = self.evaluate("motor_pmsm", {
            "category": "异步起动永磁同步电动机",
            "rated_power_kw": 5.5,
            "rated_efficiency": 94,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["极数"])
        self.assertEqual(result.actual_metrics["额定效率_%"], Decimal("94"))
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表1")
        self.assertEqual(lookup["match_status"], "极数未提供")
        self.assertEqual(lookup["query_conditions"]["rated_power_kw"], "5.5")
        self.assertEqual(lookup["query_conditions"]["dimension"], "")
        self.assertEqual(lookup["available_dimensions"], ["2", "4", "6", "8", "10", "12", "16"])
        self.assertEqual(lookup["candidate_count"], 7)
        self.assertEqual(len(lookup["candidate_rows"]), 7)
        self.assertTrue(all(row["data_ids"] for row in lookup["candidate_rows"]))
        self.assertTrue(all(row["levels"] for row in lookup["candidate_rows"]))
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertTrue(standard_step["data_ids"])

    def test_pmsm_elevator_missing_speed_retains_speed_bands_and_lookup(self):
        """电梯用永磁电机缺少额定转速时保留表29速度区间查表证据。"""
        result = self.evaluate("motor_pmsm", {
            "category": "电梯用永磁同步电动机",
            "rated_power_kw": 5.5,
            "rated_efficiency": 75,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["额定转速"])
        self.assertEqual(result.actual_metrics["额定效率_%"], Decimal("75"))
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表29")
        self.assertEqual(lookup["match_status"], "额定转速未提供")
        self.assertEqual(lookup["query_conditions"]["rated_power_kw"], "5.5")
        self.assertEqual(lookup["query_conditions"]["dimension"], "")
        self.assertEqual(lookup["query_conditions"]["dimension_name"], "rated_speed_rpm")
        self.assertEqual(lookup["available_dimensions"], [">750", ">400~750", ">250~400", ">180~250", ">140~180", ">100~140", "≤100"])
        self.assertEqual(lookup["candidate_count"], 7)
        self.assertEqual(len(lookup["candidate_rows"]), 7)
        self.assertTrue(all(row["data_ids"] for row in lookup["candidate_rows"]))
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertTrue(standard_step["data_ids"])

    def test_pmsm_variable_speed_missing_speed_retains_three_grade_tables_and_bands(self):
        """变频调速永磁电机缺少额定转速时保留表8～10的全部速度区间。"""
        result = self.evaluate("motor_pmsm", {
            "category": "变频调速永磁同步电动机",
            "rated_power_kw": 5.5,
            "efficiency_at_90pct_speed": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["额定转速"])
        self.assertEqual(result.actual_metrics["90%额定转速效率_%"], Decimal("80"))
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表8/表9/表10")
        self.assertEqual(lookup["match_status"], "额定转速未提供")
        self.assertEqual(lookup["query_conditions"]["rated_power_kw"], "5.5")
        self.assertEqual(lookup["query_conditions"]["dimension"], "")
        self.assertEqual(lookup["query_conditions"]["dimension_name"], "rated_speed_rpm")
        self.assertEqual(lookup["candidate_count"], 3)
        self.assertEqual([item["table"] for item in lookup["candidate_tables"]], ["表8", "表9", "表10"])
        self.assertTrue(all(len(item["available_dimensions"]) == 14 for item in lookup["candidate_tables"]))
        self.assertTrue(all(len(item["candidate_rows"]) == 14 for item in lookup["candidate_tables"]))
        self.assertEqual(len(lookup["data_ids"]), 42)
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(len(standard_step["data_ids"]), 42)

    def test_pmsm_variable_speed_power_miss_retains_three_grade_power_axes(self):
        """变频调速永磁电机功率未命中时保留表8～10功率轴和来源证据。"""
        result = self.evaluate("motor_pmsm", {
            "category": "变频调速永磁同步电动机",
            "rated_power_kw": 0.1,
            "rated_speed_rpm": 1500,
            "efficiency_at_90pct_speed": 80,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(result.actual_metrics["90%额定转速效率_%"], Decimal("80"))
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表8/表9/表10")
        self.assertEqual(lookup["match_status"], "额定功率未命中")
        self.assertEqual(lookup["query_conditions"]["rated_power_kw"], "0.1")
        self.assertEqual(lookup["query_conditions"]["rated_speed_rpm"], "1500")
        self.assertEqual(lookup["candidate_count"], 3)
        self.assertEqual([item["table"] for item in lookup["candidate_tables"]], ["表8", "表9", "表10"])
        self.assertTrue(all(item["candidate_count"] == 28 for item in lookup["candidate_tables"]))
        self.assertTrue(all(len(item["candidate_rows"]) == 28 for item in lookup["candidate_tables"]))
        self.assertEqual(lookup["candidate_tables"][0]["candidate_rows"][0]["data_id"], "GB30253-R000307")
        self.assertEqual(lookup["candidate_tables"][0]["candidate_rows"][-1]["power_rule"], "315≤P≤1250")
        self.assertEqual(len(lookup["data_ids"]), 84)
        self.assertEqual(lookup["source_pages"], ["15", "16", "17", "18", "19", "20"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(len(standard_step["data_ids"]), 84)

    def test_pmsm_variable_speed_power_range_closed_endpoints_keep_boundary_trace(self):
        """表8～10的315≤P≤1250区间两端均应命中并保留结构化端点。"""
        common = {
            "category": "变频调速永磁同步电动机",
            "rated_speed_rpm": 500,
            "efficiency_at_90pct_speed": 100,
        }
        at_lower = self.evaluate("motor_pmsm", {**common, "rated_power_kw": 315})
        at_upper = self.evaluate("motor_pmsm", {**common, "rated_power_kw": 1250})
        below = self.evaluate("motor_pmsm", {**common, "rated_power_kw": "314.9999"})
        above = self.evaluate("motor_pmsm", {**common, "rated_power_kw": "1250.0001"})
        for result in (at_lower, at_upper):
            self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
            self.assertEqual(len(result.lookups), 3)
            self.assertTrue(all(item["match_status"] == "命中" for item in result.lookups))
            self.assertTrue(all(item["power_rule"] == "315≤P≤1250" for item in result.lookups))
            self.assertTrue(all(item["power_boundary"] == {
                "min": 315,
                "max": 1250,
                "min_inclusive": True,
                "max_inclusive": True,
            } for item in result.lookups))
        for result in (below, above):
            self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
            self.assertEqual(result.lookups[0]["match_status"], "额定功率未命中")
            self.assertEqual(result.lookups[0]["candidate_tables"][0]["candidate_rows"][-1]["power_rule"], "315≤P≤1250")

    def test_pmsm_variable_speed_high_voltage_power_open_lower_boundary_keeps_summary(self):
        """表11～13的P>3150严格开下限需汇总保留3150边界候选。"""
        common = {
            "category": "变频调速永磁同步电动机",
            "voltage_group": "3kV(3.3kV)/6kV",
            "cooling_group": "IC81W/IC86W/IC71W(IC3W7)",
            "rated_speed_rpm": 500,
            "efficiency_at_90pct_speed": 100,
        }
        at_open_lower = self.evaluate("motor_pmsm", {**common, "rated_power_kw": 3150})
        above_open_lower = self.evaluate("motor_pmsm", {**common, "rated_power_kw": "3150.0001"})
        self.assertEqual(at_open_lower.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(at_open_lower.limits, {})
        self.assertEqual(at_open_lower.comparisons, [])
        self.assertEqual(len(at_open_lower.lookups), 1)
        miss_lookup = at_open_lower.lookups[0]
        self.assertEqual(miss_lookup["table"], "表11/表12/表13")
        self.assertEqual(miss_lookup["match_status"], "额定功率未命中")
        self.assertEqual(miss_lookup["power_boundary_candidates"], [
            {
                "table": "表11",
                "data_id": "GB30253-R000499",
                "power_rule": "P>3150",
                "min": 3150,
                "max": None,
                "min_inclusive": False,
                "max_inclusive": True,
            },
            {
                "table": "表12",
                "data_id": "GB30253-R000549",
                "power_rule": "P>3150",
                "min": 3150,
                "max": None,
                "min_inclusive": False,
                "max_inclusive": True,
            },
            {
                "table": "表13",
                "data_id": "GB30253-R000599",
                "power_rule": "P>3150",
                "min": 3150,
                "max": None,
                "min_inclusive": False,
                "max_inclusive": True,
            },
        ])
        self.assertEqual(above_open_lower.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(len(above_open_lower.lookups), 3)
        self.assertTrue(all(item["power_boundary"] == {
            "min": 3150,
            "max": None,
            "min_inclusive": False,
            "max_inclusive": True,
        } for item in above_open_lower.lookups))

    def test_pmsm_variable_speed_second_cooling_group_power_miss_names_tables(self):
        """表14～16功率未命中时说明必须引用实际表组，而非写死表8～10。"""
        result = self.evaluate("motor_pmsm", {
            "category": "变频调速永磁同步电动机",
            "voltage_group": "3kV(3.3kV)/6kV",
            "cooling_group": "IC411/IC416",
            "rated_power_kw": 100,
            "rated_speed_rpm": 500,
            "efficiency_at_90pct_speed": 100,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(len(result.lookups), 1)
        lookup = result.lookups[0]
        self.assertEqual(lookup["table"], "表14/表15/表16")
        self.assertEqual(lookup["match_status"], "额定功率未命中")
        self.assertEqual(lookup["candidate_count"], 3)
        self.assertEqual(
            [item["table"] for item in lookup["candidate_tables"]],
            ["表14", "表15", "表16"],
        )
        self.assertTrue(all(item["candidate_count"] == 25 for item in lookup["candidate_tables"]))
        self.assertEqual(lookup["power_boundary_candidates"], [
            {
                "table": "表14",
                "data_id": "GB30253-R000649",
                "power_rule": "P>3150",
                "min": 3150,
                "max": None,
                "min_inclusive": False,
                "max_inclusive": True,
            },
            {
                "table": "表15",
                "data_id": "GB30253-R000699",
                "power_rule": "P>3150",
                "min": 3150,
                "max": None,
                "min_inclusive": False,
                "max_inclusive": True,
            },
            {
                "table": "表16",
                "data_id": "GB30253-R000749",
                "power_rule": "P>3150",
                "min": 3150,
                "max": None,
                "min_inclusive": False,
                "max_inclusive": True,
            },
        ])
        self.assertEqual(
            lookup["interpolation_blocked"],
            "目标功率不在表14/表15/表16的标准功率档或功率区间内",
        )
        self.assertIn("表14/表15/表16", result.explanation)
        self.assertNotIn("表8～表10", result.explanation)

    def test_pmsm_structural_dash_preserves_lookup_trace(self):
        """表1其他已复核的结构性“—”也必须保留原文查表证据。"""
        result = self.evaluate("motor_pmsm", {
            "category": "异步起动永磁同步电动机",
            "rated_power_kw": 5.5,
            "poles": 12,
            "rated_efficiency": 94,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(len(result.lookups), 3)
        self.assertEqual(
            [item["level"] for item in result.lookups],
            ["1", "2", "3"],
        )
        self.assertTrue(all(item.get("no_data") is True for item in result.lookups))
        self.assertTrue(all(item.get("standard_marker") == "—" for item in result.lookups))
        self.assertTrue(all(item.get("data_id") for item in result.lookups))
        self.assertIn("标准原文", result.explanation)

    def test_pmsm_normal_result_preserves_standard_table_clause(self):
        """永磁电机正常结果和轨迹都应保留实际命中的标准表题。"""
        result = self.evaluate("motor_pmsm", dict(self.specs["motor_pmsm"]["example"]))
        self.assertTrue(result.standard_reference["table"])
        self.assertEqual(result.standard_reference["clause"], result.standard_reference["table"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(standard_step["clause"], result.standard_reference["table"])

    def test_v4_pump_fields_and_full_category_are_accepted(self):
        result = self.evaluate("pump_water", {
            "category": "单级双吸清水离心泵",
            "suction": "双吸",
            "flow": 100,
            "head": 50,
            "speed": 2900,
            "power": 20,
            "stages": 1,
            "efficiency": 80,
        })
        self.assertIn(result.conclusion, {Conclusion.LEVEL_1, Conclusion.LEVEL_2, Conclusion.LEVEL_3, Conclusion.NOT_COMPLIANT})
        self.assertEqual(result.calculated_metrics["计算流量_m3/h"], 50)

    def test_v4_boiler_fields_and_roman_fuel_class_are_accepted(self):
        result = self.evaluate("boiler", {
            "category": "蒸汽锅炉",
            "combustion": "层状燃烧",
            "fuel": "烟煤",
            "fuel_class": "II类",
            "condensing": "否",
            "evaporation": 10,
            "lhv": 19000,
            "vdaf": 25,
            "design_efficiency": 90,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)

    def test_v4_heat_pump_water_heater_combines_small_capacity_methods(self):
        result = self.evaluate("heat_pump_water_heater", {
            "category": "普通型",
            "heating_method": "一次加热式",
            "with_pump": "否",
            "heating_capacity": 5,
            "rated_power": 1.2,
            "cop": 4.6,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)

    def test_heat_pump_water_heater_ten_kw_boundary_and_five_level_equality(self):
        """10 kW进入标准的另一容量档，等于5级阈值仍应判为5级。"""
        result = self.evaluate("heat_pump_water_heater", {
            "category": "普通型",
            "heating_method": "循环加热式",
            "with_pump": "否",
            "heating_capacity": 10,
            "rated_power": 2.4,
            "cop": 3.7,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_5)
        self.assertEqual(result.standard_reference["table"], "表1")
        self.assertEqual(result.limits["1级性能系数COP"], 4.6)
        self.assertEqual(result.limits["5级性能系数COP"], 3.7)
        self.assertTrue(any(item.get("data_id") == "GB29541-T1-05" for item in result.lookups))

    def test_heat_pump_water_heater_ten_kw_inclusive_band_is_preserved(self):
        """表1的循环加热带泵档从10 kW起含下限，证据不得写成严格大于。"""
        result = self.evaluate("heat_pump_water_heater", {
            "category": "普通型",
            "heating_method": "循环加热式",
            "with_pump": "是",
            "heating_capacity": 10,
            "rated_power": 2.4,
            "cop": 3.6,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_5)
        self.assertEqual(result.lookups[0]["data_id"], "GB29541-T1-06")
        self.assertEqual(result.lookups[0]["capacity_band"], "heating_capacity_kw>=10")
        self.assertEqual(result.calculated_metrics["容量分档"], "heating_capacity_kw>=10")

    def test_heat_pump_water_heater_missing_cop_keeps_capacity_lookup_context(self):
        """缺少COP早退时仍须保留已命中的10 kW容量分档证据。"""
        result = self.evaluate("heat_pump_water_heater", {
            "category": "普通型",
            "heating_method": "循环加热式",
            "with_pump": "是",
            "heating_capacity": 10,
            "rated_power": 2.4,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["性能系数COP"])
        self.assertEqual(result.lookups[0]["data_id"], "GB29541-T1-06")
        self.assertEqual(result.lookups[0]["capacity_band"], "heating_capacity_kw>=10")
        self.assertTrue(any(item.get("step_type") == "标准查询结果" for item in result.trace))

    def test_heat_pump_water_heater_invalid_cop_keeps_raw_value_in_lookup(self):
        """非法COP早退时保留原始文本，且不把它伪装成数值指标。"""
        result = self.evaluate("heat_pump_water_heater", {
            "category": "普通型",
            "heating_method": "循环加热式",
            "with_pump": "是",
            "heating_capacity": 10,
            "rated_power": 2.4,
            "cop": "4．0",  # 全角小数点，当前数值解析不能可靠解释
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["性能系数COP"])
        self.assertEqual(result.actual_metrics, {})
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB29541-T1-06")
        self.assertEqual(lookup["provided_metric_name"], "性能系数COP")
        self.assertEqual(lookup["provided_metric_value"], "4．0")
        self.assertEqual(lookup["match_status"], "设计指标数值无效")
        self.assertEqual(lookup["capacity_band"], "heating_capacity_kw>=10")

    def test_heat_pump_water_heater_zero_cop_keeps_raw_value_in_lookup(self):
        """COP为零时保留原始零值，并明确标记非正数早退。"""
        result = self.evaluate("heat_pump_water_heater", {
            "category": "普通型",
            "heating_method": "循环加热式",
            "with_pump": "是",
            "heating_capacity": 10,
            "rated_power": 2.4,
            "cop": 0,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["性能系数COP"])
        self.assertEqual(result.actual_metrics, {})
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB29541-T1-06")
        self.assertEqual(lookup["provided_metric_name"], "性能系数COP")
        self.assertEqual(lookup["provided_metric_value"], 0)
        self.assertEqual(lookup["match_status"], "设计指标数值非正")
        self.assertEqual(lookup["capacity_band"], "heating_capacity_kw>=10")

    def test_v4_duct_ac_converts_kw_and_dynamic_metric(self):
        result = self.evaluate("duct_ac", {
            "category": "风管送风式空调（热泵）机组",
            "cooling": "风冷式",
            "mode": "单冷型",
            "enthalpy": "不适用",
            "cooling_capacity": 5,
            "rated_power": 1.2,
            "indicator_name": "SEER",
            "indicator_value": 4.2,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(str(result.actual_metrics["SEER"]), "4.2")

    def test_duct_ac_open_capacity_lower_bound_is_preserved(self):
        """GB 37479表1中7100 W以上档位的下限为开区间。"""
        result = self.evaluate("duct_ac", {
            "product_type": "风管送风式机组",
            "cooling_source": "风冷式",
            "mode": "单冷型",
            "cooling_capacity": 7.1001,
            "seer": 3.0,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_3)
        self.assertEqual(result.lookups[0]["data_id"], "GB37479-T1-02")
        self.assertEqual(result.lookups[0]["capacity_band"], "7100<cooling_capacity_w<=14000")
        self.assertEqual(result.calculated_metrics["容量分档"], "7100<cooling_capacity_w<=14000")

    def test_duct_ac_water_iplv_open_capacity_lower_bound_keeps_boundary_evidence(self):
        """GB 37479表1水冷IPLV档位的14 000 W下限为开区间，并保留结构化边界证据。"""
        result = self.evaluate("duct_ac", {
            "product_type": "风管送风式机组",
            "cooling_source": "水冷式",
            "cooling_capacity": 14.0001,
            "iplv": 3.3,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_3)
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB37479-T1-10")
        self.assertEqual(lookup["metric_name"], "IPLV")
        self.assertEqual(lookup["thresholds"], [4.0, 3.8, 3.3])
        self.assertEqual(lookup["capacity_band"], "cooling_capacity_w>14000")
        self.assertEqual(lookup["capacity_boundary"], {
            "metric": "cooling_capacity_w",
            "min": 14000,
            "max": None,
            "min_inclusive": False,
            "max_inclusive": True,
        })
        self.assertEqual(result.calculated_metrics["容量分档"], "cooling_capacity_w>14000")
        self.assertEqual(result.standard_reference["table"], "表1")

    def test_duct_ac_heat_pump_apf_7100w_boundary_switches_to_open_lower_band(self):
        """GB 37479表1热泵型APF在7100 W处仍属上档，超过7100 W才进入开下限档。"""
        at_boundary = self.evaluate("duct_ac", {
            "product_type": "风管送风式机组",
            "cooling_source": "风冷式",
            "mode": "热泵型",
            "cooling_capacity": 7.1,
            "apf": 2.9,
        })
        self.assertEqual(at_boundary.conclusion, Conclusion.LEVEL_3)
        at_lookup = at_boundary.lookups[0]
        self.assertEqual(at_lookup["data_id"], "GB37479-T1-05")
        self.assertEqual(at_lookup["capacity_band"], "cooling_capacity_w<=7100")
        self.assertEqual(at_lookup["capacity_boundary"], {
            "metric": "cooling_capacity_w",
            "min": None,
            "max": 7100,
            "min_inclusive": True,
            "max_inclusive": True,
        })

        above_boundary = self.evaluate("duct_ac", {
            "product_type": "风管送风式机组",
            "cooling_source": "风冷式",
            "mode": "热泵型",
            "cooling_capacity": 7.1001,
            "apf": 2.8,
        })
        self.assertEqual(above_boundary.conclusion, Conclusion.LEVEL_3)
        above_lookup = above_boundary.lookups[0]
        self.assertEqual(above_lookup["data_id"], "GB37479-T1-06")
        self.assertEqual(above_lookup["capacity_band"], "7100<cooling_capacity_w<=14000")
        self.assertEqual(above_lookup["capacity_boundary"]["min"], 7100)
        self.assertFalse(above_lookup["capacity_boundary"]["min_inclusive"])
        self.assertEqual(above_lookup["thresholds"], [3.6, 3.2, 2.8])

    def test_duct_ac_indicator_name_mismatch_does_not_silently_judge(self):
        """填写的指标名称与标准行不一致时，不能把通用值当成标准指标判级。"""
        values = {
            "category": "风管送风式空调（热泵）机组",
            "cooling": "风冷式",
            "mode": "单冷型",
            "enthalpy": "不适用",
            "cooling_capacity": 5,
            "rated_power": 1.2,
            # 该容量/型式标准行要求SEER；EER是错误的指标名称。
            "indicator_name": "EER",
            "indicator_value": 4.2,
        }
        result = self.evaluate("duct_ac", values)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("设计指标", result.explanation)
        self.assertIn("SEER", result.explanation)
        self.assertEqual(result.missing_fields, ["SEER"])
        self.assertEqual(result.lookups[0]["data_id"], "GB37479-T1-01")
        self.assertEqual(result.lookups[0]["provided_metric_name"], "EER")
        self.assertEqual(str(result.lookups[0]["provided_metric_value"]), "4.2")
        self.assertEqual(str(result.actual_metrics["EER"]), "4.2")

    def test_v4_unitary_ac_combines_cooling_and_category(self):
        result = self.evaluate("unitary_ac", {
            "category": "普通单元式空调机",
            "cooling": "风冷式",
            "mode": "单冷型",
            "cooling_capacity": 10,
            "rated_power": 2,
            "indicator_name": "SEER",
            "indicator_value": 4.5,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)

    def test_unitary_ac_full_category_and_cooling_conflict_keeps_candidates(self):
        """完整类别与冷却方式冲突时不能静默套用错误标准行。"""
        result = self.evaluate("unitary_ac", {
            # GB 19576表1分别列出风冷式和水冷式单元式空调机；
            # 这里故意让完整类别与独立冷却方式相反。
            "category": "风冷式单元式空调机",
            "cooling": "水冷式",
            "mode": "单冷型",
            "cooling_capacity": 10,
            "rated_power": 2,
            "indicator_name": "SEER",
            "indicator_value": 4.5,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("冷却方式", result.explanation)
        self.assertIn("冲突", result.explanation)
        self.assertTrue(result.missing_fields)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "类别与冷却方式冲突")
        self.assertEqual(lookup["conflict_fields"], ["category", "cooling_source"])
        self.assertGreaterEqual(lookup["candidate_count"], 2)
        self.assertIn("GB19576-T1-01", lookup["candidate_data_ids"])
        self.assertIn("GB19576-T1-06", lookup["candidate_data_ids"])
        self.assertIn("PDF第3-4页", lookup["source_pages"])
        self.assertEqual(str(result.actual_metrics["SEER"]), "4.5")

    def test_unitary_ac_water_capacity_below_minimum_is_out_of_scope(self):
        """GB 19576表1水冷单元式空调机低于7 kW不在标准容量范围。"""
        result = self.evaluate("unitary_ac", {
            "category": "水冷式单元式空调机",
            "cooling_capacity": 6.9999,
            "iplv": 4.0,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertIn("未落入", result.explanation)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "容量超出标准范围")
        self.assertEqual(lookup["candidate_data_ids"], ["GB19576-T1-05", "GB19576-T1-06"])
        self.assertEqual(lookup["input_values"]["cooling_capacity_w"], "6999.9000")
        self.assertEqual(lookup["source_clause"], "表1")
        self.assertEqual(lookup["capacity_boundary_candidates"], [
            {
                "data_id": "GB19576-T1-05",
                "min": 14000,
                "max": None,
                "min_inclusive": False,
                "max_inclusive": True,
            },
            {
                "data_id": "GB19576-T1-06",
                "min": 7000,
                "max": 14000,
                "min_inclusive": True,
                "max_inclusive": True,
            },
        ])

    def test_unitary_ac_water_wrong_indicator_name_keeps_iplv_lookup(self):
        """水冷单元式空调机要求IPLV时，错误SEER不能被静默判级。"""
        result = self.evaluate("unitary_ac", {
            "category": "水冷式单元式空调机",
            "cooling_capacity": 10,
            "indicator_name": "SEER",
            "indicator_value": 4.5,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("IPLV", result.explanation)
        self.assertEqual(result.missing_fields, ["IPLV"])
        self.assertEqual(result.actual_metrics["SEER"], Decimal("4.5"))
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19576-T1-06")
        self.assertEqual(lookup["metric_name"], "IPLV")
        self.assertEqual(lookup["provided_metric_name"], "SEER")
        self.assertEqual(str(lookup["provided_metric_value"]), "4.5")
        self.assertEqual(lookup["match_status"], "设计指标名称不匹配")
        self.assertEqual(lookup["capacity_band"], "7000<=cooling_capacity_w<=14000")
        self.assertEqual(lookup["capacity_boundary"], {
            "metric": "cooling_capacity_w",
            "min": 7000,
            "max": 14000,
            "min_inclusive": True,
            "max_inclusive": True,
        })

    def test_unitary_ac_water_missing_iplv_keeps_capacity_lookup(self):
        """水冷单元式空调机IPLV缺失时保留容量查表证据并明确早退状态。"""
        result = self.evaluate("unitary_ac", {
            "category": "水冷式单元式空调机",
            "cooling_capacity": 10,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["IPLV"])
        self.assertEqual(result.actual_metrics, {})
        self.assertEqual(result.calculated_metrics, {})
        self.assertEqual(result.limits, {})
        self.assertEqual(result.comparisons, [])
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19576-T1-06")
        self.assertEqual(lookup["table"], "表1")
        self.assertEqual(lookup["source_page"], "PDF第3-4页")
        self.assertEqual(lookup["metric_name"], "IPLV")
        self.assertEqual(lookup["thresholds"], [4.0, 3.7, 3.3])
        self.assertEqual(lookup["capacity_band"], "7000<=cooling_capacity_w<=14000")
        self.assertEqual(lookup["capacity_boundary"], {
            "metric": "cooling_capacity_w",
            "min": 7000,
            "max": 14000,
            "min_inclusive": True,
            "max_inclusive": True,
        })
        self.assertEqual(lookup["provided_metric_name"], "IPLV")
        self.assertIsNone(lookup["provided_metric_value"])
        self.assertEqual(lookup["match_status"], "设计指标缺失")

    def test_unitary_ac_water_iplv_equal_level3_threshold_passes(self):
        """GB 19576表1水冷IPLV等于3级阈值时应判为3级。"""
        result = self.evaluate("unitary_ac", {
            "category": "水冷式单元式空调机",
            "cooling_capacity": 10,
            "iplv": 3.3,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_3)
        self.assertEqual(result.actual_metrics["IPLV"], Decimal("3.3"))
        self.assertEqual(result.limits, {
            "1级IPLV": 4.0,
            "2级IPLV": 3.7,
            "3级IPLV": 3.3,
        })
        self.assertTrue(any(
            item["level"] == "3级" and item["passed"] and item["direction"] == ">="
            for item in result.comparisons
        ))
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19576-T1-06")
        self.assertEqual(lookup["capacity_band"], "7000<=cooling_capacity_w<=14000")
        self.assertEqual(lookup["capacity_boundary"], {
            "metric": "cooling_capacity_w",
            "min": 7000,
            "max": 14000,
            "min_inclusive": True,
            "max_inclusive": True,
        })

    def test_unitary_ac_air_single_cold_seer_equal_level3_threshold_passes(self):
        """GB 19576表1风冷单冷型SEER等于3级阈值时应判为3级。"""
        result = self.evaluate("unitary_ac", {
            "category": "风冷式单元式空调机",
            "mode": "单冷型",
            "cooling_capacity": 10,
            "seer": 2.9,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_3)
        self.assertEqual(result.actual_metrics["SEER"], Decimal("2.9"))
        self.assertEqual(result.limits, {
            "1级SEER": 4.5,
            "2级SEER": 3.8,
            "3级SEER": 2.9,
        })
        self.assertTrue(any(
            item["level"] == "3级" and item["passed"] and item["direction"] == ">="
            for item in result.comparisons
        ))
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19576-T1-01")
        self.assertEqual(lookup["metric_name"], "SEER")
        self.assertEqual(lookup["capacity_band"], "7000<=cooling_capacity_w<=14000")
        self.assertEqual(lookup["capacity_boundary"], {
            "metric": "cooling_capacity_w",
            "min": 7000,
            "max": 14000,
            "min_inclusive": True,
            "max_inclusive": True,
        })

    def test_unitary_ac_air_single_cold_seer_below_level3_is_not_compliant(self):
        """GB 19576表1风冷单冷型SEER低于3级阈值时应判为未达标。"""
        result = self.evaluate("unitary_ac", {
            "category": "风冷式单元式空调机",
            "mode": "单冷型",
            "cooling_capacity": 10,
            "seer": 2.89,
        })
        self.assertEqual(result.conclusion, Conclusion.NOT_COMPLIANT)
        self.assertEqual(result.actual_metrics["SEER"], Decimal("2.89"))
        self.assertEqual(result.limits["3级SEER"], 2.9)
        self.assertTrue(all(item["passed"] is False for item in result.comparisons))
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19576-T1-01")
        self.assertEqual(lookup["metric_name"], "SEER")
        self.assertEqual(lookup["capacity_band"], "7000<=cooling_capacity_w<=14000")

    def test_unitary_ac_air_single_cold_seer_14000w_switches_to_open_lower_band(self):
        """GB 19576表1风冷单冷型SEER在14 000 W处按闭上限/开下限切档。"""
        at_boundary = self.evaluate("unitary_ac", {
            "category": "风冷式单元式空调机",
            "mode": "单冷型",
            "cooling_capacity": 14,
            "seer": 2.9,
        })
        self.assertEqual(at_boundary.conclusion, Conclusion.LEVEL_3)
        at_lookup = at_boundary.lookups[0]
        self.assertEqual(at_lookup["data_id"], "GB19576-T1-01")
        self.assertEqual(at_lookup["capacity_band"], "7000<=cooling_capacity_w<=14000")
        self.assertEqual(at_lookup["capacity_boundary"], {
            "metric": "cooling_capacity_w",
            "min": 7000,
            "max": 14000,
            "min_inclusive": True,
            "max_inclusive": True,
        })
        self.assertEqual(at_lookup["thresholds"], [4.5, 3.8, 2.9])

        above_boundary = self.evaluate("unitary_ac", {
            "category": "风冷式单元式空调机",
            "mode": "单冷型",
            "cooling_capacity": 14.0001,
            "seer": 2.7,
        })
        self.assertEqual(above_boundary.conclusion, Conclusion.LEVEL_3)
        above_lookup = above_boundary.lookups[0]
        self.assertEqual(above_lookup["data_id"], "GB19576-T1-02")
        self.assertEqual(above_lookup["capacity_band"], "cooling_capacity_w>14000")
        self.assertEqual(above_lookup["capacity_boundary"], {
            "metric": "cooling_capacity_w",
            "min": 14000,
            "max": None,
            "min_inclusive": False,
            "max_inclusive": True,
        })
        self.assertEqual(above_lookup["thresholds"], [3.6, 3.0, 2.7])

    def test_unitary_ac_computer_room_air_aeer_equal_level3_threshold_passes(self):
        """GB 19576表1计算机房风冷AEER等于3级阈值时应判为3级。"""
        result = self.evaluate("unitary_ac", {
            "category": "计算机和数据处理机房用单元式空调机",
            "cooling": "风冷式",
            "aeer": 3.0,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_3)
        self.assertEqual(result.actual_metrics["AEER"], Decimal("3.0"))
        self.assertEqual(result.limits, {
            "1级AEER": 4.0,
            "2级AEER": 3.6,
            "3级AEER": 3.0,
        })
        self.assertTrue(any(
            item["level"] == "3级" and item["passed"] and item["direction"] == ">="
            for item in result.comparisons
        ))
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19576-T1-07")
        self.assertEqual(lookup["metric_name"], "AEER")
        self.assertEqual(lookup["thresholds"], [4.0, 3.6, 3.0])
        self.assertEqual(lookup["query_conditions"], {
            "category": "计算机和数据处理机房用单元式空调机",
            "cooling_source": "风冷式",
        })

    def test_unitary_ac_computer_room_water_aeer_equal_level3_threshold_passes(self):
        """GB 19576表1计算机房水冷AEER等于3级阈值时应判为3级。"""
        result = self.evaluate("unitary_ac", {
            "category": "计算机和数据处理机房用单元式空调机",
            "cooling": "水冷式",
            "aeer": 3.5,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_3)
        self.assertEqual(result.actual_metrics["AEER"], Decimal("3.5"))
        self.assertEqual(result.limits, {
            "1级AEER": 4.2,
            "2级AEER": 4.0,
            "3级AEER": 3.5,
        })
        self.assertTrue(any(
            item["level"] == "3级" and item["passed"] and item["direction"] == ">="
            for item in result.comparisons
        ))
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19576-T1-08")
        self.assertEqual(lookup["metric_name"], "AEER")
        self.assertEqual(lookup["thresholds"], [4.2, 4.0, 3.5])
        self.assertEqual(lookup["query_conditions"], {
            "category": "计算机和数据处理机房用单元式空调机",
            "cooling_source": "水冷式",
        })

    def test_unitary_ac_computer_room_water_aeer_below_level3_is_not_compliant(self):
        """GB 19576表1计算机房水冷AEER低于3级阈值时应判为未达标。"""
        result = self.evaluate("unitary_ac", {
            "category": "计算机和数据处理机房用单元式空调机",
            "cooling": "水冷式",
            "aeer": 3.49,
        })
        self.assertEqual(result.conclusion, Conclusion.NOT_COMPLIANT)
        self.assertEqual(result.actual_metrics["AEER"], Decimal("3.49"))
        self.assertEqual(result.limits["3级AEER"], 3.5)
        self.assertTrue(all(item["passed"] is False for item in result.comparisons))
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19576-T1-08")
        self.assertEqual(lookup["query_conditions"]["cooling_source"], "水冷式")

    def test_unitary_ac_computer_room_air_aeer_below_level3_is_not_compliant(self):
        """GB 19576表1计算机房风冷AEER低于3级阈值时应判为未达标。"""
        result = self.evaluate("unitary_ac", {
            "category": "计算机和数据处理机房用单元式空调机",
            "cooling": "风冷式",
            "aeer": 2.99,
        })
        self.assertEqual(result.conclusion, Conclusion.NOT_COMPLIANT)
        self.assertEqual(result.actual_metrics["AEER"], Decimal("2.99"))
        self.assertEqual(result.limits["3级AEER"], 3.0)
        self.assertTrue(all(item["passed"] is False for item in result.comparisons))
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19576-T1-07")
        self.assertEqual(lookup["query_conditions"]["cooling_source"], "风冷式")

    def test_unitary_ac_constant_temperature_humidity_aeer_equal_level3_threshold_passes(self):
        """GB 19576表1恒温恒湿型AEER等于3级阈值时应判为3级。"""
        result = self.evaluate("unitary_ac", {
            "category": "恒温恒湿型单元式空气调节机",
            "aeer": 3.0,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_3)
        self.assertEqual(result.actual_metrics["AEER"], Decimal("3.0"))
        self.assertEqual(result.limits, {
            "1级AEER": 4.0,
            "2级AEER": 3.7,
            "3级AEER": 3.0,
        })
        self.assertTrue(any(
            item["level"] == "3级" and item["passed"] and item["direction"] == ">="
            for item in result.comparisons
        ))
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19576-T1-10")
        self.assertEqual(lookup["metric_name"], "AEER")
        self.assertEqual(lookup["thresholds"], [4.0, 3.7, 3.0])
        self.assertEqual(lookup["query_conditions"], {
            "category": "恒温恒湿型单元式空气调节机",
        })

    def test_unitary_ac_constant_temperature_humidity_aeer_below_level3_is_not_compliant(self):
        """GB 19576表1恒温恒湿型AEER低于3级阈值时应判为未达标。"""
        result = self.evaluate("unitary_ac", {
            "category": "恒温恒湿型单元式空气调节机",
            "aeer": 2.99,
        })
        self.assertEqual(result.conclusion, Conclusion.NOT_COMPLIANT)
        self.assertEqual(result.actual_metrics["AEER"], Decimal("2.99"))
        self.assertEqual(result.limits["3级AEER"], 3.0)
        self.assertTrue(all(item["passed"] is False for item in result.comparisons))
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19576-T1-10")
        self.assertEqual(lookup["metric_name"], "AEER")
        self.assertEqual(lookup["thresholds"], [4.0, 3.7, 3.0])

    def test_unitary_ac_telecom_station_cop_equal_level3_threshold_passes(self):
        """GB 19576表1通讯基站机组COP等于3级阈值时应判为3级。"""
        at_level3 = self.evaluate("unitary_ac", {
            "category": "通讯基站用单元式空气调节机",
            "cop": 2.8,
        })
        self.assertEqual(at_level3.conclusion, Conclusion.LEVEL_3)
        self.assertEqual(at_level3.actual_metrics["COP"], Decimal("2.8"))
        self.assertEqual(at_level3.limits, {
            "1级COP": 3.2,
            "2级COP": 3.0,
            "3级COP": 2.8,
        })
        lookup = at_level3.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19576-T1-09")
        self.assertEqual(lookup["metric_name"], "COP")
        self.assertEqual(lookup["thresholds"], [3.2, 3.0, 2.8])
        self.assertEqual(lookup["capacity_band"], "")
        self.assertEqual(lookup["capacity_boundary"], {})
        self.assertTrue(any(item["level"] == "3级" and item["passed"] for item in at_level3.comparisons))

        below_level3 = self.evaluate("unitary_ac", {
            "category": "通讯基站用单元式空气调节机",
            "cop": 2.79,
        })
        self.assertEqual(below_level3.conclusion, Conclusion.NOT_COMPLIANT)
        self.assertFalse(next(item for item in below_level3.comparisons if item["level"] == "3级")["passed"])

    def test_unitary_ac_telecom_station_invalid_cop_keeps_raw_lookup(self):
        """通讯基站COP非法文本早退时保留原值，不伪装成可比较数值。"""
        result = self.evaluate("unitary_ac", {
            "category": "通讯基站用单元式空气调节机",
            "cop": "3．0",
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["COP"])
        self.assertEqual(result.actual_metrics, {})
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19576-T1-09")
        self.assertEqual(lookup["provided_metric_name"], "COP")
        self.assertEqual(lookup["provided_metric_value"], "3．0")
        self.assertEqual(lookup["match_status"], "设计指标数值无效")
        self.assertEqual(lookup["thresholds"], [3.2, 3.0, 2.8])
        self.assertEqual(lookup["capacity_band"], "")
        self.assertEqual(lookup["capacity_boundary"], {})

    def test_unitary_ac_telecom_station_missing_cop_keeps_standard_lookup(self):
        """通讯基站COP缺失时不能补默认值，已命中的标准行必须保留。"""
        result = self.evaluate("unitary_ac", {
            "category": "通讯基站用单元式空气调节机",
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["COP"])
        self.assertEqual(result.actual_metrics, {})
        self.assertEqual(result.calculated_metrics, {})
        self.assertEqual(result.limits, {})
        self.assertEqual(result.comparisons, [])
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB19576-T1-09")
        self.assertEqual(lookup["metric_name"], "COP")
        self.assertEqual(lookup["thresholds"], [3.2, 3.0, 2.8])
        self.assertEqual(lookup["capacity_band"], "")
        self.assertEqual(lookup["capacity_boundary"], {})
        self.assertEqual(lookup["provided_metric_name"], "COP")
        self.assertIsNone(lookup["provided_metric_value"])
        self.assertEqual(lookup["match_status"], "设计指标缺失")

    def test_unitary_ac_heat_pump_apf_14000w_switches_to_open_lower_band(self):
        """GB 19576表1热泵型APF在14 000 W处由闭上限切换到开下限档。"""
        at_boundary = self.evaluate("unitary_ac", {
            "category": "风冷式单元式空调机",
            "mode": "热泵型",
            "cooling_capacity": 14,
            "apf": 2.7,
        })
        self.assertEqual(at_boundary.conclusion, Conclusion.LEVEL_3)
        at_lookup = at_boundary.lookups[0]
        self.assertEqual(at_lookup["data_id"], "GB19576-T1-03")
        self.assertEqual(at_lookup["capacity_band"], "7000<=cooling_capacity_w<=14000")
        self.assertEqual(at_lookup["capacity_boundary"], {
            "metric": "cooling_capacity_w",
            "min": 7000,
            "max": 14000,
            "min_inclusive": True,
            "max_inclusive": True,
        })

        above_boundary = self.evaluate("unitary_ac", {
            "category": "风冷式单元式空调机",
            "mode": "热泵型",
            "cooling_capacity": 14.0001,
            "apf": 2.6,
        })
        self.assertEqual(above_boundary.conclusion, Conclusion.LEVEL_3)
        above_lookup = above_boundary.lookups[0]
        self.assertEqual(above_lookup["data_id"], "GB19576-T1-04")
        self.assertEqual(above_lookup["capacity_band"], "cooling_capacity_w>14000")
        self.assertEqual(above_lookup["capacity_boundary"]["min"], 14000)
        self.assertFalse(above_lookup["capacity_boundary"]["min_inclusive"])
        self.assertEqual(above_lookup["thresholds"], [3.4, 3.0, 2.6])

    def test_v4_multi_split_ac_maps_three_dynamic_metrics(self):
        result = self.evaluate("multi_split_ac", {
            "category": "风冷式单冷型多联机",
            "cooling_capacity": 10,
            "rated_power": 2,
            "external_static": 0,
            "indicator1_name": "SEER",
            "indicator1_value": 5.5,
            "indicator2_name": "EERmin",
            "indicator2_value": 2.1,
        })
        # 表1中EERmin按等级分别为3.60/2.90/2.10；EERmin=2.10时只能达到3级。
        self.assertEqual(result.conclusion, Conclusion.LEVEL_3)
        self.assertTrue(any(item.get("metric") == "EERmin" for item in result.comparisons))
        self.assertEqual(result.limits["1级EERmin"], 3.6)
        self.assertEqual(result.limits["2级EERmin"], 2.9)
        self.assertEqual(result.limits["3级EERmin"], 2.1)

    def test_multi_split_ac_auxiliary_indicator_name_mismatch_is_not_treated_as_missing_only(self):
        """编号辅助指标填错名称时，应保留该输入并明确指出通道不匹配。"""
        result = self.evaluate("multi_split_ac", {
            "category": "风冷式单冷型多联机",
            "cooling_capacity": 10,
            "rated_power": 2,
            "external_static": 0,
            "indicator1_name": "SEER",
            "indicator1_value": 5.5,
            # 表1第二通道要求EERmin，这里故意填写COP(-12℃)。
            "indicator2_name": "COP(-12℃)",
            "indicator2_value": 2.1,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("indicator2", result.explanation)
        self.assertIn("EERmin", result.explanation)
        self.assertIn("COP(-12℃)", result.explanation)
        self.assertEqual(result.missing_fields, ["EERmin"])
        lookup = result.lookups[0]
        self.assertEqual(lookup["data_id"], "GB21454-T1-01")
        self.assertEqual(lookup["match_status"], "设计指标名称不匹配")
        self.assertEqual(lookup["provided_metrics"][1]["name"], "COP(-12℃)")
        self.assertEqual(str(lookup["provided_metrics"][1]["value"]), "2.1")
        self.assertEqual(str(result.actual_metrics["COP(-12℃)"]), "2.1")

    def test_multi_split_ac_eer_gate_is_and_with_seer_at_each_level(self):
        """GB 21454表1的SEER与EERmin必须按同一等级AND判定。"""
        base = {
            "category": "风冷单冷",
            "cooling_capacity": 10,
            "seer": 5.5,
        }
        level1 = self.evaluate("multi_split_ac", {**base, "eer": 3.6})
        self.assertEqual(level1.conclusion, Conclusion.LEVEL_1)
        self.assertTrue(all(item["passed"] is True for item in level1.comparisons))
        self.assertEqual(level1.actual_metrics["EERmin"], Decimal("3.6"))
        self.assertEqual(level1.limits["1级EERmin"], 3.6)
        lookup = level1.lookups[0]
        self.assertEqual(lookup["comparison_channels"], ["SEER", "EERmin"])
        self.assertEqual(lookup["fixed_gate_thresholds"]["EERmin"], [3.6, 2.9, 2.1])
        self.assertEqual(lookup["fixed_gate_directions"]["EERmin"], ">=")

        # SEER仍达到1级，但EERmin仅达到2级，结论必须降为2级。
        level2 = self.evaluate("multi_split_ac", {**base, "eer": 2.9})
        self.assertEqual(level2.conclusion, Conclusion.LEVEL_2)
        self.assertTrue(any(
            item.get("metric") == "EERmin"
            and item.get("level") == "1级"
            and item.get("passed") is False
            for item in level2.comparisons
        ))
        self.assertTrue(any(
            item.get("metric") == "EERmin"
            and item.get("level") == "2级"
            and item.get("passed") is True
            for item in level2.comparisons
        ))

        # 低于EERmin的3级门槛时，即使SEER达到1级也只能判未达标。
        below = self.evaluate("multi_split_ac", {**base, "eer": 2.09})
        self.assertEqual(below.conclusion, Conclusion.NOT_COMPLIANT)
        self.assertTrue(any(
            item.get("metric") == "EERmin"
            and item.get("level") == "3级"
            and item.get("passed") is False
            for item in below.comparisons
        ))

    def test_multi_split_ac_low_temperature_cop_gates_are_required(self):
        """GB 21454表4的HSPF、-12℃COP和-20℃COP均为AND门槛。"""
        base = {
            "category": "低温机组",
            "heating_capacity": 10,
            "hspf": 3.4,
            "cop_minus12": 2.2,
            "cop_minus20": 1.8,
        }
        level1 = self.evaluate("multi_split_ac", base)
        self.assertEqual(level1.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(level1.actual_metrics["COP(-12℃)"], Decimal("2.2"))
        self.assertEqual(level1.actual_metrics["COP(-20℃)"], Decimal("1.8"))
        self.assertEqual(level1.limits["固定门槛:COP(-12℃)"], 2.2)
        self.assertEqual(level1.limits["固定门槛:COP(-20℃)"], 1.8)
        self.assertEqual({item.get("metric") for item in level1.comparisons}, {"HSPF", "COP(-12℃)", "COP(-20℃)"})
        self.assertEqual(level1.lookups[0]["comparison_channels"], ["HSPF", "COP(-12℃)", "COP(-20℃)"])
        self.assertEqual(level1.lookups[0]["fixed_gate_thresholds"]["COP(-12℃)"], [2.2, 2.2, 2.2])
        self.assertEqual(level1.lookups[0]["fixed_gate_thresholds"]["COP(-20℃)"], [1.8, 1.8, 1.8])

        # 低于任一固定COP门槛时，不能仅凭HSPF判为1/2/3级。
        below = self.evaluate("multi_split_ac", {**base, "cop_minus12": 2.19})
        self.assertEqual(below.conclusion, Conclusion.NOT_COMPLIANT)
        self.assertTrue(all(
            item.get("passed") is False
            for item in below.comparisons
            if item.get("metric") == "COP(-12℃)"
        ))

        # HSPF恰好等于3级阈值，两个固定门槛也达到时，等于阈值视为达到3级。
        level3 = self.evaluate("multi_split_ac", {**base, "hspf": 3.0})
        self.assertEqual(level3.conclusion, Conclusion.LEVEL_3)
        self.assertTrue(any(
            item.get("metric") == "HSPF"
            and item.get("level") == "3级"
            and item.get("passed") is True
            for item in level3.comparisons
        ))

        missing = self.evaluate("multi_split_ac", {**base, "hspf": 3.0, "cop_minus12": None, "cop_minus20": None})
        self.assertEqual(missing.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(set(missing.missing_fields), {"COP(-12℃)", "COP(-20℃)"})
        self.assertTrue(all(
            item.get("passed") is None
            for item in missing.comparisons
            if item.get("metric") in {"COP(-12℃)", "COP(-20℃)"}
        ))

    def test_v4_multi_split_low_temperature_fields_map_and_equal_thresholds_pass(self):
        """V4字段在表4等阈值场景下保留换算、查表和固定门槛轨迹。"""
        result = self.evaluate("multi_split_ac", {
            "category": "低温多联机",
            "heating_capacity": 10,
            "rated_power": 2,
            "external_static": 0,
            "primary_metric_value": 3.4,
            "cop_minus12_value": 2.2,
            "cop_minus20_value": 1.8,
        })
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.missing_fields, [])
        self.assertEqual(result.actual_metrics["HSPF"], Decimal("3.4"))
        self.assertEqual(result.actual_metrics["COP(-12℃)"], Decimal("2.2"))
        self.assertEqual(result.actual_metrics["COP(-20℃)"], Decimal("1.8"))
        self.assertEqual(result.calculated_metrics["容量分档"], "heating_capacity_w<=18000")
        self.assertEqual(result.lookups[0]["data_id"], "GB21454-T4-01")
        self.assertEqual(result.lookups[0]["source_page"], "PDF第5页")
        self.assertEqual(result.lookups[0]["comparison_channels"], ["HSPF", "COP(-12℃)", "COP(-20℃)"])
        self.assertEqual(result.lookups[0]["fixed_gate_thresholds"]["COP(-12℃)"], [2.2, 2.2, 2.2])
        self.assertEqual(result.lookups[0]["fixed_gate_thresholds"]["COP(-20℃)"], [1.8, 1.8, 1.8])
        normalization = next(item for item in result.trace if item.get("step_type") == "输入规范化")
        conversion = next(item for item in normalization["changes"] if item.get("source_field") == "heating_capacity")
        self.assertEqual(conversion["source_unit"], "kW")
        self.assertEqual(conversion["target_unit"], "W")
        self.assertEqual(conversion["value"], Decimal("10000"))
        self.assertTrue(all(item.get("passed") is True for item in result.comparisons))

    def test_multi_split_positive_static_pressure_requires_standard_correction(self):
        base = {
            "category": "风冷单冷",
            "cooling_capacity": 10,
            "rated_power": 2,
            "external_static": 120,
            "primary_metric_value": 5.5,
            "eer_min_value": 3.6,
        }
        missing = self.evaluate("multi_split_ac", base)
        self.assertEqual(missing.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("静压修正后指标", missing.missing_fields)
        self.assertTrue(missing.actual_metrics)
        self.assertEqual(next(iter(missing.actual_metrics.values())), Decimal("5.5"))
        self.assertTrue(missing.lookups)
        self.assertEqual(missing.lookups[-1]["table"], "表1")
        self.assertTrue(missing.lookups[-1]["data_id"])
        self.assertTrue(any(item.get("step_type") == "标准查询结果" for item in missing.trace))

        corrected = self.evaluate("multi_split_ac", {**base, "static_pressure_correction_factor": 0.95})
        self.assertEqual(corrected.conclusion, Conclusion.LEVEL_2)
        self.assertIn("静压修正后指标", corrected.calculated_metrics)
        self.assertTrue(any(item.get("step_type") == "静压修正" for item in corrected.lookups))
        correction = corrected.lookups[0]
        self.assertEqual(correction["source_standards"], ["GB/T 18837-2015", "GB/T 18836-2017"])
        self.assertTrue(correction["requires_upstream_evidence"])
        self.assertIn("具体条款由上游提供", correction["source_clause"])
        self.assertEqual(corrected.lookups[-1]["step_type"], "精确查表")

        both = self.evaluate("multi_split_ac", {
            **base, "static_pressure_correction_factor": 0.95,
            "static_pressure_corrected_metric": 5.2,
        })
        self.assertEqual(both.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("只能填写一项", both.explanation)

    def test_multi_split_static_pressure_boundaries_keep_standard_context(self):
        base = {
            "category": "风冷单冷",
            "cooling_capacity": 10,
            "external_static": 0,
            "primary_metric_value": 5.5,
            "eer_min_value": 3.6,
        }
        # 静压为0时无需引用修正结果，原始主指标可以直接判定。
        zero = self.evaluate("multi_split_ac", base)
        self.assertEqual(zero.conclusion, Conclusion.LEVEL_1)
        self.assertFalse(any(item.get("step_type") == "静压修正" for item in zero.lookups))
        self.assertEqual(zero.lookups[-1]["data_id"], "GB21454-T1-01")

        # 静压为0却同时填写修正系数，不能默认为有效修正。
        zero_with_factor = self.evaluate("multi_split_ac", {**base, "static_pressure_correction_factor": 0.95})
        self.assertEqual(zero_with_factor.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("机外静压", zero_with_factor.missing_fields)
        self.assertEqual(zero_with_factor.lookups[-1]["data_id"], "GB21454-T1-01")

        # 修正系数/修正后指标必须为正数；非法值早退时仍保留主表查表记录。
        for field, value, reason in (
            ("static_pressure_correction_factor", 0, "静压修正系数必须大于0"),
            ("static_pressure_correction_factor", "bad", "静压修正系数不是有效数值"),
            ("static_pressure_corrected_metric", 0, "静压修正后指标必须大于0"),
            ("static_pressure_corrected_metric", "bad", "静压修正后指标不是有效数值"),
        ):
            with self.subTest(field=field, value=value):
                result = self.evaluate("multi_split_ac", {
                    **base,
                    "external_static": 120,
                    field: value,
                })
                self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
                self.assertIn(reason, result.explanation)
                self.assertEqual(result.lookups[-1]["data_id"], "GB21454-T1-01")

        invalid_static = self.evaluate("multi_split_ac", {**base, "external_static": "bad"})
        self.assertEqual(invalid_static.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("机外静压不是有效数值", invalid_static.explanation)
        self.assertEqual(invalid_static.lookups[-1]["data_id"], "GB21454-T1-01")

    def test_hvac_unmatched_lookup_retains_candidate_records(self):
        result = self.evaluate("duct_ac", {
            "category": "风管送风式空调（热泵）机组",
            "cooling": "风冷式",
            "mode": "不存在的机组型式",
            "enthalpy": "不适用",
            "cooling_capacity": 999999,
            "rated_power": 1.2,
            "indicator_name": "SEER",
            "indicator_value": 4.2,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "未命中")
        self.assertGreater(lookup["candidate_count"], 0)
        self.assertTrue(lookup["candidate_records"])
        self.assertTrue(lookup["candidate_data_ids"])
        self.assertTrue(lookup["source_pages"])
        self.assertTrue(result.standard_reference["clause"])
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertIn(lookup["data_id"], standard_step["data_ids"])

    def test_duct_ac_table2_capacity_above_max_is_out_of_scope(self):
        """GB 37479表2水冷全新风机组超过14 000 W应判为不在范围。"""
        result = self.evaluate("duct_ac", {
            "product_type": "直接蒸发式全新风机组",
            "cooling_source": "水冷式(水环式)",
            "enthalpy_difference": "小焓差",
            "cooling_capacity": 14.0001,
            "eer": 4.3,
        })
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertIn("未落入", result.explanation)
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "容量超出标准范围")
        self.assertEqual(lookup["candidate_data_ids"], ["GB37479-T2-03"])
        self.assertEqual(lookup["input_values"]["cooling_capacity_w"], "14000.1000")
        self.assertEqual(lookup["source_clause"], "表2")
        self.assertEqual(lookup["capacity_boundary_candidates"], [{
            "data_id": "GB37479-T2-03",
            "min": None,
            "max": 14000,
            "min_inclusive": True,
            "max_inclusive": True,
        }])
        self.assertEqual(result.missing_fields, [])

    def test_hvac_matched_missing_metric_retains_standard_row_lookup(self):
        result = self.evaluate("duct_ac", {
            "category": "风管送风式空调（热泵）机组",
            "cooling": "风冷式",
            "mode": "单冷型",
            "enthalpy": "不适用",
            "cooling_capacity": 5,
            "rated_power": 1.2,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("SEER", result.missing_fields)
        self.assertEqual(result.lookups[0]["data_id"], "GB37479-T1-01")
        self.assertEqual(result.lookups[0]["source_page"], "PDF第4页")
        self.assertTrue(result.standard_reference["clause"])
        self.assertTrue(any(item.get("step_type") == "标准查询结果" for item in result.trace))

    def test_heat_pump_chiller_v4_auxiliary_metrics_feed_fixed_gates(self):
        pack = {
            "status": "active",
            "devices": {
                "heat_pump_chiller": {
                    "records": [{
                        "data_id": "TEST-GB19577",
                        "table": "表3",
                        "conditions": {"product_standard": "GB/T25127.2", "unit_type": "地板采暖型"},
                        "range_metric": "heating_capacity_kw",
                        "max": 35,
                        "metric_field": "hspf",
                        "metric_name": "HSPF",
                        "thresholds": [3.6, 3.2, 2.8],
                        "fixed_gates": [
                            {"field": "cop_dh", "name": "COPdh", "threshold": 2.0},
                            {"field": "cop_h", "name": "COPh", "threshold": 2.3},
                        ],
                    }]
                }
            },
        }
        result = HvacEvaluator("heat_pump_chiller").evaluate({
            "record_id": "TEST-GB19577",
            "product_standard": "GB/T25127.2",
            "unit_type": "地板采暖型",
            "heating_capacity_kw": 20,
            "primary_metric_value": 4.0,
            "aux_metric1_value": 2.1,
            "aux_metric2_value": 2.4,
        }, pack)
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual({item["metric"] for item in result.comparisons[-6:]}, {"COPdh", "COPh"})

    def test_heat_pump_chiller_normal_lookup_preserves_query_context(self):
        """热泵和冷水机组正常查表应保留产品条件和容量查询轴。"""
        result = self.evaluate("heat_pump_chiller", dict(self.specs["heat_pump_chiller"]["example"]))
        lookup = result.lookups[0]
        self.assertEqual(lookup["query_conditions"], {
            "category": "低环境温度空气源热泵（冷水）机组",
            "product_standard": "GB/T 25127.2",
            "unit_type": "地板采暖型",
            "source": "空气源",
            "evaluation_system": "对应产品类别指标体系（表3～表8）",
            "heating_capacity_kw": "20",
        })
        self.assertEqual(lookup["data_id"], "GB19577-T3-01")
        self.assertEqual(lookup["table"], "表3")
        self.assertEqual(lookup["source_clause"], "4.2、表3")

    def test_heat_pump_chiller_normal_lookup_marks_standard_row_as_matched(self):
        """热泵和冷水机组正常标准行查表应显式标记命中状态。"""
        result = self.evaluate("heat_pump_chiller", dict(self.specs["heat_pump_chiller"]["example"]))
        lookup = result.lookups[0]
        self.assertEqual(lookup["match_status"], "命中")

    def test_fixed_gate_can_apply_only_to_specified_levels(self):
        pack = {
            "status": "active",
            "devices": {
                "heat_pump_chiller": {
                    "records": [{
                        "data_id": "TEST-LEVEL-GATE",
                        "table": "表X",
                        "conditions": {"category": "测试机组"},
                        "range_metric": "cooling_capacity_kw",
                        "max": 100,
                        "metric_field": "apf",
                        "metric_name": "APF",
                        "thresholds": [5.0, 4.0, 3.0],
                        "fixed_gates": [
                            {"field": "cop", "name": "COP", "threshold": 2.5, "levels": [3]},
                        ],
                    }]
                }
            },
        }
        result = HvacEvaluator("heat_pump_chiller").evaluate({
            "record_id": "TEST-LEVEL-GATE",
            "category": "测试机组",
            "cooling_capacity_kw": 20,
            "primary_metric_value": 4.5,
            "cop": 2.4,
        }, pack)
        # APF=4.5 reaches level 2; COP gate is only a level-3 requirement.
        self.assertEqual(result.conclusion, Conclusion.LEVEL_2)
        self.assertTrue(any(item.get("metric") == "COP" and item.get("level") == "3级"
                            and item.get("passed") is False for item in result.comparisons))

    def test_fixed_gate_non_numeric_input_returns_unable_instead_of_raising(self):
        pack = {
            "status": "active",
            "devices": {"heat_pump_chiller": {"records": [{
                "data_id": "TEST-BAD-GATE", "table": "表X",
                "conditions": {"category": "测试机组"}, "range_metric": "cooling_capacity_kw", "max": 100,
                "metric_field": "apf", "metric_name": "APF", "thresholds": [5.0, 4.0, 3.0],
                "fixed_gates": [{"field": "cop", "name": "COP", "threshold": 2.5}],
            }]}}
        }
        result = HvacEvaluator("heat_pump_chiller").evaluate({
            "record_id": "TEST-BAD-GATE", "category": "测试机组", "cooling_capacity_kw": 20,
            "primary_metric_value": 4.5, "cop": "not-a-number",
        }, pack)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("COP", result.missing_fields)

    def test_hvac_dash_threshold_is_retained_without_decimal_error(self):
        """HVAC标准表中的“—”不应被当作零值或丢弃查表依据。"""
        pack = {
            "status": "active",
            "devices": {"heat_pump_water_heater": {"records": [{
                "data_id": "TEST-GB29541-DASH",
                "table": "表X",
                "conditions": {"category": "测试热泵热水机"},
                "range_metric": "heating_capacity_kw",
                "max": 100,
                "metric_field": "cop",
                "metric_name": "性能系数COP",
                "thresholds": [None, 4.0, 3.0, None, None],
            }]}}
        }
        result = HvacEvaluator("heat_pump_water_heater", True).evaluate({
            "record_id": "TEST-GB29541-DASH",
            "category": "测试热泵热水机",
            "heating_capacity_kw": 20,
            "cop": 4.0,
        }, pack)
        self.assertEqual(result.conclusion, Conclusion.LEVEL_2)
        first = next(item for item in result.comparisons if item["level"] == "1级")
        self.assertIsNone(first["threshold"])
        self.assertIsNone(first["passed"])
        self.assertFalse(first["applicable"])
        self.assertEqual(first["standard_marker"], "—")
        self.assertNotIn("1级性能系数COP", result.limits)
        self.assertTrue(any(item.get("data_id") == "TEST-GB29541-DASH" for item in result.trace))

    def test_hvac_all_dash_thresholds_return_unable_with_lookup(self):
        pack = {
            "status": "active",
            "devices": {"heat_pump_water_heater": {"records": [{
                "data_id": "TEST-GB29541-ALL-DASH",
                "table": "表Y",
                "conditions": {"category": "测试热泵热水机"},
                "range_metric": "heating_capacity_kw",
                "max": 100,
                "metric_field": "cop",
                "metric_name": "性能系数COP",
                "thresholds": [None, None, None, None, None],
            }]}}
        }
        result = HvacEvaluator("heat_pump_water_heater", True).evaluate({
            "record_id": "TEST-GB29541-ALL-DASH",
            "category": "测试热泵热水机",
            "heating_capacity_kw": 20,
            "cop": 4.0,
        }, pack)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.actual_metrics["性能系数COP"], 4)
        self.assertEqual(result.lookups[0]["data_id"], "TEST-GB29541-ALL-DASH")
        self.assertTrue(any(item.get("standard_marker") == "—" for item in result.trace))

    def test_gb19577_pdf_verified_tables_one_to_eight_are_active_and_traceable(self):
        cases = [
            ({
                "category": "蒸气压缩循环冷水（热泵）机组-舒适型", "product_standard": "GB/T 18430.1",
                "unit_type": "舒适型", "source": "水冷式",
                "evaluation_system": "综合部分负荷/季节性能指标体系（表1）",
                "cooling_capacity": 100, "primary_metric_value": 6.0, "aux_metric1_value": 4.2,
            }, "表1", Conclusion.LEVEL_1),
            ({
                "category": "蒸气压缩循环冷水（热泵）机组-舒适型", "product_standard": "GB/T 18430.1",
                "unit_type": "舒适型", "source": "水冷式",
                "evaluation_system": "制冷性能系数COPc指标体系（表2）",
                "cooling_capacity": 100, "primary_metric_value": 5.3,
            }, "表2", Conclusion.LEVEL_1),
            ({
                "category": "低环境温度空气源热泵（冷水）机组", "product_standard": "GB/T 25127.2",
                "unit_type": "地板采暖型", "source": "空气源",
                "evaluation_system": "对应产品类别指标体系（表3～表8）",
                "heating_capacity": 20, "primary_metric_value": 3.6,
                "aux_metric1_value": 2.0, "aux_metric2_value": 2.3,
            }, "表3", Conclusion.LEVEL_1),
            ({
                "category": "水（地）源热泵机组", "product_standard": "GB/T 19409",
                "unit_type": "冷热水型-热泵型", "source": "水环式",
                "evaluation_system": "对应产品类别指标体系（表3～表8）",
                "cooling_capacity": 200, "primary_metric_value": 5.1,
            }, "表4", Conclusion.LEVEL_1),
            ({
                "category": "溴化锂吸收式冷（温）水机组", "product_standard": "GB/T 18431",
                "unit_type": "饱和蒸汽压力0.4MPa", "source": "饱和蒸汽",
                "evaluation_system": "对应产品类别指标体系（表3～表8）", "cooling_capacity": 100, "primary_metric_value": 1.05,
            }, "表5", Conclusion.LEVEL_1),
            ({
                "category": "蒸气压缩循环高温热泵机组", "product_standard": "GB/T 25861",
                "unit_type": "H1a", "source": "水源",
                "evaluation_system": "对应产品类别指标体系（表3～表8）", "heating_capacity": 100, "primary_metric_value": 4.0,
            }, "表6", Conclusion.LEVEL_1),
            ({
                "category": "间接蒸发冷却冷水机组", "product_standard": "JB/T 14642",
                "unit_type": "标准机型", "source": "不适用",
                "evaluation_system": "对应产品类别指标体系（表3～表8）",
                "cooling_capacity": 80, "primary_metric_value": 17, "aux_metric1_value": 9,
            }, "表7", Conclusion.LEVEL_1),
            ({
                "category": "一体式冷水（热泵）机组", "product_standard": "JB/T 12839",
                "unit_type": "风冷式", "source": "不适用",
                "evaluation_system": "对应产品类别指标体系（表3～表8）",
                "cooling_capacity": 50, "primary_metric_value": 4.4, "aux_metric1_value": 2.7,
            }, "表8", Conclusion.LEVEL_1),
        ]
        for values, table, expected in cases:
            with self.subTest(table=table):
                result = self.evaluate("heat_pump_chiller", values)
                self.assertEqual(result.conclusion, expected)
                self.assertEqual(result.standard_reference.get("table"), table)
                self.assertEqual(result.standard_reference.get("status"), "active")
                self.assertTrue(result.standard_reference.get("clause"))
                self.assertTrue(any(item.get("data_id", "").startswith(f"GB19577-T{table[-1]}-") and item.get("source_page") for item in result.lookups))

    def test_gb19577_open_capacity_boundary_selects_next_table_row(self):
        base = {
            "category": "蒸气压缩循环冷水（热泵）机组-舒适型",
            "product_standard": "GB/T 18430.1",
            "unit_type": "舒适型", "source": "水冷式",
            "evaluation_system": "制冷性能系数COPc指标体系（表2）",
            "primary_metric_value": 5.5,
        }
        at_300 = self.evaluate("heat_pump_chiller", {**base, "cooling_capacity": 300})
        above_300 = self.evaluate("heat_pump_chiller", {**base, "cooling_capacity": 300.01})
        self.assertEqual(at_300.limits["1级COPc"], 5.3)
        self.assertEqual(above_300.limits["1级COPc"], 5.8)
        self.assertNotEqual(at_300.lookups[-1].get("data_id"), above_300.lookups[-1].get("data_id"))

    def test_gb19577_table2_applies_alternate_metric_only_to_level3(self):
        """GB 19577表2的双通道行：COPc分级值与替代指标三级门槛须按AND处理。"""
        base = {
            "category": "蒸气压缩循环冷水（热泵）机组-舒适型",
            "product_standard": "GB/T 18430.1",
            "unit_type": "舒适型", "source": "水冷式",
            "evaluation_system": "制冷性能系数COPc指标体系（表2）",
            "cooling_capacity": 100,
        }
        # 1级已经由COPc确定时，不应强制索要只约束3级的替代指标。
        level1 = self.evaluate("heat_pump_chiller", {**base, "primary_metric_value": 5.3})
        self.assertEqual(level1.conclusion, Conclusion.LEVEL_1)
        self.assertNotIn("CSPF/IPLV/ACCOP", level1.missing_fields)

        # 仅达到COPc 3级且替代指标缺失，不能把3级误判为已达到。
        missing = self.evaluate("heat_pump_chiller", {**base, "primary_metric_value": 4.2})
        self.assertEqual(missing.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("CSPF/IPLV/ACCOP", missing.missing_fields)
        self.assertEqual(missing.lookups[0]["data_id"], "GB19577-T2-01")

        # 等于替代指标门槛视为达到；低于门槛则为未达标。
        at_limit = self.evaluate("heat_pump_chiller", {
            **base, "primary_metric_value": 4.2, "alternate_metric_value": 5.2,
        })
        self.assertEqual(at_limit.conclusion, Conclusion.LEVEL_3)
        self.assertEqual(at_limit.actual_metrics["CSPF/IPLV/ACCOP"], Decimal("5.2"))
        self.assertTrue(any(item.get("metric") == "CSPF/IPLV/ACCOP" and item.get("level") == "3级" and item.get("passed") is True for item in at_limit.comparisons))
        lookup = at_limit.lookups[0]
        self.assertEqual(lookup["comparison_logic"], {
            "operator": "AND",
            "primary_metric": "COPc",
            "fixed_gate_metrics": ["CSPF/IPLV/ACCOP"],
        })
        gate_comparison = next(item for item in at_limit.comparisons if item.get("metric") == "CSPF/IPLV/ACCOP")
        self.assertEqual(gate_comparison["logic"], "AND_WITH_PRIMARY")
        below = self.evaluate("heat_pump_chiller", {
            **base, "primary_metric_value": 4.2, "cspf": 5.19,
        })
        self.assertEqual(below.conclusion, Conclusion.NOT_COMPLIANT)
        self.assertTrue(any(item.get("metric") == "CSPF/IPLV/ACCOP" and item.get("passed") is False for item in below.comparisons))


if __name__ == "__main__":
    unittest.main()
