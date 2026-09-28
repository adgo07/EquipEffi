from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator, FormatChecker

from tools import validate_phase1_contracts as validator


ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIR = ROOT / "specs/equipment_efficiency/golden/pump_water_approval_review"
SCHEMA_04_PATH = ROOT / "specs/equipment_efficiency/schemas/golden_case_0_4.schema.json"
REVIEW_SCHEMA_PATH = ROOT / "specs/equipment_efficiency/schemas/golden_case_0_4_review.schema.json"


class GoldenCaseV04ApprovalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.approved_schema = json.loads(SCHEMA_04_PATH.read_text(encoding="utf-8"))
        cls.review_schema = json.loads(REVIEW_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.approved_schema)
        Draft202012Validator.check_schema(cls.review_schema)
        cls.approved_validator = Draft202012Validator(cls.approved_schema, format_checker=FormatChecker())
        cls.review_validator = Draft202012Validator(cls.review_schema, format_checker=FormatChecker())
        cls.review_cases = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(REVIEW_DIR.glob("GC-PUMP-V4-WATER-*.json"))
        ]

    def test_approved_contract_requires_named_review_and_all_approved_states(self):
        required = set(self.approved_schema["required"])
        self.assertTrue({"review_owner", "reviewed_at", "approved_at", "approval_basis", "known_limits", "provenance"}.issubset(required))
        self.assertEqual(self.approved_schema["properties"]["case_status"]["const"], "APPROVED")
        self.assertEqual(self.approved_schema["properties"]["approval_status"]["const"], "APPROVED")
        self.assertEqual(self.approved_schema["properties"]["review_status"]["const"], "APPROVED")
        pending = copy.deepcopy(self.review_cases[0])
        promoted = pending.copy()
        promoted["case_schema_version"] = "golden-case-0.4"
        promoted["case_status"] = promoted["approval_status"] = promoted["review_status"] = "APPROVED"
        promoted["review_owner"] = "标准负责人示例姓名"
        promoted["reviewed_at"] = "2026-09-28T10:00:00+08:00"
        promoted["approved_at"] = "2026-09-28T10:30:00+08:00"
        promoted["approval_basis"] = ["GB 19762—2025 表3，独立核对本案例的适用行和判级结论"]
        self.assertEqual(list(self.approved_validator.iter_errors(promoted)), [])
        promoted["approval_status"] = "PENDING"
        self.assertTrue(list(self.approved_validator.iter_errors(promoted)))

    def test_review_package_is_pending_and_covers_exact_water_candidate_pool(self):
        self.assertEqual(len(self.review_cases), 18)
        count, error_count, errors, _, skipped = validator._validate_approval_review_packages(
            ROOT, REVIEW_DIR, skip_external_evidence=True
        )
        self.assertEqual(count, 18, errors)
        self.assertEqual(error_count, 0, errors)
        self.assertGreaterEqual(skipped, 18)
        for case in self.review_cases:
            with self.subTest(case_id=case["case_id"]):
                self.review_validator.validate(case)
                self.assertEqual(case["case_status"], "PENDING_APPROVAL")
                self.assertEqual(case["approval_status"], "PENDING")
                self.assertEqual(case["review_status"], "PENDING")
                self.assertEqual(case["profile_id"], "pump_water")
                self.assertEqual(case["evaluation_layer"], "APPLICATION_E2E")

    def test_pending_records_cannot_enter_official_golden_directory(self):
        case = copy.deepcopy(self.review_cases[0])
        with tempfile.TemporaryDirectory() as temporary_directory:
            official_dir = Path(temporary_directory)
            (official_dir / "pending.json").write_text(json.dumps(case), encoding="utf-8")
            with patch.object(validator, "CASE_DIR", official_dir):
                count, error_count, errors, _, _ = validator._validate_cases(ROOT, skip_external_evidence=True)
        self.assertEqual(count, 1)
        self.assertGreater(error_count, 0)
        self.assertTrue(any("cannot be loaded as an official Golden" in error for error in errors), errors)

    def test_official_records_cannot_be_mislabeled_as_review_packages(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            review_dir = Path(temporary_directory)
            case = copy.deepcopy(self.review_cases[0])
            case["case_schema_version"] = "golden-case-0.4"
            case["case_status"] = case["approval_status"] = case["review_status"] = "APPROVED"
            case["review_owner"] = "Named Standard Owner"
            case["reviewed_at"] = "2026-09-28T10:00:00+08:00"
            case["approved_at"] = "2026-09-28T10:10:00+08:00"
            case["approval_basis"] = ["Reviewed against the registered standard evidence"]
            (review_dir / "wrong-layer.json").write_text(json.dumps(case), encoding="utf-8")
            count, error_count, errors, _, _ = validator._validate_approval_review_packages(
                ROOT, review_dir, skip_external_evidence=True
            )
        self.assertEqual(count, 1)
        self.assertGreater(error_count, 0)
        self.assertTrue(any("only accepts golden-case-0.4-review" in error for error in errors), errors)

    def test_source_candidate_hash_and_copied_payload_are_enforced(self):
        case = copy.deepcopy(self.review_cases[0])
        errors = validator._provenance_errors(ROOT, case, case["case_schema_version"])
        self.assertEqual(errors, [])
        case["provenance"]["source_candidate_sha256"] = "0" * 64
        errors = validator._provenance_errors(ROOT, case, case["case_schema_version"])
        self.assertTrue(any("candidate SHA-256" in error for error in errors), errors)
        case = copy.deepcopy(self.review_cases[0])
        case["raw_inputs"]["QBEP"] = "999"
        errors = validator._provenance_errors(ROOT, case, case["case_schema_version"])
        self.assertTrue(any("raw_inputs" in error for error in errors), errors)

    def test_approved_record_must_have_real_owner_and_monotonic_timestamps(self):
        case = copy.deepcopy(self.review_cases[0])
        case.update({
            "case_schema_version": "golden-case-0.4",
            "case_status": "APPROVED",
            "approval_status": "APPROVED",
            "review_status": "APPROVED",
            "review_owner": "TBD",
            "reviewed_at": "2026-09-28T10:30:00+08:00",
            "approved_at": "2026-09-28T10:00:00+08:00",
            "approval_basis": ["test"],
        })
        errors = validator._approval_semantic_errors(case, "golden-case-0.4")
        self.assertTrue(any("real named human" in error for error in errors), errors)
        self.assertTrue(any("later than reviewed_at" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
