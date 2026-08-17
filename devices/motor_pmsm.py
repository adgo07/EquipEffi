# -*- coding: utf-8 -*-
"""devices/motor_pmsm.py - 永磁同步电动机判定（GB 30253-2024）
表选择：起动方式（异步起动/变频调速）→电压+冷却→表→功率×极数/转速查表+插值
"""
from .base import BaseEvaluator, to_float, CANNOT_JUDGE, NOT_MEET_3
from .motor_lv import motor_judge


def _pick_pmsm_table(tables, start_type, voltage, cooling):
    """start_type: 异步起动/变频调速；变频表标题含'变频'且含等级"""
    st = str(start_type or "")
    if "变频" in st:
        # 变频表：按等级分表（表8~28），需要按"1级/2级/3级"选三张
        groups = {"1": [], "2": [], "3": []}
        for t in tables:
            if "变频" not in t["title"]:
                continue
            for lv in ("1", "2", "3"):
                if lv + "级" in t["title"]:
                    groups[lv].append(t)
        v = "10" if (voltage and voltage > 7) else ("3" if voltage else None)
        sel = {}
        for lv in ("1", "2", "3"):
            cands = [t for t in groups[lv] if
                     ("10kV" in t["title"]) == (v == "10")]
            if not cands:
                cands = groups[lv]
            if cands:
                sel[lv] = cands[0]
        return sel
    else:
        # 异步起动：表1~7
        for t in tables:
            if "变频" in t["title"] or "电梯" in t["title"]:
                continue
            title = t["title"]
            if voltage is None:
                return t
            is10 = "10kV" in title
            if (voltage > 7) == is10:
                return t
        return None


class MotorPmsmEvaluator(BaseEvaluator):
    code = "motor_pmsm"
    name = "永磁同步电机"
    standard_key = "motor_pmsm"

    def evaluate(self, params: dict) -> dict:
        start_type = params.get("start_type", "异步起动")
        voltage = to_float(params.get("voltage_kv"))
        cooling = params.get("cooling")
        power = to_float(params.get("power_kw"))
        speed = to_float(params.get("speed_rpm"))
        poles = params.get("poles")
        eff = to_float(params.get("efficiency_pct"))

        sel = _pick_pmsm_table(self.standard["tables"], start_type, voltage, cooling)
        if not sel:
            return {"result": CANNOT_JUDGE, "note": "未匹配到标准表"}

        if "变频" in str(start_type or ""):
            # 变频：按转速档查（表8~28每表一个等级）
            limits = {}
            result = NOT_MEET_3
            for lv in ("1", "2", "3"):
                t = sel.get(lv)
                if not t:
                    continue
                if power is None or speed is None:
                    limits[lv] = None
                    continue
                caps = sorted({r["power_kw"] for r in t["rows"]})
                lo = None
                for c in caps:
                    if c <= power:
                        lo = c
                    else:
                        break
                hi = None
                for c in caps:
                    if c > power:
                        hi = c
                        break
                row = None
                if lo is not None:
                    cands = [r for r in t["rows"] if r["power_kw"] == lo]
                    row = cands[0] if cands else None
                if row is None and hi is not None:
                    cands = [r for r in t["rows"] if r["power_kw"] == hi]
                    row = cands[0] if cands else None
                if row is None:
                    limits[lv] = None
                    continue
                # 转速档匹配：找含speed的区间
                idx = None
                for i, (label, rg) in enumerate(t["dims"]):
                    lo_s, hi_s = rg
                    if lo_s < speed <= hi_s or (lo_s == hi_s and speed <= lo_s):
                        idx = i
                        break
                if idx is None:
                    # 取最近
                    diffs = []
                    for i, (label, rg) in enumerate(t["dims"]):
                        diffs.append((abs(rg[1] - speed), i))
                    idx = min(diffs)[1]
                limits[lv] = row["efficiency"].get(lv, {}).get(str(idx), row["efficiency"].get(lv, {}).get(idx))
                if limits[lv] is not None and eff is not None and eff >= limits[lv]:
                    result = lv + "级"
                    break
            return {"level1": limits.get("1"), "level2": limits.get("2"), "level3": limits.get("3"),
                    "result": result, "basis": "GB 30253-2024 变频调速表",
                    "note": "" if result != CANNOT_JUDGE else "缺少功率/转速/效率"}
        else:
            t = sel
            try:
                poles = str(poles).replace("极", "").strip()
                int(poles)
            except (TypeError, ValueError):
                return {"result": CANNOT_JUDGE, "note": f"极数格式错误[{poles}]"}
            limits, result = motor_judge(t["rows"], t["dims"], power, poles, eff)
            return {"level1": limits.get("1"), "level2": limits.get("2"), "level3": limits.get("3"),
                    "result": result, "basis": f"GB 30253-2024 {t['title'][:24]}",
                    "note": "" if result != CANNOT_JUDGE else "缺少功率或效率"}
