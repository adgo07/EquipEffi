from __future__ import annotations

from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from pathlib import Path
import posixpath
import re
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


class OOXMLReadError(ValueError):
    """Office Open XML工作簿无法读取。"""


_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _tag(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def _column_index(reference: str) -> int:
    letters = re.match(r"([A-Z]+)", reference.upper())
    if not letters:
        raise OOXMLReadError(f"单元格地址无效: {reference}")
    value = 0
    for char in letters.group(1):
        value = value * 26 + ord(char) - ord("A") + 1
    return value - 1


def _parse_number(value: str) -> Any:
    """解析 OOXML 数值单元格，**保持可证明的十进制语义**。

    Phase 8 / QA-EXCEL-001：本函数曾经把非整数 `Decimal` 转成 `float`，
    再经 `str()` 送进正式评价链，等于把 Numeric Contract 降级成 float。
    实测精度损失（Excel 的十进制文本 → float → str）：

    ```text
    0.12345678901234567890123456789012345  ->  0.12345678901234568   （35 位变 17 位）
    12345678901234567890                   ->  1.2345678901234567e+19（大整数被改写）
    ```

    因此这里直接返回 `int` / `Decimal`：整数值返回 `int`，其余保留 `Decimal`，
    **绝不经过 `float`**。Excel 自己写出的十进制文本本身就是最好的十进制来源。
    """

    text = value.strip()
    if text == "":
        return ""
    try:
        number = Decimal(text)
    except InvalidOperation:
        return text
    if number == number.to_integral_value():
        return int(number)
    return number


def _inline_text(node: ElementTree.Element) -> str:
    return "".join(element.text or "" for element in node.iter(_tag(_MAIN_NS, "t")))


@dataclass(frozen=True)
class OOXMLCellMetadata:
    """Input-cell type details that a cached-value read cannot preserve."""

    cell_type: str
    style_index: int | None
    has_formula: bool
    raw_value: str
    is_date: bool


_BUILTIN_DATE_FORMAT_IDS = frozenset({
    *range(14, 23), 27, 28, 29, 30, 31, 32, 33, 34, 35, 36,
    45, 46, 47, *range(50, 59),
})


def _is_date_format_code(format_code: str) -> bool:
    """Recognize Excel date/time format tokens without interpreting cell values."""

    text = re.sub(r'"(?:[^"]|"")*"', "", format_code.lower())
    text = re.sub(r"\\.", "", text)
    bracket_tokens = re.findall(r"\[([^\]]*)\]", text)
    if any(re.fullmatch(r"\s*[hms]+\s*", token) for token in bracket_tokens):
        return True
    text = re.sub(r"\[[^\]]*\]", "", text)
    return bool(re.search(r"[ydhs]", text) or re.search(r"(?<![a-z])m{1,4}(?![a-z])", text))


class OOXMLWorkbook:
    """只读、无外部依赖的xlsx基础读取器。

    它只读取单元格值、工作表名称和合并范围，不保存或改写压缩包，因此不会破坏图片、保护和公式。
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        try:
            self.archive = ZipFile(self.path)
        except (BadZipFile, OSError) as exc:
            raise OOXMLReadError(f"无法打开xlsx文件: {exc}") from exc
        self._shared_strings = self._read_shared_strings()
        self._sheets = self._read_sheet_targets()
        self._merged_ranges: dict[str, tuple[str, ...]] = {}

    def __enter__(self) -> "OOXMLWorkbook":
        return self

    def __exit__(self, _type, _value, _trace) -> None:
        self.archive.close()

    def _read_shared_strings(self) -> tuple[str, ...]:
        try:
            xml = self.archive.read("xl/sharedStrings.xml")
        except KeyError:
            return ()
        root = ElementTree.fromstring(xml)
        return tuple(_inline_text(node) for node in root.findall(_tag(_MAIN_NS, "si")))

    def _read_sheet_targets(self) -> dict[str, str]:
        try:
            workbook_root = ElementTree.fromstring(self.archive.read("xl/workbook.xml"))
            rel_root = ElementTree.fromstring(self.archive.read("xl/_rels/workbook.xml.rels"))
        except (KeyError, ElementTree.ParseError) as exc:
            raise OOXMLReadError(f"工作簿关系结构无效: {exc}") from exc
        relationships = {
            node.attrib.get("Id", ""): node.attrib.get("Target", "")
            for node in rel_root.findall(_tag(_PKG_REL_NS, "Relationship"))
        }
        sheets: dict[str, str] = {}
        for node in workbook_root.findall(f"{{{_MAIN_NS}}}sheets/{{{_MAIN_NS}}}sheet"):
            name = node.attrib.get("name", "")
            rel_id = node.attrib.get(_tag(_REL_NS, "id"), "")
            target = relationships.get(rel_id, "")
            if not name or not target:
                continue
            if target.startswith("/"):
                target = target[1:]
            elif not target.startswith("xl/"):
                target = f"xl/{target}"
            target = posixpath.normpath(target)
            sheets[name] = target
        return sheets

    @property
    def sheet_names(self) -> tuple[str, ...]:
        return tuple(self._sheets)

    def merged_ranges(self, sheet_name: str) -> tuple[str, ...]:
        """Return merge references captured while parsing this sheet with rows()."""

        if sheet_name not in self._sheets:
            raise OOXMLReadError(f"工作簿中不存在sheet: {sheet_name}")
        return self._merged_ranges.get(sheet_name, ())

    def _date_style_indexes(self) -> frozenset[int]:
        try:
            root = ElementTree.fromstring(self.archive.read("xl/styles.xml"))
        except KeyError:
            return frozenset()
        except ElementTree.ParseError as exc:
            raise OOXMLReadError(f"工作簿样式结构无效: {exc}") from exc

        formats = {
            int(node.attrib["numFmtId"]): node.attrib.get("formatCode", "")
            for node in root.findall(f"{_tag(_MAIN_NS, 'numFmts')}/{_tag(_MAIN_NS, 'numFmt')}")
            if node.attrib.get("numFmtId", "").isdigit()
        }
        cell_formats = root.find(_tag(_MAIN_NS, "cellXfs"))
        if cell_formats is None:
            return frozenset()
        date_indexes: set[int] = set()
        for index, cell_format in enumerate(cell_formats.findall(_tag(_MAIN_NS, "xf"))):
            raw_id = cell_format.attrib.get("numFmtId", "0")
            if not raw_id.isdigit():
                continue
            format_id = int(raw_id)
            if (format_id in _BUILTIN_DATE_FORMAT_IDS
                    or _is_date_format_code(formats.get(format_id, ""))):
                date_indexes.add(index)
        return frozenset(date_indexes)

    def cell_metadata(self, sheet_name: str, *, columns: set[str] | None = None
                      ) -> dict[str, OOXMLCellMetadata]:
        """Expose formula, error, and date-style markers beside parsed cell values.

        `rows()` intentionally returns formula cached values for compatibility with
        its established callers. Adapters that cannot accept cached calculations
        can use this parallel metadata view to reject formula inputs explicitly.
        """

        target = self._sheets.get(sheet_name)
        if not target:
            raise OOXMLReadError(f"工作簿中不存在sheet: {sheet_name}")
        try:
            root = ElementTree.fromstring(self.archive.read(target))
        except (KeyError, ElementTree.ParseError) as exc:
            raise OOXMLReadError(f"sheet结构无效({sheet_name}): {exc}") from exc

        date_styles = self._date_style_indexes()
        result: dict[str, OOXMLCellMetadata] = {}
        for cell in root.findall(f"{{{_MAIN_NS}}}sheetData/{{{_MAIN_NS}}}row/{{{_MAIN_NS}}}c"):
            reference = cell.attrib.get("r", "")
            match = re.fullmatch(r"([A-Z]+)[1-9][0-9]*", reference)
            if not match:
                continue
            if columns is not None and match.group(1) not in columns:
                continue
            raw_style = cell.attrib.get("s", "")
            style_index = int(raw_style) if raw_style.isdigit() else None
            raw_value = cell.find(_tag(_MAIN_NS, "v"))
            cell_type = cell.attrib.get("t", "")
            result[reference] = OOXMLCellMetadata(
                cell_type=cell_type,
                style_index=style_index,
                has_formula=cell.find(_tag(_MAIN_NS, "f")) is not None,
                raw_value=(raw_value.text or "") if raw_value is not None else "",
                is_date=(cell_type == "d" or
                         (style_index is not None and style_index in date_styles)),
            )
        return result

    def rows(self, sheet_name: str) -> list[list[Any]]:
        target = self._sheets.get(sheet_name)
        if not target:
            raise OOXMLReadError(f"工作簿中不存在sheet: {sheet_name}")
        try:
            root = ElementTree.fromstring(self.archive.read(target))
        except (KeyError, ElementTree.ParseError) as exc:
            raise OOXMLReadError(f"sheet结构无效({sheet_name}): {exc}") from exc
        merge_cells = root.find(_tag(_MAIN_NS, "mergeCells"))
        self._merged_ranges[sheet_name] = (
            tuple(node.attrib.get("ref", "")
                  for node in merge_cells.findall(_tag(_MAIN_NS, "mergeCell")))
            if merge_cells is not None else ()
        )
        rows: dict[int, dict[int, Any]] = {}
        max_row = 0
        max_col = 0
        for row_node in root.findall(f"{{{_MAIN_NS}}}sheetData/{{{_MAIN_NS}}}row"):
            row_number = int(row_node.attrib.get("r", "0"))
            if row_number <= 0:
                continue
            row_values: dict[int, Any] = {}
            for cell in row_node.findall(_tag(_MAIN_NS, "c")):
                reference = cell.attrib.get("r", "")
                if not reference:
                    continue
                col_index = _column_index(reference)
                cell_type = cell.attrib.get("t", "")
                value_node = cell.find(_tag(_MAIN_NS, "v"))
                if cell_type == "inlineStr":
                    value: Any = _inline_text(cell.find(_tag(_MAIN_NS, "is"))) if cell.find(_tag(_MAIN_NS, "is")) is not None else ""
                elif cell_type == "s":
                    raw = value_node.text if value_node is not None and value_node.text else ""
                    try:
                        value = self._shared_strings[int(raw)]
                    except (ValueError, IndexError):
                        value = raw
                elif cell_type in {"str", "e"}:
                    value = value_node.text if value_node is not None and value_node.text else ""
                else:
                    value = _parse_number(value_node.text if value_node is not None and value_node.text else "")
                row_values[col_index] = value
                max_col = max(max_col, col_index)
            rows[row_number - 1] = row_values
            max_row = max(max_row, row_number - 1)
        output: list[list[Any]] = []
        for row_index in range(max_row + 1):
            row = rows.get(row_index, {})
            output.append([row.get(col_index, "") for col_index in range(max_col + 1)])
        return output
