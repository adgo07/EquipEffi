"""Phase 8 R3 — OOXML 命名空间保持（最终 blocker 回归）。

被 `PHASE_8_BLOCKED` 的 head 为
`fec8fd0ddbcc64e861e05a6ad204463a6d7fcc0c`，本轮 blocker 是：

> 合法 worksheet 使用 `xmlns="某个非 SpreadsheetML URI"` +
> `xmlns:x="…/spreadsheetml/2006/main"`，并以 `<x:row>` / `<x:c>` / `<x:v>`
> 承载 SpreadsheetML 元素时，Writer 错误删除 `x:` 前缀，
> 导致这些元素落入**错误的默认命名空间**。

根因：`_has_default_namespace()` 只判断"是否存在 `xmlns="…"`"，
没有判断该 URI 是什么，于是把「存在任意默认 namespace」当成
「已经是 SpreadsheetML 默认 namespace」。

三种必须区分的情况（§二）：

```text
A. 没有默认 namespace            -> 允许规范化为 xmlns="MAIN_NS"
B. 默认 namespace == MAIN_NS     -> 允许删除冗余 x: 前缀
C. 默认 namespace != MAIN_NS     -> 必须保留 xmlns:x 与 x: 前缀
```

本模块用**真正合法、前置变换保语义**的 OOXML fixture 覆盖这三种情况，
并额外用 namespace-aware 解析器做**最终语义门禁**（§六）。
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import openpyxl

from equipeffi.infrastructure.excel.pump_result_writer import (
    PumpResultWorkbookWriter,
    ResultWorkbookWriteError,
    _assert_main_namespace_semantics,
    _default_namespace_uri,
)
from equipeffi.infrastructure.excel.pump_workbook_reader import (
    PUMP_SHEET,
    V6PumpWorkbookReader,
)
from equipeffi.infrastructure.excel.template_resource import V6TemplateResource

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OTHER_NS = "urn:equipeffi:not-spreadsheetml"
EXT_NS = "urn:independent:extension"
FIRST_DATA_ROW = 4
AS_OF = date(2026, 8, 23)


# ---------------------------------------------------------------------------
# Fixture 构造（保语义的前置变换）
# ---------------------------------------------------------------------------

def _sheet_target(archive: zipfile.ZipFile, sheet_name: str) -> str:
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


def _prefix_all_elements(xml: str) -> str:
    """把**所有**元素名限定成 ``x:``（属性一字不动）。

    调用前提：根元素已声明 ``xmlns:x=MAIN_NS``。因为该 sheet 里所有元素原本
    都属于 MAIN_NS（默认命名空间），把它们显式限定为 ``x:`` 保持语义不变。
    """

    return re.sub(r"<(/?)([A-Za-z_][\w.-]*)(?=[\s/>])", r"<\1x:\2", xml)


def _set_root_declarations(xml: str, default_uri: str | None) -> str:
    """重写根元素上的 ``xmlns`` / ``xmlns:x``（其它属性保持原样）。"""

    def replace_root(match: re.Match[str]) -> str:
        tag = match.group(0)
        tag = re.sub(r'\sxmlns(?::[A-Za-z_][\w.-]*)?="[^"]*"', "", tag)
        additions = ""
        if default_uri is not None:
            additions += f' xmlns="{default_uri}"'
        additions += f' xmlns:x="{MAIN_NS}"'
        return tag[:-1].rstrip() + additions + ">"

    return re.sub(r"<x:worksheet\b[^>]*>", replace_root, xml, count=1)


def build_prefixed_worksheet(source: Path, destination: Path,
                             *, default_uri: str | None,
                             already_prefixed: bool = False) -> Path:
    """生成"SpreadsheetML 元素带 ``x:`` 前缀"的合法 fixture。

    ``default_uri=None``  -> 情况 A（无默认命名空间）
    ``default_uri=MAIN_NS`` -> 情况 B（默认 == MAIN）
    ``default_uri=OTHER_NS`` -> 情况 C（默认 != MAIN，本轮 blocker）
    """

    shutil.copy(source, destination)
    with zipfile.ZipFile(destination) as archive:
        entries = [(info, archive.read(info.filename))
                   for info in archive.infolist()]
        target = _sheet_target(archive, PUMP_SHEET)
        for info, data in entries:
            if info.filename == target:
                sheet_xml = data.decode("utf-8")
                break
        else:
            raise AssertionError("找不到工作表 XML")

    if not already_prefixed:
        sheet_xml = _prefix_all_elements(sheet_xml)
    sheet_xml = _set_root_declarations(sheet_xml, default_uri)

    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for info, data in entries:
            if info.filename == target:
                data = sheet_xml.encode("utf-8")
            archive.writestr(info, data)
    return destination


def read_sheet_xml(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(_sheet_target(archive, PUMP_SHEET)).decode("utf-8")


def add_nested_prefix_rebinding_extension(path: Path) -> Path:
    """加入合法的嵌套 xmlns:x 重绑定扩展 payload。"""

    with zipfile.ZipFile(path) as archive:
        entries = [(info, archive.read(info.filename))
                   for info in archive.infolist()]
        target = _sheet_target(archive, PUMP_SHEET)

    extension = (
        '<x:extLst><x:ext uri="{EQUIPEFFI-NESTED-REBIND}">'
        f'<x:payload xmlns:x="{EXT_NS}">sentinel</x:payload>'
        '</x:ext></x:extLst>'
    )
    rewritten: list[tuple[zipfile.ZipInfo, bytes]] = []
    for info, data in entries:
        if info.filename == target:
            xml = data.decode("utf-8")
            marker = "</x:worksheet>"
            if marker not in xml:
                raise AssertionError("fixture 必须是 x:worksheet 前缀形式")
            xml = xml.replace(marker, extension + marker, 1)
            root = ElementTree.fromstring(xml)
            payloads = list(root.iter("{" + EXT_NS + "}payload"))
            if len(payloads) != 1 or payloads[0].text != "sentinel":
                raise AssertionError("嵌套 xmlns:x 重绑定 fixture 构造失败")
            data = xml.encode("utf-8")
        rewritten.append((info, data))

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for info, data in rewritten:
            archive.writestr(info, data)
    return path


# ---------------------------------------------------------------------------
# 测试
# ---------------------------------------------------------------------------

class R3NamespaceTestCase(unittest.TestCase):
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
        self.source = self.make("输入.xlsx")
        self.addCleanup(self.tmp.cleanup)

    @staticmethod
    def water(**overrides) -> dict:
        row = dict(B="水泵", C="M-001", D=1, E="1号车间", F="单级单吸清水离心泵",
                   G=100, H=50, I=2900, J=45, K="单吸", L=1, M=78)
        row.update(overrides)
        return row

    def make(self, name: str) -> Path:
        path = self.root / name
        V6TemplateResource().download_to(path)
        workbook = openpyxl.load_workbook(path)
        sheet = workbook[PUMP_SHEET]
        for column, value in self.water().items():
            sheet[f"{column}{FIRST_DATA_ROW}"] = value
        workbook.save(path)
        workbook.close()
        return path

    # -- §五.1 情况 A -------------------------------------------------------

    def test_case_a_no_default_namespace_is_normalised(self):
        """无默认 namespace + `x:MAIN_NS` -> 归一为默认命名空间，输出可重新读取。"""

        fixture = build_prefixed_worksheet(
            self.source, self.root / "case_a.xlsx", default_uri=None)
        self.assertIsNone(_default_namespace_uri(read_sheet_xml(fixture)))

        result = self.batch.evaluate_workbook(
            fixture, destination=self.root / "case_a_out.xlsx", as_of=AS_OF,
            persist=False)
        xml = read_sheet_xml(result.result_workbook)
        _assert_main_namespace_semantics(xml)
        root = ElementTree.fromstring(xml)
        self.assertEqual(root.tag, "{" + MAIN_NS + "}worksheet")
        # 允许去前缀：元素已属默认 MAIN_NS
        self.assertNotIn("<x:row", xml)
        # 正式 Reader 可重新读取
        self.assertEqual(len(V6PumpWorkbookReader().read(
            result.result_workbook).rows), 1)

    # -- §五.2 情况 B -------------------------------------------------------

    def test_case_b_default_main_namespace_drops_redundant_prefix(self):
        """默认 == MAIN_NS + `x:MAIN_NS` -> 可安全去前缀，输出可重新读取。"""

        fixture = build_prefixed_worksheet(
            self.source, self.root / "case_b.xlsx", default_uri=MAIN_NS)
        xml_before = read_sheet_xml(fixture)
        self.assertEqual(_default_namespace_uri(xml_before), MAIN_NS)

        result = self.batch.evaluate_workbook(
            fixture, destination=self.root / "case_b_out.xlsx", as_of=AS_OF,
            persist=False)
        xml = read_sheet_xml(result.result_workbook)
        _assert_main_namespace_semantics(xml)
        self.assertNotIn("<x:row", xml, "情况 B 允许去掉冗余前缀")
        self.assertNotIn(f'xmlns:x="{MAIN_NS}"', xml, "冗余声明应被移除")
        self.assertEqual(len(V6PumpWorkbookReader().read(
            result.result_workbook).rows), 1)

    # -- §五.3 情况 C（本轮核心）-------------------------------------------

    def test_case_c_other_default_namespace_preserves_main_ns(self):
        """【本轮核心】默认 == OTHER_URI + `x:MAIN_NS`。

        必须：MAIN_NS 元素仍属 MAIN_NS、不得落入 OTHER_URI、
        正式 Reader 可重新读取、U4 结果正确、无重复坐标、工作簿良构。
        """

        fixture = build_prefixed_worksheet(
            self.source, self.root / "case_c.xlsx", default_uri=OTHER_NS)
        xml_before = read_sheet_xml(fixture)
        self.assertEqual(_default_namespace_uri(xml_before), OTHER_NS)
        self.assertIn("<x:row", xml_before)
        # 前置条件：fixture 合法且语义正确（SpreadsheetML 在 MAIN_NS）
        _assert_main_namespace_semantics(xml_before)
        self.assertEqual(len(V6PumpWorkbookReader().read(fixture).rows), 1)

        result = self.batch.evaluate_workbook(
            fixture, destination=self.root / "case_c_out.xlsx", as_of=AS_OF,
            persist=False)
        xml = read_sheet_xml(result.result_workbook)

        # 1) MAIN_NS 语义必须保住（namespace-aware 解析，不是字符串判断）
        _assert_main_namespace_semantics(xml)
        root = ElementTree.fromstring(xml)
        self.assertEqual(root.tag, "{" + MAIN_NS + "}worksheet")
        # 2) 默认命名空间仍是 OTHER_URI，且 MAIN_NS 前缀声明必须保留
        self.assertEqual(_default_namespace_uri(xml), OTHER_NS)
        self.assertIn(f'xmlns:x="{MAIN_NS}"', xml,
                      "情况 C 必须保留 xmlns:x=MAIN_NS")
        # 3) 所有核心元素仍在 MAIN_NS（不得落入 OTHER_URI）
        for element in root.iter():
            local = element.tag.rsplit("}", 1)[-1]
            if local in ("worksheet", "sheetData", "row", "c", "v"):
                with self.subTest(element=element.tag):
                    self.assertTrue(
                        element.tag.startswith("{" + MAIN_NS + "}"),
                        f"{element.tag} 落入了错误命名空间")
        # 4) U4 结果正确
        sheet = openpyxl.load_workbook(result.result_workbook)[PUMP_SHEET]
        self.assertIsNotNone(sheet[f"X{FIRST_DATA_ROW}"].value)
        self.assertIsNotNone(sheet[f"U{FIRST_DATA_ROW}"].value)
        # 5) 无重复坐标
        references = re.findall(r'r="([A-Z]+\d+)"', xml)
        self.assertEqual([ref for ref in set(references)
                          if references.count(ref) > 1], [])
        # 6) 工作簿良构
        ElementTree.fromstring(xml)
        # 7) 正式 Reader 可重新读取
        reopened = V6PumpWorkbookReader().read(result.result_workbook)
        self.assertEqual(len(reopened.rows), 1)
        self.assertEqual(reopened.rows[0].values.get("device_name"), "水泵")

    # -- §五.4 情况 C + 已存在 U4 ------------------------------------------

    def test_case_c_updates_existing_cell_in_place(self):
        """默认 OTHER_URI + `x:MAIN_NS` + 已存在 U4 -> 原位更新，不新增第二个。"""

        fixture = build_prefixed_worksheet(
            self.source, self.root / "case_c2.xlsx", default_uri=OTHER_NS)
        xml = read_sheet_xml(fixture)
        self.assertEqual(len(re.findall(r'r="U4"', xml)), 1,
                         "fixture 里 U4 应已存在且唯一")

        result = self.batch.evaluate_workbook(
            fixture, destination=self.root / "case_c2_out.xlsx", as_of=AS_OF,
            persist=False)
        out = read_sheet_xml(result.result_workbook)
        self.assertEqual(len(re.findall(r'r="U4"', out)), 1,
                         "必须原位更新，不得新增第二个 U4")
        _assert_main_namespace_semantics(out)
        sheet = openpyxl.load_workbook(result.result_workbook)[PUMP_SHEET]
        self.assertIsNotNone(sheet[f"U{FIRST_DATA_ROW}"].value)

    # -- §五.5 情况 C + 重复坐标 -> fail closed ----------------------------

    def test_case_c_duplicate_coordinate_still_fails_closed(self):
        """默认 OTHER_URI + `x:MAIN_NS` + duplicate U4 -> 继续 fail closed。"""

        fixture = build_prefixed_worksheet(
            self.source, self.root / "case_c3.xlsx", default_uri=OTHER_NS)
        # 人为把既有 U4 复制一份（制造歧义输入）
        xml = read_sheet_xml(fixture)
        match = re.search(r'<x:c[^>]*r="U4"[^>]*>.*?</x:c>|<x:c[^>]*r="U4"[^>]*/>', xml)
        self.assertIsNotNone(match)
        duplicated = xml[:match.end()] + match.group(0) + xml[match.end():]
        with zipfile.ZipFile(fixture) as archive:
            entries = [(info, archive.read(info.filename))
                       for info in archive.infolist()]
            target = _sheet_target(archive, PUMP_SHEET)
        with zipfile.ZipFile(fixture, "w", zipfile.ZIP_DEFLATED) as archive:
            for info, data in entries:
                if info.filename == target:
                    data = duplicated.encode("utf-8")
                archive.writestr(info, data)

        with self.assertRaises(ResultWorkbookWriteError):
            self.batch.evaluate_workbook(
                fixture, destination=self.root / "case_c3_out.xlsx", as_of=AS_OF)
        self.assertFalse((self.root / "case_c3_out.xlsx").exists(),
                         "写回失败不得留下假成功结果文件")
        self.assertEqual(
            len(self.batch.batch_repository.list_batch_records()), 0,
            "写回失败不得保存成功 batch_record")

    # -- §五.6/§六 嵌套 xmlns 前缀重绑定 -----------------------------------

    def test_nested_x_rebinding_is_preserved_in_cases_a_and_b(self):
        """A/B 情况下，局部 xmlns:x 重绑定的扩展 QName 必须原样保真。"""

        for label, default_uri in (("a", None), ("b", MAIN_NS)):
            with self.subTest(case=label):
                fixture = build_prefixed_worksheet(
                    self.source, self.root / f"nested_{label}.xlsx",
                    default_uri=default_uri)
                add_nested_prefix_rebinding_extension(fixture)
                before = ElementTree.fromstring(read_sheet_xml(fixture))
                self.assertEqual(
                    len(list(before.iter("{" + EXT_NS + "}payload"))), 1,
                    "前置 fixture 必须真实包含独立扩展 namespace payload")

                result = self.batch.evaluate_workbook(
                    fixture,
                    destination=self.root / f"nested_{label}_out.xlsx",
                    as_of=AS_OF, persist=False)
                out_xml = read_sheet_xml(result.result_workbook)
                root = ElementTree.fromstring(out_xml)

                extension_payloads = list(root.iter("{" + EXT_NS + "}payload"))
                self.assertEqual(len(extension_payloads), 1)
                self.assertEqual(extension_payloads[0].text, "sentinel")
                self.assertEqual(
                    list(root.iter("{" + MAIN_NS + "}payload")), [],
                    "扩展 payload 不得被静默改写进 SpreadsheetML namespace")
                self.assertIn(f'xmlns:x="{EXT_NS}"', out_xml,
                              "局部扩展 namespace 声明必须保留")
                _assert_main_namespace_semantics(out_xml)

    def test_qname_gate_blocks_namespace_drift_before_file_and_batch_record(self):
        """即使归一化未来回归，QName 门禁也必须阻断结果文件与 batch_record。"""

        fixture = build_prefixed_worksheet(
            self.source, self.root / "nested_guard.xlsx", default_uri=None)
        add_nested_prefix_rebinding_extension(fixture)
        destination = self.root / "nested_guard_out.xlsx"

        import equipeffi.infrastructure.excel.pump_result_writer as writer_module
        original = writer_module._normalise_main_namespace

        def deliberately_corrupt(xml: str) -> str:
            normalised = original(xml)
            normalised = normalised.replace(
                f'<x:payload xmlns:x="{EXT_NS}">',
                f'<payload xmlns:x="{EXT_NS}">', 1)
            normalised = normalised.replace("</x:payload>", "</payload>", 1)
            ElementTree.fromstring(normalised)
            return normalised

        with patch.object(writer_module, "_normalise_main_namespace",
                          side_effect=deliberately_corrupt):
            with self.assertRaises(ResultWorkbookWriteError):
                self.batch.evaluate_workbook(
                    fixture, destination=destination, as_of=AS_OF, persist=True)

        self.assertFalse(destination.exists(),
                         "命名空间语义门禁失败时不得留下结果工作簿")
        self.assertEqual(
            len(self.batch.batch_repository.list_batch_records()), 0,
            "Writer 失败时不得保存成功 batch_record")

    # -- §六 语义门禁本身 ---------------------------------------------------

    def test_semantic_gate_rejects_wrong_namespace_output(self):
        """门禁必须抓住"语法合法但命名空间语义错误"的 worksheet。"""

        bad = (f'<worksheet xmlns="{OTHER_NS}">'
               '<sheetData><row r="4"><c r="U4"><v>1</v></c></row></sheetData>'
               '</worksheet>')
        ElementTree.fromstring(bad)  # 语法完全合法
        with self.assertRaises(ResultWorkbookWriteError):
            _assert_main_namespace_semantics(bad)

    def test_writer_never_strips_prefix_when_default_is_other(self):
        """机械守卫：情况 C 下不得出现"去掉前缀但没补 MAIN_NS 绑定"的结果。"""

        fixture = build_prefixed_worksheet(
            self.source, self.root / "guard.xlsx", default_uri=OTHER_NS)
        result = self.batch.evaluate_workbook(
            fixture, destination=self.root / "guard_out.xlsx", as_of=AS_OF,
            persist=False)
        xml = read_sheet_xml(result.result_workbook)
        # 只要默认命名空间不是 MAIN_NS，就绝不能存在裸 `row` / `c` / `v`
        if _default_namespace_uri(xml) != MAIN_NS:
            for tag in ("row", "c", "v", "sheetData"):
                with self.subTest(tag=tag):
                    self.assertNotRegex(
                        xml, r"<" + tag + r"[\s/>]",
                        f"默认命名空间非 MAIN_NS 时不得出现裸 <{tag}>")
        _assert_main_namespace_semantics(xml)


if __name__ == "__main__":
    unittest.main()
