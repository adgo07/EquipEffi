from __future__ import annotations

import json
from pathlib import Path
import unittest

from tools.render_pmsm_review_pages import _page_table_map, _table_summary


ROOT = Path(__file__).resolve().parents[2]


class PmsmRenderPagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "src" / "equipeffi" / "resources" / "standards" / "gb30253_2024_pdf_verified_v1.json"
        cls.pack = json.loads(path.read_text(encoding="utf-8"))

    def test_pdf_page_index_covers_all_tables_and_pages(self):
        pages, page_tables = _page_table_map(self.pack)
        self.assertEqual(len(self.pack["tables"]), 29)
        self.assertEqual(pages[0], 7)
        self.assertEqual(pages[-1], 51)
        self.assertEqual(len(pages), 45)
        self.assertEqual({table["table_no"] for table in page_tables[7]}, {1})
        self.assertIn(29, {table["table_no"] for table in page_tables[51]})

    def test_table_summary_preserves_no_data_and_suspicious_counts(self):
        table = {
            "table_no": 1,
            "product": "异步起动",
            "mode": "poles",
            "pages": [7, 8],
            "rows": [
                {"suspicious_cells": [0, 1], "no_data_cells": [5, 12, 19]},
                {"suspicious_cells": [], "no_data_cells": []},
            ],
        }
        summary = _table_summary(table)
        self.assertEqual(summary["row_count"], 2)
        self.assertEqual(summary["suspicious_cell_count"], 2)
        self.assertEqual(summary["no_data_cell_count"], 3)


if __name__ == "__main__":
    unittest.main()
