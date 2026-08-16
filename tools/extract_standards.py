# -*- coding: utf-8 -*-
"""
tools/extract_standards.py - 标准数据提取（V1.11标准sheet → JSON + 校对表Excel）

第一批：变压器、低压电动机、空压机、清水泵/化工泵（GB 19762公式系数单独处理）

用法：
    python tools/extract_standards.py [设备key...]    # 缺省=全部第一批

输出：
    standards/<key>.json          工具运行数据源（机器格式）
    standards/校对表_<日期>.xlsx  人工校对用（王玮只碰这个）
"""
import json
import sys
import warnings
from datetime import date
from pathlib import Path

import openpyxl

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
SRC = r"G:\标准  规范\02_能耗限额_终端产品\用能设备\用能设备能效分析表V1.11.xlsx"
STD_DIR = ROOT / "standards"
STD_DIR.mkdir(exist_ok=True)

# 可疑值判定：同表内相邻行同列数值跳变超过阈值（如相邻容量档损耗比<0.7或>1.5）
JUMP_THRESHOLD = 0.5  # |1 - v2/v1| 超过0.5视为可疑（变压器损耗随容量递增，一般不会减半）


# ============ 变压器 ============
def extract_transformer(wb) -> dict:
    ws = wb["变压器标准"]
    rows = []
    prev_key = None
    prev_vals = None
    for r in ws.iter_rows(min_row=2, max_col=12):
        t, cat, cap, mat, ins, conn = [r[i].value for i in range(6)]
        losses = [r[i].value for i in range(6, 12)]
        if t is None and cat is None and all(v is None for v in losses):
            continue
        # 合并单元格：表格名称/类别可能向下延续（None=沿用上一行）
        if t is None:
            t = prev_key["t"] if prev_key else ""
        if cat is None:
            cat = prev_key["cat"] if prev_key else ""
        if mat is None:
            mat = prev_key["mat"] if prev_key else ""
        if conn is None:
            conn = prev_key["conn"] if prev_key else ""
        # 数值化
        try:
            cap_f = float(cap)
        except (TypeError, ValueError):
            cap_f = None
        loss_f = []
        for v in losses:
            try:
                loss_f.append(float(v))
            except (TypeError, ValueError):
                loss_f.append(None)
        row = {
            "table": str(t).strip() if t else "",
            "category": str(cat).strip() if cat else "",
            "capacity_kva": cap_f,
            "core_material": str(mat).strip() if mat else "",
            "insulation": str(ins).strip() if ins else "",
            "connection": str(conn).strip() if conn else "",
            "no_load_kw": loss_f[0:3],
            "load_kw": loss_f[3:6],
            "suspicious": False,
        }
        # 可疑值检测：与上一行（同表同材质同连接组）比较
        if prev_key and prev_key["t"] == t and prev_key["mat"] == mat and prev_key["conn"] == conn:
            for i in range(6):
                pv, cv = prev_vals[i], loss_f[i]
                if pv and cv and pv > 0:
                    ratio = cv / pv
                    if abs(1 - ratio) > JUMP_THRESHOLD and cap_f and prev_key["cap"]:
                        # 容量档跳变>50%时可解释为正常档差，不做标记；同档突变才可疑
                        cap_ratio = cap_f / prev_key["cap"] if prev_key["cap"] else 1
                        if 0.8 <= cap_ratio <= 1.25:
                            row["suspicious"] = True
        prev_key = {"t": t, "cat": cat, "mat": mat, "conn": conn, "cap": cap_f}
        prev_vals = loss_f
        rows.append(row)
    return {
        "standard_code": "GB 20052-2024",
        "standard_name": "电力变压器能效限定值及能效等级",
        "effective_date": "2025-02-01",
        "unit_note": "损耗单位kW；1级/2级/3级对应数组[no_load_kw]和[load_kw]",
        "rows": rows,
    }


