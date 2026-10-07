"""Phase 8 R2 — Writer 命名空间前缀无关 + 整表坐标唯一性（第三次复审 blocker）。

被 `PHASE_8_BLOCKED` 的 head 为
`f2518a93179f51fd5339d8bfcf8cbbe02fa67e28`。

**根因：namespace prefix-sensitive raw OOXML scanner（命名空间前缀敏感的原生
OOXML 扫描器）**。结果 Writer 用**字符串前缀**识别元素：

```text
row_xml.find("<c", index)        row_xml.find("</c>", tag_end)
xml.find("<row", index)          xml.find("</row>", tag_end)
row_xml.rfind("</row>")
```

这些只能识别**无前缀**的字面形式。合法 OOXML 允许任意命名空间前缀，
`<x:c r="U4">…</x:c>` / `<ss:c …/>` / `<x:row r="4">…</x:row>` 因此完全不可见：
Writer 以为该单元格不存在，又追加一个**无前缀**的 `<c r="U4">`，
输出工作簿出现**重复坐标**。更糟的是旧代码的
``after in "_:.-"`` 分支把 `<x:c` 当成 `<col`/`<cols` 之类的误匹配**主动跳过**。

本轮修复的最终语义：**元素身份由 expanded QName（namespace URI + local-name）
决定，与前缀字面形式无关**；只有 `{MAIN_NS}c` 才是正式 SpreadsheetML 单元格，
只有 `{MAIN_NS}row` 才是正式行。不同前缀只要绑定同一个 MAIN_NS 就是同一类元素；
无默认 namespace 时的裸 `<c>` 则不是 SpreadsheetML。结束标记仍必须匹配开标记的
实际限定名，并在写结果 Workbook **之前**对正式 SpreadsheetML 路径强制坐标唯一性
后置条件。

本模块的每个测试在被 BLOCKED 的 head 上都必须失败。

**测试夹具纪律（上一轮的教训）**：上一轮的"前缀测试"是
``xml.replace('<c r="U4"', '<c r="U4"')``——一个**空操作**，因此从来没有真正
产生过 `<x:c>` 输入，测试通过是假象。本模块**禁止**这种夹具：每个前缀化夹具
都必须

```text
1. 复制/创建 xlsx
2. 打开 ZIP 内真实的 worksheet XML
3. **结构化**改写为合法的命名空间前缀 SpreadsheetML（补/改 xmlns 声明）
4. 写回 ZIP
5. 在调用 Writer **之前**断言夹具里确实存在 <x:c，且 U4 真的是前缀化单元格
```
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path
from typing import Callable
from xml.etree import ElementTree

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import openpyxl

from equipeffi.application.ports.batch_workbook import BatchRowOutcome
from equipeffi.infrastructure.excel.pump_result_writer import (
    PumpResultWorkbookWriter,
    ResultWorkbookWriteError,
    cell_references,
)
from equipeffi.infrastructure.excel.pump_workbook_reader import PUMP_SHEET
from equipeffi.infrastructure.excel.template_resource import (
    V6TemplateResource,
)
from equipeffi.infrastructure.persistence.sqlite_batch_record_repository import (
    SqliteBatchRecordRepository,
)

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
FIRST_DATA_ROW = 4
AS_OF = date(2026, 8, 23)
#: 单元格元素的机械识别（任意合法前缀都算）。
ANY_PREFIX_CELL = re.compile(r"<(?:[A-Za-z_][\w.\-]*:)?c\s")
#: 带坐标的单元格元素（任意合法前缀）。
ANY_PREFIX_REF = re.compile(r"<(?:[A-Za-z_][\w.\-]*:)?c\s[^>]*?r=\"([A-Z]{1,3}\d+)\"")


# ---------------------------------------------------------------------------
# 夹具：把真实 worksheet XML **结构化**改写成命名空间前缀形式
# ---------------------------------------------------------------------------

def _sheet_xml_path(archive: zipfile.ZipFile, sheet_name: str = PUMP_SHEET) -> str:
    """定位「离心泵」sheet 的 worksheet XML 路径（与 Writer 同一策略）。"""

    workbook = archive.read("xl/workbook.xml").decode("utf-8")
    relationships = archive.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    relation_map: dict[str, str] = {}
    for element in re.findall(r"<Relationship\b[^>]*>", relationships):
        rid = re.search(r'Id="([^"]*)"', element)
        target = re.search(r'Target="([^"]*)"', element)
        if rid and target:
            relation_map[rid.group(1)] = target.group(1)
    for element in re.findall(r"<sheet\b[^>]*>", workbook):
        name = re.search(r'name="([^"]*)"', element)
        rid = re.search(r'[A-Za-z0-9]+:id="([^"]*)"', element)
        if not name or not rid or name.group(1) != sheet_name:
            continue
        target = relation_map[rid.group(1)].lstrip("/")
        return target if target.startswith("xl/") else f"xl/{target}"
    raise AssertionError(f"找不到「{sheet_name}」sheet")


def read_sheet_xml(path: Path) -> str:
    """读取 xlsx **ZIP 内部**真实的 worksheet XML。"""

    with zipfile.ZipFile(path) as archive:
        return archive.read(_sheet_xml_path(archive)).decode("utf-8")


def rewrite_sheet_xml(path: Path, transform: Callable[[str], str]) -> Path:
    """把 worksheet XML 结构化改写后写回 ZIP（其余部件逐字节不动）。"""

    with zipfile.ZipFile(path) as archive:
        entries = [(info, archive.read(info.filename))
                   for info in archive.infolist()]
        target = _sheet_xml_path(archive)
    rewritten = []
    for info, data in entries:
        if info.filename == target:
            data = transform(data.decode("utf-8")).encode("utf-8")
        rewritten.append((info, data))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for info, data in rewritten:
            archive.writestr(info, data)
    return path


def prefix_worksheet_xml(xml: str, prefix: str) -> str:
    """把整张 worksheet **结构化**改写成 `prefix` 前缀的合法 SpreadsheetML。

    用 XML 解析器改写（并注册 ``xmlns:<prefix>`` 声明），而不是碰运气的字符串
    替换：只有真正的结构改写才能保证每个元素都带上该前缀、文件仍然合法。
    """

    root = ElementTree.fromstring(xml)
    # `xml:space` 是 XML 保留命名空间的前缀，序列化器无法重新声明，直接去掉
    # （不影响任何被测语义：被测的是元素命名空间前缀）。
    for node in root.iter():
        for key in [key for key in node.attrib if key == XML_SPACE]:
            del node.attrib[key]
    ElementTree.register_namespace(prefix, MAIN_NS)
    body = ElementTree.tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + body


def assert_prefixed(xml: str, prefix: str, reference: str = "U4",
                    *, fully_prefixed: bool = True) -> None:
    """**机械证明**夹具真的含前缀化元素（不是空操作）。

    ``fully_prefixed=False`` 用于**故意**混用前缀/无前缀表示的夹具（§六 F/G）：
    那种夹具本来就应当同时含有两种写法。
    """

    assert f"<{prefix}:c " in xml, f"夹具无效：没有 <{prefix}:c 元素"
    assert re.search(rf'<{prefix}:c [^>]*r="{reference}"', xml), (
        f"夹具无效：{reference} 不是 <{prefix}:c 前缀化单元格")
    assert f"<{prefix}:row " in xml, f"夹具无效：没有 <{prefix}:row 元素"
    if fully_prefixed:
        assert not re.search(r'<c[ />]', xml), "夹具无效：仍存在无前缀 <c> 元素"


# ---------------------------------------------------------------------------
# 基类
# ---------------------------------------------------------------------------

class PrefixedWriterTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

        from equipeffi.composition import create_batch_evaluation_service
        from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
        from equipeffi.infrastructure.persistence.records_migrations import (
            migrate_records_database,
        )

        self.paths = AppDataPaths(self.root / "app")
        migrate_records_database(self.paths.records_db, app_version="test")
        self.batch = create_batch_evaluation_service(paths=self.paths)
        self.repository = SqliteBatchRecordRepository(self.paths.records_db)

    # -- 输入夹具 ----------------------------------------------------------

    @staticmethod
    def water(**overrides) -> dict:
        row = dict(B="水泵", C="M-001", D=1, E="1号车间", F="单级单吸清水离心泵",
                   G=100, H=50, I=2900, J=45, K="单吸", L=1, M=78)
        row.update(overrides)
        return row

    def make_input(self, name: str, rows: list[dict]) -> Path:
        """创建真实输入工作簿（模板 + 用户输入）。"""

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

    def make_prefixed(self, name: str, rows: list[dict],
                      prefix: str = "x") -> Path:
        """创建**真正**前缀化的输入工作簿，并机械校验夹具有效。"""

        path = self.make_input(name, rows)
        rewrite_sheet_xml(path, lambda xml: prefix_worksheet_xml(xml, prefix))
        xml = read_sheet_xml(path)
        assert_prefixed(xml, prefix, "U4")
        return path

    # -- 机械断言 ----------------------------------------------------------

    def u4_occurrences(self, path: Path) -> int:
        return len(re.findall(r'r="U4"', read_sheet_xml(path)))

    def all_references(self, path: Path) -> list[str]:
        """列出结果工作簿中的全部坐标（**独立 expat 解析**，非 Writer 扫描器）。"""

        return list(cell_references(read_sheet_xml(path)))

    def raw_cell_references(self, path: Path) -> list[str]:
        """正则独立复算坐标（任意前缀），用于交叉验证扫描器。"""

        return ANY_PREFIX_REF.findall(read_sheet_xml(path))

    def assert_whole_sheet_unique(self, path: Path) -> None:
        """**整表坐标唯一性不变式**：任何坐标都不得出现两次。"""

        references = self.all_references(path)
        duplicates = sorted({ref for ref in references
                             if references.count(ref) > 1})
        self.assertEqual(duplicates, [], f"出现重复坐标：{duplicates}")

        raw = [ref for ref in self.raw_cell_references(path)]
        raw_duplicates = sorted({ref for ref in raw if raw.count(ref) > 1})
        self.assertEqual(raw_duplicates, [],
                         f"正则复算发现重复坐标：{raw_duplicates}")

    def assert_batch_record_count(self, expected: int) -> None:
        self.assertEqual(len(self.repository.list_batch_records()), expected)


# ---------------------------------------------------------------------------
# §六 A～D：前缀无关的单元格识别
# ---------------------------------------------------------------------------

class PrefixAgnosticCellTests(PrefixedWriterTestCase):
    def test_A_unprefixed_cell_is_reused_and_unique(self):
        """A 无前缀 `<c r="U4">…</c>` -> 写回后 U4 恰好 1 次。"""

        source = self.make_input("a_plain.xlsx", [self.water()])
        self.assertIn('<c r="U4"', read_sheet_xml(source))

        result = self.batch.evaluate_workbook(
            source, destination=self.root / "a_out.xlsx", as_of=AS_OF,
            persist=False)

        self.assertEqual(self.u4_occurrences(result.result_workbook), 1)
        self.assert_whole_sheet_unique(result.result_workbook)

    def test_B_prefix_x_cell_is_recognised_and_updated_in_place(self):
        """B 前缀 `x`：`<x:c r="U4">…</x:c>` -> U4 恰好 1 次，且值 == 正式阈值。"""

        source = self.make_prefixed("b_x.xlsx", [self.water()], prefix="x")

        result = self.batch.evaluate_workbook(
            source, destination=self.root / "b_out.xlsx", as_of=AS_OF,
            persist=False)
        outcome = result.outcomes[0]

        self.assertEqual(self.u4_occurrences(result.result_workbook), 1,
                         "前缀化 U4 必须被就地更新，不得再插入第二个坐标")
        self.assert_whole_sheet_unique(result.result_workbook)

        # 值必须等于**当前正式阈值**
        sheet = openpyxl.load_workbook(result.result_workbook)[PUMP_SHEET]
        from equipeffi.infrastructure.excel.pump_result_writer import (
            THRESHOLD_COLUMNS,
        )

        expected = {column: name for column, name in THRESHOLD_COLUMNS}
        self.assertTrue(outcome.thresholds)
        self.assertEqual(float(sheet["U4"].value),
                         float(outcome.thresholds[expected["U"]]),
                         "U4 必须写入正式 Result.thresholds 的值")

    def test_C_non_x_prefix_cell_is_recognised(self):
        """C 非 `x` 前缀：`<ss:c r="U4">…</ss:c>` -> U4 恰好 1 次。"""

        source = self.make_prefixed("c_ss.xlsx", [self.water()], prefix="ss")

        result = self.batch.evaluate_workbook(
            source, destination=self.root / "c_out.xlsx", as_of=AS_OF,
            persist=False)

        self.assertEqual(self.u4_occurrences(result.result_workbook), 1)
        self.assert_whole_sheet_unique(result.result_workbook)
        sheet = openpyxl.load_workbook(result.result_workbook)[PUMP_SHEET]
        self.assertIsNotNone(sheet["U4"].value)

    def test_C2_arbitrary_prefix_p1_is_recognised(self):
        """C 补充：另一个任意前缀 `p1` 同样必须被识别。"""

        source = self.make_prefixed("c_p1.xlsx", [self.water()], prefix="p1")

        result = self.batch.evaluate_workbook(
            source, destination=self.root / "c_p1_out.xlsx", as_of=AS_OF,
            persist=False)

        self.assertEqual(self.u4_occurrences(result.result_workbook), 1)
        self.assert_whole_sheet_unique(result.result_workbook)

    def test_D_self_closing_prefixed_cell_is_recognised(self):
        """D 自闭合：`<x:c r="U4"/>` -> U4 恰好 1 次（不得再插入一个）。"""

        def make_self_closing(xml: str) -> str:
            xml = prefix_worksheet_xml(xml, "x")
            # 结构化改写后 U4 必然自闭合（模板该格没有值）；显式断言而不是假设。
            assert re.search(r'<x:c [^>]*r="U4"[^>]*/>', xml), \
                "夹具无效：U4 不是自闭合的 <x:c .../>"
            return xml

        source = self.make_input("d_self.xlsx", [self.water()])
        rewrite_sheet_xml(source, make_self_closing)
        xml = read_sheet_xml(source)
        assert_prefixed(xml, "x", "U4")
        self.assertRegex(xml, r'<x:c [^>]*r="U4"[^>]*/>')

        result = self.batch.evaluate_workbook(
            source, destination=self.root / "d_out.xlsx", as_of=AS_OF,
            persist=False)

        self.assertEqual(self.u4_occurrences(result.result_workbook), 1)
        self.assert_whole_sheet_unique(result.result_workbook)
        self.assertIsNotNone(
            openpyxl.load_workbook(result.result_workbook)[PUMP_SHEET]["U4"].value)


# ---------------------------------------------------------------------------
# §六 E～F：前缀化的 row 与混合表示
# ---------------------------------------------------------------------------

class PrefixedRowAndMixedTests(PrefixedWriterTestCase):
    def test_E_prefixed_row_is_recognised_normally(self):
        """E `<x:row r="4"><x:c r="U4">…</x:c></x:row>` -> 必须照常识别整行。"""

        source = self.make_prefixed("e_row.xlsx", [self.water()], prefix="x")
        xml = read_sheet_xml(source)
        self.assertRegex(xml, r'<x:row r="4"[^>]*>')
        self.assertNotRegex(xml, r"<row[ />]")

        result = self.batch.evaluate_workbook(
            source, destination=self.root / "e_out.xlsx", as_of=AS_OF,
            persist=False)

        # 整行结果列必须全部写回（不得"定位不到行"而静默漏写）
        for column in ("N", "U", "V", "W", "X", "AA"):
            with self.subTest(column=column):
                self.assertEqual(
                    len(re.findall(r'r="' + column + r'4"',
                                   read_sheet_xml(result.result_workbook))), 1,
                    f"{column}4 必须恰好出现一次")
        self.assert_whole_sheet_unique(result.result_workbook)
        sheet = openpyxl.load_workbook(result.result_workbook)[PUMP_SHEET]
        self.assertIsNotNone(sheet["X4"].value)

    def test_F_mixed_prefixed_and_unprefixed_cells_work_normally(self):
        """F 同一 worksheet 混用 `<c …>` 与 `<x:c …>`（不同坐标）-> 正常工作。"""

        def make_mixed(xml: str) -> str:
            xml = prefix_worksheet_xml(xml, "x")
            # 让 N4 回到无前缀形式：同一工作表内混用两种表示。
            # 裸 `<c>` 只有在**默认命名空间 == MAIN_NS** 时才仍是 SpreadsheetML，
            # 因此这里必须显式声明默认命名空间（否则裸 c 会落进"无命名空间"，
            # 那是非法输入而不是"混用两种表示"）。
            xml = re.sub(r'<x:worksheet\b', f'<x:worksheet xmlns="{MAIN_NS}"', xml, count=1)
            xml = re.sub(r'<x:c ([^>]*r="N4"[^>]*)/>', r'<c \1/>', xml, count=1)
            return xml

        source = self.make_input("f_mixed.xlsx", [self.water()])
        rewrite_sheet_xml(source, make_mixed)
        xml = read_sheet_xml(source)
        assert_prefixed(xml, "x", "U4", fully_prefixed=False)
        self.assertRegex(xml, r'<c [^>]*r="N4"')
        self.assertRegex(xml, r'<x:c [^>]*r="U4"')
        self.assertRegex(xml, r'<x:c [^>]*r="V4"')

        result = self.batch.evaluate_workbook(
            source, destination=self.root / "f_out.xlsx", as_of=AS_OF,
            persist=False)

        for reference in ("N4", "U4", "V4", "W4", "X4", "AA4"):
            with self.subTest(reference=reference):
                self.assertEqual(
                    len(re.findall(r'r="' + reference + r'"',
                                   read_sheet_xml(result.result_workbook))), 1)
        self.assert_whole_sheet_unique(result.result_workbook)
        sheet = openpyxl.load_workbook(result.result_workbook)[PUMP_SHEET]
        self.assertIsNotNone(sheet["N4"].value)

    def test_mixed_prefixes_across_two_rows_work_normally(self):
        """F 补充：同一工作表内**不同行**用不同前缀（`x:` 与 `ss:`）。"""

        def make_two_prefixes(xml: str) -> str:
            """第 5 行用**另一个同样绑定主命名空间**的前缀（同一工作表两种前缀）。"""

            xml = prefix_worksheet_xml(xml, "x")
            # 第二个前缀必须绑定到**同一个**主命名空间，否则它就不是
            # SpreadsheetML 单元格，测的就不是本轮的缺陷了。
            xml = xml.replace(
                "xmlns:x=", f'xmlns:ss="{MAIN_NS}" xmlns:x=', 1)
            start = xml.index('<x:row r="5"')
            end = xml.index("</x:row>", start) + len("</x:row>")
            row5 = "".join(
                part.replace("<x:", "<ss:").replace("</x:", "</ss:")
                for part in [xml[start:end]])
            return xml[:start] + row5 + xml[end:]

        source = self.make_input("f_two.xlsx", [self.water(), self.water(C="M-002")])
        rewrite_sheet_xml(source, make_two_prefixes)
        xml = read_sheet_xml(source)
        assert_prefixed(xml, "x", "U4", fully_prefixed=False)
        self.assertRegex(xml, r'<ss:row r="5"')
        self.assertRegex(xml, r'<ss:c [^>]*r="U5"')
        self.assertRegex(xml, r'<x:c [^>]*r="U4"')
        self.assertNotRegex(xml, r'<ss:c [^>]*r="U4"')

        result = self.batch.evaluate_workbook(
            source, destination=self.root / "f_two_out.xlsx", as_of=AS_OF,
            persist=False)

        # 同一工作表内两种前缀都必须被识别：两个数据行的结果列各恰好一次。
        for reference in ("U4", "U5", "X4", "X5"):
            with self.subTest(reference=reference):
                self.assertEqual(
                    len(re.findall(r'r="' + reference + r'"',
                                   read_sheet_xml(result.result_workbook))), 1)
        self.assert_whole_sheet_unique(result.result_workbook)
        sheet = openpyxl.load_workbook(result.result_workbook)[PUMP_SHEET]
        for reference in ("U4", "U5", "X4", "X5"):
            with self.subTest(written=reference):
                self.assertIsNotNone(sheet[reference].value)


# ---------------------------------------------------------------------------
# §六 G + §三/§四：重复坐标 fail closed
# ---------------------------------------------------------------------------

class DuplicateCoordinateFailClosedTests(PrefixedWriterTestCase):
    @staticmethod
    def _add_same_qname_duplicate(xml: str, reference: str) -> str:
        """插入第二个**真正的 SpreadsheetML** 单元格。

        夹具用不同字面前缀 `x:` / `ss:`，但二者都绑定 MAIN_NS，因此 expanded
        QName 都是 `{MAIN_NS}c`。这同时验证"前缀无关"和"正式坐标重复必须拒绝"；
        不再把无默认 namespace 下的裸 `<c>` 错当成 SpreadsheetML。
        """

        xml = prefix_worksheet_xml(xml, "x")
        xml = xml.replace(
            "xmlns:x=", f'xmlns:ss="{MAIN_NS}" xmlns:x=', 1)
        anchor = re.search(
            rf'<x:c [^>]*r="{re.escape(reference)}"[^>]*/>', xml)
        assert anchor, f"夹具无效：找不到前缀化 {reference}"
        duplicate = f'<ss:c r="{reference}" s="234"/>'
        return xml[:anchor.start()] + duplicate + xml[anchor.start():]

    def _assert_formal_duplicate(self, xml: str, reference: str) -> None:
        """独立证明重复发生在正式 SpreadsheetML 路径，而非仅文本坐标重名。"""

        references = list(cell_references(xml))
        self.assertEqual(
            references.count(reference), 2,
            f"夹具无效：namespace-aware 解析必须识别两个正式 {reference}")
        root = ElementTree.fromstring(xml)
        matching = [
            element for element in root.iter("{" + MAIN_NS + "}c")
            if element.attrib.get("r") == reference
        ]
        self.assertEqual(
            len(matching), 2,
            f"夹具无效：两个 {reference} 必须具有相同 expanded QName {{MAIN_NS}}c")

    def _duplicate_u4_input(self, name: str) -> Path:
        """输入已经含两个同 expanded QName 的正式 U4（`x:c` + `ss:c`）。"""

        source = self.make_input(name, [self.water()])
        rewrite_sheet_xml(
            source, lambda xml: self._add_same_qname_duplicate(xml, "U4"))
        xml = read_sheet_xml(source)
        assert_prefixed(xml, "x", "U4", fully_prefixed=False)
        self.assertRegex(xml, r'<ss:c [^>]*r="U4"')
        self.assertRegex(xml, r'<x:c [^>]*r="U4"')
        self._assert_formal_duplicate(xml, "U4")
        return source

    def test_G_duplicate_input_fails_closed_without_result_workbook(self):
        """G 输入已有重复 U4 -> Writer 必须 fail closed：无结果文件、无成功记录。"""

        source = self._duplicate_u4_input("g_dup.xlsx")
        destination = self.root / "g_dup_out.xlsx"

        with self.assertRaises(ResultWorkbookWriteError) as caught:
            self.batch.evaluate_workbook(
                source, destination=destination, as_of=AS_OF, persist=True)

        self.assertIn("重复坐标", str(caught.exception))
        self.assertIn("拒绝", str(caught.exception))
        self.assertFalse(destination.exists(),
                         "写回失败时不得留下任何结果工作簿")
        self.assert_batch_record_count(0)

    def test_G2_writer_directly_fails_closed_on_duplicate_target(self):
        """G 直接调用 Writer：目标坐标 >1 时必须抛错，且不产出目标文件。"""

        source = self._duplicate_u4_input("g2_dup.xlsx")
        destination = self.root / "g2_dup_out.xlsx"
        outcome = BatchRowOutcome(
            row_number=FIRST_DATA_ROW, evaluated=True, conclusion="2级",
            evaluation_status="SUCCESS", grade="2",
            thresholds={"1级能效效率限值（%）": "80.5",
                        "2级能效效率限值（%）": "79.5",
                        "3级能效效率限值（%）": "78.5"})

        with self.assertRaises(ResultWorkbookWriteError):
            PumpResultWorkbookWriter().write(
                source, {FIRST_DATA_ROW: outcome}, destination)
        self.assertFalse(destination.exists())

    def test_G3_duplicate_target_on_a_later_row_also_fails_closed(self):
        """G 重复坐标出现在**非首行**时同样必须 fail closed（不是特例修补）。"""

        source = self.make_input("g3_dup.xlsx",
                                 [self.water(), self.water(C="M-002")])
        rewrite_sheet_xml(
            source, lambda xml: self._add_same_qname_duplicate(xml, "U5"))
        xml = read_sheet_xml(source)
        assert_prefixed(xml, "x", "U4", fully_prefixed=False)
        self.assertRegex(xml, r'<ss:c [^>]*r="U5"')
        self.assertRegex(xml, r'<x:c [^>]*r="U5"')
        self._assert_formal_duplicate(xml, "U5")

        destination = self.root / "g3_dup_out.xlsx"
        with self.assertRaises(ResultWorkbookWriteError):
            self.batch.evaluate_workbook(
                source, destination=destination, as_of=AS_OF, persist=True)
        self.assertFalse(destination.exists())
        self.assert_batch_record_count(0)


# ---------------------------------------------------------------------------
# §六 H：整张工作表的坐标唯一性不变式
# ---------------------------------------------------------------------------

class WholeSheetUniquenessInvariantTests(PrefixedWriterTestCase):
    def test_H_every_coordinate_in_the_written_sheet_is_unique(self):
        """H 写回后扫描**每个**带 `r` 的单元格，断言全部坐标唯一。"""

        source = self.make_prefixed("h_unique.xlsx",
                                    [self.water(), self.water(C="M-002"),
                                     self.water(C="M-003")], prefix="x")
        result = self.batch.evaluate_workbook(
            source, destination=self.root / "h_out.xlsx", as_of=AS_OF,
            persist=False)

        xml = read_sheet_xml(result.result_workbook)
        references = [ref for ref in cell_references(xml) if ref]
        self.assertGreater(len(references), 1000,
                           "必须扫描整张工作表，而不是只看少数结果列")
        duplicates = sorted({ref for ref in references
                             if references.count(ref) > 1})
        self.assertEqual(duplicates, [], f"出现重复坐标：{duplicates}")

        # 独立正则复算（任意前缀）交叉验证
        raw = ANY_PREFIX_REF.findall(xml)
        raw_duplicates = sorted({ref for ref in raw if raw.count(ref) > 1})
        self.assertEqual(raw_duplicates, [])
        self.assertEqual(sorted(raw), sorted(references),
                         "扫描器与正则必须给出同一组坐标")

    def test_H2_postcondition_gate_rejects_a_duplicate_that_scanning_missed(self):
        """H 后置条件必须独立生效：即使某处插入逻辑回归，重复坐标也不能交付。

        机械模拟"插入逻辑再次退化"：把 Writer 的补丁结果人为注入一个重复坐标，
        直接验证 ``assert_unique_references`` 这个**结构门禁**会拒绝它。
        """

        from equipeffi.infrastructure.excel.pump_result_writer import (
            assert_unique_references,
        )

        clean = read_sheet_xml(self.make_prefixed(
            "h2_clean.xlsx", [self.water()], prefix="x"))
        assert_unique_references(clean)      # 干净输入必须通过

        anchor = re.search(r'<x:c [^>]*r="U4"[^>]*/>', clean)
        assert anchor, "夹具无效：找不到前缀化 U4"
        # 注入的重复 cell 必须与既有 U4 属同一命名空间（MAIN_NS）：该工作表里
        # 裸 `<c>` 只有在默认命名空间为 MAIN_NS 时才是 SpreadsheetML 单元格。
        polluted = (clean[:anchor.start()] + '<c r="U4" s="234"/>'
                    + clean[anchor.start():])
        polluted = polluted.replace("<x:worksheet ", '<x:worksheet xmlns="' + MAIN_NS + '" ', 1)
        from equipeffi.infrastructure.excel.result_invariants import (
            InvariantViolation,
        )

        with self.assertRaises(InvariantViolation) as caught:
            assert_unique_references(polluted)
        self.assertIn("重复坐标", str(caught.exception))

    def test_H3_non_cell_elements_are_never_mistaken_for_cells(self):
        """机械守卫：`<cols>` / `<col>` / `<customFilter>` 等绝不能被当成单元格。

        （旧实现用 ``find("<c")`` + 字符白名单，正是把 `<x:c` 误判掉的原因。）
        """

        samples = {
            "<cols><col min=\"1\" max=\"1\" width=\"10\"/></cols>": [],
            "<customFilters><customFilter operator=\"equal\" val=\"1\"/>"
            "</customFilters>": [],
            "<c r=\"U4\"/>": ["U4"],
            "<x:c r=\"U4\"/>": ["U4"],
            "<ss:c r=\"U4\"/>": ["U4"],
            "<p1:c r=\"U4\"/>": ["U4"],
            "<c r=\"U4\"><v>1</v></c>": ["U4"],
            "<x:c r=\"U4\"><x:v>1</x:v></x:c>": ["U4"],
            "<cell r=\"U4\"/>": [],
            "<conditionalFormatting><cfRule type=\"cellIs\"/></conditionalFormatting>": [],
        }
        for xml, expected in samples.items():
            with self.subTest(xml=xml):
                self.assertEqual(
                    list(cell_references(xml)), expected,
                    f"元素身份判断错误：{xml}")


# ---------------------------------------------------------------------------
# §七 真实工作簿级端到端
# ---------------------------------------------------------------------------

class PrefixedEndToEndTests(PrefixedWriterTestCase):
    def _formal_result(self):
        from equipeffi.composition import create_pump_analysis_service

        analysis = create_pump_analysis_service(paths=self.paths)
        from equipeffi.application.services.centrifugal_pump_analysis_service import (
            PumpAnalysisRequest,
        )

        return analysis.evaluate(PumpAnalysisRequest(
            product_category="单级单吸清水离心泵", as_of=AS_OF, QBEP="100",
            HBEP="50", speed="2900", efficiency="78", suction="单吸", stages="1"))

    def test_prefixed_end_to_end_reader_batch_writer_reopen(self):
        """§七 合法输入 -> 前缀化 U4 -> Reader -> 批量 -> Writer -> 解压复核。

        机械证明：U4 恰好 1 次；U4 值 == 正式 `Result.thresholds`；
        结果工作簿可正常重新打开；批次统计正确；`batch_record` 仅在
        Writer 成功后保存。
        """

        source = self.make_prefixed("e2e.xlsx", [self.water(D=3)], prefix="x")
        self.assert_whole_sheet_unique(source)      # 输入本身是干净的

        result = self.batch.evaluate_workbook(
            source, destination=self.root / "e2e_out.xlsx", as_of=AS_OF)

        out = result.result_workbook
        xml = read_sheet_xml(Path(out))

        # 1) U4 恰好一次
        self.assertEqual(len(re.findall(r'r="U4"', xml)), 1,
                         "结果工作簿中 U4 必须恰好出现一次")

        # 2) U4 值 == 正式 Result.thresholds 的 1 级限值
        formal = self._formal_result()
        formal_threshold = float(formal.thresholds["1级能效效率限值（%）"])
        sheet = openpyxl.load_workbook(out)[PUMP_SHEET]
        self.assertIsNotNone(sheet["U4"].value, "U4 必须已写入正式限值")
        self.assertEqual(float(sheet["U4"].value), formal_threshold)
        self.assertEqual(float(result.outcomes[0].thresholds[
            "1级能效效率限值（%）"]), formal_threshold,
            "批量结果必须来自同一个正式 Application 契约")

        # 3) 结果工作簿可正常重新打开（Excel/openpyxl 双向）
        reopened = openpyxl.load_workbook(out)
        self.assertEqual(len(reopened.sheetnames), 18)
        pump = reopened[PUMP_SHEET]
        self.assertIsNotNone(pump["X4"].value, "结论必须写出")
        self.assertEqual(pump["D4"].value, 3, "用户输入必须原样保留")
        first = pump["U4"].value
        reopened.close()
        second = openpyxl.load_workbook(out)[PUMP_SHEET]["U4"].value
        self.assertEqual(float(first), float(second))

        # 4) 批次统计正确（数量加权：3 台）
        summary = result.summary
        self.assertEqual(summary.data_row_count, 1)
        self.assertEqual(summary.total_quantity, 3)
        self.assertEqual(summary.evaluated_quantity, 3)
        self.assertEqual(sum(result.summary.conclusion_quantities.values()), 3)
        self.assertEqual(summary.input_error_rows, 0)
        self.assertEqual(summary.execution_error_rows, 0)

        # 5) `batch_record` 仅在 Writer 成功后保存
        self.assertTrue(result.batch_record_saved)
        self.assertEqual(result.batch_record_error, "")
        self.assert_batch_record_count(1)
        record = self.repository.list_batch_records()[0]
        self.assertEqual(record.result_workbook, str(out))
        self.assertEqual(record.total_quantity, 3)
        self.assertTrue(record.result_workbook_sha256)

        # 6) 整表坐标唯一
        self.assert_whole_sheet_unique(Path(out))

    def test_prefixed_and_plain_inputs_agree_exactly(self):
        """前缀化输入与普通输入必须给出**完全相同**的结论、限值与输入保真。"""

        plain = self.make_input("cmp_plain.xlsx", [self.water(D=7)])
        prefixed = self.make_prefixed("cmp_prefixed.xlsx",
                                     [self.water(D=7)], prefix="x")

        plain_result = self.batch.evaluate_workbook(
            plain, destination=self.root / "cmp_plain_out.xlsx",
            as_of=AS_OF, persist=False)
        prefixed_result = self.batch.evaluate_workbook(
            prefixed, destination=self.root / "cmp_prefixed_out.xlsx",
            as_of=AS_OF, persist=False)

        plain_outcome = plain_result.outcomes[0]
        prefixed_outcome = prefixed_result.outcomes[0]
        self.assertEqual(prefixed_outcome.conclusion, plain_outcome.conclusion)
        self.assertEqual(prefixed_outcome.evaluation_status,
                         plain_outcome.evaluation_status)
        self.assertEqual(prefixed_outcome.grade, plain_outcome.grade)
        self.assertEqual(prefixed_outcome.thresholds, plain_outcome.thresholds)
        self.assertEqual(plain_result.summary.as_dict(),
                         prefixed_result.summary.as_dict())

        plain_sheet = openpyxl.load_workbook(
            plain_result.result_workbook)[PUMP_SHEET]
        prefixed_sheet = openpyxl.load_workbook(
            prefixed_result.result_workbook)[PUMP_SHEET]
        for column in ("N", "U", "V", "W", "X", "AA"):
            reference = f"{column}{FIRST_DATA_ROW}"
            with self.subTest(reference=reference):
                self.assertEqual(prefixed_sheet[reference].value,
                                 plain_sheet[reference].value)

    def test_prefixed_workbook_inputs_are_not_rewritten(self):
        """结果 Workbook 与用户输入列：前缀化输入下也不得改写用户输入。"""

        source = self.make_prefixed("keep.xlsx", [self.water()], prefix="x")
        before_xml = read_sheet_xml(source)
        before = openpyxl.load_workbook(source)[PUMP_SHEET]

        result = self.batch.evaluate_workbook(
            source, destination=self.root / "keep_out.xlsx", as_of=AS_OF,
            persist=False)

        self.assertEqual(read_sheet_xml(source), before_xml,
                         "源文件不得被改写")
        after = openpyxl.load_workbook(result.result_workbook)[PUMP_SHEET]
        for column in ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
                       "K", "L", "M", "Y", "Z"):
            reference = f"{column}{FIRST_DATA_ROW}"
            with self.subTest(reference=reference):
                self.assertEqual(after[reference].value, before[reference].value)
        self.assertIsNotNone(after["U4"].value)


if __name__ == "__main__":
    unittest.main()
