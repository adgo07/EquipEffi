"""Integrity checks for the frozen-source-derived transformer runtime pack."""

from __future__ import annotations

import json
import posixpath
import sys
import xml.etree.ElementTree as ET
import zipfile
from decimal import Decimal
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.build_transformer_v21_pack import (  # noqa: E402
    DEFAULT_OUTPUT,
    MAPPING_RELATIVE_PATH,
    WORKBOOK_RELATIVE_PATH,
    build_pack,
    verify_pack_integrity,
)


PACK_PATH = ROOT / DEFAULT_OUTPUT
WORKBOOK_PATH = ROOT / WORKBOOK_RELATIVE_PATH
NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def qname(namespace: str, local_name: str) -> str:
    return f"{{{namespace}}}{local_name}"


def column_of(address: str) -> str:
    return "".join(character for character in address if character.isalpha())


def read_source_cells() -> dict[tuple[str, int], dict[str, str]]:
    """Read source cell lexemes independently of the production derivation code."""
    with zipfile.ZipFile(WORKBOOK_PATH) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall(qname(NS_PACKAGE_REL, "Relationship"))
        }
        sheet_paths: dict[str, str] = {}
        for sheet in workbook.findall(
            f"{qname(NS_MAIN, 'sheets')}/{qname(NS_MAIN, 'sheet')}"
        ):
            target = targets[sheet.attrib[qname(NS_REL, "id")]]
            sheet_paths[sheet.attrib["name"]] = (
                target.lstrip("/")
                if target.startswith("/")
                else posixpath.normpath(posixpath.join("xl", target))
            )

        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = [
                "".join(node.text or "" for node in item.iter(qname(NS_MAIN, "t")))
                for item in shared_root.findall(qname(NS_MAIN, "si"))
            ]

        all_rows: dict[tuple[str, int], dict[str, str]] = {}
        for table_no in range(1, 36):
            sheet_name = f"表{table_no:02d}"
            sheet_root = ET.fromstring(archive.read(sheet_paths[sheet_name]))
            for row in sheet_root.findall(
                f"{qname(NS_MAIN, 'sheetData')}/{qname(NS_MAIN, 'row')}"
            ):
                row_number = int(row.attrib["r"])
                if row_number < 4:
                    continue
                cells: dict[str, str] = {}
                for cell in row.findall(qname(NS_MAIN, "c")):
                    if cell.find(qname(NS_MAIN, "f")) is not None:
                        raise AssertionError(f"unexpected source formula: {cell.attrib['r']}")
                    address = cell.attrib["r"]
                    cell_type = cell.attrib.get("t")
                    if cell_type == "inlineStr":
                        inline = cell.find(qname(NS_MAIN, "is"))
                        text = "" if inline is None else "".join(
                            node.text or "" for node in inline.iter(qname(NS_MAIN, "t"))
                        )
                    else:
                        value_node = cell.find(qname(NS_MAIN, "v"))
                        text = "" if value_node is None else value_node.text or ""
                        if cell_type == "s" and text:
                            text = shared_strings[int(text)]
                    cells[column_of(address)] = text
                if cells.get("A", "").strip():
                    all_rows[(sheet_name, row_number)] = cells
    return all_rows


def source_cell(row: dict, name: str) -> str:
    return row["source"]["cell_coordinates"][name]


