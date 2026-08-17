# -*- coding: utf-8 -*-
"""devices/fan.py - 通风机判定（GB 19761-2020）
离心：Ψ=pF×kp/(ρ×u²)，ns=5.54n√(Q/3600)/(1.2×pF×kp/ρ)^0.75 → ψ区间×ns区间×机号区间查效率
轴流：按轮毂比γ×机号区间查效率
外转子：ψ×ns×机号区间
公式与V1.11验证一致（除尘风机Ψ=0.489、ns=64.5）
"""
import math
import re
from .base import BaseEvaluator, to_float, CANNOT_JUDGE, NOT_MEET_3


def _kp(pF, psg2, k):
    """压缩性修正系数（V1.11公式）：kp = pF/psg2×(((k-1)/k×pF/psg2+1)^(k/(k-1))-1)^(-1)"""
    if not psg2 or psg2 <= 0:
        return 1.0
    x = pF / psg2
    return x * (((k - 1) / k * x + 1) ** (k / (k - 1)) - 1) ** (-1)


def _in_range(val, rng):
    """区间匹配：'1.35≤ψ<1.55' / '>1800' / '45<ns≤65' / 'γ<0.3' / 'No2<机号≤No2.5'
    按比较符方向解析：'1.35≤'→val≥1.35；'<1.55'→val<1.55"""
    s = str(rng).strip()
    if not s:
        return True
    ok = True
    for p in re.findall(r"(\d+(?:\.\d+)?)\s*([<>≤≥])|([<>≤≥])\s*(?:No|机号)?\s*(\d+(?:\.\d+)?)", s):
        if p[0]:
            # "1.35≤" 数字在左：num op 变量 → val 反向比较
            num, op = float(p[0]), p[1]
            if op == "<":
                ok = ok and val > num
            elif op == "≤":
                ok = ok and val >= num
            elif op == ">":
                ok = ok and val < num
            elif op == "≥":
                ok = ok and val <= num
        else:
            # "≤1.55" 符号在左：变量 op num
            op, num = p[2], float(p[3])
            if op == "<":
                ok = ok and val < num
            elif op == "≤":
                ok = ok and val <= num
            elif op == ">":
                ok = ok and val > num
            elif op == "≥":
                ok = ok and val >= num
    return ok


class FanEvaluator(BaseEvaluator):
    code = "fan"
    name = "通风机"
    standard_key = "fan"

    def evaluate(self, params: dict) -> dict:
        ftype = str(params.get("type") or "离心").strip()
        pF = to_float(params.get("pressure_pa"))
        flow = to_float(params.get("flow_m3h"))
        n = to_float(params.get("speed_rpm"))
        no = to_float(params.get("no"))
        rho = to_float(params.get("density")) or 1.2
        k = to_float(params.get("isentropic_k")) or 1.4
        psg2 = to_float(params.get("outlet_pa"))
        eff = to_float(params.get("efficiency_pct"))
        if eff is None:
            return {"result": CANNOT_JUDGE, "note": "缺少实测效率（铭牌通常无，须检测报告）"}
        if pF is None or flow is None or n is None or no is None:
            return {"result": CANNOT_JUDGE, "note": "缺少压力/流量/转速/机号"}
        # 压力分类校验
        if pF > 30000:
            return {"result": "不在范围", "note": f"全压{pF}Pa>30kPa，属鼓风机/压缩机，不在GB 19761范围"}

        # 选表
        tables = self.standard["tables"]
        # 类型缺省推断：有轮毂比→轴流
        if not ftype and params.get("hub_ratio") is not None:
            ftype = "轴流"
        if "轴流" in ftype:
            t = next((t for t in tables if t["type"] == "轴流"), None)
            if t is None:
                return {"result": CANNOT_JUDGE, "note": "轴流风机表缺失"}
            # 轮毂比γ（参数）
            gamma = to_float(params.get("hub_ratio"))
            if gamma is None:
                return {"result": CANNOT_JUDGE, "note": "轴流风机缺少轮毂比γ"}
            row = next((r for r in t["rows"] if _in_range(gamma, r["psi"])), None)
            if row is None:
                return {"result": CANNOT_JUDGE, "note": f"轮毂比γ={gamma}不在标准区间"}
            return self._judge_cols(t, row, no, eff, f"GB 19761-2020 表3 轴流")
        if "外转子" in ftype:
            t = next((t for t in tables if t["type"] == "外转子"), None)
            u = math.pi * no * 0.1 * n / 60
            psi = pF / (rho * u * u)
            row = next((r for r in t["rows"] if _in_range(psi, r["psi"]) and _in_range(self._ns(pF, flow, n, rho, 1.0), r["ns"])), None)
            if row is None:
                return {"result": CANNOT_JUDGE, "note": f"ψ={psi:.3f}或ns不在标准区间"}
            return self._judge_cols(t, row, no, eff, "GB 19761-2020 表4 外转子")
        # 离心
        t = None
        for cand in tables:
            if cand["type"] == "离心":
                for row in cand["rows"]:
                    psi_ok = _in_range(self._psi(pF, psg2, k, rho, n, no), row["psi"])
                    if psi_ok:
                        t = cand
                        break
                if t:
                    break
        if t is None:
            return {"result": CANNOT_JUDGE, "note": "压力系数ψ不在任何表区间（0.25~1.55）"}
        kp = _kp(pF, psg2, k) if psg2 else 1.0
        psi = self._psi(pF, psg2, k, rho, n, no)
        ns = self._ns(pF, flow, n, rho, kp)
        row = None
        for r in t["rows"]:
            if _in_range(psi, r["psi"]) and _in_range(ns, r["ns"]):
                row = r
                break
        if row is None:
            return {"result": CANNOT_JUDGE, "note": f"ψ={psi:.3f}或ns={ns:.1f}无匹配行"}
        res = self._judge_cols(t, row, no, eff, f"GB 19761-2020 {t['title'][:16]}")
        res["psi"] = round(psi, 3)
        res["ns"] = round(ns, 1)
        return res

    def _psi(self, pF, psg2, k, rho, n, no):
        u = math.pi * no * 0.1 * n / 60
        kp = _kp(pF, psg2, k) if psg2 else 1.0
        return pF * kp / (rho * u * u)

    @staticmethod
    def _ns(pF, flow, n, rho, kp):
        """风机比转速（V1.11验证公式）：5.54n√(Q/3600)/(1.2×pF×kp/ρ)^0.75"""
        q_s = flow / 3600.0
        if q_s <= 0:
            return 0
        return 5.54 * n * math.sqrt(q_s) / (1.2 * pF * kp / rho) ** 0.75

    def _judge_cols(self, t, row, no, eff, basis):
        """按机号区间取列，返回等级"""
        vals = row["eff"]
        col = None
        for i, nr in enumerate(t["no_ranges"]):
            if _in_range(no, nr["no"]):
                col = i
                break
        if col is None:
            return {"result": CANNOT_JUDGE, "note": f"机号No{no}不在标准区间"}
        l1 = vals[col * 3 + 2]
        l2 = vals[col * 3 + 1]
        l3 = vals[col * 3]
        result = NOT_MEET_3
        for lv, lim in (("1", l1), ("2", l2), ("3", l3)):
            if lim is not None and eff >= lim:
                result = lv + "级"
                break
        return {"level1": l1, "level2": l2, "level3": l3, "result": result, "basis": basis,
                "note": "" if result != CANNOT_JUDGE else ""}
