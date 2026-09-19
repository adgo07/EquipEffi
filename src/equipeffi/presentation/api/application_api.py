from __future__ import annotations

from datetime import date
from typing import Any

from ...application.services.evaluation_facade import EvaluationFacade, EvaluationRequest
from ...application.services.schema_constraints import fallback_field_metadata
from ...application.services.v4_template_contract import V4TemplateContract
from ...domain.common.enums import Conclusion, EliminationScope
from ...domain.evaluation.device_specs import ENUM_VALUES, get_device_spec
from ...domain.evaluation.device_types import PUBLIC_DEVICE_NAMES, PUBLIC_TYPE_BY_SHEET, profiles_for_public_type, public_device_types
from ...domain.evaluation.metadata import get_device_profile
from ..metadata_projection import (
    MetadataProjectionError,
    metadata_fallback_input_payloads,
    project_input_payloads,
)


class ApiRequestError(ValueError):
    """窗口、HTTP或移动端请求不符合公共接口。"""


# 结论允许值是公共接口的一部分。把它放在API schema中，展示层无需复制
# 设备差异，也不会把普通三级设备误显示成五级或鼓风机专用结论。
_COMMON_CONCLUSIONS = [
    Conclusion.OUT_OF_SCOPE.value,
    Conclusion.UNABLE_TO_JUDGE.value,
    Conclusion.ELIMINATED.value,
    Conclusion.NOT_COMPLIANT.value,
]
_THREE_LEVEL_CONCLUSIONS = [Conclusion.LEVEL_3.value, Conclusion.LEVEL_2.value, Conclusion.LEVEL_1.value]
_CONCLUSIONS_BY_PUBLIC_TYPE = {
    "blower": _COMMON_CONCLUSIONS + [Conclusion.SAVING_VALUE.value, Conclusion.LIMIT_VALUE.value],
    "heat_treatment": _COMMON_CONCLUSIONS + [Conclusion.FIRST_CLASS.value, Conclusion.SECOND_CLASS.value, Conclusion.THIRD_CLASS.value],
    "heat_pump_water_heater": _COMMON_CONCLUSIONS + [
        Conclusion.LEVEL_1.value,
        Conclusion.LEVEL_2.value,
        Conclusion.LEVEL_3.value,
        Conclusion.LEVEL_4.value,
        Conclusion.LEVEL_5.value,
    ],
}

# 这些是公共API/网页表单的扩展输入，不属于V4工作簿列，因此不会改变
# Excel契约或写回字段。它们用于表达标准要求但模板暂未设列的计算辅助值。
_PUBLIC_INPUT_EXTENSIONS = {
    "blower": [
        {
            "field_id": "stage_efficiencies",
            "display_name": "各级多变效率",
            "group": "计算辅助结果",
            "data_type": "文本",
            "unit": "%",
            "editable": True,
            "required": "可选",
            "validation": "多级鼓风机可填列表或逗号/分号分隔值；数量必须等于级数，各项1～100",
            "minimum": 1,
            "maximum": 100,
            "enum_name": "",
            "enum_values": [],
            "extension": True,
        },
    ],
}


def public_input_extensions(public_code: str) -> list[dict[str, Any]]:
    """Return presentation-only input extensions for one public device type.

    These fields are deliberately kept outside the V4 workbook contract.  The
    helper gives desktop and other presentation layers the same extension
    metadata as the Web/JSON schema without importing the Excel adapter or
    copying the definition of fields such as a blower's stage efficiencies.
    """

    return [dict(item) for item in _PUBLIC_INPUT_EXTENSIONS.get(str(public_code), ())]


