"""Explicit GB30254 product fields; no voltage-based standard inference."""
from types import MappingProxyType
from ..motor.input_contract import MOTOR_INPUT_CONTRACT, MotorCategoryOption, MotorInputField

HV_CATEGORY_ID = "gb30254_cage_induction"
HV_CATEGORY = MotorCategoryOption(HV_CATEGORY_ID,
    "GB 30254—2024 高压三相笼型异步电动机", None, MappingProxyType({}))
COOLING_CODES = ("IC01", "IC11", "IC21", "IC31", "IC81W", "IC611", "IC616", "IC511", "IC516", "IC411")
HV_FIELDS = tuple(MotorInputField(*args, required=True) for args in (
    ("rated_voltage_v", "额定电压", "V"), ("rated_frequency_hz", "额定频率", "Hz"),
    ("cooling_method", "冷却方式", None), ("rated_output_power_kw", "额定输出功率", "kW"),
    ("poles", "极数", "极"), ("rated_efficiency_pct", "额定效率", "%"))) + (
        MotorInputField("user_note", "备注"),)


class MotorProductInputContract:
    categories = MOTOR_INPUT_CONTRACT.categories[:-2] + (HV_CATEGORY,) + MOTOR_INPUT_CONTRACT.categories[-2:]
    basis_options = MOTOR_INPUT_CONTRACT.basis_options
    speed_band_label = MOTOR_INPUT_CONTRACT.speed_band_label
    legacy_visible_fields = MOTOR_INPUT_CONTRACT.legacy_visible_fields

    @staticmethod
    def visible_fields(category):
        return HV_FIELDS if category == HV_CATEGORY_ID else MOTOR_INPUT_CONTRACT.visible_fields(category)

    @staticmethod
    def snapshot_fields(category, values):
        return HV_FIELDS if category == HV_CATEGORY_ID else MOTOR_INPUT_CONTRACT.snapshot_fields(category, values)

    @staticmethod
    def options(category, field):
        if category == HV_CATEGORY_ID:
            return tuple((code, code) for code in COOLING_CODES) if field == "cooling_method" else ()
        return MOTOR_INPUT_CONTRACT.options(category, field)

    @staticmethod
    def scope_hint(category):
        if category == HV_CATEGORY_ID:
            return "高压候选已实现，待独立验收。额定电压3000、3300、6000或10000 V，50 Hz；按冷却方式及极数查表。"
        return MOTOR_INPUT_CONTRACT.scope_hint(category)


MOTOR_PRODUCT_INPUT_CONTRACT = MotorProductInputContract()
