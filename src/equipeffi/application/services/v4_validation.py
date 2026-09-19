from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from ...domain.common.enums import IssueSeverity
from ...domain.common.issues import ValidationIssue
from ...domain.common.models import DeviceDraft
from ...domain.evaluation.metadata import get_device_profile
from .v4_input_adapter import V4_DEVICE_SHEETS


COMMON_REQUIRED = ("device_name", "model", "quantity", "category", "photo")
FIELD_LABELS = {
    "device_name": "设备名称",
    "model": "型号",
    "quantity": "数量",
    "category": "设备类别",
    "photo": "铭牌照片",
}
CONDITIONAL_FIELD_LABELS = {
    "product_standard": "产品标准",
    "unit_type": "机组型式",
    "source": "冷却/热源方式",
    "evaluation_system": "能效评价指标体系",
    "cooling": "冷却方式",
    "mode": "机组类型",
    "enthalpy": "焓差类型",
    "rated_power": "额定功率",
    "external_static": "机外静压",
    "primary_metric_value": "分级指标设计值",
    "indicator_value": "设计指标值",
}
POSITIVE_FIELDS: dict[str, tuple[str, ...]] = {
    "变压器": ("rated_capacity", "no_load_loss", "load_loss"),
    "电动机": ("rated_voltage", "rated_frequency", "rated_power", "poles", "rated_speed"),
    "空压机": ("input_power", "volume_flow", "discharge_pressure", "specific_power"),
    "离心泵": ("flow", "head", "speed", "power", "stages"),
    "离心通风机": ("flow", "fan_pressure", "outlet_stag_pressure", "inlet_stag_pressure", "rated_power", "impeller_power", "speed", "machine_no", "density", "isentropic_k"),
    "轴流通风机": ("flow", "fan_pressure", "rated_power", "impeller_power", "speed", "machine_no", "density", "isentropic_k"),
    "鼓风机": ("stages", "flow", "rated_power", "p1", "p2", "t1", "t2", "isentropic_k", "b2", "d2"),
    "潜水电泵": ("flow", "head", "speed", "power", "stages"),
    "工业锅炉": ("evaporation", "thermal_power", "lhv"),
    "热处理设备": ("rated_power", "rated_temperature", "equivalent_weight", "electricity", "fuel_consumption", "fuel_heat"),
    "热泵和冷水机组": (
        "cooling_capacity", "heating_capacity", "rated_power",
        "primary_metric_value", "aux_metric1_value", "aux_metric2_value",
        "indicator1_value", "indicator2_value", "indicator3_value", "indicator_value",
    ),
    "热泵热水机": ("heating_capacity", "rated_power", "cop"),
    "风管送风式空调": (
        "cooling_capacity", "rated_power", "indicator_value",
        "indicator1_value", "primary_metric_value",
    ),
    "单元式空调": (
        "cooling_capacity", "rated_power", "indicator_value",
        "indicator1_value", "primary_metric_value",
    ),
    "多联式空调": (
        "cooling_capacity", "heating_capacity", "rated_power", "primary_metric_value",
        "eer_min_value", "cop_minus12_value", "cop_minus20_value",
        "indicator1_value", "indicator2_value", "indicator3_value",
        # 机外静压>0时由引用标准取得的修正结果，不能为零或负值。
        "static_pressure_correction_factor", "static_pressure_corrected_metric",
    ),
}

# 模板中的“a～b”规则不能用单纯的正数检查代替；边界按标准含义取闭区间。
RANGE_FIELDS: dict[str, dict[str, tuple[Decimal, Decimal]]] = {
    "工业锅炉": {"vdaf": (Decimal(0), Decimal(100))},
    "潜水电泵": {"temperature": (Decimal(0), Decimal(100))},
    "离心通风机": {"isentropic_k": (Decimal(1), Decimal(2))},
    "轴流通风机": {"isentropic_k": (Decimal(1), Decimal(2)), "hub_ratio": (Decimal(0), Decimal(1))},
    "鼓风机": {"isentropic_k": (Decimal(1), Decimal(2))},
}

INTEGER_FIELDS: dict[str, tuple[str, ...]] = {
    "电动机": ("poles",),
    "离心泵": ("stages",),
    "潜水电泵": ("stages",),
    "鼓风机": ("stages",),
}

# 外静压允许为零（表示未增加外部静压），但不能为负。
NON_NEGATIVE_FIELDS: dict[str, tuple[str, ...]] = {
    # 潜水电泵的效率容差以百分点表示，标准允许为0，但不能为负。
    "潜水电泵": ("efficiency_tolerance",),
}


# 百分数本值字段：例如98%必须填写为98，而不是0.98。
# 同时保留中文表头/历史别名，便于旧版导入接口继续得到相同校验。
PERCENT_FIELDS = {
    "效率", "设计热效率", "设计风机效率", "多变效率", "泵效率", "电泵效率",
    "额定效率", "90%额定转速效率", "规定效率ηDB", "电动机效率",
    "efficiency", "rated_efficiency", "efficiency_at_90pct_speed", "specified_efficiency",
    "motor_efficiency", "design_efficiency", "fan_efficiency",
    "polytropic_efficiency", "pump_efficiency",
}
SEQUENCE_PERCENT_FIELDS = {"stage_efficiencies", "各级多变效率"}

