"""结果 Workbook Writer（Phase 8 R4 重写）。

输出契约（Owner Phase 8）
------------------------
```text
结果 Workbook = 原输入文件**逐字节副本** + 只对「离心泵」Sheet 的结果列做定点补丁
```

因此：

- 用户输入列（企业/项目、设备名称、型号、数量、安装位置、类别、流量、扬程、转速、
  功率、吸入方式、级数、效率、附件/备注）**永不重新序列化**，35 位小数等精度保持原样；
- 其它 ZIP 部件（其余 17 个 Sheet、图片、验证、保护、样式、sharedStrings）
  **逐字节不变**；
- 原始输入文件**永不覆盖**。

成功的最低条件（缺一不可，全部由**独立解析器**证明）
--------------------------------------------------
```text
1. 每个结果行都真正被补丁（定位不到 -> 硬失败，绝不静默漏写）
2. XML 良构
3. 正式路径上的核心元素属于 SpreadsheetML 主命名空间
4. 每个结果坐标在整表中恰好一次（独立 expat 解析，不依赖自研扫描器）
5. 用户输入单元格的值逐一不变
6. 结果列的值等于本 Writer 声称写入的 payload
7. 文件**原子提交**：先写临时文件并重新打开复验，通过后才替换目标；
   任何失败都清理半成品，目标路径不会留下残缺文件
```

只有以上全部通过，调用方（批量服务）才允许保存成功 `batch_record`。
"""
from __future__ import annotations

import os
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from ...application.ports.batch_workbook import BatchRowOutcome
from .result_invariants import (
    InvariantViolation,
    assert_input_preserved,
    assert_main_namespace_paths,
    assert_non_main_elements_preserved,
    assert_result_payloads,
    assert_unique_references,
)
from .worksheet_patch import (
    SheetStructureError,
    outer_attributes,
    WorksheetPatch,
    cell_xml,
    column_number,
    split_reference,
)
from .xml_model import EMPTY, END, MAIN_NS, START, parse_elements, scan_tags

PUMP_SHEET = "离心泵"

#: 派生列：列 -> 正式 `calculation_trace.derived` 的键（含中文后缀的键按前缀匹配）。
_DERIVED_FIELDS: tuple[tuple[str, str], ...] = (
    ("N", "比转速 ns"),
    ("O", "C1"),
    ("P", "C2"),
    ("Q", "C3"),
    ("R", "基准效率（%）"),
    ("S", "效率修正值（%）"),
    ("T", "规定点效率（%）"),
)

#: 等级限值列：**只读正式 `PumpAnalysisResult.thresholds`**，绝不重算。
THRESHOLD_COLUMNS: tuple[tuple[str, str], ...] = (
    ("U", "1级能效效率限值（%）"),
    ("V", "2级能效效率限值（%）"),
    ("W", "3级能效效率限值（%）"),
)

_DERIVED_BY_COLUMN: dict[str, str] = dict(_DERIVED_FIELDS)
_THRESHOLD_BY_COLUMN: dict[str, str] = dict(THRESHOLD_COLUMNS)

#: 会被写入的结果列（其余一律原样保留）。
RESULT_COLUMNS: tuple[str, ...] = tuple(
    column for column, _ in _DERIVED_FIELDS
) + tuple(column for column, _ in THRESHOLD_COLUMNS) + ("X", "AA")

#: 全部结果列定义（列 -> 中文表头），供一致性检查与文档使用。
RESULT_FIELDS: tuple[tuple[str, str], ...] = tuple(
    (column, name) for column, name in _DERIVED_FIELDS
) + tuple(THRESHOLD_COLUMNS) + (("X", "结论"), ("AA", "说明"))

RESULT_FILENAME_INFIX = "_评价结果_"

_TEMP_SUFFIX = ".equipeffi-tmp"


class ResultWorkbookWriteError(RuntimeError):
    """结果 Workbook 未能按契约写回（硬失败，绝不静默漏写或留下半成品）。"""


class ResultWorkbookExistsError(FileExistsError):
    """目标结果工作簿已存在（禁止静默覆盖）。"""


