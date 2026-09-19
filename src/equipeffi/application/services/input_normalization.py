from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any


# V4 模板字段只作为外部输入契约；评价器继续使用带单位含义的规范字段。
# 同一输入同时包含两种字段时，规范字段优先，避免静默覆盖调用方数据。
COMMON_ALIASES: dict[str, str] = {
    "设备名称": "device_name",
    "型号": "model",
    "数量": "quantity",
    "设备类别": "category",
    "安装位置": "location",
}


DEVICE_ALIASES: dict[str, dict[str, str]] = {
    "transformer": {
        "rated_capacity": "capacity_kva",
        "no_load_loss": "no_load_loss_w",
        "load_loss": "load_loss_w",
        "insulation_grade": "insulation",
    },
    "motor_lv": {
        "frame_size": "frame_size_mm",
        "frame": "frame_size_mm",
        "rated_power": "rated_power_kw",
        "rated_speed": "rated_speed_rpm",
        "efficiency": "rated_efficiency",
        "cooling": "cooling_method",
    },
    "motor_hv": {
        "frame_size": "frame_size_mm",
        "frame": "frame_size_mm",
        "rated_power": "rated_power_kw",
        "rated_speed": "rated_speed_rpm",
        "efficiency": "rated_efficiency",
        "cooling": "cooling_method",
    },
    "motor_pmsm": {
        "rated_power": "rated_power_kw",
        "rated_speed": "rated_speed_rpm",
        "cooling": "cooling_method",
        "efficiency_90_speed": "efficiency_at_90pct_speed",
    },
    "compressor": {
        "input_power": "input_power_kw",
        "rated_power": "rated_power_kw",
        "volume_flow": "volume_flow_m3min",
        "discharge_pressure": "discharge_pressure_mpa",
        "cooling": "cooling_method",
    },
    "pump_water": {
        "flow": "flow_m3h",
        "head": "head_m",
        "speed": "rated_speed_rpm",
        "power": "rated_power_kw",
        "rated_power": "rated_power_kw",
        "efficiency": "pump_efficiency",
    },
    "pump_chemical": {
        "flow": "flow_m3h",
        "head": "head_m",
        "speed": "rated_speed_rpm",
        "power": "rated_power_kw",
        "efficiency": "pump_efficiency",
    },
    "fan": {
        "flow": "flow_m3h",
        "fan_pressure": "fan_pressure_pa",
        "outlet_stag_pressure": "outlet_stagnation_pressure_pa",
        "inlet_stag_pressure": "inlet_stagnation_pressure_pa",
        "rated_power": "rated_power_kw",
        "impeller_power": "impeller_power_kw",
        "speed": "rated_speed_rpm",
        "density": "inlet_stagnation_density",
        "design_efficiency": "fan_efficiency",
        "unit_efficiency": "unit_efficiency",
        "motor_efficiency": "motor_efficiency",
    },
    "blower": {
        "flow": "flow_m3h",
        "rated_power": "rated_power_kw",
        "p1": "inlet_absolute_pressure_kpa",
        "p2": "outlet_absolute_pressure_kpa",
        "t1": "inlet_temperature_k",
        "t2": "outlet_temperature_k",
        "b2": "impeller_width_mm",
        "d2": "impeller_diameter_mm",
    },
    "submersible": {
        "flow": "flow_m3h",
        "head": "head_m",
        "speed": "rated_speed_rpm",
        "temperature": "working_temperature_c",
        "power": "rated_power_kw",
        "rated_power": "rated_power_kw",
        "efficiency": "pump_efficiency",
        "device_form": "subtype",
        "specified_eff": "specified_efficiency",
        "tolerance": "efficiency_tolerance",
        "pump_form": "pump_form",
        "form": "pump_form",
        "specific_speed": "specific_speed",
        "motor_efficiency": "motor_efficiency",
        "phase": "motor_phase",
        "motor_phase": "motor_phase",
        "motor_structure": "motor_structure",
        "sync_speed": "sync_speed_rpm",
        "sync_speed_rpm": "sync_speed_rpm",
    },
    "boiler": {
        "combustion": "combustion_method",
        "evaporation": "evaporation_tph",
        "thermal_power": "thermal_power_mw",
        "lhv": "lower_heating_value_kjkg",
        "vdaf": "volatile_matter_percent",
    },
    "heat_treatment": {
        "rated_power": "rated_power_kw",
        "rated_temperature": "rated_temperature_c",
        "equivalent_weight": "equivalent_weight_t",
        "electricity": "total_electricity_kwh",
        "fuel_heat": "fuel_calorific_value_kjkg",
    },
    "heat_pump_chiller": {
        "cooling_capacity": "cooling_capacity_kw",
        "heating_capacity": "heating_capacity_kw",
        "rated_power": "rated_power_kw",
        "source": "cooling_source",
    },
    "heat_pump_water_heater": {
        "category": "unit_type",
        "heating_capacity": "heating_capacity_kw",
        "rated_power": "rated_power_kw",
        "with_pump": "provides_pump",
    },
    "duct_ac": {
        "category": "product_type",
        "cooling": "cooling_source",
        "enthalpy": "enthalpy_difference",
        "rated_power": "rated_power_kw",
    },
    "unitary_ac": {
        "cooling": "cooling_source",
        "rated_power": "rated_power_kw",
    },
    "multi_split_ac": {
        "water_source": "cooling_source",
        "rated_power": "rated_power_kw",
        "external_static": "external_static_pressure_pa",
    },
}


