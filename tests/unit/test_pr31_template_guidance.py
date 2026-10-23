"""Inspect the shipped workbook, including protected pump styles and decimal inputs."""
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from equipeffi.domain.devices.transformer.input_contract import (
    TRANSFORMER_CATEGORIES, TRANSFORMER_SCOPE_HINT,
)
from tools.build_v61_transformer_template import DEFAULT_SOURCE, DEFAULT_OUTPUT, _sheet_target

NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


class TemplateGuidanceTests(unittest.TestCase):
    def test_loss_inputs_retain_fraction_and_unlocked_style_through_row_103(self):
        with ZipFile(DEFAULT_OUTPUT) as z:
            styles = ET.fromstring(z.read("xl/styles.xml"))
            xfs = styles.find("s:cellXfs", NS)
            formats = {x.get("numFmtId"): x.get("formatCode")
                       for x in styles.find("s:numFmts", NS)}
            sheet = ET.fromstring(z.read(_sheet_target(z, "变压器")))
            for row in range(4, 104):
                for col in ("J", "K"):
                    cell = sheet.find(f".//s:c[@r='{col}{row}']", NS)
                    xf = xfs[int(cell.get("s"))]
                    self.assertEqual(formats[xf.get("numFmtId")], "0.###############")
                    self.assertEqual(xf.find("s:protection", NS).get("locked"), "0")
                for col in ("B", "C", "D", "E", "F", "G", "H", "I", "S", "T", "V", "W", "X", "Y"):
                    cell = sheet.find(f".//s:c[@r='{col}{row}']", NS)
                    self.assertIsNotNone(cell, f"{col}{row}")
                    xf = xfs[int(cell.get("s"))]
                    self.assertEqual(xf.find("s:protection", NS).get("locked"), "0", f"{col}{row}")

    def test_existing_shared_styles_and_pump_sheet_remain_unchanged(self):
        with ZipFile(DEFAULT_SOURCE) as old, ZipFile(DEFAULT_OUTPUT) as new:
            old_styles = ET.fromstring(old.read("xl/styles.xml"))
            new_styles = ET.fromstring(new.read("xl/styles.xml"))
            for tag in ("cellXfs", "numFmts", "fonts", "fills", "borders"):
                previous = old_styles.find(f"s:{tag}", NS)
                current = new_styles.find(f"s:{tag}", NS)
                for i, child in enumerate(previous):
                    self.assertEqual(ET.tostring(child), ET.tostring(current[i]), (tag, i))
            pump = _sheet_target(old, "离心泵")
            self.assertEqual(old.read(pump), new.read(pump))

    def test_instructions_explain_actual_impedance_roles_and_frequency(self):
        with ZipFile(DEFAULT_OUTPUT) as z:
            root = ET.fromstring(z.read(_sheet_target(z, "模板说明")))
            cell = root.find(".//s:c[@r='B13']", NS)
            text = "".join(cell.itertext())
        self.assertNotIn("本阶段不参与自动判级", text)
        for expected in ("表2仅630 kVA", "表27/28", "I、X、Y", "损耗统一按W", TRANSFORMER_SCOPE_HINT):
            self.assertIn(expected, text)

    def test_controlled_categories_declare_fifty_hertz_without_extra_field(self):
        for category in TRANSFORMER_CATEGORIES:
            if category.table_no:
                self.assertEqual(category.route_facts["rated_frequency_hz"], "50")


if __name__ == "__main__":
    unittest.main()
