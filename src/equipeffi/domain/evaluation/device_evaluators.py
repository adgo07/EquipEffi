"""评价器兼容门面。

实际设备评价器位于``evaluators/``，共享辅助函数和工厂分别位于
``evaluators/shared.py``与``evaluator_registry.py``。本模块保留历史导出，
避免旧调用方在迁移期间中断。
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from ..common.enums import ComparisonDirection, Conclusion
from ..common.models import EvaluationResult
from .decimal_math import bracket, decimal, linear_interpolate, rounded
from .grading import compare, grade_five, grade_three, grade_three_optional
from .evaluators.shared import (
    _active_or_unable,
    _attach_lookup_trace,
    _attach_metrics,
    _condition_hit,
    _condition_matches,
    _condition_text,
    _decimal_sequence,
    _explicit_boundary_hit,
    _interval_hit,
    _matching_boundary,
    _missing,
    _percent_or_unable,
    _positive_integer_or_unable,
    _positive_or_unable,
    _range_or_unable,
    _record_matches,
    _reference,
    _result,
    _value,
    out_of_scope,
    unable,
)
from .evaluator_registry import EVALUATOR_FACTORIES
from .evaluators.boiler import BoilerEvaluator
from .evaluators.blower import BlowerEvaluator
from .evaluators.compressor import CompressorEvaluator
from .evaluators.fan import FanEvaluator
from .evaluators.heat_treatment import HeatTreatmentEvaluator
from .evaluators.hvac import HvacEvaluator
from .evaluators.motor import MotorEvaluator, PmsmEvaluator
from .evaluators.pump import ChemicalPumpEvaluator, WaterPumpEvaluator
from .evaluators.submersible import SubmersibleEvaluator
from .evaluators.transformer import TransformerEvaluator


def _specific_speed(values: dict[str, Any], chemical: bool = False) -> tuple[Decimal, dict[str, Any]]:
    """Compatibility hook for the centrifugal-pump specific-speed helper.

    The implementation now lives in ``evaluators.pump``.  Keeping this
    forwarding function preserves the historical patch/import point used by
    integrations and tests while allowing the split evaluator to call the
    same hook dynamically.
    """

    from .evaluators.pump import _specific_speed as implementation

    return implementation(values, chemical)