ENUM_ALIASES: dict[str, dict[str, str]] = {
    "motor_lv": {
        # V4/历史填报的说明性后缀，标准类别本身为“三相异步电动机”。
        "三相异步电动机（一般用途）": "三相异步电动机",
    },
    "pump_water": {
        "单级单吸清水离心泵": "单级单吸",
        "单级双吸清水离心泵": "单级双吸",
        "管道清水离心泵": "管道",
        "多级清水离心泵": "多级",
        "轻型多级清水离心泵（立式）": "轻型多级立式",
        "轻型多级清水离心泵（卧式）": "轻型多级卧式",
    },
    "boiler": {
        "I类": "Ⅰ类",
        "II类": "Ⅱ类",
        "III类": "Ⅲ类",
    },
    "heat_pump_water_heater": {
        "一次加热式": "一次加热",
        "循环加热式": "循环加热",
    },
    "duct_ac": {
        "风管送风式空调（热泵）机组": "风管送风式机组",
        "直接蒸发式全新风空气处理机组": "直接蒸发式全新风机组",
        "水冷式（水环式）": "水冷式(水环式)",
    },
    "multi_split_ac": {
        "风冷式单冷型多联机": "风冷单冷",
        "风冷式热泵型多联机": "风冷热泵",
        "水冷式多联机": "水冷",
        "低温多联机": "低温机组",
    },
    "submersible": {
        "QDX": "QDX和QD", "QD": "QDX和QD",
        "QX": "QX和Q", "Q": "QX和Q",
        "混流式（蜗壳）": "混流式(蜗壳)", "混流式（导叶）": "混流式(导叶)",
        "其他（请备注说明）": "其他",
    },
}


def _present(value: Any) -> bool:
    return value not in (None, "")


def _set_alias(
    normalized: dict[str, Any],
    changes: list[dict[str, Any]],
    source: str,
    target: str,
    transform: str = "字段别名",
) -> None:
    if target in normalized and _present(normalized[target]):
        return
    if source not in normalized or not _present(normalized[source]):
        return
    normalized[target] = normalized[source]
    changes.append({"rule": transform, "source_field": source, "target_field": target, "value": normalized[target]})


def _decimal_multiply(value: Any, factor: Decimal) -> Decimal | None:
    try:
        result = Decimal(str(value).strip()) * factor
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError, AttributeError):
        return None


