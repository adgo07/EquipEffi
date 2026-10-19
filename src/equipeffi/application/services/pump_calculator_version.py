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
    "pump-calculator:sha256:fe33a288210678508e85a3a806d83fd5"
    "8ba8c46fbdac98184879d3fd0e60e856"
)
