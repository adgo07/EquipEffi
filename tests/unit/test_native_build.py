from __future__ import annotations

from contextlib import nullcontext, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from types import SimpleNamespace
from unittest.mock import patch

from tools.build_native import build_native, build_native_command, main, package_native
from tools.check_distribution_assets import runtime_asset_paths


ROOT = Path(__file__).resolve().parents[2]


class NativeBuildTests(unittest.TestCase):
    def test_native_status_smoke_uses_utf8_for_child_and_json_decode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executable = root / "dist" / "equipeffi" / "equipeffi.exe"
            status_payload = {
                "ready": True,
                "desktop": {"surface": "PySide6 Qt", "available": True},
                "template": {"template_id": "V6测试模板", "available": True},
                "pump_profiles": {"pump_water": {}, "pump_chemical": {}},
            }

            def fake_run(command, **kwargs):
                if command == ["fake-pyinstaller"]:
                    executable.parent.mkdir(parents=True)
                    executable.write_bytes(b"native executable")
                    return SimpleNamespace(returncode=0)
                self.assertEqual(command, [str(executable), "--status"])
                self.assertTrue(kwargs["text"])
                self.assertEqual(kwargs["encoding"], "utf-8")
                self.assertEqual(kwargs["env"]["PYTHONIOENCODING"], "utf-8")
                return SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps(status_payload, ensure_ascii=False),
                    stderr="",
                )

            with (
                patch("tools.build_native.build_native_command", return_value=(["fake-pyinstaller"], executable)),
                patch("tools.build_native.build_lock", return_value=nullcontext()),
                patch("tools.build_native.audit_artifact", return_value=SimpleNamespace(is_valid=True, errors=[])),
                patch("tools.build_native.subprocess.run", side_effect=fake_run),
            ):
                result = build_native(root, tool="fake-pyinstaller")

        self.assertTrue(result["status_ready"])
        self.assertTrue(result["qt_environment"]["template_available"])

    def test_main_fails_and_preserves_report_without_zip_when_status_is_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zip_path = root / "native.zip"
            report_path = root / "native-report.json"
            failed_result = {
                "executable": str(root / "equipeffi.exe"),
                "status_ready": False,
                "status_smoke_error": "QtWidgets 加载失败",
            }
            stdout = io.StringIO()
            with (
                patch("tools.build_native.build_native", return_value=failed_result),
                patch("tools.build_native.package_native") as package_mock,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--root",
                        str(root),
                        "--output-dir",
                        str(root / "build"),
                        "--zip-output",
                        str(zip_path),
                        "--report",
                        str(report_path),
                    ]
                )

            self.assertEqual(exit_code, 1)
            package_mock.assert_not_called()
            self.assertFalse(zip_path.exists())
            output_payload = json.loads(stdout.getvalue())
            report_payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(output_payload["status_smoke_error"], "QtWidgets 加载失败")
            self.assertIn("未生成 native ZIP", output_payload["package_error"])
            self.assertEqual(report_payload, output_payload)

    def test_windows_command_adds_only_declared_runtime_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            command, executable = build_native_command(
                ROOT,
                Path(tmp),
                tool="pyinstaller.exe",
                path_separator=";",
            )
        self.assertIn("--onedir", command)
        self.assertIn("--collect-submodules", command)
        data_args = [command[index + 1] for index, item in enumerate(command[:-1]) if item == "--add-data"]
        expected_args = set()
        package = ROOT / "src" / "equipeffi"
        for asset in runtime_asset_paths(ROOT):
            relative_parent = asset.relative_to(package).parent.as_posix()
            destination = f"equipeffi/{relative_parent}" if relative_parent != "." else "equipeffi"
            expected_args.add(f"{asset};{destination}")
        self.assertEqual(set(data_args), expected_args)
        self.assertEqual(len(data_args), len(expected_args))
        self.assertFalse(any("resources;equipeffi/resources" in item for item in command))
        self.assertIn(str(ROOT / "tools" / "native_entrypoint.py"), command)
        self.assertEqual(executable.name, "equipeffi.exe")

    def test_linux_command_uses_colon_and_platform_launcher_name(self):
        command, executable = build_native_command(
            ROOT,
            ROOT / "tmp" / "native-test",
            tool="pyinstaller",
            path_separator=":",
        )
        data_args = [command[index + 1] for index, item in enumerate(command[:-1]) if item == "--add-data"]
        self.assertTrue(any(f"{ROOT / 'src' / 'equipeffi' / 'standard_manifest.json'}:equipeffi" == item for item in data_args))
        self.assertTrue(any(f"{ROOT / 'src' / 'equipeffi' / 'resources' / 'standards' / 'pump.json'}:" in item for item in data_args))
        self.assertEqual(executable.name, "equipeffi")
        self.assertNotEqual(executable.suffix.lower(), ".exe")

    def test_native_package_is_stable_and_contains_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "dist" / "equipeffi"
            bundle.mkdir(parents=True)
            (bundle / "equipeffi.exe").write_bytes(b"launcher")
            (bundle / "_internal").mkdir()
            (bundle / "_internal" / "data.json").write_bytes(b"data")
            report = root / "native-windows-build.json"
            report.write_text("{}", encoding="utf-8")
            first = package_native(bundle / "equipeffi.exe", root / "one.zip", report=report)
            second = package_native(bundle / "equipeffi.exe", root / "two.zip", report=report)
            self.assertEqual(first["sha256"], second["sha256"])
            self.assertEqual(first["members"], second["members"])
            with zipfile.ZipFile(root / "one.zip") as archive:
                self.assertIn("equipeffi/equipeffi.exe", archive.namelist())
                self.assertIn("equipeffi/_internal/data.json", archive.namelist())
                self.assertIn("native-windows-build.json", archive.namelist())


if __name__ == "__main__":
    unittest.main()