def default_result_filename(source: Path, when: datetime | None = None) -> str:
    """``原文件名_评价结果_YYYYMMDD_HHMMSS.xlsx``。"""

    source = Path(source)
    stamp = (when or datetime.now()).strftime("%Y%m%d_%H%M%S")
    suffix = source.suffix or ".xlsx"
    return f"{source.stem}{RESULT_FILENAME_INFIX}{stamp}{suffix}"


# ---------------------------------------------------------------------------
# payload 计算（只读正式 Result，不重算任何业务值）
# ---------------------------------------------------------------------------

def _as_number(value) -> str | None:
    """把正式数值写成**精确字面量**：Decimal 保持精度，绝不经 `float`。"""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return format(Decimal(text), "f")
    except (InvalidOperation, ValueError):
        return text


def _derived_value(outcome: BatchRowOutcome, name: str) -> str | None:
    derived = outcome.derived or {}
    if name in derived:
        return _as_number(derived[name])
    prefix = name.split("（")[0]
    for key, value in derived.items():
        if str(key).strip().startswith(prefix):
            return _as_number(value)
    return None


def _threshold_value(outcome: BatchRowOutcome, name: str) -> str | None:
    return _as_number((outcome.thresholds or {}).get(name))


def cell_payloads(outcome: BatchRowOutcome) -> dict[str, tuple[str, str] | None]:
    """该行每个结果列的写入内容。

    `None` 表示**刻意不写**（例如 `OUT_OF_STANDARD_SCOPE` / 不确定类别没有正式
    等级限值）——绝不伪造 `U/V/W`。
    """

    payloads: dict[str, tuple[str, str] | None] = {}
    for column, name in _DERIVED_FIELDS:
        value = _derived_value(outcome, name)
        payloads[column] = None if value is None else ("n", value)
    for column, name in THRESHOLD_COLUMNS:
        value = _threshold_value(outcome, name)
        payloads[column] = None if value is None else ("n", value)
    payloads["X"] = ("s", outcome.conclusion or "")
    messages = [message for message in (outcome.messages or []) if message]
    payloads["AA"] = ("s", "；".join(messages))
    return payloads


# ---------------------------------------------------------------------------
# 命名空间规范化（A/B/C 三分法；R3 语义保持）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NamespacePlan:
    """前缀归一决策。"""

    default_uri: str | None
    #: 可安全去掉的 MAIN_NS 前缀（仅情况 A / B）。
    strippable: tuple[str, ...]
    #: 必须保留的 MAIN_NS 前缀（情况 C）。
    preserved: tuple[str, ...]
    #: 是否需要在根元素补 `xmlns="MAIN_NS"`（仅情况 A）。
    needs_default: bool


def plan_namespace(xml: str) -> NamespacePlan:
    """按 Owner §二 区分 A / B / C。

    ```text
    A 无默认 namespace           -> 允许规范化（补默认绑定 + 去前缀）
    B 默认 == MAIN_NS            -> 允许去掉冗余前缀
    C 默认 != MAIN_NS            -> 必须保留前缀与声明（去掉会落进别的命名空间）
    ```
    """

    elements = parse_elements(xml)
    if not elements:
        return NamespacePlan(None, (), (), False)
    root = elements[0]
    default_uri = root.scope.get("")
    main_prefixes = tuple(prefix for prefix, uri in root.declared.items()
                          if uri == MAIN_NS and prefix)
    if default_uri is not None and default_uri != MAIN_NS:
        return NamespacePlan(default_uri, (), main_prefixes, False)
    return NamespacePlan(default_uri, main_prefixes, (), default_uri is None)


