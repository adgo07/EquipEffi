"""Shared current input contract for the three motor standards."""
from ..motor_hv.input_contract import MotorProductInputContract as V4MotorInputContract
from ..motor_pmsm.input_contract import BRANCHES, COOLING_CODES

MOTOR_V5_REVISION = "motor-input.v5"


class MotorProductInputContract(V4MotorInputContract):
    categories = V4MotorInputContract.categories[:-2] + tuple(
        branch.category for branch in BRANCHES.values()) + V4MotorInputContract.categories[-2:]

    @staticmethod
    def visible_fields(category):
        if category in BRANCHES:
            return BRANCHES[category].fields
        return V4MotorInputContract.visible_fields(category)

    @staticmethod
    def snapshot_fields(category, values):
        if category in BRANCHES:
            return BRANCHES[category].fields
        return V4MotorInputContract.snapshot_fields(category, values)

    @staticmethod
    def options(category, field):
        if category in BRANCHES:
            return tuple((code, code) for code in COOLING_CODES) if (
                field == "cooling_method" and BRANCHES[category].high_voltage) else ()
        return V4MotorInputContract.options(category, field)

    @staticmethod
    def scope_hint(category):
        if category in BRANCHES:
            return BRANCHES[category].scope_hint
        return V4MotorInputContract.scope_hint(category)


MOTOR_PRODUCT_INPUT_CONTRACT = MotorProductInputContract()
