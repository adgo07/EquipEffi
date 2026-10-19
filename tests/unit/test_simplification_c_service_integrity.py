from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from equipeffi.application.lifecycle import (
    WorkspaceSnapshot,
    business_keys_metadata,
)
from equipeffi.application.services.centrifugal_pump_analysis_service import (
    GB19762_STANDARD_CODE,
    PUMP_FINGERPRINT_KEYS,
    PUMP_STANDARD_IDENTITY_KEY,
    PumpAnalysisRequest,
    CentrifugalPumpAnalysisService,
    _pump_payload,
    user_conclusion_from_snapshot,
    user_conclusion_text,
    user_grade_text,
)
from equipeffi.application.services.pump_calculator_version import (
    PUMP_CALCULATOR_SOURCE_FILES,
    PUMP_CALCULATOR_VERSION,
)
from equipeffi.infrastructure.standards.json_repository import (
    JsonStandardRepository,
    StandardPackError,
)


ROOT = Path(__file__).resolve().parents[2]


class _NoPackAccess:
    def get_pack(self, *_args, **_kwargs):
        raise AssertionError("标准身份不匹配时不应读取规则包")


class StandardIdentityTests(unittest.TestCase):
    def test_standard_identity_is_fingerprinted_and_rejected_before_rules(self):
        service = CentrifugalPumpAnalysisService(_NoPackAccess())
        correct = PumpAnalysisRequest(
            "单级单吸清水离心泵", date(2026, 10, 19),
            QBEP="100", HBEP="50", speed="2900", efficiency="80",
            suction="单吸", stages="1")
        wrong = PumpAnalysisRequest(
            correct.product_category, correct.as_of, QBEP=correct.QBEP,
            HBEP=correct.HBEP, speed=correct.speed, efficiency=correct.efficiency,
            suction=correct.suction, stages=correct.stages,
            standard_code="GB 20052-2024")

        self.assertNotEqual(correct.request_fingerprint(), wrong.request_fingerprint())
        result = service.evaluate(wrong)
        self.assertEqual(result.evaluation_status, "INVALID_INPUT")
        self.assertEqual(result.issue_codes, ("STANDARD_IDENTITY_MISMATCH",))
        self.assertEqual(result.standard_code, GB19762_STANDARD_CODE)
        self.assertFalse(result.finalizable)

    def test_new_workspace_persists_standard_identity_in_its_fingerprint(self):
        request = PumpAnalysisRequest(
            "单级单吸清水离心泵", date(2026, 10, 19), standard_code="GB 20052-2024")
        payload = _pump_payload(request)
        self.assertEqual(payload[PUMP_STANDARD_IDENTITY_KEY], "GB 20052-2024")
        self.assertIn(PUMP_STANDARD_IDENTITY_KEY, payload["_business_keys"])
        workspace = WorkspaceSnapshot(
            workspace_id="W-identity",
            standard_code=request.standard_code,
            device_type="centrifugal_pump",
            product_category=request.product_category,
            rule_profile="pump_water",
            as_of=request.as_of.isoformat(),
            payload=payload,
            schema_version=1,
            created_at_utc="2026-10-19T00:00:00+00:00",
            updated_at_utc="2026-10-19T00:00:00+00:00",
        )
        self.assertEqual(workspace.request_fingerprint(), request.request_fingerprint())

    def test_legacy_workspace_fingerprint_remains_reconstructable(self):
        request = PumpAnalysisRequest(
            "单级单吸清水离心泵", date(2026, 10, 19), QBEP="100")
        payload = request.raw_values() | business_keys_metadata(PUMP_FINGERPRINT_KEYS)
        workspace = WorkspaceSnapshot(
            workspace_id="W-legacy",
            standard_code=request.standard_code,
            device_type="centrifugal_pump",
            product_category=request.product_category,
            rule_profile="pump_water",
            as_of=request.as_of.isoformat(),
            payload=payload,
            schema_version=1,
            created_at_utc="2026-10-19T00:00:00+00:00",
            updated_at_utc="2026-10-19T00:00:00+00:00",
        )
        self.assertEqual(
            workspace.request_fingerprint(PUMP_FINGERPRINT_KEYS),
            request.request_fingerprint(include_standard_identity=False),
        )

    def test_finalize_accepts_unchanged_phase4_workspace_shape(self):
        class LegacyWorkspaceRepository:
            def __init__(self, snapshot):
                self.snapshot = snapshot

            def load_workspace(self, _workspace_id):
                return self.snapshot

        class RecordCapture:
            def append_record(self, snapshot):
                self.snapshot = snapshot

        request = PumpAnalysisRequest(
            "单级单吸清水离心泵", date(2026, 10, 19), QBEP="100",
            HBEP="50", speed="2900", efficiency="90", suction="单吸",
            stages="1", workspace_revision=1)
        legacy_workspace = WorkspaceSnapshot(
            workspace_id="W-legacy-finalize",
            standard_code=request.standard_code,
            device_type="centrifugal_pump",
            product_category=request.product_category,
            rule_profile="pump_water",
            as_of=request.as_of.isoformat(),
            payload=request.raw_values() | business_keys_metadata(PUMP_FINGERPRINT_KEYS),
            schema_version=1,
            created_at_utc="2026-10-19T00:00:00+00:00",
            updated_at_utc="2026-10-19T00:00:00+00:00",
            revision=1,
        )
        records = RecordCapture()
        service = CentrifugalPumpAnalysisService(
            JsonStandardRepository(ROOT / "src" / "equipeffi"),
            LegacyWorkspaceRepository(legacy_workspace), records)
        result = service.evaluate(request)
        self.assertTrue(result.finalizable)
        record = service.finalize(
            record_id="R-legacy-workspace",
            workspace_id=legacy_workspace.workspace_id,
            request=request,
            result=result,
        )
        self.assertEqual(record.record_id, "R-legacy-workspace")
        self.assertEqual(records.snapshot.standard_code, request.standard_code)

    def test_standard_pack_failure_propagates_as_system_error(self):
        class FailedPack:
            def get_pack(self, *_args, **_kwargs):
                raise StandardPackError("pack unreadable")

        service = CentrifugalPumpAnalysisService(FailedPack())
        request = PumpAnalysisRequest(
            "单级单吸清水离心泵", date(2026, 10, 19), QBEP="100",
            HBEP="50", speed="2900", efficiency="80", suction="单吸", stages="1")
        with self.assertRaisesRegex(StandardPackError, "pack unreadable"):
            service.evaluate(request)