# V4下拉框保存的是标准规范值，但兼容接口/历史表中存在少量明确的
# 说明性别名。别名只用于“是否为合法枚举”的质量检查，不会改写原始输入；
# 规范化副本仍由 input_normalization 负责。这样既保留下拉框的标准值，
# 又避免把已知合法写法误报为非法枚举。
V4_ENUM_ALIASES: dict[tuple[str, str], dict[str, str]] = {
    ("电动机", "category"): {
        "三相异步电动机（一般用途）": "三相异步电动机",
    },
    ("风管送风式空调", "category"): {
        # 公共API/领域输入使用内部短名称；V4契约使用标准全称。
        # 反向映射只用于合法性检查，不改写调用方原始输入。
        "风管送风式机组": "风管送风式空调（热泵）机组",
        "直接蒸发式全新风机组": "直接蒸发式全新风空气处理机组",
    },
    ("风管送风式空调", "cooling"): {
        "水冷式(水环式)": "水冷式（水环式）",
    },
    ("单元式空调", "category"): {
        # 旧内部profile把普通机组的冷却方式合并进标准类别；V4把
        # “普通单元式空调机”与冷却方式分列。这里只接受输入规范化中
        # 已有的确定组合，不放宽到模糊相似文本。
        "风冷式单元式空调机": "普通单元式空调机",
        "水冷式单元式空调机": "普通单元式空调机",
    },
    ("多联式空调", "category"): {
        # 兼容输入规范化中已有的确定短名称；不接受模糊的“多联机”等文本。
        "风冷单冷": "风冷式单冷型多联机",
        "风冷热泵": "风冷式热泵型多联机",
        "水冷": "水冷式多联机",
        "低温机组": "低温多联机",
    },
    ("潜水电泵", "category"): {
        "小型潜水电泵（QDX）": "小型潜水电泵",
        "小型潜水电泵（QD）": "小型潜水电泵",
    },
    ("潜水电泵", "device_form"): {
        "QDX": "QDX和QD",
        "QD": "QDX和QD",
        "QX": "QX和Q",
        "Q": "QX和Q",
        "混流式(蜗壳)": "混流式（蜗壳）",
        "混流式(导叶)": "混流式（导叶）",
        "其他": "其他（请备注说明）",
    },
    # 核心评价器使用简短的清水泵分类；V4下拉框保留标准全称。
    # 只登记已有输入规范化规则中的确定映射，不把模糊相似型号视为别名。
    ("离心泵", "category"): {
        "单级单吸": "单级单吸清水离心泵",
        "单级双吸": "单级双吸清水离心泵",
        "管道": "管道清水离心泵",
        "多级": "多级清水离心泵",
        "轻型多级立式": "轻型多级清水离心泵（立式）",
        "轻型多级卧式": "轻型多级清水离心泵（卧式）",
    },
    ("热泵热水机", "heating_method"): {
        "一次加热": "一次加热式",
        "循环加热": "循环加热式",
    },
}


def _present(value: Any) -> bool:
    return value not in (None, "")


def _number(value: Any) -> Decimal | None:
    if not _present(value):
        return None
    try:
        number = Decimal(str(value).strip())
        return number if number.is_finite() else None
    except (InvalidOperation, ValueError, AttributeError):
        return None


def _metadata_numeric_constraints(sheet_name: str) -> dict[str, tuple[str, ...]] | None:
    """Return numeric constraint fields for the metadata validation pilot.

    The transformer, motor, blower, fan, pump and heat-treatment numeric
    fields are the currently reviewed migrations.  The compressor,
    industrial-boiler and heat-pump-water-heater pilots are intentionally
    field-scoped (the four reviewed compressor fields ``input_power``,
    ``volume_flow``, ``discharge_pressure`` and ``specific_power``; boiler
    ``evaporation``, ``thermal_power`` and ``lhv``; and HPWH
    ``heating_capacity``, ``rated_power`` and ``cop``); duct/unitary-AC
    ``indicator_value``; and heat-pump/chiller
    ``rated_power``, ``cooling_capacity``, ``heating_capacity``,
    ``primary_metric_value``, ``aux_metric1_value`` and ``aux_metric2_value``),
    and multi-split AC's reviewed ``primary_metric_value`` and
    ``heating_capacity``, ``eer_min_value``, ``cop_minus12_value`` and
    ``cop_minus20_value`` fields)
    so adding one V4 rule
    cannot silently migrate other inputs.  The metadata records
    V4 IDs and numeric types; fields with a strict V4 lower-bound hint of zero
    are positive design values (the validator still applies ``> 0``), while
    integer and percentage types are kept separate.  Other sheets deliberately
    return ``None`` and continue using their existing rule tables until their
    own contract migration is reviewed.
    """

    if sheet_name not in {"变压器", "电动机", "空压机", "离心泵", "离心通风机", "轴流通风机", "鼓风机", "潜水电泵", "工业锅炉", "热处理设备", "热泵热水机", "热泵和冷水机组", "风管送风式空调", "单元式空调", "多联式空调"}:
        return None
    profile = get_device_profile(sheet_name)
    # Keep each newly reviewed device migration narrow. Existing reviewed
    # sheets use their complete mapped numeric surface; field-scoped sheets
    # opt in only the V4 fields that have been checked one by one.
    field_allowlist = (
        {"input_power", "volume_flow", "discharge_pressure", "specific_power"}
        if sheet_name == "空压机"
        else {"evaporation", "thermal_power", "lhv"}
        if sheet_name == "工业锅炉"
        else {"heating_capacity", "rated_power", "cop"}
        if sheet_name == "热泵热水机"
        else {"rated_power", "cooling_capacity", "heating_capacity", "primary_metric_value", "aux_metric1_value", "aux_metric2_value"}
        if sheet_name == "热泵和冷水机组"
        else {"cooling_capacity", "rated_power", "indicator_value"}
        if sheet_name == "风管送风式空调"
        else {"cooling_capacity", "rated_power", "indicator_value"}
        if sheet_name == "单元式空调"
        else {"cooling_capacity", "heating_capacity", "rated_power", "primary_metric_value", "eer_min_value", "cop_minus12_value", "cop_minus20_value"}
        if sheet_name == "多联式空调"
        else None
    )
    positive: list[str] = []
    integer: list[str] = []
    percentage: list[str] = []
    for field in profile.input_fields:
        field_id = str(field.v4_field_id or "")
        # Hidden/internal fields (for example production_year and frame_size)
        # are not V4 inputs and must not accidentally enter the V4 rule set.
        if not field_id:
            continue
        if field_allowlist is not None and field_id not in field_allowlist and field_id != "quantity":
            continue
        if field.data_type == "integer":
            integer.append(field_id)
        elif field.data_type == "percentage":
            percentage.append(field_id)
        elif (
            field.data_type == "number"
            and field.minimum == Decimal("0")
            and field.maximum is None
        ):
            positive.append(field_id)
    return {
        "positive": tuple(positive),
        "integer": tuple(integer),
        "percentage": tuple(percentage),
    }


