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
from .template_resource import (
    PUMP_SHEET,
    PUMP_SHEET_CONTRACT,
    input_field_columns,
    pump_data_layout_issues,
    pump_header_issues,
)

#: 用户可编辑的输入列（Excel 列字母 → 正式字段 ID）。
#: **结果列（比转速 / C1~C3 / 基准效率 / 效率修正值 / 规定点效率 / 1~3 级效率 /
#: 能效等级 / 自动备注）刻意不在其中**：它们是软件写入的产出，永远不是输入。
INPUT_COLUMNS: tuple[tuple[str, str], ...] = input_field_columns()

#: 结果列的 Excel 坐标与可见表头（不承载业务指标 ID；稳定指标由正式结果契约提供）。
RESULT_COLUMNS: tuple[tuple[str, str], ...] = tuple(
    (field["column"], field["label"])
    for field in PUMP_SHEET_CONTRACT["fields"]
    if field.get("role") == "result")

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
        validation = None
        if self.require_template_structure:
            validation = self._check_structure(source)

        contract = (validation.pump_sheet_contract
                    if validation and validation.pump_sheet_contract
                    else PUMP_SHEET_CONTRACT)
        sheet_name = str(contract["sheet_name"])
        input_columns = input_field_columns(contract)
        with OOXMLWorkbook(source) as workbook:
            grid = workbook.rows(sheet_name)
            merged_ranges = workbook.merged_ranges(sheet_name)

        layout_issues = pump_data_layout_issues(merged_ranges, contract)
        if layout_issues:
            raise OOXMLReadError(
                "离心泵 Sheet 数据区布局与输入/结果读写契约冲突："
                + "；".join(layout_issues))

        header_row = int(contract["header_row"]) - 1
        if header_row < 0 or header_row >= len(grid):
            raise OOXMLReadError(f"「{sheet_name}」Sheet 缺少正式表头行")

        # 列位置以**列字母契约**为准，同时用表头文本做防御性校验，
        # 避免模板被误改后软件静默读错列。
        self._verify_headers(grid[header_row], contract, sheet_name)

        rows: list[PumpWorkbookRow] = []
        blank = 0
        for offset, raw in enumerate(grid[header_row + 1:], start=header_row + 2):
            values = {field_id: _cell(raw, letter)
                      for letter, field_id in input_columns}
            row = BatchSourceRow(row_number=offset, values=values)
            if _is_blank(row):
                blank += 1
                continue
            rows.append(row)
        template_identity = dict(validation.identity or {}) if validation else {}
        template_identity.update({
            "sheet_id": str(contract["sheet_id"]),
            "sheet_contract_revision": str(contract["contract_revision"]),
        })
        identity_source = (str(validation.identity_source or "").strip()
                           if validation else "")
        if identity_source:
            template_identity["identity_source"] = identity_source
        return BatchSourceWorkbook(path=str(source), rows=tuple(rows),
                                   skipped_blank_rows=blank,
                                   template_identity=template_identity)

    # -- 结构校验 ----------------------------------------------------------

    def _check_structure(self, source: Path):
        from .template_resource import V6TemplateResource

        # Header units and merge layout are checked against the same manifest
        # contract from one worksheet parse. Avoid materializing the 10k-row
        # sheet twice on the batch input path.
        validation = V6TemplateResource().validate(source, check_pump_sheet=False)
        if not validation.is_valid:
            raise OOXMLReadError(validation.message)
        return validation

    def _verify_headers(self, header: list[Any], contract=None,
                        sheet_name: str = PUMP_SHEET) -> None:
        issues = pump_header_issues(header, contract)
        if issues:
            raise OOXMLReadError(
                f"「{sheet_name}」Sheet 的表头/单位与模板契约不符："
                + "；".join(issues))


def _cell(row: list[Any], letter: str) -> Any:
    index = _column_index(letter)
    if index >= len(row):
        return ""
    value = row[index]
    return "" if value is None else value


def formal_category_names() -> tuple[str, ...]:
    """正式类别枚举（唯一来源：Application 契约）。"""
    return tuple(item.visible_name for item in PUMP_CATEGORIES)
