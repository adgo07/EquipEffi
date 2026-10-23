from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from equipeffi.domain.common.enums import Conclusion, EliminationScope
from equipeffi.domain.common.models import DeviceDraft
from equipeffi.domain.evaluation.decimal_math import bracket, linear_interpolate
from equipeffi.domain.evaluation.device_evaluators import PmsmEvaluator
from equipeffi.domain.evaluation.elimination import EliminationMatcher
from equipeffi.domain.evaluation.evaluator_registry import EVALUATOR_FACTORIES
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository, StandardPackError

ROOT = Path(__file__).resolve().parents[2]


class DomainEvaluationCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = JsonStandardRepository(ROOT)

    def evaluate_candidate(self, draft: DeviceDraft, pack=None):
        values = {"record_id": draft.record_id, **draft.raw_values}
        return EVALUATOR_FACTORIES[draft.device_type]().evaluate(
            values, pack or self.repo.get_pack(draft.device_type))

    def test_decimal_interpolation_forbids_extrapolation_and_non_finite_values(self):
        value, factor = linear_interpolate(5, 0, 0, 10, 100)
        self.assertEqual((value, str(factor)), (50, "0.5"))
        with self.assertRaises(ValueError):
            bracket([{"x": 0}, {"x": 10}], "x", 11)
        for value in ("NaN", "Infinity"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                linear_interpolate(value, 0, 0, 1, 1)

    def test_motor_percentage_candidate_results(self):
        draft = DeviceDraft(record_id="LV-98", device_type="motor_lv", raw_values={
            "category": "三相异步电动机（一般用途）", "rated_power_kw": 7.5,
            "poles": 4, "rated_efficiency": 98,
        })
        result = self.evaluate_candidate(draft)
        self.assertEqual(result.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(result.actual_metrics["额定效率_%"], 98)
        invalid = DeviceDraft(record_id="LV-098", device_type="motor_lv",
                              raw_values=dict(draft.raw_values, rated_efficiency=0.98))
        self.assertEqual(self.evaluate_candidate(invalid).conclusion, Conclusion.UNABLE_TO_JUDGE)

    def test_pmsm_uses_pdf_verified_pack_and_keeps_explicit_no_data_cells(self):
        pack = self.repo.get_pack("motor_pmsm")
        self.assertEqual(pack["pack_id"], "gb30253_2024_pdf_verified_v1")
        self.assertEqual(pack["verified_table_count"], 29)
        self.assertEqual(pack["status"], "active")
        self.assertTrue(pack.get("activation_review", {}).get("all_cells_reviewed"))
        normal = self.evaluate_candidate(DeviceDraft(record_id="PMSM-1", device_type="motor_pmsm", raw_values={
            "category": "变频调速永磁同步电动机", "rated_power_kw": 5.5,
            "rated_speed_rpm": 1500, "efficiency_at_90pct_speed": 94,
        }), pack)
        self.assertEqual(normal.conclusion, Conclusion.LEVEL_1)
        self.assertEqual(normal.standard_reference["pack_id"], "gb30253_2024_pdf_verified_v1")

        no_data = PmsmEvaluator("motor_pmsm").evaluate({
            "record_id": "PMSM-NODATA", "category": "异步起动永磁同步电动机",
            "rated_power_kw": 55, "poles": 12, "rated_efficiency": 95,
        }, pack)
        self.assertEqual(no_data.conclusion, Conclusion.OUT_OF_SCOPE)
        self.assertEqual(no_data.calculated_metrics["标准无数据等级"], ["1级", "2级", "3级"])
        self.assertEqual(len(no_data.lookups), 3)
        self.assertTrue(all(item["no_data"] for item in no_data.lookups))
        self.assertEqual({item["level"] for item in no_data.lookups}, {"1", "2", "3"})
        self.assertTrue(all(item["data_id"].startswith("GB30253-T01-") for item in no_data.lookups))

    def test_pmsm_partial_data_remains_mapped_to_its_original_grade(self):
        pack = {"pack_id": "gb30253_2024_pdf_verified_v1", "verified_table_count": 29,
                "status": "active", "tables": [{
                    "table_no": 1, "table": "表1", "product": "异步起动",
                    "voltage_group": "≤1140V", "cooling_group": "通用", "dims": [2],
                    "rows": [{"power_kw": 1, "efficiency": {"1": [90], "2": [None], "3": [88]},
                              "no_data_cells": [1]}]}]}
        result = PmsmEvaluator("motor_pmsm").evaluate({
            "record_id": "PMSM-PARTIAL", "category": "异步起动",
            "rated_power_kw": 1, "poles": 2, "rated_efficiency": 95,
        }, pack)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertEqual(result.calculated_metrics["标准无数据等级"], ["2级"])
        self.assertEqual(result.calculated_metrics["已查到标准等级阈值_%"],
                         {"1级": Decimal("90"), "3级": Decimal("88")})
        self.assertEqual(len(result.lookups), 3)

    def test_pmsm_suspicious_cells_keep_all_lookup_trace(self):
        import copy
        pack = copy.deepcopy(self.repo.get_pack("motor_pmsm"))
        table = next(item for item in pack["tables"] if item["table_no"] == 1)
        row = next(item for item in table["rows"] if item.get("power_kw") == 45)
        row["suspicious_cells"] = [5, 12, 19]
        result = PmsmEvaluator("motor_pmsm").evaluate({
            "record_id": "PMSM-SUSPICIOUS", "category": "异步起动永磁同步电动机",
            "rated_power_kw": 45, "poles": 12, "rated_efficiency": 95,
        }, pack)
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("存疑", result.explanation)
        self.assertEqual({item["level"] for item in result.lookups}, {"1", "2", "3"})
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertEqual(set(standard_step["data_ids"]), {item["data_id"] for item in result.lookups})

    def test_pmsm_variable_speed_suspicious_endpoint_keeps_grade_lookups(self):
        tables = []
        for grade in (1, 2, 3):
            tables.append({
                "table_no": 7 + grade, "table": f"表{7 + grade}",
                "product": "变频调速", "grade": grade,
                "voltage_group": "≤1140V", "cooling_group": "通用",
                "dims": ["1000", "1500"], "rows": [{
                    "power_kw": 1,
                    "efficiency": {"1": [90, 91], "2": [89, 90], "3": [88, 89]},
                    "suspicious_cells": [0],
                }],
            })
        result = PmsmEvaluator("motor_pmsm").evaluate({
            "record_id": "PMSM-VS-SUSPICIOUS", "category": "变频调速永磁同步电动机",
            "rated_power_kw": 1, "rated_speed_rpm": 1250,
            "efficiency_at_90pct_speed": 95,
        }, {"pack_id": "gb30253_2024_pdf_verified_v1", "verified_table_count": 29,
            "status": "active", "tables": tables})
        self.assertEqual(result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("存疑", result.explanation)
        self.assertGreaterEqual(len(result.lookups), 3)
        standard_step = next(item for item in result.trace if item.get("step_type") == "标准查询结果")
        self.assertGreaterEqual(len(standard_step.get("data_ids", ())), 3)

    def test_old_pmsm_pack_is_rejected_and_standard_files_are_packaged(self):
        manifest_path = ROOT / "src/equipeffi/standard_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entry = next(item for item in manifest["packs"] if item["device_type"] == "motor_pmsm")
        entry["pack_id"] = "old"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(StandardPackError):
                JsonStandardRepository(ROOT, manifest=path).get_pack("motor_pmsm")
        base = ROOT / "src/equipeffi"
        for item in manifest["packs"]:
            source = (base / item["source"]).resolve()
            with self.subTest(device_type=item["device_type"]):
                self.assertTrue(source.is_file(), source)
                self.assertEqual(source.suffix, ".json")
                self.assertTrue(str(source).startswith(str(base.resolve())))

    def test_industry_elimination_matcher_preserves_controlled_motor_conditions(self):
        matcher = EliminationMatcher()
        scope = EliminationScope.INDUSTRY_ONLY
        missing = matcher.match("motor_lv", {"model": "YBF160M-4"}, scope)
        self.assertTrue(missing.possible)
        self.assertIn("frame_size_mm", missing.detail["missing_conditions"])
        hit = matcher.match("motor_lv", {"model": "YBF160M-4", "frame_size_mm": 160,
                                         "rated_voltage": 0.38}, scope)
        self.assertTrue(hit.matched)
        self.assertTrue(matcher.match("motor_lv", {"model": "YB160M-4", "frame_size_mm": 160,
                                                     "rated_voltage_v": "380/660"}, scope).matched)
        self.assertTrue(matcher.match("motor_lv", {"model": "YB160M-4", "frame_size_mm": 160,
                                                     "rated_voltage_v": "0.38/0.66kV"}, scope).matched)
        self.assertFalse(matcher.match("motor_lv", {"model": "YB2-160M-4", "frame_size_mm": 160,
                                                      "rated_voltage_v": 380}, scope).matched)
        self.assertFalse(matcher.match("motor_lv", {"model": "YBF180M-4", "frame_size_mm": 180,
                                                      "rated_voltage_v": 380}, scope).matched)
        self.assertFalse(matcher.match("pump_water", {"model": "BLA-100"}, scope).matched)

    def test_user_supplied_industry_rules_keep_controlled_entry_ids(self):
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
            ("boiler", {"model": "BOILER-1", "category": "燃煤固定炉排锅炉"}, "IND2024-BOILER-FIXED-GRATE"),
            ("compressor", {"model": "L-10/7"}, "IND2024-COMPRESSOR-L10"),
            ("fan", {"model": "8-18-11", "category": "离心通风机"}, "IND2024-FAN-HIGH-PRESSURE"),
            ("boiler", {"model": "BOILER-2", "fuel": "煤", "evaporation_tph": 10}, "IND2024-BOILER-COAL-10T"),
            ("boiler", {"model": "BOILER-3", "fuel": "生物质成型燃料", "evaporation_tph": 2}, "IND2024-BOILER-BIOMASS-2T"),
        )
        for device_type, values, expected in cases:
            with self.subTest(expected=expected):
                decision = matcher.match(device_type, values, EliminationScope.INDUSTRY_ONLY)
                self.assertTrue(decision.matched, decision.detail)
                self.assertEqual(decision.detail["entry_id"], expected)

    def test_catalog_entries_and_year_voltage_boundaries_remain_exact(self):
        matcher = EliminationMatcher()
        self.assertGreaterEqual(len(matcher.entries), 110)
        self.assertEqual({item.batch for item in matcher.entries if item.batch},
                         {"第一批", "第二批", "第三批", "第四批"})
        self.assertTrue(any(not item.batch for item in matcher.entries))
        scope = EliminationScope.MOTOR_BATCHES_1_4
        self.assertTrue(matcher.match("transformer", {"model": "S9-100"}, scope).possible)
        self.assertTrue(matcher.match("transformer", {"model": "S9-100", "production_year": 1997}, scope).matched)
        self.assertFalse(matcher.match("transformer", {"model": "S9-100", "production_year": 1998}, scope).matched)
        self.assertTrue(matcher.match("motor_hv", {"model": "JK133-2", "rated_voltage_v": 6000}, scope).matched)
        newer = matcher.match("motor_lv", {"model": "Y2-80M1-2", "production_year": 2004}, scope)
        self.assertFalse(newer.matched or newer.possible)
        self.assertFalse(matcher.match("transformer", {"model": "S8X-100"}, scope).matched)


if __name__ == "__main__":
    unittest.main()
