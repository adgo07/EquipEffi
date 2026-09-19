from __future__ import annotations

from pathlib import Path
import unittest

from tools.validate_android_skeleton import validate


ROOT = Path(__file__).resolve().parents[2] / "android"


class AndroidSkeletonTests(unittest.TestCase):
    def test_android_project_structure_is_valid_without_sdk(self):
        result = validate(ROOT)
        self.assertTrue(result["is_valid"], result["errors"])
        self.assertTrue(result["checks"]["modules_declared"])
        self.assertTrue(result["checks"]["bridge_dependency"])
        self.assertTrue(result["checks"]["protocol_client"])
        self.assertFalse(result["checks"]["bundled_business_data"])


if __name__ == "__main__":
    unittest.main()
