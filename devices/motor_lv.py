# -*- coding: utf-8 -*-
"""devices/motor_lv.py - 低压电动机判定（GB 18613-2020）
功率×极数查表 + 功率档效率线性插值；效率≥限值
"""
from .base import BaseEvaluator, to_float, interp, find_bracket, LEVEL_1, LEVEL_2, LEVEL_3, NOT_MEET_3, CANNOT_JUDGE


def motor_judge(rows, power_kw, poles, efficiency_pct):
    """通用电机判定：rows=标准行[{power_kw, efficiency:{lv:{idx:val}}}]，
    poles=极数序列，返回(限值dict, result)"""
    if power_kw is None or efficiency_pct is None:
        return {}, CANNOT_JUDGE
    caps = sorted({r["power_kw"] for r in rows})
    lo, hi = find_bracket(caps, power_kw)
    if lo is None:
        return {}, CANNOT_JUDGE
    row_lo = next(r for r in rows if r["power_kw"] == lo)
    row_hi = next(r for r in rows if r["power_kw"] == hi) if hi != lo else row_lo
    try:
        pole_idx = rows[0]["poles"].index(str(poles))
    except ValueError:
        return {}, CANNOT_JUDGE
    limits = {}
    for lv in ("1", "2", "3"):
        v_lo = row_lo["efficiency"].get(lv, {}).get(pole_idx)
        if row_hi is row_lo:
            limits[lv] = v_lo
        else:
            v_hi = row_hi["efficiency"].get(lv, {}).get(pole_idx)
            limits[lv] = interp(power_kw, lo, hi, v_lo, v_hi)
    result = NOT_MEET_3
    for lv in ("1", "2", "3"):
        if limits[lv] is not None and efficiency_pct >= limits[lv]:
            result = lv + "级"
            break
    return limits, result


class MotorLvEvaluator(BaseEvaluator):
    code = "motor_lv"
    name = "低压电动机"
    standard_key = "motor_lv"

    def evaluate(self, params: dict) -> dict:
        power = to_float(params.get("power_kw"))
        poles = params.get("poles")
        eff = to_float(params.get("efficiency_pct"))
        if poles is None:
            return {"result": CANNOT_JUDGE, "note": "缺少极数"}
        try:
            poles = str(poles).replace("极", "").strip()
            int(poles)
        except (TypeError, ValueError):
            return {"result": CANNOT_JUDGE, "note": f"极数格式错误[{poles}]"}
        limits, result = motor_judge(self.standard["rows"], power, poles, eff)
        return {
            "level1": limits.get("1"), "level2": limits.get("2"), "level3": limits.get("3"),
            "result": result,
            "basis": "GB 18613-2020 表1",
            "note": "功率不在档位时效率线性插值" if result != CANNOT_JUDGE else "缺少功率或效率",
        }
