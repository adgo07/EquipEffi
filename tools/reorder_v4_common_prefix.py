"""Put the V4 common prefix in the contractual order.

The V4 contract is ``序号｜设备名称｜型号｜数量｜设备类别｜安装位置``.
An earlier workbook revision placed the last two fields in the opposite order.
This migration swaps columns E/F in the 15 device sheets and updates formulas,
validations, table metadata and row-2 group merges so the operation is safe to
rerun on a copy of the workbook.
"""

from __future__ import annotations

import re
import sys
from copy import copy
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import range_boundaries

from equipeffi.infrastructure.excel.template_resource import REQUIRED_V4_SHEETS


_CELL_REF = re.compile(r"(\$?)([EF])(\$?\d+)")


def _swap_refs(value: object) -> object:
    if not isinstance(value, str) or not value.startswith("="):
        return value
    marker = "\x00COLUMN_E\x00"
    value = _CELL_REF.sub(lambda m: f"{m.group(1)}{marker}{m.group(3)}" if m.group(2) == "E" else f"{m.group(1)}E{m.group(3)}", value)
    return value.replace(marker, "F")


def _swap_range_token(token: str) -> str:
    try:
        min_col, min_row, max_col, max_row = range_boundaries(token)
    except ValueError:
        return token
    if min_col == max_col == 5:
        min_col = max_col = 6
    elif min_col == max_col == 6:
        min_col = max_col = 5
    elif min_col == 5 and max_col == 6:
        # A range spanning both columns is unchanged as a set.
        return token
    else:
        return token
    letter = get_column_letter(min_col)
    return f"{letter}{min_row}:{letter}{max_row}" if ":" in token else f"{letter}{min_row}"


def _swap_row2_groups(sheet) -> None:
    ranges = list(sheet.merged_cells.ranges)
    to_replace = [item for item in ranges if item.min_row == item.max_row == 2 and (item.min_col == 1 or item.min_col == 6)]
    if not to_replace:
        return
    anchors: dict[str, tuple[object, object]] = {}
    for item in to_replace:
        anchor = sheet.cell(item.min_row, item.min_col)
        anchors[str(item)] = (anchor.value, copy(anchor._style))
        sheet.unmerge_cells(str(item))
    for item in to_replace:
        if item.min_col == 1 and item.max_col == 5:
            new_min, new_max = 1, 6
        elif item.min_col == 6:
            new_min, new_max = 7, item.max_col
        else:
            continue
        new_range = f"{get_column_letter(new_min)}2:{get_column_letter(new_max)}2"
        sheet.merge_cells(new_range)
        value, style = anchors[str(item)]
        target = sheet.cell(2, new_min)
        target.value = value
        target._style = copy(style)


def reorder(source: Path, destination: Path | None = None) -> Path:
    source = Path(source)
    destination = Path(destination) if destination else source
    workbook = load_workbook(source, read_only=False, data_only=False)
    try:
        for sheet_name in REQUIRED_V4_SHEETS[3:]:
            sheet = workbook[sheet_name]
            header_e, header_f = sheet.cell(3, 5).value, sheet.cell(3, 6).value
            old_order = "安装位置" in str(header_e or "") and "设备类别" in str(header_f or "")
            desired_order = "设备类别" in str(header_e or "") and "安装位置" in str(header_f or "")
            if not old_order and not desired_order:
                raise ValueError(f"{sheet_name}的E/F表头不是安装位置/设备类别组合")
            if desired_order:
                continue
            _swap_row2_groups(sheet)
            # Swap all visible header/data cells.  Rows 1/2 contain merged
            # title/group cells and are handled separately above.
            for row in range(3, sheet.max_row + 1):
                left, right = sheet.cell(row, 5), sheet.cell(row, 6)
                left._style, right._style = copy(right._style), copy(left._style)
                left.number_format, right.number_format = right.number_format, left.number_format
                left.value, right.value = right.value, left.value
                left.protection, right.protection = copy(right.protection), copy(left.protection)
                left.hyperlink, right.hyperlink = right.hyperlink, left.hyperlink
                left.comment, right.comment = right.comment, left.comment
            # Formulas and validation formulas still refer to their old
            # physical columns after the cell swap.
            for row in sheet.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str) and cell.value.startswith("="):
                        cell.value = _swap_refs(cell.value)
            for validation in sheet.data_validations.dataValidation:
                validation.sqref = " ".join(_swap_range_token(token) for token in str(validation.sqref).split())
                validation.formula1 = _swap_refs(validation.formula1)
                validation.formula2 = _swap_refs(validation.formula2)
            # Keep column widths and visibility attached to their fields.
            left_dim, right_dim = sheet.column_dimensions["E"], sheet.column_dimensions["F"]
            left_dim.width, right_dim.width = right_dim.width, left_dim.width
            left_dim.hidden, right_dim.hidden = right_dim.hidden, left_dim.hidden
            for table in sheet.tables.values():
                if len(table.tableColumns) >= 6:
                    table.tableColumns[4].name, table.tableColumns[5].name = table.tableColumns[5].name, table.tableColumns[4].name
                for column in table.tableColumns:
                    formula = getattr(column, "calculatedColumnFormula", None)
                    if formula is not None and getattr(formula, "attr_text", None):
                        formula.attr_text = _swap_refs(formula.attr_text)
        # 配置sheet也按公共前缀顺序提供字段，确保桌面动态表单与Excel列顺序一致。
        config = workbook["配置"]
        header_index = {str(config.cell(1, col).value or ""): col for col in range(1, config.max_column + 1)}
        sheet_col, field_col, group_col = (header_index.get("sheet", 1), header_index.get("字段ID", 2), header_index.get("字段分组", 4))
        for sheet_name in REQUIRED_V4_SHEETS[3:]:
            rows_by_field: dict[str, int] = {}
            for row in range(2, config.max_row + 1):
                if str(config.cell(row, sheet_col).value or "") == sheet_name:
                    rows_by_field[str(config.cell(row, field_col).value or "")] = row
            category_row, location_row = rows_by_field.get("category"), rows_by_field.get("location")
            if category_row and location_row and category_row > location_row:
                for col in range(1, config.max_column + 1):
                    left, right = config.cell(location_row, col), config.cell(category_row, col)
                    left.value, right.value = right.value, left.value
                    left._style, right._style = copy(right._style), copy(left._style)
                    left.number_format, right.number_format = right.number_format, left.number_format
                category_row = location_row
            if category_row:
                config.cell(category_row, group_col).value = "基础信息"
        workbook.save(destination)
    finally:
        workbook.close()
    return destination


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or len(args) > 2:
        print("用法: python tools/reorder_v4_common_prefix.py 输入.xlsx [输出.xlsx]", file=sys.stderr)
        return 2
    reorder(Path(args[0]), Path(args[1]) if len(args) == 2 else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
