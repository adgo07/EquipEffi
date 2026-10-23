from __future__ import annotations

import os
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
            env = dict(os.environ)
            env["PYTHONIOENCODING"] = "utf-8"
            with zipfile.ZipFile(output) as archive:
                self.assertIn("__main__.py", archive.namelist())
                self.assertIn("equipeffi/standard_manifest.json", archive.namelist())
                self.assertIn("equipeffi/resources/elimination_catalog_batches_1_4.json", archive.namelist())
                self.assertIn("equipeffi/resources/elimination_catalog_industry_2024.json", archive.namelist())
                self.assertIn("equipeffi/resources/templates/设备能效分析空白模板_重构版V6_20261005.xlsx", archive.namelist())
                self.assertNotIn("equipeffi/resources/README.md", archive.namelist())
                self.assertNotIn("equipeffi/resources/standards/README.md", archive.namelist())
            completed = subprocess.run(
                [sys.executable, str(output), "--status"],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            payload = __import__("json").loads(completed.stdout)
            # .pyz uses the host's installed desktop extra; native-package Qt
            # validation is performed separately against the built executable.
            self.assertEqual(payload["desktop"]["surface"], "PySide6 Qt")
            self.assertTrue(payload["desktop"]["available"])
            self.assertIn("template_id", payload["template"])
            self.assertIn("template_version", payload["template"])
            self.assertEqual(set(payload["pump_profiles"]), {"pump_water", "pump_chemical"})
            self.assertTrue(all(
                profile["available"] and profile["support_status"] == "SUPPORTED"
                and profile["pack_id"]
                for profile in payload["pump_profiles"].values()
            ))
            expected_ready = (
                payload["desktop"]["available"]
                and payload["template"]["available"]
                and all(profile["available"] for profile in payload["pump_profiles"].values())
            )
            self.assertTrue(expected_ready)
            self.assertEqual(payload["ready"], expected_ready)
            self.assertEqual(completed.returncode, 0 if expected_ready else 1)

    def test_zipapp_is_byte_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = build_zipapp(ROOT, Path(tmp) / "one.pyz")
            second = build_zipapp(ROOT, Path(tmp) / "two.pyz")
            self.assertEqual(first.read_bytes(), second.read_bytes())


if __name__ == "__main__":
    unittest.main()
