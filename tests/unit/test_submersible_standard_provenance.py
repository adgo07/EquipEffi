from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
RESOURCE = ROOT / "src" / "equipeffi" / "resources" / "standards" / "submersible.json"


class SubmersibleStandardProvenanceTests(unittest.TestCase):
    """锁定GB 32030-2022表级页码及关键“—/偏移”结构，防止误改标准包。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.pack = json.loads(RESOURCE.read_text(encoding="utf-8"))

    def test_all_pdf_tables_have_expected_page_ranges(self):
        pages = {table["name"]: table.get("source_pages") for table in self.pack["tables"]}
        self.assertEqual(
            pages,
            {"表1": "4", "表2": "4-5", "表3": "5-6", "表4": "6", "表6": "7-8"},
        )
        self.assertEqual({table["name"] for table in self.pack["tables"]}, {"表1", "表2", "表3", "表4", "表6"})

    def test_table_shapes_and_dash_cells_match_pdf(self):
        by_name = {table["name"]: table for table in self.pack["tables"]}
        self.assertEqual(by_name["表1"]["power_ranges"], ["P_N≤3", "3<P_N≤11", "11<P_N≤22"])
        self.assertEqual(by_name["表2"]["power_ranges"][0], "22<P_N≤100")
        # 表1的3～11 kW档对QDX/QD的1、2级为“—”，3级由ηDB−Δη给出；
        # None只表示该等级不作要求，不能在标准包中被改成0。
        self.assertIsNone(by_name["表1"]["offsets"]["1"][1])
        self.assertIsNone(by_name["表1"]["offsets"]["2"][1])
        self.assertIsNone(by_name["表1"]["offsets"]["3"])
        self.assertEqual(by_name["表1"]["offsets"]["1"][0], [2.0, 3.0, 2.5, 2.0, 1.5, 2.5, 3.0])
        self.assertEqual(by_name["表3"]["offsets"]["1"][0], [2.0, None, None, 4.0])
        self.assertEqual(by_name["表6"]["offsets"]["2"][-1], [1.8, 1.5])


if __name__ == "__main__":
    unittest.main()
