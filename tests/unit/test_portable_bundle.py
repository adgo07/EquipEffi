from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.build_portable_bundle import build_bundle


ROOT = Path(__file__).resolve().parents[2]


class PortableBundleTests(unittest.TestCase):
    def test_bundle_contains_runtime_files_and_checksums(self):
        wheel = ROOT / "tmp" / "release-20260826" / "equipeffi-0.2.1-py3-none-any.whl"
        if not wheel.is_file():
            self.skipTest("release wheel尚未构建")
        with tempfile.TemporaryDirectory() as tmp:
            result = build_bundle(wheel, Path(tmp) / "portable.zip", root=ROOT)
            self.assertTrue(result.path.is_file())
            with zipfile.ZipFile(result.path) as archive:
                names = set(archive.namelist())
                self.assertIn(wheel.name, names)
                self.assertIn("scripts/install_windows.ps1", names)
                self.assertIn("scripts/install_native_windows.ps1", names)
                self.assertIn("scripts/install_linux.sh", names)
                self.assertIn("scripts/install_linux_service.sh", names)
                self.assertIn("scripts/equipeffi-web.service.template", names)
                self.assertIn("scripts/run_jsonl_windows.ps1", names)
                self.assertIn("scripts/run_jsonl_linux.sh", names)
                self.assertIn("scripts/run_web_windows.ps1", names)
                self.assertIn("scripts/run_web_linux.sh", names)
                self.assertIn("scripts/run_web_windows.ps1", names)
                self.assertIn("tools/smoke_jsonl.py", names)
                self.assertIn("tools/validate_portable_bundle.py", names)
                self.assertIn("tools/validate_android_skeleton.py", names)
                self.assertIn("SHA256SUMS.txt", names)
                self.assertIn("运行说明.txt", names)
                self.assertIn("docs/11_JSONL协议与Android桥接.md", names)
                self.assertIn("android/README.md", names)
                self.assertIn("android/settings.gradle.kts", names)
                self.assertIn("android/app/build.gradle.kts", names)
                self.assertIn("android/app/src/main/AndroidManifest.xml", names)
                self.assertIn(
                    "android/app/src/main/kotlin/com/equipeffi/android/MainActivity.kt",
                    names,
                )
                self.assertIn(
                    "android/bridge/src/main/kotlin/com/equipeffi/bridge/JsonlBridgeClient.kt",
                    names,
                )
                checksums = archive.read("SHA256SUMS.txt").decode("utf-8")
                expected = sha256(wheel.read_bytes()).hexdigest()
                self.assertIn(f"{expected}  {wheel.name}", checksums)
                notes = archive.read("运行说明.txt").decode("utf-8")
                self.assertNotIn("-PyzPath .\\\n", notes)
                self.assertNotIn("run_jsonl_linux.sh ./\n", notes)
                self.assertIn("run_web_windows.ps1 -OpenBrowser", notes)
                self.assertIn("run_web_linux.sh", notes)
            self.assertEqual(tuple(sorted(names)), result.members)

    def test_bundle_rejects_non_wheel(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "not-wheel.txt"
            source.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                build_bundle(source, Path(tmp) / "portable.zip", root=ROOT)

    def test_bundle_is_byte_stable_for_same_inputs(self):
        wheel = ROOT / "tmp" / "release-20260826" / "equipeffi-0.2.1-py3-none-any.whl"
        if not wheel.is_file():
            self.skipTest("release wheel尚未构建")
        with tempfile.TemporaryDirectory() as tmp:
            first = build_bundle(wheel, Path(tmp) / "one.zip", root=ROOT)
            second = build_bundle(wheel, Path(tmp) / "two.zip", root=ROOT)
            self.assertEqual(first.sha256, second.sha256)
            self.assertEqual(first.path.read_bytes(), second.path.read_bytes())

    def test_bundle_can_include_zipapp_and_mentions_direct_command(self):
        wheel = ROOT / "tmp" / "release-20260826" / "equipeffi-0.2.1-py3-none-any.whl"
        if not wheel.is_file():
            self.skipTest("release wheel尚未构建")
        with tempfile.TemporaryDirectory() as tmp:
            zipapp = Path(tmp) / "equipeffi.pyz"
            zipapp.write_bytes(b"pyz")
            output = build_bundle(wheel, Path(tmp) / "portable.zip", root=ROOT, zipapp=zipapp)
            with zipfile.ZipFile(output.path) as archive:
                self.assertIn("equipeffi.pyz", archive.namelist())
                notes = archive.read("运行说明.txt").decode("utf-8")
                self.assertIn("python equipeffi.pyz --status", notes)
                self.assertIn("python -m equipeffi --jsonl", notes)
                self.assertIn("python tools/smoke_jsonl.py --pyz", notes)


if __name__ == "__main__":
    unittest.main()
