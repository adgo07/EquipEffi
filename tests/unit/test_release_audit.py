from __future__ import annotations

from pathlib import Path
import json
from hashlib import sha256
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from tools.build_release import (
    REPRODUCIBLE_BUILD_EPOCH,
    build_wheel,
    release_report_path,
    sync_review_book,
    sync_runtime_template,
    write_release_report,
)
from tools.audit_release import _audit_pmsm_confirmed_no_data, _default_review_book
from tools.build_release import main as build_release_main
from tools.audit_release import audit_project
from tools.audit_release import ReleaseAudit
from tools.audit_release import main as audit_release_main
from tools.build_portable_bundle import BundleResult


ROOT = Path(__file__).resolve().parents[2]


class ReleaseAuditTests(unittest.TestCase):
    def test_pmsm_confirmed_no_data_audit_rejects_accidental_value(self):
        """用户确认的三处空值被重建脚本误填时，发布审计必须阻断。"""
        source = ROOT / "src" / "equipeffi" / "resources" / "standards" / "gb30253_2024_pdf_verified_v1.json"
        payload = json.loads(source.read_text(encoding="utf-8"))
        table = next(item for item in payload["tables"] if item["table_no"] == 1)
        row = next(item for item in table["rows"] if item.get("power_kw") == 55.0)
        row["efficiency"]["2"][5] = 0.0
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "equipeffi" / "resources" / "standards"
            target.mkdir(parents=True)
            (target / source.name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            errors: list[str] = []
            checks: dict[str, object] = {}
            _audit_pmsm_confirmed_no_data(root, errors, checks)
        self.assertFalse(checks["pmsm_confirmed_no_data"]["is_valid"])
        self.assertTrue(errors)

    def test_default_review_book_prefers_latest_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "outputs" / "final_20260826" / "设备能效标准数据_人工校对版.xlsx"
            latest = root / "outputs" / "final_20260827_web_latest" / "设备能效标准数据_人工校对版.xlsx"
            old.parent.mkdir(parents=True)
            latest.parent.mkdir(parents=True)
            old.write_bytes(b"old")
            latest.write_bytes(b"latest")
            self.assertEqual(_default_review_book(root), latest)

    def test_default_review_book_accepts_newer_date_without_code_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "outputs" / "final_20260827_web_latest" / "设备能效标准数据_人工校对版.xlsx"
            newer = root / "outputs" / "final_20260828_web" / "设备能效标准数据_人工校对版.xlsx"
            old.parent.mkdir(parents=True)
            newer.parent.mkdir(parents=True)
            old.write_bytes(b"old")
            newer.write_bytes(b"newer")
            self.assertEqual(_default_review_book(root), newer)

    def test_sync_runtime_template_copies_protected_template_without_touching_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "src" / "equipeffi" / "resources" / "templates"
            source.mkdir(parents=True)
            template = source / "设备能效分析空白模板_重构版V4_20260825.xlsx"
            template.write_bytes(b"protected-template")
            target = sync_runtime_template(root, root / "dist")
            self.assertIsNotNone(target)
            self.assertEqual(target.read_bytes(), b"protected-template")
            self.assertEqual(template.read_bytes(), b"protected-template")

    def test_sync_review_book_copies_audited_book_without_touching_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "review" / "设备能效标准数据_人工校对版.xlsx"
            output = root / "release"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"audited-review-book")

            target = sync_review_book(source, output)

            self.assertEqual(target, output / source.name)
            self.assertEqual(target.read_bytes(), b"audited-review-book")
            self.assertEqual(source.read_bytes(), b"audited-review-book")

    def test_sync_review_book_leaves_same_directory_source_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            source = output / "review.xlsx"
            source.write_bytes(b"same-dir")

            target = sync_review_book(source, output)

            self.assertEqual(target, source.resolve())
            self.assertEqual(source.read_bytes(), b"same-dir")

    def test_sync_review_book_tolerates_missing_optional_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.xlsx"
            self.assertIsNone(sync_review_book(missing, Path(tmp) / "release"))

    def test_write_release_report_uses_delivery_directory_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "final_20260830_test"
            report = write_release_report({"is_valid": True, "marker": "ok"}, output)

            self.assertEqual(report, output / "发布审计_20260830_test.json")
            self.assertEqual(release_report_path(output), report)
            self.assertEqual(
                json.loads(report.read_text(encoding="utf-8")),
                {"is_valid": True, "marker": "ok"},
            )

    def test_build_wheel_uses_offline_reproducible_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            def fake_run(command, **kwargs):
                self.assertIn("--no-index", command)
                self.assertIn("--no-build-isolation", command)
                self.assertEqual(kwargs["check"], True)
                self.assertEqual(kwargs["env"]["SOURCE_DATE_EPOCH"], REPRODUCIBLE_BUILD_EPOCH)
                (output / "equipeffi-0.2.1-py3-none-any.whl").write_bytes(b"wheel")

            with patch("tools.build_release.subprocess.run", side_effect=fake_run):
                result = build_wheel(ROOT, output)
            self.assertEqual(result.name, "equipeffi-0.2.1-py3-none-any.whl")

    def test_build_wheel_clears_stale_setuptools_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "dist"
            stale = root / "build" / "lib" / "stale-resource.bin"
            stale.parent.mkdir(parents=True)
            stale.write_bytes(b"old")

            def fake_run(command, **kwargs):
                self.assertFalse((root / "build").exists())
                (output / "equipeffi-0.2.1-py3-none-any.whl").write_bytes(b"wheel")

            with patch("tools.build_release.subprocess.run", side_effect=fake_run):
                result = build_wheel(root, output)
            self.assertEqual(result.read_bytes(), b"wheel")

    def test_source_and_bundled_wheel_pass_release_audit(self):
        wheel = ROOT / "outputs" / "final_20260830_pmsm_active" / "equipeffi-0.2.1-py3-none-any.whl"
        result = audit_project(ROOT, review_book=None, wheel=wheel)
        self.assertTrue(result.is_valid, result.errors)
        self.assertEqual(result.checks["public_device_type_count"], 15)
        self.assertEqual(result.checks["manifest_pack_count"], 17)
        self.assertEqual(result.checks["elimination_catalog"]["source_entry_count"], 413)
        self.assertEqual(result.checks["elimination_catalog"]["industry_source_item_count"], 11)
        self.assertEqual(result.checks["elimination_catalog"]["industry_resource_rule_count"], 13)
        self.assertFalse(result.checks["elimination_catalog"]["industry_catalog_complete"])
        self.assertEqual(result.checks["elimination_catalog"]["industry_resource_rule_count"], 13)
        self.assertEqual(result.checks["elimination_catalog"]["industry_missing_rule_ids"], [])
        self.assertEqual(result.checks["elimination_catalog"]["industry_extra_rule_ids"], [])
        self.assertEqual(result.checks["elimination_catalog"]["industry_duplicate_rule_ids"], [])
        self.assertEqual(result.checks["industry_scope_behavior"]["unknown_model_conclusion"], "无法判定")
        self.assertEqual(result.checks["industry_scope_behavior"]["explicit_model_conclusion"], "淘汰")
        self.assertEqual(result.checks["industry_scope_behavior"]["combined_motor_batch_conclusion"], "淘汰")
        self.assertEqual(result.checks["pmsm_status"], "active")
        self.assertTrue(result.checks["pmsm_confirmed_no_data"]["is_valid"])
        self.assertEqual(
            result.checks["pmsm_confirmed_no_data"]["actual_no_data_indexes"],
            [5, 12, 19],
        )
        self.assertEqual(result.checks["wheel_pmsm_status"], "active")
        self.assertEqual(result.checks["wheel_missing_members"], [])
        self.assertEqual(result.checks["template_validations"]["errors"], [])
        self.assertTrue(result.checks["evaluator_trace_data_ids"]["motor_lv"])
        self.assertTrue(result.checks["evaluator_trace_data_ids"]["motor_pmsm"])
        self.assertEqual(result.checks["pump_integer_stage_validation"], {"pump_water": "无法判定", "pump_chemical": "无法判定"})
        self.assertEqual(result.checks["pump_range_miss_context"], {"pump_water": True, "pump_chemical": True})
        self.assertEqual(result.checks["early_termination_context"], {"transformer": True, "motor_lv": True, "compressor": True, "fan": True, "blower": True, "submersible": True, "multi_split_static_pressure": True, "heat_treatment": True})
        self.assertNotIn("human_review_book", result.checks)

    def test_build_release_require_activation_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            wheel = Path(tmp) / "equipeffi-0.2.1-py3-none-any.whl"
            wheel.write_bytes(b"wheel")
            audit = ReleaseAudit(
                is_valid=True,
                errors=(),
                warnings=(),
                checks={"human_review_book": {
                    "activation_ready": False,
                    "activation_blockers": ["PMSM仍为normalized"],
                }},
            )
            with patch("tools.build_release.build_wheel", return_value=wheel), patch(
                "tools.build_release.audit_project", return_value=audit
            ), patch("builtins.print"):
                code = build_release_main(["--root", str(ROOT), "--output-dir", tmp, "--require-activation"])
            self.assertEqual(code, 1)

    def test_build_release_portable_output_builds_and_embeds_zipapp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheel = root / "equipeffi-0.2.1-py3-none-any.whl"
            zipapp = root / "portable.pyz"
            portable = root / "portable.zip"
            audit = ReleaseAudit(is_valid=True, errors=(), warnings=(), checks={})
            built_portable = BundleResult(path=portable, members=(), sha256="hash")
            with patch("tools.build_release.build_wheel", return_value=wheel), patch(
                "tools.build_release.audit_project", return_value=audit
            ), patch("tools.build_release.build_zipapp", return_value=zipapp) as build_pyz, patch(
                "tools.build_release.build_bundle", return_value=built_portable
            ) as build_zip, patch(
                "tools.build_release.validate_portable_bundle",
                return_value={"is_valid": True, "errors": [], "checks": {}},
            ) as validate_zip:
                wheel.write_bytes(b"wheel")
                code = build_release_main([
                    "--root", str(root), "--output-dir", str(root),
                    "--portable-output", str(portable), "--zipapp-output", str(zipapp),
                    "--skip-review",
                ])
            self.assertEqual(code, 0)
            build_pyz.assert_called_once_with(root, zipapp)
            build_zip.assert_called_once_with(wheel, portable, root=root, zipapp=zipapp)
            validate_zip.assert_called_once_with(portable)

    def test_build_release_auto_selects_latest_review_book(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "dist"
            output.mkdir()
            wheel = output / "equipeffi-0.2.1-py3-none-any.whl"
            wheel.write_bytes(b"wheel")
            review = root / "outputs" / "final_20260827_web_latest" / "设备能效标准数据_人工校对版.xlsx"
            review.parent.mkdir(parents=True)
            review.write_bytes(b"review")
            audit = ReleaseAudit(is_valid=True, errors=(), warnings=(), checks={})
            with patch("tools.build_release.build_wheel", return_value=wheel), patch(
                "tools.build_release.audit_project", return_value=audit
            ) as audit_project, patch("builtins.print"):
                code = build_release_main(["--root", str(root), "--output-dir", str(output)])
            self.assertEqual(code, 0)
            audit_project.assert_called_once_with(root, review_book=review, wheel=wheel)

    def test_build_release_rejects_activation_without_review(self):
        with self.assertRaises(SystemExit):
            build_release_main(["--require-activation", "--skip-review"])

    def test_audit_cli_can_write_machine_readable_report(self):
        audit = ReleaseAudit(is_valid=True, errors=(), warnings=(), checks={"marker": "ok"})
        with tempfile.TemporaryDirectory() as tmp, patch("tools.audit_release.audit_project", return_value=audit), patch(
            "builtins.print"
        ):
            output = Path(tmp) / "audit.json"
            code = audit_release_main(["--root", str(ROOT), "--output", str(output)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "checks": {"marker": "ok"},
            })

    def test_audit_can_validate_native_build_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executable = root / "equipeffi.exe"
            executable.write_bytes(b"stub")
            report = root / "native.json"
            report.write_text(json.dumps({
                "platform": "windows",
                "executable": str(executable),
                "gui_capable": False,
                "presentation_mode": "web_fallback",
                "sha256": "stub",
            }), encoding="utf-8")
            result = audit_project(ROOT, review_book=None, native_report=report)
            self.assertTrue(result.is_valid, result.errors)
            self.assertEqual(result.checks["native_build"]["presentation_mode"], "web_fallback")

    def test_audit_validates_native_package_hash_and_entrypoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executable = root / "equipeffi" / "equipeffi.exe"
            executable.parent.mkdir()
            executable.write_bytes(b"stub")
            package = root / "equipeffi.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("equipeffi/equipeffi.exe", b"stub")
            package_hash = sha256(package.read_bytes()).hexdigest()
            report = root / "native.json"
            report.write_text(json.dumps({
                "platform": "windows",
                "executable": str(executable),
                "gui_capable": False,
                "presentation_mode": "web_fallback",
                "sha256": sha256(b"stub").hexdigest(),
                "package": {"path": str(package), "sha256": package_hash},
            }), encoding="utf-8")
            result = audit_project(ROOT, review_book=None, native_report=report)
            self.assertTrue(result.is_valid, result.errors)
            self.assertEqual(result.checks["native_build"]["package"]["actual_sha256"], package_hash)


if __name__ == "__main__":
    unittest.main()
