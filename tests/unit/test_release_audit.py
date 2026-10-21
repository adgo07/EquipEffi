from __future__ import annotations

from pathlib import Path
import shutil
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
    write_release_report,
)
from tools.audit_release import _audit_pmsm_confirmed_no_data
from tools.build_release import main as build_release_main
from tools.audit_release import audit_project
from tools.audit_release import ReleaseAudit
from tools.audit_release import main as audit_release_main
from tools.build_portable_bundle import BundleResult
from tools.check_distribution_assets import runtime_asset_members


ROOT = Path(__file__).resolve().parents[2]


class ReleaseAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._wheel_fixture = tempfile.TemporaryDirectory()
        temp_root = Path(cls._wheel_fixture.name)
        project = temp_root / "project"
        package = project / "src" / "equipeffi"
        package.parent.mkdir(parents=True)
        shutil.copytree(ROOT / "src" / "equipeffi", package)
        for name in ("pyproject.toml", "MANIFEST.in", "README.md"):
            shutil.copy2(ROOT / name, project / name)
        cls.current_wheel = build_wheel(project, temp_root / "dist")

    @classmethod
    def tearDownClass(cls):
        cls._wheel_fixture.cleanup()

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
                result = build_wheel(output, output)
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
        result = audit_project(ROOT, wheel=self.current_wheel)
        self.assertTrue(result.is_valid, result.errors)
        self.assertEqual(result.checks["manifest_pack_count"], 17)
        self.assertEqual(result.checks["elimination_catalog"]["source_entry_count"], 413)
        self.assertEqual(result.checks["elimination_catalog"]["industry_source_item_count"], 11)
        self.assertEqual(result.checks["elimination_catalog"]["industry_resource_rule_count"], 13)
        self.assertFalse(result.checks["elimination_catalog"]["industry_catalog_complete"])
        self.assertEqual(result.checks["elimination_catalog"]["industry_resource_rule_count"], 13)
        self.assertEqual(result.checks["elimination_catalog"]["industry_missing_rule_ids"], [])
        self.assertEqual(result.checks["elimination_catalog"]["industry_extra_rule_ids"], [])
        self.assertEqual(result.checks["elimination_catalog"]["industry_duplicate_rule_ids"], [])
        self.assertEqual(result.checks["pmsm_status"], "active")
        self.assertTrue(result.checks["pmsm_confirmed_no_data"]["is_valid"])
        self.assertEqual(
            result.checks["pmsm_confirmed_no_data"]["actual_no_data_indexes"],
            [5, 12, 19],
        )
        self.assertEqual(result.checks["wheel_missing_members"], [])
        self.assertTrue(result.checks["wheel_distribution_asset_audit"]["is_valid"])
        self.assertEqual(result.checks["wheel_headless_stdout"], "headless-pump-v6-ok")
        self.assertTrue(result.checks["wheel_status"]["ready"])
        self.assertTrue(result.checks["wheel_status"]["desktop"]["available"])
        self.assertTrue(result.checks["template"]["is_valid"])
        self.assertEqual(result.checks["pump_profiles"].keys(), {"pump_water", "pump_chemical"})
        self.assertEqual(result.checks["pump_integer_stage_validation"], {"pump_water": "INVALID_INPUT", "pump_chemical": "INVALID_INPUT"})
        self.assertEqual(result.checks["pump_range_miss_context"], {"pump_water": True, "pump_chemical": True})

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
                ])
            self.assertEqual(code, 0)
            build_pyz.assert_called_once_with(root, zipapp)
            build_zip.assert_called_once_with(wheel, portable, root=root, zipapp=zipapp)
            validate_zip.assert_called_once_with(portable)

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
                "qt_capable": True,
                "presentation_mode": "pyside6_qt",
                "status_ready": True,
                "sha256": "stub",
            }), encoding="utf-8")
            result = audit_project(ROOT, native_report=report)
            self.assertTrue(result.is_valid, result.errors)
            self.assertEqual(result.checks["native_build"]["presentation_mode"], "pyside6_qt")

    def test_audit_validates_native_package_hash_and_entrypoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executable = root / "equipeffi" / "equipeffi.exe"
            executable.parent.mkdir()
            executable.write_bytes(b"stub")
            package = root / "equipeffi.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("equipeffi/equipeffi.exe", b"stub")
                for member, source in runtime_asset_members(ROOT).items():
                    archive.write(source, member)
            package_hash = sha256(package.read_bytes()).hexdigest()
            report = root / "native.json"
            report.write_text(json.dumps({
                "platform": "windows",
                "executable": str(executable),
                "qt_capable": True,
                "presentation_mode": "pyside6_qt",
                "status_ready": True,
                "sha256": sha256(b"stub").hexdigest(),
                "package": {"path": str(package), "sha256": package_hash},
            }), encoding="utf-8")
            result = audit_project(ROOT, native_report=report)
            self.assertTrue(result.is_valid, result.errors)
            self.assertEqual(result.checks["native_build"]["package"]["actual_sha256"], package_hash)


if __name__ == "__main__":
    unittest.main()
