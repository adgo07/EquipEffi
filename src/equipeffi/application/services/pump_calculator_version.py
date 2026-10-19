"""Reviewed source identifier for the GB 19762 pump calculator.

The value is a source fingerprint maintained with a unit test. It is not
computed at runtime, so packaged applications do not need to ship Python source.
"""

PUMP_CALCULATOR_SOURCE_FILES: tuple[str, ...] = (
    "src/equipeffi/application/services/centrifugal_pump_analysis_service.py",
    "src/equipeffi/domain/evaluation/device_types.py",
    "src/equipeffi/domain/evaluation/evaluator_registry.py",
    "src/equipeffi/domain/evaluation/evaluators/pump.py",
)

PUMP_CALCULATOR_VERSION = (
    "pump-calculator:sha256:6c2e9b5031c349ba014ee295273e3f0a0"
    "ac4dbd4fb53252f90ae165378202f16"
)