def _fallback_schema_fields(public_code: str) -> list[dict[str, Any]]:
    """Build a dependency-free form schema when the V4 workbook is unavailable.

    The normal packaged path reads the V4 contract.  A damaged/missing template
    must not leave Web/Android clients with an empty form, though: the internal
    profile specs are deliberately kept as a small fallback contract.  Shared
    public types merge their profile fields by field ID while preserving the
    first profile's display metadata.
    """

    fields: list[dict[str, Any]] = []
    seen: set[str] = set()
    # 回退schema的枚举展示与自动备注校验共用领域元数据；当前只有已
    # 通过契约测试的规则族会返回非空枚举，其他设备保持原有形状。
    metadata_profile = get_device_profile(public_code)

    # Keep the dependency-free fallback aligned with the V4 common prefix.
    # Without this prefix a missing/corrupt workbook would leave the manual
    # form unable to capture the identity, quantity or nameplate attachment
    # that the normal contract exposes.
    common_fields = (
        ("device_name", "设备名称", "文本", "-", False, "缺失时在自动备注中提示"),
        ("model", "型号", "文本", "-", False, "用于标准匹配和淘汰目录匹配"),
        ("quantity", "数量", "整数", "件", True, "应为正整数"),
        ("category", "设备类别", "文本", "-", True, "按标准枚举填写"),
        ("location", "安装位置", "文本", "-", False, "可选"),
        ("photo", "铭牌照片", "图片", "-", False, "使用置于单元格的铭牌照片"),
    )
    for field_id, display_name, data_type, unit, required, validation in common_fields:
        metadata = fallback_field_metadata(public_code, field_id)
        metadata_field = metadata_profile.field(field_id) if metadata_profile is not None else None
        fields.append({
            "field_id": field_id,
            "display_name": display_name,
            "group": "基础信息",
            "data_type": data_type,
            "unit": unit,
            "editable": True,
            "required": "必填" if required else "可选",
            "validation": validation or metadata["validation"],
            "minimum": metadata["minimum"],
            "maximum": metadata["maximum"],
            "enum_name": metadata_field.enum_name if metadata_field is not None else "",
            "enum_values": list(metadata_field.enum_values) if metadata_field is not None else [],
        })
        seen.add(field_id)
    profiles = profiles_for_public_type(public_code) or (public_code,)
    for profile in profiles:
        try:
            spec = get_device_spec(profile)
        except KeyError:
            continue
        for item in spec.get("fields", ()):
            field_id = str(item.get("name", ""))
            if not field_id or field_id in seen:
                continue
            seen.add(field_id)
            unit = str(item.get("unit", "-"))
            metadata = fallback_field_metadata(public_code, field_id)
            metadata_field = metadata_profile.field(field_id) if metadata_profile is not None else None
            # Lists such as blower stage_efficiencies are entered as text even
            # though each element has a percentage unit.  For finite numeric
            # fields, use the shared metadata type so a missing V4 workbook
            # cannot turn a numeric input into a text box.
            data_type = "文本" if field_id in {"stage_efficiencies"} or unit in {"", "-", "No."} else "数值"
            if metadata_field is not None:
                data_type = {
                    "text": "文本",
                    "number": "数值",
                    "integer": "整数",
                    "percentage": "数值",
                    "image": "图片",
                }.get(metadata_field.data_type, data_type)
            note = str(item.get("note", "") or "")
            validation = note
            if metadata["validation"] and metadata["validation"] not in note:
                validation = f"{note}；{metadata['validation']}" if note else metadata["validation"]
            payload = {
                "field_id": field_id,
                "display_name": str(item.get("label", field_id)),
                "group": "设备参数",
                "data_type": data_type,
                "unit": unit,
                "editable": True,
                "required": "必填" if item.get("required", True) else "可选",
                "validation": validation,
                "minimum": metadata["minimum"],
                "maximum": metadata["maximum"],
                "enum_name": (
                    metadata_field.enum_name
                    if metadata_field is not None and metadata_field.enum_name
                    else str(item.get("enum_name", "") or "")
                ),
                "enum_values": (
                    list(metadata_field.enum_values)
                    if metadata_field is not None and metadata_field.enum_values
                    else list(ENUM_VALUES.get(str(item.get("enum_name", "") or ""), ()))
                ),
            }
            if metadata.get("conditional_limits"):
                payload["conditional_limits"] = metadata["conditional_limits"]
            fields.append(payload)
    # A few V4 columns are public inputs but were never represented in the
    # legacy internal specs (for example duct_ac's enthalpy type).  Add only
    # those metadata-registered, V4-mapped fields and keep the old fallback
    # fields/JSON shape otherwise unchanged.
    for payload in metadata_fallback_input_payloads(public_code, seen):
        fields.append(payload)
        seen.add(payload["field_id"])
    return fields


