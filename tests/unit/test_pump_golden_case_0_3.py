from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from equipeffi.application.services.evaluation_service import EvaluationService
from equipeffi.domain.common.enums import Conclusion
from equipeffi.domain.common.models import DeviceDraft
from equipeffi.domain.evaluation.evaluators.pump import ChemicalPumpEvaluator
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "specs/equipment_efficiency/schemas/golden_case_0_3.schema.json"
CASES_PATH = ROOT / "specs/equipment_efficiency/golden/pump_e2e_v0_3_candidates.jsonl"


class PumpGoldenCaseV03Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.validator = Draft202012Validator(cls.schema)
        cls.cases = [
            json.loads(line)
            for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        cls.repository = JsonStandardRepository(ROOT)
        cls.service = EvaluationService(cls.repository)

    def test_all_candidates_validate_and_remain_draft(self):
        self.assertGreaterEqual(len(self.cases), 15)
        self.assertLessEqual(len(self.cases), 30)
        ids = [case["case_id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))
        water_cases = [case for case in self.cases if case["profile_id"] == "pump_water"]
        chemical_cases = [case for case in self.cases if case["profile_id"] == "pump_chemical"]
        self.assertEqual(len(water_cases), 18)
        self.assertEqual(len(chemical_cases), 8)
        self.assertTrue(all(case["evaluation_layer"] == "APPLICATION_E2E" for case in water_cases))
        self.assertTrue(all(case["evaluation_layer"] == "PROFILE_EVALUATOR_TECHNICAL" for case in chemical_cases))
        self.assertTrue({"1", "2", "3"}.issubset({case["expected_result"]["grade"] for case in water_cases}))
        self.assertTrue(any(case["raw_inputs"].get("product_type") == "管道清水离心泵" for case in water_cases))
        for case in self.cases:
            with self.subTest(case_id=case["case_id"]):
                self.validator.validate(case)
                references = case["source_sidecar"]["source_references"]
                roles = {item["evidence_role"] for item in references}
                self.assertTrue({"STANDARD", "CANONICAL_PACK", "CURRENT_IMPLEMENTATION"}.issubset(roles))
                self.assertEqual(case["case_status"], "DRAFT")
                self.assertEqual(case["approval_status"], "PENDING")
                self.assertEqual(case["review_status"], "DRAFT")
                self.assertEqual(
                    case["expected_calculation_trace"]["execution_basis"],
                    "BUSINESS_DRAFT" if case["profile_id"] == "pump_water" else "TECHNICAL_DIAGNOSTIC_ONLY",
                )

    def test_candidate_inputs_results_and_calculation_traces_replay(self):
        for case in self.cases:
            with self.subTest(case_id=case["case_id"]):
                if case["evaluation_layer"] == "APPLICATION_E2E":
                    result = self.service.evaluate(DeviceDraft(
                        record_id=case["case_id"],
                        device_type=case["device_type"],
                        raw_values=case["raw_inputs"],
                    ))
                else:
                    evaluator = ChemicalPumpEvaluator()
                    result = evaluator.evaluate(case["raw_inputs"], self.repository.get_pack(case["profile_id"]))
                expected = case["expected_result"]
                self.assertEqual(result.support_status, expected["support_status"])
                self.assertEqual(result.category_status, expected["category_status"])
                self.assertEqual(result.evaluation_status, expected["evaluation_status"])
                self.assertEqual(result.conclusion.value, expected["ui_conclusion"])
                self.assertEqual(result.grade, expected["grade"])
                self.assertEqual(result.issue_codes, expected["issue_codes"])

                actual_metrics = result.calculated_metrics
                derived_keys = {
                    "suction_factor": "suction_factor",
                    "stage_count": "stage_count",
                    "q_for_ns_m3s": "q_for_ns_m3s",
                    "h_for_ns_m": "h_for_ns_m",
                    "ns_raw": "ns_raw",
                    "eta_b": "基准效率_%",
                    "delta_eta": "效率修正值_%",
                    "eta_0": "规定点效率_%",
                    "output_power_kw": "输出功率_kW",
                }
                for expected_key, actual_key in derived_keys.items():
                    value = actual_metrics.get(actual_key)
                    actual_text = None if value is None else str(value)
                    self.assertEqual(
                        case["expected_calculation_trace"]["derived"][expected_key],
                        actual_text,
                        msg=f"derived field {expected_key}",
                    )

                first_lookup = result.lookups[0] if result.lookups else {}
                self.assertEqual(
                    case["expected_calculation_trace"]["matched_rule_id"],
                    first_lookup.get("data_id"),
                )
                self.assertEqual(
                    case["expected_calculation_trace"]["grade_thresholds_internal"],
                    [str(value) for value in actual_metrics.get("grade_thresholds_internal", [])],
                )
                if result.evaluation_status == "SUCCESS":
                    self.assertIn(result.grade, {"1", "2", "3", "BELOW_MINIMUM"})
                else:
                    self.assertIsNone(result.grade)

    def test_public_route_separates_unknown_other_and_chemical_release_gate(self):
        base = {
            "suction": "单吸", "stages": "1", "QBEP": "100", "HBEP": "50",
            "speed": "2900", "efficiency": "80",
        }

        def evaluate(values):
            return self.service.evaluate(
                DeviceDraft(record_id="PUMP-PUBLIC-STATUS", device_type="centrifugal_pump", raw_values=values)
            )

        water = evaluate({**base, "product_type": "单级单吸清水离心泵"})
        self.assertEqual(water.internal_device_type, "pump_water")
        self.assertEqual(water.support_status, "SUPPORTED")
        self.assertEqual(water.category_status, "APPLICABLE")
        self.assertEqual(water.evaluation_status, "SUCCESS")
        self.assertEqual(water.grade, "1")

        missing = evaluate({**base, "product_type": None})
        self.assertEqual(missing.support_status, "NOT_IN_RELEASE_SCOPE")
        self.assertEqual(missing.category_status, "UNRESOLVED")
        self.assertEqual(missing.evaluation_status, "INSUFFICIENT_DATA")
        self.assertEqual(missing.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("CATEGORY_MISSING", missing.issue_codes)
        self.assertFalse(missing.calculated_metrics)

        unknown = evaluate({**base, "product_type": "未知泵型"})
        self.assertEqual(unknown.support_status, "NOT_IN_RELEASE_SCOPE")
        self.assertEqual(unknown.category_status, "UNRESOLVED")
        self.assertEqual(unknown.evaluation_status, "INVALID_INPUT")
        self.assertEqual(unknown.conclusion, Conclusion.UNABLE_TO_JUDGE)
        self.assertIn("CATEGORY_UNRESOLVED", unknown.issue_codes)
        self.assertFalse(unknown.calculated_metrics)

        other = evaluate({"product_type": "其他类别"})
        self.assertEqual(other.support_status, "NOT_IN_RELEASE_SCOPE")
        self.assertEqual(other.category_status, "NOT_APPLICABLE")
        self.assertEqual(other.evaluation_status, "OUT_OF_STANDARD_SCOPE")
        self.assertEqual(other.conclusion, Conclusion.NOT_APPLICABLE)
        self.assertIn("CATEGORY_NOT_APPLICABLE", other.issue_codes)
        self.assertFalse(other.calculated_metrics)

        chemical = evaluate({
            "product_type": "单级石油化工离心泵", "suction": "单吸", "stages": "1",
            "QBEP": "100", "HBEP": "50", "speed": "2900", "efficiency": "90",
        })
        self.assertEqual(chemical.support_status, "NOT_IN_RELEASE_SCOPE")
        self.assertEqual(chemical.category_status, "APPLICABLE")
        self.assertIsNone(chemical.evaluation_status)
        self.assertIsNone(chemical.grade)
        self.assertEqual(chemical.conclusion, Conclusion.NOT_IN_RELEASE_SCOPE)
        self.assertFalse(chemical.calculated_metrics)

    def test_public_application_marks_present_invalid_values_without_missing_codes(self):
        base = {
            "product_type": "单级单吸清水离心泵", "suction": "单吸", "stages": "1",
            "QBEP": "100", "HBEP": "50", "speed": "2900", "efficiency": "80",
        }
        cases = (
            ("suction", "bogus", "SUCTION_INVALID", "单双吸"),
            ("stages", "0", "STAGES_INVALID", "级数"),
            ("stages", "1.5", "STAGES_INVALID", "级数"),
            ("QBEP", "-1", "FLOW_INVALID", "流量"),
            ("HBEP", "-1", "HEAD_INVALID", "扬程"),
            ("efficiency", "101", "EFFICIENCY_INVALID", "泵效率"),
        )
        for field, value, issue_code, display_field in cases:
            values = dict(base)
            values[field] = value
            with self.subTest(field=field, value=value):
                result = self.service.evaluate(DeviceDraft(
                    record_id="PUMP-PUBLIC-INVALID",
                    device_type="centrifugal_pump",
                    raw_values=values,
                ))
                self.assertEqual(result.support_status, "SUPPORTED")
                self.assertEqual(result.evaluation_status, "INVALID_INPUT")
                self.assertIn(issue_code, result.issue_codes)
                self.assertNotIn(display_field, result.missing_fields)
                self.assertIsNone(result.grade)
                self.assertNotIn("ns_raw", result.calculated_metrics)


if __name__ == "__main__":
    unittest.main()
