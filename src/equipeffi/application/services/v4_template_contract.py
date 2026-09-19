from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from ...domain.evaluation.device_types import PUBLIC_DEVICE_NAMES, PUBLIC_TYPE_BY_SHEET


V4_TEMPLATE_ID = "v4_20260825"
V4_TEMPLATE_NAME = "设备能效分析空白模板_重构版V4_20260825.xlsx"
V4_DEVICE_SHEETS: tuple[str, ...] = tuple(PUBLIC_DEVICE_NAMES.values())

# 这类约束无法用单一minimum/maximum表达，作为公共schema元数据返回，
# 让Web/桌面等展示层可以即时提示；最终仍由V4ValidationService再次校验。
CONDITIONAL_LIMITS: dict[tuple[str, str], tuple[dict[str, Any], ...]] = {
    ("工业锅炉", "design_efficiency"): (
        {
            "when": {"field": "category", "equals": "室燃燃烧锅炉（燃气冷凝）"},
            "minimum": 1,
            "maximum": 110,
        },
        {"when": "otherwise", "minimum": 1, "maximum": 100},
    ),
}


@dataclass(frozen=True)
class V4FieldDefinition:
    sheet: str
    field_id: str
    display_name: str
    group: str
    data_type: str
    unit: str
    editable: bool
    required: str
    validation: str
    minimum: Any = None
    maximum: Any = None
    enum_name: str = ""

    @property
    def is_input(self) -> bool:
        return self.editable


class V4TemplateContractError(ValueError):
    """V4模板契约行无法解析或不完整。"""


def _bool_editable(value: Any) -> bool:
    return str(value).strip() in {"是", "是（可编辑）", "true", "True", "1"}


def _row_value(row: Mapping[str, Any] | list[Any] | tuple[Any, ...], key: str, index: int) -> Any:
    if isinstance(row, Mapping):
        aliases = {
            "sheet": ("sheet", "工作表"),
            "field_id": ("field_id", "id", "字段ID"),
            "display_name": ("display_name", "name", "显示名称"),
            "group": ("group", "字段分组"),
            "data_type": ("data_type", "type", "数据类型"),
            "unit": ("unit", "单位"),
            "editable": ("editable", "是否可编辑"),
            "required": ("required", "必填条件"),
            "validation": ("validation", "验证规则"),
            "enum_name": ("enum_name", "enumName", "枚举集合"),
            "minimum": ("minimum", "min", "最小值"),
            "maximum": ("maximum", "max", "最大值"),
        }.get(key, (key,))
        for candidate in aliases:
            if candidate in row:
                return row[candidate]
        return None
    return row[index] if len(row) > index else None


