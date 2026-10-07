"""Phase 8 R4 — Writer 身份解析与输出完整性（诊断 D01～D04 回归）。

被诊断为 BLOCKED 的 head 为
`5fea7fa0b79789d49277c504b0913266518416da`。本轮不再"按已知反例逐项扩展正则"，
而是把身份判定集中到真正的 XML 词法/命名空间模型，并用**独立解析器**做
输入 → 输出校验。

覆盖的独立发现：

```text
D01/P1  合法单引号属性 r='U4' 绕过唯一性门禁 -> 重复 U4 被当成成功
D02/P1  属性命名空间被抹掉（r 与 e:r 合并）-> 重复坐标 + 正式限值静默丢失
D03/P2  namespace 门禁误拒绝合法扩展内容（extLst 内同名 e:t）
D04/P2  磁盘写失败留下最终文件名的残缺 Workbook
```

每个测试在被 BLOCKED 的 head 上都必须失败。
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
from xml.etree import ElementTree

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import openpyxl

from equipeffi.infrastructure.excel.pump_result_writer import (
    PumpResultWorkbookWriter,
    ResultWorkbookWriteError,
    default_namespace_uri,
)
from equipeffi.infrastructure.excel.pump_workbook_reader import (
    PUMP_SHEET,
    V6PumpWorkbookReader,
)
from equipeffi.infrastructure.excel.result_invariants import (
    InvariantViolation,
    assert_unique_references,
    parse_cells_with_expat,
)
from equipeffi.infrastructure.excel.template_resource import V6TemplateResource
from equipeffi.infrastructure.excel.xml_model import MAIN_NS, parse_elements

FIRST_DATA_ROW = 4
AS_OF = date(2026, 8, 23)
OTHER_NS = "urn:independent"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"


def sheet_target(archive: zipfile.ZipFile, sheet_name: str = PUMP_SHEET) -> str:
    workbook = archive.read("xl/workbook.xml").decode("utf-8")
    rels = archive.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    targets: dict[str, str] = {}
    for element in re.findall(r"<Relationship\b[^>]*>", rels):
        rid = re.search(r'Id="([^"]*)"', element)
        target = re.search(r'Target="([^"]*)"', element)
        if rid and target:
            targets[rid.group(1)] = target.group(1)
    for element in re.findall(r"<sheet\b[^>]*>", workbook):
        if f'name="{sheet_name}"' not in element:
            continue
        rid = re.search(r'[A-Za-z0-9]+:id="([^"]*)"', element).group(1)
        target = targets[rid].lstrip("/")
        return target if target.startswith("xl/") else f"xl/{target}"
    raise AssertionError(f"找不到 {sheet_name} sheet")


class R4TestCase(unittest.TestCase):
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
        self.source = self.make_source()
        self.addCleanup(self.tmp.cleanup)

    @staticmethod
    def water(**overrides) -> dict:
        row = dict(B="水泵", C="M-001", D=1, E="1号车间", F="单级单吸清水离心泵",
                   G=100, H=50, I=2900, J=45, K="单吸", L=1, M=78)
        row.update(overrides)
        return row

    def make_source(self) -> Path:
        path = self.root / "输入.xlsx"
        V6TemplateResource().download_to(path)
        workbook = openpyxl.load_workbook(path)
        sheet = workbook[PUMP_SHEET]
        for column, value in self.water().items():
            sheet[f"{column}{FIRST_DATA_ROW}"] = value
        workbook.save(path)
        workbook.close()
        return path

    def mutate(self, name: str, transform) -> Path:
        """在**不改动业务输入**的前提下改写「离心泵」Sheet 的 XML 文本。"""

        destination = self.root / name
        shutil.copy(self.source, destination)
        with zipfile.ZipFile(destination) as archive:
            entries = [(info, archive.read(info.filename))
                       for info in archive.infolist()]
            target = sheet_target(archive)
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            for info, data in entries:
                if info.filename == target:
                    data = transform(data.decode("utf-8")).encode("utf-8")
                archive.writestr(info, data)
        return destination

    def cells_of(self, workbook: Path) -> dict[str, str]:
        with zipfile.ZipFile(workbook) as archive:
            xml = archive.read(sheet_target(archive)).decode("utf-8")
        return {fact.reference: fact.text for fact in parse_cells_with_expat(xml)}

    def result_of(self, source: Path, name: str):
        return self.batch.evaluate_workbook(
            source, destination=self.root / name, as_of=AS_OF, persist=True)

    # ==================================================================
    # D01 — 合法单引号属性不得绕过唯一性门禁
    # ==================================================================

    def test_D01_single_quoted_reference_is_recognised(self):
        """`r='U4'`（单引号）必须被识别为**同一个** U4，不得重复坐标。"""

        source = self.mutate("d01.xlsx", lambda xml: re.sub(
            r'<c r="U4"', "<c r='U4'", xml, count=1))
        with zipfile.ZipFile(source) as archive:
            self.assertIn("r='U4'",
                          archive.read(sheet_target(archive)).decode("utf-8"))
        # 前置：正式 Reader 仍能读到这一行
        self.assertEqual(len(V6PumpWorkbookReader().read(source).rows), 1)

        result = self.result_of(source, "d01_out.xlsx")
        cells = self.cells_of(result.result_workbook)
        self.assertEqual(list(cells).count("U4"), 1,
                         "U4 必须恰好一次（不得因单引号而重复）")
        self.assertTrue(cells["U4"].strip(), "U4 限值必须写出")
        self.assertEqual(cells["X4"], "2级")

    def test_D01_single_quote_with_reordered_attributes(self):
        """属性顺序 + 单引号同时出现也必须正确。"""

        source = self.mutate("d01b.xlsx", lambda xml: re.sub(
            r'<c r="U4"([^>]*?)/>', r'<c\1 s="9" r=\'U4\'/>', xml, count=1))
        result = self.result_of(source, "d01b_out.xlsx")
        cells = self.cells_of(result.result_workbook)
        self.assertEqual(list(cells).count("U4"), 1)

    # ==================================================================
    # D02 — 属性命名空间身份
    # ==================================================================

    def test_D02_extension_attribute_does_not_shadow_the_reference(self):
        """`e:r="ZZ999"` 与无命名空间的 `r="U4"` 是**两个不同属性**。

        旧实现按 local-name 取属性，后者覆盖前者，于是真正的 U4 被漏掉：
        输出出现重复坐标，且正式 Reader reopen 后 U4 为空。
        """

        def add_extension_attribute(xml: str) -> str:
            xml = re.sub(
                r"<worksheet\b",
                f'<worksheet xmlns:e="{OTHER_NS}" xmlns:mc="{MC_NS}"'
                ' mc:Ignorable="e"', xml, count=1)
            return re.sub(r'<c r="U4"', '<c r="U4" e:r="ZZ999"', xml, count=1)

        source = self.mutate("d02.xlsx", add_extension_attribute)
        result = self.result_of(source, "d02_out.xlsx")

        cells = self.cells_of(result.result_workbook)
        self.assertEqual(list(cells).count("U4"), 1, "不得出现重复坐标")
        self.assertTrue(cells["U4"].strip(), "正式 U4 限值不得丢失")
        # 正式 OOXML Reader reopen 后 U4 必须有值
        reopened = V6PumpWorkbookReader().read(result.result_workbook)
        self.assertEqual(len(reopened.rows), 1)
        sheet = openpyxl.load_workbook(result.result_workbook)[PUMP_SHEET]
        self.assertIsNotNone(sheet[f"U{FIRST_DATA_ROW}"].value)

    def test_D02_extension_namespace_attribute_is_preserved(self):
        """扩展属性本身必须原样保留（只读判定，不改用户内容）。"""

        def add_declared_extension_attribute(xml: str) -> str:
            xml = re.sub(r"<worksheet\b",
                         f'<worksheet xmlns:e="{OTHER_NS}"', xml, count=1)
            return re.sub(r'<c r="U4"', '<c r="U4" e:r="ZZ999">', xml, count=1)

        source = self.mutate("d02b.xlsx", add_declared_extension_attribute)
        result = self.result_of(source, "d02b_out.xlsx")
        with zipfile.ZipFile(result.result_workbook) as archive:
            out = archive.read(sheet_target(archive)).decode("utf-8")
        self.assertIn('e:r="ZZ999"', out, "扩展属性必须保留")

    # ==================================================================
    # D03 — 合法扩展内容不得被误拒
    # ==================================================================

    def test_D03_extension_payload_in_own_namespace_is_accepted(self):
        """`extLst` 内独立命名空间的同名元素不构成命名空间错误。"""

        def add_extension(xml: str) -> str:
            extension = (
                f'<extLst><ext uri="{{EQUIPEFFI-EXT}}" xmlns:e="{OTHER_NS}">'
                "<e:t>sentinel</e:t><e:c>not-a-cell</e:c></ext></extLst>")
            return xml.replace("</worksheet>", extension + "</worksheet>")

        source = self.mutate("d03.xlsx", add_extension)
        self.assertEqual(len(V6PumpWorkbookReader().read(source).rows), 1)

        result = self.result_of(source, "d03_out.xlsx")
        with zipfile.ZipFile(result.result_workbook) as archive:
            out = archive.read(sheet_target(archive)).decode("utf-8")
        self.assertIn("sentinel", out, "合法扩展 payload 必须保留")
        root = ElementTree.fromstring(out)
        # `extLst` / `ext` 本身是 SpreadsheetML 元素；只有 payload 在扩展命名空间
        containers = list(root.iter("{" + MAIN_NS + "}extLst"))
        self.assertEqual(len(containers), 1, "扩展容器必须保留")
        payloads = list(root.iter("{" + OTHER_NS + "}t"))
        self.assertEqual(len(payloads), 1,
                         "扩展内的 e:t 必须留在它自己的命名空间")
        self.assertEqual(payloads[0].text, "sentinel")
        # 扩展容器**内部**不得把 payload 搬进 MAIN_NS
        # （工作表别处的 `{MAIN_NS}t` 是结果文本的合法 inline string，不在此列）
        for element in containers[0].iter():
            with self.subTest(element=element.tag):
                self.assertFalse(
                    element.tag.startswith("{" + MAIN_NS + "}")
                    and element.tag.endswith("}t") and element.text == "sentinel",
                    "扩展 payload 不得被改写进 SpreadsheetML 命名空间")

    # ==================================================================
    # 嵌套 prefix 重绑定（词法作用域）
    # ==================================================================

    def test_nested_prefix_rebinding_keeps_the_extension_namespace(self):
        """后代重绑定同一前缀时，扩展 payload 必须留在**它的**命名空间。"""

        def add_rebinding(xml: str) -> str:
            extension = (
                '<x:extLst><x:ext uri="{NESTED}">'
                f'<x:payload xmlns:x="{OTHER_NS}">sentinel</x:payload>'
                "</x:ext></x:extLst>")
            if "</x:worksheet>" not in xml:
                raise AssertionError("夹具必须是 x: 前缀形式")
            return xml.replace("</x:worksheet>", extension + "</x:worksheet>", 1)

        def prefix_all(xml: str) -> str:
            """把该 sheet 的元素整体前缀化为 x:（保语义：原本都在 MAIN_NS）。"""

            xml = re.sub(r"<(/?)([A-Za-z_][\w.-]*)(?=[\s/>])", r"<\1x:\2", xml)
            # 根上：去掉原默认 xmlns，改为声明 xmlns:x=MAIN_NS
            def fix_root(match):
                tag = re.sub(r'\sxmlns="[^"]*"', "", match.group(0))
                return tag[:-1].rstrip() + f' xmlns:x="{MAIN_NS}">'

            return re.sub(r"<x:worksheet\b[^>]*>", fix_root, xml, count=1)

        source = self.mutate("nested.xlsx", lambda xml: add_rebinding(prefix_all(xml)))
        result = self.result_of(source, "nested_out.xlsx")
        with zipfile.ZipFile(result.result_workbook) as archive:
            out = archive.read(sheet_target(archive)).decode("utf-8")
        root = ElementTree.fromstring(out)
        payloads = list(root.iter("{" + OTHER_NS + "}payload"))
        self.assertEqual(len(payloads), 1, "嵌套重绑定的 payload 必须保留")
        self.assertEqual(payloads[0].text, "sentinel")
        self.assertEqual(list(root.iter("{" + MAIN_NS + "}payload")), [],
                         "payload 不得被改写进 SpreadsheetML 命名空间")

    def test_case_a_unprefixed_extension_remains_no_namespace(self):
        """无默认 namespace 时，裸 <payload> 不得因 Writer 补 xmlns 而进入 MAIN_NS。"""

        def prefix_main_and_add_bare_extension(xml: str) -> str:
            xml = re.sub(r"<(/?)([A-Za-z_][\w.-]*)(?=[\s/>])", r"<\1x:\2", xml)

            def fix_root(match):
                tag = re.sub(r'\sxmlns="[^"]*"', "", match.group(0))
                return tag[:-1].rstrip() + f' xmlns:x="{MAIN_NS}">'

            xml = re.sub(r"<x:worksheet\b[^>]*>", fix_root, xml, count=1)
            extension = (
                '<x:extLst><x:ext uri="{NO-DEFAULT-EXT}">'
                '<payload kind="independent">sentinel</payload>'
                '</x:ext></x:extLst>')
            return xml.replace("</x:worksheet>", extension + "</x:worksheet>", 1)

        source = self.mutate("bare_extension.xlsx", prefix_main_and_add_bare_extension)
        with zipfile.ZipFile(source) as archive:
            before_xml = archive.read(sheet_target(archive)).decode("utf-8")
        before_root = ElementTree.fromstring(before_xml)
        self.assertEqual(len(list(before_root.iter("payload"))), 1)
        self.assertEqual(list(before_root.iter("{" + MAIN_NS + "}payload")), [])

        result = self.result_of(source, "bare_extension_out.xlsx")
        with zipfile.ZipFile(result.result_workbook) as archive:
            out = archive.read(sheet_target(archive)).decode("utf-8")
        root = ElementTree.fromstring(out)

        payloads = list(root.iter("payload"))
        self.assertEqual(len(payloads), 1,
                         "原本无命名空间的 payload 必须继续无命名空间")
        self.assertEqual(payloads[0].text, "sentinel")
        self.assertEqual(payloads[0].attrib.get("kind"), "independent")
        self.assertEqual(list(root.iter("{" + MAIN_NS + "}payload")), [],
                         "payload 不得被补加的默认命名空间污染")
        self.assertIn('xmlns=""', out,
                      "A 情况必须为无命名空间扩展子树建立显式边界")
        self.assertEqual(len(self.batch.batch_repository.list_batch_records()), 1)

    # ==================================================================
    # 唯一性门禁与输入保真
    # ==================================================================

    def test_duplicate_coordinate_still_fails_closed(self):
        def duplicate(xml: str) -> str:
            match = re.search(r'<c r="U4"[^>]*/>|<c r="U4"[^>]*>.*?</c>', xml)
            return xml[:match.end()] + match.group(0) + xml[match.end():]

        source = self.mutate("dup.xlsx", duplicate)
        destination = self.root / "dup_out.xlsx"
        with self.assertRaises(ResultWorkbookWriteError):
            self.batch.evaluate_workbook(source, destination=destination,
                                         as_of=AS_OF, persist=True)
        self.assertFalse(destination.exists())
        self.assertEqual(len(self.batch.batch_repository.list_batch_records()), 0)

    def test_user_input_cells_are_never_rewritten(self):
        result = self.result_of(self.source, "preserve_out.xlsx")
        before = self.cells_of(self.source)
        after = self.cells_of(result.result_workbook)
        for reference, value in before.items():
            column = "".join(ch for ch in reference if ch.isalpha())
            if column in ("N", "O", "P", "Q", "R", "S", "T", "U", "V", "W",
                          "X", "AA"):
                continue
            with self.subTest(reference=reference):
                self.assertEqual(after[reference], value)

    def test_high_precision_input_survives(self):
        literal = "100.12345678901234567890123456789012345"
        source = self.mutate("precision.xlsx", lambda xml: re.sub(
            r'<c r="G4"[^>]*>.*?</c>|<c r="G4"[^>]*/>',
            f'<c r="G4" s="226"><v>{literal}</v></c>', xml, count=1))
        result = self.result_of(source, "precision_out.xlsx")
        with zipfile.ZipFile(result.result_workbook) as archive:
            out = archive.read(sheet_target(archive)).decode("utf-8")
        self.assertIn(literal, out, "用户输入精度必须逐字节保留")

    def test_only_the_pump_sheet_differs_from_the_input(self):
        result = self.result_of(self.source, "parts_out.xlsx")
        with zipfile.ZipFile(self.source) as archive:
            before = {name: archive.read(name) for name in archive.namelist()}
        with zipfile.ZipFile(result.result_workbook) as archive:
            after = {info.filename: archive.read(info.filename)
                     for info in archive.infolist()}
        self.assertEqual(set(before), set(after))
        changed = [name for name in before if before[name] != after[name]]
        self.assertEqual(changed, [sheet_target(zipfile.ZipFile(self.source))])

    # ==================================================================
    # D04 — 原子提交：失败不得留下残缺文件
    # ==================================================================

    def test_D04_disk_failure_leaves_no_partial_file(self):
        """落盘中途失败：目标不存在、无临时残留、无成功 batch_record。"""

        import equipeffi.infrastructure.excel.pump_result_writer as writer_module

        original = writer_module.PumpResultWorkbookWriter._commit
        destination = self.root / "d04_out.xlsx"

        def failing_commit(self, destination, entries, patched):
            # 复用真实实现，但让第 2 个部件的写入抛磁盘错误
            from zipfile import ZIP_DEFLATED, ZipFile

            temporary = destination.with_name(
                f".{destination.name}.{uuid.uuid4().hex}"
                f"{writer_module._TEMP_SUFFIX}")
            try:
                with ZipFile(temporary, "w", ZIP_DEFLATED) as target:
                    for index, ((info, _original), data) in enumerate(
                            zip(entries, patched)):
                        if index == 1:
                            raise OSError(28, "No space left on device")
                        target.writestr(info, data)
                import os

                os.replace(temporary, destination)
            except BaseException:
                try:
                    if temporary.exists():
                        temporary.unlink()
                except OSError:
                    pass
                raise

        import uuid

        writer_module.PumpResultWorkbookWriter._commit = failing_commit
        try:
            with self.assertRaises(OSError):
                self.batch.evaluate_workbook(
                    self.source, destination=destination, as_of=AS_OF,
                    persist=True)
        finally:
            writer_module.PumpResultWorkbookWriter._commit = original

        self.assertFalse(destination.exists(), "不得留下残缺结果文件")
        leftovers = [p.name for p in self.root.iterdir()
                     if p.name.startswith(".")]
        self.assertEqual(leftovers, [], "不得留下临时文件")
        self.assertEqual(len(self.batch.batch_repository.list_batch_records()), 0,
                         "写失败不得保存成功 batch_record")

    def test_existing_destination_is_not_silently_overwritten(self):
        destination = self.root / "exists_out.xlsx"
        self.batch.evaluate_workbook(self.source, destination=destination,
                                     as_of=AS_OF, persist=False)
        from equipeffi.infrastructure.excel.pump_result_writer import (
            ResultWorkbookExistsError,
        )

        with self.assertRaises(ResultWorkbookExistsError):
            self.batch.evaluate_workbook(self.source, destination=destination,
                                         as_of=AS_OF, persist=False)

    # ==================================================================
    # 独立不变量本身
    # ==================================================================

    def test_independent_parser_rejects_duplicate_coordinates(self):
        xml = (f'<worksheet xmlns="{MAIN_NS}"><sheetData><row r="4">'
               '<c r="U4"><v>1</v></c><c r="U4"><v>2</v></c>'
               "</row></sheetData></worksheet>")
        with self.assertRaises(InvariantViolation):
            assert_unique_references(xml)

    def test_identity_model_separates_namespaced_attributes(self):
        xml = (f'<worksheet xmlns="{MAIN_NS}" xmlns:e="{OTHER_NS}">'
               '<sheetData><row r="4"><c r="U4" e:r="ZZ999"/></row>'
               "</sheetData></worksheet>")
        cell = next(element for element in parse_elements(xml)
                    if element.local == "c")
        self.assertEqual(cell.attribute_value("r"), "U4")
        self.assertEqual(cell.attribute_value("r", OTHER_NS), "ZZ999")

    def test_default_namespace_uri_distinguishes_the_three_cases(self):
        for default, expected in ((None, None), (MAIN_NS, MAIN_NS),
                                  (OTHER_NS, OTHER_NS)):
            declaration = "" if default is None else f' xmlns="{default}"'
            xml = (f"<worksheet{declaration}><sheetData/></worksheet>")
            with self.subTest(default=default):
                self.assertEqual(default_namespace_uri(xml), expected)


if __name__ == "__main__":
    unittest.main()
