from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.build_native import build_native_command, package_native
from tools.check_distribution_assets import runtime_asset_paths


ROOT = Path(__file__).resolve().parents[2]


class NativeBuildTests(unittest.TestCase):
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