_FALLBACK_RESULT_FIELDS: dict[str, tuple[tuple[str, str, str, str], ...]] = {
    # (字段ID, 显示名称, 字段分组, 单位)。这些ID与V4配置sheet保持一致，
    # 让无模板时的公共schema仍能表达查表/计算结果的锁定列。
    "transformer": (
        ("no_load_1", "空载损耗-1级", "标准查询结果", "W"),
        ("no_load_2", "空载损耗-2级", "标准查询结果", "W"),
        ("no_load_3", "空载损耗-3级", "标准查询结果", "W"),
        ("load_1", "负载损耗-1级", "标准查询结果", "W"),
        ("load_2", "负载损耗-2级", "标准查询结果", "W"),
        ("load_3", "负载损耗-3级", "标准查询结果", "W"),
    ),
    "motor": (("grade1", "1级对应效率指标", "标准查询结果", "%"), ("grade2", "2级对应效率指标", "标准查询结果", "%"), ("grade3", "3级对应效率指标", "标准查询结果", "%")),
    "compressor": (("sp1", "1级机组比功率", "标准查询结果", "kW/(m³/min)"), ("sp2", "2级机组比功率", "标准查询结果", "kW/(m³/min)"), ("sp3", "3级机组比功率", "标准查询结果", "kW/(m³/min)")),
    "centrifugal_pump": (
        ("specific_speed", "比转速", "计算辅助结果", "-"), ("c1", "C1", "计算辅助结果", "-"),
        ("c2", "C2", "计算辅助结果", "-"), ("c3", "C3", "计算辅助结果", "-"),
        ("base_efficiency", "基准效率", "计算辅助结果", "%"), ("correction", "效率修正值", "计算辅助结果", "%"),
        ("specified_efficiency", "规定点效率", "计算辅助结果", "%"),
        ("grade1", "1级效率", "标准查询结果", "%"), ("grade2", "2级效率", "标准查询结果", "%"), ("grade3", "3级效率", "标准查询结果", "%"),
    ),
    "centrifugal_fan": (
        ("compression_correction", "压缩性修正系数", "计算辅助结果", "-"), ("circum_speed", "叶轮圆周速度", "计算辅助结果", "m/s"),
        ("pressure_coefficient", "压力系数", "计算辅助结果", "-"), ("specific_speed", "比转速", "计算辅助结果", "-"),
        ("grade1", "1级效率", "标准查询结果", "%"), ("grade2", "2级效率", "标准查询结果", "%"), ("grade3", "3级效率", "标准查询结果", "%"),
    ),
    "axial_fan": (
        ("compression_correction", "压缩性修正系数", "计算辅助结果", "-"), ("pressure_coefficient", "压力系数", "计算辅助结果", "-"),
        ("specific_speed", "轮毂比标准分档", "计算辅助结果", "-"),
        ("grade1", "1级效率", "标准查询结果", "%"), ("grade2", "2级效率", "标准查询结果", "%"), ("grade3", "3级效率", "标准查询结果", "%"),
    ),
    "blower": (("b2_d2", "b₂/D₂", "计算辅助结果", "-"), ("limit_value", "能效限定值", "标准查询结果", "%"), ("saving_value", "节能评价值", "标准查询结果", "%")),
    "submersible_pump": (
        ("specified_eff", "规定效率", "计算辅助结果", "%"), ("tolerance", "效率容差", "计算辅助结果", "%"),
        ("grade1", "1级效率", "标准查询结果", "%"), ("grade2", "2级效率", "标准查询结果", "%"), ("grade3", "3级效率", "标准查询结果", "%"),
    ),
    "industrial_boiler": (("grade1", "1级热效率", "标准查询结果", "%"), ("grade2", "2级热效率", "标准查询结果", "%"), ("grade3", "3级热效率", "标准查询结果", "%")),
    "heat_treatment": (
        ("fuel_factor", "燃料系数", "计算辅助结果", "-"), ("electric_specific", "电炉可比单耗", "计算辅助结果", "kW·h/t"),
        ("fuel_specific", "燃料炉可比单耗", "计算辅助结果", "kgce/t"),
        ("grade_a", "一等指标", "标准查询结果", "按炉型"), ("grade_b", "二等指标", "标准查询结果", "按炉型"), ("grade_c", "三等指标", "标准查询结果", "按炉型"),
    ),
    "heat_pump_chiller": (
        ("primary_metric_name", "分级指标名称（自动）", "设备参数", "-"), ("aux_metric1_name", "辅助约束指标1名称（自动）", "设备参数", "-"),
        ("aux_metric2_name", "辅助约束指标2名称（自动）", "设备参数", "-"), ("standard_table", "适用标准表（自动）", "计算辅助结果", "-"),
        ("capacity_band", "容量分档（自动）", "计算辅助结果", "-"), ("primary_l1", "1级标准值", "标准查询结果", "无量纲"),
        ("primary_l2", "2级标准值", "标准查询结果", "无量纲"), ("primary_l3", "3级标准值", "标准查询结果", "无量纲"),
    ),
    "heat_pump_water_heater": tuple((f"cop{level}", f"{level}级性能系数", "标准查询结果", "W/W") for level in range(1, 6)),
    "duct_ac": (
        ("indicator_name", "设计指标名称", "设备参数", "-"), ("indicator_unit", "设计指标单位", "设备参数", "-"),
        ("level1", "1级对应指标", "标准查询结果", "按指标"), ("level2", "2级对应指标", "标准查询结果", "按指标"), ("level3", "3级对应指标", "标准查询结果", "按指标"),
    ),
    "unitary_ac": (
        ("indicator_name", "设计指标名称", "设备参数", "-"), ("indicator_unit", "设计指标单位", "设备参数", "-"),
        ("level1", "1级对应指标", "标准查询结果", "按指标"), ("level2", "2级对应指标", "标准查询结果", "按指标"), ("level3", "3级对应指标", "标准查询结果", "按指标"),
    ),
    "multi_split_ac": (
        ("primary_metric_name", "分级指标名称（自动）", "设备参数", "-"), ("standard_table", "适用标准表（自动）", "计算辅助结果", "-"),
        ("capacity_band", "容量分档（自动）", "计算辅助结果", "-"), ("query_metric_name", "分级查询指标（自动）", "标准查询结果", "-"),
        ("primary_l1", "分级指标1级标准值", "标准查询结果", "无量纲"), ("primary_l2", "分级指标2级标准值", "标准查询结果", "无量纲"), ("primary_l3", "分级指标3级标准值", "标准查询结果", "无量纲"),
        ("eer_min_l1", "EERmin 1级标准值", "标准查询结果", "W/W"), ("eer_min_l2", "EERmin 2级标准值", "标准查询结果", "W/W"), ("eer_min_l3", "EERmin 3级标准值", "标准查询结果", "W/W"),
        ("cop_minus12_limit", "COP(-12℃)最低标准值", "标准查询结果", "W/W"), ("cop_minus20_limit", "COP(-20℃)最低标准值", "标准查询结果", "W/W"),
    ),
}


