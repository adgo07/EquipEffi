# -*- coding: utf-8 -*-
"""devices/pump.py - 清水泵/化工泵判定（GB 19762-2025 公式法）
清水泵：ns=3.65n√Q/H^0.75（双吸Q取半、多级H取单级）→Ci常数→回归公式算各级效率
化工泵：ns→ηb(6阶多项式)→Δη(修正)→η0=ηb-Δη→表2偏移→各级限值
"""
import math
from .base import BaseEvaluator, to_float, CANNOT_JUDGE, NOT_MEET_3


def calc_ns(n, q_m3h, h_m, stages, suction):
    """比转数：Q转m³/s（双吸取半），H取单级"""
    q_s = q_m3h / 3600.0
    if "双" in str(suction):
        q_s /= 2.0
    h1 = h_m / stages if stages and stages > 1 else h_m
    if h1 <= 0 or q_s <= 0:
        return None
    return 3.65 * n * math.sqrt(q_s) / (h1 ** 0.75)


def _poly(coefs, x):
    """coefs=[a6,a5,a4,a3,a2,a1,a0]，x为ln值"""
    return (coefs[0] * x ** 6 + coefs[1] * x ** 5 + coefs[2] * x ** 4
            + coefs[3] * x ** 3 + coefs[4] * x ** 2 + coefs[5] * x + coefs[6])


class PumpEvaluator(BaseEvaluator):
    code = "pump"
    name = "离心泵（清水/化工）"
    standard_key = "pump"

    def evaluate(self, params: dict) -> dict:
        kind = str(params.get("kind") or "清水").strip()  # 清水/化工
        q = to_float(params.get("flow_m3h"))
        h = to_float(params.get("head_m"))
        n = to_float(params.get("speed_rpm"))
        stages = to_float(params.get("stages")) or 1
        suction = params.get("suction")  # 单吸/双吸
        eff = to_float(params.get("efficiency_pct"))
        pump_type = str(params.get("pump_type") or "").strip()  # 单级单吸/单级双吸/管道/多级/轻型多级立式/轻型多级卧式
        if q is None or h is None or n is None:
            return {"result": CANNOT_JUDGE, "note": "缺少流量/扬程/转速"}
        if eff is None:
            return {"result": CANNOT_JUDGE, "note": "缺少实测效率（须为检测值）"}
        ns = calc_ns(n, q, h, stages, suction)
        if ns is None:
            return {"result": CANNOT_JUDGE, "note": "比转数计算失败"}
        if ns < 20 or ns > 300:
            return {"result": "不在范围", "note": f"比转数ns={ns:.1f}超出标准范围20~300"}
        std = self.standard
        if "化" in kind:
            return self._chemical(std, q, ns, stages, eff, pump_type)
        return self._water(std, q, ns, stages, suction, pump_type, eff)

    # ---------- 清水泵 ----------
    def _water(self, std, q, ns, stages, suction, pump_type, eff):
        # 确定泵类型（缺省推断）
        pt = pump_type
        if not pt:
            if stages and stages > 1:
                pt = "多级"
            elif "双" in str(suction):
                pt = "单级双吸"
            else:
                pt = "单级单吸"
        # Ci表匹配
        ci_row = None
        for row in std["water"]["ci"]:
            if row["type"] in pt and row["q_min"] <= q <= row["q_max"]:
                ci_row = row
                break
        if ci_row is None:
            return {"result": "不在范围", "note": f"流量Q={q}m³/h超出Ci常数表范围"}
        # 公式系数
        formula = std["water"]["formulas"]["单级" if stages == 1 or "单" in pt and "多" not in pt else "多级"]
        # 多级判断：多级泵用公式(3)
        is_multi = (stages and stages > 1) or "多级" in pt
        f = std["water"]["formulas"]["多级" if is_multi else "单级"]
        ln_q, ln_ns = math.log(q), math.log(ns)
        levels = []
        for ci in ci_row["ci"]:
            eta = (f["a"] * ln_ns ** 2 + f["b"] * ln_q ** 2 + f["c"] * ln_ns * ln_q
                   + f["d"] * ln_ns + f["e"] * ln_q - ci)
            levels.append(eta)
        result = NOT_MEET_3
        for i, lv in enumerate(("1", "2", "3")):
            if eff >= levels[i]:
                result = lv + "级"
                break
        return {"level1": round(levels[0], 2), "level2": round(levels[1], 2), "level3": round(levels[2], 2),
                "result": result, "basis": f"GB 19762-2025 公式({2 if not is_multi else 3})+表3",
                "note": f"ns={ns:.1f}, Ci={ci_row['ci']}"}

    # ---------- 化工泵 ----------
    def _chemical(self, std, q, ns, stages, eff, pump_type):
        pt = "多级" if (stages and stages > 1) or "多" in str(pump_type) else "单级"
        q_eff = min(q, 3000)
        ln_q = math.log(q_eff)
        eta_b = _poly(std["chemical"]["eta_b"][pt], ln_q)
        # Δη
        delta = 0.0
        if 20 <= ns < 120:
            delta = _poly(std["chemical"]["delta_eta"]["ns_20_120"], ns)
        elif 210 < ns <= 300:
            delta = _poly(std["chemical"]["delta_eta"]["ns_210_300"], ns)
        eta0 = eta_b - delta if (20 <= ns < 120 or 210 < ns <= 300) else eta_b
        # 表2偏移
        off = None
        for row in std["chemical"]["level_offsets"]:
            if row["pump"] == pt and row["q_min"] <= q <= row["q_max"] and row["ns_min"] <= ns <= row["ns_max"]:
                off = row
                break
        if off is None:
            return {"result": "不在范围", "note": f"ns={ns:.1f}或Q={q}超出表2范围"}
        levels = [eta0 + o for o in off["offsets"]]
        result = NOT_MEET_3
        for i, lv in enumerate(("1", "2", "3")):
            if eff >= levels[i]:
                result = lv + "级"
                break
        return {"level1": round(levels[0], 2), "level2": round(levels[1], 2), "level3": round(levels[2], 2),
                "result": result, "basis": f"GB 19762-2025 公式(4/5/6/7)+表2",
                "note": f"ns={ns:.1f}, ηb={eta_b:.2f}, Δη={delta:.2f}, η0={eta0:.2f}"}
