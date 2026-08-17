# -*- coding: utf-8 -*-
"""devices/motor_hv.py - 高压电动机判定（GB 30254-2024）
表选择：电压档(3/6/10kV) + 冷却方式(IC代码) → 功率×极数查表+插值
"""
from .base import BaseEvaluator, to_float, CANNOT_JUDGE, NOT_MEET_3
from .motor_lv import motor_judge


def _voltage_bin(v):
    """电压归一：3kV(3.3)、6kV(6.6)、10kV(11归10)"""
    if v is None:
        return None
    if isinstance(v, str):
        v = float(v.replace("kV", "").strip())
    if v <= 3.5:
        return "3"
    if v <= 7:
        return "6"
    return "10"


def _pick_table(tables, voltage, cooling):
    """按电压+冷却选表。冷却IC代码归类：
    IC01/11/21/31/81W → 开启式（表1/表2）
    IC611/616/511/516 → 封闭式（表3/表4）
    IC411 → 封闭式自扇冷（表5/表6）
    """
    cooling = str(cooling or "").strip().upper()
    if any(x in cooling for x in ("IC01", "IC11", "IC21", "IC31", "IC81W")):
        grp = "01"
    elif any(x in cooling for x in ("IC611", "IC616", "IC511", "IC516")):
        grp = "61"
    else:
        grp = "41"
    v = _voltage_bin(voltage)
    for t in tables:
        title = t["title"]
        has_v3 = "3kV" in title or "6kV" in title
        has_v10 = "10kV" in title
        if grp == "01" and ("IC01" in title or "IC11" in title or "IC81W" in title or "IC21" in title):
            pass
        elif grp == "61" and ("IC611" in title or "IC511" in title):
            pass
        elif grp == "41" and "IC411" in title:
            pass
        else:
            continue
        if v == "10" and has_v10 and not has_v3:
            return t
        if v != "10" and has_v3 and not has_v10:
            return t
    return None


class MotorHvEvaluator(BaseEvaluator):
    code = "motor_hv"
    name = "高压电动机"
    standard_key = "motor_hv"

    def evaluate(self, params: dict) -> dict:
        voltage = to_float(params.get("voltage_kv"))
        cooling = params.get("cooling")
        power = to_float(params.get("power_kw"))
        poles = params.get("poles")
        eff = to_float(params.get("efficiency_pct"))
        if voltage is None or not cooling:
            return {"result": CANNOT_JUDGE, "note": "缺少电压等级或冷却方式"}
        t = _pick_table(self.standard["tables"], voltage, cooling)
        if t is None:
            return {"result": CANNOT_JUDGE, "note": f"未匹配表：电压{voltage}kV 冷却{cooling}"}
        try:
            poles = str(poles).replace("极", "").strip()
            int(poles)
        except (TypeError, ValueError):
            return {"result": CANNOT_JUDGE, "note": f"极数格式错误[{poles}]"}
        limits, result = motor_judge(t["rows"], t["dims"], power, poles, eff)
        return {
            "level1": limits.get("1"), "level2": limits.get("2"), "level3": limits.get("3"),
            "result": result, "basis": f"GB 30254-2024 {t['title'][:30]}",
            "note": "" if result != CANNOT_JUDGE else "缺少功率或效率",
        }
