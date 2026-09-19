from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.build_native import build_native_command, package_native


ROOT = Path(__file__).resolve().parents[2]


class NativeBuildTests(unittest.TestCase):
    def test_windows_command_contains_all_packaged_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            command, executable = build_native_command(
                ROOT,
                Path(tmp),
                tool="pyinstaller.exe",
                path_separator=";",
            )
        self.assertIn("--onedir", command)
        self.assertIn("--collect-submodules", command)
        self.assertTrue(any("standard_manifest.json;equipeffi" in item for item in command))
        self.assertTrue(any("resources;equipeffi/resources" in item for item in command))
        self.assertTrue(command[-1].endswith("tools\\native_entrypoint.py"))
        self.assertEqual(executable.name, "equipeffi.exe")

    def test_linux_command_uses_colon_and_platform_launcher_name(self):
        command, executable = build_native_command(
            ROOT,
            ROOT / "tmp" / "native-test",
            tool="pyinstaller",
            path_separator=":",
        )
        self.assertTrue(any("standard_manifest.json:equipeffi" in item for item in command))
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
