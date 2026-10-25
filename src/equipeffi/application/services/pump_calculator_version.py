"""Reviewed source identifier for the GB 19762 pump calculator.

The value is a source fingerprint maintained with a unit test. It is not
computed at runtime, so packaged applications do not need to ship Python source.
"""

PUMP_CALCULATOR_SOURCE_FILES: tuple[str, ...] = (
    "src/equipeffi/application/services/centrifugal_pump_analysis_service.py",
    "src/equipeffi/application/result_projection.py",
    "src/equipeffi/domain/common/enums.py",
    "src/equipeffi/domain/common/models.py",
    "src/equipeffi/domain/evaluation/decimal_math.py",
    "src/equipeffi/domain/evaluation/device_evaluators.py",
    "src/equipeffi/domain/evaluation/device_types.py",
    "src/equipeffi/domain/evaluation/evaluator_registry.py",
    "src/equipeffi/domain/evaluation/evaluators/pump.py",
    "src/equipeffi/domain/evaluation/evaluators/shared.py",
    "src/equipeffi/domain/evaluation/grading.py",
    "src/equipeffi/application/services/pump_release_gate.py",
)

PUMP_CALCULATOR_VERSION = (
    "pump-calculator:sha256:064c91cd346d6aff9c522f01c6ca3422392391807af6054cca93b6e574d56da0"
)
