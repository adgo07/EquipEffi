# -*- coding: utf-8 -*-
"""devices/boiler.py - 工业锅炉判定（GB 24500-2020）
燃料(品种+类别)×容量档→热效率限值；实测热效率≥限值
层燃/流化床需燃料品种+发热量（挥发分缺省忽略）；室燃按品种+冷凝
"""
from .base import BaseEvaluator, to_float, CANNOT_JUDGE, NOT_MEET_3


class BoilerEvaluator(BaseEvaluator):
    code = "boiler"
    name = "工业锅炉"
    standard_key = "boiler"

    def evaluate(self, params: dict) -> dict:
        btype = str(params.get("boiler_type") or "").strip()   # 层状燃烧/流化床/生物质/室燃
        fuel = str(params.get("fuel") or "").strip()           # 烟煤/贫煤/无烟煤/褐煤/天然气/燃油/煤/生物质
        condensing = params.get("condensing")                  # 是否冷凝
        capacity = to_float(params.get("capacity"))            # 蒸发量t/h或热功率MW
        q = to_float(params.get("heat_value"))                 # 低位发热量kJ/kg
        eff = to_float(params.get("efficiency_pct"))
        if eff is None:
            return {"result": CANNOT_JUDGE, "note": "缺少实测热效率（须能效检测报告）"}
        # 表选择
        table = None
        if "层" in btype or "层状" in btype:
            table = next((t for t in self.standard["tables"] if t["name"] == "表1"), None)
            kind_key = "表1"
        elif "流化" in btype:
            table = next((t for t in self.standard["tables"] if t["name"] == "表2"), None)
            kind_key = "表2"
        elif "生物质" in btype or "生物" in fuel:
            table = next((t for t in self.standard["tables"] if t["name"] == "表3"), None)
            kind_key = "表3"
        elif "室燃" in btype or fuel:
            table = next((t for t in self.standard["tables"] if t["name"] == "表4"), None)
            kind_key = "表4"
        if table is None:
            return {"result": CANNOT_JUDGE, "note": f"未匹配锅炉类型[{btype}]"}
        # 行匹配
        row = None
        if kind_key == "表4":
            for r in table["rows"]:
                if r["fuel"] in fuel or fuel in r["fuel"]:
                    if r["class"] == "冷凝" and str(condensing) not in ("1", "true", "True", "是"):
                        continue
                    if r["class"] == "非冷凝" and str(condensing) in ("1", "true", "True", "是"):
                        continue
                    row = r
                    break
        else:
            for r in table["rows"]:
                if fuel in r["fuel"] or r["fuel"] in fuel:
                    # 发热量条件（Q区间）
                    if q is not None and r["q_cond"] and "≤" in r["q_cond"]:
                        import re
                        nums = [float(x) for x in re.findall(r"\d+", r["q_cond"])]
                        if len(nums) == 2 and not (nums[0] <= q <= nums[1]):
                            continue
                        if len(nums) == 1 and "≥" in r["q_cond"] and q < nums[0]:
                            continue
                    row = r
                    break
        if row is None:
            return {"result": CANNOT_JUDGE, "note": f"燃料[{fuel}]发热量[{q}]无匹配行"}
        # 容量档
        levels = row["eff"]
        if len(levels) > 1:
            cap_hi = 20 if kind_key == "表1" else 10
            idx = 0 if (capacity is None or capacity <= cap_hi) else 1
        else:
            idx = 0
        l1, l2, l3 = levels[idx]
        result = NOT_MEET_3
        for lv, lim in (("1", l1), ("2", l2), ("3", l3)):
            if eff >= lim:
                result = lv + "级"
                break
        return {"level1": l1, "level2": l2, "level3": l3, "result": result,
                "basis": f"GB 24500-2020 {kind_key}",
                "note": "热效率须来自能效检测报告" if result != CANNOT_JUDGE else ""}