class TransformerV21PackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
        cls.rows = {
            (table["source_sheet"], row["source"]["row"]): row
            for table in cls.pack["tables"]
            for row in table["rows"]
        }
        cls.source = read_source_cells()

    def test_pack_identity_counts_and_integrity(self) -> None:
        pack = self.pack
        self.assertEqual(pack["pack_id"], "GB20052-2024-TRANSFORMER-V2.1")
        self.assertEqual(pack["mapping_revision"], "V2.1")
        self.assertEqual(pack["runtime_loss_unit"], "W")
        self.assertEqual(pack["counts"], {
            "tables": 35,
            "threshold_rows": 589,
            "threshold_values": 3534,
        })
        self.assertEqual(
            [table["table_no"] for table in pack["tables"]],
            list(range(1, 36)),
        )
        self.assertTrue(verify_pack_integrity(pack))
        self.assertEqual(len(self.rows), 589)

    def test_all_thresholds_match_frozen_workbook_cells_and_units(self) -> None:
        unit_scale = {"W": Decimal(1), "kW": Decimal(1000)}
        self.assertEqual(len(self.source), 589)
        self.assertEqual(set(self.rows), set(self.source))

        for coordinate, pack_row in self.rows.items():
            with self.subTest(sheet=coordinate[0], row=coordinate[1]):
                source_cells = self.source[coordinate]
                provenance = pack_row["source"]
                self.assertEqual(pack_row["source_row_id"], source_cells["A"].strip())
                self.assertEqual(pack_row["capacity_kva"], source_cells["B"].strip())
                self.assertEqual(
                    provenance["source_units"],
                    {
                        "no_load_loss": source_cells["M"].strip(),
                        "load_loss": source_cells["N"].strip(),
                    },
                )
                self.assertEqual(
                    provenance["condition_values"],
                    {
                        "core_material": source_cells.get("C", "").strip(),
                        "vector_group": source_cells.get("D", "").strip(),
                        "thermal_class": source_cells.get("E", "").strip(),
                        "loss_branch": source_cells.get("F", "").strip(),
                    },
                )
                for grade_no, columns in enumerate((("G", "H"), ("I", "J"), ("K", "L")), 1):
                    grade = f"grade_{grade_no}"
                    no_load_raw = source_cells[columns[0]].strip()
                    load_raw = source_cells[columns[1]].strip()
                    self.assertEqual(
                        provenance["source_thresholds"][grade],
                        {"no_load_loss": no_load_raw, "load_loss": load_raw},
                    )
                    threshold = pack_row["thresholds_w"][grade]
                    self.assertEqual(
                        Decimal(threshold["no_load_loss"]),
                        Decimal(no_load_raw) * unit_scale[source_cells["M"].strip()],
                    )
                    self.assertEqual(
                        Decimal(threshold["load_loss"]),
                        Decimal(load_raw) * unit_scale[source_cells["N"].strip()],
                    )
                    self.assertIsInstance(threshold["no_load_loss"], str)
                    self.assertIsInstance(threshold["load_loss"], str)

                self.assertEqual(source_cell(pack_row, "capacity_kva"), f"B{coordinate[1]}")
                self.assertEqual(source_cell(pack_row, "load_reference_temperature"), f"O{coordinate[1]}")
                self.assertEqual(source_cell(pack_row, "technical_condition"), f"P{coordinate[1]}")
                self.assertEqual(source_cell(pack_row, "page_reference"), f"Q{coordinate[1]}")

    def test_branch_distinctions_and_shared_source_note_are_preserved(self) -> None:
        tables = {table["table_no"]: table["rows"] for table in self.pack["tables"]}

        shared_rows = [
            row for row in tables[1]
            if row["source"]["shared_source_label"] == "Pk合并原格共享"
        ]
        self.assertTrue(shared_rows)
        self.assertTrue(all("Pk合并原格共享" not in row["branch_id"] for row in shared_rows))
        self.assertEqual(len({row["source_row_id"] for row in shared_rows}), len(shared_rows))

        table_2_630 = [row for row in tables[2] if row["capacity_kva"] == "630"]
        self.assertEqual(len(table_2_630), 12)
        self.assertEqual(len({row["branch_id"] for row in table_2_630}), 12)

        table_15 = [row for row in tables[15] if row["capacity_kva"] in {"120000", "150000", "180000"}]
        for capacity in {"120000", "150000", "180000"}:
            branches = {row["branch_id"] for row in table_15 if row["capacity_kva"] == capacity}
            self.assertEqual(
                branches,
                {
                    "GB20052-T15/loss_group=ordinary",
                    "GB20052-T15/loss_group=lv_66_69_special",
                },
            )

        for table_no in (27, 28):
            table_rows = tables[table_no]
            first_capacity = table_rows[0]["capacity_kva"]
            siblings = [row for row in table_rows if row["capacity_kva"] == first_capacity]
            self.assertEqual(
                {row["branch_id"] for row in siblings},
                {f"GB20052-T{table_no:02d}/uk_group={group}" for group in "ABC"},
            )

        self.assertNotIn("3000", {row["capacity_kva"] for row in tables[32]})
        self.assertIn("3000", {row["capacity_kva"] for row in tables[31]})

    def test_pack_is_reproducible_from_frozen_source_pair(self) -> None:
        regenerated = build_pack()
        self.assertEqual(self.pack, regenerated)
        self.assertTrue(MAPPING_RELATIVE_PATH.is_file())


if __name__ == "__main__":
    unittest.main()