def _metadata_non_negative_constraints(sheet_name: str) -> tuple[str, ...]:
    """Return reviewed V4 fields that allow zero but reject negatives.

    ``多联式空调``的“机外静压”在V4中是“数值≥0”。它必须与严格
    正数的设计指标分开，避免把未增加外部静压的合法0误报为错误。
    """

    if sheet_name != "多联式空调":
        return ()
    profile = get_device_profile(sheet_name)
    fields: list[str] = []
    for field in profile.input_fields:
        if (
            field.v4_field_id == "external_static"
            and field.data_type == "number"
            and field.minimum == Decimal("0")
            and field.maximum is None
        ):
            fields.append("external_static")
    return tuple(fields)


def _metadata_range_constraints(
    sheet_name: str,
) -> dict[str, tuple[Decimal, Decimal]]:
    """Return reviewed finite numeric ranges from the shared metadata.

    The reviewed bounded-number migrations are V4 ``isentropic_k`` shared by
    the centrifugal-fan, axial-fan and blower sheets, axial-fan ``hub_ratio``,
    submersible-pump ``temperature`` and industrial-boiler ``vdaf``. Other
    range rules deliberately remain in ``RANGE_FIELDS`` until their own V4
    contracts are reviewed, so this helper cannot silently broaden validation
    coverage.
    """

    if sheet_name not in {"工业锅炉", "离心通风机", "轴流通风机", "鼓风机", "潜水电泵"}:
        return {}
    profile = get_device_profile(sheet_name)
    ranges: dict[str, tuple[Decimal, Decimal]] = {}
    for field in profile.input_fields:
        field_id = str(field.v4_field_id or "")
        if field_id not in {"vdaf", "isentropic_k", "hub_ratio", "temperature"}:
            continue
        if field_id == "vdaf" and sheet_name != "工业锅炉":
            continue
        if field_id == "hub_ratio" and sheet_name != "轴流通风机":
            continue
        if field_id == "temperature" and sheet_name != "潜水电泵":
            continue
        if field.minimum is None or field.maximum is None:
            continue
        ranges[field_id] = (field.minimum, field.maximum)
    return ranges


def _metadata_percentage_limits(
    sheet_name: str,
    field_id: str,
    values: Mapping[str, Any],
) -> tuple[Decimal, Decimal] | None:
    """Return the metadata-backed percentage bounds for the boiler pilot."""

    if sheet_name != "工业锅炉" or field_id != "design_efficiency":
        return None
    field = get_device_profile(sheet_name).field(field_id)
    minimum = field.minimum if field.minimum is not None else Decimal("1")
    maximum = field.maximum if field.maximum is not None else Decimal("100")
    # The profile stores the safe union 1～110; the non-condensing branch is
    # narrowed by the standard's explicit condition, without changing the
    # metadata value or the raw input.
    if not _is_condensing_boiler(values):
        maximum = min(maximum, Decimal("100"))
    return minimum, maximum


def _metadata_enum_values(sheet_name: str) -> dict[str, set[str]]:
    """Return enum rules already verified in the lightweight domain metadata.

    The V4 workbook contract remains the presentation source whenever it is
    available.  The fallback currently covers the small rule families already
    verified against the V4 contract: the motor cooling field (whose complete
    16-value list is maintained in ``device_specs``), the four transformer
    fields and the compressor category. Any future family added to the
    metadata module is picked up automatically, while this function remains
    independent of Excel loading.
    """

    try:
        profile = get_device_profile(sheet_name)
    except (KeyError, ValueError):
        return {}
    return {
        field.v4_field_id: set(field.enum_values)
        for field in profile.input_fields
        if field.v4_field_id and field.enum_values
    }


