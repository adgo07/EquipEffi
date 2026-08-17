# -*- coding: utf-8 -*-
"""core/summary.py - 汇总统计（模块C）
对判定结果做数量/容量统计 + 问题/无法判定清单。
"""
from collections import Counter


def build_summary(results: dict, sheet_names: dict = None) -> dict:
    """results: {key: [{params, issues, row, name, result_dict}]}
    返回汇总数据：统计表 + 问题清单"""
    stats = []      # 每类设备一行
    problems = []   # 问题清单
    total = Counter()
    for key, items in results.items():
        level_cnt = Counter()
        cap_sum = 0.0
        cap_key = ""
        for item in items:
            rd = item["result_dict"]
            result = rd.get("result", "")
            level_cnt[result] += 1
            total[result] += 1
            # 容量统计（取该设备类型的容量字段）
            cap_val, ck = _capacity(key, item["params"])
            if cap_val:
                cap_sum += cap_val
                cap_key = ck
            # 问题记录
            for issue in item.get("issues", []):
                problems.append({"key": key, "row": item["row"], "name": item["name"], "issue": issue})
            if rd.get("note"):
                problems.append({"key": key, "row": item["row"], "name": item["name"],
                                 "issue": f"判定备注: {rd['note']}"})
            if result in ("无法判定", "不在范围", "未辨识"):
                problems.append({"key": key, "row": item["row"], "name": item["name"],
                                 "issue": f"判定结果[{result}]，需人工复核"})
        stats.append({
            "key": key, "count": len(items),
            "levels": dict(level_cnt),
            "capacity_sum": round(cap_sum, 1) if cap_sum else None,
            "capacity_unit": cap_key,
        })
    return {"stats": stats, "problems": problems, "total": dict(total)}


def _capacity(key, params):
    """各类设备的容量字段"""
    mapping = {
        "transformer": ("capacity_kva", "kVA"),
        "motor_lv": ("power_kw", "kW"),
        "motor_hv": ("power_kw", "kW"),
        "motor_pmsm": ("power_kw", "kW"),
        "compressor": ("power_kw", "kW"),
        "pump_water": ("power_kw", "kW"),
        "pump_chem": ("power_kw", "kW"),
        "fan": ("power_kw", "kW"),
        "blower": ("power_kw", "kW"),
        "submersible": ("power_kw", "kW"),
        "boiler": ("capacity", "t/h或MW"),
        "heat_treatment": ("weight_t", "t"),
    }
    f, unit = mapping.get(key, (None, ""))
    if f:
        v = params.get(f)
        if v:
            return v, unit
    return None, ""
