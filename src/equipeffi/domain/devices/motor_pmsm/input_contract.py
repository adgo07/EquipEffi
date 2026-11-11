"""Explicit GB 30253 categories, fields and cooling codes."""
from dataclasses import dataclass
from types import MappingProxyType

from ..motor.input_contract import MotorCategoryOption, MotorInputField

STANDARD_CODE = "GB 30253-2024"
COOLING_GROUPS = (
    ("IC81W", "IC86W", "IC71W(IC3W7)"),
    ("IC411", "IC416"),
    ("IC511", "IC611", "IC616", "IC516", "IC666"),
)
COOLING_CODES = tuple(code for group in COOLING_GROUPS for code in group)

_VOLTAGE = MotorInputField("rated_voltage_v", "额定电压", "V", required=True)
_FREQUENCY = MotorInputField("rated_frequency_hz", "额定频率", "Hz", required=True)
_COOLING = MotorInputField("cooling_method", "冷却方式", required=True)
_POWER = MotorInputField("rated_output_power_kw", "额定输出功率", "kW", required=True)
_POLES = MotorInputField("poles", "极数", "极", required=True)
_SPEED = MotorInputField("rated_speed_rpm", "额定转速", "r/min", required=True)
_EFFICIENCY = MotorInputField("rated_efficiency_pct", "额定效率", "%", required=True)
_NOTE = MotorInputField("user_note", "备注")


@dataclass(frozen=True)
class PmsmBranch:
    code: str
    category: MotorCategoryOption
    fields: tuple[MotorInputField, ...]
    high_voltage: bool
    pole_axis: bool
    scope_hint: str


def _branch(code: str, suffix: str, label: str, *, high_voltage: bool,
            pole_axis: bool, scope_hint: str) -> PmsmBranch:
    category = MotorCategoryOption(f"gb30253_{suffix}",
        f"GB 30253—2024 永磁同步电动机—{label}", None, MappingProxyType({}))
    fields = (_VOLTAGE,) + ((_FREQUENCY,) if pole_axis else ()) + ((_COOLING,) if high_voltage else ())
    fields += (_POWER, _POLES if pole_axis else _SPEED, _EFFICIENCY, _NOTE)
    return PmsmBranch(code, category, fields, high_voltage, pole_axis,
                      f"适用于连续工作制、一般用途或防爆用途的{label}永磁同步电动机。{scope_hint}")


BRANCHES = MappingProxyType({branch.category.category_id: branch for branch in (
    _branch("A", "lv_async_start", "低压异步起动", high_voltage=False, pole_axis=True,
            scope_hint="额定电压≤1140 V，额定频率50 Hz。"),
    _branch("B", "hv_async_start", "高压异步起动", high_voltage=True, pole_axis=True,
            scope_hint="额定电压3000、3300、6000或10000 V，额定频率50 Hz。"),
    _branch("C", "lv_vfd", "低压变频调速", high_voltage=False, pole_axis=False,
            scope_hint="额定电压≤1140 V，按额定转速查表。"),
    _branch("D", "hv_vfd", "高压变频调速", high_voltage=True, pole_axis=False,
            scope_hint="额定电压3000、3300、6000或10000 V，按额定转速查表。"),
    _branch("E", "elevator", "电梯用", high_voltage=False, pole_axis=False,
            scope_hint="额定电压≤1140 V，按额定转速区间查表。"),
)})
