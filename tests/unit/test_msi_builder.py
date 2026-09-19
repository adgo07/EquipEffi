from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from tools.build_msi import build_msi, generate_wix_source


class MsiBuilderTests(unittest.TestCase):
    def test_generates_deterministic_wix_components_from_onedir(self):
        with tempfile.TemporaryDirectory() as tmp:
            native = Path(tmp) / "equipeffi"
            native.mkdir()
            (native / "equipeffi.exe").write_bytes(b"launcher")
            (native / "_internal").mkdir()
            (native / "_internal" / "data.json").write_text("{}", encoding="utf-8")
            first = Path(tmp) / "one.wxs"
            second = Path(tmp) / "two.wxs"
            a = generate_wix_source(native, first)
            b = generate_wix_source(native, second)
            self.assertEqual(a["file_count"], 2)
            self.assertEqual(a["component_count"], 2)
            self.assertEqual(a["wix_source_sha256"], b["wix_source_sha256"])
            self.assertEqual(first.read_bytes(), second.read_bytes())
            root = ET.parse(first).getroot()
            self.assertEqual(sum(1 for item in root.iter() if item.tag.endswith("Component")), 2)
            self.assertIn("INSTALLFOLDER", first.read_text(encoding="utf-8"))

    def test_dry_run_writes_report_without_msi(self):
        with tempfile.TemporaryDirectory() as tmp:
            native = Path(tmp) / "equipeffi"
            native.mkdir()
            (native / "equipeffi.exe").write_bytes(b"launcher")
            output = Path(tmp) / "equipeffi.msi"
            result = build_msi(native, output, dry_run=True)
            self.assertFalse(result.built)
            self.assertFalse(output.exists())
            report = json.loads(result.report.read_text(encoding="utf-8"))
            self.assertTrue(report["dry_run"])
            self.assertEqual(report["file_count"], 1)

    def test_requires_windows_entrypoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                generate_wix_source(Path(tmp), Path(tmp) / "missing.wxs")


if __name__ == "__main__":
    unittest.main()