def strip_main_namespace_prefixes(xml: str, plan: NamespacePlan) -> str:
    """去掉可归一的前缀（逐元素按词法作用域配对判定），其余字节原样保留。

    两个必须同时满足的约束：

    1. 判定用**该元素自己的作用域**，不能用根层声明推全局。后代把同一前缀重绑定
       到别的 URI 时（`<x:ext><x:payload xmlns:x="urn:other">`），那些元素不属于
       MAIN_NS，绝不能去前缀——否则扩展 payload 被静默改写进 SpreadsheetML。
    2. 开标记与**配对的**闭合标记同进退，不能只按"前缀在名单里"删闭合标记，
       否则会留下悬空的 `</x:...>`。
    """

    if not plan.strippable:
        return xml
    elements = parse_elements(xml)
    by_start = {element.start: element for element in elements
                if element.kind != END}

    # 扫描标记流，用栈把闭合标记与**配对的**开标记关联起来
    removable: set[int] = set()
    stack: list[str] = []
    for kind, start, tag_end in scan_tags(xml):
        if kind not in (START, EMPTY, END):
            continue
        window = xml[start:tag_end + 1]
        if kind == END:
            if not stack:
                continue
            if stack.pop() in plan.strippable:
                removable.add(start)
            continue
        match = re.match(r"<([A-Za-z_][\w.-]*):", window)
        if not match:
            if kind == START:
                stack.append("")
            continue
        prefix = match.group(1)
        element = by_start.get(start)
        strip_here = bool(
            prefix in plan.strippable and element is not None
            and element.ns_uri == MAIN_NS)
        if kind == START:
            stack.append(prefix if strip_here else "")
        if strip_here:
            removable.add(start)

    still_used = _prefixes_still_used(elements, plan)
    edits: set[tuple[int, int, str]] = set()
    for kind, start, tag_end in scan_tags(xml):
        if kind not in (START, EMPTY, END):
            continue
        window = xml[start:tag_end + 1]
        if start in removable:
            match = re.match(r"</?([A-Za-z_][\w.-]*):", window)
            if match:
                prefix_start = (start + 2) if kind == END else (start + 1)
                edits.add((prefix_start,
                           prefix_start + len(match.group(1)) + 1, ""))
        if kind == END:
            continue
        for match in re.finditer(
                r'\s+xmlns:([A-Za-z_][\w.-]*)\s*=\s*"[^"]*"', window):
            prefix = match.group(1)
            if prefix in plan.strippable and prefix not in still_used:
                edits.add((start + match.start(), start + match.end(), ""))

    if not edits:
        return xml
    out = xml
    cursor = len(out)
    for start, end, replacement in sorted(edits, key=lambda item: item[0],
                                          reverse=True):
        if start >= cursor:
            continue
        out = out[:start] + replacement + out[end:]
        cursor = start
    return out


def _prefixes_still_used(elements, plan: NamespacePlan) -> set[str]:
    """归一后**仍会被引用**的前缀（即不属于 MAIN_NS 的元素所用的前缀）。"""

    used: set[str] = set()
    for element in elements:
        if element.kind == END or not element.prefix:
            continue
        if not (element.ns_uri == MAIN_NS and element.prefix in plan.strippable):
            used.add(element.prefix)
    return used


def protect_no_namespace_subtrees(xml: str, plan: NamespacePlan) -> str:
    """情况 A 补根默认命名空间前，保护原本**无命名空间**的扩展子树。

    若根原本没有默认 namespace，而 SpreadsheetML 通过 x:/ss: 等前缀承载，
    合法扩展可以使用无前缀元素：<payload>。直接给根补 xmlns=MAIN_NS 会把它
    静默改成 {MAIN_NS}payload。

    这里仅在每个无命名空间子树的**最外层边界**补 xmlns=""。这样随后根增加
    xmlns=MAIN_NS 时，SpreadsheetML 可安全去前缀，而扩展子树继续保持
    "无命名空间"。已有显式 xmlns="" 的边界不重复添加。
    """

    if not plan.needs_default:
        return xml
    elements = parse_elements(xml)
    edits: list[tuple[int, int, str]] = []
    for element in elements:
        if element.prefix or element.ns_uri not in (None, ""):
            continue
        if element.declared.get("") == "":
            continue
        parent = element.parent
        # 父元素本身已是无命名空间时，由父级最外层边界一次保护整个子树。
        if parent is not None and not parent.prefix and parent.ns_uri in (None, ""):
            continue
        insertion = element.tag_end - 1 if element.kind == EMPTY else element.tag_end
        edits.append((insertion, insertion, ' xmlns=""'))

    out = xml
    for start, end, replacement in sorted(edits, key=lambda item: item[0], reverse=True):
        out = out[:start] + replacement + out[end:]
    return out


def insert_default_namespace(xml: str, plan: NamespacePlan) -> str:
    """情况 A 下在根元素补 `xmlns="MAIN_NS"`；B / C 绝不追加。"""

    if not plan.needs_default:
        return xml
    elements = parse_elements(xml)
    if not elements:
        return xml
    root = elements[0]
    return xml[:root.tag_end] + f' xmlns="{MAIN_NS}"' + xml[root.tag_end:]