@dataclass(frozen=True)
class V4TemplateContract:
    """V4字段契约。

    Excel读取器只负责把“配置”sheet转换为config rows；界面和写回器均通过本类读取字段，
    不直接依赖列号或内部17类评价器名称。
    """

    template_id: str = V4_TEMPLATE_ID
    template_name: str = V4_TEMPLATE_NAME
    fields: tuple[V4FieldDefinition, ...] = ()
    enums: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @classmethod
    def from_config_rows(
        cls,
        rows: Iterable[Mapping[str, Any] | list[Any] | tuple[Any, ...]],
        *,
        template_id: str = V4_TEMPLATE_ID,
        template_name: str = V4_TEMPLATE_NAME,
    ) -> "V4TemplateContract":
        fields: list[V4FieldDefinition] = []
        enum_values: dict[str, list[str]] = {}
        for row_number, row in enumerate(rows, start=1):
            sheet = _row_value(row, "sheet", 0)
            field_id = _row_value(row, "field_id", 1)
            display_name = _row_value(row, "display_name", 2)
            if not sheet or not field_id or not display_name:
                raise V4TemplateContractError(f"V4配置第{row_number}行缺少sheet、字段ID或显示名称")
            if str(sheet) not in V4_DEVICE_SHEETS and str(sheet) not in {"注意事项", "模板说明", "配置"}:
                raise V4TemplateContractError(f"V4配置第{row_number}行存在未知sheet: {sheet}")
            for key, value in (row.items() if isinstance(row, Mapping) else ()):
                if key.startswith("EV_") and value not in (None, ""):
                    text = str(value)
                    if text not in enum_values.setdefault(key, []):
                        enum_values[key].append(text)
            fields.append(V4FieldDefinition(
                sheet=str(sheet),
                field_id=str(field_id),
                display_name=str(display_name),
                group=str(_row_value(row, "group", 3) or ""),
                data_type=str(_row_value(row, "data_type", 4) or "文本"),
                unit=str(_row_value(row, "unit", 5) or "-"),
                editable=_bool_editable(_row_value(row, "editable", 6)),
                required=str(_row_value(row, "required", 7) or ""),
                validation=str(_row_value(row, "validation", 8) or ""),
                minimum=_row_value(row, "minimum", 9),
                maximum=_row_value(row, "maximum", 10),
                enum_name=str(_row_value(row, "enum_name", 11) or ""),
            ))
        return cls(
            template_id=template_id,
            template_name=template_name,
            fields=tuple(fields),
            enums={key: tuple(values) for key, values in enum_values.items()},
        )

    def validate(self) -> list[str]:
        issues: list[str] = []
        sheets = {field.sheet for field in self.fields}
        for sheet in V4_DEVICE_SHEETS:
            if sheet not in sheets:
                issues.append(f"缺少设备sheet字段契约: {sheet}")
        duplicate_ids = {(field.sheet, field.field_id) for field in self.fields}
        if len(duplicate_ids) != len(self.fields):
            issues.append("存在重复的sheet+字段ID")
        return issues

    def fields_for_sheet(self, sheet_name: str, *, editable_only: bool = False) -> tuple[V4FieldDefinition, ...]:
        fields = tuple(field for field in self.fields if field.sheet == sheet_name)
        if editable_only:
            fields = tuple(field for field in fields if field.editable)
        return fields

    def fields_for_public_type(self, public_device_type: str, *, editable_only: bool = False) -> tuple[V4FieldDefinition, ...]:
        try:
            sheet = PUBLIC_DEVICE_NAMES[public_device_type]
        except KeyError as exc:
            sheet = public_device_type if public_device_type in PUBLIC_TYPE_BY_SHEET else ""
            if not sheet:
                raise V4TemplateContractError(f"未知V4公共设备类型: {public_device_type}") from exc
        return self.fields_for_sheet(sheet, editable_only=editable_only)

    def schema_for_public_type(self, public_device_type: str) -> dict[str, Any]:
        # 输入字段和锁定结果字段同时公开：展示层只把 ``fields`` 渲染为
        # 可编辑表单，而移动端/Excel适配器可以通过 ``result_fields`` 获知
        # 标准查询结果、判定说明和自动备注等写回列，不必复制V4列定义。
        all_fields = self.fields_for_public_type(public_device_type, editable_only=False)
        fields = tuple(field for field in all_fields if field.editable)
        result_fields = tuple(field for field in all_fields if not field.editable)

        def field_payload(field: V4FieldDefinition) -> dict[str, Any]:
            payload = {
                "field_id": field.field_id,
                "display_name": field.display_name,
                "group": field.group,
                "data_type": field.data_type,
                "unit": field.unit,
                "editable": field.editable,
                "required": field.required,
                "validation": field.validation,
                "minimum": field.minimum,
                "maximum": field.maximum,
                "enum_name": field.enum_name,
                "enum_values": list(self.enums.get(field.enum_name, ())),
            }
            if (field.sheet, field.field_id) in CONDITIONAL_LIMITS:
                payload["conditional_limits"] = [
                    dict(rule) for rule in CONDITIONAL_LIMITS[(field.sheet, field.field_id)]
                ]
            return payload

        return {
            "template_id": self.template_id,
            "template_name": self.template_name,
            "device_type": public_device_type,
            "sheet": PUBLIC_DEVICE_NAMES.get(public_device_type, public_device_type),
            "fields": [field_payload(field) for field in fields],
            "result_fields": [field_payload(field) for field in result_fields],
        }
