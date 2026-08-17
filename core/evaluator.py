# -*- coding: utf-8 -*-
"""core/evaluator.py - 判定调度（模块B）
把清洗后的params按设备key分发到对应判定器，返回判定结果。
"""
from devices.transformer import TransformerEvaluator
from devices.motor_lv import MotorLvEvaluator
from devices.motor_hv import MotorHvEvaluator
from devices.motor_pmsm import MotorPmsmEvaluator
from devices.compressor import CompressorEvaluator
from devices.pump import PumpEvaluator
from devices.fan import FanEvaluator
from devices.blower import BlowerEvaluator
from devices.submersible import SubmersibleEvaluator
from devices.boiler import BoilerEvaluator
from devices.heat_treatment import HeatTreatmentEvaluator

_EVALUATORS = {
    "transformer": TransformerEvaluator(),
    "motor_lv": MotorLvEvaluator(),
    "motor_hv": MotorHvEvaluator(),
    "motor_pmsm": MotorPmsmEvaluator(),
    "compressor": CompressorEvaluator(),
    "pump_water": PumpEvaluator(),
    "pump_chem": PumpEvaluator(),
    "fan": FanEvaluator(),
    "blower": BlowerEvaluator(),
    "submersible": SubmersibleEvaluator(),
    "boiler": BoilerEvaluator(),
    "heat_treatment": HeatTreatmentEvaluator(),
}

# 设备key → 判定器需要的params补充字段
EXTRA_PARAMS = {
    "pump_water": {"kind": "清水"},
    "pump_chem": {"kind": "化工"},
    "motor_pmsm": {"start_type": "异步起动"},
}


def evaluate_device(key, params):
    """单台设备判定。返回判定结果dict + 状态"""
    ev = _EVALUATORS[key]
    p = dict(params)
    p.update(EXTRA_PARAMS.get(key, {}))
    try:
        res = ev.evaluate(p)
    except Exception as e:
        res = {"result": "判定异常", "note": f"{type(e).__name__}: {e}"}
    res.setdefault("level1", None)
    res.setdefault("level2", None)
    res.setdefault("level3", None)
    res.setdefault("note", "")
    res.setdefault("basis", "")
    return res


def evaluate_all(devices: dict) -> dict:
    """清洗结果 → 判定结果。devices: {key: [{params, issues, row, name}]}
    返回 {key: [{...原字段, result_dict}]}"""
    out = {}
    for key, items in devices.items():
        results = []
        for item in items:
            res = evaluate_device(key, item["params"])
            results.append({**item, "result_dict": res})
        out[key] = results
    return out
