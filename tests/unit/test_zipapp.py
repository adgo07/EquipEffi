from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from tools.build_zipapp import build_zipapp


ROOT = Path(__file__).resolve().parents[2]


class ZipappTests(unittest.TestCase):
    def test_zipapp_contains_package_resources_and_runs_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = build_zipapp(ROOT, Path(tmp) / "equipeffi.pyz")
            with zipfile.ZipFile(output) as archive:
                self.assertIn("__main__.py", archive.namelist())
                self.assertIn("equipeffi/standard_manifest.json", archive.namelist())
                self.assertIn("equipeffi/resources/elimination_catalog_batches_1_4.json", archive.namelist())
                self.assertIn("equipeffi/resources/elimination_catalog_industry_2024.json", archive.namelist())
            completed = subprocess.run(
                [sys.executable, str(output), "--status"],
                cwd=tmp,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn('"public_device_type_count": 15', completed.stdout)
            self.assertIn('"entry_count": 124', completed.stdout)

    def test_zipapp_is_byte_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = build_zipapp(ROOT, Path(tmp) / "one.pyz")
            second = build_zipapp(ROOT, Path(tmp) / "two.pyz")
            self.assertEqual(first.read_bytes(), second.read_bytes())


if __name__ == "__main__":
    unittest.main()