def _fallback_result_fields(public_code: str) -> list[dict[str, Any]]:
    """Return the V4-compatible locked result contract without requiring Excel."""

    definitions = [("seq", "序号", "基础信息", "-")]
    definitions.extend(_FALLBACK_RESULT_FIELDS.get(public_code, ()))
    conclusion_label = "能效结论" if public_code == "blower" else "评价等级" if public_code == "heat_treatment" else "能效等级"
    definitions.extend((("conclusion", conclusion_label, "结论", "-"), ("auto_note", "自动备注", "附件备注", "-")))
    definitions.extend((
        ("standard_code", "采用标准", "标准结果", "-"),
        ("standard_table", "匹配表/条款", "标准结果", "-"),
        ("reference_grade", "参考能效等级", "标准结果", "-"),
        ("explanation", "判定说明", "标准结果", "-"),
        ("missing_fields", "缺失信息", "标准结果", "-"),
    ))
    # 个别V4设备（例如热泵和冷水机组、多联式空调）把standard_table
    # 作为专属计算辅助结果显式列出；公共结果尾部仍需提供它的同一字段，
    # 但不能在回退schema中重复输出相同ID。
    unique_definitions: list[tuple[str, str, str, str]] = []
    seen: set[str] = set()
    for definition in definitions:
        if definition[0] in seen:
            continue
        seen.add(definition[0])
        unique_definitions.append(definition)
    return [
        {
            "field_id": field_id,
            "display_name": label,
            "group": group,
            "data_type": "数值" if unit not in {"", "-", "按指标"} else "文本",
            "unit": unit,
            "editable": False,
            "required": "判定生成",
            "validation": "由评价服务生成并锁定",
            "minimum": None,
            "maximum": None,
            "enum_name": "",
            "enum_values": [],
        }
        for field_id, label, group, unit in unique_definitions
    ]