def _is_condensing_boiler(values: Mapping[str, Any]) -> bool:
    """识别冷凝锅炉，供设计热效率的动态上限使用。

    V4把“是否冷凝”作为独立字段，但历史/兼容输入有时把属性写在设备类别中。
    先处理“非冷凝/无冷凝/否”否定词，避免简单搜索“冷凝”造成误判。
    """

    condensing = str(values.get("condensing", "")).strip().lower()
    if condensing in {"非冷凝", "无冷凝", "否", "no", "n", "false", "0"}:
        return False
    if condensing in {"冷凝", "是", "yes", "y", "true", "1"}:
        return True
    category = str(values.get("category", "")).strip()
    if any(token in category for token in ("非冷凝", "无冷凝")):
        return False
    return "冷凝" in category


def _issue(field: str | None, code: str, message: str, **metadata: Any) -> ValidationIssue:
    return ValidationIssue(field=field, code=code, message=message, severity=IssueSeverity.ERROR, metadata=metadata)


def _compact_text(value: Any) -> str:
    """Normalize display-only differences for dynamic indicator checks."""

    return (
        str(value or "")
        .strip()
        .replace("\u3000", "")
        .replace(" ", "")
        .replace("（", "(")
        .replace("）", ")")
        .upper()
    )


def _dynamic_indicator_entries(values: Mapping[str, Any]) -> list[tuple[str, Any, str]]:
    """Return (field prefix, value, name) triples in V4 indicator order.

    The V4 workbook exposes one generic indicator for the two single-metric
    air-conditioner sheets and up to three numbered indicators for the heat
    pump/multi-split sheets.  Keeping this small adapter here lets the
    automatic-note checker validate both forms without changing caller data.
    """

    numbered: list[tuple[str, Any, str]] = []
    for index in (1, 2, 3):
        name_key = f"indicator{index}_name"
        value_key = f"indicator{index}_value"
        if _present(values.get(name_key)) or _present(values.get(value_key)):
            numbered.append((f"indicator{index}", values.get(value_key), str(values.get(name_key, ""))))
    # A caller may provide both the generic compatibility pair and the V4
    # numbered pairs after normalization.  The numbered representation is the
    # authoritative order; otherwise the generic pair would shift every
    # expected auxiliary metric by one position.
    if numbered:
        return numbered
    if _present(values.get("indicator_name")) or _present(values.get("indicator_value")):
        return [("indicator", values.get("indicator_value"), str(values.get("indicator_name", "")))]
    return []


def _expected_dynamic_indicators(sheet_name: str, values: Mapping[str, Any]) -> tuple[str, ...] | None:
    """Derive the indicator names shown by the V4 formulas.

    ``None`` means the classification fields are not complete enough to make
    a safe assertion.  An empty tuple means the category is known but has no
    second/third indicator.  This function only validates names; all numeric
    limits still come from the standard data package/evaluator.
    """

    category = _compact_text(values.get("category"))
    if not category:
        return None

    if sheet_name == "热泵和冷水机组":
        product_standard = _compact_text(values.get("product_standard"))
        unit_type = _compact_text(values.get("unit_type"))
        source = _compact_text(values.get("source"))
        evaluation_system = _compact_text(values.get("evaluation_system"))
        is_copc_channel = "表2" in evaluation_system or "COPC指标体系" in evaluation_system
        if "蒸气压缩循环冷水(热泵)机组-舒适型" in category:
            if is_copc_channel:
                # GB 19577-2024表2以COPc为主指标，CSPF/IPLV为替代
                # 指标的3级固定门槛；V4把两者分别放在主指标和辅助指标1。
                alternate = "CSPF" if source == "风冷式" else "IPLV"
                return ("COPc", alternate)
            primary = "CSPF" if source == "风冷式" else "IPLV"
            return (primary, "COPc")
        if "蒸气压缩循环冷水(热泵)机组-数据中心专用型" in category:
            # 表2对数据中心专用型并非适用组合；这里仍镜像V4公式，
            # 让“类别/指标体系不适用”的既有自动备注负责提示组合问题。
            return ("ACCOP", "ACCOP") if is_copc_channel else ("ACCOP", "COPc")
        if "低环境温度空气源热泵(冷水)机组" in category:
            return ("APF" if unit_type == "风机盘管型" else "HSPF", "COPDH", "COPH")
        if "水(地)源热泵机组" in category:
            return ("COP" if "单热型" in unit_type else "ACOP",)
        if "溴化锂吸收式冷(温)水机组" in category:
            return ("单位制冷量加热源耗量" if product_standard == "GB/T18431" else "COP",)
        if "蒸气压缩循环高温热泵机组" in category:
            return ("COPH" if product_standard == "GB/T25861" else "COP",)
        if "间接蒸发冷却冷水机组" in category:
            if product_standard == "JB/T14642":
                return ("AEER", "EER")
            return ("EER",)
        if "一体式冷水(热泵)机组" in category:
            return ("IPLV(I)", "COP(I)")
        return None

    if sheet_name == "风管送风式空调":
        if "直接蒸发式全新风" in category:
            return ("EER",)
        cooling = _compact_text(values.get("cooling"))
        mode = _compact_text(values.get("mode"))
        if cooling in {"水冷式(水环式)", "水冷式"}:
            return ("IPLV",)
        if mode == "单冷型":
            return ("SEER",)
        if mode == "热泵型":
            return ("APF",)
        return None

    if sheet_name == "单元式空调":
        if "计算机和数据处理机房用" in category:
            return ("AEER",)
        if "通讯基站用" in category:
            return ("COP",)
        if "恒温恒湿型" in category:
            return ("AEER",)
        cooling = _compact_text(values.get("cooling"))
        mode = _compact_text(values.get("mode"))
        if cooling == "水冷式":
            return ("IPLV",)
        if mode == "单冷型":
            return ("SEER",)
        if mode == "热泵型":
            return ("APF",)
        return None

    if sheet_name == "多联式空调":
        if "风冷式单冷型多联机" in category or "风冷单冷" in category:
            names = ["SEER"]
            capacity = _number(values.get("cooling_capacity"))
            if capacity is not None and capacity <= Decimal(14):
                names.append("EERMIN")
            return tuple(names)
        if "风冷式热泵型多联机" in category or "风冷热泵" in category:
            names = ["APF"]
            capacity = _number(values.get("cooling_capacity"))
            if capacity is not None and capacity <= Decimal(14):
                names.append("EERMIN")
            return tuple(names)
        if "水冷式多联机" in category or category == "水冷":
            return ("IPLV(C)",) if _compact_text(values.get("water_source")) == "水环式" else ("EER",)
        if "低温多联机" in category or "低温机组" in category:
            return ("HSPF", "COP(-12℃)", "COP(-20℃)")
        return None
    return None