# ============ 低压电动机 ============
def extract_motor_lv(wb) -> dict:
    ws = wb["电动机标准"]
    # 实际结构（A列空，数据从B列起）：
    # R3: [空, 额定功率/kW, 效率%...]
    # R4: [空, 空, 1级, 空, 空, 空, 2级, 空, 空, 空, 3级, ...]
    # R5: [空, 极数, 2, 4, 6, 8, 2, 4, 6, 8, 2, 4, 6, 8]
    # R6+: [空, 0.12, 71.4, 74.3, ...]
    rows = []
    for i, r in enumerate(ws.iter_rows(min_row=3, max_col=14), start=3):
        vals = [c.value for c in r]
        if i == 3:
            continue  # 表头行
        if i == 4:
            levels = vals
            continue
        if i == 5:
            poles = vals
            continue
        power = vals[1]  # B列
        if power is None:
            continue
        try:
            power_f = float(power)
        except (TypeError, ValueError):
            continue
        eff = []
        for j in range(2, 14):
            v = vals[j]
            if v in (None, "", "—", "-"):
                eff.append(None)
            else:
                try:
                    eff.append(float(v))
                except (TypeError, ValueError):
                    eff.append(None)
        rows.append({
            "power_kw": power_f,
            "poles": [str(p).strip() for p in poles[2:14]],
            "efficiency_pct": eff,
        })
    return {
        "standard_code": "GB 18613-2020",
        "standard_name": "电动机能效限定值及能效等级",
        "effective_date": "2021-06-01",
        "unit_note": "效率单位%；efficiency_pct按极数列顺序[2,4,6,8]",
        "rows": rows,
    }


# ============ 空压机（GB 19153-2019，4张表） ============
# V1.11"空压机标准"sheet横向布局了4张表：
#   表1 A~N   一般用喷油回转（工频）     功率/等级/压力0.3~1.25×风冷液冷
#   表2 P~AC  一般用变转速喷油回转       功率/等级/压力0.3~1.25×风冷液冷
#   表3 AE~AN 一般用往复活塞             功率/等级/压力0.25~1.4（不区分冷却）
#   表4 AP~AX 全无油润滑往复活塞         功率/等级/压力0.4~1.4（不区分冷却）
COMPRESSOR_TABLES = [
    # (表名, 类型, 功率列, 等级列, 数值起始列, 压力档列表, 是否区分冷却)
    ("表1", "一般用喷油回转（工频）", 1, 2, 3, [0.3, 0.5, 0.7, 0.8, 1.0, 1.25], True),
    ("表2", "一般用变转速喷油回转", 16, 17, 18, [0.3, 0.5, 0.7, 0.8, 1.0, 1.25], True),
    ("表3", "一般用往复活塞", 31, 32, 33, [0.25, 0.4, 0.5, 0.7, 0.8, 1.0, 1.25, 1.4], False),
    ("表4", "全无油润滑往复活塞", 42, 43, 44, [0.4, 0.5, 0.7, 0.8, 1.0, 1.25, 1.4], False),
]


def _to_float(v):
    if v in (None, "", "—", "-", "－"):
        return None
    try:
        return float(str(v).replace("—", "").replace("－", "").strip())
    except (TypeError, ValueError):
        return None


def extract_compressor(wb) -> dict:
    ws = wb["空压机标准"]
    rows = []
    for tname, ttype, pc, lc, sc, pressures, has_cool in COMPRESSOR_TABLES:
        n_cols = len(pressures) * (2 if has_cool else 1)
        cur_power = None
        for r in ws.iter_rows(min_row=2, max_row=90, min_col=pc, max_col=sc + n_cols - 1):
            vals = [c.value for c in r]
            power_v = vals[0]
            if power_v not in (None, ""):
                f = _to_float(power_v)
                if f is not None:
                    cur_power = f
            level_v = vals[1] if len(vals) > 1 else None
            level = _to_float(level_v)
            if level is None or level not in (1, 2, 3):
                continue
            for i, press in enumerate(pressures):
                if has_cool:
                    v_feng, v_ye = vals[2 + i * 2], vals[3 + i * 2]
                    rows.append({"table": tname, "type": ttype, "power_kw": cur_power,
                                 "level": int(level), "pressure_mpa": press,
                                 "cooling": "风冷", "specific_power": _to_float(v_feng)})
                    rows.append({"table": tname, "type": ttype, "power_kw": cur_power,
                                 "level": int(level), "pressure_mpa": press,
                                 "cooling": "液冷", "specific_power": _to_float(v_ye)})
                else:
                    v = vals[2 + i]
                    rows.append({"table": tname, "type": ttype, "power_kw": cur_power,
                                 "level": int(level), "pressure_mpa": press,
                                 "cooling": "", "specific_power": _to_float(v)})
    return {
        "standard_code": "GB 19153-2019",
        "standard_name": "容积式空气压缩机能效限定值及能效等级",
        "effective_date": "2020-07-01",
        "unit_note": "比功率单位kW/(m³/min)，越小越好；specific_power=None表示该档不适用(-)",
        "rows": rows,
    }


