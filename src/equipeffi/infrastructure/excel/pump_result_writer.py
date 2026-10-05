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


def _insertion_point(row_xml: str, column: str) -> int:
    """在行长内找到按列序应插入的位置（保持 OOXML 的列升序约定）。"""

    target = _column_number(column)
    for match in re.finditer(r'<c r="([A-Z]+)\d+"', row_xml):
        if _column_number(match.group(1)) > target:
            return match.start()
    end = row_xml.rfind("</row>")
    return end if end != -1 else len(row_xml)


_COLUMN_CELL_PATTERNS: dict[str, re.Pattern[str]] = {}


def _cell_pattern(reference: str) -> re.Pattern[str]:
    """按坐标缓存的 cell 正则。

    `re` 的内建缓存上限是 512 条；批量场景会用到上万个不同坐标，
    逐次 `re.compile` 会反复重新编译（10,000 行时是主要耗时来源）。
    """

    pattern = _COLUMN_CELL_PATTERNS.get(reference)
    if pattern is None:
        pattern = re.compile(
            r'<c r="' + reference
            + r'"(?P<attrs>[^>]*?)(?:/>|>(?P<body>.*?)</c>)', re.DOTALL)
        _COLUMN_CELL_PATTERNS[reference] = pattern
    return pattern


def _row_default_style(row_xml: str) -> str | None:
    """取该行第一个带样式的 cell 的样式号，供新增结果 cell 继承外观。"""

    for match in re.finditer(r'<c r="[A-Z]+\d+"([^>]*?)(?:/>|>)', row_xml):
        style = re.search(r's="(\d+)"', match.group(1) or "")
        if style:
            return style.group(1)
    return None


def _patch_row(row_xml: str, row_number: int,
               payloads: dict[str, tuple[str, str] | None]) -> str:
    fallback_style = _row_default_style(row_xml)
    for column in sorted(payloads, key=_column_number):
        payload = payloads[column]
        reference = f"{column}{row_number}"
        match = _cell_pattern(reference).search(row_xml)
        if match:
            style_match = re.search(r's="(\d+)"', match.group("attrs") or "")
            style = style_match.group(1) if style_match else fallback_style
            row_xml = (row_xml[:match.start()]
                       + _cell_xml(reference, style, payload)
                       + row_xml[match.end():])
            continue
        insertion = _insertion_point(row_xml, column)
        row_xml = (row_xml[:insertion]
                   + _cell_xml(reference, fallback_style, payload)
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
    """

    targets: list[tuple[int, int, int]] = []
    row_pattern = re.compile(r'<row r="(\d+)"[^>]*>.*?</row>', re.DOTALL)
    for match in row_pattern.finditer(xml):
        row_number = int(match.group(1))
        if row_number in outcomes:
            targets.append((match.start(), match.end(), row_number))
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
