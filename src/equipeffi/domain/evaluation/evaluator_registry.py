"""Internal compatibility evaluator registrations.

GB 18613 now delegates to its dedicated calculator. The older shared MotorEvaluator
remains only for the GB 30254 high-voltage profile; PMSM keeps its own evaluator.
"""
from __future__ import annotations

from typing import Any, Callable

from ..common.enums import Conclusion
from ..common.models import EvaluationResult
from ..devices.motor.calculator import Gb18613MotorCalculator
from .evaluators.boiler import BoilerEvaluator
from .evaluators.blower import BlowerEvaluator
from .evaluators.compressor import CompressorEvaluator
from .evaluators.fan import FanEvaluator
from .evaluators.heat_treatment import HeatTreatmentEvaluator
from .evaluators.hvac import HvacEvaluator
from .evaluators.motor import MotorEvaluator, PmsmEvaluator
from .evaluators.pump import ChemicalPumpEvaluator, WaterPumpEvaluator
from .evaluators.submersible import SubmersibleEvaluator


_CONCLUSIONS = {
    "LEVEL_1": Conclusion.LEVEL_1,
    "LEVEL_2": Conclusion.LEVEL_2,
    "LEVEL_3": Conclusion.LEVEL_3,
    "NOT_COMPLIANT": Conclusion.NOT_COMPLIANT,
    "OUT_OF_SCOPE": Conclusion.OUT_OF_SCOPE,
    "UNABLE_TO_JUDGE": Conclusion.UNABLE_TO_JUDGE,
}


class Gb18613EvaluatorAdapter:
    """Thin legacy result adapter over the single GB18613 calculator."""

    def __init__(self):
        self._calculator = Gb18613MotorCalculator()

    def evaluate(self, values: dict[str, Any], pack: dict[str, Any]) -> EvaluationResult:
        result = self._calculator.evaluate(values, pack)
        conclusion = _CONCLUSIONS.get(
            result.conclusion, Conclusion.UNABLE_TO_JUDGE)
        thresholds = dict(result.thresholds)
        limits = {
            f"{index}级效率_%": (
                item.get("display_text")
                if item.get("state") == "AVAILABLE"
                else "—" if item.get("state") == "NO_INDICATOR" else None
            )
            for index, item in (
                (1, thresholds.get("grade_1", {})),
                (2, thresholds.get("grade_2", {})),
                (3, thresholds.get("grade_3", {})),
            )
        }
        measured = values.get("measured_efficiency_pct")
        return EvaluationResult(
            record_id=str(values.get("record_id", "")),
            conclusion=conclusion,
            actual_metrics={"实测效率_%": measured} if measured not in (None, "") else {},
            limits=limits,
            lookups=[dict(item) for item in result.trace],
            trace=[dict(item) for item in result.trace],
            missing_fields=list(result.missing_fields),
            standard_reference=dict(result.references),
            explanation=result.explanation,
            public_device_type="motor",
            internal_device_type="motor_lv",
            support_status="SUPPORTED",
            evaluation_status=result.evaluation_status,
            grade=result.grade,
            issue_codes=list(result.reason_codes),
        )


EVALUATOR_FACTORIES: dict[str, Callable[[], Any]] = {
    "motor_lv": Gb18613EvaluatorAdapter,
    "motor_hv": lambda: MotorEvaluator("motor_hv"),
    "motor_pmsm": lambda: PmsmEvaluator("motor_pmsm"),
    "compressor": CompressorEvaluator,
    "pump_water": WaterPumpEvaluator,
    "pump_chemical": ChemicalPumpEvaluator,
    "fan": FanEvaluator,
    "blower": BlowerEvaluator,
    "submersible": SubmersibleEvaluator,
    "boiler": BoilerEvaluator,
    "heat_treatment": HeatTreatmentEvaluator,
    "heat_pump_chiller": lambda: HvacEvaluator("heat_pump_chiller"),
    "heat_pump_water_heater": lambda: HvacEvaluator("heat_pump_water_heater", True),
    "duct_ac": lambda: HvacEvaluator("duct_ac"),
    "unitary_ac": lambda: HvacEvaluator("unitary_ac"),
    "multi_split_ac": lambda: HvacEvaluator("multi_split_ac"),
}
