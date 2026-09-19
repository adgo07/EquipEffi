# -*- coding: utf-8 -*-
"""tools/build_review_sheets.py - 生成全部12类设备的标准数据校对表
校对表是给专家对照标准PDF核对用的（红色=可疑值）
用法: python tools/build_review_sheets.py
输出: standards/校对表_全部设备_<日期>.xlsx
"""
import json
import re
import warnings
from datetime import date
from pathlib import Path

import openpyxl

warnings.filterwarnings("ignore")

STD_DIR = Path(__file__).resolve().parent.parent / "standards"

RED = openpyxl.styles.Font(color="FF0000", bold=True)


def _warn_red(ws, row_idx, cols):
    for c in cols:
        ws.cell(row_idx, c).font = RED


def sheet_transformer(ws, data):
    ws.append(["表", "类别", "容量kVA", "铁芯材质", "绝缘等级", "连接组标号",
               "1级空载kW", "2级空载kW", "3级空载kW", "1级负载kW", "2级负载kW", "3级负载kW", "校对", "备注"])
    prev = None
    for r in data["rows"]:
        ws.append([r["table"], r["category"], r["capacity_kva"], r["core_material"],
                   r["insulation"], r["connection"], *r["no_load_kw"], *r["load_kw"], "待校对", ""])
        if r["suspicious"]:
            _warn_red(ws, ws.max_row, range(7, 13))


def sheet_motor_lv(ws, data):
    ws.append(["功率kW", "2极1", "2极2", "2极3", "4极1", "4极2", "4极3",
               "6极1", "6极2", "6极3", "8极1", "8极2", "8极3", "校对", "备注"])
    for r in data["rows"]:
        e = [r["efficiency"].get(lv, {}).get(str(idx)) for lv in ("1", "2", "3") for idx in range(4)]
        ws.append([r["power_kw"], e[0], e[4], e[8], e[1], e[5], e[9],
                   e[2], e[6], e[10], e[3], e[7], e[11], "待校对", ""])


def sheet_motor(ws, data, label):
    """高压电机/永磁：每行对应一个功率×极数/转速维度。"""
    ws.append(["表", "极数/转速", "功率kW", "1级", "2级", "3级", "校对", "备注"])
    for t in data["tables"]:
        for r in t["rows"]:
            for i, dim in enumerate(t["dims"]):
                if isinstance(dim, list):
                    dim_txt = dim[0]
                else:
                    dim_txt = dim
                vals = [r["efficiency"].get(lv, {}).get(str(i)) for lv in ("1", "2", "3")]
                ws.append([t["title"], dim_txt, r["power_kw"], *vals, "待校对", ""])


def sheet_compressor(ws, data):
    ws.append(["表", "类型", "功率kW", "等级", "压力MPa", "冷却", "比功率", "校对", "备注"])
    prev = None
    for r in data["rows"]:
        ws.append([r["table"], r["type"], r["power_kw"], r["level"], r["pressure_mpa"],
                   r["cooling"], r["specific_power"] if r["specific_power"] is not None else "—", "待校对", ""])
        v = r["specific_power"]
        if prev and prev["t"] == r["table"] and prev["p"] == r["pressure_mpa"] \
                and prev["c"] == r["cooling"] and prev["l"] == r["level"] and prev["v"] and v:
            if abs(1 - v / prev["v"]) > 0.25:
                _warn_red(ws, ws.max_row, [7])
        prev = {"t": r["table"], "p": r["pressure_mpa"], "c": r["cooling"], "l": r["level"], "v": v}


def sheet_pump(ws, data):
    ws.append(["类型", "流量范围m³/h", "C1", "C2", "C3", "校对", "备注"])
    for r in data["water"]["ci"]:
        ws.append([r["type"], f"{r['q_min']}~{r['q_max']}", *r["ci"], "待校对", ""])
    ws.append([])
    ws.append(["化工泵判定表（泵类型/流量/ns → 偏移）", "", "", "", "", "", ""])
    ws.append(["泵", "Q范围", "ns范围", "η0", "1级偏移", "2级偏移", "3级偏移", "校对"])
    for r in data["chemical"]["level_offsets"]:
        ws.append([r["pump"], f"{r['q_min']}~{r['q_max']}", f"{r['ns_min']}~{r['ns_max']}",
                   "ηb-Δη" if r["eta0_uses_delta"] else "ηb", *r["offsets"], "待校对"])


