from __future__ import annotations

from pathlib import Path
import unittest

from tools.build_pmsm_review_queue import DEFAULT_SOURCE, build_report


class PmsmReviewQueueTests(unittest.TestCase):
    def test_queue_covers_all_tables_and_confirmed_no_data_cell(self):
        report = build_report(DEFAULT_SOURCE)
        self.assertIn("结构化表数：29", report)
        self.assertIn("已确认无数据单元格", report)
        self.assertIn("表1｜55.0 kW｜1级｜维度12", report)
        self.assertIn("按标准原文无数据处理", report)
        self.assertIn("命中时按用户复核结果判定为‘不在范围’", report)

    def test_queue_source_is_independent_pdf_rebuild_pack(self):
        self.assertTrue(Path(DEFAULT_SOURCE).name.startswith("gb30253_2024_pdf_verified_v1"))


if __name__ == "__main__":
    unittest.main()
