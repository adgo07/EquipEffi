# -*- coding: utf-8 -*-
"""devices/transformer.py - 变压器判定（GB 20052-2024）
多条件查表 + 容量线性插值 + 双指标（空载/负载损耗同时达标）
"""
from .base import BaseEvaluator, to_float, interp, match_rows, LEVEL_1, LEVEL_2, LEVEL_3, NOT_MEET_3, CANNOT_JUDGE


def _norm(s):
    """类别文本归一化：小写+去空格（企业常写10KV，标准是10kV）"""
    return str(s).lower().replace(" ", "").replace("　", "")


class TransformerEvaluator(BaseEvaluator):
    code = "transformer"
    name = "变压器"
    standard_key = "transformer"

    def evaluate(self, params: dict) -> dict:
        category = str(params.get("category") or "").strip()
        capacity = to_float(params.get("capacity_kva"))
        material = str(params.get("core_material") or "").strip()
        insulation = str(params.get("insulation") or "").strip()
        connection = str(params.get("connection") or "").strip()
        p0 = to_float(params.get("no_load_loss_w"))  # W
        pk = to_float(params.get("load_loss_w"))      # W

        if not category or capacity is None:
            return {"result": CANNOT_JUDGE, "note": "缺少变压器类别或额定容量"}
        if p0 is None or pk is None:
            return {"result": CANNOT_JUDGE, "note": "缺少空载损耗或负载损耗实测值"}

        # 类别匹配：归一化（小写+去空格）后模糊匹配，多候选取文本最接近
        cat_n = _norm(category)
        cand = []
        for r in self.standard["rows"]:
            rc = _norm(r["category"])
            if rc and (rc in cat_n or cat_n in rc):
                cand.append(r)
        if not cand:
            return {"result": CANNOT_JUDGE, "note": f"未找到类别[{category}]的标准表"}
        cand.sort(key=lambda r: abs(len(_norm(r["category"])) - len(cat_n)))
        rows = cand[:1]  # 只取文本最接近的类别（避免配电/新能源等多候选干扰）

        # 维度自适应：材质/连接组/绝缘仅在该表内区分时才参与匹配
        mats = {r["core_material"] for r in rows if r["core_material"]}
        conns = {r["connection"] for r in rows if r["connection"]}
        rows2 = rows
        if len(mats) > 1 and material:
            rows2 = match_rows(rows2, core_material=material)
        if len(conns) > 1 and connection:
            rows2 = match_rows(rows2, connection=connection)
        if not rows2:
            return {"result": CANNOT_JUDGE, "note": f"类别[{category}]匹配材质[{material}]/连接组[{connection}]无结果"}

        # 容量档位（插值）
        caps = sorted({r["capacity_kva"] for r in rows2 if r["capacity_kva"]})
        lo, hi = self._bracket(caps, capacity)
        cand_lo = [r for r in rows2 if r["capacity_kva"] == lo] if lo is not None else []
        cand_hi = [r for r in rows2 if r["capacity_kva"] == hi] if hi is not None else []
        if lo == hi:
            row = cand_lo[0]
            nl = row["no_load_kw"]; lk = row["load_kw"]
        else:
            if not cand_lo or not cand_hi:
                return {"result": CANNOT_JUDGE, "note": f"容量{capacity}kVA超出标准范围"}
            # 插值（空载/负载分别插值）
            nl = []
            lk = []
            for i in range(3):
                nl.append(interp(capacity, lo, hi, cand_lo[0]["no_load_kw"][i], cand_hi[0]["no_load_kw"][i]))
                lk.append(interp(capacity, lo, hi, cand_lo[0]["load_kw"][i], cand_hi[0]["load_kw"][i]))

        p0kw, pkkw = p0 / 1000.0, pk / 1000.0
        # 双指标：取同时满足的最优等级
        result = NOT_MEET_3
        for lv, i in (("1", 0), ("2", 1), ("3", 2)):
            if nl[i] is not None and lk[i] is not None and p0kw <= nl[i] and pkkw <= lk[i]:
                result = lv + "级"
                break
        return {
            "level1": (nl[0], lk[0]) if nl[0] is not None else None,
            "level2": (nl[1], lk[1]) if nl[1] is not None else None,
            "level3": (nl[2], lk[2]) if nl[2] is not None else None,
            "no_load_levels": [round(v, 3) if v is not None else None for v in nl],
            "load_levels": [round(v, 3) if v is not None else None for v in lk],
            "result": result,
            "basis": f"GB 20052-2024 {category}",
            "note": "双指标：空载+负载损耗同时达标" if result != CANNOT_JUDGE else "",
        }

    @staticmethod
    def _bracket(vals, x):
        if x <= vals[0]:
            return vals[0], vals[0]
        if x >= vals[-1]:
            return vals[-1], vals[-1]
        for i in range(len(vals) - 1):
            if vals[i] <= x <= vals[i + 1]:
                return vals[i], vals[i + 1] if x != vals[i] else vals[i]
        return None, None
