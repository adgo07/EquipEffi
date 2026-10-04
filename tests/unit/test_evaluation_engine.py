import json
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from equipeffi.application.services.evaluation_service import EvaluationService
from equipeffi.application.services.batch_evaluation_service import BatchEvaluationService
from equipeffi.domain.common.enums import Conclusion, EliminationScope
from equipeffi.domain.common.models import DeviceDraft
from equipeffi.domain.evaluation.decimal_math import bracket, linear_interpolate
from equipeffi.domain.evaluation.elimination import EliminationMatcher
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository, StandardPackError
from equipeffi.domain.evaluation.evaluation_engine import EvaluationEngine


ROOT = Path(__file__).resolve().parents[2]


class EvaluationEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = JsonStandardRepository(ROOT)
        cls.service = EvaluationService(cls.repo)

    def test_decimal_interpolation_forbids_extrapolation(self):
        value, factor = linear_interpolate(5, 0, 0, 10, 100)
        self.assertEqual(value, 50)
        self.assertEqual(str(factor), "0.5")
        with self.assertRaises(ValueError):
            bracket([{"x": 0}, {"x": 10}], "x", 11)

    def test_decimal_rejects_non_finite_values(self):
        with self.assertRaises(ValueError):
            linear_interpolate("NaN", 0, 0, 1, 1)
        with self.assertRaises(ValueError):
            linear_interpolate("Infinity", 0, 0, 1, 1)

    def test_core_service_rejects_invalid_as_of_and_keeps_date_trace(self):
        result = self.service.evaluate(DeviceDraft(
            record_id="BAD-DATE",
            device_type="motor_lv",
            raw_values={},
        ), as_of="2026-02-30", elimination_scope=EliminationScope.INDUSTRY_ONLY)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.missing_fields, ["as_of"])
        self.assertEqual(result.elimination_scope, EliminationScope.INDUSTRY_ONLY)
        self.assertEqual(result.trace[0]["scope"], EliminationScope.INDUSTRY_ONLY.value)
        self.assertEqual(result.trace[0]["step_type"], "判定基准日期")

    def test_core_service_keeps_scope_when_device_type_cannot_be_routed(self):
        result = self.service.evaluate(
            DeviceDraft(record_id="BAD-ROUTE", device_type="motor", raw_values={}),
            elimination_scope=EliminationScope.INDUSTRY_ONLY,
        )
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.elimination_scope, EliminationScope.INDUSTRY_ONLY)
        self.assertEqual(result.trace[1]["scope"], EliminationScope.INDUSTRY_ONLY.value)

    def test_core_service_canonicalizes_datetime_as_of(self):
        from datetime import datetime

        result = self.service.evaluate(DeviceDraft(
            record_id="DATE-OK",
            device_type="motor_lv",
            raw_values={},
        ), as_of=datetime(2026, 8, 24, 12, 30))
        self.assertEqual(result.trace[0]["as_of"], "2026-08-24")

    def test_low_motor_efficiency_is_percent_value(self):
        draft = DeviceDraft(record_id="LV-98", device_type="motor_lv", raw_values={
            "category": "三相异步电动机（一般用途）", "rated_power_kw": 7.5,
            "poles": 4, "rated_efficiency": 98,
        })
        result = self.service.evaluate(draft)
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.actual_metrics["额定效率_%"], 98)
        invalid = dict(draft.raw_values, rated_efficiency=0.98)
        invalid_result = self.service.evaluate(DeviceDraft(record_id="LV-098", device_type="motor_lv", raw_values=invalid))
        self.assertEqual(invalid_result.conclusion, Conclusion.UNABLE_TO_JUDGE)

    def test_transformer_requires_both_losses(self):
        result = self.service.evaluate(DeviceDraft(record_id="TR-1", device_type="transformer", raw_values={
            "category": "10kV油浸式三相双绕组无励磁调压配电变压器", "capacity_kva": 100,
            "core_material": "电工钢带", "connection": "Dyn11/Yzn11",
            "no_load_loss_w": 200, "load_loss_w": 1500,
        }))
        self.assertEqual(result.conclusion, Conclusion.NOT_COMPLIANT)
        self.assertEqual(len(result.lookups), 1)
        self.assertTrue(any(item.get("rule") == "空载损耗AND负载损耗" for item in result.comparisons))
        comparison = next(item for item in result.comparisons if item.get("level") == "1级")
        self.assertIn("no_load_threshold", comparison)
        self.assertIn("load_threshold", comparison)

    def test_pmsm_uses_only_rebuilt_pdf_pack(self):
        pack = self.repo.get_pack("motor_pmsm")
        self.assertEqual(pack["pack_id"], "gb30253_2024_pdf_verified_v1")
        self.assertEqual(pack["verified_table_count"], 29)
        self.assertEqual(pack["status"], "active")
        self.assertTrue(pack.get("activation_review", {}).get("all_cells_reviewed"))
        result = self.service.evaluate(DeviceDraft(record_id="PMSM-1", device_type="motor_pmsm", raw_values={
            "category": "变频调速永磁同步电动机", "rated_power_kw": 5.5,
            "rated_speed_rpm": 1500, "efficiency_at_90pct_speed": 94,
        }))
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.standard_reference["pack_id"], "gb30253_2024_pdf_verified_v1")

    def test_pmsm_table1_55kw_12pole_is_confirmed_no_data(self):
        from copy import deepcopy
        from equipeffi.domain.evaluation.device_evaluators import PmsmEvaluator

        pack = deepcopy(self.repo.get_pack("motor_pmsm"))
        pack["status"] = "active"  # 仅测试已激活包命中无数据单元格时的行为
        result = PmsmEvaluator("motor_pmsm").evaluate({
            "record_id": "PMSM-NODATA",
            "category": "异步起动永磁同步电动机",
            "rated_power_kw": 55,
            "poles": 12,
            "rated_efficiency": 95,
        }, pack)
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertIn("按复核结果判定为不在范围", result.explanation)
        self.assertEqual(result.actual_metrics["额定效率_%"], 95)
        self.assertEqual(result.calculated_metrics["标准无数据等级"], ["1级", "2级", "3级"])
        self.assertEqual(len(result.lookups), 3)
        self.assertTrue(all(item["no_data"] for item in result.lookups))
        self.assertEqual({item["level"] for item in result.lookups}, {"1", "2", "3"})
        self.assertTrue(all(item["data_id"].startswith("GB30253-T01-") for item in result.lookups))
        self.assertTrue(any(item.get("step_type") == "范围检查" for item in result.trace))
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertIn(result.lookups[0]["data_id"], standard_step["data_ids"])

    def test_pmsm_no_data_lookup_survives_public_batch_service(self):
        """服务层不得丢弃无数据单元格的查表记录和标准引用。"""
        from copy import deepcopy

        pack = deepcopy(self.repo.get_pack("motor_pmsm"))
        pack["status"] = "active"  # 仅模拟数据包完成复核后的服务层链路
        service = EvaluationService(self.repo)
        service._pack_cache["motor_pmsm"] = pack
        draft = DeviceDraft(record_id="PMSM-SERVICE-NODATA", device_type="motor_pmsm", raw_values={
            "category": "异步起动永磁同步电动机",
            "rated_power_kw": 55,
            "poles": 12,
            "rated_efficiency": 95,
        })

        result = service.evaluate(draft)
        self.assertEqual(result.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(result.actual_metrics["额定效率_%"], 95)
        self.assertTrue(result.lookups)
        self.assertEqual(result.standard_reference["table"], "表1")
        self.assertTrue(any(item.get("no_data") for item in result.trace))

        record = BatchEvaluationService.result_record(result)
        self.assertEqual(record["conclusion"], "不在范围")
        self.assertEqual(result.trace_schema_version, "1.0")
        self.assertEqual(record["trace_schema_version"], "1.0")
        self.assertTrue(record["lookups"][0]["no_data"])
        self.assertTrue(any(item.get("data_id", "").startswith("GB30253-T01-") for item in record["trace"]))

    def test_pmsm_partial_no_data_preserves_available_level_mapping(self):
        """部分等级无数据时，已查到的阈值必须仍对应原等级。"""
        from equipeffi.domain.evaluation.device_evaluators import PmsmEvaluator

        pack = {
            "pack_id": "gb30253_2024_pdf_verified_v1",
            "verified_table_count": 29,
            "status": "active",
            "tables": [{
                "table_no": 1,
                "table": "表1",
                "product": "异步起动",
                "voltage_group": "≤1140V",
                "cooling_group": "通用",
                "dims": [2],
                "rows": [{
                    "power_kw": 1,
                    "efficiency": {"1": [90], "2": [None], "3": [88]},
                    "no_data_cells": [1],
                }],
            }],
        }
        result = PmsmEvaluator("motor_pmsm").evaluate({
            "record_id": "PMSM-PARTIAL-NODATA",
            "category": "异步起动",
            "rated_power_kw": 1,
            "poles": 2,
            "rated_efficiency": 95,
        }, pack)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.calculated_metrics["标准无数据等级"], ["2级"])
        self.assertEqual(result.calculated_metrics["已查到标准等级阈值_%"], {"1级": Decimal("90"), "3级": Decimal("88")})
        self.assertEqual(len(result.lookups), 3)

    def test_pmsm_suspicious_cells_preserve_all_level_lookup_trace(self):
        """PDF存疑单元格提前终止时，1～3级查表依据仍必须完整保留。"""
        from copy import deepcopy
        from equipeffi.domain.evaluation.device_evaluators import PmsmEvaluator

        pack = deepcopy(self.repo.get_pack("motor_pmsm"))
        pack["status"] = "active"  # 仅模拟完成激活后的评价路径
        table = next(item for item in pack["tables"] if item["table_no"] == 1)
        row = next(item for item in table["rows"] if item.get("power_kw") == 45)
        # 表1的12极维度为索引5；对三个等级叶节点均标为存疑。
        row["suspicious_cells"] = [5, 12, 19]
        result = PmsmEvaluator("motor_pmsm").evaluate({
            "record_id": "PMSM-SUSPICIOUS",
            "category": "异步起动永磁同步电动机",
            "rated_power_kw": 45,
            "poles": 12,
            "rated_efficiency": 95,
        }, pack)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("存疑", result.explanation)
        self.assertEqual(len(result.lookups), 3)
        self.assertEqual({item["level"] for item in result.lookups}, {"1", "2", "3"})
        self.assertTrue(all(item.get("data_id", "").startswith("GB30253-T01-") for item in result.lookups))
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(set(standard_step["data_ids"]), {item["data_id"] for item in result.lookups})

    def test_pmsm_variable_speed_suspicious_lookup_is_not_dropped(self):
        """变频调速转速插值命中存疑端点时仍保留各等级查表轨迹。"""
        from equipeffi.domain.evaluation.device_evaluators import PmsmEvaluator

        tables = []
        for grade in (1, 2, 3):
            tables.append({
                "table_no": 7 + grade,
                "table": f"表{7 + grade}",
                "product": "变频调速",
                "grade": grade,
                "voltage_group": "≤1140V",
                "cooling_group": "通用",
                "dims": ["1000", "1500"],
                "rows": [{
                    "power_kw": 1,
                    "efficiency": {"1": [90, 91], "2": [89, 90], "3": [88, 89]},
                    "suspicious_cells": [0],
                }],
            })
        result = PmsmEvaluator("motor_pmsm").evaluate({
            "record_id": "PMSM-VS-SUSPICIOUS",
            "category": "变频调速永磁同步电动机",
            "rated_power_kw": 1,
            "rated_speed_rpm": 1250,
            "efficiency_at_90pct_speed": 95,
        }, {
            "pack_id": "gb30253_2024_pdf_verified_v1",
            "verified_table_count": 29,
            "status": "active",
            "tables": tables,
        })
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("存疑", result.explanation)
        self.assertGreaterEqual(len(result.lookups), 3)
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertTrue(standard_step.get("data_ids"))
        self.assertGreaterEqual(len(standard_step["data_ids"]), 3)

    def test_old_pmsm_pack_is_rejected(self):
        manifest = json.loads((ROOT / "src/equipeffi/standard_manifest.json").read_text(encoding="utf-8"))
        entry = next(item for item in manifest["packs"] if item["device_type"] == "motor_pmsm")
        entry["pack_id"] = "old"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "manifest.json"
            p.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            repo = JsonStandardRepository(ROOT, manifest=p)
            with self.assertRaises(StandardPackError):
                repo.get_pack("motor_pmsm")

    def test_standard_manifest_sources_are_self_contained_package_resources(self):
        manifest = json.loads((ROOT / "src/equipeffi/standard_manifest.json").read_text(encoding="utf-8"))
        base = ROOT / "src/equipeffi"
        for entry in manifest["packs"]:
            source = (base / entry["source"]).resolve()
            with self.subTest(device_type=entry["device_type"]):
                self.assertTrue(source.is_file(), source)
                self.assertEqual(source.suffix, ".json")
                self.assertTrue(str(source).startswith(str(base.resolve())))

    def test_legacy_generation_and_validation_tools_exclude_old_pmsm_sources(self):
        import tools.build_review_sheets as review
        import tools.build_standards2 as build_standards2
        import tools.clean_standard_excels as clean_excels
        import tools.validate_standards2 as validator

        self.assertNotIn("motor_pmsm.json", review.FILES)
        self.assertNotIn("motor_pmsm", build_standards2.MOTOR_JOBS)
        self.assertNotIn("motor_pmsm", build_standards2.CONVERTED_MAP)
        self.assertNotIn("04_永磁同步电动机.xlsx", clean_excels.STANDARD_FILES)
        self.assertEqual(validator.PMSM_VERIFIED.name, "gb30253_2024_pdf_verified_v1.json")

    def test_conclusion_universal_values_exist(self):
        self.assertEqual({item.value for item in Conclusion} >= {"不在范围", "无法判定", "淘汰", "未达标"}, True)
        self.assertEqual(EliminationScope.INDUSTRY_AND_MOTOR_BATCHES.value.startswith("产业结构调整"), True)
        self.assertEqual(EliminationScope.MOTOR_BATCHES_1_4.value, "高耗能落后机电设备淘汰目录第一至第四批")

    def test_user_supplied_industry_catalog_matches_explicit_entry(self):
        result = self.service.evaluate(DeviceDraft(
            record_id="INDUSTRY-3W",
            device_type="compressor",
            raw_values={"model": "3W-0.9/7", "category": "往复式空气压缩机", "input_power_kw": 3, "discharge_pressure_mpa": 0.7, "specific_power": 5},
        ), elimination_scope=EliminationScope.INDUSTRY_ONLY)
        self.assertEqual(result.conclusion, Conclusion.ELIMINATED)
        self.assertEqual(result.elimination_match["catalog"], "产业结构调整指导目录（2024年本）")
        self.assertEqual(result.elimination_match["entry_id"], "IND2024-COMPRESSOR-3W")

    def test_string_elimination_scope_is_normalized_before_catalog_filtering(self):
        """配置/适配器传入字符串时不能绕过产业目录过滤。"""
        # S8-100 is a four-batch entry, not one of the user-supplied industry
        # subset.  A raw string must therefore take the conservative
        # industry-catalog path instead of matching every catalog entry.
        result = self.service.evaluate(
            DeviceDraft(
                record_id="INDUSTRY-STRING-SCOPE",
                device_type="transformer",
                raw_values={"model": "S8-100", "production_year": 1997},
            ),
            elimination_scope="仅产业结构调整指导目录",
        )
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("非全文", result.explanation)

    def test_match_helper_normalizes_string_scope(self):
        matcher = EliminationMatcher()
        decision = matcher.match(
            "transformer",
            {"model": "S8-100", "production_year": 1997},
            "仅产业结构调整指导目录",
        )
        self.assertFalse(decision.matched)
        self.assertFalse(decision.possible)

    def test_partial_industry_catalog_does_not_treat_unknown_model_as_not_eliminated(self):
        """产业目录只有受控子集时，未命中必须保守返回无法判定。"""
        result = self.service.evaluate(
            DeviceDraft(
                record_id="INDUSTRY-UNKNOWN",
                device_type="compressor",
                raw_values={
                    "model": "UNKNOWN-1",
                    "category": "往复式空气压缩机",
                    "input_power_kw": 3,
                    "discharge_pressure_mpa": 0.7,
                    "specific_power": 5,
                },
            ),
            elimination_scope=EliminationScope.INDUSTRY_ONLY,
        )
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("非全文", result.explanation)
        elimination_trace = next(item for item in result.trace if item.get("step_type") == "淘汰检查")
        self.assertEqual(elimination_trace["output"], "未覆盖、无法判定")
        self.assertFalse(elimination_trace["catalog_complete"])

    def test_partial_industry_catalog_keeps_reference_evidence(self):
        """产业目录非全文早退时，仍保留可确定的能效参考查表证据。"""
        result = self.service.evaluate(
            DeviceDraft(
                record_id="INDUSTRY-UNKNOWN-EVIDENCE",
                device_type="compressor",
                raw_values={
                    "model": "UNKNOWN-1",
                    "category": "一般用喷油回转（工频）",
                    "input_power_kw": 1.5,
                    "discharge_pressure_mpa": 0.3,
                    "cooling_method": "风冷",
                    "specific_power": 5.8,
                },
            ),
            elimination_scope=EliminationScope.INDUSTRY_ONLY,
        )
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.reference_conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.actual_metrics["机组比功率_kW/(m3/min)"], Decimal("5.8"))
        self.assertTrue(result.limits)
        self.assertTrue(result.lookups)
        self.assertEqual(len(result.comparisons), 3)
        self.assertIsNone(result.elimination_match)
        reference_step = next(item for item in result.trace if item.get("step_type") == "能效参考判定")
        self.assertEqual(reference_step["output"], "1级")
        record = BatchEvaluationService.result_record(result)
        self.assertEqual(record["conclusion"], "无法判定")
        self.assertEqual(record["reference_conclusion"], "1级")
        self.assertTrue(record["lookups"])

    def test_pre_effective_date_no_longer_blocks_pump_standard_evaluation(self):
        """Owner 规则（Phase 6）：评价日期不是业务门禁。

        此前该用例断言"实施日前跳过标准查表"。Owner 已决定评价日期只用于记录与
        追溯，因此离心泵必须照常进入能效参考判定；断言改为证明**不再跳过**。
        """
        result = self.service.evaluate(
            DeviceDraft(
                record_id="PRE-EFFECTIVE-INDUSTRY",
                device_type="pump_water",
                raw_values={
                    "model": "UNKNOWN-PUMP",
                    "category": "单级单吸",
                    "flow_m3h": 100,
                    "head_m": 50,
                    "rated_speed_rpm": 2900,
                    "pump_efficiency": 80,
                },
            ),
            as_of="2026-02-28",
            elimination_scope=EliminationScope.INDUSTRY_ONLY,
        )
        step_types = {item.get("step_type") for item in result.trace}
        # 关键差异：不再出现"标准生效日期：已跳过"门禁步骤，而是照常执行
        # "能效参考判定"。
        self.assertNotIn("标准生效日期", step_types)
        self.assertIn("能效参考判定", step_types)
        self.assertEqual(result.standard_reference["effective_date"], "2026-03-01")
        # 该草稿缺少清水泵级数，因此结论仍是"无法判定"，但原因是缺参数，
        # 不是日期门禁。
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertTrue(any("stages" in note for note in result.notes))

    def test_pre_effective_confirmed_elimination_still_reports_elimination(self):
        """确认淘汰不依赖能效标准；实施日前同样不再跳过标准评价。"""
        result = self.service.evaluate(
            DeviceDraft(
                record_id="PRE-EFFECTIVE-ELIMINATED",
                device_type="pump_water",
                raw_values={
                    "model": "B-100",
                    "category": "单级单吸",
                    "flow_m3h": 100,
                    "head_m": 50,
                    "rated_speed_rpm": 2900,
                    "pump_efficiency": 80,
                },
            ),
            as_of="2026-02-28",
            elimination_scope=EliminationScope.INDUSTRY_ONLY,
        )
        self.assertEqual(result.conclusion, Conclusion.ELIMINATED)
        self.assertEqual(result.elimination_match["entry_id"], "IND2024-PUMP-BA")
        step_types = {item.get("step_type") for item in result.trace}
        self.assertNotIn("标准生效日期", step_types)
        self.assertNotIn("标准尚未实施", result.explanation)

    def test_combined_scope_keeps_explicit_motor_batch_hit_under_partial_industry_catalog(self):
        """组合口径下，四批目录的明确命中不应被产业目录非全文门禁拦截。"""
        result = self.service.evaluate(
            DeviceDraft(
                record_id="COMBINED-YB",
                device_type="motor_lv",
                raw_values={
                    "model": "YB160M-4",
                    "frame_size_mm": 160,
                    "rated_voltage_v": 660,
                },
            ),
            elimination_scope=EliminationScope.INDUSTRY_AND_MOTOR_BATCHES,
        )
        self.assertEqual(result.conclusion, Conclusion.ELIMINATED)
        self.assertEqual(result.elimination_match["entry_id"], "IND2024-MOTOR-YB")
        self.assertEqual(result.elimination_match["catalog"], "产业结构调整指导目录（2024年本）")
        elimination_trace = next(item for item in result.trace if item.get("step_type") == "淘汰检查")
        self.assertEqual(elimination_trace["output"], "明确命中")

    def test_industry_motor_series_requires_frame_and_voltage_conditions(self):
        matcher = EliminationMatcher()
        missing = matcher.match("motor_lv", {"model": "YBF160M-4"}, EliminationScope.INDUSTRY_ONLY)
        self.assertTrue(missing.possible)
        self.assertIn("frame_size_mm", missing.detail["missing_conditions"])
        hit = matcher.match("motor_lv", {"model": "YBF160M-4", "frame_size_mm": 160, "rated_voltage": 0.38}, EliminationScope.INDUSTRY_ONLY)
        self.assertTrue(hit.matched)
        dual_voltage_hit = matcher.match("motor_lv", {"model": "YB160M-4", "frame_size_mm": 160, "rated_voltage_v": "380/660"}, EliminationScope.INDUSTRY_ONLY)
        self.assertTrue(dual_voltage_hit.matched)
        dual_kv_hit = matcher.match("motor_lv", {"model": "YB160M-4", "frame_size_mm": 160, "rated_voltage_v": "0.38/0.66kV"}, EliminationScope.INDUSTRY_ONLY)
        self.assertTrue(dual_kv_hit.matched)
        yb2_not_yb = matcher.match("motor_lv", {"model": "YB2-160M-4", "frame_size_mm": 160, "rated_voltage_v": 380}, EliminationScope.INDUSTRY_ONLY)
        self.assertFalse(yb2_not_yb.matched)
        dual_voltage_outside = matcher.match("motor_lv", {"model": "YB160M-4", "frame_size_mm": 160, "rated_voltage_v": "660/1140"}, EliminationScope.INDUSTRY_ONLY)
        self.assertFalse(dual_voltage_outside.matched)
        outside = matcher.match("motor_lv", {"model": "YBF180M-4", "frame_size_mm": 180, "rated_voltage": 0.38}, EliminationScope.INDUSTRY_ONLY)
        self.assertFalse(outside.matched)
        self.assertFalse(matcher.match("pump_water", {"model": "BLA-100"}, EliminationScope.INDUSTRY_ONLY).matched)

    def test_all_user_supplied_industry_equipment_rules_have_controlled_matches(self):
        """回归覆盖用户列出的13条产业目录受控规则。"""
        matcher = EliminationMatcher()
        cases = (
            ("motor_lv", {"model": "YB160M-4", "frame_size_mm": 160, "rated_voltage_v": 660}, "IND2024-MOTOR-YB"),
            ("motor_lv", {"model": "YBF160M-4", "frame_size_mm": 160, "rated_voltage_v": 380}, "IND2024-MOTOR-YBF"),
            ("motor_lv", {"model": "YBK355M-4", "frame_size_mm": 355, "rated_voltage_v": "660/1140"}, "IND2024-MOTOR-YBK"),
            ("pump_water", {"model": "B-100"}, "IND2024-PUMP-BA"),
            ("pump_chemical", {"model": "F-100"}, "IND2024-PUMP-F"),
            ("pump_water", {"model": "JD-100"}, "IND2024-PUMP-JD"),
            ("compressor", {"model": "3W-0.9/7"}, "IND2024-COMPRESSOR-3W"),
            ("pump_water", {"model": "GC-8"}, "IND2024-PUMP-BOILER-FEED"),
            ("pump_water", {"model": "DG270-140"}, "IND2024-PUMP-BOILER-FEED"),
            # 属性顺序不应影响“固定炉排”与“燃煤”两个条件的同时满足。
            ("boiler", {"model": "BOILER-1", "category": "燃煤固定炉排锅炉"}, "IND2024-BOILER-FIXED-GRATE"),
            ("compressor", {"model": "L-10/7"}, "IND2024-COMPRESSOR-L10"),
            ("fan", {"model": "8-18-11", "category": "离心通风机"}, "IND2024-FAN-HIGH-PRESSURE"),
            ("boiler", {"model": "BOILER-2", "fuel": "煤", "evaporation_tph": 10}, "IND2024-BOILER-COAL-10T"),
            ("boiler", {"model": "BOILER-3", "fuel": "生物质成型燃料", "evaporation_tph": 2}, "IND2024-BOILER-BIOMASS-2T"),
        )
        for device_type, values, expected_id in cases:
            with self.subTest(expected_id=expected_id):
                decision = matcher.match(device_type, values, EliminationScope.INDUSTRY_ONLY)
                self.assertTrue(decision.matched, decision.detail)
                self.assertEqual(decision.detail["entry_id"], expected_id)

    def test_confirmed_catalog_series_is_eliminated(self):
        result = self.service.evaluate(DeviceDraft(record_id="TR-S8", device_type="transformer", raw_values={
            "model": "S8-100", "category": "10kV油浸式三相双绕组无励磁调压配电变压器",
            "capacity_kva": 100, "core_material": "电工钢带", "connection": "Dyn11/Yzn11",
            "no_load_loss_w": 200, "load_loss_w": 1500,
        }))
        self.assertEqual(result.conclusion, Conclusion.ELIMINATED)
        self.assertEqual(result.reference_conclusion, Conclusion.NOT_COMPLIANT)
        self.assertEqual(result.elimination_match["batch"], "第四批")
        trace = next(item for item in result.trace if item.get("step_type") == "淘汰检查")
        self.assertEqual(trace["entry_id"], result.elimination_match["entry_id"])
        self.assertEqual(trace["catalog"], result.elimination_match["catalog"])
        self.assertIn("型号及全部附加条件精确命中", trace["reason"])

        record = BatchEvaluationService.result_record(result)
        self.assertEqual(result.elimination, result.elimination_match)
        self.assertEqual(record["elimination"], record["elimination_match"])

    def test_four_batch_catalog_is_loaded_from_docx_extract(self):
        matcher = EliminationMatcher()
        self.assertGreaterEqual(len(matcher.entries), 110)
        self.assertEqual({entry.batch for entry in matcher.entries if entry.batch}, {"第一批", "第二批", "第三批", "第四批"})
        self.assertTrue(any(not entry.batch for entry in matcher.entries))

    def test_s9_requires_production_year_and_respects_boundary(self):
        matcher = EliminationMatcher()
        missing = matcher.match("transformer", {"model": "S9-100"}, EliminationScope.MOTOR_BATCHES_1_4)
        self.assertTrue(missing.possible)
        self.assertEqual(missing.detail["missing_conditions"], ["production_year"])
        boundary = matcher.match(
            "transformer", {"model": "S9-100", "production_year": 1997}, EliminationScope.MOTOR_BATCHES_1_4
        )
        self.assertTrue(boundary.matched)
        newer = matcher.match(
            "transformer", {"model": "S9-100", "production_year": 1998}, EliminationScope.MOTOR_BATCHES_1_4
        )
        self.assertFalse(newer.matched or newer.possible)

    def test_possible_elimination_keeps_reference_evidence(self):
        """淘汰附加条件缺失时，不能丢弃已经可确定的能效查表证据。"""
        result = self.service.evaluate(DeviceDraft(
            record_id="S9-POSSIBLE-EVIDENCE",
            device_type="transformer",
            raw_values={
                "model": "S9-100",
                "category": "10kV油浸式三相双绕组无励磁调压配电变压器",
                "capacity_kva": 100,
                "core_material": "电工钢带",
                "connection": "Dyn11/Yzn11",
                "no_load_loss_w": 200,
                "load_loss_w": 1500,
            },
        ))
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.reference_conclusion, Conclusion.NOT_COMPLIANT)
        self.assertEqual(result.actual_metrics["空载损耗_W"], Decimal("200"))
        self.assertTrue(result.limits)
        self.assertTrue(result.lookups)
        self.assertEqual(len(result.comparisons), 3)
        self.assertEqual(result.elimination_match["missing_conditions"], ["production_year"])
        self.assertTrue(any(item.get("step_type") == "标准查询结果" for item in result.trace))
        reference_step = next(item for item in result.trace if item.get("step_type") == "能效参考判定")
        self.assertEqual(reference_step["output"], "未达标")
        record = BatchEvaluationService.result_record(result)
        self.assertEqual(record["conclusion"], "无法判定")
        self.assertEqual(record["reference_conclusion"], "未达标")
        self.assertTrue(record["actual_metrics"])
        self.assertTrue(any(item.get("step_type") == "标准查询结果" for item in record["trace"]))

    def test_fourth_batch_high_voltage_motor_requires_6kv(self):
        matcher = EliminationMatcher()
        missing = matcher.match("motor_hv", {"model": "JK133-2"}, EliminationScope.MOTOR_BATCHES_1_4)
        self.assertTrue(missing.possible)
        hit = matcher.match(
            "motor_hv", {"model": "JK133-2", "rated_voltage_v": 6000}, EliminationScope.MOTOR_BATCHES_1_4
        )
        self.assertTrue(hit.matched)
        other_voltage = matcher.match(
            "motor_hv", {"model": "JK133-2", "rated_voltage_v": 10000}, EliminationScope.MOTOR_BATCHES_1_4
        )
        self.assertFalse(other_voltage.matched or other_voltage.possible)

    def test_catalog_matching_is_not_fuzzy(self):
        matcher = EliminationMatcher()
        decision = matcher.match("transformer", {"model": "S8X-100"}, EliminationScope.MOTOR_BATCHES_1_4)
        self.assertFalse(decision.matched or decision.possible)

    def test_third_batch_year_condition_is_applied(self):
        matcher = EliminationMatcher()
        old = matcher.match(
            "motor_lv", {"model": "Y2-80M1-2", "production_year": 2003}, EliminationScope.MOTOR_BATCHES_1_4
        )
        self.assertTrue(old.matched)
        new = matcher.match(
            "motor_lv", {"model": "Y2-80M1-2", "production_year": 2004}, EliminationScope.MOTOR_BATCHES_1_4
        )
        self.assertFalse(new.matched or new.possible)

    def test_batch_service_serializes_decimal_results(self):
        batch = BatchEvaluationService(self.service)
        records = batch.evaluate_records([{"record_id": "LV-B", "device_type": "motor_lv", "values": {
            "category": "三相异步电动机（一般用途）", "rated_power_kw": 7.5, "poles": 4, "rated_efficiency": 98,
        }}])
        self.assertEqual(records[0]["conclusion"], "1级")
        self.assertEqual(records[0]["actual_metrics"]["额定效率_%"], "98")

    def test_evaluation_service_reuses_immutable_standard_snapshot(self):
        class CountingRepository:
            def __init__(self, wrapped):
                self.wrapped = wrapped
                self.calls = 0

            def get_pack(self, device_type):
                self.calls += 1
                return self.wrapped.get_pack(device_type)

        repository = CountingRepository(JsonStandardRepository(ROOT))
        service = EvaluationService(repository)
        values = {
            "category": "三相异步电动机（一般用途）",
            "rated_power_kw": 7.5,
            "poles": 4,
            "rated_efficiency": 98,
        }
        for index in range(4):
            result = service.evaluate(DeviceDraft(record_id=f"CACHE-{index}", device_type="motor_lv", raw_values=values))
            self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(repository.calls, 1)

    def test_batch_trace_preserves_heat_treatment_standard_data_ids(self):
        batch = BatchEvaluationService(self.service)
        records = batch.evaluate_records([{"record_id": "HT-TRACE", "device_type": "heat_treatment", "values": {
            "category": "箱式多用炉", "energy_type": "电力", "equivalent_weight_t": 1,
            "rated_power_kw": 60, "total_electricity_kwh": 600,
        }}])
        self.assertEqual(records[0]["conclusion"], "二等")
        trace = records[0]["trace"]
        lookup = next(item for item in trace if item.get("step_type") == "公式计算")
        result = next(item for item in trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(lookup["data_id"], "GB36561-R000006")
        self.assertEqual(result["data_ids"], ["GB36561-R000006"])
        self.assertEqual(lookup["inputs"]["equivalent_weight_t"], "1")
        self.assertEqual(str(result["output"]["一等"]), "480")

    def test_common_engine_dispatches_current_two_argument_evaluator(self):
        class TwoArgumentEvaluator:
            def evaluate(self, values, standard):
                return (values, standard)

        result = EvaluationEngine().evaluate(TwoArgumentEvaluator(), {"x": 1}, {"ignored": 2}, {"table": "T1"})
        self.assertEqual(result, ({"x": 1}, {"table": "T1"}))

    def test_common_engine_keeps_legacy_three_argument_evaluator(self):
        class ThreeArgumentEvaluator:
            def evaluate(self, values, indicators, standard):
                return (values, indicators, standard)

        result = EvaluationEngine().evaluate(ThreeArgumentEvaluator(), {"x": 1}, {"i": 2}, {"table": "T1"})
        self.assertEqual(result, ({"x": 1}, {"i": 2}, {"table": "T1"}))


if __name__ == "__main__":
    unittest.main()
