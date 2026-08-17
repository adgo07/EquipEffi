# -*- coding: utf-8 -*-
"""devices/blower.py - 鼓风机判定（GB 28381-2012）
多变效率计算：ηpol=(1/(k/(k-1)))×ln(P2/P1)/ln(T2/T1)（V1.11公式验证）
表选择：单级/多级×低速/高速 → b2/D2×级数×叶轮直径查多变效率限值
判定：实测≥评价值→节能评价值；≥限定值→达标；否则未达标
"""
import math
from .base import BaseEvaluator, to_float, CANNOT_JUDGE, NOT_MEET_3, PASS, NOT_PASS, ENERGY_SAVING


def _in_range(val, rng):
    s = str(rng).strip()
    if not s:
        return True
    import re
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)]
    if not nums:
        return True
    if "~" in s and len(nums) == 2:
        return nums[0] <= val <= nums[1]
    if "<" in s:
        return val < nums[-1]
    if ">" in s:
        return val > nums[0]
    if "≤" in s and len(nums) == 1:
        return val <= nums[0]
    if "≥" in s and len(nums) == 1:
        return val >= nums[0]
    return True


class BlowerEvaluator(BaseEvaluator):
    code = "blower"
    name = "鼓风机"
    standard_key = "blower"

    def evaluate(self, params: dict) -> dict:
        ftype = str(params.get("type") or "").strip()  # 如 多级低速离心鼓风机
        b2 = to_float(params.get("b2_mm"))
        d2 = to_float(params.get("d2_mm"))
        stages = params.get("stages")  # 离心级数
        p1 = to_float(params.get("p1_kpa"))
        p2 = to_float(params.get("p2_kpa"))
        t1 = to_float(params.get("t1_k"))
        t2 = to_float(params.get("t2_k"))
        k = to_float(params.get("k")) or 1.4
        eff = to_float(params.get("efficiency_pct"))  # 实测多变效率（若有）
        # 多变效率计算（V1.11公式）
        eta_pol = None
        if p1 and p2 and t1 and t2 and p2 > p1 and t2 > t1:
            eta_pol = (1 / (k / (k - 1))) * (math.log(p2 / p1) / math.log(t2 / t1))
        if eff is not None:
            eta_pol = eff  # 实测优先
        if eta_pol is None:
            return {"result": CANNOT_JUDGE, "note": "缺少多变效率（计算或实测）"}
        if b2 is None or d2 is None or d2 <= 0:
            return {"result": CANNOT_JUDGE, "note": "缺少叶轮出口宽度b2/直径D2"}
        b2d2 = b2 / d2
        # 表选择
        kind = "限定值"
        tables = self.standard["tables"]
        is_multi = "多级" in ftype
        is_high = "高速" in ftype
        t_limit = None
        t_save = None
        for t in tables:
            t_multi = "多级" in t["type"]
            t_high = "高速" in t["type"]
            if t_multi == is_multi and t_high == is_high:
                if t["kind"] == "限定值":
                    t_limit = t
                else:
                    t_save = t
        if t_limit is None:
            return {"result": CANNOT_JUDGE, "note": f"未匹配鼓风机类型[{ftype}]"}
        # 行匹配
        row_lim = self._match_row(t_limit, b2d2, stages)
        if row_lim is None:
            return {"result": CANNOT_JUDGE, "note": f"b2/D2={b2d2:.3f}或级数不在标准范围"}
        lim = self._col_val(t_limit, row_lim, d2)
        save = None
        if t_save is not None:
            row_save = self._match_row(t_save, b2d2, stages)
            if row_save is not None:
                save = self._col_val(t_save, row_save, d2)
        result = NOT_PASS
        if save is not None and eta_pol * 100 >= save:
            result = ENERGY_SAVING
        elif lim is not None and eta_pol * 100 >= lim:
            result = PASS
        return {"level1": save, "level2": lim, "level3": None, "result": result,
                "basis": f"GB 28381-2012 {t_limit['name']}",
                "note": f"ηpol={eta_pol*100:.1f}%；限定值{lim}%；评价值{save}%"}

    @staticmethod
    def _match_row(t, b2d2, stages):
        for r in t["rows"]:
            if not _in_range(b2d2, r["b2_d2"]):
                continue
            if t["has_stages"] and stages is not None:
                if not _in_range(float(stages), r["stages"] or ""):
                    continue
            return r
        return None

    @staticmethod
    def _col_val(t, row, d2):
        for i, rng in enumerate(t["d2_ranges"]):
            if _in_range(d2, rng):
                return row["eff"][i]
        return None
