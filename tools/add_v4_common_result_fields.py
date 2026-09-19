"""为V4的15个设备sheet增加统一的锁定判定结果字段。

字段插在“铭牌照片”之前，保证照片、填表备注、自动备注仍为固定后缀；
配置sheet同步写入字段定义，供只读读取器和结果写回器使用。
"""
from __future__ import annotations

from copy import copy
from pathlib import Path
import re

from openpyxl import load_workbook
from openpyxl.worksheet.table import TableColumn
from openpyxl.utils import get_column_letter, range_boundaries


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "src" / "equipeffi" / "resources" / "templates" / "设备能效分析空白模板_重构版V4_20260825.xlsx"
DEVICE_SHEETS = (
    "变压器", "电动机", "空压机", "离心泵", "离心通风机", "轴流通风机", "鼓风机",
    "潜水电泵", "工业锅炉", "热处理设备", "热泵和冷水机组", "热泵热水机",
    "风管送风式空调", "单元式空调", "多联式空调",
)
COMMON_FIELDS = (
    ("standard_code", "采用标准", "标准结果", "文本", "-"),
    ("standard_table", "匹配表/条款", "标准结果", "文本", "-"),
    ("reference_grade", "参考能效等级", "标准结果", "文本", "-"),
    ("explanation", "判定说明", "标准结果", "文本", "-"),
    ("missing_fields", "缺失信息", "标准结果", "文本", "-"),
)


def _header_key(value: object) -> str:
    return re.sub(r"[\s\r\n（）()\[\]【】]", "", str(value or "")).strip()


def _shift_merged_ranges(sheet, start_col: int, amount: int) -> None:
    original = [str(item) for item in sheet.merged_cells.ranges]
    for item in list(sheet.merged_cells.ranges):
        sheet.unmerge_cells(str(item))
    for text in original:
        min_col, min_row, max_col, max_row = range_boundaries(text)
        if min_col >= start_col:
            min_col += amount
            max_col += amount
        elif max_col >= start_col:
            max_col += amount
        sheet.merge_cells(start_row=min_row, start_column=min_col, end_row=max_row, end_column=max_col)


def _insert_result_columns(sheet) -> None:
    headers = [sheet.cell(3, col).value for col in range(1, sheet.max_column + 1)]
    photo_col = next((index + 1 for index, value in enumerate(headers) if "铭牌照片" in _header_key(value)), None)
    if photo_col is None:
        raise ValueError(f"{sheet.title}缺少铭牌照片列")
    if any(_header_key(value) == "采用标准" for value in headers):
        return

    # 插入前先保存被移动列的宽度与样式来源。
    source_col = max(1, photo_col - 1)
    source_width = sheet.column_dimensions[get_column_letter(source_col)].width
    _shift_merged_ranges(sheet, photo_col, len(COMMON_FIELDS))
    sheet.insert_cols(photo_col, len(COMMON_FIELDS))
    for offset, (_, display, *_rest) in enumerate(COMMON_FIELDS):
        col = photo_col + offset
        letter = get_column_letter(col)
        sheet.column_dimensions[letter].width = max(source_width or 12, 16 if display != "判定说明" else 28)
        for row in range(1, sheet.max_row + 1):
            source = sheet.cell(row, source_col)
            target = sheet.cell(row, col)
            if source.has_style:
                target._style = copy(source._style)
            if source.number_format:
                target.number_format = source.number_format
            target.alignment = copy(source.alignment)
            target.protection = copy(source.protection)
        sheet.cell(3, col).value = display
        # 所有统一结果字段均由引擎生成，不开放编辑。
        locked = copy(sheet.cell(3, col).protection)
        locked.locked = True
        sheet.cell(3, col).protection = locked

    # 第2行增加独立的“标准结果”分组，不与原有合并区域重叠。
    sheet.merge_cells(start_row=2, start_column=photo_col, end_row=2, end_column=photo_col + len(COMMON_FIELDS) - 1)
    sheet.cell(2, photo_col).value = "标准结果"
    source_header = sheet.cell(2, source_col)
    for col in range(photo_col, photo_col + len(COMMON_FIELDS)):
        cell = sheet.cell(2, col)
        cell._style = copy(source_header._style)
        cell.alignment = copy(source_header.alignment)
        cell.protection = copy(source_header.protection)
    # 表格引用和列元数据必须同步扩展，否则Excel会把新增字段视为表外列。
    for table in sheet.tables.values():
        min_col, min_row, max_col, max_row = range_boundaries(table.ref)
        if max_col >= photo_col:
            max_col += len(COMMON_FIELDS)
        table.ref = f"{get_column_letter(min_col)}{min_row}:{get_column_letter(max_col)}{max_row}"
        columns = list(table.tableColumns)
        for offset, (_, display, *_rest) in enumerate(COMMON_FIELDS):
            columns.insert(photo_col - min_col - 1 + offset, TableColumn(id=0, name=display))
        for index, column in enumerate(columns, start=1):
            column.id = index
        table.tableColumns = columns


def _config_rows(workbook) -> None:
    config = workbook["配置"]
    existing = {
        (str(config.cell(row, 1).value or ""), str(config.cell(row, 2).value or ""))
        for row in range(2, config.max_row + 1)
    }
    for sheet_name in DEVICE_SHEETS:
        standard_code = ""
        # 采用标准会由评价结果写入；标准编号列仅作为字段来源说明。
        for field_id, display, group, data_type, unit in COMMON_FIELDS:
            if (sheet_name, field_id) in existing:
                continue
            row = config.max_row + 1
            config.cell(row, 1).value = sheet_name
            values = [
                sheet_name, field_id, display, group, data_type, unit, "否", "判定生成",
                "锁定结果列", None, None, None, "不清洗（由判定引擎生成）",
                "判定失败或缺失时由引擎写入；不改写输入", standard_code, "判定结果",
            ]
            for col, value in enumerate(values, start=1):
                config.cell(row, col).value = value
            for col in range(1, 17):
                config.cell(row, col).protection = copy(config.cell(2, col).protection)


def patch(path: Path = TEMPLATE) -> Path:
    workbook = load_workbook(path)
    for sheet_name in DEVICE_SHEETS:
        _insert_result_columns(workbook[sheet_name])
    _config_rows(workbook)
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    workbook.calculation.calcMode = "auto"
    workbook.save(path)
    return path


if __name__ == "__main__":
    print(patch())
