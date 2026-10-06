"""Phase 8B/R1：离心泵批量评价**结果 Workbook** Writer（Excel-as-adapter）。

硬规则
------
- 从原始输入 Workbook 创建**新文件**，**绝不**覆盖原输入文件。
- 默认文件名：``原文件名_评价结果_YYYYMMDD_HHMMSS.xlsx``；目标已存在时**显式报错**。
- **结果 Workbook = 原始 Workbook 的副本 + 只写正式结果区域**（Owner Phase 8 R1 / B3）。

为什么必须做 XML 级补丁而不是 openpyxl 重写
-------------------------------------------
`openpyxl` 会把数值单元格读成 Python `float` 再序列化回去，用户输入精度因此被改写。
实测（输入 `100.12345678901234567890123456789012345`）：

```text
原文件  <c r="G4" s="226"><v>100.12345678901234567890123456789012345</v></c>
读入    float 100.12345678901235
存回    <c r="G4" s="226" t="n"><v>100.1234567890124</v></c>      <- 精度被改写
```

因此本 Writer 改为：**先逐字节复制原文件**（其他 17 个 Sheet、图片、验证、保护、
样式、共享字符串、以及全部用户输入 cell 的原始 XML 一律原样保留），
**再只对「离心泵」Sheet 的授权结果列**做定点 XML 补丁。

授权写入范围（复用 V6 既有结果列，不新增字段体系）
--------------------------------------------------
```text
N  比转速                      O/P/Q  C1 / C2 / C3
R  基准效率                    S  效率修正值
T  规定点效率                  U/V/W  1 / 2 / 3 级效率限值
X  能效等级 / 处理·评价状态     AA  自动备注 / 说明
```

- `U/V/W` **取自正式 `PumpAnalysisResult.thresholds`**（不重新计算、不从 Excel 旧公式恢复）。
  没有正式阈值的状态（`OUT_OF_STANDARD_SCOPE` / `INSUFFICIENT_DATA` / 不确定类别 等）
  **不写** `U/V/W`，绝不伪造。
- `N/O–Q/R/S/T` 取自正式 `calculation_trace.derived`。
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from ...application.ports.batch_workbook import BatchRowOutcome
from .pump_workbook_reader import PUMP_SHEET

#: 结果列（Excel 列字母 → 语义）。顺序即写回顺序。
RESULT_FIELDS: tuple[tuple[str, str], ...] = (
    ("N", "specific_speed"),
    ("O", "c1"),
    ("P", "c2"),
    ("Q", "c3"),
    ("R", "base_efficiency"),
    ("S", "correction"),
    ("T", "specified_efficiency"),
    ("U", "grade1"),
    ("V", "grade2"),
    ("W", "grade3"),
    ("X", "conclusion"),
    ("AA", "auto_note"),
)

#: 正式 `PumpAnalysisResult.thresholds` 的键 → 结果列（**唯一来源**）。
THRESHOLD_COLUMNS: tuple[tuple[str, str], ...] = (
    ("U", "1级能效效率限值（%）"),
    ("V", "2级能效效率限值（%）"),
    ("W", "3级能效效率限值（%）"),
)

#: 派生量名称 → 结果列（`calculation_trace.derived` 的键为中文名）。
_DERIVED_BY_COLUMN: dict[str, str] = {
    "N": "比转速 ns",
    "O": "C1",
    "P": "C2",
    "Q": "C3",
    "R": "基准效率（%）",
    "S": "效率修正值（%）",
    "T": "规定点效率（%）",
}

#: 按数值写入的结果列（其余按文本）。
_NUMERIC_COLUMNS: frozenset[str] = frozenset("NOPQRSTUVW")

#: 结果文件默认名中缀。
RESULT_FILENAME_INFIX = "_评价结果_"

_THRESHOLD_COLUMN_SET = frozenset(column for column, _name in THRESHOLD_COLUMNS)


def default_result_filename(source: Path, when: datetime | None = None) -> str:
    """``原文件名_评价结果_YYYYMMDD_HHMMSS.xlsx``（Owner 8B 默认命名）。"""

    source = Path(source)
    stamp = (when or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"{source.stem}{RESULT_FILENAME_INFIX}{stamp}.xlsx"


class ResultWorkbookExistsError(FileExistsError):
    """目标结果文件已存在；不得静默覆盖。"""


# ---------------------------------------------------------------------------
# 取值
# ---------------------------------------------------------------------------

def _as_number(value: Any) -> str | None:
    """转成 Excel 数值字面量；无法转换返回 None（由调用方决定回退为文本）。"""

    from decimal import Decimal, InvalidOperation

    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not number.is_finite():
        return None
    if number == number.to_integral_value():
        return str(number.to_integral_value())
    return format(number, "f")


def _derived_value(derived: dict[str, Any], column: str) -> Any:
    name = _DERIVED_BY_COLUMN.get(column)
    if not name:
        return None
    if name in derived:
        return derived[name]
    prefix = name.split("（")[0]
    for key, value in derived.items():
        if str(key).strip().startswith(prefix):
            return value
    return None


def _threshold_value(thresholds: dict[str, Any], column: str) -> Any:
    """从**正式 Result.thresholds**取等级限值；取不到返回 None（不伪造、不重算）。"""

    for target, name in THRESHOLD_COLUMNS:
        if target != column:
            continue
        if name in thresholds:
            return thresholds[name]
        # 键名措辞变化时按"级别 + 限值"语义容错匹配，仍不重新计算。
        level = name[0]
        for key, value in thresholds.items():
            text = str(key)
            if text.startswith(f"{level}级") and "限值" in text:
                return value
        return None
    return None


def _status_and_conclusion(outcome: BatchRowOutcome) -> str:
    """`X` 列内容：处理 / 评价状态 + 最终结论 + 能效等级。

    输入错误与执行失败**不属于**正式评价结论，必须一眼可辨。
    """

    if outcome.is_input_error:
        return f"输入错误（{outcome.conclusion}）"
    if outcome.is_execution_error:
        return f"执行失败（{outcome.conclusion}）"
    if outcome.grade and str(outcome.grade) not in str(outcome.conclusion):
        return f"{outcome.conclusion}（{outcome.grade}级）"
    return outcome.conclusion


def _auto_note(outcome: BatchRowOutcome) -> str:
    return "；".join(dict.fromkeys(outcome.messages)) if outcome.messages else ""


def cell_payloads(outcome: BatchRowOutcome) -> dict[str, tuple[str, str] | None]:
    """算出一行要在结果列写入的内容：``column -> (kind, text) | None``。

    ``kind`` 为 ``"n"``（数值）/ ``"s"``（文本）；``None`` 表示**不写**该列
    （用于没有正式阈值的状态——绝不伪造）。
    """

    payloads: dict[str, tuple[str, str] | None] = {}
    for column, _name in RESULT_FIELDS:
        if column == "X":
            payloads[column] = ("s", _status_and_conclusion(outcome))
            continue
        if column == "AA":
            payloads[column] = ("s", _auto_note(outcome))
            continue
        raw = (_threshold_value(outcome.thresholds, column)
               if column in _THRESHOLD_COLUMN_SET
               else _derived_value(outcome.derived, column))
        if raw in (None, ""):
            payloads[column] = None
            continue
        if column in _NUMERIC_COLUMNS:
            literal = _as_number(raw)
            payloads[column] = (("n", literal) if literal is not None
                                else ("s", str(raw)))
        else:
            payloads[column] = ("s", str(raw))
    return payloads


# ---------------------------------------------------------------------------
# XML 级补丁
# ---------------------------------------------------------------------------

_SHEET_ELEMENT = re.compile(r"<sheet\b[^>]*>")
_NAME_ATTR = re.compile(r'name="([^"]*)"')
_ID_ATTR = re.compile(r'[A-Za-z0-9]+:id="([^"]*)"')
_REL_ELEMENT = re.compile(r"<Relationship\b[^>]*>")
_REL_ID_ATTR = re.compile(r'Id="([^"]*)"')
_REL_TARGET_ATTR = re.compile(r'Target="([^"]*)"')


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _cell_xml(reference: str, style: str | None,
              payload: tuple[str, str] | None) -> str:
    """无前缀（默认命名空间）单元格元素。"""

    return _cell_element_xml(reference, style, payload, "")


def _column_number(letter: str) -> int:
    value = 0
    for char in letter.upper():
        value = value * 26 + ord(char) - ord("A") + 1
    return value


#: 需要补丁的 sheet XML 中出现的**结果列**（提前算出，便于扫描时快速跳过无关格）。
_RESULT_COLUMN_SET = frozenset(column for column, _name in RESULT_FIELDS)

_ATTR_RE = re.compile(r'([A-Za-z_][\w.:-]*)\s*=\s*"([^"]*)"')


class ResultWorkbookWriteError(RuntimeError):
    """结果 Workbook 未能按契约写回。

    这是**硬失败**：宁可让批次整体失败并明确报错，也绝不静默漏写结果、
    或写出结构无效（重复坐标）的工作簿。Owner Phase 8 R1 复审 blocker 1/2。
    """


def _local_name(name: str) -> str:
    """取元素的**局部名**。

    同时支持两种 QName 写法：

    ```text
    x:row                     -> row      （原始 XML 里的前缀式限定名）
    {http://…/main}row        -> row      （namespace-aware 解析器给出的 Clark 记法）
    ```
    """

    if name.startswith("{"):
        closing = name.find("}")
        if closing != -1:
            name = name[closing + 1:]
    return name.rsplit(":", 1)[-1]


def _parse_attrs(text: str) -> dict[str, str]:
    """解析元素属性为字典。

    **属性顺序无关**，这正是复审 blocker 1/2 的根因：OOXML **不保证**属性顺序，
    因此任何形如 `<c r="U4" ...>` 的位置/顺序假设都是错的。
    """

    return {_local_name(key): value for key, value in _ATTR_RE.findall(text)}


def _skip_quoted(text: str, index: int) -> int:
    """从引号处跳到匹配的结束引号之后。"""

    quote = text[index]
    index += 1
    while index < len(text):
        char = text[index]
        if char == "&":
            semi = text.find(";", index)
            index = len(text) if semi == -1 else semi + 1
            continue
        if char == quote:
            return index + 1
        index += 1
    return index


def _find_tag_end(text: str, start: int) -> int:
    """找到标签的 `>`（正确跳过属性值里的引号与实体）。"""

    index = start
    while index < len(text):
        char = text[index]
        if char == '"':
            index = _skip_quoted(text, index)
            continue
        if char == ">":
            return index
        index += 1
    return -1


_XMLNS_RE = re.compile(r"xmlns:([A-Za-z_][\w.-]*)\s*=\s*\"([^\"]*)\"")
_XMLNS_DECL_RE = re.compile(
    r'\s+xmlns(?::([A-Za-z_][\w.-]*))?\s*=\s*"([^"]*)"')
_XMLNS_DEFAULT_RE = re.compile(r"xmlns\s*=")

#: SpreadsheetML 主命名空间（OOXML 工作表的正式命名空间）。
_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
#: 根元素上的**任意**默认命名空间声明（`xmlns="…"`，无前缀）。
_DEFAULT_XMLNS_ANY_RE = re.compile(r"\sxmlns\s*=\s*\"([^\"]*)\"")
#: 根元素上的 **SpreadsheetML** 默认命名空间声明。
_DEFAULT_XMLNS_RE = re.compile(
    r"\sxmlns\s*=\s*\"" + re.escape(_MAIN_NS) + r"\"")


def _root_element_tag(xml: str) -> str:
    """工作表根元素的开标记原文；找不到返回空串。"""

    start, end = _root_tag_bounds(xml)
    return "" if start == -1 else xml[start:end + 1]


def _default_namespace_uri(xml: str) -> str | None:
    """根元素**默认命名空间**的 URI。

    Owner Phase 8 R3 §一/§二：namespace 决策**必须**区分三种情况，不能只看
    "有没有 `xmlns=`"：

    ```text
    A. 没有默认 namespace            -> None
    B. 默认 namespace == MAIN_NS     -> _MAIN_NS
    C. 默认 namespace != MAIN_NS     -> 那个别的 URI
    ```

    只判断"存在任意 `xmlns=`"是本轮 blocker 的根因：它把情况 C 误当成情况 B，
    于是删掉了 MAIN_NS 前缀声明，让 SpreadsheetML 元素落进别的命名空间。
    """

    root_tag = _root_element_tag(xml)
    if not root_tag:
        return None
    match = _DEFAULT_XMLNS_ANY_RE.search(root_tag)
    return None if match is None else match.group(1).strip()


def _has_default_namespace(xml: str) -> bool:
    """根元素是否已声明**任意**默认命名空间。

    仅用于"不能再追加第二个 `xmlns` 属性"这类语法判断；
    **不得**再用它决定要不要删 MAIN_NS 前缀（见 `_default_namespace_uri`）。
    """

    return _default_namespace_uri(xml) is not None


def _root_tag_bounds(xml: str) -> tuple[int, int]:
    """工作表根元素开标记的 ``(起点, '>' 下标)``；找不到返回 ``(-1, -1)``。"""

    position = xml.find("<")
    while 0 <= position < len(xml) and xml[position:position + 2] in ("<?", "<!"):
        end = _find_tag_end(xml, position)
        if end == -1:
            return -1, -1
        position = xml.find("<", end + 1)
    if position == -1:
        return -1, -1
    end = _find_tag_end(xml, position)
    return (position, end) if end != -1 else (-1, -1)


def _main_namespace_prefixes(text: str) -> list[str]:
    """工作表根元素上**所有**绑定到 SpreadsheetML 主命名空间的前缀。

    同一张工作表可能混用多个前缀（`<x:c>` 与 `<ss:c>` 并存），因此这里返回
    全部命中项，而不是"第一个"。
    """

    start = text.find("<")
    while 0 <= start < len(text) and text[start:start + 2] in ("<?", "<!"):
        end = _find_tag_end(text, start)
        if end == -1:
            return []
        start = text.find("<", end + 1)
    if start == -1:
        return []
    end = _find_tag_end(text, start)
    if end == -1:
        return []
    root_tag = text[start:end]
    return [prefix for prefix, uri in _XMLNS_RE.findall(root_tag)
            if uri == _MAIN_NS]


def _strip_main_namespace_prefix(xml: str, prefix: str) -> str:
    """把绑定到主命名空间的前缀 ``prefix`` 写回**默认命名空间**形式。

    为什么必须做这一步：大量现有 OOXML 读取器（含本仓测试所用的 `openpyxl`）
    只按**字面**无前缀标签匹配 `c` / `v` / `row`，对 `<x:c><x:v>…</x:v></x:c>`
    会静默丢掉单元格**值**。输入工作簿使用前缀写法时，若结果工作簿原样保留
    前缀，用户用 Excel/其它工具打开就会"结果消失"，因此结果 Writer 在产出前
    把**主命名空间**的元素统一写成默认命名空间形式。

    只改两件事：

    ```text
    1. 元素**限定名上的前缀**   <x:c  ->  <c   /  </x:row>  ->  </row>
    2. 该前缀自己的声明          xmlns:x="…/main"  ->  xmlns="…/main"
    ```

    第 2 步是**必须**的：只声明了 `xmlns:x` 的工作表本来就没有默认命名空间，
    若只删声明不补默认绑定，元素就会落进"无命名空间"，文件对 OOXML 读取器
    整体失效（属性、属性顺序、文本、其它命名空间 `r:` / `mc:` / `x14ac:` 等
    全部逐字节保留）。若工作表**已经**有默认命名空间声明，则该前缀声明是
    多余的，直接删除——绝不能产生第二个 `xmlns` 属性（那是非法 XML）；
    若同名前缀**已经**绑定到别的命名空间（例如 `ss` 已被关系命名空间占用），
    则**保留**原声明不动，只改元素名。最终整张工作表由 `_assert_well_formed`
    机械复核为良构。
    """

    if not prefix:
        return xml
    declaration_re = re.compile(
        r"(?P<head>\s+xmlns):" + re.escape(prefix)
        + r"(?P<tail>\s*=\s*\")(?P<uri>[^\"<>]*)(?P<quote>\")")

    edits: list[tuple[int, int, str]] = []
    # 元素名位置由带 namespace 作用域的结构扫描给出。
    # 同一个字面前缀可在子树内合法重绑定；只有当前位置实际解析为 MAIN_NS
    # 的元素才允许去前缀。嵌套 xmlns:x="urn:extension" 下的 x:payload 必须保持。
    for position, _tag_end, qualified, namespace_uri in _iter_tags_with_namespace(xml):
        if _prefix_of(qualified) != prefix or namespace_uri != _MAIN_NS:
            continue
        name_start = position + 1
        if xml[name_start:name_start + 1] == "/":
            name_start += 1
        name_end = name_start + len(prefix)
        # 前缀后必须紧跟 `:` 才是"前缀 + 局部名"（`x` vs `xylophone` 的区分），
        # 删除范围包含这个 `:`——留下裸冒号会立刻变成非法 XML。
        if xml[name_end:name_end + 1] != ":":
            continue
        edits.append((name_start, name_end + 1, ""))
    # 关键判定（Owner Phase 8 R3 §二/§三）：只有**情况 A（无默认 namespace）**
    # 与**情况 B（默认 namespace == MAIN_NS）**才允许把 MAIN_NS 前缀归一为无前缀。
    # 情况 C（默认 namespace 是别的 URI）下，去掉前缀会让这些元素落进别的
    # namespace —— 必须保留 `xmlns:x="…/main"` 与所有 `x:` 元素前缀。
    default_uri = _default_namespace_uri(xml)
    if default_uri is not None and default_uri != _MAIN_NS:
        return xml

    declaration = declaration_re.search(xml)
    if declaration is not None:
        if declaration.group("uri") != _MAIN_NS:
            # 同名前缀属于**别的**命名空间（例如关系命名空间）：元素名归一后
            # 该声明可能仍被别处引用，因此保留声明，只把元素写成默认形式。
            pass
        elif _default_namespace_uri(xml) == _MAIN_NS:
            # 情况 B：已有 MAIN_NS 默认命名空间，该前缀声明是多余的，直接删除
            # （否则重复属性）。
            edits.append((declaration.start(), declaration.end(), ""))
        else:
            # 情况 A：把前缀声明改写成默认命名空间声明。
            edits.append((declaration.start(), declaration.end(),
                          f'{declaration.group("head")}'
                          f'{declaration.group("tail")}'
                          f'{declaration.group("uri")}'
                          f'{declaration.group("quote")}'))

    if not edits:
        return xml
    pieces: list[str] = []
    cursor = 0
    for start, end, replacement in sorted(edits):
        pieces.append(xml[cursor:start])
        pieces.append(replacement)
        cursor = end
    pieces.append(xml[cursor:])
    return "".join(pieces)



def _default_prefix_from_root(text: str) -> str:
    """工作表根元素的**默认元素前缀**（`<x:worksheet ...>` → `"x"`；无前缀 → `""`）。

    新插入的元素必须与该工作表既有的前缀风格一致：只声明了 `xmlns:prefix`
    的工作表里，无前缀元素**不属于** SpreadsheetML 命名空间，会是非法 OOXML。
    """

    start = text.find("<")
    while 0 <= start < len(text) and text[start:start + 2] in ("<?", "<!"):
        end = _find_tag_end(text, start)
        if end == -1:
            return ""
        start = text.find("<", end + 1)
    if start == -1:
        return ""
    end = _find_tag_end(text, start)
    if end == -1:
        return ""
    element = _element_name(text[start:end])
    return element.split(":", 1)[0] if ":" in element else ""


def _iter_tags(xml: str, start: int = 0, end: int | None = None):
    """逐个产出标记的 ``(标记起点, 标记终点, 元素名)``（**跳过**注释与处理指令）。

    这是取代 ``find("<c")`` / ``find("<row")`` 的基础：元素身份由**限定名**
    决定，绝不靠字符串前缀匹配。
    """

    if end is None:
        end = len(xml)
    index = start
    while index < end:
        position = xml.find("<", index)
        if position == -1 or position >= end:
            break
        if xml[position:position + 4] == "<!--":
            comment_end = xml.find("-->", position + 4)
            index = end if comment_end == -1 else comment_end + 3
            continue
        if xml[position:position + 9] == "<![CDATA[":
            cdata_end = xml.find("]]>", position + 9)
            index = end if cdata_end == -1 else cdata_end + 3
            continue
        if xml[position + 1:position + 2] in ("?", "!"):
            tag_end = _find_tag_end(xml, position)
            if tag_end == -1:
                break
            index = tag_end + 1
            continue
        tag_end = _find_tag_end(xml, position)
        if tag_end == -1:
            break
        yield position, tag_end, _element_name(xml[position:tag_end])
        index = tag_end + 1


def _iter_tags_with_namespace(xml: str):
    """逐标记返回其当前位置实际生效的元素命名空间 URI。

    与只看根元素 xmlns:x 不同，这里维护 XML namespace 的词法作用域：
    子元素可以合法地用 xmlns:x="urn:..." 重新绑定同一个前缀，离开该元素后
    又恢复父作用域。Writer 的前缀归一化只能改写当前位置实际解析为
    SpreadsheetML 主命名空间的元素，绝不能按前缀字面值全局替换。
    """

    scope: dict[str, str] = {}
    parents: list[dict[str, str]] = []
    for position, tag_end, qualified in _iter_tags(xml):
        closing = xml[position + 1:position + 2] == "/"
        prefix = qualified.split(":", 1)[0] if ":" in qualified else ""

        if closing:
            yield position, tag_end, qualified, scope.get(prefix)
            if parents:
                scope = parents.pop()
            continue

        parent_scope = scope
        element_scope = dict(scope)
        raw_tag = xml[position:tag_end + 1]
        for declared_prefix, uri in _XMLNS_DECL_RE.findall(raw_tag):
            element_scope[declared_prefix or ""] = uri
        scope = element_scope
        yield position, tag_end, qualified, scope.get(prefix)

        if xml[tag_end - 1] == "/":
            scope = parent_scope
        else:
            parents.append(parent_scope)


def _element_name(raw_tag: str) -> str:
    """从 `<x:c r="U4"/>` / `</c>` 取**限定名**（`x:c` / `c`）。"""

    text = raw_tag[1:]
    if text[:1] == "/":
        text = text[1:]
    return text.split(None, 1)[0].rstrip("/") if text.split(None, 1) else ""


def _close_tag(qualified: str) -> str:
    """该元素对应的**精确**结束标记：`x:c` → `</x:c>`（不是硬编码的 `</c>`）。"""

    return f"</{qualified}>"


def _element_extent(xml: str, position: int, tag_end: int, limit: int) -> int:
    """返回以 ``position`` 为起点、``tag_end`` 为开标记 `>` 的元素**结束位置**。

    单元格元素可以**含子元素**（`<c><f>..</f><v>..</v></c>`、
    `<c t="inlineStr"><is><t>..</t></is></c>`），因此不能简单地找第一个 `</c>`：
    那会停在子元素之后、把外层单元格的区间截断。这里用**嵌套深度**配对开/闭标记，
    并且只在深度归零时接受结束标记。
    """

    if xml[tag_end - 1] == "/":
        return tag_end + 1
    depth = 1
    index = tag_end + 1
    while index < limit:
        marker = xml.find("<", index)
        if marker == -1 or marker >= limit:
            break
        marker_end = _find_tag_end(xml, marker)
        if marker_end == -1:
            break
        if xml[marker:marker + 4] == "<!--":
            comment_end = xml.find("-->", marker + 4)
            index = limit if comment_end == -1 else comment_end + 3
            continue
        if xml[marker:marker + 9] == "<![CDATA[":
            cdata_end = xml.find("]]>", marker + 9)
            index = limit if cdata_end == -1 else cdata_end + 3
            continue
        if xml[marker + 1:marker + 2] == "!":
            index = marker_end + 1
            continue
        closing = xml[marker + 1:marker + 2] == "/"
        if closing:
            depth -= 1
            if depth == 0:
                return marker_end + 1
        elif xml[marker_end - 1] != "/":
            depth += 1
        index = marker_end + 1
    return -1


@dataclass(frozen=True)
class _CellSpan:
    """一个单元格元素在工作表/行片段中的位置、限定名与属性。"""

    start: int
    end: int
    qualified: str
    attrs: dict[str, str]
    #: 该元素自带的 `xmlns` / `xmlns:*` 声明原文（就地改写时必须原样保留）。
    namespaces: str = ""

    @property
    def reference(self) -> str:
        return self.attrs.get("r", "")

    @property
    def style(self) -> str | None:
        return self.attrs.get("s")

    @property
    def prefix(self) -> str:
        return _prefix_of(self.qualified)


def _prefix_of(qualified: str) -> str:
    """限定名 → 命名空间前缀（`x:c` → `x`；`c` → `""`）。"""

    return qualified.split(":", 1)[0] if ":" in qualified else ""


def _scan_cells(xml: str, start: int = 0, end: int | None = None) -> list[_CellSpan]:
    """扫描范围内的所有**单元格**元素——按 local-name，而非字符串前缀。

    命名空间前缀是**载体细节**，以下四者必须是**同一个** SpreadsheetML 单元格：

    ```text
    <c r="U4">      <x:c r="U4">      <ss:c r="U4">      <p1:c r="U4">
    ```

    因此这里：解析开标记的限定名 → 取 local-name → **仅当 local-name == "c"**
    才当成单元格；结束标记必须匹配开标记的**实际限定名**（`</x:c>`）。
    属性顺序无关；自闭合与带内容一视同仁；`<cols>` / `<col>` / `<customFilter>`
    之类 local-name 不是 `c` 的元素一律不会误判。
    """

    cells: list[_CellSpan] = []
    limit = len(xml) if end is None else end
    for position, tag_end, qualified in _iter_tags(xml, start, end):
        if xml[position + 1:position + 2] == "/":
            continue    # 结束标记不是元素起点
        if _local_name(qualified) != "c":
            continue
        stop = _element_extent(xml, position, tag_end, limit)
        if stop == -1:
            raise ResultWorkbookWriteError(
                f"工作表 XML 结构无效：<{qualified}> 缺少匹配的结束标记 "
                f"</{qualified}>")
        cells.append(_CellSpan(position, stop, qualified,
                               _parse_attrs(xml[position:tag_end]),
                               _namespace_declarations(xml, position, tag_end)))
    return cells


def _scan_rows(xml: str) -> list[tuple[int, int, int]]:
    """扫描 sheetData 中的所有**行**元素：返回 ``(start, end, row_number)``。

    与 `_scan_cells` 同一策略：local-name == "row"，结束标记按该元素实际的
    限定名匹配（`</x:row>` 对 `<x:row>`），**不假设前缀，也不假设属性顺序**。
    """

    rows: list[tuple[int, int, int]] = []
    limit = len(xml)
    for position, tag_end, qualified in _iter_tags(xml):
        if xml[position + 1:position + 2] == "/":
            continue    # 结束标记不是元素起点
        if _local_name(qualified) != "row":
            continue
        attrs = _parse_attrs(xml[position:tag_end])
        row_number = attrs.get("r")
        if row_number is None:
            continue
        stop = _element_extent(xml, position, tag_end, limit)
        if stop == -1:
            raise ResultWorkbookWriteError(
                f"工作表 XML 结构无效：<{qualified}> 缺少匹配的结束标记 "
                f"</{qualified}>")
        try:
            rows.append((position, stop, int(row_number)))
        except ValueError:
            continue
    return rows


def row_xml_is_self_closing(xml: str, tag_end: int) -> bool:
    return xml[tag_end - 1] == "/"


def _reference_counts(cells) -> dict[str, int]:
    counts: dict[str, int] = {}
    for cell in cells:
        if cell.reference:
            counts[cell.reference] = counts.get(cell.reference, 0) + 1
    return counts


def _assert_unique_references(xml: str) -> None:
    """**结构后置条件**：整张工作表的单元格坐标必须唯一。

    在把结果写进结果 Workbook **之前**执行；一旦发现任何非空坐标出现多于一次，
    就硬失败（`ResultWorkbookWriteError`）：不产出"成功"的结果文件、不保存
    "成功"的 `batch_record`。这样即使将来扫描/插入逻辑再次退化，重复坐标的
    工作簿也**不可能**以成功形式交付给用户。
    """

    counts = _reference_counts(_scan_cells(xml))
    duplicates = sorted(ref for ref, count in counts.items() if count > 1)
    if duplicates:
        preview = "、".join(duplicates[:10])
        more = "" if len(duplicates) <= 10 else f" 等 {len(duplicates)} 个"
        raise ResultWorkbookWriteError(
            f"结果写回结构校验失败：「{PUMP_SHEET}」Sheet 出现重复单元格坐标 "
            f"{preview}{more}；拒绝产出结构无效的结果工作簿")


def _assert_well_formed(xml: str) -> None:
    """后置条件：打补丁后的整张工作表必须仍是**良构 XML**。

    补丁是原生字符串操作，因此这里用 XML 解析器独立复核一次：一旦结构被破坏
    （标签不配对、前缀未声明等），宁可硬失败，也不写出打不开的工作簿。
    """

    from xml.etree import ElementTree

    try:
        ElementTree.fromstring(xml)
    except ElementTree.ParseError as error:
        raise ResultWorkbookWriteError(
            f"结果写回结构校验失败：「{PUMP_SHEET}」Sheet 补丁后不是良构 XML"
            f"（{error}）；拒绝产出无法打开的结果工作簿") from error


def _expanded_element_qnames(xml: str) -> list[str]:
    """返回文档序中的 expanded element QName（{uri}local）。"""

    from xml.etree import ElementTree

    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as error:
        raise ResultWorkbookWriteError(
            f"结果写回命名空间校验失败：「{PUMP_SHEET}」Sheet 不是良构 XML"
            f"（{error}）；拒绝执行命名空间归一化") from error
    return [element.tag for element in root.iter()]


def _assert_namespace_normalisation_preserves_qnames(before: str, after: str) -> None:
    """前缀归一化只能改变词法前缀，不得改变任何元素的 expanded QName。

    扩展 payload 不一定属于 SpreadsheetML，旧门禁无法发现
    {urn:extension}payload -> {SpreadsheetML}payload。这里直接比较归一化
    前后的 namespace-aware QName 序列；任何命名空间漂移都 fail closed。
    """

    before_names = _expanded_element_qnames(before)
    after_names = _expanded_element_qnames(after)
    if before_names == after_names:
        return

    mismatch = next(
        (index for index, pair in enumerate(zip(before_names, after_names))
         if pair[0] != pair[1]),
        min(len(before_names), len(after_names)),
    )
    before_name = before_names[mismatch] if mismatch < len(before_names) else "<missing>"
    after_name = after_names[mismatch] if mismatch < len(after_names) else "<missing>"
    raise ResultWorkbookWriteError(
        "结果写回命名空间校验失败：前缀归一化改变了元素的实际命名空间"
        f"（位置 {mismatch}: {before_name!r} -> {after_name!r}）；"
        "拒绝产出会静默改写扩展数据的结果工作簿")


def _insert_default_namespace(xml: str) -> str:
    """确保根元素声明 ``xmlns="…/main"``（前缀归一后元素必须仍属于主命名空间）。

    只在**情况 A（没有默认 namespace）**下追加。

    情况 C（默认 namespace 是**别的** URI）**绝不**追加：那会产生第二个 `xmlns`
    属性（非法 XML），或把 MAIN_NS 绑到别的 URI 上——两者都会破坏语义。
    Owner Phase 8 R3 §二/§三。
    """

    if _default_namespace_uri(xml) is not None:
        # 情况 B（已是 MAIN_NS）无需动作；情况 C（别的 URI）绝不能追加。
        return xml
    start, end = _root_tag_bounds(xml)
    if start == -1:
        return xml
    root_tag = xml[start:end]
    if _XMLNS_RE.search(root_tag) is None:
        # 根元素没有任何前缀声明：无法安全补默认命名空间（用错了会改变语义）。
        return xml
    return xml[:start + 1] + f'xmlns="{_MAIN_NS}" ' + xml[start + 1:]


def _normalise_main_namespace(xml: str) -> str:
    """把工作表的主命名空间元素统一写成默认命名空间形式（可被普通读取器读）。"""

    for prefix in _main_namespace_prefixes(xml):
        xml = _strip_main_namespace_prefix(xml, prefix)
    return _insert_default_namespace(xml)


def _row_default_style(cells: list[_CellSpan]) -> str | None:
    """取该行第一个带样式的 cell 的样式号，供新增结果 cell 继承外观。"""

    for cell in cells:
        if cell.style:
            return cell.style
    return None


def _patch_row(row_xml: str, row_number: int,
               payloads: dict[str, tuple[str, str] | None]) -> str:
    """把结果列的 payload 写进这一行（**前缀无关**、顺序无关、不产生重复坐标）。

    目标坐标语义（Owner Phase 8 R2 §四）：

    ```text
    已有 0 个 -> 按既有逻辑插入 1 个
    已有 1 个 -> **就地更新**该单元格（带任何合法前缀都能识别）
    已有 >1 个 -> 输入本身已经歧义 -> fail closed（不猜哪个才是真的）
    ```
    """

    cells = _scan_cells(row_xml)
    fallback_style = _row_default_style(cells)
    counts = _reference_counts(cells)

    # 本行出现重复坐标：输入已歧义 -> 硬失败（不猜、不掩盖）。
    duplicated = sorted(ref for ref, count in counts.items() if count > 1)
    if duplicated:
        raise ResultWorkbookWriteError(
            f"输入工作表第 {row_number} 行存在重复单元格坐标"
            f"（{'、'.join(duplicated[:10])}），无法确定应更新哪一个；拒绝写回")

    by_reference = {cell.reference: cell for cell in cells if cell.reference}
    opening_end = _find_tag_end(row_xml, 0)
    if opening_end == -1:
        raise ResultWorkbookWriteError(
            f"结果写回失败：第 {row_number} 行的 XML 结构无效（标记未闭合）")
    row_element = _element_name(row_xml[:opening_end])
    prefix = _row_prefix(_parse_attrs(row_xml[:opening_end]), row_element)

    edits: list[tuple[int, int, str]] = []
    for column in sorted(payloads, key=_column_number):
        reference = f"{column}{row_number}"
        existing = by_reference.get(reference)
        if existing is not None:
            # 就地更新：保留原有样式与**原有命名空间前缀**，绝不新增第二个坐标。
            style = existing.style or fallback_style
            edits.append((existing.start, existing.end,
                          _cell_element_xml(
                              reference, style, payloads[column],
                              _prefix_of(existing.qualified),
                              existing.namespaces)))
    # 从后往前替换，保证前面的偏移仍然有效。
    for start, end, replacement in sorted(edits, key=lambda item: item[0],
                                          reverse=True):
        row_xml = row_xml[:start] + replacement + row_xml[end:]

    # 补齐该行**不存在**的结果 cell（按列序插入到正确位置）。
    missing = [column for column in sorted(payloads, key=_column_number)
               if f"{column}{row_number}" not in by_reference]
    if missing:
        row_xml = _insert_missing_cells(row_xml, row_number, missing,
                                        payloads, fallback_style, prefix)

    # 自校验：目标坐标必须恰好各出现一次。
    final_counts = _reference_counts(_scan_cells(row_xml))
    for column in payloads:
        reference = f"{column}{row_number}"
        if final_counts.get(reference, 0) != 1:
            raise ResultWorkbookWriteError(
                f"结果写回自校验失败：{reference} 出现 "
                f"{final_counts.get(reference, 0)} 次（必须恰好 1 次）")
    return row_xml


def _namespace_declarations(xml: str, start: int, tag_end: int) -> str:
    """取该元素开标记里的 `xmlns` / `xmlns:*` 声明（逐字节保留）。

    就地改写单元格时**必须**连同它自带的命名空间声明一起保留：原声明是载体
    事实，重新合成可能丢掉它。
    """

    declarations: list[str] = []
    for match in re.finditer(r'\s+xmlns(?::[A-Za-z_][\w.\-]*)?\s*=\s*"[^"]*"',
                             xml[start:tag_end]):
        declarations.append(match.group(0))
    return "".join(declarations)


def _style_attribute(style: str | None) -> str:
    return f' s="{style}"' if style else ""


def _cell_element_xml(reference: str, style: str | None,
                      payload: tuple[str, str] | None, prefix: str,
                      declarations: str = "") -> str:
    """按给定**命名空间前缀**（可为空）生成单元格元素。

    Owner Phase 8 R3：前缀必须应用到**该单元格的全部子元素**（`v` / `is` / `t`），
    而不只是 `c`。否则在"默认 namespace 不是 MAIN_NS"的工作表里，
    `<x:c><v>…</v></x:c>` 的 `<v>` 会落进**别的**默认命名空间 ——
    正是本轮 blocker 的同类语义错误。
    """

    name = f"{prefix}:c" if prefix else "c"
    value_name = f"{prefix}:v" if prefix else "v"
    inline_name = f"{prefix}:is" if prefix else "is"
    text_name = f"{prefix}:t" if prefix else "t"
    style_attr = _style_attribute(style)
    if payload is None:
        return f'<{name} r="{reference}"{style_attr}{declarations}/>'
    kind, text = payload
    if kind == "n":
        return (f'<{name} r="{reference}"{style_attr}{declarations}>'
                f"<{value_name}>{text}</{value_name}></{name}>")
    if text == "":
        return f'<{name} r="{reference}"{style_attr}{declarations}/>'
    # 内联字符串：不改动 sharedStrings，因此不影响任何其他单元格。
    return (f'<{name} r="{reference}"{style_attr}{declarations} '
            f't="inlineStr"><{inline_name}><{text_name} xml:space="preserve">'
            f"{_escape(text)}</{text_name}></{inline_name}></{name}>")


def _row_prefix(row_attrs: dict[str, str], row_element: str) -> str:
    """该行**新插入**单元格应使用的命名空间前缀。

    优先沿用该行元素自身的前缀（`<x:row r="4">` → `x`）；否则看该行是否声明了
    前缀化的 `xmlns:*`；都没有就用无前缀形式（默认命名空间工作表）。
    """

    row_prefix = _prefix_of(row_element)
    if row_prefix:
        return row_prefix
    for key in row_attrs:
        if key.startswith("xmlns:"):
            return key.split(":", 1)[1]
    return ""


def _insert_missing_cells(row_xml: str, row_number: int, missing: list[str],
                          payloads: dict[str, tuple[str, str] | None],
                          fallback_style: str | None,
                          prefix: str) -> str:
    """把不存在的结果 cell 按**列序**插入，避免打乱既有列顺序。

    行结束位置按该行元素**实际的限定名**定位（`</x:row>` 对 `<x:row>`），
    绝不 rfind 硬编码的 `</row>`。
    """

    open_end = _find_tag_end(row_xml, 0)
    if open_end == -1:
        raise ResultWorkbookWriteError(
            f"结果写回失败：第 {row_number} 行的 XML 结构无效（标记未闭合）")
    qualified = _element_name(row_xml[:open_end])
    declarations = _namespace_declarations(row_xml, 0, open_end - 1)
    if row_xml[open_end - 1] == "/":
        # 自闭合空行 `<x:row r="4"/>` -> 显式展开成开/闭标记对再插入。
        body_start = body_end = open_end + 1
        opening = (row_xml[:open_end - 1].rstrip()
                   + f"{declarations}>")
        closing = f"</{qualified}>"
        row_xml = opening + closing + row_xml[body_start:]
        body_start = len(opening)
        body_end = body_start
        open_end = len(opening) - 1
    else:
        close = row_xml.find(_close_tag(qualified), open_end)
        if close == -1:
            raise ResultWorkbookWriteError(
                f"结果写回失败：第 {row_number} 行缺少匹配的结束标记 "
                f"{_close_tag(qualified)}")
        body_start = open_end + 1
        body_end = close

    for column in sorted(missing, key=_column_number):
        reference = f"{column}{row_number}"
        target = _column_number(column)
        body = row_xml[body_start:body_end]
        insertion = body_end
        for cell in _scan_cells(body):
            letter = re.match(r"([A-Z]+)", cell.reference)
            if letter and _column_number(letter.group(1)) > target:
                insertion = body_start + cell.start
                break
        row_xml = (row_xml[:insertion]
                   + _cell_element_xml(reference, fallback_style,
                                       payloads[column], prefix, declarations)
                   + row_xml[insertion:])
        # 插入后重新定位行内容区间（结束标记整体后移）。
        body_end = row_xml.find(_close_tag(qualified), open_end)
    return row_xml



#: 结果 worksheet 中**必须**属于 SpreadsheetML 主命名空间的核心元素（local name）。
_REQUIRED_MAIN_NS_ELEMENTS: frozenset[str] = frozenset(
    ("worksheet", "sheetData", "row", "c", "v", "is", "t"))


def _assert_main_namespace_semantics(xml: str) -> None:
    """用**真正 namespace-aware 的解析器**校验核心元素的命名空间。

    仅检查"XML 良构"是不够的：语法可以完全合法，而 namespace 语义完全错误
    （例如 `<x:row>` 被去掉前缀后落进别的默认命名空间）——那正是
    Owner Phase 8 R3 的 blocker。因此这里用 `ElementTree` 展开 QName
    （`{namespace}local`）做最终结构门禁（§六）。
    """

    from xml.etree import ElementTree

    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as error:
        raise ResultWorkbookWriteError(
            f"结果写回命名空间校验失败：「{PUMP_SHEET}」Sheet 不是良构 XML"
            f"（{error}）；拒绝产出无法打开的结果工作簿") from error

    main_prefix = "{" + _MAIN_NS + "}"
    local_root = _local_name(root.tag)
    if local_root != "worksheet" or not root.tag.startswith(main_prefix):
        raise ResultWorkbookWriteError(
            "结果写回命名空间校验失败：根元素不属于 SpreadsheetML 主命名空间"
            f"（实际 {root.tag!r}）；拒绝产出语义错误的结果工作簿")

    offenders: list[str] = []
    for element in root.iter():
        local = _local_name(element.tag)
        if local not in _REQUIRED_MAIN_NS_ELEMENTS:
            continue
        if not element.tag.startswith(main_prefix):
            offenders.append(element.tag)
    if offenders:
        raise ResultWorkbookWriteError(
            "结果写回命名空间校验失败：以下核心元素不属于 SpreadsheetML 主命名空间 "
            f"{sorted(set(offenders))[:10]}；拒绝产出语义错误的结果工作簿")


def _sheet_xml_paths(archive: ZipFile, sheet_name: str) -> str | None:
    """定位目标 Sheet 的 worksheet XML 路径。

    逐元素解析属性（而不是假设 `name` 与 `r:id` 的先后顺序或命名空间前缀），
    这样不同 Excel / openpyxl 版本写出的 workbook.xml 都能正确定位。
    """

    workbook = archive.read("xl/workbook.xml").decode("utf-8")
    relationships = archive.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    relation_map: dict[str, str] = {}
    for element in _REL_ELEMENT.findall(relationships):
        rid = _REL_ID_ATTR.search(element)
        target = _REL_TARGET_ATTR.search(element)
        if rid and target:
            relation_map[rid.group(1)] = target.group(1)

    for element in _SHEET_ELEMENT.findall(workbook):
        name = _NAME_ATTR.search(element)
        rid = _ID_ATTR.search(element)
        if not name or not rid or name.group(1) != sheet_name:
            continue
        target = relation_map.get(rid.group(1))
        if not target:
            return None
        target = target.lstrip("/")
        return target if target.startswith("xl/") else f"xl/{target}"
    return None


def _patch_sheet_xml(xml: str, outcomes: dict[int, BatchRowOutcome]) -> str:
    """**单遍**扫描并补丁全部目标行，最后强制整表坐标唯一。

    刻意避免"每行一次全串搜索"：那在 10,000 行时是 O(n²)（实测由 78s 恶化到 408s）。
    这里先把所有 `<row>` 位置一次找出，再从后往前替换，
    使每个目标行的补丁都只作用在其**自身**的片段上。

    **行定位不依赖属性顺序，也不依赖命名空间前缀**（local-name == "row"），
    并且**每个结果行都必须真正被补丁**：任何一行没找到就抛
    `ResultWorkbookWriteError`，绝不静默漏写后仍然保存"成功"的批次记录。

    返回之前执行**整张工作表**的坐标唯一性后置条件（Owner Phase 8 R2 §三）：
    任何非空坐标出现多于一次 -> 硬失败，绝不产出结构无效的结果工作簿。
    """

    rows = {row_number: (start, end)
            for start, end, row_number in _scan_rows(xml)}
    targets: list[tuple[int, int, int]] = []
    unresolved: list[int] = []
    for row_number in sorted(outcomes):
        span = rows.get(row_number)
        if span is None:
            unresolved.append(row_number)
        else:
            targets.append((span[0], span[1], row_number))
    if unresolved:
        raise ResultWorkbookWriteError(
            "结果写回失败：无法在「离心泵」Sheet 中定位以下数据行 "
            f"{unresolved[:10]}（共 {len(unresolved)} 行）；"
            "拒绝保存部分写回的结果工作簿")

    if targets:
        pieces: list[str] = []
        cursor = len(xml)
        for start, end, row_number in reversed(targets):
            pieces.append(xml[end:cursor])
            pieces.append(_patch_row(xml[start:end], row_number,
                                     cell_payloads(outcomes[row_number])))
            cursor = start
        pieces.append(xml[:cursor])
        pieces.reverse()
        xml = "".join(pieces)
        # 前缀化工作表：把主命名空间元素写回默认命名空间形式，确保结果工作簿
        # 能被 Excel / 现有 OOXML 读取器正常读取（它们不认前缀化元素），
        # 混用多个主命名空间前缀时逐个归一。
        before_normalisation = xml
        normalised = _normalise_main_namespace(xml)
        _assert_namespace_normalisation_preserves_qnames(
            before_normalisation, normalised)
        xml = normalised

    # 结构后置条件：写结果 Workbook 之前，整表坐标必须唯一，且整张工作表良构。
    _assert_unique_references(xml)
    _assert_well_formed(xml)
    # Owner Phase 8 R3 §六：良构 + 坐标唯一还不够，必须证明核心元素仍属于
    # SpreadsheetML 主命名空间（namespace-aware 解析，而不是字符串判断）。
    _assert_main_namespace_semantics(xml)
    return xml


class PumpResultWorkbookWriter:
    """把评价结果写入**新的**结果 Workbook（字节级复制 + 结果列定点补丁）。"""

    def default_destination(self, source: Path) -> Path:
        """``原文件名_评价结果_YYYYMMDD_HHMMSS.xlsx``（与源文件同目录）。"""

        source = Path(source)
        return source.with_name(default_result_filename(source))

    def write(self, source: Path, outcomes: dict[int, BatchRowOutcome],
              destination: Path, *, overwrite: bool = False) -> Path:
        source = Path(source)
        destination = Path(destination)
        if source.resolve() == destination.resolve():
            raise ValueError("结果工作簿不得覆盖原始输入文件")
        if destination.exists() and not overwrite:
            raise ResultWorkbookExistsError(
                f"结果工作簿已存在，不得静默覆盖：{destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)

        with ZipFile(source) as archive:
            entries = [(info, archive.read(info.filename))
                       for info in archive.infolist()]
            sheet_path = _sheet_xml_paths(archive, PUMP_SHEET)

        if not sheet_path:
            raise ValueError(f"结果工作簿写入失败：找不到「{PUMP_SHEET}」Sheet")

        # **先全部算完、再落盘**：结构后置条件（坐标唯一 / 良构）必须在目标文件
        # 创建之前完成。否则一旦写回中途硬失败，磁盘上会留下一个半成品结果文件，
        # 用户可能把它当成"结果工作簿"。既然后置条件在这里抛
        # `ResultWorkbookWriteError`，目标路径就必须保持**不存在**。
        patched: list[bytes | None] = []
        for info, data in entries:
            if info.filename == sheet_path:
                data = _patch_sheet_xml(data.decode("utf-8"),
                                        outcomes).encode("utf-8")
            patched.append(data)

        with ZipFile(destination, "w", ZIP_DEFLATED) as target:
            for (info, _original), data in zip(entries, patched):
                target.writestr(info, data)
        return destination

    def copy_verbatim(self, source: Path, destination: Path) -> Path:
        """逐字节复制（供"只输出模板"之类不修改内容的场景）。"""

        source, destination = Path(source), Path(destination)
        if source.resolve() == destination.resolve():
            raise ValueError("复制目标不得是源文件自身")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination
