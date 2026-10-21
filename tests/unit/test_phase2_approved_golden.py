"""直接回放 18 条已批准 0.4；不改写任何业务 Oracle。"""
import json
from pathlib import Path
import unittest

from datetime import date
from equipeffi.application.services.centrifugal_pump_analysis_service import (
    CentrifugalPumpAnalysisService, PumpAnalysisRequest,
)
from equipeffi.application.result_projection import PUMP_METRIC_IDS
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository

ROOT = Path(__file__).resolve().parents[2]


class ApprovedPumpGoldenTests(unittest.TestCase):
    def test_all_18_approved_cases_replay_with_full_value_trace(self):
        cases = [json.loads(path.read_text(encoding="utf-8"))
                 for path in sorted((ROOT / "specs/equipment_efficiency/golden/pump_water").glob("*.json"))]
        approved = [case for case in cases if case.get("case_schema_version") == "golden-case-0.4"]
        self.assertEqual(len(approved), 18)
        service = CentrifugalPumpAnalysisService(JsonStandardRepository(ROOT))
        derived = {"suction_factor": "suction_factor", "stage_count": "stage_count",
                   "q_for_ns_m3s": "flow_for_specific_speed", "h_for_ns_m": "head_per_stage",
                   "ns_raw": "specific_speed", "eta_b": "base_efficiency",
                   "delta_eta": "efficiency_correction", "eta_0": "specified_efficiency",
                   "output_power_kw": "output_power"}
        for case in approved:
            with self.subTest(case=case["case_id"]):
                self.assertEqual(case["approval_status"], "APPROVED")
                self.assertTrue(case["review_owner"])
                raw = case["raw_inputs"]
                result = service.evaluate(PumpAnalysisRequest(
                    product_category=raw["product_type"], as_of=date(2026, 8, 23),
                    QBEP=raw.get("QBEP"), HBEP=raw.get("HBEP"), speed=raw.get("speed"),
                    efficiency=raw.get("efficiency"), suction=raw.get("suction"),
                    stages=raw.get("stages"), record_id=case["case_id"],
                ))
                expected = case["expected_result"]
                for field in ("category_status", "evaluation_status", "grade"):
                    self.assertEqual(getattr(result, field), expected[field], field)
                # 正式服务对没有选中规则Profile的类别级结论不声明发布支持；
                # Golden保留旧入口的历史支持字段，业务真值与中间量仍逐项精确比较。
                self.assertEqual(result.support_status,
                                 expected["support_status"] if result.rule_profile else None)
                self.assertEqual(list(result.issue_codes), expected["issue_codes"])
                self.assertEqual(result.ui_conclusion, expected["ui_conclusion"])
                trace = case["expected_calculation_trace"]
                for key, metric in derived.items():
                    value = result.metrics_by_id.get(PUMP_METRIC_IDS[metric])
                    self.assertEqual(None if value is None else value.value, trace["derived"][key], key)
                self.assertEqual(result.matched_rule_id, trace["matched_rule_id"])
                self.assertEqual(result.calculation_trace.get("thresholds_internal", []),
                                 trace["grade_thresholds_internal"])
