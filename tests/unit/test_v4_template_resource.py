from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from equipeffi.infrastructure.excel.template_resource import REQUIRED_V4_SHEETS, V4TemplateResource


ROOT = Path(__file__).resolve().parents[2]


class V4TemplateResourceTests(unittest.TestCase):
    def test_bundled_template_has_v4_sheet_structure(self):
        resource = V4TemplateResource()
        result = resource.validate()
        self.assertTrue(result.is_valid, result.message)
        self.assertEqual(result.missing_sheets, ())
        self.assertEqual(len(result.sheet_names), len(REQUIRED_V4_SHEETS))
        self.assertEqual(len(resource.fingerprint()), 64)

    def test_download_copies_to_new_file_without_overwriting_source(self):
        resource = V4TemplateResource()
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "V4结果输入模板.xlsx"
            output = resource.download_to(destination)
            self.assertEqual(output, destination)
            self.assertTrue(destination.is_file())
            copied = resource.validate(destination)
            self.assertTrue(copied.is_valid, copied.message)
            self.assertEqual(copied.sha256, resource.fingerprint())


if __name__ == "__main__":
    unittest.main()