_DYNAMIC_METRIC_FIELDS: dict[str, tuple[str, ...]] = {
    "CSPF": ("cspf", "cspf_value"),
    "IPLV": ("iplv", "iplv_value"),
    "COPC": ("copc", "copc_value"),
    "ACCOP": ("accop", "accop_value"),
    "APF": ("apf", "apf_value"),
    "HSPF": ("hspf", "hspf_value"),
    "COPDH": ("copdh", "copdh_value"),
    "COPH": ("coph", "coph_value"),
    "ACOP": ("acop", "acop_value"),
    "COP": ("cop", "cop_value"),
    "AEER": ("aeer", "aeer_value"),
    "EER": ("eer", "eer_value"),
    "IPLV(I)": ("iplv_i", "iplv_i_value"),
    "COP(I)": ("cop_i", "cop_i_value"),
    "EERMIN": ("eer_min_value", "eer_min", "eer_min_design_value"),
    "COP(-12℃)": ("cop_minus12_value", "cop_minus12", "cop_minus_12"),
    "COP(-20℃)": ("cop_minus20_value", "cop_minus20", "cop_minus_20"),
    "单位制冷量加热源耗量": ("heat_source_consumption", "unit_heat_source_consumption"),
}


def _dynamic_metric_value(values: Mapping[str, Any], metric_name: str, position: int) -> Any:
    """Resolve a dynamic metric without treating a missing value as zero.

    ``primary_metric_value``/``aux_metric*`` are the stable V4/API aliases;
    the metric-specific candidates cover direct API payloads and the public
    15-sheet field IDs (for example ``eer_min_value`` and ``cop_minus12``).
    """

    compact = _compact_text(metric_name)
    for key in _DYNAMIC_METRIC_FIELDS.get(compact, ()):
        if _present(values.get(key)):
            return values.get(key)
    canonical_keys = ("primary_metric_value", "aux_metric1_value", "aux_metric2_value")
    if 0 <= position < len(canonical_keys) and _present(values.get(canonical_keys[position])):
        return values.get(canonical_keys[position])
    # The generic single-indicator compatibility form is only a safe alias for
    # the first metric.  Never reuse it for an auxiliary gate.
    if position == 0:
        for key in ("indicator1_value", "indicator_value"):
            if _present(values.get(key)):
                return values.get(key)
    return None


def _dynamic_metric_field(sheet_name: str, metric_name: str, position: int) -> str:
    # 优先返回V4实际可编辑列，而不是内部/兼容API可能使用的指标别名。
    # 这样自动备注可以直接定位到用户需要填写的单元格。
    if sheet_name in {"风管送风式空调", "单元式空调"}:
        return "indicator_value"
    if sheet_name == "热泵和冷水机组":
        return ("primary_metric_value", "aux_metric1_value", "aux_metric2_value")[min(position, 2)]
    if sheet_name == "多联式空调":
        compact = _compact_text(metric_name)
        if compact == "EERMIN":
            return "eer_min_value"
        if compact == "COP(-12℃)":
            return "cop_minus12_value"
        if compact == "COP(-20℃)":
            return "cop_minus20_value"
        return "primary_metric_value"
    compact = _compact_text(metric_name)
    candidates = _DYNAMIC_METRIC_FIELDS.get(compact, ())
    if candidates:
        return candidates[0]
    return ("primary_metric_value", "aux_metric1_value", "aux_metric2_value")[min(position, 2)]