def _metadata_schema_fields(
    public_code: str,
    device_type: str,
    contract: V4TemplateContract | None,
) -> tuple[list[dict[str, Any]], str]:
    """Build one public device input view from the unified metadata registry.

    When the V4 contract is loaded, its payload remains the presentation
    contract (including exact validation text and enum values), while metadata
    supplies the canonical-to-V4 mapping and the expected editable order.  The
    helper name is retained for compatibility with the first transformer pilot;
    the implementation is now deliberately device-agnostic.  In fallback mode
    the old payload is returned unchanged after the same coverage check, so
    callers do not observe a schema-shape migration merely because the
    template is unavailable.
    """

    profile = get_device_profile(public_code)
    if contract is None:
        try:
            fields = project_input_payloads(
                public_code, _fallback_schema_fields(public_code), mode="fallback",
                context=f"{device_type}回退",
            )
        except MetadataProjectionError as exc:
            raise ApiRequestError(str(exc)) from exc
        return fields, "fallback"

    schema = contract.schema_for_public_type(device_type)
    try:
        projected = project_input_payloads(
            public_code, schema["fields"], mode="v4", context=f"{device_type}V4"
        )
    except MetadataProjectionError as exc:
        raise ApiRequestError(str(exc)) from exc
    return projected, "v4"


