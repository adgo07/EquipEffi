"""直接回放 18 条已批准 0.4；不改写任何业务 Oracle。"""
import json
from pathlib import Path
import unittest

from equipeffi.application.services.evaluation_service import EvaluationService
from equipeffi.domain.common.models import DeviceDraft
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository

ROOT = Path(__file__).resolve().parents[2]


class ApprovedPumpGoldenTests(unittest.TestCase):
    def test_all_18_approved_cases_replay_with_full_value_trace(self):
        cases = [json.loads(path.read_text(encoding="utf-8"))
                 for path in sorted((ROOT / "specs/equipment_efficiency/golden/pump_water").glob("*.json"))]
        approved = [case for case in cases if case.get("case_schema_version") == "golden-case-0.4"]
        self.assertEqual(len(approved), 18)
        service = EvaluationService(JsonStandardRepository(ROOT))
        derived = {"suction_factor": "suction_factor", "stage_count": "stage_count",
                   "q_for_ns_m3s": "q_for_ns_m3s", "h_for_ns_m": "h_for_ns_m", "ns_raw": "ns_raw",
                   "eta_b": "基准效率_%", "delta_eta": "效率修正值_%", "eta_0": "规定点效率_%",
                   "output_power_kw": "输出功率_kW"}
        for case in approved:
            with self.subTest(case=case["case_id"]):
                self.assertEqual(case["approval_status"], "APPROVED")
                self.assertTrue(case["review_owner"])
                result = service.evaluate(DeviceDraft(case["case_id"], case["device_type"], case["raw_inputs"]),
                                          as_of="2026-08-23")
                expected = case["expected_result"]
                for field in ("support_status", "category_status", "evaluation_status", "grade", "issue_codes"):
                    self.assertEqual(getattr(result, field), expected[field], field)
                self.assertEqual(result.conclusion.value, expected["ui_conclusion"])
                trace = case["expected_calculation_trace"]
                for key, metric in derived.items():
                    value = result.calculated_metrics.get(metric)
                    self.assertEqual(None if value is None else str(value), trace["derived"][key], key)
                lookup = result.lookups[0] if result.lookups else {}
                self.assertEqual(lookup.get("data_id"), trace["matched_rule_id"])
                self.assertEqual([str(value) for value in result.calculated_metrics.get("grade_thresholds_internal", [])],
                                 trace["grade_thresholds_internal"])
