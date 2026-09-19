from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
from typing import Any


"""公共设备类型与内部规则profile。

V4的15个设备sheet是对外契约；标准评价器仍可按标准差异保留内部profile。
本模块只负责类型解析，不执行任何能效计算。
"""


PUBLIC_DEVICE_TYPES: tuple[str, ...] = (
    "transformer",
    "motor",
    "compressor",
    "centrifugal_pump",
    "centrifugal_fan",
    "axial_fan",
    "blower",
    "submersible_pump",
    "industrial_boiler",
    "heat_treatment",
    "heat_pump_chiller",
    "heat_pump_water_heater",
    "duct_ac",
    "unitary_ac",
    "multi_split_ac",
)


PUBLIC_DEVICE_NAMES: dict[str, str] = {
    "transformer": "变压器",
    "motor": "电动机",
    "compressor": "空压机",
    "centrifugal_pump": "离心泵",
    "centrifugal_fan": "离心通风机",
    "axial_fan": "轴流通风机",
    "blower": "鼓风机",
    "submersible_pump": "潜水电泵",
    "industrial_boiler": "工业锅炉",
    "heat_treatment": "热处理设备",
    "heat_pump_chiller": "热泵和冷水机组",
    "heat_pump_water_heater": "热泵热水机",
    "duct_ac": "风管送风式空调",
    "unitary_ac": "单元式空调",
    "multi_split_ac": "多联式空调",
}


PUBLIC_SHEET_NAMES: dict[str, str] = dict(PUBLIC_DEVICE_NAMES)
PUBLIC_TYPE_BY_SHEET: dict[str, str] = {name: code for code, name in PUBLIC_DEVICE_NAMES.items()}


# 17类内部评价器代码。它们不是新的公共设备sheet。
INTERNAL_DEVICE_TYPES: tuple[str, ...] = (
    "transformer",
    "motor_lv",
    "motor_hv",
    "motor_pmsm",
    "compressor",
    "pump_water",
    "pump_chemical",
    "fan",
    "blower",
    "submersible",
    "boiler",
    "heat_treatment",
    "heat_pump_chiller",
    "heat_pump_water_heater",
    "duct_ac",
    "unitary_ac",
    "multi_split_ac",
)


INTERNAL_TO_PUBLIC: dict[str, str] = {
    "transformer": "transformer",
    "motor_lv": "motor",
    "motor_hv": "motor",
    "motor_pmsm": "motor",
    "compressor": "compressor",
    "pump_water": "centrifugal_pump",
    "pump_chemical": "centrifugal_pump",
    # 兼容旧的通风机入口。V4新入口应使用centrifugal_fan或axial_fan。
    "fan": "centrifugal_fan",
    "blower": "blower",
    "submersible": "submersible_pump",
    "boiler": "industrial_boiler",
    "heat_treatment": "heat_treatment",
    "heat_pump_chiller": "heat_pump_chiller",
    "heat_pump_water_heater": "heat_pump_water_heater",
    "duct_ac": "duct_ac",
    "unitary_ac": "unitary_ac",
    "multi_split_ac": "multi_split_ac",
}


PUBLIC_INTERNAL_PROFILES: dict[str, tuple[str, ...]] = {
    "transformer": ("transformer",),
    "motor": ("motor_lv", "motor_hv", "motor_pmsm"),
    "compressor": ("compressor",),
    "centrifugal_pump": ("pump_water", "pump_chemical"),
    "centrifugal_fan": ("fan",),
    "axial_fan": ("fan",),
    "blower": ("blower",),
    "submersible_pump": ("submersible",),
    "industrial_boiler": ("boiler",),
    "heat_treatment": ("heat_treatment",),
    "heat_pump_chiller": ("heat_pump_chiller",),
    "heat_pump_water_heater": ("heat_pump_water_heater",),
    "duct_ac": ("duct_ac",),
    "unitary_ac": ("unitary_ac",),
    "multi_split_ac": ("multi_split_ac",),
}


def profiles_for_public_type(public_type: str) -> tuple[str, ...]:
    """Return the internal evaluator profiles for one public device type.

    The 15-to-17 mapping is deliberately kept inside this routing module.
    Application and presentation layers should use this read-only query rather
    than importing ``PUBLIC_INTERNAL_PROFILES`` and duplicating knowledge of
    the internal profile split.
    """

    normalized = PUBLIC_TYPE_BY_SHEET.get(str(public_type), str(public_type))
    return tuple(PUBLIC_INTERNAL_PROFILES.get(normalized, ()))


class DeviceTypeResolutionError(ValueError):
    """公共设备类型无法安全路由到唯一内部规则profile。"""


@dataclass(frozen=True)
class DeviceTypeResolution:
    requested_type: str
    public_device_type: str
    internal_device_type: str
    changes: tuple[dict[str, Any], ...] = ()