def sheet_fan(ws, data):
    ws.append(["表", "ψ/γ区间", "ns区间", "机号区间", "3级", "2级", "1级", "校对", "备注"])
    for t in data["tables"]:
        for r in t["rows"]:
            for i, nr in enumerate(t["no_ranges"]):
                e = r["eff"]
                if i * 3 + 2 < len(e):
                    ws.append([t["title"][:14], r["psi"], r["ns"], nr["no"],
                               e[i * 3], e[i * 3 + 1], e[i * 3 + 2], "待校对", ""])


def _safe_off(t, lv, bi, si):
    """安全取值：offsets[lv][bi][si]（部分表等级/行可能缺失）"""
    offs = t["offsets"].get(lv)
    if not offs or bi >= len(offs) or offs[bi] is None or si >= len(offs[bi]):
        return None
    return offs[bi][si]


def sheet_submersible(ws, data):
    ws.append(["表", "型式", "功率档", "1级偏移", "2级偏移", "3级", "校对"])
    for t in data["tables"]:
        for bi, (lo, hi) in enumerate(t["power_bins"]):
            for si, st in enumerate(t["subtypes"]):
                o1 = _safe_off(t, "1", bi, si)
                o2 = _safe_off(t, "2", bi, si)
                ws.append([t["name"], st, f"{lo}<P≤{hi}", o1, o2, "ηDB-Δη", "待校对"])


def sheet_boiler(ws, data):
    ws.append(["表", "燃料", "类别", "发热量条件", "挥发分条件", "容量档", "1级", "2级", "3级", "校对"])
    for t in data["tables"]:
        for r in t["rows"]:
            for i, cap in enumerate(t["capacity_cols"] or [""]):
                ws.append([t["name"], r["fuel"], r["class"], r["q_cond"], r["v_cond"],
                           cap, *r["eff"][i], "待校对"])


def sheet_heat(ws, data):
    ws.append(["炉型", "规格", "单位", "一等", "二等", "三等", "校对", "备注"])
    for r in data["table8"]:
        ws.append([r["furnace"], r["spec"], r["unit"], *r["level"], "待校对", ""])


def sheet_blower(ws, data):
    ws.append(["表", "类型", "b2/D2", "级数", "<300", "301~400", "401~600", "601~800", ">801", "校对"])
    for t in data["tables"]:
        for r in t["rows"]:
            ws.append([t["name"], f"{t['type']}-{t['kind']}", r["b2_d2"], r["stages"] or "", *r["eff"], "待校对"])


BUILDERS = {
    "transformer": sheet_transformer,
    "motor_lv": sheet_motor_lv,
    "motor_hv": lambda ws, d: sheet_motor(ws, d, "高压电机"),
    "compressor": sheet_compressor,
    "pump": sheet_pump,
    "fan": sheet_fan,
    "submersible": sheet_submersible,
    "boiler": sheet_boiler,
    "heat_treatment": sheet_heat,
    "blower": sheet_blower,
}

FILES = ["transformer.json", "motor_lv.json", "motor_hv.json",
         "compressor.json", "pump.json", "fan.json", "submersible.json",
         "boiler.json", "heat_treatment.json", "blower.json"]

NAME = {
    "transformer": "变压器", "motor_lv": "低压电机", "motor_hv": "高压电机",
    "compressor": "空压机", "pump": "泵_清水化工",
    "fan": "通风机", "submersible": "潜水电泵", "boiler": "锅炉",
    "heat_treatment": "热处理", "blower": "鼓风机",
}


def main():
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for f in FILES:
        key = f.replace(".json", "")
        data = json.loads((STD_DIR / f).read_text(encoding="utf-8"))
        ws = wb.create_sheet(NAME.get(key, key)[:28])
        BUILDERS[key](ws, data)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
    out = STD_DIR / f"校对表_全部设备_{date.today().strftime('%Y%m%d')}.xlsx"
    wb.save(out)
    print(f"✅ 校对表已生成: {out}")


if __name__ == "__main__":
    main()