class StandardPackFailureBoundaryTests(unittest.TestCase):
    def _repository(self, root: Path, *, status: str = "active") -> JsonStandardRepository:
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({
            "packs": [{
                "device_type": "pump_water",
                "pack_id": "gb19762_test_v1",
                "source": "pump.json",
                "status": status,
            }],
        }), encoding="utf-8")
        return JsonStandardRepository(root, manifest)

    def test_missing_active_pack_is_a_system_pack_error(self):
        with tempfile.TemporaryDirectory() as temp:
            repository = self._repository(Path(temp))
            with self.assertRaisesRegex(StandardPackError, "正式启用.*不存在"):
                repository.get_pack("pump_water")

    def test_malformed_active_pack_is_not_returned_as_business_input_error(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._repository(root)
            (root / "pump.json").write_text("{", encoding="utf-8")
            repository = JsonStandardRepository(root, root / "manifest.json")
            with self.assertRaisesRegex(StandardPackError, "无法读取或解析标准包"):
                repository.get_pack("pump_water")

    def test_active_pack_read_error_is_wrapped_at_the_repository_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._repository(root)
            source = root / "pump.json"
            source.write_text("{}", encoding="utf-8")
            repository = JsonStandardRepository(root, root / "manifest.json")
            real_read_text = Path.read_text

            def fail_pack_read(path, *args, **kwargs):
                if path == source:
                    raise PermissionError("test resource access failure")
                return real_read_text(path, *args, **kwargs)

            with patch.object(Path, "read_text", fail_pack_read):
                with self.assertRaisesRegex(StandardPackError, "无法读取或解析标准包"):
                    repository.get_pack("pump_water")

    def test_missing_inactive_pack_keeps_existing_unavailable_shell(self):
        with tempfile.TemporaryDirectory() as temp:
            repository = self._repository(Path(temp), status="extracted")
            pack = repository.get_pack("pump_water")
            self.assertEqual(pack["status"], "extracted")
            self.assertIn("unavailable_reason", pack)


class UserDisplayProjectionTests(unittest.TestCase):
    def test_live_and_snapshot_conclusions_use_the_same_short_labels(self):
        cases = (
            ({"evaluation_status": "SUCCESS", "grade": "1", "ui_conclusion": "1级"}, "1级"),
            ({"evaluation_status": "SUCCESS", "grade": "BELOW_MINIMUM",
              "ui_conclusion": "未达标"}, "未达3级"),
            ({"evaluation_status": "OUT_OF_STANDARD_SCOPE", "ui_conclusion": "不适用"},
             "不在范围"),
            ({"evaluation_status": "INSUFFICIENT_DATA", "ui_conclusion": "无法判定"},
             "无法判定"),
            ({"evaluation_status": "INVALID_INPUT", "grade": "2",
              "ui_conclusion": "2级"}, "无法判定"),
            ({"evaluation_status": None, "requires_category_confirmation": True,
              "ui_conclusion": "无法评价"}, "无法判定"),
        )
        for snapshot, expected in cases:
            with self.subTest(snapshot=snapshot):
                self.assertEqual(user_conclusion_text(snapshot), expected)
                self.assertEqual(user_conclusion_from_snapshot(snapshot), expected)

    def test_internal_grade_codes_never_leak_to_user_text(self):
        self.assertEqual(user_grade_text("1"), "1级")
        self.assertEqual(user_grade_text("BELOW_MINIMUM"), "未达3级")
        self.assertEqual(user_grade_text("PRIVATE_INTERNAL_CODE"), "")


class PumpCalculatorVersionTests(unittest.TestCase):
    def test_calculator_version_matches_the_reviewed_source_fingerprint(self):
        digest = hashlib.sha256()
        for relative_path in PUMP_CALCULATOR_SOURCE_FILES:
            digest.update(relative_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update((ROOT / relative_path).read_bytes().replace(b"\r\n", b"\n"))
            digest.update(b"\0")
        self.assertEqual(PUMP_CALCULATOR_VERSION,
                         f"pump-calculator:sha256:{digest.hexdigest()}")


if __name__ == "__main__":
    unittest.main()
