# -*- coding: utf-8 -*-
"""devices/compressor.py - 空压机判定（GB 19153-2019）
表选择：型式(喷油回转/往复活塞/全无油) + 变/定频 → 功率靠档 + 压力靠档 + 冷却 → 比功率限值
比功率越小越好。功率/压力不在档位时按标准"向上靠档"处理。
"""
from .base import BaseEvaluator, to_float, CANNOT_JUDGE, NOT_MEET_3, LEVEL_1, LEVEL_2, LEVEL_3


def _pick_comp_table(tables, ftype, variable):
    """选表：表1工频喷油回转 / 表2变转速喷油回转 / 表3往复活塞 / 表4全无油"""
    ft = str(ftype or "")
    var = str(variable or "")
    is_var = "变频" in var or "变" in var and "不变" not in var
    for t in tables:
        name = t["name"] if "name" in t else t["table"]
        ttype = t["type"]
        if "喷油回转" in ttype:
            if is_var and "变转速" in ttype:
                return t
            if not is_var and "变转速" not in ttype:
                return t
        elif "往复活塞" in ttype and "无油" not in ttype and "全无油" not in ttype:
            return t
        elif "无油" in ttype or "全无油" in ttype:
            if "无油" in ft or "全无油" in ft:
                return t
    return None


class CompressorEvaluator(BaseEvaluator):
    code = "compressor"
    name = "空压机"
    standard_key = "compressor"

    def evaluate(self, params: dict) -> dict:
        ftype = params.get("type")
        power = to_float(params.get("power_kw"))
        pressure = to_float(params.get("pressure_mpa"))
        cooling = str(params.get("cooling") or "").strip()
        variable = params.get("variable")
        sp = to_float(params.get("specific_power"))
        if sp is None:
            return {"result": CANNOT_JUDGE, "note": "缺少机组比功率实测值（须为机组输入功率÷排气量）"}
        if power is None or pressure is None:
            return {"result": CANNOT_JUDGE, "note": "缺少额定功率或排气压力"}
        t = _pick_comp_table(self.standard["tables"], ftype, variable)
        if t is None:
            return {"result": CANNOT_JUDGE, "note": f"未匹配空压机类型[{ftype}]变频[{variable}]"}
        # 冷却标准化
        if "液" in cooling or "水" in cooling:
            cooling_n = "液冷"
        else:
            cooling_n = "风冷"
        # 功率靠档（向上取整档）
        powers = sorted({r["power_kw"] for r in t["rows"] if r["power_kw"]})
        p_pick = next((p for p in powers if p >= power), powers[-1])
        # 压力靠档
        presses = sorted({r["pressure_mpa"] for r in t["rows"] if r["pressure_mpa"]})
        pr_pick = next((p for p in presses if p >= pressure), presses[-1])
        # 查1/2/3级比功率
        lv = {}
        for lv_i in (1, 2, 3):
            rows = [r for r in t["rows"] if r["power_kw"] == p_pick and r["level"] == lv_i
                    and r["pressure_mpa"] == pr_pick and r["cooling"] == cooling_n]
            lv[str(lv_i)] = rows[0]["specific_power"] if rows else None
        result = NOT_MEET_3
        for lv_i in ("1", "2", "3"):
            if lv[lv_i] is not None and sp <= lv[lv_i]:
                result = lv_i + "级"
                break
        note = ""
        if p_pick != power:
            note += f"功率{power}kW按标准向上靠档至{p_pick}kW；"
        if pr_pick != pressure:
            note += f"排气压力{pressure}MPa靠档至{pr_pick}MPa；"
        return {"level1": lv["1"], "level2": lv["2"], "level3": lv["3"], "result": result,
                "basis": f"GB 19153-2019 {t['type']}", "note": note}