def _validate_dynamic_indicators(sheet_name: str, values: Mapping[str, Any], issues: list[ValidationIssue]) -> None:
    """Check V4 dynamic indicator names and conditional values.

    The check deliberately does not invent a metric when a classification is
    incomplete.  Once a category is known, an entered name must agree with
    the metric selected by the template/standard; values for an indicator
    that is not applicable are reported instead of silently ignored.
    """

    expected = _expected_dynamic_indicators(sheet_name, values)
    if expected is None:
        return
    entries = _dynamic_indicator_entries(values)
    existing_required_fields = {
        str(issue.field)
        for issue in issues
        if issue.code == "conditional_required" and issue.field is not None
    }
    seen_positions: set[int] = set()
    for sequence, (prefix, value, name) in enumerate(entries):
        # 对编号指标保留其真实位置；例如只填indicator2时，不能把它
        # 当成第1个指标而漏掉主指标缺失。
        if prefix.startswith("indicator") and prefix != "indicator":
            try:
                position = max(int(prefix.removeprefix("indicator")) - 1, 0)
            except ValueError:
                position = sequence
        else:
            position = sequence
        seen_positions.add(position)
        expected_name = expected[position] if position < len(expected) else None
        if expected_name is None:
            if _present(value) or _present(name):
                issues.append(_issue(f"{prefix}_name/{prefix}_value", "indicator_mismatch", f"{prefix}与当前设备类别不匹配"))
            continue
        if _present(name) and _compact_text(name) != _compact_text(expected_name):
            issues.append(_issue(f"{prefix}_name", "indicator_mismatch", f"{prefix}名称应为{expected_name}"))
        if not _present(value) and _dynamic_metric_value(values, expected_name, position) is None:
            target_field = _dynamic_metric_field(sheet_name, expected_name, position)
            if target_field not in existing_required_fields:
                issues.append(_issue(target_field, "conditional_required", f"缺少设计指标值（{expected_name}）"))

    # 对没有显式指标对的输入，以及编号指标中间留空的输入，逐个补齐
    # 缺失位置检查。稳定的primary/aux别名和V4特定字段均可作为值来源。
    for index, expected_name in enumerate(expected):
        if index in seen_positions:
            continue
        if _dynamic_metric_value(values, expected_name, index) is None:
            target_field = _dynamic_metric_field(sheet_name, expected_name, index)
            if target_field not in existing_required_fields:
                issues.append(_issue(target_field, "conditional_required", f"缺少设计指标值（{expected_name}）"))



