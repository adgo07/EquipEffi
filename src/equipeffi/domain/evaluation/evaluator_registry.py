"""运行中的17个内部评价器注册表。

公开接口仍由``device_types``负责15类到17个内部profile的路由；本模块只
负责将内部profile绑定到评价器，避免把工厂注册和共享辅助函数混在一起。
"""

from __future__ import annotations

from typing import Any, Callable

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


EVALUATOR_FACTORIES: dict[str, Callable[[], Any]] = {
    "transformer": TransformerEvaluator,
    "motor_lv": lambda: MotorEvaluator("motor_lv"),
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
