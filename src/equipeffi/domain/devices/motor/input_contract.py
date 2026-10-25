"""GB 18613—2020 motor category and field contract.

Equipment type is always selected explicitly. This module never infers it from
model names, free text, voltage, or other numeric values.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True)
class MotorCategoryOption:
    category_id: str
    label: str
    table_no: int | None
    route_facts: Mapping[str, Any]


@dataclass(frozen=True)
class MotorInputField:
    field_id: str
    label: str
    unit: str | None = None
    required: bool = False
    required_when: str | None = None


class MotorInputError(ValueError):
    """An unknown or contradictory value in the GB 18613 input contract."""

    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field
        self.message = message


MOTOR_CATEGORIES: tuple[MotorCategoryOption, ...] = (
    MotorCategoryOption("three_phase_induction", "三相异步电动机（一般用途或一般用途防爆）", 1,
        MappingProxyType({"power_min_kw": "0.12", "power_max_kw": "1000", "rated_voltage_max_kv": "1", "rated_voltage_max_inclusive": False, "rated_frequency_hz": "50", "poles": (2, 4, 6, 8)})),
    MotorCategoryOption("capacitor_start", "电容起动异步电动机（一般用途）", 2,
        MappingProxyType({"power_min_kw": "0.12", "power_max_kw": "3.7", "rated_voltage_max_kv": "0.69", "rated_voltage_max_inclusive": True, "rated_frequency_hz": "50", "poles": (2, 4, 6)})),
    MotorCategoryOption("capacitor_run", "电容运转异步电动机（一般用途）", 3,
        MappingProxyType({"power_min_kw": "0.12", "power_max_kw": "2.2", "rated_voltage_max_kv": "0.69", "rated_voltage_max_inclusive": True, "rated_frequency_hz": "50", "poles": (2, 4, 6)})),
    MotorCategoryOption("two_value_capacitor", "双值电容异步电动机（一般用途）", 4,
        MappingProxyType({"power_min_kw": "0.25", "power_max_kw": "3.7", "rated_voltage_max_kv": "0.69", "rated_voltage_max_inclusive": True, "rated_frequency_hz": "50", "poles": (2, 4)})),
    MotorCategoryOption("ac_fan_capacitor_run", "空调器风扇用电容运转电动机", 5,
        MappingProxyType({"power_min_kw": "0.01", "power_max_kw": "1.1", "poles": (4, 6, 8)})),
    MotorCategoryOption("ac_fan_brushless_dc", "空调器风扇用无刷直流电动机", 6,
        MappingProxyType({"power_min_kw": "0.01", "power_max_kw": "1.1"})),
    MotorCategoryOption("OTHER_CATEGORY", "其他类别", None, MappingProxyType({})),
    MotorCategoryOption("UNCERTAIN_CATEGORY", "不确定类别", None, MappingProxyType({})),
)
_CATEGORY_BY_ID = {x.category_id: x for x in MOTOR_CATEGORIES}
_CATEGORY_BY_LABEL = {x.label: x for x in MOTOR_CATEGORIES}

# A blank I cell is AS_DECLARED_BY_FIELD; selecting USER_DECLARED records an
# explicit user statement. Neither represents review of a test report.
BASIS_OPTIONS: tuple[tuple[str, str], ...] = (
    ("USER_DECLARED", "按上述口径填报"),
    ("NAMEPLATE_ONLY", "仅有铭牌效率"),
    ("KNOWN_NONCONFORMING", "已知试验工况不符合"),
    ("INSEPARABLE_MOTOR_ONLY", "驱动不可分离但仅有电机本体效率（仅表6）"),
    ("UNKNOWN", "效率口径不确定"),
)
_BASIS_BY_LABEL = {label: code for code, label in BASIS_OPTIONS}
_BASIS_CODES = {code for code, _ in BASIS_OPTIONS} | {"AS_DECLARED_BY_FIELD"}

_SCOPE_HINTS = {
    1: "仅适用于单速、封闭自扇冷式、N设计、连续工作制的一般用途三相异步电动机（含一般用途防爆）；其它型式请选择“其他类别”。",
    2: "仅适用于一般用途电容起动异步电动机。",
    3: "仅适用于一般用途电容运转异步电动机。",
    4: "仅适用于一般用途双值电容异步电动机。",
    5: "仅适用于空调器风扇用电容运转电动机。",
    6: "仅适用于空调器风扇用无刷直流电动机。",
}
_TEST_BASIS_HINTS = {
    1: "三相异步电动机按GB/T 1032 B法试验；不得以普通输入/输出功率比替代。",
    2: "单相异步电动机按GB/T 5171.21直接法试验。",
    3: "单相异步电动机按GB/T 5171.21直接法试验。",
    4: "单相异步电动机按GB/T 5171.21直接法试验。",
    5: "风扇电机按GB/T 5171.21直接法试验，试验转速取铭牌标称最高转速。",
    6: "风扇电机按GB/T 5171.21直接法试验，试验转速取铭牌标称最高转速；驱动不可分离时按电机与驱动整体效率考核。",
}
SPEED_BAND_LABELS = {
    "rpm_band_1": "0<r≤500 r/min",
    "rpm_band_2": "500<r≤700 r/min",
    "rpm_band_3": "700<r≤1000 r/min",
    "rpm_band_4": "1000<r≤1300 r/min",
    "rpm_band_5": "r>1300 r/min",
}

_COMMON_FIELDS = (
    MotorInputField("rated_output_power_kw", "额定输出功率", "kW", True),
    MotorInputField("measured_efficiency_pct", "额定输出功率下实测效率", "%", True),
)
_VOLTAGE = MotorInputField("rated_voltage_kv", "额定电压", "kV", True)
_FREQUENCY = MotorInputField("rated_frequency_hz", "额定频率", "Hz", True)
_POLES = MotorInputField("poles", "极数", "极", True)
_SPEED = MotorInputField("max_nameplate_speed_rpm", "铭牌标称最高转速", "r/min", True)
_BASIS = MotorInputField("efficiency_basis_status", "实测效率口径说明")
_NOTE = MotorInputField("user_note", "备注")


def _resolve_category(value: str | None) -> MotorCategoryOption | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise MotorInputError("category_id", "设备类别必须使用已登记的类别选项。")
    option = _CATEGORY_BY_ID.get(value) or _CATEGORY_BY_LABEL.get(value)
    if option is None:
        raise MotorInputError("category_id", "设备类别不属于已登记的六类或其他/不确定类别。")
    return option


def category_fields(category_id: str | None) -> tuple[MotorInputField, ...]:
    """Return conditional fields for one category, excluding common fields."""
    category = _resolve_category(category_id)
    if category is None or category.table_no is None:
        return ()
    fields: list[MotorInputField] = []
    if category.table_no <= 4:
        fields.extend((_VOLTAGE, _FREQUENCY))
    if category.table_no <= 5:
        fields.append(_POLES)
    if category.table_no == 6:
        fields.append(_SPEED)
    fields.extend((_BASIS, _NOTE))
    return tuple(fields)


def visible_fields(category_id: str | None) -> tuple[MotorInputField, ...]:
    """Return fields needed to enter one explicitly selected standard type."""
    category = _resolve_category(category_id)
    if category is None or category.table_no is None:
        return ()
    return _COMMON_FIELDS + category_fields(category.category_id)


def options(category_id: str | None, field_id: str) -> tuple[tuple[str, str], ...]:
    """Return controlled choices as stable value/label pairs."""
    if field_id == "efficiency_basis_status":
        return BASIS_OPTIONS
    if field_id == "poles":
        category = _resolve_category(category_id)
        if category is None:
            return ()
        return tuple((str(n), f"{n}极") for n in category.route_facts.get("poles", ()))
    return ()


def scope_hint(category_id: str | None) -> str:
    """Return the fixed physical-scope reminder for a selected category."""
    category = _resolve_category(category_id)
    return _SCOPE_HINTS.get(category.table_no, "") if category is not None else ""


def efficiency_basis_hint(category_id: str | None) -> str:
    """Return the field's required efficiency-test-basis reminder."""
    category = _resolve_category(category_id)
    return _TEST_BASIS_HINTS.get(category.table_no, "") if category is not None else ""


