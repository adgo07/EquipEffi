from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.audit_standard_provenance import audit


class StandardProvenanceAuditTests(unittest.TestCase):
    def test_current_manifest_has_complete_provenance_for_all_seventeen_packs(self):
        """生产标准清单的追溯字段必须持续完整，避免后续整理丢失来源。"""
        report = audit()
        self.assertEqual(report["pack_count"], 17)
        self.assertEqual(report["packs_with_complete_record_id_and_page"], 17)
        self.assertEqual(report["warnings"], [])
        self.assertEqual(sum(item["record_count"] for item in report["packs"]), 4996)
        for item in report["packs"]:
            with self.subTest(device_type=item["device_type"]):
                self.assertEqual(item["records_with_id"], item["record_count"])
                self.assertEqual(item["records_with_page"], item["record_count"])
                self.assertNotEqual(Path(item["resource"]).name, "motor_pmsm.json")
        pmsm = next(item for item in report["packs"] if item["device_type"] == "motor_pmsm")
        self.assertEqual(pmsm["pack_id"], "gb30253_2024_pdf_verified_v1")

    def test_audit_reports_record_id_and_page_coverage_without_guessing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "pack.json"
            package.write_text(
                json.dumps(
                    {
                        "standard_code": "TEST",
                        "rows": [
                            {"data_id": "A", "source_page": 3, "efficiency": 98},
                            {"efficiency": 97},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            manifest = root / "standard_manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "packs": [
                            {
                                "device_type": "test",
                                "standard_code": "TEST",
                                "pack_id": "test-v1",
                                "source": "pack.json",
                                "status": "active",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            report = audit(manifest)
            item = report["packs"][0]
            self.assertEqual(item["record_count"], 2)
            self.assertEqual(item["records_with_id"], 1)
            self.assertEqual(item["records_with_page"], 1)
            self.assertEqual(item["records_with_id_and_page"], 1)
            self.assertEqual(item["missing_record_id_count"], 1)
            self.assertEqual(item["missing_record_page_count"], 1)
            self.assertEqual(report["packs_with_complete_record_id_and_page"], 0)

    def test_activation_review_metadata_is_not_counted_as_standard_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "pack.json"
            package.write_text(
                json.dumps(
                    {
                        "standard_code": "TEST",
                        "tables": [{"rows": [{"data_id": "A", "source_page": 3, "efficiency": {"1": [98]}}]}],
                        "activation_review": [
                            {"table_no": 1, "power_kw": 55, "level": "1级", "no_data": True, "pdf_page": 7}
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            manifest = root / "standard_manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "packs": [
                            {
                                "device_type": "test",
                                "standard_code": "TEST",
                                "pack_id": "test-v1",
                                "source": "pack.json",
                                "status": "active",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            item = audit(manifest)["packs"][0]
            self.assertEqual(item["record_count"], 1)
            self.assertEqual(item["records_with_id"], 1)
            self.assertEqual(item["missing_record_id_count"], 0)


if __name__ == "__main__":
    unittest.main()