EXTRACTORS = {
    "transformer": extract_transformer,
    "motor_lv": extract_motor_lv,
    "compressor": extract_compressor,
}


# ============ 校对表Excel ============
def build_review_xlsx(data_map: dict, out_path: Path):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    red_font = openpyxl.styles.Font(color="FF0000", bold=True)
    for key, data in data_map.items():
        ws = wb.create_sheet(key)
        if key == "transformer":
            heads = ["表格", "变压器类别", "容量kVA", "铁芯材质", "绝缘等级", "连接组标号",
                     "1级空载kW", "2级空载kW", "3级空载kW", "1级负载kW", "2级负载kW", "3级负载kW",
                     "校对状态", "备注"]
            ws.append(heads)
            for row in data["rows"]:
                ws.append([
                    row["table"], row["category"], row["capacity_kva"], row["core_material"],
                    row["insulation"], row["connection"],
                    *row["no_load_kw"], *row["load_kw"],
                    "待校对", "可疑值" if row["suspicious"] else "",
                ])
                if row["suspicious"]:
                    for c in range(6, 12):
                        ws.cell(ws.max_row, c + 1).font = red_font
        elif key == "motor_lv":
            heads = ["额定功率kW", "2极1级", "2极2级", "2极3级", "4极1级", "4极2级", "4极3级",
                     "6极1级", "6极2级", "6极3级", "8极1级", "8极2级", "8极3级", "校对状态", "备注"]
            ws.append(heads)
            for row in data["rows"]:
                e = row["efficiency_pct"]
                # 列顺序：2极(3个) 4极(3个) 6极(3个) 8极(3个)
                ws.append([row["power_kw"], *e, "待校对", ""])
        elif key == "compressor":
            heads = ["表", "类型", "功率kW", "等级", "排气压力MPa", "冷却方式", "比功率kW/(m³/min)",
                     "校对状态", "备注"]
            ws.append(heads)
            prev = None
            for row in data["rows"]:
                cur = (row["table"], row["power_kw"], row["level"], row["pressure_mpa"], row["cooling"])
                v = row["specific_power"]
                ws.append([row["table"], row["type"], row["power_kw"], row["level"],
                           row["pressure_mpa"], row["cooling"], v if v is not None else "—", "待校对", ""])
                # 可疑：同表同压力同冷却、相邻功率档比功率跳变>25%（比功率随功率递减，跳变应≤25%）
                if prev and prev["t"] == row["table"] and prev["p"] == row["pressure_mpa"] \
                        and prev["c"] == row["cooling"] and prev["l"] == row["level"] \
                        and prev["v"] and v and prev["v"] > 0:
                    if abs(1 - v / prev["v"]) > 0.25:
                        ws.cell(ws.max_row, 7).font = red_font
                prev = {"t": row["table"], "p": row["pressure_mpa"], "c": row["cooling"],
                        "l": row["level"], "v": v}
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
    wb.save(out_path)
    print(f"校对表已生成: {out_path}")


def main():
    keys = sys.argv[1:] or list(EXTRACTORS.keys())
    wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
    data_map = {}
    for key in keys:
        if key not in EXTRACTORS:
            print(f"跳过未知设备: {key}")
            continue
        data = EXTRACTORS[key](wb)
        out = STD_DIR / f"{key}.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        data_map[key] = data
        print(f"✅ {key}.json: {len(data['rows'])}行 -> {out}")
    wb.close()
    if data_map:
        build_review_xlsx(data_map, STD_DIR / f"校对表_{date.today().strftime('%Y%m%d')}.xlsx")


if __name__ == "__main__":
    main()