def _normalise_main_namespace(xml: str) -> str:
    """兼容别名（Phase 8 R3 时期的名称）；行为与 `normalise_namespace` 一致。"""

    return normalise_namespace(xml)


def normalise_namespace(xml: str) -> str:
    plan = plan_namespace(xml)
    # 顺序不可交换：必须在去掉 SpreadsheetML 前缀之前识别原本无命名空间的
    # 扩展子树并建立 xmlns="" 边界，否则去前缀后无法区分二者。
    protected = protect_no_namespace_subtrees(xml, plan)
    stripped = strip_main_namespace_prefixes(protected, plan)
    return insert_default_namespace(stripped, plan)


# ---------------------------------------------------------------------------
# 公开查询辅助（供测试与门禁使用；不要再用私有扫描器证明 Writer 正确）
# ---------------------------------------------------------------------------

def default_namespace_uri(xml: str) -> str | None:
    """工作表根元素的**默认命名空间 URI**（无默认命名空间时为 `None`）。

    Owner Phase 8 R3 / §二 的 A / B / C 判定基础，由真正的解析器给出，
    不再是"是否存在 `xmlns=`"的字符串判断。
    """

    elements = parse_elements(xml)
    return elements[0].scope.get("") if elements else None


def main_namespace_prefixes(xml: str) -> tuple[str, ...]:
    """根元素上绑定到 MAIN_NS 的全部前缀。"""

    elements = parse_elements(xml)
    if not elements:
        return ()
    return tuple(prefix for prefix, uri in elements[0].declared.items()
                 if uri == MAIN_NS and prefix)


def assert_main_namespace_semantics(xml: str) -> None:
    """校验**正式路径**上的核心元素属于 MAIN_NS（独立解析器）。

    只检查 `worksheet / sheetData / row / c / v` 这条实际路径；扩展容器里同名但
    不同命名空间的元素不受影响（D03）。
    """

    try:
        assert_main_namespace_paths(xml)
    except InvariantViolation as error:
        raise ResultWorkbookWriteError(
            f"结果写回命名空间校验失败：{error}；拒绝产出语义错误的结果工作簿"
        ) from error


def assert_unique_references(xml: str):  # noqa: F811 - 公开别名
    """整表坐标唯一性（独立 expat 解析）。"""

    from .result_invariants import assert_unique_references as _check

    return _check(xml)


def cell_references(xml: str) -> list[str]:
    """按正式路径取全部单元格坐标（独立 expat 解析）。

    这是取代旧 `_scan_cells(...).reference` 的公开入口：**身份判定由独立解析器
    给出**，因此单引号属性、属性顺序、命名空间前缀都不再影响结果。
    """

    from .result_invariants import parse_cells_with_expat

    return [fact.reference for fact in parse_cells_with_expat(xml)]


def _scan_cells_compat(xml: str):
    """仅为既有测试保留的兼容视图（**不用于任何产品判定**）。"""

    patch = WorksheetPatch(xml)
    cells = []
    for row in patch.rows.values():
        cells.extend(row.cells)
    return cells


# ---------------------------------------------------------------------------
# 补丁
# ---------------------------------------------------------------------------

def _normalised_prefix(plan: NamespacePlan, prefix: str,
                      ns_uri: str | None) -> str:
    """某个元素在**命名空间归一之后**应使用的前缀。

    归一化会把"绑定 MAIN_NS 且在情况 A/B 下"的前缀去掉，因此**生成阶段就必须**
    用归一后的前缀，否则会先写出 `x:` 元素、归一化时又对不上闭合标记。
    """

    if not prefix:
        return ""
    if ns_uri == MAIN_NS and prefix in plan.strippable:
        return ""
    return prefix


def _row_prefix(patch: WorksheetPatch, plan: NamespacePlan,
                row_number: int) -> str:
    """新插入单元格在归一后应使用的命名空间前缀。

    情况 C（默认命名空间不是 MAIN_NS）必须沿用行的前缀，否则新元素会落进别的
    默认命名空间——由**解析后的作用域**决定，不做字面猜测。
    """

    default_uri = patch.root.scope.get("") if patch.root is not None else None
    row = patch.rows.get(row_number)
    if default_uri is None or default_uri != MAIN_NS:
        # 情况 A：行前缀若绑定 MAIN_NS，归一化会去掉它 -> 新元素用无前缀形式
        if row is not None:
            return _normalised_prefix(plan, row.element.prefix,
                                      row.element.ns_uri)
        return ""
    # 情况 B：默认已是 MAIN_NS，新元素必须无前缀
    if row is not None and row.element.ns_uri != MAIN_NS:
        return _normalised_prefix(plan, row.element.prefix, row.element.ns_uri)
    return ""


