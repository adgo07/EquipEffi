from __future__ import annotations

import math
from pathlib import Path
import unittest

from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository, StandardPackError
from equipeffi.infrastructure.standards.pack_validator import StandardPackValidator


ROOT = Path(__file__).resolve().parents[2]


class StandardPackValidatorTests(unittest.TestCase):
    def test_all_manifest_packs_pass_conservative_structure_validation(self):
        repository = JsonStandardRepository(ROOT)
        validator = StandardPackValidator()
        for entry in repository.list_packs():
            with self.subTest(device_type=entry["device_type"]):
                pack = repository.get_pack(entry["device_type"])
                self.assertEqual(validator.validate(pack), [])

    def test_rejects_unknown_status_and_nonfinite_numbers(self):
        errors = StandardPackValidator().validate({
            "standard_code": "TEST",
            "standard_name": "测试",
            "status": "published",
            "rows": [{"data_id": "A", "value": math.nan}],
        })
        self.assertTrue(any("status" in error for error in errors))
        self.assertTrue(any("非有限数" in error for error in errors))

    def test_rejects_duplicate_data_ids(self):
        errors = StandardPackValidator().validate({
            "standard_code": "TEST",
            "standard_name": "测试",
            "rows": [{"data_id": "A"}, {"data_id": "A"}],
        })
        self.assertTrue(any("重复data_id" in error for error in errors))

    def test_rejects_duplicate_data_ids_across_standard_tables(self):
        errors = StandardPackValidator().validate({
            "standard_code": "TEST",
            "standard_name": "测试",
            "tables": [
                {"rows": [{"data_id": "SHARED", "value": 1}]},
                {"rows": [{"data_id": "SHARED", "value": 2}]},
            ],
        })
        self.assertTrue(any("标准数据包存在重复data_id" in error for error in errors))

    def test_rejects_active_pack_with_unreviewed_cells(self):
        errors = StandardPackValidator().validate({
            "standard_code": "TEST",
            "standard_name": "测试",
            "status": "active",
            "tables": [{"rows": [{"suspicious_cells": [12]}]}],
        })
        self.assertTrue(any("suspicious_cells" in error for error in errors))

    def test_rejects_malformed_no_data_cell_metadata(self):
        errors = StandardPackValidator().validate({
            "standard_code": "TEST",
            "standard_name": "测试",
            "status": "normalized",
            "tables": [{
                "dims": [2, 4],
                "rows": [{
                    "efficiency": {"1": [90, None]},
                    "no_data_cells": [0, 1, 1],
                    "suspicious_cells": [1],
                }],
            }],
        })
        self.assertTrue(any("缺少no_data_reason" in error for error in errors))
        self.assertTrue(any("对应值必须为空" in error for error in errors))
        self.assertTrue(any("重复索引" in error for error in errors))
        self.assertTrue(any("与suspicious_cells重复" in error for error in errors))

    def test_repository_raises_for_invalid_loaded_pack(self):
        repository = JsonStandardRepository(ROOT)
        repository._validator = StandardPackValidator()
        original = repository._validator.validate
        repository._validator.validate = lambda _pack: ["测试结构错误"]
        try:
            with self.assertRaises(StandardPackError):
                repository.get_pack("transformer")
        finally:
            repository._validator.validate = original


if __name__ == "__main__":
    unittest.main()