class V4ValidationService:
    """V4模板自动备注的可复用检查器。

    它只检查输入质量和条件逻辑；标准查表、插值及能效等级仍由EvaluationService完成。
    enum_values可由V4配置sheet/命名区域导入，未提供时不会猜测枚举集合。
    """

    @staticmethod
    def validate(
        sheet_name: str,
        values: Mapping[str, Any],
        *,
        enum_values: Mapping[str, set[str]] | None = None,
        row_enabled: bool | None = None,
    ) -> list[ValidationIssue]:
        if sheet_name not in V4_DEVICE_SHEETS:
            return [_issue(None, "unknown_sheet", f"不是V4设备sheet：{sheet_name}")]
        raw = dict(values)
        active = row_enabled if row_enabled is not None else any(_present(raw.get(key)) for key in raw)
        if not active:
            return []
        issues: list[ValidationIssue] = []

        for field in COMMON_REQUIRED:
            if not _present(raw.get(field)):
                issues.append(_issue(field, "required", f"缺少{FIELD_LABELS.get(field, field)}"))

        # V4配置中的“必填/条件必填”不能只依赖Excel下拉或表格公式；
        # 公共API和桌面回退表单也要对同一组基础设计参数给出自动备注。
        required_by_sheet: dict[str, tuple[str, ...]] = {
            "热泵和冷水机组": ("product_standard", "unit_type", "source", "evaluation_system", "rated_power"),
            "风管送风式空调": ("cooling", "mode", "enthalpy", "rated_power", "indicator_value"),
            "单元式空调": ("cooling", "mode", "rated_power", "indicator_value"),
            "多联式空调": ("rated_power", "external_static", "primary_metric_value"),
        }
        for field in required_by_sheet.get(sheet_name, ()):
            if not _present(raw.get(field)):
                issues.append(_issue(field, "required", f"缺少{CONDITIONAL_FIELD_LABELS.get(field, field)}"))

        metadata_constraints = _metadata_numeric_constraints(sheet_name)
        quantity_field = "quantity"
        if metadata_constraints is not None and "quantity" not in metadata_constraints["integer"]:
            # A missing common metadata field is a contract defect, not a
            # reason to silently fall back to a duplicated validation rule.
            raise ValueError(f"{sheet_name}元数据缺少数量整数约束")

        quantity = raw.get(quantity_field)
        if _present(quantity):
            number = _number(quantity)
            if number is None or number != number.to_integral_value() or number <= 0:
                issues.append(_issue(quantity_field, "positive_integer", "数量应为正整数"))

        if metadata_constraints is not None:
            # Keep already-reviewed metadata rules authoritative for mapped
            # V4 fields, while retaining legacy positive aliases for the
            # public motor bridge (rated_voltage/rated_frequency) until those
            # fields receive their own numeric migration.  This prevents a
            # one-field pilot from silently weakening an existing check.
            positive_fields = tuple(dict.fromkeys(
                (*metadata_constraints["positive"], *POSITIVE_FIELDS.get(sheet_name, ()))
            ))
        else:
            positive_fields = POSITIVE_FIELDS.get(sheet_name, ())
        integer_fields = (
            metadata_constraints["integer"]
            if metadata_constraints is not None
            else INTEGER_FIELDS.get(sheet_name, ())
        )
        metadata_percent_fields = (
            set(metadata_constraints["percentage"])
            if metadata_constraints is not None
            else set()
        )

        for field in positive_fields:
            value = raw.get(field)
            if not _present(value):
                continue
            number = _number(value)
            if number is None:
                issues.append(_issue(field, "number", f"{field}应为数值"))
            elif number <= 0:
                issues.append(_issue(field, "positive", f"{field}应大于0"))

        non_negative_fields = tuple(dict.fromkeys(
            (*NON_NEGATIVE_FIELDS.get(sheet_name, ()), *_metadata_non_negative_constraints(sheet_name))
        ))
        for field in non_negative_fields:
            value = raw.get(field)
            if not _present(value):
                continue
            number = _number(value)
            if number is None:
                issues.append(_issue(field, "number", f"{field}应为数值"))
            elif number < 0:
                issues.append(_issue(field, "non_negative", f"{field}不得小于0"))

        # Metadata-backed finite ranges override the legacy entry for the
        # reviewed field, while all other range fields continue to use the
        # existing table until their own migration is approved.
        range_fields = dict(RANGE_FIELDS.get(sheet_name, {}))
        range_fields.update(_metadata_range_constraints(sheet_name))
        for field, (minimum, maximum) in range_fields.items():
            value = raw.get(field)
            if not _present(value):
                continue
            number = _number(value)
            if number is None:
                # 范围字段也是数值字段；不能因无法解析就跳过，
                # 否则“待复核”等文本会绕过自动备注的质量检查。
                issues.append(_issue(field, "number", f"{field}应为数值"))
            elif not minimum <= number <= maximum:
                issues.append(_issue(field, "range", f"{field}应位于{minimum}～{maximum}"))

        for field in integer_fields:
            value = raw.get(field)
            if not _present(value):
                continue
            number = _number(value)
            if number is not None and number != number.to_integral_value():
                issues.append(_issue(field, "integer", f"{field}应为整数"))

        for field, value in raw.items():
            if not _present(value):
                continue
            if field in SEQUENCE_PERCENT_FIELDS:
                items = list(value) if isinstance(value, (list, tuple)) else re.split(r"[,，;；|、\s]+", str(value).strip())
                numbers = [_number(item) for item in items if item not in (None, "")]
                if not items or len(numbers) != len(items) or any(number is None or not Decimal(1) <= number <= Decimal(100) for number in numbers):
                    issues.append(_issue(field, "percent_range", f"{field}各项应按百分数本值填写且均位于1～100"))
                continue
            if field in PERCENT_FIELDS or field in metadata_percent_fields:
                number = _number(value)
                metadata_limits = _metadata_percentage_limits(sheet_name, field, raw)
                if metadata_limits is None:
                    minimum, maximum = Decimal(1), Decimal(100)
                    if sheet_name == "工业锅炉" and _is_condensing_boiler(raw):
                        maximum = Decimal(110)
                else:
                    minimum, maximum = metadata_limits
                if number is None or not minimum <= number <= maximum:
                    issues.append(_issue(field, "percent_range", f"{field}应按百分数本值填写且位于{minimum}～{maximum}"))
            if isinstance(value, str) and (value != value.strip() or "　" in value):
                issues.append(_issue(field, "whitespace", f"{field}含首尾空格或全角空格"))

        # 模板契约存在时，保留其字段级枚举作为展示/校验来源；没有契约
        # （直接公共API、桌面回退表单或JSONL桥接）时，仅补入已登记且
        # 可追溯的轻量元数据枚举。不同来源不得互相覆盖，避免把旧模板
        # 的标准值静默替换成另一套列表。
        effective_enum_values = dict(_metadata_enum_values(sheet_name))
        effective_enum_values.update(enum_values or {})
        if effective_enum_values:
            for field, allowed in effective_enum_values.items():
                value = raw.get(field)
                if not _present(value):
                    continue
                text = str(value)
                alias_target = V4_ENUM_ALIASES.get((sheet_name, field), {}).get(text)
                if text not in allowed and alias_target not in allowed:
                    issues.append(_issue(field, "enum", f"{field}不在标准枚举中", allowed=sorted(allowed), value=value))

        if sheet_name == "工业锅炉" and not (_present(raw.get("evaporation")) or _present(raw.get("thermal_power"))):
            issues.append(_issue("evaporation/thermal_power", "one_of_required", "蒸发量和热功率至少填写一项"))
        if sheet_name == "热泵和冷水机组":
            category = _compact_text(raw.get("category"))
            unit_type = _compact_text(raw.get("unit_type"))
            if category in {
                "蒸气压缩循环冷水(热泵)机组-舒适型",
                "蒸气压缩循环冷水(热泵)机组-数据中心专用型",
                "水(地)源热泵机组",
                "溴化锂吸收式冷(温)水机组",
                "间接蒸发冷却冷水机组",
                "一体式冷水(热泵)机组",
            } and not _present(raw.get("cooling_capacity")):
                issues.append(_issue("cooling_capacity", "conditional_required", "当前热泵/冷水机组类别缺少名义制冷量"))
            if category in {"低环境温度空气源热泵(冷水)机组", "蒸气压缩循环高温热泵机组"} and not _present(raw.get("heating_capacity")):
                issues.append(_issue("heating_capacity", "conditional_required", "当前热泵机组类别缺少名义制热量"))
            if category == "水(地)源热泵机组":
                if "单热型" in unit_type and not _present(raw.get("heating_capacity")):
                    issues.append(_issue("heating_capacity", "conditional_required", "单热型水（地）源热泵缺少名义制热量"))
                if "单热型" not in unit_type and not _present(raw.get("cooling_capacity")):
                    issues.append(_issue("cooling_capacity", "conditional_required", "热泵型水（地）源热泵缺少名义制冷量"))
        if sheet_name == "轴流通风机" and not _present(raw.get("hub_ratio")):
            # 轴流通风机按轮毂比分档；缺项应在自动备注中明确提示，
            # 与评价器的“无法判定”门禁保持一致。
            issues.append(_issue("hub_ratio", "conditional_required", "轴流通风机缺少轮毂比"))
        if sheet_name == "离心泵" and "多级" in str(raw.get("category", "")) and not _present(raw.get("stages")):
            # 多级泵的标准比转速使用单级扬程；没有级数不能安全计算。
            issues.append(_issue("stages", "conditional_required", "多级离心泵缺少级数"))
        if sheet_name == "变压器":
            category = str(raw.get("category", ""))
            # 使用数字边界，避免把“110kV”误识别为“10kV”。
            is_10kv = bool(re.search(r"(?<!\d)10\s*kV", category, flags=re.IGNORECASE))
            if is_10kv and not _present(raw.get("core_material")):
                issues.append(_issue("core_material", "conditional_required", "10kV变压器缺少铁芯材质"))
            if is_10kv and "干式" in category and not _present(raw.get("insulation")):
                issues.append(_issue("insulation", "conditional_required", "干式变压器缺少绝缘耐热等级"))
            if is_10kv and "油浸式" in category and not _present(raw.get("connection")):
                issues.append(_issue("connection", "conditional_required", "油浸式变压器缺少连接组标号"))
        if sheet_name == "热处理设备":
            energy = str(raw.get("energy_type", ""))
            electric = _present(raw.get("electricity"))
            fuel = _present(raw.get("fuel_consumption")) or _present(raw.get("fuel_heat"))
            if energy == "电力" and not electric:
                issues.append(_issue("electricity", "conditional_required", "能源类型为电力时缺少电炉总耗电量"))
            if energy == "电力" and fuel:
                issues.append(_issue("fuel_consumption/fuel_heat", "mutually_exclusive", "能源类型为电力时不应填写燃料耗量或燃料热值"))
            if energy and energy != "电力" and (not _present(raw.get("fuel_consumption")) or not _present(raw.get("fuel_heat"))):
                issues.append(_issue("fuel_consumption/fuel_heat", "conditional_required", "燃料设备缺少燃料总耗量或燃料热值"))
            if energy and energy != "电力" and electric:
                issues.append(_issue("electricity", "mutually_exclusive", "能源类型为燃料时不应填写电炉总耗电量"))
        if sheet_name == "多联式空调":
            category = str(raw.get("category", ""))
            water_source = raw.get("water_source")
            if "水冷" in category:
                if not _present(water_source):
                    issues.append(_issue("water_source", "conditional_required", "水冷式多联机缺少水冷式类型"))
                elif str(water_source).strip() == "不适用":
                    issues.append(_issue("water_source", "conditional_enum", "水冷式多联机不能选择“不适用”"))
            elif _present(water_source) and str(water_source).strip() != "不适用":
                # 下拉为静态完整集合后，非水冷类别仍只能填写“不适用”；
                # 不能靠Excel下拉本身表达条件枚举，必须在自动备注中复核。
                issues.append(_issue("water_source", "conditional_enum", "非水冷多联机的水冷式类型应为“不适用”"))
            if "低温" in category and not _present(raw.get("heating_capacity")):
                issues.append(_issue("heating_capacity", "conditional_required", "低温多联机缺少名义制热量"))
            if "低温" not in category and not _present(raw.get("cooling_capacity")):
                issues.append(_issue("cooling_capacity", "conditional_required", "当前类别缺少名义制冷量"))
            if "低温" in category and not _present(raw.get("cop_minus12_value")):
                issues.append(_issue("cop_minus12_value", "conditional_required", "低温多联机缺少COP(-12℃)设计值"))
            if "低温" in category and not _present(raw.get("cop_minus20_value")):
                issues.append(_issue("cop_minus20_value", "conditional_required", "低温多联机缺少COP(-20℃)设计值"))
            static = _number(raw.get("external_static"))
            corrected_present = _present(raw.get("static_pressure_corrected_metric"))
            factor_present = _present(raw.get("static_pressure_correction_factor"))
            if corrected_present and factor_present:
                issues.append(_issue("static_pressure_corrected_metric/static_pressure_correction_factor", "mutually_exclusive", "静压修正后指标和修正系数只能填写一项"))
            if (corrected_present or factor_present) and (static is None or static <= 0):
                issues.append(_issue("external_static", "conditional_required", "填写静压修正结果时机外静压必须大于0"))

        # 动态指标名称由V4公式按类别、标准和型式生成；手工/API输入的
        # 指标名和值必须与该选择一致，且每个适用指标都要有设计值。
        _validate_dynamic_indicators(sheet_name, raw, issues)

        return issues

    @staticmethod
    def validate_draft(draft: DeviceDraft, sheet_name: str) -> list[ValidationIssue]:
        return V4ValidationService.validate(sheet_name, draft.raw_values)
