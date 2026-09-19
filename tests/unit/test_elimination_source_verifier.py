import json
import tempfile
import unittest
from pathlib import Path

from docx import Document

from tools.extract_elimination_catalogs import sha256
from tools.verify_elimination_sources import verify


class EliminationSourceVerifierTests(unittest.TestCase):
    def _docx(self, path: Path, batch: int) -> None:
        document = Document()
        table = document.add_table(rows=1, cols=3 if batch < 3 else 6)
        headers = ["序号", "产品名称", "淘汰理由"] + (["型号", "规格", "适用范围"] if batch >= 3 else [])
        for cell, value in zip(table.rows[0].cells, headers):
            cell.text = value
        row = table.add_row().cells
        row[0].text = "1-1"
        row[1].text = "测试产品"
        row[2].text = "测试理由"
        if batch >= 3:
            row[3].text = "TEST-1"
            row[4].text = "测试规格"
            row[5].text = "测试范围"
        document.save(path)

    def test_verifies_hashes_and_extracted_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = {
                1: "高耗能机电设备淘汰目录(第一批).docx",
                2: "第二批.docx",
                3: "第三批.docx",
                4: "高耗能落后机电设备（产品）淘汰目录(第四批).docx",
            }
            sources = []
            entries = []
            for batch, name in names.items():
                path = root / name
                self._docx(path, batch)
                sources.append({"batch": batch, "file": name, "sha256": sha256(path), "entry_count": 1})
                entries.append({"batch": f"第{'一二三四'[batch - 1]}批"})
            catalog = root / "catalog.json"
            catalog.write_text(json.dumps({"status": "normalized", "sources": sources, "entries": entries}), encoding="utf-8")
            report = verify(root, catalog)
            self.assertTrue(report["is_valid"], report["errors"])
            self.assertEqual(report["catalog_entry_count"], 4)
            (root / names[2]).write_bytes((root / names[2]).read_bytes() + b"changed")
            changed = verify(root, catalog)
            self.assertFalse(changed["is_valid"])
            self.assertTrue(any("SHA-256" in error for error in changed["errors"]))


if __name__ == "__main__":
    unittest.main()
