"""Phase 8A：正式「离心泵」Workbook Reader（Excel-as-adapter）。

职责边界
--------
- 只读取**正式 input columns**；**绝不**把 Excel 中旧的计算结果
  （旧比转速 / C1~C3 / 基准效率 / 旧阈值 / 旧等级 / 旧自动备注）当作业务输入或真值。
- 行启用是**语义式**的，不依赖固定行范围：
    所有用户可编辑输入字段均为空 → 真正空行，跳过；
    任一用户输入字段非空       → 用户已开始填写该行 → 读取并交给软件验证。
  因此"只填了安装位置"的行**不会**被静默跳过，而会在软件侧报告缺少评价所需数据。
- 数值保持**可证明的十进制语义**（`Decimal` / `int`），不经过 `float`。
- 不在本层做业务判定：类别、吸入方式、级数、数量的合法性由正式 Application 契约裁定。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ...application.ports.batch_workbook import (
    BatchSourceRow,
    BatchSourceWorkbook,
)
from ...application.services.centrifugal_pump_analysis_service import (
    PUMP_CATEGORIES,
)
from .ooxml_reader import OOXMLReadError, OOXMLWorkbook

PUMP_SHEET = "离心泵"
CONFIG_SHEET = "配置"
CONFIG_TABLE = "FieldDictionary"

#: 用户可编辑的输入列（Excel 列字母 → 正式字段 ID）。
#: **结果列（比转速 / C1~C3 / 基准效率 / 效率修正值 / 规定点效率 / 1~3 级效率 /
#: 能效等级 / 自动备注）刻意不在其中**：它们是软件写入的产出，永远不是输入。
INPUT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("B", "device_name"),
    ("C", "model"),
    ("D", "quantity"),
    ("E", "location"),
    ("F", "category"),
    ("G", "flow"),
    ("H", "head"),
    ("I", "speed"),
    ("J", "power"),
    ("K", "suction"),
    ("L", "stages"),
    ("M", "efficiency"),
    ("Y", "photo"),
    ("Z", "fill_note"),
)

#: 正式结果列（只用于 Writer 定位；Reader 绝不读取）。
RESULT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("N", "specific_speed"), ("O", "c1"), ("P", "c2"), ("Q", "c3"),
    ("R", "base_efficiency"), ("S", "correction"), ("T", "specified_efficiency"),
    ("U", "grade1"), ("V", "grade2"), ("W", "grade3"), ("X", "conclusion"),
    ("AA", "auto_note"),
)

#: 任一非空即视为"用户已开始填写该行"的字段。
ENABLEMENT_FIELDS: tuple[str, ...] = tuple(field_id for _, field_id in INPUT_COLUMNS)


def _column_index(letter: str) -> int:
    value = 0
    for char in letter.upper():
        value = value * 26 + ord(char) - ord("A") + 1
    return value - 1


#: 载体 DTO 由 Application 端口定义（Application 不认识 Excel）。
PumpWorkbookRow = BatchSourceRow
PumpWorkbook = BatchSourceWorkbook


def _is_blank(row: BatchSourceRow) -> bool:
    return not any(row.values.get(name) not in (None, "")
                   for name in ENABLEMENT_FIELDS)


class V6PumpWorkbookReader:
    """读取「离心泵」Sheet 的输入行。"""

    def __init__(self, *, require_template_structure: bool = True):
        self.require_template_structure = require_template_structure

    def read(self, source: Path) -> PumpWorkbook:
        source = Path(source)
        if self.require_template_structure:
            self._check_structure(source)

        with OOXMLWorkbook(source) as workbook:
            grid = workbook.rows(PUMP_SHEET)

        header_row = self._find_header_row(grid)
        if header_row is None:
            raise OOXMLReadError(f"「{PUMP_SHEET}」Sheet 缺少正式表头行")

        # 列位置以**列字母契约**为准，同时用表头文本做防御性校验，
        # 避免模板被误改后软件静默读错列。
        self._verify_headers(grid[header_row])

        rows: list[PumpWorkbookRow] = []
        blank = 0
        for offset, raw in enumerate(grid[header_row + 1:], start=header_row + 2):
            values = {field_id: _cell(raw, letter)
                      for letter, field_id in INPUT_COLUMNS}
            row = BatchSourceRow(row_number=offset, values=values)
            if _is_blank(row):
                blank += 1
                continue
            rows.append(row)
        return BatchSourceWorkbook(path=str(source), rows=tuple(rows),
                                   skipped_blank_rows=blank)

    # -- 结构校验 ----------------------------------------------------------

    def _check_structure(self, source: Path) -> None:
        from .template_resource import V6TemplateResource

        validation = V6TemplateResource().validate(source)
        if not validation.is_valid:
            raise OOXMLReadError(validation.message)

    def _find_header_row(self, grid: list[list[Any]]) -> int | None:
        for index, row in enumerate(grid[:10]):
            names = {_header_text(value) for value in row}
            if {"序号", "设备名称", "型号"}.issubset(names):
                return index
        return None

    def _verify_headers(self, header: list[Any]) -> None:
        expected = {
            "B": "设备名称", "C": "型号", "D": "数量", "E": "安装位置", "F": "设备类别",
            "G": "流量", "H": "扬程", "I": "额定转速", "J": "额定功率", "K": "单吸/双吸",
            "L": "级数", "M": "泵效率",
        }
        for letter, name in expected.items():
            actual = _header_text(_cell(header, letter))
            if name not in actual:
                raise OOXMLReadError(
                    f"「{PUMP_SHEET}」Sheet 的表头与模板契约不符："
                    f"{letter} 列期望含「{name}」，实际为「{actual}」")


def _header_text(value: Any) -> str:
    return str(value or "").replace("\r", "").strip().split("\n", 1)[0].strip()


def _cell(row: list[Any], letter: str) -> Any:
    index = _column_index(letter)
    if index >= len(row):
        return ""
    value = row[index]
    return "" if value is None else value


def formal_category_names() -> tuple[str, ...]:
    """正式类别枚举（唯一来源：Application 契约）。"""
    return tuple(item.visible_name for item in PUMP_CATEGORIES)
