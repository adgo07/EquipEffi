from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator, FormatChecker
from tools import validate_phase1_contracts


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_01 = json.loads((ROOT / "specs/equipment_efficiency/schemas/golden_case.schema.json").read_text(encoding="utf-8"))
SCHEMA_02 = json.loads((ROOT / "specs/equipment_efficiency/schemas/golden_case_0_2.schema.json").read_text(encoding="utf-8"))


def _case_02() -> dict:
    return {
        "case_schema_version": "golden-case-0.2",
        "case_id": "GC-PUMP-02-TEST",
        "case_status": "DRAFT",
        "device_type": "centrifugal_pump",
        "profile_id": "pump_water",
        "business_spec_version": "0.2-candidate",
        "standard_pack_id": "gb19762_2025_water_v1",
        "standard_pack_version": "v1",
        "catalog_data_version": "test-data",
        "ruleset_version": "pump-water-rules-0.2-candidate",
        "input": {
            "as_of": "2026-09-27",
            "category": "多级清水离心泵",
            "flow_m3h": "101",
            "head_m": "120",
            "rated_speed_rpm": "2900",
            "suction": "单吸",
            "stages": "3",
            "pump_efficiency": "80",
            "input_basis": "STANDARD_BEP",
            "measurement_point": "BEP",
            "unit_id_by_field": {
                "flow_m3h": "m3/h",
                "head_m": "m",
                "rated_speed_rpm": "rpm",
                "suction": "unitless",
                "stages": "stage",
                "pump_efficiency": "%",
            },
        },
        "expected_status": "SUPPORTED",
        "expected_actual_metrics": {},
        "expected_lookups": [],
        "expected_calculated_metrics": {},
        "expected_limits": {},
        "expected_conclusion": "1级",
        "expected_issue_codes": [],
        "expected_rule_ids": [],
        "source_reference": [{
            "source_id": "STANDARD-TEST",
            "artifact_kind": "EXTERNAL_FILE",
            "artifact_path": "source.pdf",
            "artifact_sha256": "0" * 64,
            "clause_or_table": "table",
            "evidence_role": "STANDARD",
        }],
        "review_status": "DRAFT",
        "review_metadata": {
            "reviewed_at": "2026-09-27",
            "reviewer": "test fixture",
            "review_owner": "王玮（待正式复核）",
            "approval_basis": ["test only"],
            "known_limits": ["unapproved"],
        },
    }


