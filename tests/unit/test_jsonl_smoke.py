from __future__ import annotations

import unittest
from pathlib import Path

from tools.smoke_jsonl import run_smoke


ROOT = Path(__file__).resolve().parents[2]


class JsonlSmokeToolTests(unittest.TestCase):
    def test_source_entrypoint_protocol_smoke(self):
        result = run_smoke(root=ROOT, timeout=10)
        self.assertTrue(result["passed"])
        self.assertEqual(result["protocol_version"], "1.0")
        self.assertEqual(result["public_device_type_count"], 15)
        self.assertTrue(result["schema_conclusions_verified"])
        self.assertTrue(result["schema_result_fields_verified"])
        self.assertEqual(result["pmsm_status_verified"], "active")
        self.assertIn(result["pmsm_conclusion"], {"1级", "2级", "3级", "未达标", "不在范围", "无法判定"})
        self.assertEqual(result["pmsm_no_data_conclusion"], "不在范围")

    def test_source_entrypoint_runs_in_isolated_python_mode(self):
        result = run_smoke(root=ROOT, timeout=10, isolated=True)
        self.assertTrue(result["passed"])
        self.assertTrue(result["isolated"])


if __name__ == "__main__":
    unittest.main()