def _row_reference_counts(row) -> dict[str, int]:
    counts: dict[str, int] = {}
    for cell in row.cells:
        if cell.reference:
            counts[cell.reference] = counts.get(cell.reference, 0) + 1
    return counts


def _row_edits(patch: WorksheetPatch, row_number: int,
               payloads: dict[str, tuple[str, str] | None],
               plan: NamespacePlan) -> list[tuple[int, int, str]]:
    """算出该行的全部替换/插入编辑（**不修改** XML，便于一次解析、单遍应用）。"""

    row = patch.rows[row_number]
    duplicated = sorted(ref for ref, count in _row_reference_counts(row).items()
                        if count > 1)
    if duplicated:
        raise ResultWorkbookWriteError(
            f"输入工作表第 {row_number} 行存在重复单元格坐标"
            f"（{'、'.join(duplicated[:10])}），无法确定应更新哪一个；拒绝写回")

    prefix = _row_prefix(patch, plan, row_number)
    by_reference = {cell.reference: cell for cell in row.cells if cell.reference}
    fallback_style = next((cell.style for cell in row.cells if cell.style), None)

    edits: list[tuple[int, int, str]] = []
    missing: list[str] = []
    for column in sorted(payloads, key=column_number):
        reference = f"{column}{row_number}"
        existing = by_reference.get(reference)
        if existing is not None:
            style = existing.style or fallback_style
            # 就地替换：使用**归一化之后**的前缀，保持其命名空间语义
            effective = _normalised_prefix(plan, existing.element.prefix,
                                           existing.element.ns_uri)
            edits.append((existing.start, existing.end,
                          cell_xml(reference, style, payloads[column],
                                   effective,
                                   extra=outer_attributes(existing.element))))
        else:
            missing.append(column)

    body_end = row.body_end
    for column in sorted(missing, key=column_number):
        reference = f"{column}{row_number}"
        target = column_number(column)
        insertion = body_end
        for cell in row.cells:
            split = split_reference(cell.reference or "")
            if split and column_number(split[0]) > target:
                insertion = cell.start
                break
        edits.append((insertion, insertion,
                      cell_xml(reference, fallback_style, payloads[column], prefix)))
    return edits


def patch_sheet_xml(xml: str, outcomes: dict[int, BatchRowOutcome]) -> str:
    """补丁全部结果行，然后执行**独立**后置条件校验。"""

    try:
        patch = WorksheetPatch(xml)
    except SheetStructureError as error:
        raise ResultWorkbookWriteError(
            f"结果写回结构校验失败：{error}；拒绝产出结果工作簿") from error

    missing = sorted(number for number in outcomes if number not in patch.rows)
    if missing:
        raise ResultWorkbookWriteError(
            "结果写回失败：无法在「离心泵」Sheet 中定位以下数据行 "
            f"{missing[:10]}（共 {len(missing)} 行）；拒绝保存部分写回的结果工作簿")

    duplicates = patch.duplicate_references()
    if duplicates:
        raise ResultWorkbookWriteError(
            "输入工作表存在重复单元格坐标（数据完整性缺陷）："
            f"{sorted(duplicates)[:10]}；拒绝写回")

    # **一次解析**：所有行的编辑先收集（相对原始 XML 的绝对区间），再单遍从后
    # 往前应用。逐行重新解析整份工作表在 10,000 行时是 O(n²)（实测不可接受）。
    plan = plan_namespace(xml)
    all_edits: list[tuple[int, int, str]] = []
    for row_number in sorted(outcomes):
        all_edits.extend(_row_edits(patch, row_number,
                                    cell_payloads(outcomes[row_number]), plan))
    # 校验：编辑区间之间不得重叠（同行内的插入点与替换区间按列序天然不重叠）
    all_edits.sort(key=lambda item: (item[0], item[1]))
    previous_end = -1
    for start, end, _fragment in all_edits:
        if start < previous_end:
            raise ResultWorkbookWriteError(
                "结果写回失败：补丁区间相互重叠，拒绝产出可能损坏的工作簿")
        previous_end = max(previous_end, end)
    current = patch.apply(all_edits)
    current = _normalise_main_namespace(current)

    # 独立后置条件：除正式 SpreadsheetML 结果区外，扩展元素的 QName/内容也必须
    # 保持。该门禁能抓住"补默认命名空间导致 <payload> 被静默搬进 MAIN_NS"。
    try:
        assert_non_main_elements_preserved(xml, current)
        assert_unique_references(current)
        assert_main_namespace_paths(current)
    except InvariantViolation as error:
        raise ResultWorkbookWriteError(
            f"结果写回独立校验失败：{error}；拒绝产出结果工作簿") from error
    return current


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