class GoldenCaseSchema02Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = Draft202012Validator(SCHEMA_02, format_checker=FormatChecker())

    def test_02_accepts_explicit_suction_and_normal_draft(self) -> None:
        self.assertEqual(list(self.validator.iter_errors(_case_02())), [])

    def test_02_represents_missing_stage_as_null_or_omitted_field(self) -> None:
        case = _case_02()
        case["input"]["stages"] = None
        self.assertEqual(list(self.validator.iter_errors(case)), [])
        del case["input"]["stages"]
        self.assertEqual(list(self.validator.iter_errors(case)), [])

    def test_02_represents_missing_category_as_explicit_null(self) -> None:
        case = _case_02()
        case["input"]["category"] = None
        case["expected_status"] = "REQUIRES_REVIEW"
        case["expected_conclusion"] = "无法判定"
        self.assertEqual(list(self.validator.iter_errors(case)), [])

    def test_02_keeps_legitimate_conflict_representable_for_invalid_input_expectation(self) -> None:
        case = _case_02()
        case["input"]["stages"] = "1"
        case["expected_status"] = "INVALID_INPUT"
        self.assertEqual(list(self.validator.iter_errors(case)), [])

    def test_02_rejects_wrong_version_json_numbers_and_bad_suction(self) -> None:
        case = _case_02()
        case["case_schema_version"] = "golden-case-0.1"
        self.assertTrue(list(self.validator.iter_errors(case)))
        case = _case_02()
        case["input"]["flow_m3h"] = 101
        self.assertTrue(list(self.validator.iter_errors(case)))
        case = _case_02()
        case["input"]["suction"] = "不适用"
        self.assertTrue(list(self.validator.iter_errors(case)))

    def test_01_schema_remains_unchanged_and_rejects_suction_extension(self) -> None:
        self.assertEqual(SCHEMA_01["properties"]["case_schema_version"]["const"], "golden-case-0.1")
        self.assertNotIn("suction", SCHEMA_01["$defs"]["input"]["properties"])

    def test_01_old_canonical_hash_is_historical_and_case_bytes_are_unchanged(self) -> None:
        case_path = ROOT / "specs/equipment_efficiency/golden/pump_water/GC-PUMP-001-NORMAL.json"
        original_bytes = case_path.read_bytes()
        case = json.loads(original_bytes)
        pack_path = ROOT / "src/equipeffi/resources/standards/pump.json"
        current_pack_hash = validate_phase1_contracts._sha256(pack_path)
        actual_hashes = [current_pack_hash] + [
            reference["artifact_sha256"] for reference in case["source_reference"][1:]
        ]
        with (
            patch.object(validate_phase1_contracts, "_artifact_path", return_value=pack_path),
            patch.object(validate_phase1_contracts, "_sha256", side_effect=actual_hashes),
        ):
            errors, historical, external_skipped = validate_phase1_contracts._source_errors(
                ROOT, case, case["case_schema_version"]
            )
        self.assertEqual(errors, [])
        self.assertEqual(external_skipped, 0)
        self.assertTrue(any("registered historical hash" in message for message in historical))
        self.assertEqual(
            case["source_reference"][0]["artifact_sha256"],
            "D1FAB8310AA5ADE7ACCCB379BD347F442D51202E0EE2EEF4CA6E34F5A2F3EA00",
        )
        self.assertEqual(case_path.read_bytes(), original_bytes)

    def test_01_unknown_historical_hash_is_still_an_error(self) -> None:
        case = _case_02()
        case["case_schema_version"] = "golden-case-0.1"
        case["catalog_data_version"] = "2026.08.23"
        case["source_reference"] = [
            {
                "source_id": "canonical",
                "artifact_kind": "REPOSITORY_FILE",
                "artifact_path": "src/equipeffi/resources/standards/pump.json",
                "artifact_sha256": "0" * 64,
                "clause_or_table": "table",
                "evidence_role": "CANONICAL_PACK",
            },
            {
                "source_id": "standard",
                "artifact_kind": "EXTERNAL_FILE",
                "artifact_path": "source.pdf",
                "artifact_sha256": "1" * 64,
                "clause_or_table": "table",
                "evidence_role": "STANDARD",
            },
        ]
        pack_path = ROOT / "src/equipeffi/resources/standards/pump.json"
        with (
            patch.object(validate_phase1_contracts, "_artifact_path", return_value=pack_path),
            patch.object(validate_phase1_contracts, "_sha256", side_effect=[validate_phase1_contracts._sha256(pack_path), "1" * 64]),
        ):
            errors, historical, _ = validate_phase1_contracts._source_errors(ROOT, case, "golden-case-0.1")
        self.assertTrue(any("SHA-256" in message for message in errors))
        self.assertFalse(any("registered historical hash" in message for message in historical))

    def test_old_implementation_hash_is_historical_only_when_exactly_registered(self) -> None:
        pump_path = ROOT / "src/equipeffi/domain/evaluation/evaluators/pump.py"
        pack_path = ROOT / "src/equipeffi/resources/standards/pump.json"
        case = _case_02()
        case["case_schema_version"] = "golden-case-0.1"
        case["catalog_data_version"] = "2026.08.23"
        case["source_reference"] = [
            {
                "source_id": "canonical-current",
                "artifact_kind": "REPOSITORY_FILE",
                "artifact_path": "src/equipeffi/resources/standards/pump.json",
                "artifact_sha256": validate_phase1_contracts._reference_sha256(
                    pack_path, {"artifact_kind": "REPOSITORY_FILE"}
                ),
                "clause_or_table": "test standard identity",
                "evidence_role": "STANDARD",
            },
            {
                "source_id": "pump-implementation-old",
                "artifact_kind": "REPOSITORY_FILE",
                "artifact_path": "src/equipeffi/domain/evaluation/evaluators/pump.py",
                "artifact_sha256": "66F84899DA5FE411340311075346D75216F1335577669CF3CC2C16F1129611EF",
                "clause_or_table": "immutable historical implementation",
                "evidence_role": "CURRENT_IMPLEMENTATION",
            },
        ]

        errors, historical, _ = validate_phase1_contracts._source_errors(ROOT, case, "golden-case-0.1")
        self.assertEqual(errors, [])
        self.assertEqual(len(historical), 1)

        case["source_reference"][1]["artifact_sha256"] = "0" * 64
        errors, historical, _ = validate_phase1_contracts._source_errors(ROOT, case, "golden-case-0.1")
        self.assertTrue(any("SHA-256" in message for message in errors))
        self.assertEqual(historical, [])

        case["source_reference"][1]["artifact_sha256"] = "66F84899DA5FE411340311075346D75216F1335577669CF3CC2C16F1129611EF"
        errors, historical, _ = validate_phase1_contracts._source_errors(ROOT, case, "golden-case-0.2")
        self.assertTrue(any("SHA-256" in message for message in errors))
        self.assertEqual(historical, [])

    def test_repository_text_digest_is_stable_across_crlf_and_lf_checkouts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            text_path = Path(temp_dir) / "source.py"
            reference = {"artifact_kind": "REPOSITORY_FILE"}
            text_path.write_bytes(b"alpha = 1\r\nbeta = 2\r\n")
            crlf_digest = validate_phase1_contracts._reference_sha256(text_path, reference)
            raw_crlf_digest = validate_phase1_contracts._sha256(text_path)
            text_path.write_bytes(b"alpha = 1\nbeta = 2\n")
            lf_digest = validate_phase1_contracts._reference_sha256(text_path, reference)
            raw_lf_digest = validate_phase1_contracts._sha256(text_path)
            self.assertEqual(crlf_digest, lf_digest)
            self.assertNotEqual(raw_crlf_digest, raw_lf_digest)

    def test_candidate_jsonl_schema_and_repository_pins_validate_without_external_pdf(self) -> None:
        candidate_path = ROOT / "specs/equipment_efficiency/golden/pump_e2e_v0_3_candidates.jsonl"
        count, error_count, errors, historical, external_skipped = validate_phase1_contracts._validate_candidate_jsonl(
            ROOT, candidate_path, skip_external_evidence=True
        )
        self.assertEqual(count, 26)
        self.assertEqual(error_count, 0, "\n".join(errors))
        self.assertEqual(errors, [])
        self.assertEqual(historical, [])
        self.assertEqual(external_skipped, 26)

    def test_external_evidence_root_is_portable_and_sha256_is_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = temp_root / "clone-a"
            evidence_root = temp_root / "mounted-evidence"
            registry_dir = repo_root / "specs/equipment_efficiency"
            registry_dir.mkdir(parents=True)
            evidence_root.mkdir()
            implementation_path = repo_root / "src/current.py"
            implementation_path.parent.mkdir(parents=True)
            implementation_path.write_text("current implementation\n", encoding="utf-8")
            pdf_bytes = b"synthetic external standard bytes for path-resolution regression"
            (evidence_root / "standard.pdf").write_bytes(pdf_bytes)
            pdf_hash = validate_phase1_contracts.hashlib.sha256(pdf_bytes).hexdigest().upper()
            (registry_dir / "evidence_registry.json").write_text(
                json.dumps({
                    "registry_version": "test",
                    "external_sources": {
                        "SYNTHETIC-STANDARD": {
                            "artifact_kind": "EXTERNAL_FILE",
                            "default_locator": "EQUIPEFFI_EXTERNAL_EVIDENCE_ROOT",
                            "relative_path": "standard.pdf",
                            "artifact_sha256": pdf_hash,
                        }
                    },
                    "historical_repository_hashes": [],
                }),
                encoding="utf-8",
            )
            case = {
                "case_schema_version": "golden-case-0.3",
                "catalog_data_version": "test",
                "source_sidecar": {
                    "source_references": [
                        {
                            "source_id": "SYNTHETIC-STANDARD",
                            "artifact_kind": "EXTERNAL_FILE",
                            "artifact_path": "standard.pdf",
                            "artifact_sha256": pdf_hash,
                            "evidence_role": "STANDARD",
                        },
                        {
                            "source_id": "current",
                            "artifact_kind": "REPOSITORY_FILE",
                            "artifact_path": "src/current.py",
                            "artifact_sha256": validate_phase1_contracts._sha256(implementation_path, normalize_repository_text=True),
                            "evidence_role": "CURRENT_IMPLEMENTATION",
                        },
                    ]
                },
            }

            errors, historical, skipped = validate_phase1_contracts._source_errors(
                repo_root,
                case,
                "golden-case-0.3",
                external_evidence_root=evidence_root,
            )
            self.assertEqual(errors, [])
            self.assertEqual(historical, [])
            self.assertEqual(skipped, 0)

            (evidence_root / "standard.pdf").write_bytes(pdf_bytes + b"tampered")
            errors, _, _ = validate_phase1_contracts._source_errors(
                repo_root,
                case,
                "golden-case-0.3",
                external_evidence_root=evidence_root,
            )
            self.assertTrue(any("SHA-256" in message for message in errors))

    def test_external_evidence_root_maps_immutable_01_drive_path_by_source_id(self) -> None:
        case_path = ROOT / "specs/equipment_efficiency/golden/pump_water/GC-PUMP-001-NORMAL.json"
        case = json.loads(case_path.read_text(encoding="utf-8"))
        reference = next(
            item for item in case["source_reference"] if item["evidence_role"] == "STANDARD"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            evidence_root = Path(temp_dir)
            resolved = validate_phase1_contracts._artifact_path(
                ROOT, reference, external_evidence_root=evidence_root
            )
            self.assertEqual(
                resolved,
                evidence_root
                / "6 7. GB 19762-2025 离心泵能效限定值及能效等级.pdf",
            )
            self.assertIn("G:/", reference["artifact_path"])

    def test_candidate_0_3_has_no_machine_specific_drive_locator(self) -> None:
        path = ROOT / "specs/equipment_efficiency/golden/pump_e2e_v0_3_candidates.jsonl"
        registry = validate_phase1_contracts._load_evidence_registry(ROOT)
        relative_path = registry["external_sources"]["GB19762-2025-PDF"]["relative_path"]
        for line in path.read_text(encoding="utf-8").splitlines():
            case = json.loads(line)
            standard = next(
                ref
                for ref in case["source_sidecar"]["source_references"]
                if ref["source_id"] == "GB19762-2025-PDF"
            )
            self.assertEqual(standard["artifact_path"], relative_path)
            self.assertFalse(Path(standard["artifact_path"]).is_absolute())
            self.assertNotRegex(standard["artifact_path"], r"^[A-Za-z]:")


if __name__ == "__main__":
    unittest.main()
