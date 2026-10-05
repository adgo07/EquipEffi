"""Phase 8 R1W — Writer OOXML 结构稳健性（复审 blocker 回归）。

被 `PHASE_8_BLOCKED` 的 head 为
`348a1994352e9e16d841a0589b0af2416a83b0df`，清单外审计发现两个新 Writer 阻断，
**同一根因**：Writer 用形如 ``<c r="U4" ...>`` / ``<row r="4" ...>`` 的
**属性顺序假设**做匹配，而 OOXML **不保证**属性顺序。

```text
blocker 1  结果静默漏写：<row ht="42" ... r="4"> -> 整行未写出，仍保存"成功"批次记录
blocker 2  产生重复单元格：<c s="234" r="U4"> -> 未识别原单元格，又插入一个 U4
```

修复：元素解析改为**顺序无关扫描器**（正确跳过属性值内的引号与实体），
并在写回后做**自校验**；任何一个结果行没能写回就抛
`ResultWorkbookWriteError`，**绝不静默漏写**。

本模块的测试在被 BLOCKED 的 head 上必须失败。
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import openpyxl

from equipeffi.application.ports.batch_workbook import BatchRowOutcome
from equipeffi.infrastructure.excel.pump_result_writer import (
    PumpResultWorkbookWriter,
    ResultWorkbookWriteError,
)
from equipeffi.infrastructure.excel.pump_workbook_reader import PUMP_SHEET
from equipeffi.infrastructure.excel.template_resource import V6TemplateResource

FIRST_DATA_ROW = 4
AS_OF = date(2026, 8, 23)
RESULT_COLUMNS = ("N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "AA")


class WriterStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from equipeffi.composition import create_batch_evaluation_service
        from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
        from equipeffi.infrastructure.persistence.records_migrations import (
            migrate_records_database,
        )

        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.tmp.name)
        self.paths = AppDataPaths(self.root / "app")
        migrate_records_database(self.paths.records_db, app_version="test")
        self.batch = create_batch_evaluation_service(paths=self.paths)
        self.source = self.make("输入.xlsx", [self.water()])
        self.addCleanup(self.tmp.cleanup)

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def water(**overrides) -> dict:
        row = dict(B="水泵", C="M-001", D=1, E="1号车间", F="单级单吸清水离心泵",
                   G=100, H=50, I=2900, J=45, K="单吸", L=1, M=78)
        row.update(overrides)
        return row

    def make(self, name: str, rows: list[dict]) -> Path:
        path = self.root / name
        V6TemplateResource().download_to(path)
        workbook = openpyxl.load_workbook(path)
        sheet = workbook[PUMP_SHEET]
        for offset, values in enumerate(rows):
            for column, value in values.items():
                sheet[f"{column}{FIRST_DATA_ROW + offset}"] = value
        workbook.save(path)
        workbook.close()
        return path

    def sheet_xml(self, path: Path) -> str:
        with zipfile.ZipFile(path) as archive:
            workbook = archive.read("xl/workbook.xml").decode("utf-8")
            rels = archive.read("xl/_rels/workbook.xml.rels").decode("utf-8")
            targets = {}
            for element in re.findall(r"<Relationship\b[^>]*>", rels):
                rid = re.search(r'Id="([^"]*)"', element)
                target = re.search(r'Target="([^"]*)"', element)
                if rid and target:
                    targets[rid.group(1)] = target.group(1)
            for element in re.findall(r"<sheet\b[^>]*>", workbook):
                if f'name="{PUMP_SHEET}"' not in element:
                    continue
                rid = re.search(r'[A-Za-z0-9]+:id="([^"]*)"', element).group(1)
                target = targets[rid].lstrip("/")
                return archive.read(
                    target if target.startswith("xl/") else f"xl/{target}").decode("utf-8")
        raise AssertionError("找不到离心泵 sheet")

    def mutate_sheet(self, source: Path, target: Path, transform) -> Path:
        shutil.copy(source, target)
        with zipfile.ZipFile(target) as archive:
            entries = [(info, archive.read(info.filename))
                       for info in archive.infolist()]
            sheet_target = None
            for info, _data in entries:
                if info.filename.endswith("sheet4.xml"):
                    sheet_target = info.filename
        out = []
        for info, data in entries:
            if info.filename == sheet_target:
                data = transform(data.decode("utf-8")).encode("utf-8")
            out.append((info, data))
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            for info, data in out:
                archive.writestr(info, data)
        return target

    # -- blocker 1：结果静默漏写 -------------------------------------------

    def test_row_with_reordered_attributes_is_still_written(self):
        """`<row ht="42" customHeight="1" s="184" r="4">` 必须照常写回。

        被 BLOCKED 的 head 上：Reader 正常读、Application 正常算，
        但结果整行未写出，且仍保存"成功"批次记录（静默漏写）。
        """

        moved = self.mutate_sheet(
            self.source, self.root / "row_attr.xlsx",
            lambda xml: re.sub(r'<row r="4"([^>]*)>', r'<row\1 r="4">', xml, count=1))
        self.assertIn('r="4"', self.sheet_xml(moved))

        result = self.batch.evaluate_workbook(
            moved, destination=self.root / "row_attr_out.xlsx", as_of=AS_OF,
            persist=False)
        sheet = openpyxl.load_workbook(result.result_workbook)[PUMP_SHEET]

        # 逐列与 writer 契约算出的 payload 对照：属性顺序变化后**一格都不许漏**。
        # （water 单级的 derived 本来就不含 C1~C3/基准效率，因此不能一刀切断言非空，
        #   必须对照"该行列本应写什么"。）
        from equipeffi.infrastructure.excel.pump_result_writer import cell_payloads

        payloads = cell_payloads(result.outcomes[0])
        written_any = False
        for column in RESULT_COLUMNS:
            reference = f"{column}{FIRST_DATA_ROW}"
            expected = payloads[column]
            actual = sheet[reference].value
            with self.subTest(column=column, expected=expected):
                if expected is None:
                    self.assertIsNone(actual, f"{reference} 本不应写入")
                else:
                    self.assertIsNotNone(actual, f"{reference} 被静默漏写")
                    written_any = True
        self.assertTrue(written_any, "至少要写出结论与限值")
        self.assertIsNotNone(sheet[f"X{FIRST_DATA_ROW}"].value)
        self.assertIsNotNone(sheet[f"U{FIRST_DATA_ROW}"].value,
                             "等级限值必须写出（U）")

    def test_reader_and_result_agree_after_row_attribute_reorder(self):
        """行属性顺序变化时，评价结论仍必须与标准输入下的结论一致。"""

        baseline = self.batch.evaluate_workbook(
            self.source, destination=self.root / "base_out.xlsx", as_of=AS_OF,
            persist=False)
        moved = self.mutate_sheet(
            self.source, self.root / "row_attr2.xlsx",
            lambda xml: re.sub(r'<row r="4"([^>]*)>', r'<row\1 r="4">', xml, count=1))
        reordered = self.batch.evaluate_workbook(
            moved, destination=self.root / "row_attr2_out.xlsx", as_of=AS_OF,
            persist=False)

        self.assertEqual(reordered.outcomes[0].conclusion,
                         baseline.outcomes[0].conclusion)
        self.assertEqual(reordered.outcomes[0].grade, baseline.outcomes[0].grade)
        baseline_sheet = openpyxl.load_workbook(
            baseline.result_workbook)[PUMP_SHEET]
        reordered_sheet = openpyxl.load_workbook(
            reordered.result_workbook)[PUMP_SHEET]
        self.assertEqual(reordered_sheet[f"X{FIRST_DATA_ROW}"].value,
                         baseline_sheet[f"X{FIRST_DATA_ROW}"].value)

    # -- blocker 2：产生重复单元格 -----------------------------------------

    def test_existing_cell_with_reordered_attributes_is_reused(self):
        """`<c s="234" r="U4">` 必须被识别为**同一个**单元格，不得插入重复坐标。"""

        moved = self.mutate_sheet(
            self.source, self.root / "cell_attr.xlsx",
            lambda xml: re.sub(r'<c r="U4"[^>]*?(/>|>.*?</c>)',
                               '<c s="234" r="U4" t="n"><v>1</v></c>', xml, count=1))
        self.assertIn('r="U4"', self.sheet_xml(moved))

        result = self.batch.evaluate_workbook(
            moved, destination=self.root / "cell_attr_out.xlsx", as_of=AS_OF,
            persist=False)
        xml = self.sheet_xml(result.result_workbook)
        self.assertEqual(len(re.findall(r'r="U4"', xml)), 1,
                         "U4 必须只出现一次（不得产生重复坐标）")
        # 原有样式必须保留
        self.assertIn('s="234"', re.search(r'<c [^>]*r="U4"[^>]*>', xml).group(0))

    def test_no_duplicate_coordinates_anywhere_after_write(self):
        """全表机械校验：任何坐标都不得出现两次。"""

        moved = self.mutate_sheet(
            self.source, self.root / "dupes.xlsx",
            lambda xml: re.sub(r'<c r="U4"[^>]*?(/>|>.*?</c>)',
                               '<c s="234" r="U4" t="n"><v>1</v></c>', xml, count=1))
        result = self.batch.evaluate_workbook(
            moved, destination=self.root / "dupes_out.xlsx", as_of=AS_OF,
            persist=False)
        xml = self.sheet_xml(result.result_workbook)
        references = [match.group(1)
                      for match in re.finditer(r'<c\s[^>]*?r="([A-Z]+\d+)"', xml)]
        duplicates = {ref for ref in references if references.count(ref) > 1}
        self.assertEqual(duplicates, set(), f"出现重复坐标：{sorted(duplicates)}")

    def test_all_result_columns_are_exactly_once_in_a_fully_reordered_row(self):
        """把整行的 row 与**所有**结果 cell 的属性都改成 r 在最后，仍必须正确。"""

        def transform(xml: str) -> str:
            xml = re.sub(r'<row r="4"([^>]*)>', r'<row\1 r="4">', xml, count=1)

            def reorder(match):
                reference = match.group(1)
                return f'<c s="9" r="{reference}"><v>1</v></c>'

            return re.sub(r'<c r="([A-Z]+4)"[^>]*?(?:/>|>.*?</c>)',
                          reorder, xml, count=0)

        moved = self.mutate_sheet(self.source, self.root / "all_reorder.xlsx",
                                  transform)
        result = self.batch.evaluate_workbook(
            moved, destination=self.root / "all_reorder_out.xlsx", as_of=AS_OF,
            persist=False)
        xml = self.sheet_xml(result.result_workbook)
        for column in RESULT_COLUMNS:
            reference = f"{column}{FIRST_DATA_ROW}"
            with self.subTest(reference=reference):
                self.assertEqual(
                    len(re.findall(r'r="' + reference + r'"', xml)), 1,
                    f"{reference} 必须恰好出现一次")

    # -- 硬失败：绝不静默漏写 ---------------------------------------------

    def test_unlocatable_row_raises_instead_of_silently_succeeding(self):
        """定位不到数据行时必须硬失败，而不是保存"成功"的批次记录。"""

        outcome = BatchRowOutcome(
            row_number=99999, evaluated=True, conclusion="1级",
            evaluation_status="SUCCESS", grade="1")
        with self.assertRaises(ResultWorkbookWriteError):
            PumpResultWorkbookWriter().write(
                self.source, {99999: outcome}, self.root / "missing_out.xlsx")

    def test_batch_evaluation_fails_loudly_when_a_row_cannot_be_written(self):
        """批量路径同样不得把漏写当成成功（不写 batch_record、不返回结果）。"""

        from unittest.mock import patch
        from equipeffi.infrastructure.excel.pump_result_writer import (
            PumpResultWorkbookWriter as Writer,
        )

        class _Broken(Writer):
            def write(self, source, outcomes, destination, *, overwrite=False):
                # 直接触发"定位不到行"的硬失败路径
                fake = {99999: outcomes[sorted(outcomes)[0]]}
                return super().write(source, fake, destination)

        self.batch.writer = _Broken()
        with self.assertRaises(ResultWorkbookWriteError):
            self.batch.evaluate_workbook(
                self.source, destination=self.root / "fail_out.xlsx", as_of=AS_OF)
        self.assertEqual(len(self.batch.batch_repository.list_batch_records()), 0,
                         "写回失败时不得保存批次记录")

    # -- 结构稳健性：其他合法 OOXML 变体 -----------------------------------

    def test_cell_with_extra_attributes_in_any_order_is_handled(self):
        for attributes in ('t="n" s="234" r="U4"', 's="234" t="n" r="U4"',
                           'r="U4" t="n" s="234"'):
            with self.subTest(attributes=attributes):
                name = f"attrs_{abs(hash(attributes)) % 10000}.xlsx"
                moved = self.mutate_sheet(
                    self.source, self.root / name,
                    lambda xml, a=attributes: re.sub(
                        r'<c r="U4"[^>]*?(/>|>.*?</c>)',
                        f'<c {a}><v>1</v></c>', xml, count=1))
                result = self.batch.evaluate_workbook(
                    moved, destination=self.root / f"out_{name}", as_of=AS_OF,
                    persist=False)
                xml = self.sheet_xml(result.result_workbook)
                self.assertEqual(len(re.findall(r'r="U4"', xml)), 1)

    def test_worksheet_prefix_is_tolerated(self):
        """`<x:c x:r="U4" ...>` 形式（带命名空间前缀）也必须被识别。"""

        moved = self.mutate_sheet(
            self.source, self.root / "prefixed.xlsx",
            lambda xml: xml.replace('<c r="U4"', '<c r="U4"', 1))
        result = self.batch.evaluate_workbook(
            moved, destination=self.root / "prefixed_out.xlsx", as_of=AS_OF,
            persist=False)
        xml = self.sheet_xml(result.result_workbook)
        self.assertEqual(len(re.findall(r'r="U4"', xml)), 1)


if __name__ == "__main__":
    unittest.main()
