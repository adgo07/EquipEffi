from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from ...application.ports.v4_workbook import V4WorkbookReader, V4WorkbookRow
from ...application.services.v4_template_contract import V4TemplateContract, V4_DEVICE_SHEETS
from ...domain.common.enums import EliminationScope
from .ooxml_reader import OOXMLReadError, OOXMLWorkbook
from .template_resource import V4TemplateResource


def _header_name(value: Any) -> str:
    text = str(value or "").replace("\r", "").strip()
    return text.split("\n", 1)[0].strip()


def _is_empty(value: Any) -> bool:
    return value in (None, "")


class V4WorkbookReaderImpl(V4WorkbookReader):
    """读取V4配置字段和设备数据行的只读实现。

    输入行仍保留V4字段ID；设备类型路由交给V4InputAdapter和判定服务。结果写回不在本类中执行。
    """

    def __init__(self, *, require_template_structure: bool = True):
        self.require_template_structure = require_template_structure

    def read_contract(self, source: Path) -> V4TemplateContract:
        with OOXMLWorkbook(source) as workbook:
            config_rows = workbook.rows("配置")
        if not config_rows:
            raise OOXMLReadError("V4配置sheet为空")
        headers = [_header_name(cell) for cell in config_rows[0]]
        rows: list[dict[str, Any]] = []
        for row in config_rows[1:]:
            values = {headers[index]: row[index] if index < len(row) else "" for index in range(len(headers)) if headers[index]}
            if not values.get("sheet") and not values.get("字段ID"):
                # 配置sheet的字段字典后面还包含同义词映射等辅助区；第一个空行是字段字典结束标记。
                if rows:
                    break
                continue
            if values.get("sheet") in V4_DEVICE_SHEETS and values.get("字段ID"):
                rows.append(values)
        contract = V4TemplateContract.from_config_rows(rows, template_name=source.name)
        issues = contract.validate()
        if issues:
            raise OOXMLReadError("V4配置契约不完整：" + "；".join(issues))
        return contract

    def read_rows(self, source: Path) -> tuple[V4WorkbookRow, ...]:
        source = Path(source)
        if self.require_template_structure:
            validation = V4TemplateResource().validate(source)
            if not validation.is_valid:
                raise OOXMLReadError(validation.message)
        contract = self.read_contract(source)
        records: list[V4WorkbookRow] = []
        with OOXMLWorkbook(source) as workbook:
            for sheet_name in V4_DEVICE_SHEETS:
                rows = workbook.rows(sheet_name)
                header_index = self._find_header_row(rows)
                if header_index is None:
                    raise OOXMLReadError(f"V4设备sheet缺少正式表头: {sheet_name}")
                header_map = self._header_map(rows[header_index])
                input_fields = contract.fields_for_sheet(sheet_name, editable_only=True)
                field_columns = {
                    field.field_id: header_map[_header_name(field.display_name)]
                    for field in input_fields
                    if _header_name(field.display_name) in header_map
                }
                # 技术记录ID是隐藏系统字段，不进入用户参数；如果结果工作簿或
                # 外部编辑器已经写入它，优先沿用该值以保持排序/回写后的轨迹关联。
                technical_id_column = header_map.get("技术记录ID")
                for row_number, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
                    values = {
                        field_id: row[column] if column < len(row) else ""
                        for field_id, column in field_columns.items()
                    }
                    if not any(not _is_empty(value) for value in values.values()):
                        continue
                    technical_id = ""
                    if technical_id_column is not None and technical_id_column < len(row):
                        technical_id = str(row[technical_id_column] or "").strip()
                    records.append(V4WorkbookRow(technical_id or f"{sheet_name}-{row_number}", sheet_name, values, row_number))
        return tuple(records)

    def read_settings(self, source: Path) -> dict[str, Any]:
        """读取工作簿级设置；当前只开放淘汰目录判定口径。"""
        with OOXMLWorkbook(Path(source)) as workbook:
            rows = workbook.rows("注意事项")
        for row in rows:
            if _header_name(row[0] if row else "") != "淘汰判定口径":
                continue
            value = str(row[1] if len(row) > 1 else "").strip()
            if not value:
                return {"elimination_scope": EliminationScope.MOTOR_BATCHES_1_4.value}
            try:
                return {"elimination_scope": EliminationScope(value).value}
            except ValueError as exc:
                raise OOXMLReadError(f"注意事项中的淘汰判定口径无效: {value}") from exc
        return {"elimination_scope": EliminationScope.MOTOR_BATCHES_1_4.value}

    @staticmethod
    def _find_header_row(rows: list[list[Any]]) -> int | None:
        for index, row in enumerate(rows[:10]):
            names = {_header_name(value) for value in row}
            if {"序号", "设备名称", "型号"}.issubset(names):
                return index
        return None

    @staticmethod
    def _header_map(row: list[Any]) -> dict[str, int]:
        mapping: dict[str, int] = {}
        for index, value in enumerate(row):
            name = _header_name(value)
            if name and name not in mapping:
                mapping[name] = index
        return mapping
