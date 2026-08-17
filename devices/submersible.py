# -*- coding: utf-8 -*-
"""devices/submersible.py - 潜水电泵判定（GB 32030-2022）
表选择：小型/大中型/污水污物/井用/混流 → 型式×功率档 → 偏移量
各级限值=ηDB+偏移（1/2级）或ηDB-Δη（3级）；实测效率≥限值
"""
from .base import BaseEvaluator, to_float, CANNOT_JUDGE, NOT_MEET_3


class SubmersibleEvaluator(BaseEvaluator):
    code = "submersible"
    name = "潜水电泵"
    standard_key = "submersible"

    def evaluate(self, params: dict) -> dict:
        table_type = str(params.get("table_type") or "").strip()  # 小型/大中型/污水污物/井用/混流
        subtype = str(params.get("subtype") or "").strip()        # 如 QDX/离心式/旋流式/充水式/蜗壳式
        power = to_float(params.get("power_kw"))
        eta_db = to_float(params.get("eta_db"))      # 电泵规定效率
        delta = to_float(params.get("delta_eta")) or 0.0  # 容差
        eff = to_float(params.get("efficiency_pct"))
        if power is None or eta_db is None:
            return {"result": CANNOT_JUDGE, "note": "缺少额定功率或电泵规定效率ηDB"}
        if eff is None:
            return {"result": CANNOT_JUDGE, "note": "缺少实测效率"}
        t = None
        for cand in self.standard["tables"]:
            if table_type in cand["type"] or cand["type"] in table_type:
                t = cand
                break
        if t is None:
            return {"result": CANNOT_JUDGE, "note": f"未匹配潜水电泵类型[{table_type}]"}
        # 功率档
        bin_idx = None
        for i, (lo, hi) in enumerate(t["power_bins"]):
            if lo <= power <= hi:
                bin_idx = i
                break
        if bin_idx is None:
            return {"result": CANNOT_JUDGE, "note": f"功率{power}kW不在标准分档"}
        # 型式
        sub_idx = None
        for i, st in enumerate(t["subtypes"]):
            if st in subtype or subtype in st:
                sub_idx = i
                break
        if sub_idx is None:
            return {"result": CANNOT_JUDGE, "note": f"型式[{subtype}]不在标准列表{t['subtypes']}"}
        lv = {}
        for lv_i in ("1", "2", "3"):
            off = t["offsets"][lv_i]
            if off is None:
                lv[lv_i] = eta_db - delta
                continue
            v = off[bin_idx][sub_idx]
            if v is None:
                lv[lv_i] = None
            else:
                lv[lv_i] = eta_db + v
        result = NOT_MEET_3
        for lv_i in ("1", "2", "3"):
            if lv[lv_i] is not None and eff >= lv[lv_i]:
                result = lv_i + "级"
                break
        return {"level1": lv["1"], "level2": lv["2"], "level3": lv["3"], "result": result,
                "basis": f"GB 32030-2022 {t['name']}",
                "note": f"ηDB={eta_db}%，Δη={delta}%" if result != CANNOT_JUDGE else ""}
