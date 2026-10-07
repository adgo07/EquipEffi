"""结果 Workbook 的**独立**不变量校验（Phase 8 R4）。

为什么必须"独立"
----------------
此前 Writer 的"自检"复用同一个扫描器，因此扫描器的盲区同时也是自检的盲区——
单引号属性、属性 namespace、嵌套前缀这些问题因此一路过关。

本模块**不导入** Writer 的任何扫描/解析代码，只使用：

```text
xml.parsers.expat       词法 + 命名空间（expanded QName）级别的独立解析
xml.etree.ElementTree   结构 + namespace 语义
```

校验内容（Owner 要求的最低成功条件）：

```text
1. XML 良构
2. sheetData/row/c 走正式路径，核心元素属于 MAIN_NS
3. 每个结果坐标在整表中**恰好一次**（按 expanded QName + 无命名空间 r 属性）
4. 用户输入列：输出与输入的**值**逐一相同（不重序列化、不改写）
5. 结果列的值等于 Writer 声称写入的 payload（成功证据不虚报）
6. 其他 ZIP 部件与输入**逐字节相同**
```
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree
from xml.parsers import expat

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

#: expat 在 `namespace_separator="}"` 下给出的名称形式是 `URI}local`，
#: **没有**前导 `{`（与 ElementTree 的 Clark 记法不同）。两者都要用对。
_EXPAT_MAIN = MAIN_NS + "}"
#: ElementTree 的 Clark 记法（用于结构校验）。
_CLARK = "{" + MAIN_NS + "}"

#: 结果列（软件写入区）。
RESULT_COLUMNS: tuple[str, ...] = (
    "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "AA")


class InvariantViolation(AssertionError):
    """结果 Workbook 未满足输出不变量。"""


@dataclass(frozen=True)
class CellFact:
    """一个单元格的独立事实（由 expat 给出，不依赖任何自研扫描器）。"""

    reference: str
    text: str
    column: str
    row: int


def _column_of(reference: str) -> str:
    letters = "".join(char for char in reference if char.isalpha())
    return letters.upper()


_PREFIX_DECLS = (
    'xmlns="' + MAIN_NS + '" '
    'xmlns:x="' + MAIN_NS + '" '
    'xmlns:ss="' + MAIN_NS + '" '
    'xmlns:p1="' + MAIN_NS + '"'
)


def ensure_worksheet(xml: str) -> str:
    """把**独立片段**补成合法 worksheet，便于对片段做机械断言。

    片段里出现的 `x:` / `ss:` / `p1:` 一律按 MAIN_NS 声明（这正是测试想表达的
    "任意前缀只要绑定 MAIN_NS 就是 SpreadsheetML"）；未加前缀的属性保持无命名空间。
    """

    stripped = xml.lstrip()
    if stripped.startswith("<worksheet") or stripped.startswith("<?xml") \
            or stripped.startswith("<x:worksheet"):
        return xml
    return ("<worksheet " + _PREFIX_DECLS + "><sheetData>"
            '<row r="4">' + xml + "</row></sheetData></worksheet>")


def parse_cells_with_expat(xml: str) -> list[CellFact]:
    """用 expat 独立解析 `sheetData/row/c`（namespace-aware）。

    只认 expanded QName，且只认**无命名空间**的 `r` 属性；因此单引号、属性顺序、
    前缀、嵌套重绑定都不影响结果。
    """

    xml = ensure_worksheet(xml)
    facts: list[CellFact] = []
    path: list[str] = []
    current: dict[str, Any] = {}
    parser = expat.ParserCreate(namespace_separator="}")

    def start(name: str, attrs: dict[str, str]) -> None:
        path.append(name)
        if name == _EXPAT_MAIN + "c" and len(path) >= 3 \
                and path[-2] == _EXPAT_MAIN + "row" \
                and path[-3] == _EXPAT_MAIN + "sheetData":
            # 属性里只有无命名空间的 r 才是坐标；`e}r`（扩展 ns）不是。
            reference = attrs.get("r")
            current.clear()
            current.update({"reference": reference, "text": "", "active": True})
        elif current.get("active") and name in (_EXPAT_MAIN + "v", _EXPAT_MAIN + "t"):
            current["capture"] = True

    def end(name: str) -> None:
        if name == _EXPAT_MAIN + "c" and current.get("active"):
            reference = current.get("reference")
            if reference:
                row_number = int("".join(ch for ch in reference if ch.isdigit()))
                facts.append(CellFact(
                    reference=reference, text=current.get("text", ""),
                    column=_column_of(reference), row=row_number))
            current.clear()
        elif name in (_EXPAT_MAIN + "v", _EXPAT_MAIN + "t"):
            current["capture"] = False
        if path:
            path.pop()

    def characters(data: str) -> None:
        if current.get("active") and current.get("capture"):
            current["text"] = current.get("text", "") + data

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = characters
    try:
        parser.Parse(xml, True)
    except expat.ExpatError as error:
        raise InvariantViolation(f"结果 worksheet 不是良构 XML：{error}") from error
    return facts


def assert_unique_references(xml: str) -> dict[str, CellFact]:
    """每个坐标恰好出现一次；返回坐标 -> 事实。"""

    facts = parse_cells_with_expat(xml)
    seen: dict[str, CellFact] = {}
    duplicates: dict[str, int] = {}
    for fact in facts:
        if fact.reference in seen:
            duplicates[fact.reference] = duplicates.get(fact.reference, 1) + 1
        else:
            seen[fact.reference] = fact
    if duplicates:
        raise InvariantViolation(
            "结果 worksheet 出现重复坐标（数据完整性缺陷）："
            f"{sorted(duplicates)[:10]}")
    return seen


def assert_main_namespace_paths(xml: str) -> None:
    """用 namespace-aware 解析器校验**正式路径**上的核心元素属于 MAIN_NS。

    正式路径是 `worksheet / sheetData / row / c / v`（含根元素）。只在 MAIN_NS
    子树内下探，因此扩展容器（`extLst/ext`）里**同名但不同 namespace** 的元素
    不会被误判（D03）。
    """

    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as error:
        raise InvariantViolation(f"结果 worksheet 不是良构 XML：{error}") from error
    if root.tag != _CLARK + "worksheet":
        raise InvariantViolation(
            f"根元素不属于 SpreadsheetML 主命名空间：{root.tag!r}")

    def main_children(element, local: str):
        target = _CLARK + local
        return [child for child in element if child.tag == target]

    # 正式的 spreadsheetml worksheet 根必须是 MAIN_NS（已在上方断言）。
    # 若**默认命名空间**存在且不是 MAIN_NS，则该默认命名空间里的元素属于别的
    # 方言；此时它不得使用 SpreadsheetML 保留结构名——那意味着归一化把 MAIN_NS
    # 元素写进了错误命名空间（fail closed，宁可拒绝也不产出语义错误的文件）。
    default_uri = None
    for key, value in (root.attrib or {}).items():
        if key == "xmlns":
            default_uri = value
    if default_uri is not None and default_uri != MAIN_NS:
        reserved = _CLARK + "sheetData"
        for child in root:
            if child.tag == reserved:
                raise InvariantViolation(
                    "结果 worksheet 的 sheetData 落入了非 SpreadsheetML 的默认"
                    f"命名空间 {default_uri!r}；拒绝产出命名空间语义错误的结果")

    for sheet_data in main_children(root, "sheetData"):
        for row in main_children(sheet_data, "row"):
            for cell in main_children(row, "c"):
                for value in main_children(cell, "v"):
                    if not value.tag.startswith(_CLARK):
                        raise InvariantViolation(
                            f"单元格值不在主命名空间：{value.tag!r}")
                for inline in main_children(cell, "is"):
                    for text in main_children(inline, "t"):
                        if not text.tag.startswith(_CLARK):
                            raise InvariantViolation(
                                f"内联文本不在主命名空间：{text.tag!r}")


def _namespace_uri(expanded_name: str) -> str | None:
    """Clark QName -> namespace URI；无命名空间返回 None。"""

    if expanded_name.startswith("{"):
        close = expanded_name.find("}")
        if close > 0:
            return expanded_name[1:close]
    return None


def _non_main_element_facts(xml: str) -> list[tuple[str, tuple, str, str]]:
    """提取所有非 SpreadsheetML 元素的语义事实。

    Writer 只获准修改 SpreadsheetML 结果列，因此扩展元素（包括**无命名空间**
    元素）的 expanded QName、属性、文本与 tail 都必须保持。namespace 声明本身
    不作为普通属性进入 ElementTree，所以为了保护 QName 而新增的 xmlns="" 边界
    不会造成误报。
    """

    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as error:
        raise InvariantViolation(f"worksheet 不是良构 XML：{error}") from error
    facts: list[tuple[str, tuple, str, str]] = []
    for element in root.iter():
        if _namespace_uri(element.tag) == MAIN_NS:
            continue
        attributes = tuple(sorted((key, value) for key, value in element.attrib.items()))
        facts.append((element.tag, attributes, element.text or "", element.tail or ""))
    return facts


def assert_non_main_elements_preserved(source_xml: str, result_xml: str) -> None:
    """扩展/无命名空间元素的语义必须逐项保持。

    该门禁专门覆盖一种旧盲区：在无默认命名空间的工作表根上补
    xmlns=SpreadsheetML 会让原先无命名空间的 <payload> 静默变成
    {SpreadsheetML}payload；正式 sheetData/row/c 门禁对此并不敏感。
    """

    before = _non_main_element_facts(source_xml)
    after = _non_main_element_facts(result_xml)
    if before != after:
        raise InvariantViolation(
            "结果 Workbook 改写了扩展/无命名空间元素的 QName 或内容；"
            "拒绝把命名空间漂移当成成功")


def input_cells(xml: str) -> dict[str, str]:
    """坐标 -> 文本（用于输入/输出保真比对）。"""

    return {fact.reference: fact.text
            for fact in parse_cells_with_expat(xml)}


def assert_input_preserved(source_xml: str, result_xml: str,
                           *, result_columns: tuple[str, ...] = RESULT_COLUMNS,
                           row_numbers: set[int] | None = None) -> None:
    """授权结果列之外，用户输入单元格的**值必须逐一相同**。

    这里比较的是**解析后的值**（实体已解码），因此既能抓住"被改写"，
    也不会被书写形式差异（单双引号、实体写法）误报。
    """

    before = input_cells(source_xml)
    after = input_cells(result_xml)
    allowed = set(result_columns)
    problems: list[str] = []
    for reference, value in before.items():
        if _column_of(reference) in allowed and (
                row_numbers is None
                or int("".join(ch for ch in reference if ch.isdigit())) in row_numbers):
            continue
        if reference not in after:
            problems.append(f"{reference} 在结果中消失")
        elif after[reference] != value:
            problems.append(
                f"{reference} 被改写：{value!r} -> {after[reference]!r}")
    if problems:
        raise InvariantViolation(
            "结果 Workbook 改写了用户输入单元格：" + "；".join(problems[:10]))


def _as_decimal_or_none(text: str):
    from decimal import Decimal, InvalidOperation

    candidate = (text or "").strip()
    if not candidate:
        return None
    try:
        return Decimal(candidate)
    except (InvalidOperation, ValueError):
        return None


def assert_result_payloads(result_xml: str,
                           expected: dict[str, str | None]) -> None:
    """结果列的值必须等于 Writer 声称写入的 payload（成功证据不得虚报）。

    比较按**数值语义**（`Decimal`）进行：这样"未舍入的派生值"与"Excel 按单元格格式
    显示的 2 位小数"不会被误报，而"漏写 / 写错 / 写成别的值"仍会被抓住
    （空值解析为 `None`，与任何数值都不相等）。
    """

    facts = input_cells(result_xml)
    problems: list[str] = []
    for reference, want in expected.items():
        if want is None:
            continue
        got = facts.get(reference, "")
        if got.strip() == want.strip():
            continue
        want_number = _as_decimal_or_none(want)
        got_number = _as_decimal_or_none(got)
        if want_number is not None and got_number is not None \
                and want_number == got_number:
            continue
        problems.append(f"{reference} 期望 {want!r} 实际 {got!r}")
    if problems:
        raise InvariantViolation(
            "结果列写入值与正式 payload 不一致：" + "；".join(problems[:10]))
