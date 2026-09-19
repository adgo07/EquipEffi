from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from ...domain.common.models import DeviceDraft
from ...domain.evaluation.device_types import PUBLIC_TYPE_BY_SHEET
from .v4_template_contract import V4_DEVICE_SHEETS


class V4AdaptationError(ValueError):
    """V4工作表或设备类别无法安全映射到唯一内部评价器。"""


@dataclass(frozen=True)
class V4AdaptedRecord:
    """V4输入的内部化结果；保留原sheet和路由说明供轨迹/回写接口使用。"""

    draft: DeviceDraft
    sheet_name: str
    internal_device_type: str
    route_changes: tuple[dict[str, Any], ...] = field(default_factory=tuple)


def _present(value: Any) -> bool:
    return value not in (None, "")


def _number(value: Any) -> Decimal | None:
    if not _present(value):
        return None
    try:
        text = str(value).strip().replace("，", ",")
        match = re.search(r"[-+]?\d+(?:\.\d+)?", text.replace(",", ""))
        return Decimal(match.group(0)) if match else None
    except (InvalidOperation, ValueError):
        return None


def _voltage_kv(value: Any) -> Decimal | None:
    number = _number(value)
    if number is None:
        return None
    text = str(value).lower().replace(" ", "")
    if "kv" in text:
        return number
    if "v" in text:
        return number / Decimal(1000)
    # V4额定电压字段的单位是kV；没有单位时按V4约定解释为kV。
    return number


def _route_motor(values: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    category = str(values.get("category", ""))
    # GB 30253-2024仅覆盖永磁同步电动机。不能因为类别含有泛化的
    # “同步”二字就把普通同步电机送入永磁标准；没有“永磁”证据时，
    # 继续按电压路由到低压/高压profile，或在缺少电压时明确要求补充。
    if "永磁" in category:
        return "motor_pmsm", [{"rule": "V4电动机类别路由", "sheet": "电动机", "category": category, "device_type": "motor_pmsm"}]

    voltage = _voltage_kv(values.get("rated_voltage"))
    if any(token in category for token in ("低压", "低电压")) or (voltage is not None and voltage <= Decimal("1.14")):
        return "motor_lv", [{"rule": "V4电动机电压路由", "sheet": "电动机", "rated_voltage": values.get("rated_voltage"), "device_type": "motor_lv"}]
    if any(token in category for token in ("高压", "高电压")) or voltage is not None:
        return "motor_hv", [{"rule": "V4电动机电压路由", "sheet": "电动机", "rated_voltage": values.get("rated_voltage"), "device_type": "motor_hv"}]
    raise V4AdaptationError("V4电动机缺少可用于区分低压、高压或永磁产品的类别/额定电压")


def _route_pump(values: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    category = str(values.get("category", ""))
    if "石油化工" in category or "化工" in category:
        device_type = "pump_chemical"
    elif any(token in category for token in ("清水", "管道", "轻型多级")):
        device_type = "pump_water"
    else:
        raise V4AdaptationError("V4离心泵设备类别无法区分清水离心泵和石油化工离心泵")
    return device_type, [{"rule": "V4离心泵类别路由", "sheet": "离心泵", "category": category, "device_type": device_type}]


def _route_fan(sheet_name: str, values: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    category = str(values.get("category", ""))
    if sheet_name == "离心通风机" and "轴流" in category:
        raise V4AdaptationError("V4离心通风机sheet的设备类别与轴流通风机冲突")
    if sheet_name == "轴流通风机" and "离心" in category:
        raise V4AdaptationError("V4轴流通风机sheet的设备类别与离心通风机冲突")
    return "fan", [{"rule": "V4通风机sheet路由", "sheet": sheet_name, "category": category, "device_type": "fan"}]


def _route_sheet(sheet_name: str, values: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    if sheet_name not in V4_DEVICE_SHEETS:
        raise V4AdaptationError(f"不是V4设备sheet: {sheet_name}")
    if sheet_name == "电动机":
        return _route_motor(values)
    if sheet_name == "离心泵":
        return _route_pump(values)
    if sheet_name in {"离心通风机", "轴流通风机"}:
        return _route_fan(sheet_name, values)
    return {
        "变压器": "transformer",
        "空压机": "compressor",
        "鼓风机": "blower",
        "潜水电泵": "submersible",
        "工业锅炉": "boiler",
        "热处理设备": "heat_treatment",
        "热泵和冷水机组": "heat_pump_chiller",
        "热泵热水机": "heat_pump_water_heater",
        "风管送风式空调": "duct_ac",
        "单元式空调": "unitary_ac",
        "多联式空调": "multi_split_ac",
    }[sheet_name], [{"rule": "V4设备sheet路由", "sheet": sheet_name, "device_type": sheet_name}]


class V4InputAdapter:
    """V4工作表字典→内部17类DeviceDraft的适配器。

    适配器不读取Excel、不修改原始字典；Excel导入器以后只需先提取sheet名和字段ID，
    再调用本类即可复用同一套判定服务。
    """

    @staticmethod
    def adapt(record_id: str, sheet_name: str, values: dict[str, Any]) -> V4AdaptedRecord:
        if not isinstance(values, dict):
            raise V4AdaptationError("V4设备行必须是字段字典")
        internal_type, route_changes = _route_sheet(sheet_name, values)
        public_type = PUBLIC_TYPE_BY_SHEET[sheet_name]
        draft = DeviceDraft(
            record_id=str(record_id),
            device_type=internal_type,
            raw_values=dict(values),
            metadata={
                "input_source": "V4",
                "v4_sheet": sheet_name,
                "public_device_type": public_type,
                "v4_route_changes": route_changes,
            },
        )
        return V4AdaptedRecord(draft, sheet_name, internal_type, tuple(route_changes))

    @staticmethod
    def adapt_many(records: Iterable[dict[str, Any]]) -> list[V4AdaptedRecord]:
        adapted: list[V4AdaptedRecord] = []
        for record in records:
            adapted.append(V4InputAdapter.adapt(str(record["record_id"]), str(record["sheet"]), dict(record.get("values", {}))))
        return adapted
