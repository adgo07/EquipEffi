# -*- coding: utf-8 -*-
"""devices/heat_treatment.py - 热处理设备判定（GB/T 36561-2018，推荐性标准）
可比单耗：电炉bk=W(kWh)/Gz(t)；燃料炉bk=燃料耗量×热值×折标系数/Gz（kgce/t）
炉型+规格匹配表8 → 一等/二等/三等
"""
from .base import BaseEvaluator, to_float, CANNOT_JUDGE


class HeatTreatmentEvaluator(BaseEvaluator):
    code = "heat_treatment"
    name = "热处理设备"
    standard_key = "heat_treatment"

    def evaluate(self, params: dict) -> dict:
        furnace = str(params.get("furnace") or "").strip()   # 炉型
        spec = str(params.get("spec") or "").strip()         # 规格条件
        is_fuel = str(params.get("heating") or "")           # 电/燃料
        weight = to_float(params.get("weight_t"))            # 总折合重量t
        elec_kwh = to_float(params.get("elec_kwh"))          # 电炉耗电量kWh
        fuel_m3 = to_float(params.get("fuel_m3"))            # 燃料耗量m³
        fuel_hv = to_float(params.get("fuel_hv"))            # 燃料热值kJ/m³
        fuel_coef = to_float(params.get("fuel_coef")) or 1.0  # 燃料系数
        # 计算可比单耗
        bk = None
        unit = "kWh/t"
        if "燃料" in is_fuel or (fuel_m3 and fuel_hv):
            if weight and weight > 0 and fuel_m3 and fuel_hv:
                # kgce/t：燃料耗量×热值×系数/29307/重量（1kgce=29307kJ）
                bk = fuel_m3 * fuel_hv * fuel_coef / 29307.0 / weight
                unit = "kgce/t"
            else:
                return {"result": CANNOT_JUDGE, "note": "燃料炉缺少燃料耗量/热值/重量"}
        else:
            if weight and weight > 0 and elec_kwh is not None:
                bk = elec_kwh / weight
            else:
                return {"result": CANNOT_JUDGE, "note": "电炉缺少耗电量或总折合重量"}
        if bk is None:
            return {"result": CANNOT_JUDGE, "note": "可比单耗计算失败"}
        # 表8匹配
        row = None
        for r in self.standard["table8"]:
            if r["furnace"] in furnace or furnace in r["furnace"]:
                if r["unit"] == unit:
                    row = r
                    break
        if row is None:
            return {"result": CANNOT_JUDGE, "note": f"炉型[{furnace}]/单位[{unit}]无匹配行"}
        l1, l2, l3 = row["level"]
        if bk <= l1:
            result = "一等"
        elif bk <= l2:
            result = "二等"
        elif bk <= l3:
            result = "三等"
        else:
            result = "未达三等"
        return {"level1": l1, "level2": l2, "level3": l3, "result": result,
                "basis": "GB/T 36561-2018 表8（推荐性标准）",
                "note": f"可比单耗={bk:.1f}{unit}；一等≤{l1}，二等≤{l2}，三等≤{l3}"}
