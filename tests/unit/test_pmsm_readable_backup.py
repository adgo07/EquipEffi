from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools.export_pmsm_readable_backup import export


ROOT = Path(__file__).resolve().parents[2]


class PmsmReadableBackupTests(unittest.TestCase):
    def test_export_contains_all_tables_and_confirmed_no_data(self):
        pack = ROOT / "src" / "equipeffi" / "resources" / "standards" / "gb30253_2024_pdf_verified_v1.json"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "pmsm.md"
            result = export(pack, output)
            self.assertEqual(result["table_count"], 29)
            text = output.read_text(encoding="utf-8")
            self.assertEqual(sum("—（无数据）" in line and line.startswith("|") for line in text.splitlines()), 3)
            self.assertIn("| 55.0 |", text)
            self.assertIn("状态：active", text)


if __name__ == "__main__":
    unittest.main()
