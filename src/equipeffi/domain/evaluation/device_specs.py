from __future__ import annotations

from copy import deepcopy
from typing import Any


MOTOR_COOLING_OPTIONS: tuple[str, ...] = (
    "IC01", "IC11", "IC21", "IC31", "IC81W", "IC86W", "IC71W(IC3W7)",
    "IC411", "IC416", "IC511", "IC516", "IC611", "IC616", "IC666",
    "不适用", "其他（请备注说明）",
)


ENUM_VALUES: dict[str, tuple[str, ...]] = {
    "EV_COOLING_MOTOR_HV": MOTOR_COOLING_OPTIONS,
}


def f(
    name: str,
    label: str,
    unit: str = "-",
    required: bool = True,
    note: str = "",
    enum_name: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "label": label,
        "unit": unit,
        "required": required,
        "note": note,
        "enum_name": enum_name,
    }


DEVICE_SPECS: dict[str, dict[str, Any]] = {
    "transformer": {
        "name": "变压器", "standard": "GB 20052-2024",
        "fields": [f("model", "型号", required=False, note="用于淘汰目录匹配"), f("category", "设备类别"), f("capacity_kva", "额定容量", "kVA"), f("core_material", "铁芯材质", required=False, note="按类别条件必填"), f("insulation", "绝缘耐热等级", required=False, note="干式类别条件必填"), f("connection", "连接组标号", required=False, note="部分油浸式类别条件必填"), f("no_load_loss_w", "空载损耗", "W"), f("load_loss_w", "负载损耗", "W")],
        "example": {"model": "T1", "category": "10kV油浸式三相双绕组无励磁调压配电变压器", "capacity_kva": 100, "core_material": "电工钢带", "connection": "Dyn11/Yzn11", "no_load_loss_w": 120, "load_loss_w": 1140},
    },
    "motor_lv": {
        "name": "低压电动机", "standard": "GB 18613-2020",
        "fields": [f("model", "型号", required=False), f("category", "设备类别"), f("frame_size_mm", "机座号", "mm", required=False, note="产业目录淘汰条件需要"), f("rated_voltage_v", "额定电压", "V", required=False), f("rated_frequency_hz", "额定频率", "Hz", required=False), f("cooling_method", "冷却方式", required=False, enum_name="EV_COOLING_MOTOR_HV"), f("rated_power_kw", "额定功率", "kW"), f("poles", "极数", "极"), f("rated_speed_rpm", "额定转速", "r/min", required=False), f("rated_efficiency", "额定效率", "%", note="98%填写98")],
        "example": {"model": "M1", "category": "三相异步电动机（一般用途）", "rated_power_kw": 7.5, "poles": 4, "rated_efficiency": 98},
    },
    "motor_hv": {
        "name": "高压电动机", "standard": "GB 30254-2024",
        "fields": [f("model", "型号", required=False), f("category", "设备类别"), f("rated_voltage_v", "额定电压", "V"), f("cooling_method", "冷却方式", enum_name="EV_COOLING_MOTOR_HV"), f("standard_table", "匹配表/条款", required=False, note="无法唯一选表时填写"), f("rated_power_kw", "额定功率", "kW"), f("poles", "极数", "极", required=False), f("rated_speed_rpm", "额定转速", "r/min", required=False), f("rated_efficiency", "额定效率", "%")],
        "example": {"category": "卧式", "rated_voltage_v": 6000, "cooling_method": "IC01", "standard_table": "表1", "rated_power_kw": 200, "poles": 2, "rated_efficiency": 94},
    },
    "motor_pmsm": {
        "name": "永磁同步电动机", "standard": "GB 30253-2024",
        "fields": [f("model", "型号", required=False), f("category", "设备类别"), f("voltage_group", "电压组", required=False, note="默认≤1140V"), f("cooling_group", "冷却方式组", required=False, note="低压产品默认通用"), f("rated_power_kw", "额定功率", "kW"), f("poles", "极数", "极", required=False, note="异步起动产品必填"), f("rated_speed_rpm", "额定转速", "r/min", required=False, note="变频/电梯产品必填"), f("rated_efficiency", "额定效率", "%", required=False), f("efficiency_at_90pct_speed", "90%额定转速效率", "%", required=False, note="变频产品必填")],
        "example": {"category": "变频调速永磁同步电动机", "rated_power_kw": 5.5, "rated_speed_rpm": 1500, "efficiency_at_90pct_speed": 94},
    },
    "compressor": {
        "name": "空压机", "standard": "GB 19153-2019",
        "fields": [f("model", "型号", required=False), f("category", "设备类别"), f("input_power_kw", "额定输入功率", "kW"), f("volume_flow_m3min", "容积流量", "m³/min", required=False), f("discharge_pressure_mpa", "额定排气压力", "MPa"), f("cooling_method", "冷却方式"), f("specific_power", "机组比功率", "kW/(m³/min)")],
        "example": {"category": "一般用喷油回转（工频）", "input_power_kw": 1.5, "discharge_pressure_mpa": 0.3, "cooling_method": "风冷", "specific_power": 5.8},
    },
    "pump_water": {
        "name": "清水离心泵", "standard": "GB 19762-2025",
        "fields": [f("model", "型号", required=False), f("category", "设备类别"), f("suction", "单双吸", enum_name="EV_SUCTION"), f("flow_m3h", "最高效率点总流量 QBEP", "m³/h"), f("head_m", "最高效率点总扬程 HBEP", "m"), f("rated_speed_rpm", "转速 n", "r/min"), f("rated_power_kw", "额定功率", "kW", required=False), f("stages", "实际级数", "级"), f("pump_efficiency", "最高效率点效率", "%")],
        "example": {"category": "单级单吸", "suction": "单吸", "flow_m3h": "100", "head_m": "50", "rated_speed_rpm": "2900", "stages": "1", "pump_efficiency": "80"},
    },
    "pump_chemical": {
        "name": "石油化工离心泵", "standard": "GB 19762-2025",
        "fields": [f("model", "型号", required=False), f("category", "设备类别"), f("suction", "单双吸", enum_name="EV_SUCTION"), f("flow_m3h", "最高效率点总流量 QBEP", "m³/h"), f("head_m", "最高效率点总扬程 HBEP", "m"), f("rated_speed_rpm", "转速 n", "r/min"), f("rated_power_kw", "额定功率", "kW", required=False), f("stages", "实际级数", "级"), f("pump_efficiency", "最高效率点效率", "%")],
        "example": {"category": "单级石油化工离心泵", "suction": "单吸", "flow_m3h": "100", "head_m": "50", "rated_speed_rpm": "2900", "stages": "1", "pump_efficiency": "80"},
    },
    "fan": {
        "name": "通风机", "standard": "GB 19761-2020",
        # 通风机的评价器既支持直接填报标准指标，也支持用V4出厂设计
        # 参数计算指标。桌面手工窗口必须把这些参数暴露出来，否则用户
        # 只能填写最小示例字段，无法走完整的压缩性修正/结构修正路径。
        "fields": [
            f("model", "型号", required=False),
            f("category", "设备类别"),
            f("transmission", "传动方式", required=False, note="外转子前向多翼及普通电动机直联路径需明确"),
            f("machine_no", "机号", "No."),
            f("flow_m3h", "流量", "m³/h", required=False),
            f("fan_pressure_pa", "风机压力", "Pa", required=False),
            f("inlet_stagnation_pressure_pa", "进口滞止压力", "Pa", required=False),
            f("outlet_stagnation_pressure_pa", "出口滞止压力", "Pa", required=False),
            f("impeller_power_kw", "叶轮功率", "kW", required=False),
            f("rated_power_kw", "额定/电动机输入功率", "kW", required=False),
            f("rated_speed_rpm", "转速", "r/min", required=False),
            f("inlet_stagnation_density", "进口滞止密度", "kg/m³", required=False),
            f("isentropic_k", "等熵指数k", required=False, note="按标准设计工况填写"),
            f("compression_correction", "压缩性修正系数", required=False, note="缺失时可由GB/T 1236物理量计算"),
            f("pressure_coefficient", "压力系数", required=False, note="缺失时可由GB 19761-2020设计物理量计算"),
            f("specific_speed", "比转速", required=False, note="离心通风机条件必填；缺失时可计算"),
            f("hub_ratio", "轮毂比", required=False, note="轴流通风机条件必填"),
            f("fan_efficiency", "设计风机效率", "%", required=False, note="普通通风机效率ηr；可按GB 19761-2020式(1)计算"),
            f("unit_efficiency", "机组效率ηe", "%", required=False, note="外转子前向多翼或普通电动机直联换算路径"),
            f("motor_efficiency", "电动机效率ηm", "%", required=False, note="普通电动机直联换算路径"),
            f("suction", "单双吸", required=False),
            f("hvac_use", "是否暖通空调用", required=False),
            f("inlet_box", "是否带进气箱", required=False),
            f("diffuser", "是否带扩散筒", required=False),
            f("variable_blade", "是否动叶可调", required=False),
            f("reversible", "是否可逆转", required=False),
        ],
        "example": {"category": "离心通风机", "machine_no": 10, "fan_efficiency": 80, "pressure_coefficient": 0.5, "specific_speed": 40},
        "status_note": "压力系数、压缩性修正和离心比转速可按GB/T 1236及GB 19761-2020由设计参数计算；已填标准指标优先采用，缺少可靠原始参数时不使用经验近似。",
    },
    "blower": {
        "name": "鼓风机", "standard": "GB 28381-2012",
        "fields": [
            f("model", "型号", required=False),
            f("category", "设备类别"),
            f("stages", "级数", "级", required=False, note="多级鼓风机及各级效率列表必须填写"),
            f("multi_impeller", "是否多级叶轮", required=False),
            f("polytropic_efficiency", "多变效率", "%", required=False, note="单级或已有平均值时填写"),
            f("stage_efficiencies", "各级多变效率", "%", required=False, note="多级设备可填列表；数量必须等于级数"),
            f("inlet_absolute_pressure_kpa", "进口绝对压力", "kPa", required=False, note="缺少多变效率时按标准公式计算"),
            f("outlet_absolute_pressure_kpa", "出口绝对压力", "kPa", required=False, note="缺少多变效率时按标准公式计算"),
            f("inlet_temperature_k", "进口温度", "K", required=False, note="缺少多变效率时按标准公式计算"),
            f("outlet_temperature_k", "出口温度", "K", required=False, note="缺少多变效率时按标准公式计算"),
            f("isentropic_k", "绝热指数k", required=False, note="缺少多变效率时按标准公式计算"),
            f("flow_m3h", "流量", "m³/h", required=False),
            f("rated_power_kw", "额定功率", "kW", required=False),
            f("impeller_width_mm", "叶轮出口宽度b₂", "mm"),
            f("impeller_diameter_mm", "叶轮出口直径D₂", "mm"),
            f("three_dimensional", "是否三元流动叶轮", required=False),
            f("cantilever", "是否悬臂式", required=False),
        ],
        "example": {"category": "单级双支撑低速离心鼓风机", "polytropic_efficiency": 80, "impeller_width_mm": 100, "impeller_diameter_mm": 1000},
        "status_note": "多变效率优先采用设计/铭牌值；缺少该值时按GB 28381-2012第5.2条由进出口绝对压力、温度和绝热指数计算。",
    },
    "submersible": {
        "name": "潜水电泵", "standard": "GB 32030-2022",
        "fields": [f("model", "型号", required=False), f("category", "设备类别"), f("subtype", "标准型式"), f("flow_m3h", "流量", "m³/h", required=False, note="小型潜水电泵按附录A自动计算ηDB时必填"), f("head_m", "扬程", "m", required=False), f("rated_speed_rpm", "额定转速", "r/min", required=False), f("rated_power_kw", "额定功率", "kW"), f("pump_efficiency", "电泵效率", "%"), f("specified_efficiency", "规定效率ηDB", "%", required=False, note="可由GB/T25409附录A在条件完整时计算"), f("efficiency_tolerance", "效率容差Δη", "%"), f("working_temperature_c", "工作温度", "℃", required=False), f("stages", "级数", "级", required=False), f("pump_form", "泵型", required=False, note="自动计算ηDB时必填：下泵式/上泵式/QXL/QXR"), f("specific_speed", "比转速", required=False, note="自动计算ηDB时必填，标准未授权时不自动推导"), f("motor_efficiency", "电动机效率", "%", required=False, note="自动计算ηDB时可直接填写，按GB/T25409表4或产品资料填写"), f("motor_phase", "电动机相数", required=False, note="缺少电动机效率时与结构、同步转速共同用于查表4"), f("motor_structure", "电动机结构", required=False, note="充油式/充水式/干式"), f("sync_speed_rpm", "同步转速", "r/min", required=False, note="缺少电动机效率时用于查表4")],
        "example": {"category": "小型潜水电泵", "subtype": "QDX", "rated_power_kw": 1.5, "pump_efficiency": 60, "specified_efficiency": 55, "efficiency_tolerance": 2},
        "status_note": "ηDB和Δη可由引用产品标准或设计资料提供；小型潜水电泵在条件完整时按GB/T25409附录A计算ηDB，不插值或外推。",
    },
    "boiler": {
        "name": "工业锅炉", "standard": "GB 24500-2020", "status_note": "燃料锅炉按表1～表4分级；电锅炉按第5.2条能效限定值≥97%判定，达到限定值映射为3级。",
        "fields": [f("model", "型号", required=False), f("combustion_method", "燃烧方式"), f("fuel", "燃料品种"), f("fuel_class", "燃料类别", required=False), f("condensing", "是否冷凝", required=False), f("evaporation_tph", "蒸发量", "t/h", required=False, note="与热功率至少填一项"), f("thermal_power_mw", "热功率", "MW", required=False), f("lower_heating_value_kjkg", "收到基低位发热量", "kJ/kg", required=False), f("volatile_matter_percent", "干燥无灰基挥发分", "%", required=False), f("design_efficiency", "设计热效率", "%")],
        "example": {"combustion_method": "层状燃烧燃煤", "fuel": "烟煤", "fuel_class": "Ⅱ类", "evaporation_tph": 10, "lower_heating_value_kjkg": 19000, "volatile_matter_percent": 25, "design_efficiency": 90},
    },
    "heat_treatment": {
        "name": "热处理设备", "standard": "GB/T 36561-2018",
        "fields": [f("model", "型号", required=False), f("category", "标准炉型"), f("specification", "规格", required=False, note="同炉型存在多档时必填"), f("rated_power_kw", "额定功率", "kW", required=False, note="炉型按功率分档时填写"), f("rated_temperature_c", "额定温度", "℃", required=False, note="炉型按温度分档时填写"), f("energy_type", "能源类型"), f("equivalent_weight_t", "总折合重量", "t"), f("total_electricity_kwh", "总耗电量", "kW·h", required=False, note="电炉必填"), f("fuel_consumption", "燃料总耗量", required=False, note="燃料炉必填"), f("fuel_calorific_value_kjkg", "燃料热值", "kJ/m³（表9）", required=False, note="按能源类型使用标准表9对应单位；燃料炉必填")],
        "example": {"category": "传送式连续炉", "energy_type": "电力", "equivalent_weight_t": 1, "total_electricity_kwh": 300},
    },
    "heat_pump_chiller": {
        "name": "热泵和冷水机组", "standard": "GB 19577-2024", "status_note": "表1～表8已完成PDF逐表复核并启用；按产品类别选择对应指标体系。",
        "fields": [f("category", "设备类别"), f("product_standard", "产品标准"), f("unit_type", "机组型式"), f("source", "冷却/热源方式"), f("evaluation_system", "能效评价指标体系"), f("heating_capacity_kw", "名义制热量", "kW", required=False), f("cooling_capacity_kw", "名义制冷量", "kW", required=False), f("rated_power_kw", "额定功率", "kW", required=False), f("primary_metric_value", "分级指标设计值"), f("aux_metric1_value", "辅助约束指标1", required=False), f("aux_metric2_value", "辅助约束指标2", required=False)],
        "example": {"category": "低环境温度空气源热泵（冷水）机组", "product_standard": "GB/T 25127.2", "unit_type": "地板采暖型", "source": "空气源", "evaluation_system": "对应产品类别指标体系（表3～表8）", "heating_capacity_kw": 20, "primary_metric_value": 3.6, "aux_metric1_value": 2.0, "aux_metric2_value": 2.3},
    },
    "heat_pump_water_heater": {
        "name": "热泵热水机", "standard": "GB 29541-2013",
        "fields": [f("unit_type", "普通型/低温型"), f("heating_method", "加热方式"), f("heating_capacity_kw", "制热量", "kW"), f("rated_power_kw", "额定功率", "kW", required=False), f("with_pump", "是否提供水泵", required=False), f("cop", "性能系数COP", "W/W")],
        "example": {"unit_type": "普通型", "heating_method": "一次加热、循环加热式", "heating_capacity_kw": 5, "cop": 4.6},
    },
    "duct_ac": {
        "name": "风管送风式空调", "standard": "GB 37479-2019",
        "fields": [f("product_type", "产品类型"), f("cooling_source", "冷却方式"), f("mode", "单冷/热泵"), f("cooling_capacity_w", "名义制冷量", "W"), f("seer", "SEER", required=False), f("apf", "APF", required=False), f("iplv", "IPLV", required=False), f("eer", "EER", required=False)],
        "example": {"product_type": "风管送风式机组", "cooling_source": "风冷式", "mode": "单冷型", "cooling_capacity_w": 5000, "seer": 4.2},
    },
    "unitary_ac": {
        "name": "单元式空调", "standard": "GB 19576-2019",
        "fields": [f("category", "机组类别"), f("mode", "单冷/热泵"), f("cooling_capacity_w", "名义制冷量", "W"), f("seer", "SEER", required=False), f("apf", "APF", required=False), f("iplv", "IPLV", required=False), f("aeer", "AEER", required=False), f("cop", "COP", required=False)],
        "example": {"category": "风冷式单元式空调机", "mode": "单冷型", "cooling_capacity_w": 10000, "seer": 4.5},
    },
    "multi_split_ac": {
        "name": "多联式空调", "standard": "GB 21454-2021",
        "fields": [f("category", "机组类别"), f("cooling_capacity_w", "名义制冷量", "W", required=False), f("heating_capacity_w", "名义制热量", "W", required=False, note="低温类别条件必填"), f("seer", "SEER", required=False), f("apf", "APF", required=False), f("iplv_c", "IPLV(C)", required=False), f("hspf", "HSPF", required=False), f("eer", "EER", required=False), f("cop_minus12", "-12℃COP", required=False), f("cop_minus20", "-20℃COP", required=False), f("external_static_pressure_pa", "机外静压", "Pa", required=False, note="大于0时必须同时提供按GB/T 18837/18836取得的静压修正后指标或修正系数"), f("static_pressure_correction_factor", "静压修正系数", required=False, note="由引用标准内部阻力试验/修正参数得到，不使用经验常数"), f("static_pressure_corrected_metric", "静压修正后指标", required=False)],
        "example": {"category": "风冷单冷", "cooling_capacity_w": 10000, "seer": 5.5, "eer": 2.1},
    },
}


# 淘汰目录匹配使用的工作簿外公共输入。生产年份仅在目录条目带年代
# 附加条件时必需；缺少时返回“疑似命中、无法判定”，不会猜测。
for _spec in DEVICE_SPECS.values():
    _fields = _spec["fields"]
    if not any(item["name"] == "model" for item in _fields):
        _fields.insert(0, f("model", "型号", required=False, note="用于淘汰目录精确匹配"))
    _model_index = next(i for i, item in enumerate(_fields) if item["name"] == "model")
    if not any(item["name"] == "production_year" for item in _fields):
        _fields.insert(
            _model_index + 1,
            f("production_year", "生产年份", "年", required=False, note="淘汰目录含年代条件时必填"),
        )


def list_device_specs() -> dict[str, dict[str, Any]]:
    return deepcopy(DEVICE_SPECS)


def get_device_spec(device_type: str) -> dict[str, Any]:
    if device_type not in DEVICE_SPECS:
        raise KeyError(f"未知设备类型: {device_type}")
    return deepcopy(DEVICE_SPECS[device_type])
