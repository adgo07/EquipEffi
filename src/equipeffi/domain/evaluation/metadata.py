"""统一的设备字段元数据（第一阶段只读注册表）。

本模块是领域层的轻量元数据入口，不读取 Excel、Tk 或 Web 资源，也不执行
清洗和能效判定。它把现有 ``device_specs`` 中的17个内部 profile 映射到V4
对外的15类设备，并为后续 API、窗口和 Excel 适配器提供同一份字段身份、
显示名称、单位、别名、输入角色和V4映射。

当前阶段有意保留 ``v4_template_contract`` 和 ``v4_validation`` 的运行时
行为不变：模板中的完整结果列和标准专属枚举仍以V4配置为准；本注册表先
覆盖公共输入字段及通用锁定结果字段，后续再逐步让各适配器读取这里的定义。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping

from .device_specs import DEVICE_SPECS, ENUM_VALUES
from .device_types import (
    PUBLIC_DEVICE_NAMES,
    PUBLIC_DEVICE_TYPES,
    profiles_for_public_type,
    PUBLIC_TYPE_BY_SHEET,
)


# 变压器的四组枚举是V4模板中用于输入限制的标准规范值。这里保留一份
# 轻量、可序列化的领域副本，使没有加载Excel契约的API/桌面回退路径也能
# 进行同样的枚举质量检查。契约测试会逐项与V4“配置”sheet比对；若模板
# 枚举发生变化，测试必须先失败，不能静默接受两套列表。
_TRANSFORMER_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "category": (
        "EV_TRANSFORMER_CATEGORY",
        (
            "10kV油浸式三相双绕组无励磁调压配电变压器",
            "10kV干式三相双绕组无励磁调压配电变压器",
            "35kV油浸式三相双绕组无励磁调压电力变压器",
            "35kV油浸式三相双绕组有载调压电力变压器",
            "66kV油浸式三相双绕组有载调压电力变压器",
            "66kV油浸式三相双绕组无励磁调压电力变压器",
            "110kV油浸式三相双绕组无励磁调压电力变压器",
            "110kV油浸式三相双绕组低压为35kV无励磁调压电力变压器",
            "110kV油浸式三相三绕组无励磁调压变压器",
            "110kV油浸式三相双绕组有载调压电力变压器",
            "110kV油浸式三相三绕组有载调压电力变压器",
            "220kV油浸式三相双绕组无励磁调压电力变压器",
            "220kV油浸式三相三绕组无励磁调压电力变压器",
            "220kV油浸式三相双绕组低压为66kV无励磁调压电力变压器",
            "220kV油浸式三相双绕组有载调压电力变压器",
            "220kV油浸式三相三绕组有载调压电力变压器",
            "220kV油浸式三相三绕组有载调压自耦电力变压器",
            "330kV油浸式三相双绕组无励磁调压电力变压器",
            "330kV油浸式三相三绕组无励磁调压电力变压器",
            "330kV油浸式三相三绕组无励磁调压自耦电力变压器（串联绕组末端调压，中压110kV）",
            "330kV油浸式三相三绕组有载调压自耦电力变压器（串联绕组末端调压，中压110kV）",
            "330kV油浸式三相三绕组有载调压自耦电力变压器（中压110kV线端调压）",
            "330kV油浸式三相三绕组无励磁调压自耦电力变压器（中压220kV线端调压）",
            "330kV油浸式三相三绕组有载调压自耦电力变压器（中压220kV线端调压）",
            "500kV油浸式单相双绕组无励磁调压电力变压器",
            "500kV油浸式三相双绕组无励磁调压电力变压器",
            "500kV油浸式单相三绕组有载调压自耦电力变压器（中压线端调压）",
            "500kV油浸式单相三绕组无励磁调压自耦电力变压器（中压线端调压）",
            "6kV油浸式三相双绕组无励磁调压新能源发电侧光伏用、风电用、储能用变压器（6kV~7.2kV/0.4kV~1.14kV）",
            "6kV干式三相双绕组无励磁调压新能源发电侧光伏用、风电用、储能用变压器（6kV~7.2kV/0.4kV~1.14kV）",
            "10kV油浸式三相双绕组无励磁调压新能源发电侧光伏用、风电用、储能用变压器（10kV~12kV/0.4kV~1.14kV）",
            "10kV干式三相双绕组无励磁调压新能源发电侧光伏用、风电用、储能用变压器（10kV~12kV/0.4kV~1.14kV）",
            "35kV油浸式三相双绕组无励磁调压新能源发电侧光伏用、风电用、储能用变压器（35kV~38.5kV/0.4kV~1.14kV）",
            "35kV干式三相双绕组无励磁调压新能源发电侧光伏用、风电用、储能用变压器（35kV~38.5kV/0.4kV~1.14kV）",
            "66kV油浸式三相双绕组无励磁调压新能源发电侧光伏用、风电用、储能用变压器（66kV~72.5kV/0.4kV~1.14kV）",
            "其他（请备注说明）",
        ),
    ),
    "core_material": (
        "EV_CORE_MATERIAL",
        ("电工钢带", "非晶合金", "不适用", "其他（请备注说明）"),
    ),
    "insulation": (
        "EV_INSULATION",
        ("75℃", "B(100℃)", "F(120℃)", "H(145℃)", "其他（请备注说明）", "不适用"),
    ),
    "connection": (
        "EV_CONNECTION",
        ("Dyn11/Yzn11", "Yyn0", "不适用", "其他（请备注说明）"),
    ),
}

_COMPRESSOR_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "category": (
        "EV_COMPRESSOR_CATEGORY",
        (
            "一般用喷油回转（工频）",
            "一般用变转速喷油回转",
            "一般用往复活塞",
            "全无油润滑往复活塞",
            "无油润滑的直联便携式往复活塞",
            "有油润滑的直联便携式往复活塞",
            "其他（请备注说明）",
        ),
    ),
    "cooling_method": (
        "EV_COMPRESSOR_COOLING",
        ("风冷", "液冷", "不适用", "其他（请备注说明）"),
    ),
}

_MOTOR_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "category": (
        "EV_MOTOR_CATEGORY",
        (
            "三相异步电动机",
            "电容起动异步电动机",
            "电容运转异步电动机",
            "双值电容异步电动机",
            "空调器风扇用无刷直流电动机",
            "空调器风扇用电容运转电动机",
            "高压三相笼型异步电动机",
            "异步起动三相永磁同步电动机",
            "变频调速永磁同步电动机",
            "电梯用永磁同步电动机",
            "其他（请备注说明）",
        ),
    ),
    "rated_voltage_v": (
        "EV_MOTOR_VOLTAGE",
        ("0.2", "0.4", "3（3.3）", "6", "其他（请备注说明）", "10"),
    ),
    "poles": (
        "EV_POLES_PMSM",
        ("2", "4", "6", "8", "12", "10", "16", "20", "24", "32", "40", "48", "其他（请备注说明）"),
    ),
}

_PUBLIC_ENUM_VALUES: dict[str, dict[str, tuple[str, tuple[str, ...]]]] = {
    "transformer": _TRANSFORMER_ENUM_VALUES,
    "compressor": _COMPRESSOR_ENUM_VALUES,
    "motor": _MOTOR_ENUM_VALUES,
}

_PUMP_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "category": (
        "EV_PUMP_CATEGORY",
        (
            "单级单吸清水离心泵",
            "单级双吸清水离心泵",
            "管道清水离心泵",
            "多级清水离心泵",
            "轻型多级清水离心泵（卧式）",
            "轻型多级清水离心泵（立式）",
            "单级石油化工离心泵",
            "多级石油化工离心泵",
            "其他（请备注说明）",
        ),
    ),
    "suction": (
        "EV_SUCTION",
        ("单吸", "双吸", "不适用", "其他（请备注说明）"),
    ),
}

_PUBLIC_ENUM_VALUES["centrifugal_pump"] = _PUMP_ENUM_VALUES

_SUBMERSIBLE_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "category": (
        "EV_SUBMERSIBLE_CATEGORY",
        (
            "小型潜水电泵",
            "大中型潜水电泵",
            "污水污物潜水电泵",
            "井用潜水电泵",
            "其他（请备注说明）",
            "混流潜水电泵",
        ),
    ),
    "subtype": (
        "EV_SUB_FORM_ALL",
        (
            "QDX和QD", "QX和Q", "QY", "QS", "QXL", "QXR",
            "离心式", "轴流式", "混流式（蜗壳）", "混流式（导叶）",
            "旋流式", "混流式", "其他式", "充水式", "充油式", "屏蔽式",
            "单相", "蜗壳式", "导叶式", "其他（请备注说明）",
        ),
    ),
}

_PUBLIC_ENUM_VALUES["submersible_pump"] = _SUBMERSIBLE_ENUM_VALUES

_BOILER_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "category": (
        "EV_BOILER_CATEGORY",
        (
            "层状燃烧燃煤锅炉", "流化床燃烧燃煤锅炉", "生物质锅炉",
            "室燃燃烧锅炉（无冷凝）", "有机热载体锅炉（带余热回收）",
            "室燃燃烧锅炉（燃气冷凝）", "有机热载体锅炉（无余热回收）",
            "电锅炉", "其他（请备注说明）",
        ),
    ),
    "fuel": (
        "EV_FUEL",
        (
            "烟煤", "贫煤", "无烟煤", "褐煤", "天然气",
            "生物质", "燃油", "煤（室燃）", "电力", "其他（请备注说明）",
        ),
    ),
}

_PUBLIC_ENUM_VALUES["industrial_boiler"] = _BOILER_ENUM_VALUES

_HEAT_TREATMENT_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "category": (
        "EV_HEAT_TREAT_CATEGORY",
        (
            "传送式连续炉",
            "震底式连续炉",
            "推送式连续炉",
            "滚筒式连续炉",
            "井式炉-中温炉",
            "箱式多用炉",
            "井式炉-回火炉",
            "井式炉-气体渗碳(氮)炉",
            "箱式炉",
            "台车炉",
            "热处理电热浴炉",
            "辊底炉",
            "罩式炉",
            "其他（请备注说明）",
        ),
    ),
    "energy_type": (
        "EV_ENERGY_TYPE",
        (
            "燃料油",
            "发生炉煤气（1250kcal/m³～1350kcal/m³）",
            "发生炉煤气（1400kcal/m³～2200kcal/m³）",
            "城市煤气/焦炉煤气",
            "电力",
            "天然气",
            "其他（请备注说明）",
        ),
    ),
}

_PUBLIC_ENUM_VALUES["heat_treatment"] = _HEAT_TREATMENT_ENUM_VALUES

_HPWH_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "category": (
        "EV_HPWH_CATEGORY",
        ("普通型", "低温型", "其他（请备注说明）"),
    ),
    "heating_method": (
        "EV_HEATING_METHOD",
        ("一次加热式", "循环加热式", "静态加热式", "不适用", "其他（请备注说明）"),
    ),
    "with_pump": (
        "EV_YES_NO",
        ("是", "否", "不适用", "其他（请备注说明）"),
    ),
}

_PUBLIC_ENUM_VALUES["heat_pump_water_heater"] = _HPWH_ENUM_VALUES

_HP_CHILLER_CATEGORY_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "category": (
        "EV_HP_CHILLER_CATEGORY",
        (
            "蒸气压缩循环冷水（热泵）机组-舒适型",
            "蒸气压缩循环冷水（热泵）机组-数据中心专用型",
            "低环境温度空气源热泵（冷水）机组",
            "水（地）源热泵机组",
            "蒸气压缩循环高温热泵机组",
            "溴化锂吸收式冷（温）水机组",
            "间接蒸发冷却冷水机组",
            "一体式冷水（热泵）机组",
            "其他（请备注说明）",
        ),
    ),
}

_PUBLIC_ENUM_VALUES["heat_pump_chiller"] = _HP_CHILLER_CATEGORY_ENUM_VALUES

_HP_CHILLER_PRODUCT_STANDARD_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "product_standard": (
        "EV_HP_STD_ALL",
        (
            "GB/T 18430.1",
            "GB/T 18430.2",
            "GB/T 25127.1",
            "GB/T 25127.2",
            "GB/T 18431",
            "GB/T 19409",
            "GB/T 18362",
            "GB/T 25861",
            "JB/T 12840",
            "JB/T 14642",
            "JB/T 14640",
            "JB/T 12839",
            "其他（请备注说明）",
        ),
    ),
}

_PUBLIC_ENUM_VALUES["heat_pump_chiller"].update(_HP_CHILLER_PRODUCT_STANDARD_ENUM_VALUES)

_HP_CHILLER_UNIT_TYPE_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "unit_type": (
        "EV_HP_UNIT_ALL",
        (
            "舒适型",
            "数据中心专用型",
            "地板采暖型",
            "风机盘管型",
            "冷热风型-热泵型",
            "散热器型",
            "冷热水型-单热型",
            "冷热水型-热泵型",
            "饱和蒸汽压力0.4MPa",
            "饱和蒸汽压力0.6MPa",
            "饱和蒸汽压力0.8MPa",
            "直燃型机组",
            "H1a",
            "H2a",
            "H3a",
            "H4a",
            "H5a",
            "H1b",
            "H2b",
            "H3b",
            "H4b",
            "H5b",
            "循环供水式热泵高温热水机组",
            "外冷式",
            "内冷式",
            "内外冷串联式",
            "风冷式",
            "蒸发冷却式冷却塔式",
            "其他（请备注说明）",
        ),
    ),
}

_PUBLIC_ENUM_VALUES["heat_pump_chiller"].update(_HP_CHILLER_UNIT_TYPE_ENUM_VALUES)

_HP_CHILLER_SOURCE_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "source": (
        "EV_HP_SOURCE_ALL",
        (
            "水冷式",
            "风冷式",
            "蒸发冷却式",
            "空气源",
            "地下水式",
            "水环式",
            "地埋管式",
            "地表水式",
            "饱和蒸汽",
            "直燃",
            "不适用",
            "其他（请备注说明）",
        ),
    ),
}

_PUBLIC_ENUM_VALUES["heat_pump_chiller"].update(_HP_CHILLER_SOURCE_ENUM_VALUES)

_HP_CHILLER_EVALUATION_SYSTEM_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "evaluation_system": (
        "EV_HP_EVAL_SYSTEM",
        (
            "综合部分负荷/季节性能指标体系（表1）",
            "制冷性能系数COPc指标体系（表2）",
            "对应产品类别指标体系（表3～表8）",
            "其他（请备注说明）",
        ),
    ),
}

_PUBLIC_ENUM_VALUES["heat_pump_chiller"].update(_HP_CHILLER_EVALUATION_SYSTEM_ENUM_VALUES)

_CENTRIFUGAL_FAN_CATEGORY_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "category": (
        "EV_CENTRIFUGAL_FAN_CATEGORY",
        (
            "离心通风机",
            "外转子电机直联前向多翼离心风机",
            "其他（请备注说明）",
        ),
    ),
    "transmission": (
        "EV_TRANSMISSION",
        (
            "A式传动（普通电动机直联）",
            "外转子电机直联",
            "其他传动",
            "不适用",
            "其他（请备注说明）",
        ),
    ),
    "suction": (
        "EV_SUCTION",
        ("单吸", "双吸", "不适用", "其他（请备注说明）"),
    ),
    "hvac_use": (
        "EV_YES_NO",
        ("是", "否", "不适用", "其他（请备注说明）"),
    ),
    "inlet_box": (
        "EV_YES_NO",
        ("是", "否", "不适用", "其他（请备注说明）"),
    ),
}

_PUBLIC_ENUM_VALUES["centrifugal_fan"] = _CENTRIFUGAL_FAN_CATEGORY_ENUM_VALUES

_AXIAL_FAN_CATEGORY_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "category": (
        "EV_AXIAL_FAN_CATEGORY",
        ("轴流通风机", "其他（请备注说明）"),
    ),
    "transmission": (
        "EV_TRANSMISSION",
        (
            "A式传动（普通电动机直联）",
            "外转子电机直联",
            "其他传动",
            "不适用",
            "其他（请备注说明）",
        ),
    ),
    "inlet_box": (
        "EV_YES_NO",
        ("是", "否", "不适用", "其他（请备注说明）"),
    ),
    "diffuser": (
        "EV_YES_NO",
        ("是", "否", "不适用", "其他（请备注说明）"),
    ),
    "variable_blade": (
        "EV_YES_NO",
        ("是", "否", "不适用", "其他（请备注说明）"),
    ),
    "reversible": (
        "EV_YES_NO",
        ("是", "否", "不适用", "其他（请备注说明）"),
    ),
}

_PUBLIC_ENUM_VALUES["axial_fan"] = _AXIAL_FAN_CATEGORY_ENUM_VALUES

_BLOWER_CATEGORY_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "category": (
        "EV_BLOWER_CATEGORY",
        (
            "单级双支撑低速离心鼓风机",
            "多级低速离心鼓风机",
            "单级双支撑高速离心鼓风机",
            "多级高速离心鼓风机",
            "其他（请备注说明）",
        ),
    ),
}

_PUBLIC_ENUM_VALUES["blower"] = _BLOWER_CATEGORY_ENUM_VALUES

_BLOWER_MULTI_IMPELLER_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "multi_impeller": (
        "EV_YES_NO",
        ("是", "否", "不适用", "其他（请备注说明）"),
    ),
    "cantilever": (
        "EV_YES_NO",
        ("是", "否", "不适用", "其他（请备注说明）"),
    ),
    "three_dimensional": (
        "EV_YES_NO",
        ("是", "否", "不适用", "其他（请备注说明）"),
    ),
}

_PUBLIC_ENUM_VALUES["blower"].update(_BLOWER_MULTI_IMPELLER_ENUM_VALUES)

_DUCT_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "category": (
        "EV_DUCT_CATEGORY",
        (
            "风管送风式空调（热泵）机组",
            "直接蒸发式全新风空气处理机组",
            "其他（请备注说明）",
        ),
    ),
}

_PUBLIC_ENUM_VALUES["duct_ac"] = _DUCT_ENUM_VALUES

_DUCT_COOLING_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "cooling_source": (
        "EV_AC_COOLING_DUCT",
        (
            "风冷式",
            "水冷式（水环式）",
            "不适用",
            "其他（请备注说明）",
        ),
    ),
}

_PUBLIC_ENUM_VALUES["duct_ac"].update(_DUCT_COOLING_ENUM_VALUES)

_DUCT_MODE_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "mode": (
        "EV_AC_MODE",
        ("单冷型", "热泵型", "不适用", "其他（请备注说明）"),
    ),
}

_PUBLIC_ENUM_VALUES["duct_ac"].update(_DUCT_MODE_ENUM_VALUES)

_DUCT_ENTHALPY_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "enthalpy_difference": (
        "EV_ENTHALPY",
        ("小焓差", "大焓差", "不适用", "其他（请备注说明）"),
    ),
}

_PUBLIC_ENUM_VALUES["duct_ac"].update(_DUCT_ENTHALPY_ENUM_VALUES)

_UNITARY_CATEGORY_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "category": (
        "EV_UNITARY_CATEGORY",
        (
            "普通单元式空调机",
            "计算机和数据处理机房用单元式空调机",
            "通讯基站用单元式空气调节机",
            "恒温恒湿型单元式空调机",
            "其他（请备注说明）",
        ),
    ),
}

_PUBLIC_ENUM_VALUES["unitary_ac"] = _UNITARY_CATEGORY_ENUM_VALUES

_UNITARY_COOLING_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "cooling_source": (
        "EV_AC_COOLING_UNITARY",
        (
            "风冷式",
            "水冷式",
            "乙二醇经济冷却式",
            "风冷双冷源式",
            "不适用",
            "水冷双冷源式",
            "其他（请备注说明）",
        ),
    ),
}

_PUBLIC_ENUM_VALUES["unitary_ac"].update(_UNITARY_COOLING_ENUM_VALUES)

_UNITARY_MODE_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "mode": (
        "EV_AC_MODE",
        ("单冷型", "热泵型", "不适用", "其他（请备注说明）"),
    ),
}

_PUBLIC_ENUM_VALUES["unitary_ac"].update(_UNITARY_MODE_ENUM_VALUES)

_MULTI_SPLIT_WATER_SOURCE_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "cooling_source": (
        "EV_WATER_SOURCE",
        ("水环式", "地埋管式", "地下水式", "不适用", "其他（请备注说明）"),
    ),
}

_PUBLIC_ENUM_VALUES["multi_split_ac"] = _MULTI_SPLIT_WATER_SOURCE_ENUM_VALUES

_MULTI_SPLIT_CATEGORY_ENUM_VALUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "category": (
        "EV_MULTI_CATEGORY",
        (
            "风冷式单冷型多联机",
            "风冷式热泵型多联机",
            "水冷式多联机",
            "低温多联机",
            "其他（请备注说明）",
        ),
    ),
}

_PUBLIC_ENUM_VALUES["multi_split_ac"].update(_MULTI_SPLIT_CATEGORY_ENUM_VALUES)


_COMMON_FIELD_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "field_id": "device_name",
        "display_name": "设备名称",
        "group": "基础信息",
        "data_type": "text",
        "unit": "-",
        "editable": True,
        "required": False,
        "required_condition": "缺失时在自动备注中提示",
        "aliases": ("device_name", "设备名称", "设备名"),
        "role": "input",
        "ui_control": "text",
        "v4_field_id": "device_name",
    },
    {
        "field_id": "model",
        "display_name": "型号",
        "group": "基础信息",
        "data_type": "text",
        "unit": "-",
        "editable": True,
        "required": False,
        "required_condition": "缺失时在自动备注中提示；用于标准和淘汰目录匹配",
        # “设备型号”是历史模板中常见的表头写法，统一归入型号字段。
        "aliases": ("model", "型号", "设备型号"),
        "role": "input",
        "ui_control": "text",
        "v4_field_id": "model",
    },
    {
        "field_id": "quantity",
        "display_name": "数量",
        "group": "基础信息",
        "data_type": "integer",
        "unit": "-",
        "editable": True,
        "required": True,
        "required_condition": "正整数；缺失时在自动备注中提示",
        "minimum": Decimal("1"),
        "aliases": ("quantity", "数量", "台数"),
        "role": "input",
        "ui_control": "number",
        "v4_field_id": "quantity",
    },
    {
        "field_id": "category",
        "display_name": "设备类别",
        "group": "基础信息",
        "data_type": "text",
        "unit": "-",
        "editable": True,
        "required": True,
        "required_condition": "按对应标准枚举填写；缺失时在自动备注中提示",
        "aliases": ("category", "设备类别", "设备类型"),
        "role": "input",
        "ui_control": "select",
        "v4_field_id": "category",
    },
    {
        "field_id": "location",
        "display_name": "安装位置",
        "group": "基础信息",
        "data_type": "text",
        "unit": "-",
        "editable": True,
        "required": False,
        "required_condition": "可选",
        "aliases": ("location", "安装位置"),
        "role": "input",
        "ui_control": "text",
        "v4_field_id": "location",
    },
    {
        "field_id": "photo",
        "display_name": "铭牌照片",
        "group": "附件备注",
        "data_type": "image",
        "unit": "-",
        "editable": True,
        "required": False,
        "required_condition": "缺失时在自动备注中提示；使用置于单元格的图片",
    "aliases": ("photo", "铭牌照片", "铭牌图片"),
        "role": "input",
        "ui_control": "image",
        "v4_field_id": "photo",
    },
)


# 这些是跨设备稳定存在的锁定列。设备专属的标准查询结果仍由V4配置
# 和各评价器提供，暂不在这里复制第二份大表。
_COMMON_RESULT_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "field_id": "seq",
        "display_name": "序号",
        "group": "基础信息",
        "data_type": "integer",
        "unit": "-",
        "editable": False,
        "required": False,
        "role": "calculated",
        "ui_control": "readonly",
        "v4_field_id": "seq",
    },
    {
        "field_id": "standard_code",
        "display_name": "采用标准",
        "group": "标准结果",
        "data_type": "text",
        "unit": "-",
        "editable": False,
        "required": False,
        "role": "result",
        "ui_control": "readonly",
        "v4_field_id": "standard_code",
    },
    {
        "field_id": "standard_table",
        "display_name": "匹配表/条款",
        "group": "标准结果",
        "data_type": "text",
        "unit": "-",
        "editable": False,
        "required": False,
        "role": "result",
        "ui_control": "readonly",
        "v4_field_id": "standard_table",
    },
    {
        "field_id": "reference_grade",
        "display_name": "参考能效等级",
        "group": "标准结果",
        "data_type": "text",
        "unit": "-",
        "editable": False,
        "required": False,
        "role": "result",
        "ui_control": "readonly",
        "v4_field_id": "reference_grade",
    },
    {
        "field_id": "conclusion",
        "display_name": "能效等级",
        "group": "结论",
        "data_type": "text",
        "unit": "-",
        "editable": False,
        "required": False,
        "role": "result",
        "ui_control": "readonly",
        "v4_field_id": "conclusion",
    },
    {
        "field_id": "explanation",
        "display_name": "判定说明",
        "group": "标准结果",
        "data_type": "text",
        "unit": "-",
        "editable": False,
        "required": False,
        "role": "result",
        "ui_control": "readonly",
        "v4_field_id": "explanation",
    },
    {
        "field_id": "missing_fields",
        "display_name": "缺失信息",
        "group": "标准结果",
        "data_type": "text",
        "unit": "-",
        "editable": False,
        "required": False,
        "role": "result",
        "ui_control": "readonly",
        "v4_field_id": "missing_fields",
    },
    {
        "field_id": "auto_note",
        "display_name": "自动备注",
        "group": "附件备注",
        "data_type": "text",
        "unit": "-",
        "editable": False,
        "required": False,
        "role": "result",
        "ui_control": "readonly",
        "v4_field_id": "auto_note",
    },
)

_FORM_NOTE_DEFINITION: dict[str, Any] = {
    "field_id": "form_note",
    "display_name": "填表备注",
    "group": "附件备注",
    "data_type": "text",
    "unit": "-",
    "editable": True,
    "required": False,
    "required_condition": "可选；由填表人员填写",
    "role": "input",
    "ui_control": "text",
    # V4配置使用fill_note，领域层用form_note避免和备注来源混淆。
    "aliases": ("form_note", "fill_note", "填表备注"),
    "v4_field_id": "fill_note",
}

_TECHNICAL_ID_DEFINITION: dict[str, Any] = {
    "field_id": "technical_record_id",
    "display_name": "技术记录ID",
    "group": "系统字段",
    "data_type": "text",
    "unit": "-",
    "editable": False,
    "required": False,
    "role": "calculated",
    "ui_control": "readonly",
    "v4_field_id": "technical_record_id",
}


# 内部评价器使用带单位含义的规范字段，V4表头则沿用人工可读的短字段ID。
# 显式登记两者的直接映射；未列出的字段默认使用同名ID，标记为None的
# 字段是标准计算/路由辅助值，当前不在V4输入列中。
_V4_FIELD_ID_BY_PROFILE: dict[str, dict[str, str | None]] = {
    "transformer": {
        "capacity_kva": "rated_capacity",
        "no_load_loss_w": "no_load_loss",
        "load_loss_w": "load_loss",
    },
    "motor_lv": {
        "rated_voltage_v": "rated_voltage",
        "rated_frequency_hz": "rated_frequency",
        "cooling_method": "cooling",
        "rated_power_kw": "rated_power",
        "rated_speed_rpm": "rated_speed",
        "rated_efficiency": "efficiency",
        "frame_size_mm": None,
    },
    "motor_hv": {
        "rated_voltage_v": "rated_voltage",
        "cooling_method": "cooling",
        "rated_power_kw": "rated_power",
        "rated_speed_rpm": "rated_speed",
        "rated_efficiency": "efficiency",
        "frame_size_mm": None,
        "standard_table": None,
    },
    "motor_pmsm": {
        "voltage_group": None,
        "cooling_group": None,
        "rated_power_kw": "rated_power",
        "rated_speed_rpm": "rated_speed",
        "rated_efficiency": "efficiency",
        # V4只有一个“效率”输入列，具体含义由产品类别决定；
        # efficiency_at_90pct_speed是内部规范化后的派生语义。
        "efficiency_at_90pct_speed": None,
        "poles": "poles",
    },
    "compressor": {
        "input_power_kw": "input_power",
        "volume_flow_m3min": "volume_flow",
        "discharge_pressure_mpa": "discharge_pressure",
        "cooling_method": "cooling",
    },
    "pump_water": {
        "suction": "suction",
        "flow_m3h": "flow",
        "head_m": "head",
        "rated_speed_rpm": "speed",
        "rated_power_kw": "power",
        "pump_efficiency": "efficiency",
    },
    "pump_chemical": {
        "flow_m3h": "flow",
        "head_m": "head",
        "rated_speed_rpm": "speed",
        "rated_power_kw": "power",
        "pump_efficiency": "efficiency",
    },
    "fan": {
        "transmission": "transmission",
        "machine_no": "machine_no",
        "flow_m3h": "flow",
        "fan_pressure_pa": "fan_pressure",
        "inlet_stagnation_pressure_pa": "inlet_stag_pressure",
        "outlet_stagnation_pressure_pa": "outlet_stag_pressure",
        "impeller_power_kw": "impeller_power",
        "rated_power_kw": "rated_power",
        "rated_speed_rpm": "speed",
        "inlet_stagnation_density": "density",
        "isentropic_k": "isentropic_k",
        "fan_efficiency": "design_efficiency",
        "suction": "suction",
        "hvac_use": "hvac_use",
        "inlet_box": "inlet_box",
        "diffuser": "diffuser",
        "variable_blade": "variable_blade",
        "reversible": "reversible",
        "compression_correction": None,
        "pressure_coefficient": None,
        "specific_speed": None,
        "hub_ratio": None,
        "unit_efficiency": None,
        "motor_efficiency": None,
    },
    "blower": {
        "stages": "stages",
        "multi_impeller": "multi_impeller",
        "cantilever": "cantilever",
        "flow_m3h": "flow",
        "rated_power_kw": "rated_power",
        "inlet_absolute_pressure_kpa": "p1",
        "outlet_absolute_pressure_kpa": "p2",
        "inlet_temperature_k": "t1",
        "outlet_temperature_k": "t2",
        "isentropic_k": "isentropic_k",
        "impeller_width_mm": "b2",
        "impeller_diameter_mm": "d2",
        "polytropic_efficiency": "polytropic_efficiency",
        "three_dimensional": "three_dimensional",
        "stage_efficiencies": None,
    },
    "submersible": {
        "subtype": "device_form",
        "flow_m3h": "flow",
        "head_m": "head",
        "rated_speed_rpm": "speed",
        "working_temperature_c": "temperature",
        "rated_power_kw": "power",
        "stages": "stages",
        "pump_efficiency": "efficiency",
        "specified_efficiency": None,
        "efficiency_tolerance": None,
        "pump_form": None,
        "specific_speed": None,
        "motor_efficiency": None,
        "motor_phase": None,
        "motor_structure": None,
        "sync_speed_rpm": None,
    },
    "boiler": {
        "combustion_method": None,
        "fuel_class": None,
        "condensing": None,
        "fuel": "fuel",
        "evaporation_tph": "evaporation",
        "thermal_power_mw": "thermal_power",
        "lower_heating_value_kjkg": "lhv",
        "volatile_matter_percent": "vdaf",
    },
    "heat_treatment": {
        "specification": None,
        "rated_power_kw": "rated_power",
        "rated_temperature_c": "rated_temperature",
        "equivalent_weight_t": "equivalent_weight",
        "total_electricity_kwh": "electricity",
        "fuel_consumption": "fuel_consumption",
        "fuel_calorific_value_kjkg": "fuel_heat",
    },
    "heat_pump_chiller": {
        "product_standard": "product_standard",
        "unit_type": "unit_type",
        "source": "source",
        "evaluation_system": "evaluation_system",
        "heating_capacity_kw": "heating_capacity",
        "cooling_capacity_kw": "cooling_capacity",
        "rated_power_kw": "rated_power",
    },
    "heat_pump_water_heater": {
        "unit_type": None,
        "heating_method": "heating_method",
        "heating_capacity_kw": "heating_capacity",
        "rated_power_kw": "rated_power",
        "with_pump": "with_pump",
        "cop": "cop",
    },
    "duct_ac": {
        # V4的category同时携带产品类型；product_type是内部拆分结果，
        # 不能与公共category重复声明为同一直接输入列。
        "product_type": None,
        "cooling_source": "cooling",
        "mode": "mode",
        "cooling_capacity_w": "cooling_capacity",
        "rated_power_kw": "rated_power",
        "seer": None,
        "apf": None,
        "iplv": None,
        "eer": None,
    },
    "unitary_ac": {
        "cooling_source": "cooling",
        "mode": "mode",
        "cooling_capacity_w": "cooling_capacity",
        "rated_power_kw": "rated_power",
        "seer": None,
        "apf": None,
        "iplv": None,
        "aeer": None,
        "cop": None,
    },
    "multi_split_ac": {
        "cooling_capacity_w": "cooling_capacity",
        "heating_capacity_w": "heating_capacity",
        "rated_power_kw": "rated_power",
        "external_static_pressure_pa": "external_static",
        "static_pressure_correction_factor": None,
        "static_pressure_corrected_metric": None,
        "seer": None,
        "apf": None,
        "iplv_c": None,
        "hspf": None,
        "eer": None,
        "cop_minus12": None,
        "cop_minus20": None,
    },
}


# 规范字段的显示名/单位和V4原始表头有少量差异。两者同时保留，避免
# 为了模板兼容而把领域层的单位（例如电机内部统一用V）静默改掉。
_V4_DISPLAY_NAME_BY_PROFILE: dict[str, dict[str, str]] = {
    "motor_lv": {"rated_efficiency": "效率"},
    "motor_hv": {"rated_efficiency": "效率"},
    "motor_pmsm": {"rated_efficiency": "效率", "efficiency_at_90pct_speed": "效率"},
    "compressor": {"input_power_kw": "驱动电动机额定功率（合计）"},
    "pump_water": {"suction": "单吸/双吸"},
    "fan": {
        "fan_pressure_pa": "风机压力pF",
        "rated_power_kw": "额定功率",
        "fan_efficiency": "最高通风机效率ηr",
    },
    "blower": {"flow_m3h": "容积流量"},
    "submersible": {"subtype": "设备形式"},
    "heat_pump_chiller": {
        "aux_metric1_value": "辅助约束指标1设计值",
        "aux_metric2_value": "辅助约束指标2设计值",
    },
    "heat_pump_water_heater": {"cop": "性能系数"},
    "boiler": {"fuel": "能源/燃料品种"},
    "heat_treatment": {"total_electricity_kwh": "电炉总耗电量"},
    "duct_ac": {"mode": "机组类型"},
    "unitary_ac": {"mode": "机组类型"},
}

_V4_UNIT_BY_PROFILE: dict[str, dict[str, str]] = {
    "motor_lv": {"rated_voltage_v": "kV"},
    "motor_hv": {"rated_voltage_v": "kV"},
    "motor_pmsm": {"rated_voltage_v": "kV"},
    "heat_pump_chiller": {
        "primary_metric_value": "无量纲",
        "aux_metric1_value": "无量纲",
        "aux_metric2_value": "无量纲",
    },
    "heat_treatment": {"fuel_consumption": "m³", "fuel_calorific_value_kjkg": "kJ/m³"},
    "boiler": {"lower_heating_value_kjkg": "kJ/kg或kJ/m³"},
    "duct_ac": {"cooling_capacity_w": "kW"},
    "unitary_ac": {"cooling_capacity_w": "kW"},
    "multi_split_ac": {
        "cooling_capacity_w": "kW",
        "heating_capacity_w": "kW",
    },
}


# V4中为公开sheet保留、但早期内部profile没有单独字段的输入列。它们
# 仍是用户填写的出厂设计/额定参数，因此在公共元数据中补齐；评价器
# 继续通过input_normalization接收这些规范ID。
_PUBLIC_EXTRA_FIELD_DEFINITIONS: dict[str, tuple[dict[str, Any], ...]] = {
    "duct_ac": (
        {
            "field_id": "enthalpy_difference",
            "display_name": "焓差类型",
            "unit": "-",
            "required": True,
            "required_condition": "按机组类别条件填写",
            "v4_field_id": "enthalpy",
        },
        {
            "field_id": "rated_power_kw",
            "display_name": "额定功率",
            "unit": "kW",
            "required": True,
            "v4_field_id": "rated_power",
        },
        {
            "field_id": "indicator_value",
            "display_name": "设计指标值",
            "unit": "按指标",
            "required": True,
            "v4_field_id": "indicator_value",
        },
    ),
    "unitary_ac": (
        {
            "field_id": "cooling_source",
            "display_name": "冷却方式",
            "unit": "-",
            "required": True,
            "v4_field_id": "cooling",
        },
        {
            "field_id": "rated_power_kw",
            "display_name": "额定功率",
            "unit": "kW",
            "required": True,
            "v4_field_id": "rated_power",
        },
        {
            "field_id": "indicator_value",
            "display_name": "设计指标值",
            "unit": "按指标",
            "required": True,
            "v4_field_id": "indicator_value",
        },
    ),
    "multi_split_ac": (
        {
            "field_id": "cooling_source",
            "display_name": "水冷式类型",
            "unit": "-",
            "required": True,
            "required_condition": "仅水冷式多联机填写",
            "v4_field_id": "water_source",
        },
        {
            "field_id": "rated_power_kw",
            "display_name": "额定功率",
            "unit": "kW",
            "required": True,
            "v4_field_id": "rated_power",
        },
        {
            "field_id": "primary_metric_value",
            "display_name": "分级指标设计值",
            "unit": "无量纲",
            "required": True,
            "v4_field_id": "primary_metric_value",
        },
        {
            "field_id": "eer_min_value",
            "display_name": "EER设计值（用于EERmin校核）",
            "unit": "W/W",
            "required": False,
            "required_condition": "风冷式且制冷量≤14kW时必填",
            "v4_field_id": "eer_min_value",
        },
        {
            "field_id": "cop_minus12_value",
            "display_name": "COP(-12℃)设计值",
            "unit": "W/W",
            "required": False,
            "required_condition": "低温多联机条件必填",
            "v4_field_id": "cop_minus12_value",
        },
        {
            "field_id": "cop_minus20_value",
            "display_name": "COP(-20℃)设计值",
            "unit": "W/W",
            "required": False,
            "required_condition": "低温多联机条件必填",
            "v4_field_id": "cop_minus20_value",
        },
    ),
}

_V4_COMMON_PREFIX = (
    "seq", "device_name", "model", "quantity", "category", "location",
)
_V4_RESULT_ORDER = (
    "conclusion", "standard_code", "standard_table", "reference_grade",
    "explanation", "missing_fields", "technical_record_id", "photo",
    "fill_note", "auto_note",
)
_V4_DEVICE_INPUT_ORDER: dict[str, tuple[str, ...]] = {
    "transformer": ("rated_capacity", "core_material", "insulation", "connection", "no_load_loss", "load_loss"),
    "motor": ("rated_voltage", "rated_frequency", "cooling", "rated_power", "poles", "rated_speed", "efficiency"),
    "compressor": ("input_power", "volume_flow", "discharge_pressure", "cooling", "specific_power"),
    "centrifugal_pump": ("suction", "flow", "head", "speed", "power", "stages", "efficiency"),
    "centrifugal_fan": ("transmission", "suction", "hvac_use", "inlet_box", "flow", "fan_pressure", "outlet_stag_pressure", "inlet_stag_pressure", "rated_power", "impeller_power", "speed", "machine_no", "density", "isentropic_k", "design_efficiency"),
    "axial_fan": ("transmission", "inlet_box", "diffuser", "variable_blade", "reversible", "flow", "fan_pressure", "rated_power", "impeller_power", "speed", "machine_no", "density", "isentropic_k", "hub_ratio", "design_efficiency"),
    "blower": ("stages", "multi_impeller", "cantilever", "flow", "rated_power", "p1", "p2", "t1", "t2", "isentropic_k", "b2", "d2", "polytropic_efficiency", "three_dimensional"),
    "submersible_pump": ("device_form", "flow", "head", "speed", "temperature", "power", "stages", "efficiency"),
    "industrial_boiler": ("fuel", "evaporation", "thermal_power", "lhv", "vdaf", "design_efficiency"),
    "heat_treatment": ("energy_type", "rated_power", "rated_temperature", "equivalent_weight", "electricity", "fuel_consumption", "fuel_heat"),
    "heat_pump_chiller": ("product_standard", "unit_type", "source", "evaluation_system", "cooling_capacity", "heating_capacity", "rated_power", "primary_metric_value", "aux_metric1_value", "aux_metric2_value"),
    "heat_pump_water_heater": ("heating_method", "with_pump", "heating_capacity", "rated_power", "cop"),
    "duct_ac": ("cooling", "mode", "enthalpy", "cooling_capacity", "rated_power", "indicator_value"),
    "unitary_ac": ("cooling", "mode", "cooling_capacity", "rated_power", "indicator_value"),
    "multi_split_ac": ("water_source", "cooling_capacity", "heating_capacity", "rated_power", "external_static", "primary_metric_value", "eer_min_value", "cop_minus12_value", "cop_minus20_value"),
}


_INTEGER_FIELD_IDS = frozenset({
    "frame_size_mm", "poles", "stages", "production_year",
})
_PERCENT_FIELD_IDS = frozenset({
    "rated_efficiency", "efficiency_at_90pct_speed", "pump_efficiency",
    "fan_efficiency", "unit_efficiency", "motor_efficiency",
    "polytropic_efficiency",
})
# V4已明确给出上下界、但不属于百分比或正数提示的数值字段。
# 范围由V4契约和既有标准规则共同确认；有限范围字段不会套用正数提示。
_RANGE_FIELD_BOUNDS = {
    "isentropic_k": (Decimal("1"), Decimal("2")),
    "working_temperature_c": (Decimal("0"), Decimal("100")),
}
_RANGE_FIELD_IDS = frozenset(_RANGE_FIELD_BOUNDS)
# V4 marks the shared "级数" field as a positive integer.  It has no finite
# upper bound in the template, so keep its lower bound separate from the
# finite-range map above.  This lets API/desktop fallbacks expose the same
# input hint without inventing a maximum stage count.
_INTEGER_MINIMUM_BOUNDS = {
    "stages": Decimal("1"),
}
# V4明确允许为零、但不得为负的数值字段。它们不能混入正数集合，
# 否则元数据桥接会把合法的0误报为“必须大于0”。
_NON_NEGATIVE_FIELD_IDS = frozenset({
    "external_static_pressure_pa",
})
_POSITIVE_FIELD_IDS = frozenset({
    "capacity_kva", "no_load_loss_w", "load_loss_w", "rated_power_kw",
    "input_power_kw", "volume_flow_m3min", "discharge_pressure_mpa",
    "specific_power", "flow_m3h", "head_m", "rated_speed_rpm",
    "fan_pressure_pa", "inlet_stagnation_pressure_pa",
    "outlet_stagnation_pressure_pa", "impeller_power_kw",
    "inlet_stagnation_density", "specific_speed", "impeller_width_mm",
    "impeller_diameter_mm", "b2_d2", "heating_capacity_kw",
    "cooling_capacity_kw", "cooling_capacity_w", "heating_capacity_w",
    "rated_power_v", "rated_power", "cop", "seer", "apf", "iplv",
    "aeer", "eer", "cop_minus12", "cop_minus20", "primary_metric_value",
    "aux_metric1_value", "aux_metric2_value", "indicator_value",
    "eer_min_value", "cop_minus12_value", "cop_minus20_value",
    "equivalent_weight_t",
    "total_electricity_kwh", "fuel_consumption", "fuel_calorific_value_kjkg",
    "evaporation_tph", "thermal_power_mw", "lower_heating_value_kjkg",
    "inlet_absolute_pressure_kpa", "outlet_absolute_pressure_kpa", "inlet_temperature_k", "outlet_temperature_k", "impeller_width_mm", "impeller_diameter_mm",
    "rated_temperature_c",
    "machine_no",
    "static_pressure_correction_factor",
    "static_pressure_corrected_metric",
})


def _bound_for(field_id: str, *, profile: str) -> tuple[Decimal | None, Decimal | None]:
    if field_id in _PERCENT_FIELD_IDS:
        return Decimal("1"), Decimal("100")
    if field_id in _RANGE_FIELD_BOUNDS:
        return _RANGE_FIELD_BOUNDS[field_id]
    if field_id in _INTEGER_MINIMUM_BOUNDS:
        return _INTEGER_MINIMUM_BOUNDS[field_id], None
    if field_id in _NON_NEGATIVE_FIELD_IDS:
        return Decimal("0"), None
    if field_id == "design_efficiency":
        # 冷凝锅炉的110%上限由V4条件规则进一步决定；这里提供安全的
        # 总体范围，非冷凝分支仍由现有验证服务收窄到100。
        return Decimal("1"), Decimal("110")
    if field_id == "volatile_matter_percent":
        return Decimal("0"), Decimal("100")
    if field_id in _POSITIVE_FIELD_IDS:
        return Decimal("0"), None
    return None, None


def _data_type(field_id: str, unit: str) -> str:
    if field_id in _INTEGER_FIELD_IDS:
        return "integer"
    if field_id in _PERCENT_FIELD_IDS or field_id in {"design_efficiency", "volatile_matter_percent"}:
        return "percentage"
    if field_id in _RANGE_FIELD_IDS:
        return "number"
    if field_id in {"stage_efficiencies"}:
        return "text"
    if field_id in _NON_NEGATIVE_FIELD_IDS or field_id in _POSITIVE_FIELD_IDS or unit not in {"", "-", "No."}:
        return "number"
    return "text"


def _ui_control(field_id: str, data_type: str, enum_name: str) -> str:
    if enum_name:
        return "select"
    if data_type in {"integer", "number", "percentage"}:
        return "number"
    return "text"


def _condition_note(note: str) -> str:
    markers = ("必填", "条件", "至少", "多级", "电炉", "燃料炉", "类别", "自动计算")
    return note if any(marker in note for marker in markers) else ""


def _field_from_spec(
    profile: str,
    item: Mapping[str, Any],
    source_profiles: tuple[str, ...],
    required_by_profile: tuple[tuple[str, bool], ...] = (),
) -> "FieldSpec":
    field_id = str(item.get("name", ""))
    display_name = str(item.get("label", field_id))
    unit = str(item.get("unit", "-") or "-")
    enum_name = str(item.get("enum_name", "") or "")
    data_type = _data_type(field_id, unit)
    minimum, maximum = _bound_for(field_id, profile=profile)
    profile_mapping = _V4_FIELD_ID_BY_PROFILE.get(profile, {})
    # 生产年份及标准专属计算辅助字段用于核心匹配，当前V4模板不暴露。
    v4_field_id = profile_mapping[field_id] if field_id in profile_mapping else (
        None if field_id == "production_year" else field_id
    )
    aliases_list = [field_id, display_name]
    if field_id == "model":
        aliases_list.append("设备型号")
    if v4_field_id and v4_field_id not in aliases_list:
        aliases_list.append(v4_field_id)
    v4_display_name = _V4_DISPLAY_NAME_BY_PROFILE.get(profile, {}).get(field_id, display_name)
    if v4_display_name not in aliases_list:
        aliases_list.append(v4_display_name)
    v4_unit = _V4_UNIT_BY_PROFILE.get(profile, {}).get(field_id, unit)
    aliases = tuple(dict.fromkeys(aliases_list))
    required = bool(item.get("required", True))
    required_condition = _condition_note(str(item.get("note", "") or ""))
    if required_by_profile and len({value for _, value in required_by_profile}) > 1:
        # 一个公共sheet可能覆盖多个内部标准。这里不能把某个profile的
        # 必填要求静默传播到所有产品，只保守显示为条件必填，并保留
        # 每个profile的原始要求供路由后的校验层使用。
        required = False
        suffix = "不同内部标准profile的必填要求不同"
        required_condition = f"{required_condition}；{suffix}" if required_condition else suffix
    return FieldSpec(
        field_id=field_id,
        display_name=display_name,
        group="设备参数",
        data_type=data_type,
        unit=unit,
        aliases=aliases,
        editable=True,
        required=required,
        required_condition=required_condition,
        minimum=minimum,
        maximum=maximum,
        enum_name=enum_name,
        enum_values=tuple(ENUM_VALUES.get(enum_name, ())),
        role="input",
        ui_control="hidden" if v4_field_id is None else _ui_control(field_id, data_type, enum_name),
        v4_field_id=v4_field_id,
        source_profiles=source_profiles,
        required_by_profile=required_by_profile,
        v4_display_name=v4_display_name,
        v4_unit=v4_unit,
    )


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """跨界面复用的字段定义。

    ``data_type`` 使用领域层稳定代码（text/number/integer/percentage/image），
    展示层如需中文类型名称应在自己的适配器中转换。所有集合均为tuple，
    防止窗口或接口层意外改写注册表。
    """

    field_id: str
    display_name: str
    group: str
    data_type: str
    unit: str
    aliases: tuple[str, ...] = ()
    editable: bool = True
    required: bool = False
    required_condition: str = ""
    required_by_profile: tuple[tuple[str, bool], ...] = ()
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    enum_name: str = ""
    enum_values: tuple[str, ...] = ()
    role: str = "input"
    ui_control: str = "text"
    v4_field_id: str | None = None
    v4_display_name: str | None = None
    v4_unit: str | None = None
    source_profiles: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """返回适合JSON/表单适配器使用的普通字典副本。"""

        def bound(value: Decimal | None) -> int | float | None:
            if value is None:
                return None
            return int(value) if value == value.to_integral_value() else float(value)

        return {
            "field_id": self.field_id,
            "display_name": self.display_name,
            "group": self.group,
            "data_type": self.data_type,
            "unit": self.unit,
            "aliases": list(self.aliases),
            "editable": self.editable,
            "required": self.required,
            "required_condition": self.required_condition,
            "required_by_profile": [
                {"profile": profile, "required": required}
                for profile, required in self.required_by_profile
            ],
            "minimum": bound(self.minimum),
            "maximum": bound(self.maximum),
            "enum_name": self.enum_name,
            "enum_values": list(self.enum_values),
            "role": self.role,
            "ui_control": self.ui_control,
            "v4_field_id": self.v4_field_id,
            "v4_display_name": self.v4_display_name,
            "v4_unit": self.v4_unit,
            "source_profiles": list(self.source_profiles),
        }

    def required_for(self, internal_profile: str | None = None) -> bool:
        """返回路由到某个内部profile后的必填要求。

        公共“电动机”sheet同时覆盖低压、高压和永磁标准，个别字段在这些
        标准中的必填性不同。调用方完成路由后应使用本方法，而不是直接
        读取公共字段的保守 ``required`` 值。
        """

        if internal_profile and self.required_by_profile:
            for profile, required in self.required_by_profile:
                if profile == internal_profile:
                    return required
        return self.required


def _common_field_from_definition(item: Mapping[str, Any]) -> FieldSpec:
    field_id = str(item["field_id"])
    display_name = str(item["display_name"])
    v4_display_name = str(item.get("v4_display_name", display_name))
    v4_unit = str(item.get("v4_unit", item["unit"]))
    aliases = list(item.get("aliases", (field_id, display_name)))
    if v4_display_name not in aliases:
        aliases.append(v4_display_name)
    return FieldSpec(
        field_id=field_id,
        display_name=display_name,
        group=str(item["group"]),
        data_type=str(item["data_type"]),
        unit=str(item["unit"]),
        aliases=tuple(dict.fromkeys(aliases)),
        editable=bool(item.get("editable", True)),
        required=bool(item.get("required", False)),
        required_condition=str(item.get("required_condition", "")),
        minimum=item.get("minimum"),
        maximum=item.get("maximum"),
        enum_name=str(item.get("enum_name", "") or ""),
        enum_values=tuple(item.get("enum_values", ())),
        role=str(item.get("role", "input")),
        ui_control=str(item.get("ui_control", "text")),
        v4_field_id=item.get("v4_field_id", field_id),
        v4_display_name=v4_display_name,
        v4_unit=v4_unit,
        source_profiles=(),
    )


def _result_field_from_definition(item: Mapping[str, Any]) -> FieldSpec:
    field_id = str(item["field_id"])
    display_name = str(item["display_name"])
    v4_display_name = str(item.get("v4_display_name", display_name))
    v4_unit = str(item.get("v4_unit", item["unit"]))
    return FieldSpec(
        field_id=field_id,
        display_name=display_name,
        group=str(item["group"]),
        data_type=str(item["data_type"]),
        unit=str(item["unit"]),
        aliases=tuple(dict.fromkeys((field_id, display_name, v4_display_name))),
        editable=False,
        required=False,
        role=str(item.get("role", "result")),
        ui_control="readonly",
        v4_field_id=item.get("v4_field_id", field_id),
        v4_display_name=v4_display_name,
        v4_unit=v4_unit,
        source_profiles=(),
    )


def _extra_field_from_definition(public_type: str, item: Mapping[str, Any]) -> FieldSpec:
    field_id = str(item["field_id"])
    display_name = str(item["display_name"])
    unit = str(item.get("unit", "-") or "-")
    v4_field_id = item.get("v4_field_id", field_id)
    v4_display_name = str(item.get("v4_display_name", display_name))
    v4_unit = str(item.get("v4_unit", unit))
    aliases = [field_id, display_name]
    if v4_field_id and v4_field_id not in aliases:
        aliases.append(str(v4_field_id))
    if v4_display_name not in aliases:
        aliases.append(v4_display_name)
    data_type = _data_type(field_id, unit)
    minimum, maximum = _bound_for(field_id, profile=public_type)
    return FieldSpec(
        field_id=field_id,
        display_name=display_name,
        group="设备参数",
        data_type=data_type,
        unit=unit,
        aliases=tuple(dict.fromkeys(aliases)),
        editable=True,
        required=bool(item.get("required", False)),
        required_condition=str(item.get("required_condition", "")),
        minimum=minimum,
        maximum=maximum,
        role="input",
        ui_control=_ui_control(field_id, data_type, ""),
        v4_field_id=str(v4_field_id) if v4_field_id else None,
        v4_display_name=v4_display_name,
        v4_unit=v4_unit,
        source_profiles=(),
    )


def _apply_public_v4_overrides(fields: list[FieldSpec], public_type: str) -> None:
    """处理同一内部fan profile在两个V4 sheet中的字段差异。"""

    overrides: dict[str, dict[str, Any]] = {}
    if public_type == "axial_fan":
        overrides = {
            "hub_ratio": {
                "v4_field_id": "hub_ratio",
                "v4_display_name": "轮毂比",
                "v4_unit": "-",
                "data_type": "number",
                "minimum": Decimal("0"),
                "maximum": Decimal("1"),
                "ui_control": "number",
            },
            "suction": {"v4_field_id": None, "ui_control": "hidden"},
            "hvac_use": {"v4_field_id": None, "ui_control": "hidden"},
            "inlet_stagnation_pressure_pa": {"v4_field_id": None, "ui_control": "hidden"},
            "outlet_stagnation_pressure_pa": {"v4_field_id": None, "ui_control": "hidden"},
        }
    elif public_type == "centrifugal_fan":
        overrides = {
            "hub_ratio": {"v4_field_id": None, "ui_control": "hidden"},
            "diffuser": {"v4_field_id": None, "ui_control": "hidden"},
            "variable_blade": {"v4_field_id": None, "ui_control": "hidden"},
            "reversible": {"v4_field_id": None, "ui_control": "hidden"},
        }
    for index, field in enumerate(fields):
        values = overrides.get(field.field_id)
        if not values:
            continue
        aliases = list(field.aliases)
        v4_display_name = values.get("v4_display_name", field.v4_display_name)
        if v4_display_name and v4_display_name not in aliases:
            aliases.append(v4_display_name)
        fields[index] = replace(
            field,
            aliases=tuple(dict.fromkeys(aliases)),
            v4_field_id=values.get("v4_field_id", field.v4_field_id),
            v4_display_name=v4_display_name,
            v4_unit=values.get("v4_unit", field.v4_unit),
            data_type=values.get("data_type", field.data_type),
            minimum=values.get("minimum", field.minimum),
            maximum=values.get("maximum", field.maximum),
            ui_control=values.get("ui_control", field.ui_control),
        )


def _apply_public_enum_overrides(fields: list[FieldSpec], public_type: str) -> None:
    """Attach only the verified lightweight enum families to a public profile."""

    enum_definitions = _PUBLIC_ENUM_VALUES.get(public_type, {})
    if not enum_definitions:
        return
    for index, field in enumerate(fields):
        definition = enum_definitions.get(field.field_id)
        if definition is None:
            continue
        enum_name, values = definition
        fields[index] = replace(
            field,
            enum_name=enum_name,
            enum_values=values,
            ui_control="select",
        )


def _reorder_fields_for_v4(fields: list[FieldSpec], public_type: str) -> list[FieldSpec]:
    """按V4正式表头重排可见字段，内部隐藏字段插入到结果区之前。"""

    order = _V4_COMMON_PREFIX + _V4_DEVICE_INPUT_ORDER.get(public_type, ()) + _V4_RESULT_ORDER
    ordered: list[FieldSpec] = []
    used: set[int] = set()
    for field_id in order:
        for index, field in enumerate(fields):
            if index in used or field.v4_field_id != field_id:
                continue
            ordered.append(field)
            used.add(index)
            break

    # 同一V4列对应多个内部语义（例如动态效率）时，未被主顺序消费的
    # 剩余项仍保留，但放到标准结果前，避免打乱V4固定后缀。
    remaining = [field for index, field in enumerate(fields) if index not in used]
    hidden_or_extra = [field for field in remaining if field.v4_field_id is None]
    visible_unordered = [field for field in remaining if field.v4_field_id is not None]
    input_count = len(_V4_COMMON_PREFIX) + len(_V4_DEVICE_INPUT_ORDER.get(public_type, ()))
    return ordered[:input_count] + hidden_or_extra + visible_unordered + ordered[input_count:]


@dataclass(frozen=True, slots=True)
class DeviceProfile:
    """一个V4公共设备类型的只读元数据快照。"""

    public_type: str
    display_name: str
    sheet_name: str
    internal_profiles: tuple[str, ...]
    standards: tuple[str, ...]
    fields: tuple[FieldSpec, ...]
    routing_note: str = ""

    @property
    def input_fields(self) -> tuple[FieldSpec, ...]:
        return tuple(field for field in self.fields if field.role == "input")

    @property
    def calculated_fields(self) -> tuple[FieldSpec, ...]:
        return tuple(field for field in self.fields if field.role == "calculated")

    @property
    def result_fields(self) -> tuple[FieldSpec, ...]:
        return tuple(field for field in self.fields if field.role == "result")

    def field(self, field_id: str) -> FieldSpec:
        for item in self.fields:
            if item.field_id == field_id:
                return item
        raise KeyError(f"设备{self.public_type}不存在字段: {field_id}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "public_type": self.public_type,
            "display_name": self.display_name,
            "sheet_name": self.sheet_name,
            "internal_profiles": list(self.internal_profiles),
            "standards": list(self.standards),
            "routing_note": self.routing_note,
            "fields": [field.as_dict() for field in self.fields],
        }


def _build_profile(public_type: str) -> DeviceProfile:
    internal_profiles = profiles_for_public_type(public_type)
    if not internal_profiles:
        raise KeyError(public_type)
    fields: list[FieldSpec] = []
    seen: set[str] = set()

    # V4固定前缀的“序号”是锁定计算列，必须排在所有输入之前。
    seq_definition = next(item for item in _COMMON_RESULT_DEFINITIONS if item["field_id"] == "seq")
    fields.append(_result_field_from_definition(seq_definition))
    seen.add("seq")

    # “铭牌照片”属于V4固定后缀，先跳过，待标准/计算结果列之后追加。
    for item in _COMMON_FIELD_DEFINITIONS:
        if item["field_id"] == "photo":
            continue
        field = _common_field_from_definition(item)
        fields.append(field)
        seen.add(field.field_id)

    for profile in internal_profiles:
        spec = DEVICE_SPECS[profile]
        for item in spec.get("fields", ()):
            field_id = str(item.get("name", ""))
            if not field_id or field_id in seen:
                # 公共字段（例如category/model）已经在统一前缀中创建；
                # 保留内部profile使用过的显示名称作为别名，避免“标准炉型”
                # 这类设备专属表头被误判为另一个字段。
                if field_id in seen:
                    index = next(index for index, field in enumerate(fields) if field.field_id == field_id)
                    current = fields[index]
                    aliases = tuple(dict.fromkeys((*current.aliases, str(item.get("label", field_id)))))
                    sources = tuple(dict.fromkeys((*current.source_profiles, profile)))
                    fields[index] = replace(current, aliases=aliases, source_profiles=sources)
                continue
            source_profiles_for_field = tuple(
                candidate for candidate in internal_profiles
                if any(str(candidate_item.get("name", "")) == field_id for candidate_item in DEVICE_SPECS[candidate].get("fields", ()))
            )
            required_by_profile = tuple(
                (
                    candidate,
                    bool(next(
                        candidate_item.get("required", True)
                        for candidate_item in DEVICE_SPECS[candidate].get("fields", ())
                        if str(candidate_item.get("name", "")) == field_id
                    )),
                )
                for candidate in source_profiles_for_field
            )
            fields.append(_field_from_spec(profile, item, source_profiles_for_field, required_by_profile))
            seen.add(field_id)

    for item in _PUBLIC_EXTRA_FIELD_DEFINITIONS.get(public_type, ()):
        field_id = str(item["field_id"])
        if field_id in seen:
            continue
        fields.append(_extra_field_from_definition(public_type, item))
        seen.add(field_id)

    # 目录匹配用的内部辅助字段（当前只有production_year）不应插入V4
    # 公共输入顺序；保留在模型中供核心服务使用，但标记为隐藏并置于
    # 可见设备参数之后。
    fields[:] = [field for field in fields if field.v4_field_id is not None] + [
        field for field in fields if field.v4_field_id is None
    ]
    _apply_public_v4_overrides(fields, public_type)
    _apply_public_enum_overrides(fields, public_type)
    fields[:] = [field for field in fields if field.v4_field_id is not None] + [
        field for field in fields if field.v4_field_id is None
    ]

    for item in _COMMON_RESULT_DEFINITIONS:
        field_id = str(item["field_id"])
        if field_id in seen or field_id == "auto_note":
            continue
        fields.append(_result_field_from_definition(item))
        seen.add(field_id)

    # V4固定后缀：技术记录ID为隐藏系统列，照片和填表备注可编辑，自动备注
    # 由数据质量服务生成并锁定。该顺序也供未来非Excel界面复用。
    fields.append(_result_field_from_definition(_TECHNICAL_ID_DEFINITION))
    seen.add("technical_record_id")
    photo = _common_field_from_definition(next(item for item in _COMMON_FIELD_DEFINITIONS if item["field_id"] == "photo"))
    fields.append(photo)
    seen.add(photo.field_id)
    form_note = _common_field_from_definition(_FORM_NOTE_DEFINITION)
    fields.append(form_note)
    seen.add(form_note.field_id)
    auto_note = next(item for item in _COMMON_RESULT_DEFINITIONS if item["field_id"] == "auto_note")
    fields.append(_result_field_from_definition(auto_note))
    seen.add("auto_note")

    standards: list[str] = []
    for profile in internal_profiles:
        standard = str(DEVICE_SPECS[profile].get("standard", "") or "")
        if standard and standard not in standards:
            standards.append(standard)
    if len(internal_profiles) > 1:
        routing_note = {
            "motor": "按设备类别、profile或额定电压路由低压/高压/永磁标准",
            "centrifugal_pump": "按设备类别或profile路由清水泵/石油化工泵标准",
            "centrifugal_fan": "按V4通风机sheet路由离心通风机标准",
            "axial_fan": "按V4通风机sheet路由轴流通风机标准",
        }.get(public_type, "按公共类型路由内部标准")
    else:
        routing_note = ""
    fields = _reorder_fields_for_v4(fields, public_type)
    return DeviceProfile(
        public_type=public_type,
        display_name=PUBLIC_DEVICE_NAMES[public_type],
        sheet_name=PUBLIC_DEVICE_NAMES[public_type],
        internal_profiles=internal_profiles,
        standards=tuple(standards),
        fields=tuple(fields),
        routing_note=routing_note,
    )


DEVICE_PROFILES: Mapping[str, DeviceProfile] = MappingProxyType({
    public_type: _build_profile(public_type)
    for public_type in PUBLIC_DEVICE_TYPES
})


class DeviceMetadataError(ValueError):
    """公共设备元数据不存在或无法安全解析。"""


def _public_code(value: str) -> str:
    text = str(value)
    if text in DEVICE_PROFILES:
        return text
    return PUBLIC_TYPE_BY_SHEET.get(text, text)


def list_device_profiles() -> tuple[DeviceProfile, ...]:
    """按V4顺序返回15个公共设备元数据。"""

    return tuple(DEVICE_PROFILES[public_type] for public_type in PUBLIC_DEVICE_TYPES)


def get_device_profile(public_device_type: str) -> DeviceProfile:
    """按公共代码或V4中文sheet名称取得只读元数据。"""

    public_code = _public_code(public_device_type)
    try:
        return DEVICE_PROFILES[public_code]
    except KeyError as exc:
        raise DeviceMetadataError(f"未知公共设备类型: {public_device_type}") from exc


def get_field_spec(public_device_type: str, field_id: str) -> FieldSpec:
    """取得一个公共设备字段；不存在时给出明确错误。"""

    return get_device_profile(public_device_type).field(str(field_id))


def metadata_summary() -> dict[str, Any]:
    """返回轻量注册表摘要，供诊断命令和跨平台桥接层使用。"""

    return {
        "public_device_types": list(PUBLIC_DEVICE_TYPES),
        "public_device_count": len(PUBLIC_DEVICE_TYPES),
        "internal_profile_count": len(DEVICE_SPECS),
        "profiles": [
            {
                "public_type": profile.public_type,
                "sheet": profile.sheet_name,
                "internal_profiles": list(profile.internal_profiles),
                "standards": list(profile.standards),
                "field_count": len(profile.fields),
                "input_field_count": len(profile.input_fields),
                "result_field_count": len(profile.result_fields),
            }
            for profile in list_device_profiles()
        ],
    }


__all__ = [
    "DeviceMetadataError",
    "DeviceProfile",
    "FieldSpec",
    "DEVICE_PROFILES",
    "get_device_profile",
    "get_field_spec",
    "list_device_profiles",
    "metadata_summary",
]
