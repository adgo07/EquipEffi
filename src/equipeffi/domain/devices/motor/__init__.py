"""Motor-standard domain contracts and calculators."""

from .calculator import (
    CALCULATOR_VERSION, DECIMAL_PROFILE_ID, Gb18613MotorCalculator,
    MotorEvaluation, MotorPackError,
)
from .input_contract import (
    BASIS_OPTIONS, MOTOR_CATEGORIES, MOTOR_INPUT_CONTRACT,
    MotorCategoryOption, MotorInputError, MotorInputField,
    efficiency_basis_hint, normalize_motor_input, options, scope_hint, speed_band_label, visible_fields,
)

__all__ = [
    "BASIS_OPTIONS", "CALCULATOR_VERSION", "DECIMAL_PROFILE_ID",
    "Gb18613MotorCalculator", "MOTOR_CATEGORIES", "MOTOR_INPUT_CONTRACT",
    "MotorCategoryOption", "MotorEvaluation", "MotorInputError",
    "MotorInputField", "MotorPackError", "normalize_motor_input", "options",
    "efficiency_basis_hint", "scope_hint", "speed_band_label", "visible_fields",
]