class ApplicationApi:
    """无框架的应用API门面；未来可直接包装为FastAPI、WebSocket或安卓HTTP服务。"""

    def __init__(self, facade: EvaluationFacade, contract: V4TemplateContract | None = None):
        self.facade = facade
        self.contract = contract

    def device_types(self) -> list[dict[str, str]]:
        return list(public_device_types())

    def status(self) -> dict[str, Any]:
        """Return a dependency-free capability/status snapshot.

        Mobile or service clients can use this before rendering a form: it makes
        inactive standard packs and the currently available elimination catalog
        explicit without importing Excel or the desktop layer.
        """

        service = self.facade.evaluation_service
        standards = service.standards
        packs = standards.list_packs() if hasattr(standards, "list_packs") else ()
        elimination = service.elimination
        return {
            "public_device_type_count": len(PUBLIC_DEVICE_NAMES),
            "public_device_types": [item["code"] for item in self.device_types()],
            "standard_packs": [
                {
                    "device_type": item.get("device_type", ""),
                    "pack_id": item.get("pack_id", ""),
                    "standard_code": item.get("standard_code", ""),
                    "effective_date": item.get("effective_date", ""),
                    "status": item.get("status", ""),
                    "data_version": item.get("data_version", ""),
                    "unavailable_reason": item.get("unavailable_reason", ""),
                }
                for item in packs
            ],
            "elimination": {
                "has_industry_catalog": bool(getattr(elimination, "has_industry_catalog", False)),
                "industry_catalog_complete": bool(getattr(elimination, "industry_catalog_complete", False)),
                "entry_count": len(getattr(elimination, "entries", ())),
                "source_entry_count": int(getattr(elimination, "source_entry_count", len(getattr(elimination, "entries", ())))),
                "industry_source_item_count": int(getattr(elimination, "industry_source_item_count", 0)),
                "industry_resource_rule_count": int(getattr(
                    elimination,
                    "industry_resource_rule_count",
                    sum(1 for entry in getattr(elimination, "entries", ()) if not getattr(entry, "batch", "")),
                )),
                "review_only_entry_count": int(getattr(elimination, "review_only_entry_count", 0)),
                "catalog_status": str(getattr(elimination, "catalog_status", "")),
                "industry_catalog_status": str(getattr(elimination, "industry_catalog_status", "")),
                "data_version": str(getattr(elimination, "catalog_data_version", "")),
                "scope_options": [item.value for item in EliminationScope],
                "default_scope": EliminationScope.MOTOR_BATCHES_1_4.value,
                "available_scope": (
                    "产业结构调整指导目录（设备相关条目已按PDF核对、非全文）+高耗能落后机电设备淘汰目录第一至第四批"
                    if getattr(elimination, "has_industry_catalog", False)
                    else "高耗能落后机电设备淘汰目录第一至第四批"
                ),
            },
        }

    def schema(self, device_type: str) -> dict[str, Any]:
        public_code = PUBLIC_TYPE_BY_SHEET.get(str(device_type), str(device_type))
        if public_code not in PUBLIC_DEVICE_NAMES:
            raise ApiRequestError(f"未知公共设备类型: {device_type}")
        projected_fields, _schema_source = _metadata_schema_fields(
            public_code, device_type, self.contract
        )

        if self.contract is None:
            schema = {
                "device_type": device_type,
                "fields": projected_fields,
                "result_fields": _fallback_result_fields(public_code),
                "note": "V4字段契约尚未加载，当前使用内部profile回退字段；标准结果字段仍由判定结果返回",
            }
        else:
            schema = self.contract.schema_for_public_type(device_type)
            # The helper has already projected/validated the loaded V4 fields;
            # assigning the list here keeps the rest of this method (extensions,
            # conclusions and profile status) shared for all 15 public types.
            schema["fields"] = projected_fields
        schema["extensions"] = public_input_extensions(public_code)
        schema["allowed_conclusions"] = list(_CONCLUSIONS_BY_PUBLIC_TYPE.get(public_code, _COMMON_CONCLUSIONS + _THREE_LEVEL_CONCLUSIONS))
        # V4 uses device-specific labels for the final result column.  Keep
        # the label in the public contract so Web/desktop/Android clients do
        # not have to infer it from the conclusion set or duplicate the
        # workbook's wording.
        schema["conclusion_field"] = (
            "能效结论" if public_code == "blower"
            else "评价等级" if public_code == "heat_treatment"
            else "能效等级"
        )
        packs = self.facade.evaluation_service.standards.list_packs()
        packs_by_type = {str(item.get("device_type", "")): item for item in packs}
        schema["internal_profiles"] = [
            {
                "device_type": profile,
                "pack_id": packs_by_type.get(profile, {}).get("pack_id", ""),
                "standard_code": packs_by_type.get(profile, {}).get("standard_code", ""),
                "status": packs_by_type.get(profile, {}).get("status", ""),
                "unavailable_reason": packs_by_type.get(profile, {}).get("unavailable_reason", ""),
            }
            for profile in profiles_for_public_type(public_code)
        ]
        return schema

    def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ApiRequestError("判定请求必须是对象")
        device_type = payload.get("device_type")
        if not device_type:
            raise ApiRequestError("缺少公共设备类型device_type")
        values = payload.get("values", {})
        if not isinstance(values, dict):
            raise ApiRequestError("values必须是对象")
        result = self.facade.evaluate(EvaluationRequest(
            record_id=str(payload.get("record_id", "API-001")),
            device_type=str(device_type),
            values=dict(values),
            source=str(payload.get("source", "api")),
            template_id=str(payload.get("template_id", "")),
            as_of=self._as_of(payload),
        ), elimination_scope=self._scope(payload))
        return self.facade.to_record(result)

    def evaluate_batch(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Evaluate a JSON batch without coupling callers to Excel.

        The batch contract deliberately mirrors the single-record endpoint:
        ``{"records": [{"record_id", "device_type", "values"}]}``.
        Keeping this at the public API boundary lets a future Excel, HTTP or
        Android adapter submit rows without importing the desktop or OOXML
        layers.  A malformed record is rejected instead of silently skipping
        it, so callers can safely correlate every response with its input.
        """

        if not isinstance(payload, dict):
            raise ApiRequestError("批量判定请求必须是对象")
        records = payload.get("records")
        if not isinstance(records, list):
            raise ApiRequestError("records必须是数组")
        scope = self._scope(payload)
        results: list[dict[str, Any]] = []
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                raise ApiRequestError(f"records[{index}]必须是对象")
            device_type = record.get("device_type")
            values = record.get("values", {})
            if not device_type:
                raise ApiRequestError(f"records[{index}]缺少公共设备类型device_type")
            if not isinstance(values, dict):
                raise ApiRequestError(f"records[{index}].values必须是对象")
            results.append(self.facade.to_record(self.facade.evaluate(
                EvaluationRequest(
                    record_id=str(record.get("record_id", f"BATCH-{index + 1:04d}")),
                    device_type=str(device_type),
                    values=dict(values),
                    source=str(record.get("source", payload.get("source", "api_batch"))),
                    template_id=str(record.get("template_id", payload.get("template_id", ""))),
                    as_of=self._as_of(record, default=self._as_of(payload)),
                ),
                elimination_scope=scope,
            )))
        return results

    def evaluate_v4(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ApiRequestError("V4判定请求必须是对象")
        sheet = payload.get("sheet")
        values = payload.get("values", {})
        if not sheet:
            raise ApiRequestError("缺少V4工作表sheet")
        if not isinstance(values, dict):
            raise ApiRequestError("values必须是对象")
        result = self.facade.evaluate_v4(
            str(payload.get("record_id", "V4-API-001")),
            str(sheet),
            dict(values),
            elimination_scope=self._scope(payload),
            as_of=self._as_of(payload),
        )
        return self.facade.to_record(result)

    @staticmethod
    def _scope(payload: dict[str, Any]) -> EliminationScope:
        try:
            return EliminationScope(payload.get("elimination_scope", EliminationScope.MOTOR_BATCHES_1_4.value))
        except ValueError as exc:
            raise ApiRequestError(f"淘汰目录口径无效: {payload.get('elimination_scope')}") from exc

    @staticmethod
    def _as_of(payload: dict[str, Any], *, default: date | str = date(2026, 8, 23)) -> date:
        """Parse the ISO date used as the reproducible evaluation baseline."""

        value = payload.get("as_of", default)
        if value in (None, ""):
            value = default
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except (TypeError, ValueError) as exc:
            raise ApiRequestError(f"判定基准日期as_of无效: {value}") from exc
