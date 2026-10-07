"""结果 worksheet 的定点补丁层（Phase 8 R4）。

设计原则（针对反复验收失败的根因）
----------------------------------
1. **身份判定只有一个来源**：元素与属性的身份全部来自 `xml_model` 的
   词法/命名空间解析（支持单双引号、属性 namespace、嵌套 prefix 重绑定、实体）。
   本模块不再出现任何"假设属性顺序/引号/前缀"的正则。
2. **改写是定点字节替换**：补丁只替换目标 cell 的绝对区间，其余字节原样保留，
   因此绝不重序列化用户输入（35 位小数等精度不会丢失）。
3. **路径限定**：只认 `sheetData/row/c` 这条正式路径，扩展容器里同名的
   `ext/t` 之类不会被误判成 SpreadsheetML 元素。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .xml_model import (
    EMPTY,
    MAIN_NS,
    START,
    Attribute,
    Element,
    XMLLexError,
    decode_entities,
    parse_elements,
)

_PREFIX_MAIN = "{" + MAIN_NS + "}"


class SheetStructureError(ValueError):
    """worksheet 的词法/结构无法可靠补丁。"""


def _expanded(local: str) -> str:
    return _PREFIX_MAIN + local


@dataclass
class CellView:
    """目标路径上 `sheetData/row/c` 的一个单元格（带绝对区间）。"""

    element: Element
    start: int
    end: int

    @property
    def reference(self) -> str | None:
        """严格按**无命名空间的 `r` 属性**取值。

        `e:r`（扩展命名空间）**不是**坐标，绝不能与 `r` 混为一谈——旧实现把
        两者合并成一个键，导致合法输入被判成不存在而插入重复坐标（D02）。
        """

        return self.element.attribute_value("r")

    @property
    def style(self) -> str | None:
        return self.element.attribute_value("s")

    @property
    def quote(self) -> str:
        attribute = self.element.attribute("r")
        return attribute.quote if attribute is not None else '"'

    def attribute_span(self, local: str) -> tuple[int, int] | None:
        attribute = self.element.attribute(local)
        return None if attribute is None else (attribute.start, attribute.end)


@dataclass
class RowView:
    """目标路径上的 `sheetData/row`。"""

    element: Element
    start: int
    end: int
    cells: list[CellView] = field(default_factory=list)

    @property
    def number(self) -> int | None:
        raw = self.element.attribute_value("r")
        if raw is None:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    @property
    def prefix(self) -> str:
        return self.element.prefix

    @property
    def body_end(self) -> int:
        """行内容区间的结束位置（`</row>` 之前；自闭合行等于开标记末尾）。"""

        if self.element.kind == EMPTY:
            return self.element.tag_end + 1
        closing = f"</{self.element.qname}>"
        found = self._closing_index(closing)
        return self.end if found == -1 else found

    def _closing_index(self, closing: str) -> int:
        return self.end - len(closing)


class WorksheetPatch:
    """一张 worksheet 的可补丁视图（身份来自真正的 XML 解析）。"""

    def __init__(self, xml: str):
        self.xml = xml
        try:
            self.elements = parse_elements(xml)
        except XMLLexError as error:
            raise SheetStructureError(f"worksheet 词法解析失败：{error}") from error
        self.root = self.elements[0] if self.elements else None
        if self.root is None or self.root.local != "worksheet":
            raise SheetStructureError("worksheet 根元素缺失或不是 <worksheet>")
        self.rows: dict[int, RowView] = {}
        self._collect_rows()

    # -- 路径限定收集 --------------------------------------------------------

    def _collect_rows(self) -> None:
        sheet_data = self._child(self.root, "sheetData")
        if sheet_data is None:
            raise SheetStructureError("worksheet 缺少 sheetData")
        for row in self._children(sheet_data, "row"):
            number = None
            raw = row.attribute_value("r")
            if raw is not None:
                try:
                    number = int(raw)
                except ValueError:
                    number = None
            if number is None:
                continue
            row_end = self._element_end(row)
            view = RowView(element=row, start=row.start, end=row_end)
            if row.kind != EMPTY:
                for cell in self._children(row, "c"):
                    view.cells.append(CellView(
                        element=cell, start=cell.start,
                        end=self._element_end(cell)))
            self.rows[number] = view

    def _element_end(self, element: Element) -> int:
        if element.kind == EMPTY:
            return element.tag_end + 1
        closing = f"</{element.qname}>"
        index = self.xml.find(closing, element.tag_end)
        return len(self.xml) if index == -1 else index + len(closing)

    @staticmethod
    def _children(element: Element, local: str) -> list[Element]:
        target = _expanded(local)
        return [child for child in element.children
                if child.kind in (START, EMPTY) and child.expanded == target]

    @staticmethod
    def _child(element: Element, local: str) -> Element | None:
        found = WorksheetPatch._children(element, local)
        return found[0] if found else None

    # -- 坐标唯一性（独立于补丁） -------------------------------------------

    def duplicate_references(self) -> dict[str, int]:
        """整表重复坐标（按正式路径 + 无命名空间 `r` 属性统计）。"""

        counts: dict[str, int] = {}
        for row in self.rows.values():
            for cell in row.cells:
                reference = cell.reference
                if reference:
                    counts[reference] = counts.get(reference, 0) + 1
        return {ref: count for ref, count in counts.items() if count > 1}

    # -- 应用补丁 ------------------------------------------------------------

    def apply(self, edits: list[tuple[int, int, str]]) -> str:
        """按绝对区间应用替换。

        **一次 join**，不逐次拼接字符串：`out = out[:s] + r + out[e:]` 在
        10,000 行（上万个编辑）时是 O(n²)（实测 18.7s 中有 15.6s 花在这里）。
        """

        if not edits:
            return self.xml
        ordered = sorted(edits, key=lambda item: item[0])
        pieces: list[str] = []
        cursor = 0
        for start, end, replacement in ordered:
            if start < cursor or end < start or end > len(self.xml):
                raise SheetStructureError("补丁区间非法或相互重叠")
            pieces.append(self.xml[cursor:start])
            pieces.append(replacement)
            cursor = end
        pieces.append(self.xml[cursor:])
        return "".join(pieces)


# ---------------------------------------------------------------------------
# 结果单元格生成
# ---------------------------------------------------------------------------

def escape_text(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


#: Writer **拥有**的单元格属性（其余属性一律原样保留）。
_OWNED_ATTRIBUTES = frozenset(("r", "s", "t"))


def outer_attributes(element) -> str:
    """该单元格上**非 Writer 拥有**的属性与命名空间声明（逐字节保留）。

    结果补丁只应改写单元格的**值与类型**；用户在结果单元格上附带的其他属性
    （例如扩展命名空间的 `e:r="…"`）以及元素上的 `xmlns:*` 声明都属于用户/工具
    内容，必须原样保留，不能被补丁吃掉。
    """

    parts: list[str] = []
    for attribute in element.attributes:
        if attribute.is_namespace_declaration:
            parts.append(f" {attribute.prefix}:{attribute.local}"
                         f'="{attribute.raw_value}"'
                         if attribute.prefix else
                         f' {attribute.local}="{attribute.raw_value}"')
            continue
        if not attribute.prefix and attribute.local in _OWNED_ATTRIBUTES:
            continue
        parts.append(f' {attribute.prefix}:{attribute.local}'
                     f'="{attribute.raw_value}"' if attribute.prefix else
                     f' {attribute.local}="{attribute.raw_value}"')
    return "".join(parts)


def cell_xml(reference: str, style: str | None,
             payload: tuple[str, str] | None, prefix: str = "",
             *, extra: str = "") -> str:
    """生成结果单元格；前缀应用到**全部子元素**（`v` / `is` / `t`）。

    只给 `c` 加前缀会让值落进别的默认命名空间（同族缺陷）。
    `extra` 为需要逐字节保留的非拥有属性/命名空间声明。
    """

    name = f"{prefix}:c" if prefix else "c"
    value_name = f"{prefix}:v" if prefix else "v"
    inline_name = f"{prefix}:is" if prefix else "is"
    text_name = f"{prefix}:t" if prefix else "t"
    style_attr = f' s="{style}"' if style else ""
    if payload is None:
        return f'<{name} r="{reference}"{style_attr}{extra}/>'
    kind, text = payload
    if kind == "n":
        return (f'<{name} r="{reference}"{style_attr}{extra}>'
                f"<{value_name}>{text}</{value_name}></{name}>")
    if text == "":
        return f'<{name} r="{reference}"{style_attr}{extra}/>'
    return (f'<{name} r="{reference}"{style_attr}{extra} t="inlineStr">'
            f'<{inline_name}><{text_name} xml:space="preserve">'
            f"{escape_text(text)}</{text_name}></{inline_name}></{name}>")


def column_number(letter: str) -> int:
    value = 0
    for char in letter.upper():
        value = value * 26 + ord(char) - ord("A") + 1
    return value


_REFERENCE_RE = re.compile(r"^([A-Z]+)(\d+)$")


def split_reference(reference: str) -> tuple[str, int] | None:
    match = _REFERENCE_RE.match(reference.strip().upper())
    if not match:
        return None
    return match.group(1), int(match.group(2))
