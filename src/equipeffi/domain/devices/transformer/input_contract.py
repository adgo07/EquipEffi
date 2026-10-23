"""Canonical transformer input categories and category-dependent field rules.

This is the single source for the controlled F category and H standard-condition
options consumed by the desktop and workbook adapters. It contains no threshold
data and never chooses a loss table; the selected category is the user's explicit
type declaration, while the calculator checks the physical inputs required by
that route.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

TRANSFORMER_SCOPE_HINT = (
    "适用类别限额定频率50 Hz；非50 Hz或其他不适用型式请选择“其他类别”，"
    "型式不明确请选择“不确定类别”。"
)


class TransformerInputError(ValueError):
    """The transformer input uses an unknown or contradictory contract value."""


@dataclass(frozen=True)
class TransformerCategoryOption:
    category_id: str
    label: str
    table_no: int | None
    route_facts: Mapping[str, Any]


@dataclass(frozen=True)
class TransformerConditionOption:
    condition_id: str
    label: str
    values: Mapping[str, str]


@dataclass(frozen=True)
class TransformerInputField:
    field_id: str
    label: str
    unit: str | None = None
    required: bool = False
    required_when: str | None = None


_LABELS = (
    "10kV油浸式三相双绕组无励磁调压配电变压器",
    "10kV干式三相双绕组无励磁调压配电变压器",
    "35kV油浸式三相双绕组无励磁调压电力变压器",
    "35kV油浸式三相双绕组有载调压电力变压器",
    "66kV油浸式三相双绕组无励磁调压电力变压器",
    "66kV油浸式三相双绕组有载调压电力变压器",
    "110kV油浸式三相双绕组无励磁调压电力变压器（低压非35kV）",
    "110kV油浸式三相双绕组低压为35kV无励磁调压电力变压器",
    "110kV油浸式三相三绕组无励磁调压变压器",
    "110kV油浸式三相双绕组有载调压电力变压器",
    "110kV油浸式三相三绕组有载调压电力变压器",
    "220kV油浸式三相双绕组无励磁调压电力变压器（低压非66kV）",
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
    "500kV油浸式单相三绕组无励磁调压自耦电力变压器（中压线端调压）",
    "500kV油浸式单相三绕组有载调压自耦电力变压器（中压线端调压）",
    "6kV油浸式三相双绕组无励磁调压新能源发电侧变压器（光伏/风电/储能，6kV~7.2kV/0.4kV~1.14kV）",
    "6kV干式三相双绕组无励磁调压新能源发电侧变压器（光伏/风电/储能，6kV~7.2kV/0.4kV~1.14kV）",
    "10kV油浸式三相双绕组无励磁调压新能源发电侧变压器（光伏/风电/储能，10kV~12kV/0.4kV~1.14kV）",
    "10kV干式三相双绕组无励磁调压新能源发电侧变压器（光伏/风电/储能，10kV~12kV/0.4kV~1.14kV）",
    "35kV油浸式三相双绕组无励磁调压新能源发电侧变压器（光伏/风电/储能，35kV~38.5kV/0.4kV~1.14kV）",
    "35kV干式三相双绕组无励磁调压新能源发电侧变压器（光伏/风电/储能，35kV~38.5kV/0.4kV~1.14kV）",
    "66kV油浸式三相双绕组无励磁调压新能源发电侧变压器（光伏/风电/储能，66kV~72.5kV/0.4kV~1.14kV）",
)


def _facts(table_no: int) -> Mapping[str, Any]:
    renewable = table_no >= 29
    voltage = {1: 10, 2: 10, 3: 35, 4: 35, 5: 66, 6: 66,
               7: 110, 8: 110, 9: 110, 10: 110, 11: 110,
               12: 220, 13: 220, 14: 220, 15: 220, 16: 220, 17: 220,
               18: 330, 19: 330, 20: 330, 21: 330, 22: 330, 23: 330,
               24: 330, 25: 500, 26: 500, 27: 500, 28: 500,
               29: 6, 30: 6, 31: 10, 32: 10, 33: 35, 34: 35, 35: 66}[table_no]
    dry = table_no in {2, 30, 32, 34}
    phase_count = 1 if table_no in {25, 27, 28} else 3
    winding_count = 3 if table_no in {9, 11, 13, 16, 17, 19, 20, 21, 22, 23, 24, 27, 28} else 2
    on_load = table_no in {4, 6, 10, 11, 15, 16, 17, 21, 22, 24, 28}
    is_auto = table_no in {17, 20, 21, 22, 23, 24, 27, 28}
    facts: dict[str, Any] = {
        "rated_frequency_hz": "50",
        "application_group": "renewable" if renewable else "ordinary",
        "voltage_class_kv": voltage,
        "medium_type": "dry_type" if dry else "oil_immersed",
        "phase_count": phase_count,
        "winding_count": winding_count,
        "regulation_type": "on_load" if on_load else "de_energized",
        "is_autotransformer": is_auto,
    }
    if table_no == 8:
        facts["special_lv_rated_voltage_kv"] = "35"
    elif table_no == 14:
        facts["special_lv_rated_voltage_kv"] = "66"
    if table_no in {20, 21, 22}:
        facts["mv_rated_voltage_kv"] = "110"
        facts["tap_location"] = "series_winding_end" if table_no in {20, 21} else "line_end"
    elif table_no in {23, 24}:
        facts["mv_rated_voltage_kv"] = "220"
        facts["tap_location"] = "line_end"
    return MappingProxyType(facts)


TRANSFORMER_CATEGORIES: tuple[TransformerCategoryOption, ...] = tuple(
    TransformerCategoryOption(f"GB20052-T{number:02d}", label, number, _facts(number))
    for number, label in enumerate(_LABELS, start=1)
) + (
    TransformerCategoryOption("OTHER_CATEGORY", "其他类别", None, MappingProxyType({})),
    TransformerCategoryOption("UNCERTAIN_CATEGORY", "不确定类别", None, MappingProxyType({})),
)

_CATEGORY_BY_ID = {item.category_id: item for item in TRANSFORMER_CATEGORIES}
_CATEGORY_BY_LABEL = {item.label: item for item in TRANSFORMER_CATEGORIES}
_CORE_LABELS = {"电工钢带": "electrical_steel", "非晶合金": "amorphous_alloy"}
_VECTOR_LABELS = {"Dyn11/Yzn11": "dyn11_yzn11", "Yyn0": "yyn0"}
_RENEWABLE_LABELS = {"光伏": "photovoltaic", "风电": "wind", "储能": "storage"}
_RENEWABLE_DISPLAY = {"photovoltaic": "光伏", "wind": "风电", "storage": "储能"}
_CORE_DISPLAY = {"electrical_steel": "电工钢", "amorphous_alloy": "非晶合金"}
_VECTOR_DISPLAY = {"dyn11_yzn11": "Dyn11/Yzn11", "yyn0": "Yyn0"}
_THERMAL_DISPLAY = {"B": "B级（100℃）", "F": "F级（120℃）", "H": "H级（145℃）"}


def _condition_option(category_id: str, values: Mapping[str, str]) -> TransformerConditionOption:
    tid = _CATEGORY_BY_ID[category_id].table_no
    assert tid is not None
    parts: list[str] = []
    if "core_material" in values:
        parts.append(_CORE_DISPLAY[values["core_material"]])
    if "vector_group" in values:
        parts.append(_VECTOR_DISPLAY[values["vector_group"]])
    if "renewable_type" in values:
        parts.append(_RENEWABLE_DISPLAY[values["renewable_type"]])
    if "thermal_class" in values:
        parts.append(_THERMAL_DISPLAY[values["thermal_class"]])
    frozen_values = MappingProxyType(dict(values))
    condition_id = ";".join(f"{key}={value}" for key, value in values.items())
    return TransformerConditionOption(condition_id, "，".join(parts), frozen_values)


def condition_options(category_id: str) -> tuple[TransformerConditionOption, ...]:
    """Return the only valid H dropdown combinations for a controlled category."""
    category = _resolve_category(category_id)
    table_no = category.table_no
    if table_no == 1:
        return tuple(
            _condition_option(category.category_id, {"core_material": core, "vector_group": vector})
            for core in ("electrical_steel", "amorphous_alloy")
            for vector in ("dyn11_yzn11", "yyn0")
        )
    if table_no == 2:
        return tuple(
            _condition_option(category.category_id, {"core_material": core, "thermal_class": thermal})
            for core in ("electrical_steel", "amorphous_alloy")
            for thermal in ("B", "F", "H")
        )
    if table_no in {29, 31, 33, 35}:
        return tuple(
            _condition_option(category.category_id, {"renewable_type": renewable})
            for renewable in ("photovoltaic", "wind", "storage")
        )
    if table_no in {30, 32, 34}:
        return tuple(
            _condition_option(category.category_id, {"renewable_type": renewable, "thermal_class": thermal})
            for renewable in ("photovoltaic", "wind", "storage")
            for thermal in ("B", "F", "H")
        )
    return ()


_COMMON_FIELDS = (
    TransformerInputField("capacity_kva", "额定容量", "kVA", True),
    TransformerInputField("no_load_loss_w", "空载损耗", "W", True),
    TransformerInputField("load_loss_w", "负载损耗", "W", True),
)


def category_fields(category_id: str) -> tuple[TransformerInputField, ...]:
    """Return only category-specific fields, excluding common capacity/loss fields."""
    category = _resolve_category(category_id)
    table_no = category.table_no
    if table_no is None:
        return ()
    fields: list[TransformerInputField] = []
    if condition_options(category.category_id):
        fields.append(TransformerInputField("standard_conditions", "标准条件", required=True))
    if table_no == 2:
        fields.append(TransformerInputField("uk_rated_percent", "额定阻抗", "%", required_when="capacity_kva == 630"))
    if table_no in {8, 14, 15}:
        fields.append(TransformerInputField("lv_rated_voltage_kv", "低压额定电压", "kV", True))
    elif table_no in {7, 12}:
        fields.append(TransformerInputField("lv_rated_voltage_kv", "低压额定电压", "kV"))
    if 29 <= table_no <= 35:
        fields.extend((
            TransformerInputField("hv_rated_voltage_kv", "高压额定电压", "kV", True),
            TransformerInputField("lv_rated_voltage_kv", "低压额定电压", "kV", True),
        ))
    if table_no in {27, 28}:
        fields.extend((
            TransformerInputField("uk_hm_rated_percent", "额定阻抗高—中", "%", True),
            TransformerInputField("uk_hl_rated_percent", "额定阻抗高—低", "%", True),
            TransformerInputField("uk_ml_rated_percent", "额定阻抗中—低", "%", True),
        ))
    elif table_no in {23, 24}:
        # The frozen mapping records only the table's HM technical condition;
        # it does not select a loss branch or gate threshold evaluation.
        fields.append(TransformerInputField("uk_hm_rated_percent", "额定阻抗高—中", "%"))
    return tuple(fields)


def visible_fields(category_id: str) -> tuple[TransformerInputField, ...]:
    """Return the common fields and applicable category-specific input fields."""
    category = _resolve_category(category_id)
    if category.table_no is None:
        return ()
    return _COMMON_FIELDS + category_fields(category.category_id)


class TransformerInputContract:
    """Read-only facade suitable for injection into presentation services."""

    @property
    def categories(self) -> tuple[TransformerCategoryOption, ...]:
        return TRANSFORMER_CATEGORIES

    def condition_options(self, category_id: str) -> tuple[TransformerConditionOption, ...]:
        return condition_options(category_id)

    def category_fields(self, category_id: str) -> tuple[TransformerInputField, ...]:
        return category_fields(category_id)

    def visible_fields(self, category_id: str) -> tuple[TransformerInputField, ...]:
        return visible_fields(category_id)

    def normalize(self, values: Mapping[str, Any]) -> dict[str, Any]:
        return normalize_transformer_input(values)


TRANSFORMER_INPUT_CONTRACT = TransformerInputContract()


def _resolve_category(value: Any) -> TransformerCategoryOption:
    if not isinstance(value, str):
        raise TransformerInputError("category_id must be a category ID or exact display label")
    category = _CATEGORY_BY_ID.get(value) or _CATEGORY_BY_LABEL.get(value)
    if category is None:
        raise TransformerInputError(f"unknown transformer category: {value!r}")
    return category


def _canonical_condition_value(field: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TransformerInputError(f"standard_conditions.{field} must be text")
    text = value.strip()
    aliases: dict[str, dict[str, str]] = {
        "core_material": {**_CORE_LABELS, "电工钢": "electrical_steel", "电工钢铁心": "electrical_steel", "electrical_steel": "electrical_steel", "amorphous_alloy": "amorphous_alloy"},
        "vector_group": {**_VECTOR_LABELS, "dyn11_yzn11": "dyn11_yzn11", "yyn0": "yyn0"},
        "thermal_class": {"B级": "B", "B级（100℃）": "B", "B(100℃)": "B", "B100℃": "B", "B": "B", "F级": "F", "F级（120℃）": "F", "F(120℃)": "F", "F120℃": "F", "F": "F", "H级": "H", "H级（145℃）": "H", "H(145℃)": "H", "H145℃": "H", "H": "H"},
        "renewable_type": {**_RENEWABLE_LABELS, "photovoltaic": "photovoltaic", "wind": "wind", "storage": "storage"},
    }
    try:
        return aliases[field][text]
    except KeyError as exc:
        raise TransformerInputError(f"unsupported standard condition {field}={value!r}") from exc


def _as_condition_values(category: TransformerCategoryOption, value: Any) -> dict[str, str]:
    options = condition_options(category.category_id)
    if value is None or value == "":
        return {}
    if isinstance(value, str):
        for option in options:
            if value in (option.condition_id, option.label):
                return dict(option.values)
        raise TransformerInputError(f"condition option is not available for {category.category_id}: {value!r}")
    if not isinstance(value, Mapping):
        raise TransformerInputError("standard_conditions must be an option ID, label, or mapping")
    allowed = {key for option in options for key in option.values}
    if not options:
        raise TransformerInputError(f"{category.category_id} has no standard-condition choices")
    result: dict[str, str] = {}
    for field, raw in value.items():
        if field not in allowed:
            raise TransformerInputError(f"{field!r} is not a standard condition for {category.category_id}")
        result[field] = _canonical_condition_value(field, raw)
    return result


def normalize_transformer_input(values: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize aliases, F category, and H conditions without parsing numbers.

    Numeric values remain exactly as supplied so callers can preserve the input
    text and the Calculator can convert to Decimal without a float round-trip.
    Missing category/condition values are retained as missing for business-status
    handling by the Calculator.
    """
    if not isinstance(values, Mapping):
        raise TransformerInputError("transformer input must be a mapping")
    normalized = dict(values)
    raw_category_id = values.get("category_id")
    raw_category = values.get("category")
    if raw_category_id in (None, "") and raw_category not in (None, ""):
        raw_category_id = raw_category
    if raw_category_id in (None, ""):
        normalized["category_id"] = None
        return normalized
    category = _resolve_category(raw_category_id)
    if raw_category not in (None, ""):
        category_from_label = _resolve_category(raw_category)
        if category_from_label.category_id != category.category_id:
            raise TransformerInputError("category and category_id identify different categories")
    normalized["category_id"] = category.category_id
    normalized["category_label"] = category.label

    aliases = ("rated_capacity_kva",)
    for alias in aliases:
        if alias in values and values[alias] not in (None, ""):
            if normalized.get("capacity_kva") not in (None, "") and str(normalized["capacity_kva"]) != str(values[alias]):
                raise TransformerInputError(f"{alias} conflicts with capacity_kva")
            normalized["capacity_kva"] = values[alias]

    h_values = _as_condition_values(category, values.get("standard_conditions"))
    condition_fields = {"core_material", "vector_group", "thermal_class", "renewable_type"}
    direct_values: dict[str, str] = {}
    allowed_fields = {key for option in condition_options(category.category_id) for key in option.values}
    for field in condition_fields & values.keys():
        if values[field] in (None, ""):
            continue
        if field not in allowed_fields:
            raise TransformerInputError(f"{field!r} is not an allowed condition for {category.category_id}")
        direct_values[field] = _canonical_condition_value(field, values[field])
    for field, direct in direct_values.items():
        if field in h_values and h_values[field] != direct:
            raise TransformerInputError(f"standard_conditions conflicts with {field}")
        h_values[field] = direct

    if h_values:
        normalized["standard_conditions"] = dict(h_values)
        normalized.update(h_values)
    elif "standard_conditions" in values:
        normalized["standard_conditions"] = {}
    return normalized