def speed_band_label(branch_id: str) -> str:
    """Return a user-readable label for one stable table-6 branch ID."""
    return SPEED_BAND_LABELS.get(branch_id, "")


def normalize_motor_input(values: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve category/basis labels without coercing numeric values."""
    if not isinstance(values, Mapping):
        raise MotorInputError("input", "电动机输入必须是字段映射。")
    normalized = dict(values)
    raw_id, raw_label = values.get("category_id"), values.get("category")
    by_id = _resolve_category(raw_id) if raw_id not in (None, "") else None
    by_label = _resolve_category(raw_label) if raw_label not in (None, "") else None
    if by_id is not None and by_label is not None and by_id.category_id != by_label.category_id:
        raise MotorInputError("category_id", "设备类别与类别标识不一致。")
    category = by_id or by_label
    normalized["category_id"] = category.category_id if category is not None else None

    raw_basis = values.get("efficiency_basis_status")
    basis_text = raw_basis.strip() if isinstance(raw_basis, str) else raw_basis
    if basis_text in (None, ""):
        basis_status = "AS_DECLARED_BY_FIELD"
    elif basis_text in _BASIS_CODES:
        basis_status = basis_text
    elif isinstance(basis_text, str) and basis_text in _BASIS_BY_LABEL:
        basis_status = _BASIS_BY_LABEL[basis_text]
    else:
        raise MotorInputError("efficiency_basis_status", "实测效率口径请选择已登记选项。")
    if basis_status == "INSEPARABLE_MOTOR_ONLY" and (category is None or category.table_no != 6):
        raise MotorInputError("efficiency_basis_status", "该口径仅适用于空调器风扇用无刷直流电动机（表6）。")
    normalized["efficiency_basis_status"] = basis_status
    if "efficiency_basis_raw" not in normalized:
        normalized["efficiency_basis_raw"] = raw_basis if raw_basis not in (None, "") else ""
    return normalized


class MotorInputContract:
    """Read-only facade for Application and Presentation consumers."""

    categories = MOTOR_CATEGORIES
    basis_options = BASIS_OPTIONS
    category_fields = staticmethod(category_fields)
    visible_fields = staticmethod(visible_fields)
    options = staticmethod(options)
    normalize = staticmethod(normalize_motor_input)
    scope_hint = staticmethod(scope_hint)
    efficiency_basis_hint = staticmethod(efficiency_basis_hint)
    speed_band_label = staticmethod(speed_band_label)


MOTOR_INPUT_CONTRACT = MotorInputContract()
