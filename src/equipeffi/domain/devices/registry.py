from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DeviceDefinition:
    code: str
    display_name: str
    field_schema: Any = None
    normalizer: Any = None
    validator: Any = None
    indicator_calculator: Any = None
    evaluator: Any = None
    aggregation: Any = None
    knowledge_topic: str | None = None


class DeviceRegistry:
    def __init__(self, definitions: list[DeviceDefinition] | None = None):
        self._definitions = {d.code: d for d in definitions or []}

    def register(self, definition: DeviceDefinition) -> None:
        self._definitions[definition.code] = definition

    def get(self, code: str) -> DeviceDefinition:
        return self._definitions[code]

    def all(self) -> tuple[DeviceDefinition, ...]:
        return tuple(self._definitions.values())


DEVICE_NAMES = {
    "transformer": "变压器",
    "motor_lv": "低压电动机",
    "motor_hv": "高压电动机",
    "motor_pmsm": "永磁同步电动机",
    "compressor": "空压机",
    "pump_water": "清水离心泵",
    "pump_chemical": "石油化工离心泵",
    "fan": "通风机",
    "blower": "鼓风机",
    "submersible": "潜水电泵",
    "boiler": "工业锅炉",
    "heat_treatment": "热处理设备",
    "heat_pump_chiller": "热泵和冷水机组",
    "heat_pump_water_heater": "热泵热水机",
    "duct_ac": "风管送风式空调",
    "unitary_ac": "单元式空调",
    "multi_split_ac": "多联式空调",
}


def default_registry() -> DeviceRegistry:
    return DeviceRegistry(
        [DeviceDefinition(code=code, display_name=name) for code, name in DEVICE_NAMES.items()]
    )