def _voltage_to_v(value: Any) -> Decimal | None:
    """Normalize a motor voltage input to volts for PMSM table selection.

    The V4 motor sheet labels its voltage column as kV, while the public
    compatibility inputs have historically accepted both values such as
    ``0.38``/``6`` and nameplate-style ``380``/``6000``.  Explicit ``V`` or
    ``kV`` suffixes always win; a unitless value below 20 is interpreted as kV
    and a larger unitless value as volts.  For dual-voltage text the highest
    component is used, which is conservative for selecting the applicable
    standard voltage group (for example ``380/660`` remains in the ≤1140 V
    group).  No default voltage is introduced when parsing fails.
    """

    if not _present(value):
        return None
    text = str(value).strip().upper().replace("千伏", "KV").replace("／", "/")
    matches = re.findall(r"[-+]?\d+(?:\.\d+)?", text)
    if not matches:
        return None
    try:
        numbers = [Decimal(item) for item in matches]
    except InvalidOperation:
        return None
    if any(not number.is_finite() for number in numbers):
        return None
    if "KV" in text:
        normalized = [number * Decimal(1000) for number in numbers]
    elif "V" in text:
        normalized = numbers
    else:
        normalized = [number * Decimal(1000) if abs(number) < Decimal(20) else number for number in numbers]
    return max(normalized)


