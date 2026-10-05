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
    style_attr = f' s="{style}"' if style else ""
    if payload is None:
        return f'<c r="{reference}"{style_attr}/>'
    kind, text = payload
    if kind == "n":
        return f'<c r="{reference}"{style_attr}><v>{text}</v></c>'
    if text == "":
        return f'<c r="{reference}"{style_attr}/>'
    # 内联字符串：不改动 sharedStrings，因此不影响任何其他单元格。
    return (f'<c r="{reference}"{style_attr} t="inlineStr">'
            f'<is><t xml:space="preserve">{_escape(text)}</t></is></c>')


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
    """去掉命名空间前缀（`r` / `x:r` → `r`）。"""

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


@dataclass(frozen=True)
class _CellSpan:
    """一个 `<c>` 元素在行片段中的位置与属性。"""

    start: int
    end: int
    attrs: dict[str, str]

    @property
    def reference(self) -> str:
        return self.attrs.get("r", "")

    @property
    def style(self) -> str | None:
        return self.attrs.get("s")


def _scan_cells(row_xml: str) -> list[_CellSpan]:
    """扫描行片段中的所有 `<c>` 元素（顺序无关、可识别自闭合与带内容）。"""

    cells: list[_CellSpan] = []
    index = 0
    while True:
        start = row_xml.find("<c", index)
        if start == -1:
            break
        after = row_xml[start + 2:start + 3]
        if after and (after.isalnum() or after in "_:.-"):
            # `<c` 其实是 `<col`/`<cols` 之类的前缀误匹配，跳过。
            index = start + 2
            continue
        tag_end = _find_tag_end(row_xml, start)
        if tag_end == -1:
            break
        if row_xml[tag_end - 1] == "/":
            end = tag_end + 1
        else:
            close = row_xml.find("</c>", tag_end)
            end = len(row_xml) if close == -1 else close + 4
        cells.append(_CellSpan(start, end, _parse_attrs(row_xml[start:tag_end])))
        index = end
    return cells


def _scan_rows(xml: str) -> list[tuple[int, int, int]]:
    """扫描 sheetData 中的所有 `<row>`：返回 ``(start, end, row_number)``。

    与 `_scan_cells` 同一策略：**不假设属性顺序**（`r` 可以在任意位置）。
    """

    rows: list[tuple[int, int, int]] = []
    index = 0
    while True:
        start = xml.find("<row", index)
        if start == -1:
            break
        after = xml[start + 4:start + 5]
        if after and (after.isalnum() or after in "_:.-"):
            index = start + 4
            continue
        tag_end = _find_tag_end(xml, start)
        if tag_end == -1:
            break
        attrs = _parse_attrs(xml[start:tag_end])
        row_number = attrs.get("r")
        if row_xml_is_self_closing(xml, tag_end):
            end = tag_end + 1
        else:
            close = xml.find("</row>", tag_end)
            end = len(xml) if close == -1 else close + 6
        if row_number is not None:
            try:
                rows.append((start, end, int(row_number)))
            except ValueError:
                pass
        index = end
    return rows


def row_xml_is_self_closing(xml: str, tag_end: int) -> bool:
    return xml[tag_end - 1] == "/"


def _row_default_style(cells: list[_CellSpan]) -> str | None:
    """取该行第一个带样式的 cell 的样式号，供新增结果 cell 继承外观。"""

    for cell in cells:
        if cell.style:
            return cell.style
    return None


def _patch_row(row_xml: str, row_number: int,
               payloads: dict[str, tuple[str, str] | None]) -> str:
    """把结果列的 payload 写进这一行（顺序无关、不产生重复坐标）。"""

    cells = _scan_cells(row_xml)
    fallback_style = _row_default_style(cells)
    by_reference = {cell.reference: cell for cell in cells if cell.reference}

    # 输入本身有重复坐标时无法保证结果正确 -> 硬失败（不猜、不掩盖）。
    if len(by_reference) != len([c for c in cells if c.reference]):
        raise ResultWorkbookWriteError(
            f"输入工作表第 {row_number} 行存在重复单元格坐标，拒绝写回")

    edits: list[tuple[int, int, str]] = []
    for column in sorted(payloads, key=_column_number):
        reference = f"{column}{row_number}"
        existing = by_reference.get(reference)
        if existing is not None:
            style = existing.style or fallback_style
            edits.append((existing.start, existing.end,
                          _cell_xml(reference, style, payloads[column])))
    # 从后往前替换，保证前面的偏移仍然有效。
    for start, end, replacement in sorted(edits, key=lambda item: item[0], reverse=True):
        row_xml = row_xml[:start] + replacement + row_xml[end:]

    # 补齐该行**不存在**的结果 cell（按列序插入到正确位置）。
    missing = [column for column in sorted(payloads, key=_column_number)
               if f"{column}{row_number}" not in by_reference]
    if missing:
        row_xml = _insert_missing_cells(row_xml, row_number, missing,
                                        payloads, fallback_style)

    # 自校验：目标坐标必须恰好各出现一次。
    final_cells = _scan_cells(row_xml)
    counts: dict[str, int] = {}
    for cell in final_cells:
        if cell.reference:
            counts[cell.reference] = counts.get(cell.reference, 0) + 1
    for column in payloads:
        reference = f"{column}{row_number}"
        if counts.get(reference, 0) != 1:
            raise ResultWorkbookWriteError(
                f"结果写回自校验失败：{reference} 出现 {counts.get(reference, 0)} 次"
                "（必须恰好 1 次）")
    return row_xml


def _insert_missing_cells(row_xml: str, row_number: int, missing: list[str],
                          payloads: dict[str, tuple[str, str] | None],
                          fallback_style: str | None) -> str:
    """把不存在的结果 cell 按**列序**插入，避免打乱既有列顺序。"""

    for column in sorted(missing, key=_column_number):
        reference = f"{column}{row_number}"
        target = _column_number(column)
        cells = _scan_cells(row_xml)
        insertion = row_xml.rfind("</row>")
        if insertion == -1:
            insertion = len(row_xml)
        for cell in cells:
            letter = re.match(r"([A-Z]+)", cell.reference)
            if letter and _column_number(letter.group(1)) > target:
                insertion = cell.start
                break
        row_xml = (row_xml[:insertion]
                   + _cell_xml(reference, fallback_style, payloads[column])
                   + row_xml[insertion:])
    return row_xml


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
    """**单遍**扫描并补丁全部目标行。

    刻意避免"每行一次全串搜索"：那在 10,000 行时是 O(n²)（实测由 78s 恶化到 408s）。
    这里先把所有 `<row>` 位置一次找出，再从后往前替换，
    使每个目标行的补丁都只作用在其**自身**的片段上。

    **行定位不依赖属性顺序**（复审 blocker 1），并且**每个结果行都必须真正
    被补丁**：任何一行没找到就抛 `ResultWorkbookWriteError`，
    绝不静默漏写后仍然保存"成功"的批次记录。
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
    if not targets:
        return xml

    pieces: list[str] = []
    cursor = len(xml)
    for start, end, row_number in reversed(targets):
        pieces.append(xml[end:cursor])
        pieces.append(_patch_row(xml[start:end], row_number,
                                 cell_payloads(outcomes[row_number])))
        cursor = start
    pieces.append(xml[:cursor])
    pieces.reverse()
    return "".join(pieces)


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

        with ZipFile(destination, "w", ZIP_DEFLATED) as target:
            for info, data in entries:
                if info.filename == sheet_path:
                    xml = data.decode("utf-8")
                    data = _patch_sheet_xml(xml, outcomes).encode("utf-8")
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