def _number(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        text = str(value).strip().replace("，", ",")
        match = re.search(r"[-+]?\d+(?:\.\d+)?", text.replace(",", ""))
        number = Decimal(match.group(0)) if match else None
        return number if number is not None and number.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def _voltage_kv(values: dict[str, Any]) -> Decimal | None:
    """按V4额定电压字段解释kV，同时兼容带V/kV单位的输入。"""

    if values.get("rated_voltage_v") not in (None, ""):
        voltage_v = _number(values["rated_voltage_v"])
        return voltage_v / Decimal(1000) if voltage_v is not None else None
    value = values.get("rated_voltage")
    voltage = _number(value)
    if voltage is None:
        return None
    text = str(value).lower().replace(" ", "")
    if "kv" in text:
        return voltage
    if "v" in text:
        return voltage / Decimal(1000)
    # V4“电动机”sheet额定电压的单位是kV。
    return voltage


def _resolve_motor(values: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    profile = values.get("motor_profile") or values.get("rule_profile")
    if profile in {"lv", "motor_lv"}:
        return "motor_lv", [{"rule": "公共电动机profile", "profile": "lv"}]
    if profile in {"hv", "motor_hv"}:
        return "motor_hv", [{"rule": "公共电动机profile", "profile": "hv"}]
    if profile in {"pmsm", "motor_pmsm"}:
        return "motor_pmsm", [{"rule": "公共电动机profile", "profile": "pmsm"}]

    category = str(values.get("category", ""))
    if any(token in category for token in ("永磁", "永磁同步")):
        return "motor_pmsm", [{"rule": "按设备类别路由电动机", "category": category, "profile": "pmsm"}]
    if any(token in category for token in ("高压", "高电压")):
        return "motor_hv", [{"rule": "按设备类别路由电动机", "category": category, "profile": "hv"}]
    if any(token in category for token in ("低压", "低电压")):
        return "motor_lv", [{"rule": "按设备类别路由电动机", "category": category, "profile": "lv"}]

    voltage = _voltage_kv(values)
    if voltage is not None:
        if voltage <= Decimal("1.14"):
            return "motor_lv", [{"rule": "按额定电压路由电动机", "rated_voltage_kv": str(voltage), "profile": "lv"}]
        return "motor_hv", [{"rule": "按额定电压路由电动机", "rated_voltage_kv": str(voltage), "profile": "hv"}]
    raise DeviceTypeResolutionError("电动机缺少可区分低压、高压或永磁产品的设备类别、profile或额定电压")


def _resolve_pump(values: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    profile = values.get("pump_profile") or values.get("rule_profile")
    if profile in {"water", "pump_water"}:
        return "pump_water", [{"rule": "公共离心泵profile", "profile": "water"}]
    if profile in {"chemical", "pump_chemical", "petrochemical"}:
        return "pump_chemical", [{"rule": "公共离心泵profile", "profile": "chemical"}]

    category = str(values.get("category", ""))
    if any(token in category for token in ("石油化工", "石化", "化工")):
        return "pump_chemical", [{"rule": "按设备类别路由离心泵", "category": category, "profile": "chemical"}]
    if any(token in category for token in ("清水", "单级单吸", "单级双吸", "管道", "多级", "轻型多级")):
        return "pump_water", [{"rule": "按设备类别路由离心泵", "category": category, "profile": "water"}]
    raise DeviceTypeResolutionError("离心泵缺少可区分清水泵或石油化工泵的设备类别或profile")


def resolve_device_type(device_type: str, values: dict[str, Any] | None = None) -> DeviceTypeResolution:
    """将15类公共类型或17类兼容类型解析为唯一内部评价器。"""

    values = values or {}
    requested = str(device_type)
    if requested in INTERNAL_DEVICE_TYPES:
        public = INTERNAL_TO_PUBLIC[requested]
        return DeviceTypeResolution(requested, public, requested, ({"rule": "兼容内部设备类型", "public_device_type": public},))
    if requested not in PUBLIC_DEVICE_TYPES:
        # 同时接受V4中文sheet名称，方便Excel适配器之外的调用方。
        requested = PUBLIC_TYPE_BY_SHEET.get(requested, requested)
    if requested not in PUBLIC_DEVICE_TYPES:
        raise DeviceTypeResolutionError(f"未知公共设备类型: {device_type}")

    if requested == "motor":
        internal, changes = _resolve_motor(values)
    elif requested == "centrifugal_pump":
        internal, changes = _resolve_pump(values)
    elif requested in {"centrifugal_fan", "axial_fan"}:
        category = str(values.get("category", ""))
        if requested == "centrifugal_fan" and "轴流" in category:
            raise DeviceTypeResolutionError("离心通风机公共类型与设备类别中的轴流属性冲突")
        if requested == "axial_fan" and "离心" in category:
            raise DeviceTypeResolutionError("轴流通风机公共类型与设备类别中的离心属性冲突")
        internal = "fan"
        changes = [{"rule": "按V4通风机sheet路由", "public_device_type": requested, "profile": requested.replace("_fan", "")}]
    else:
        internal = {
            "transformer": "transformer",
            "compressor": "compressor",
            "blower": "blower",
            "submersible_pump": "submersible",
            "industrial_boiler": "boiler",
            "heat_treatment": "heat_treatment",
            "heat_pump_chiller": "heat_pump_chiller",
            "heat_pump_water_heater": "heat_pump_water_heater",
            "duct_ac": "duct_ac",
            "unitary_ac": "unitary_ac",
            "multi_split_ac": "multi_split_ac",
        }[requested]
        changes = [{"rule": "公共设备类型映射", "public_device_type": requested, "internal_device_type": internal}]
    return DeviceTypeResolution(str(device_type), requested, internal, tuple(changes))


def public_device_types() -> tuple[dict[str, str], ...]:
    return tuple({"code": code, "name": PUBLIC_DEVICE_NAMES[code], "sheet": PUBLIC_SHEET_NAMES[code]} for code in PUBLIC_DEVICE_TYPES)
