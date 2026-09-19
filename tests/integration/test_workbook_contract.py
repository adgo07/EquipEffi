import unittest
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "src/equipeffi/resources/templates/设备能效分析空白模板_重构版V4_20260825.xlsx"


class WorkbookContractTests(unittest.TestCase):
    def test_template_structure_and_protection(self):
        self.assertTrue(TEMPLATE.exists(), TEMPLATE)
        with zipfile.ZipFile(TEMPLATE) as z:
            ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            wb = ET.fromstring(z.read("xl/workbook.xml"))
            sheets = wb.find("m:sheets", ns)
            self.assertEqual(len(sheets), 18)
            names = [s.attrib["name"] for s in sheets]
            self.assertIn("注意事项", names)
            self.assertIn("模板说明", names)
            self.assertNotIn("判定轨迹", names)  # 空白模板在执行判定前不生成轨迹sheet
            self.assertEqual(next(s.attrib.get("state") for s in sheets if s.attrib["name"] == "配置"), "hidden")
            # table1～table15与15类公共设备sheet一一对应；其余表为标准目录和配置字典。
            for i in range(1, 16):
                table = z.read(f"xl/tables/table{i}.xml").decode("utf-8")
                self.assertNotIn("设备位号", table)
                self.assertNotIn("是否在标准适用范围", table)
                self.assertIn("自动备注", table)
                self.assertIn("采用标准", table)
                self.assertIn("判定说明", table)
                self.assertIn("技术记录ID", table)
            styles = z.read("xl/styles.xml").decode("utf-8")
            self.assertIn('locked="0"', styles)
            for i in range(1, 19):
                self.assertIn("sheetProtection", z.read(f"xl/worksheets/sheet{i}.xml").decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
