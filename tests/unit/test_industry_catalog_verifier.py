from __future__ import annotations

import unittest

from tools.verify_industry_catalog import render_report


class IndustryCatalogVerifierTests(unittest.TestCase):
    def test_human_report_contains_pdf_and_resource_counts(self):
        report = render_report({
            "pdf": "industry.pdf",
            "sha256": "ABC",
            "expected_count": 13,
            "verified_count": 13,
            "resource_entry_count": 13,
            "missing_resource_ids": [],
            "extra_resource_ids": [],
            "duplicate_resource_ids": [],
            "results": [],
        })
        self.assertIn("PDF核对结果：13/13", report)
        self.assertIn("机器资源规则数：13；清单缺失ID：0；多余ID：0；重复ID：0", report)

    def test_human_report_exposes_stale_or_duplicate_rule_ids(self):
        report = render_report({
            "pdf": "industry.pdf",
            "sha256": "ABC",
            "expected_count": 13,
            "verified_count": 13,
            "resource_entry_count": 14,
            "missing_resource_ids": ["IND2024-MOTOR-YB"],
            "extra_resource_ids": ["STALE"],
            "duplicate_resource_ids": ["DUP"],
            "results": [],
        })
        self.assertIn("清单缺失ID：1；多余ID：1；重复ID：1", report)


if __name__ == "__main__":
    unittest.main()
