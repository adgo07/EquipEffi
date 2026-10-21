from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.build_portable_bundle import build_bundle
from tools.check_distribution_assets import runtime_asset_members


ROOT = Path(__file__).resolve().parents[2]
RETIRED_MEMBERS = {
    "scripts/install_linux_service.sh",
    "scripts/equipeffi-web.service.template",
    "scripts/run_jsonl_windows.ps1",
    "scripts/run_jsonl_linux.sh",
    "scripts/run_web_windows.ps1",
    "scripts/run_web_linux.sh",
    "tools/smoke_jsonl.py",
    "tools/validate_android_skeleton.py",
    "docs/10_跨平台运行与模块边界.md",
    "docs/11_JSONL协议与Android桥接.md",
}


def _write_current_runtime_wheel(path: Path) -> Path:
    """Create a package-data fixture without reusing a historical V4 wheel."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for member, source in runtime_asset_members(ROOT).items():
            archive.write(source, member)
    return path


class PortableBundleTests(unittest.TestCase):
    def test_bundle_contains_runtime_files_and_checksums(self):
        with tempfile.TemporaryDirectory() as tmp:
            wheel = _write_current_runtime_wheel(Path(tmp) / "equipeffi-0.2.1-py3-none-any.whl")
            result = build_bundle(wheel, Path(tmp) / "portable.zip", root=ROOT)
            self.assertTrue(result.path.is_file())
            with zipfile.ZipFile(result.path) as archive:
                names = set(archive.namelist())
                self.assertIn(wheel.name, names)
                self.assertIn("scripts/install_windows.ps1", names)
                self.assertIn("scripts/install_native_windows.ps1", names)
                self.assertIn("scripts/install_linux.sh", names)
                self.assertIn("scripts/README.md", names)
                self.assertIn("tools/validate_portable_bundle.py", names)
                self.assertIn("SHA256SUMS.txt", names)
                self.assertIn("运行说明.txt", names)
                self.assertFalse(RETIRED_MEMBERS & names)
                self.assertFalse(any(name.startswith("android/") for name in names))
                self.assertFalse(any(name.lower().endswith(".xlsx") and "v4" in name.lower()
                                     for name in names))
                checksums = archive.read("SHA256SUMS.txt").decode("utf-8")
                expected = sha256(wheel.read_bytes()).hexdigest()
                self.assertIn(f"{expected}  {wheel.name}", checksums)
                notes = archive.read("运行说明.txt").decode("utf-8")
                self.assertIn("headless", notes)
                self.assertIn("PySide6 Qt", notes)
                self.assertIn("desktop extra", notes)
                self.assertNotIn("--jsonl", notes)
                self.assertNotIn("--web", notes)
            self.assertEqual(tuple(sorted(names)), result.members)

    def test_bundle_rejects_non_wheel(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "not-wheel.txt"
            source.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                build_bundle(source, Path(tmp) / "portable.zip", root=ROOT)

    def test_bundle_is_byte_stable_for_same_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            wheel = _write_current_runtime_wheel(Path(tmp) / "equipeffi-0.2.1-py3-none-any.whl")
            first = build_bundle(wheel, Path(tmp) / "one.zip", root=ROOT)
            second = build_bundle(wheel, Path(tmp) / "two.zip", root=ROOT)
            self.assertEqual(first.sha256, second.sha256)
            self.assertEqual(first.path.read_bytes(), second.path.read_bytes())

    def test_bundle_can_include_zipapp_and_mentions_direct_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            wheel = _write_current_runtime_wheel(Path(tmp) / "equipeffi-0.2.1-py3-none-any.whl")
            zipapp = Path(tmp) / "equipeffi.pyz"
            zipapp.write_bytes(b"pyz")
            output = build_bundle(wheel, Path(tmp) / "portable.zip", root=ROOT, zipapp=zipapp)
            with zipfile.ZipFile(output.path) as archive:
                self.assertIn("equipeffi.pyz", archive.namelist())
                notes = archive.read("运行说明.txt").decode("utf-8")
                self.assertIn("python equipeffi.pyz --status", notes)
                self.assertNotIn("--jsonl", notes)
                self.assertNotIn("--web", notes)


if __name__ == "__main__":
    unittest.main()