def normalize_evaluation_input(device_type: str, values: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """将外部/V4 字段映射为判定器规范字段，并返回可审计的转换记录。"""

    normalized = dict(values)
    changes: list[dict[str, Any]] = []

    for source, target in COMMON_ALIASES.items():
        _set_alias(normalized, changes, source, target)
    for source, target in DEVICE_ALIASES.get(device_type, {}).items():
        _set_alias(normalized, changes, source, target)

    # V4 transformer rows use the explicit enum value “不适用” for category
    # combinations where GB 20052 has no additional material/insulation/
    # connection discriminator.  The standard data represents that state as
    # an empty criterion; preserve the user's original value while removing it
    # only from the normalized lookup copy so those rows can match safely.
    if device_type == "transformer":
        for field in ("core_material", "insulation", "connection"):
            if str(normalized.get(field, "")).strip() in {"不适用", "不适用（标准不要求）"}:
                original = normalized[field]
                normalized[field] = ""
                changes.append({
                    "rule": "不适用枚举不参与变压器标准匹配",
                    "field": field,
                    "source_value": original,
                    "value": "",
                })

    # V4 高压电机额定电压单位为 kV；接口规范字段明确为 V。
    if device_type == "motor_hv" and not _present(normalized.get("rated_voltage_v")) and _present(normalized.get("rated_voltage")):
        converted = _voltage_to_v(normalized["rated_voltage"])
        if converted is not None:
            normalized["rated_voltage_v"] = converted
            changes.append({
                "rule": "单位换算",
                "source_field": "rated_voltage",
                "target_field": "rated_voltage_v",
                "source_unit": "kV",
                "target_unit": "V",
                "source_value": normalized["rated_voltage"],
                "value": converted,
            })

    # V4 永磁电机只有一个效率输入列；其含义由标准产品类别决定。
    if device_type == "motor_pmsm" and _present(normalized.get("efficiency")):
        category = str(normalized.get("category", ""))
        target = "efficiency_at_90pct_speed" if "变频" in category else "rated_efficiency"
        _set_alias(normalized, changes, "efficiency", target, "按产品类别解释效率字段")

    # V4 将潜水电泵标准型式写在完整类别后的括号内。
    if device_type == "submersible" and not _present(normalized.get("subtype")):
        category = str(normalized.get("category", ""))
        match = re.search(r"[（(]([^（）()]+)[）)]", category)
        if match:
            original_subtype = match.group(1).strip()
            normalized["subtype"] = ENUM_ALIASES["submersible"].get(original_subtype, original_subtype)
            normalized["category"] = "小型潜水电泵" if "小型" in category else "大中型潜水电泵"
            # GB/T25409附录A按下泵式/上泵式区分ηSP；V4类别括号中的
            # QDX/QD等型号特征可以安全映射，单独的“QX和Q”合并值则不能猜测。
            if original_subtype in {"QDX", "QX"}:
                normalized["pump_form"] = "下泵式"
            elif original_subtype in {"QD", "Q", "QY", "QS"}:
                normalized["pump_form"] = "上泵式"
            elif original_subtype in {"QXL", "QXR"}:
                normalized["pump_form"] = original_subtype
            changes.append({"rule": "从完整类别拆分标准型式", "source_field": "category", "target_field": "subtype", "source_value": category, "value": normalized["subtype"]})

    # V4 普通单元式空调将用途和冷却方式分列，标准表则把二者合成类别。
    if device_type == "unitary_ac" and normalized.get("category") == "普通单元式空调机":
        cooling = normalized.get("cooling_source")
        if cooling in {"风冷式", "水冷式"}:
            original = normalized["category"]
            normalized["category"] = f"{cooling}单元式空调机"
            changes.append({"rule": "组合标准产品类别", "source_fields": ["category", "cooling_source"], "target_field": "category", "source_value": original, "value": normalized["category"]})

    if device_type == "boiler":
        # V4把GB 24500-2020的燃烧方式/冷凝条件合并到“设备类别”列。
        # 内部评价器仍保留拆分字段，只有在对应字段缺失时才从完整枚举安全映射，
        # 不覆盖调用方已经明确提供的值。
        category = str(normalized.get("category", ""))
        if category and not _present(normalized.get("combustion_method")):
            category_to_combustion = {
                "层状燃烧燃煤锅炉": "层状燃烧燃煤",
                "流化床燃烧燃煤锅炉": "流化床燃烧燃煤",
                "生物质锅炉": "生物质锅炉",
                "室燃燃烧锅炉（无冷凝）": "室燃锅炉",
                "室燃燃烧锅炉（燃气冷凝）": "室燃锅炉",
                "电锅炉": "电加热锅炉",
            }
            mapped_combustion = category_to_combustion.get(category)
            if mapped_combustion:
                normalized["combustion_method"] = mapped_combustion
                changes.append({"rule": "从完整锅炉类别拆分燃烧方式", "source_field": "category", "target_field": "combustion_method", "source_value": category, "value": mapped_combustion})
        if category == "室燃燃烧锅炉（燃气冷凝）" and not _present(normalized.get("condensing")):
            normalized["condensing"] = "冷凝"
            changes.append({"rule": "从完整锅炉类别拆分冷凝条件", "source_field": "category", "target_field": "condensing", "source_value": category, "value": "冷凝"})
        elif category == "室燃燃烧锅炉（无冷凝）" and not _present(normalized.get("condensing")):
            normalized["condensing"] = "非冷凝"
            changes.append({"rule": "从完整锅炉类别拆分冷凝条件", "source_field": "category", "target_field": "condensing", "source_value": category, "value": "非冷凝"})
        if normalized.get("fuel_class") == "不适用":
            normalized["fuel_class"] = ""
            changes.append({"rule": "不适用枚举不参与标准匹配", "field": "fuel_class", "source_value": "不适用", "value": ""})
        fuel = str(normalized.get("fuel", ""))
        combustion = str(normalized.get("combustion_method", ""))
        combustion_aliases = {
            # 兼容旧API/V4填报的简写；规范化后再进行标准表的精确匹配。
            "层状燃烧": "层状燃烧燃煤",
            "流化床燃烧": "流化床燃烧燃煤",
        }
        mapped_combustion_alias = combustion_aliases.get(combustion)
        if mapped_combustion_alias:
            normalized["combustion_method"] = mapped_combustion_alias
            changes.append({
                "rule": "锅炉燃烧方式兼容别名规范化",
                "source_field": "combustion_method",
                "target_field": "combustion_method",
                "source_value": combustion,
                "value": mapped_combustion_alias,
            })
            combustion = mapped_combustion_alias
        mapped = ""
        if fuel == "生物质":
            mapped = "生物质锅炉"
        elif fuel in {"天然气", "燃油", "煤（室燃）", "煤"} and combustion == "室燃燃烧":
            mapped = "室燃锅炉"
        if mapped and mapped != combustion:
            normalized["combustion_method"] = mapped
            changes.append({"rule": "按燃料组合标准燃烧类别", "source_fields": ["combustion_method", "fuel"], "target_field": "combustion_method", "source_value": combustion, "value": mapped})

    if device_type == "motor_pmsm" and not _present(normalized.get("voltage_group")):
        voltage_source = normalized.get("rated_voltage_v") if _present(normalized.get("rated_voltage_v")) else normalized.get("rated_voltage")
        voltage = _voltage_to_v(voltage_source)
        voltage_group = None
        if voltage is not None and voltage <= Decimal(1140):
            voltage_group = "≤1140V"
        elif voltage in {Decimal(3000), Decimal(3300), Decimal(6000), Decimal(6600)}:
            voltage_group = "3kV(3.3kV)/6kV"
        elif voltage == 10000:
            voltage_group = "10kV"
        if voltage_group:
            normalized["voltage_group"] = voltage_group
            changes.append({"rule": "按额定电压选择标准电压组", "source_field": "rated_voltage_v" if _present(normalized.get("rated_voltage_v")) else "rated_voltage", "target_field": "voltage_group", "source_value": voltage_source, "normalized_voltage_v": voltage, "value": voltage_group})
        elif voltage is not None:
            # 电压已成功解析，但不属于GB 30253-2024规定的≤1140 V、
            # 3/6 kV或10 kV离散组时，不能让评价器把缺失的电压组
            # 当作默认低压组。保留内部范围外标记，交给PMSM评价器
            # 生成候选表证据并返回“不在范围”。
            normalized["_pmsm_voltage_out_of_scope_v"] = voltage
            changes.append({
                "rule": "额定电压未命中PMSM标准离散电压组",
                "source_field": "rated_voltage_v" if _present(normalized.get("rated_voltage_v")) else "rated_voltage",
                "target_field": "_pmsm_voltage_out_of_scope_v",
                "source_value": voltage_source,
                "normalized_voltage_v": voltage,
                "match_status": "额定电压未命中",
            })
    if device_type == "motor_pmsm" and _present(normalized.get("cooling_method")) and not _present(normalized.get("cooling_group")):
        cooling = str(normalized["cooling_method"])
        groups = {
            "IC81W/IC86W/IC71W(IC3W7)": {"IC81W", "IC86W", "IC71W(IC3W7)"},
            "IC411/IC416": {"IC411", "IC416"},
            "IC511/IC611/IC616/IC516/IC666": {"IC511", "IC611", "IC616", "IC516", "IC666"},
        }
        cooling_group = next((group for group, members in groups.items() if cooling in members), None)
        if cooling_group:
            normalized["cooling_group"] = cooling_group
            changes.append({"rule": "按冷却方式选择标准冷却组", "source_field": "cooling_method", "target_field": "cooling_group", "source_value": cooling, "value": cooling_group})

    # 小于10 kW时，GB 29541表1将一次加热与循环加热合并为同一档。
    if device_type == "heat_pump_water_heater" and _present(normalized.get("heating_capacity_kw")):
        capacity = _decimal_multiply(normalized["heating_capacity_kw"], Decimal(1))
        method = str(normalized.get("heating_method", ""))
        if capacity is not None and capacity < 10 and method in {"一次加热式", "循环加热式", "一次加热", "循环加热"}:
            normalized["heating_method"] = "一次加热、循环加热式"
            changes.append({"rule": "按标准容量档合并加热方式", "field": "heating_method", "source_value": method, "value": normalized["heating_method"]})

    # V4 HVAC 容量均用 kW；GB 37479、GB 19576、GB 21454 数据包以 W 分档。
    if device_type in {"duct_ac", "unitary_ac", "multi_split_ac"}:
        for source, target in (("cooling_capacity", "cooling_capacity_w"), ("heating_capacity", "heating_capacity_w")):
            if _present(normalized.get(target)) or not _present(normalized.get(source)):
                continue
            converted = _decimal_multiply(normalized[source], Decimal(1000))
            if converted is not None:
                normalized[target] = converted
                changes.append({
                    "rule": "单位换算",
                    "source_field": source,
                    "target_field": target,
                    "source_unit": "kW",
                    "target_unit": "W",
                    "source_value": normalized[source],
                    "value": converted,
                })

    # V4 动态指标：只有在名称和值同时存在时才映射，禁止猜测指标名称。
    for index in (1, 2, 3):
        name = normalized.get(f"indicator{index}_name")
        value = normalized.get(f"indicator{index}_value")
        if not (_present(name) and _present(value)):
            continue
        target = _metric_field(str(name))
        if target:
            _set_alias(normalized, changes, f"indicator{index}_value", target, f"按指标名称{name}映射")
    if _present(normalized.get("indicator_name")) and _present(normalized.get("indicator_value")):
        target = _metric_field(str(normalized["indicator_name"]))
        if target:
            _set_alias(normalized, changes, "indicator_value", target, f"按指标名称{normalized['indicator_name']}映射")

    # 兼容只传一个通用指标值的 API；具体指标由唯一匹配到的标准行再解释。
    if not _present(normalized.get("primary_metric_value")):
        for candidate in ("indicator1_value", "indicator_value"):
            if _present(normalized.get(candidate)):
                normalized["primary_metric_value"] = normalized[candidate]
                changes.append({"rule": "通用设计指标", "source_field": candidate, "target_field": "primary_metric_value", "value": normalized[candidate]})
                break

    # 只在规范化副本中处理明确枚举同义词；原始输入仍保留在 DeviceDraft。
    aliases = ENUM_ALIASES.get(device_type, {})
    for key in ("category", "product_type", "cooling_source", "unit_type", "fuel_class", "heating_method", "subtype"):
        original = normalized.get(key)
        mapped = aliases.get(str(original))
        if mapped and mapped != original:
            normalized[key] = mapped
            changes.append({"rule": "标准枚举同义词", "field": key, "source_value": original, "value": mapped})

    return normalized, changes


def v4_input_contract(device_type: str) -> dict[str, Any]:
    """返回供 CLI/API 使用的人可读 V4 兼容字段说明。"""

    aliases = dict(COMMON_ALIASES)
    aliases.update(DEVICE_ALIASES.get(device_type, {}))
    conversions: list[str] = []
    if device_type == "motor_hv":
        conversions.append("rated_voltage 按V4的kV输入并换算为 rated_voltage_v（V）")
    if device_type in {"duct_ac", "unitary_ac", "multi_split_ac"}:
        conversions.append("cooling_capacity/heating_capacity 按V4的kW输入并换算为标准分档使用的W")
    if device_type == "motor_pmsm":
        conversions.append("rated_voltage 用于选择电压组；efficiency_90_speed用于变频调速产品")
    if device_type in {"duct_ac", "unitary_ac", "multi_split_ac", "heat_pump_chiller"}:
        conversions.append("indicator_name+indicator_value或indicator1~3名称和值按指标名映射")
    return {
        "v4_aliases": aliases,
        "v4_conversions": conversions,
        "precedence": "同时提供规范字段和V4字段时，规范字段优先；所有转换写入判定轨迹",
    }


def _metric_field(name: str) -> str | None:
    compact = name.strip().upper().replace("（", "(").replace("）", ")").replace(" ", "")
    mapping = {
        "SEER": "seer",
        "APF": "apf",
        "IPLV": "iplv",
        "IPLV(C)": "iplv_c",
        "IPLV(I)": "iplv_i",
        "AEER": "aeer",
        "EER": "eer",
        "EERMIN": "eer",
        "HSPF": "hspf",
        "COP": "cop",
        "COPDH": "cop_dh",
        "COPH": "cop_h",
        "COP(-12℃)": "cop_minus_12",
        "COP(-20℃)": "cop_minus_20",
        "CSPF": "cspf",
        "ACCOP": "accop",
    }
    return mapping.get(compact)