def _sheet_target(archive: ZipFile, sheet_name: str) -> str | None:
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
        target = relation_map.get(rid.group(1))
        if not target:
            return None
        target = target.lstrip("/")
        return target if target.startswith("xl/") else f"xl/{target}"
    return None


class PumpResultWorkbookWriter:
    """字节级复制 + 结果列定点补丁 + 原子提交。"""

    def default_destination(self, source: Path) -> Path:
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
            sheet_path = _sheet_target(archive, PUMP_SHEET)
        if not sheet_path:
            raise ValueError(f"结果工作簿写入失败：找不到「{PUMP_SHEET}」Sheet")

        names = [info.filename for info, _ in entries]
        source_xml = entries[names.index(sheet_path)][1].decode("utf-8")
        result_xml = patch_sheet_xml(source_xml, outcomes)
        patched: list[bytes] = []
        for info, data in entries:
            patched.append(result_xml.encode("utf-8")
                           if info.filename == sheet_path else data)

        # 用户输入保真 + 结果值一致性：**落盘之前**用独立解析器证明。
        expected: dict[str, str | None] = {}
        for row_number, outcome in outcomes.items():
            for column, payload in cell_payloads(outcome).items():
                if payload is not None:
                    expected[f"{column}{row_number}"] = str(payload[1])
        try:
            assert_input_preserved(
                source_xml, result_xml,
                row_numbers={int(number) for number in outcomes})
            assert_result_payloads(result_xml, expected)
        except InvariantViolation as error:
            raise ResultWorkbookWriteError(
                f"结果写回独立校验失败：{error}；拒绝产出结果工作簿") from error

        self._commit(destination, entries, patched)
        return destination

    # -- 原子提交 ----------------------------------------------------------

    def _commit(self, destination: Path, entries, patched: list[bytes]) -> None:
        """先写临时文件并**重新打开复验**，全部通过后才替换目标。

        任何失败都清理半成品：目标路径绝不留下残缺 Workbook
        （磁盘写失败、进程中断都不会污染最终文件名）。
        """

        temporary = destination.with_name(
            f".{destination.name}.{uuid.uuid4().hex}{_TEMP_SUFFIX}")
        try:
            with ZipFile(temporary, "w", ZIP_DEFLATED) as target:
                for (info, _original), data in zip(entries, patched):
                    target.writestr(info, data)
            # 复验临时文件：部件齐全、可读、结果 sheet 通过独立不变量。
            with ZipFile(temporary) as archive:
                if archive.namelist() != [info.filename for info, _ in entries]:
                    raise ResultWorkbookWriteError(
                        "结果工作簿部件列表与输入不一致，拒绝提交")
                for name in archive.namelist():
                    archive.read(name)
                sheet_path = _sheet_target(archive, PUMP_SHEET)
                if not sheet_path:
                    raise ResultWorkbookWriteError("临时结果工作簿缺少目标 Sheet")
                assert_unique_references(
                    archive.read(sheet_path).decode("utf-8"))
            os.replace(temporary, destination)
        except BaseException:
            try:
                if temporary.exists():
                    temporary.unlink()
            except OSError:
                pass
            raise

    def copy_verbatim(self, source: Path, destination: Path) -> Path:
        source, destination = Path(source), Path(destination)
        if source.resolve() == destination.resolve():
            raise ValueError("复制目标不得是源文件自身")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination
