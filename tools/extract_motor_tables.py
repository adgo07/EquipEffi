# -*- coding: utf-8 -*-
"""
tools/extract_motor_tables.py - 高压电机标准提取（V1.11标准sheet）
结构：表标题行(A列"表N...") + 表头(等级行/极数行) + 数据行(功率×等级×极数)
用法：python tools/extract_motor_tables.py
"""
import json
import re
import warnings
from pathlib import Path

import openpyxl

warnings.filterwarnings("ignore")

SRC = r"G:\标准  规范\02_能耗限额_终端产品\用能设备\用能设备能效分析表V1.11.xlsx"
STD_DIR = Path(__file__).resolve().parent.parent / "standards"


def to_float(v):
    if v in (None, "", "—", "-", "－", "一"):
        return None
    s = str(v).strip().replace("—", "").replace("一", "")
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def parse_speed_range(s):
    """' >1800~6000/r/min' -> (1800,6000); '500/r/min' -> (500,500); 失败->None"""
    s = str(s).replace("～", "~").replace("r/min", "").replace("r", "").replace("/", "").strip()
    m = re.match(r"[>≥≤]?(\d+(?:\.\d+)?)\s*~\s*(\d+(?:\.\d+)?)", s)
    if m:
        return (float(m.group(1)), float(m.group(2)))
    m = re.match(r"[>≥≤]?(\d+(?:\.\d+)?)", s)
    if m:
        v = float(m.group(1))
        return (v, v)
    return None


def clean_text(s):
    """Normalize layout whitespace without changing the table meaning."""
    s = str(s).replace("～", "~").replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*~\s*", "~", s)
    s = re.sub(r"(?<=\d)r/min", " r/min", s)
    return s


def parse_motor_table(ws, start_row):
    """解析一张表。支持两种维度：
    - 极数模式（异步电机）：标题/功率/等级行/极数行/数据（4行表头）
    - 转速模式（变频电机）：标题/功率/转速行/数据（3行表头，等级在标题里）
    """
    title = clean_text(ws.cell(start_row, 1).value)

    # 变频表通常在标题后第2行放转速维度；表29另有一行“额定转速”说明，
    # 实际转速维度位于第4行，因此同时检查两种布局。
    speed_dims = []
    speed_row = None
    for offset in (2, 4):
        candidate = []
        for c in range(2, 40):
            v = ws.cell(start_row + offset, c).value
            if v is None:
                continue
            s = clean_text(v)
            is_level_label = re.match(r"\d+\s*级", s)
            # 只有带转速单位、转速区间或不等号的值才可能是转速维度。
            # 不能把普通效率数值（如94、93.9）当成转速，否则极数表会被误判为转速表。
            is_speed_label = (
                "r/min" in s
                or re.search(r"\d+\s*[～~]\s*\d+", s)
                or re.match(r"[>≥≤]\s*\d+", s)
            )
            if not is_level_label and is_speed_label:
                rg = parse_speed_range(s)
                if rg:
                    if not any(existing == s for existing, _ in candidate):
                        candidate.append((s, rg))
        if candidate:
            speed_dims = candidate
            speed_row = start_row + offset
            break

    if speed_dims:
        # ===== 转速模式（变频）=====
        m = re.search(r"(\d+)\s*级", title)
        if m:
            # 旧版布局：表标题本身带有“1级/2级/3级”，数据只有一个等级块。
            level_starts = {2: int(m.group(1))}
        else:
            # 表29布局：标题不带等级，等级写在 start_row+2 的分组表头中。
            level_starts = {}
            for c in range(2, 60):
                v = ws.cell(start_row + 2, c).value
                if v is None:
                    continue
                mm = re.match(r"(\d+)\s*级", str(v).strip())
                if mm:
                    level_starts[c] = int(mm.group(1))
            if not level_starts:
                return None, start_row + 1
        dims = speed_dims
        dim_desc = "speeds"
        data_start = speed_row + 1
    else:
        # ===== 极数模式 =====
        lv_row = start_row + 2
        level_starts = {}
        for c in range(2, 60):
            v = ws.cell(lv_row, c).value
            if v is not None:
                mm = re.match(r"(\d+)\s*级", str(v).strip())
                if mm:
                    level_starts[c] = int(mm.group(1))
        if not level_starts:
            return None, start_row + 1
        pole_row = start_row + 3
        poles_raw = []
        for c in range(2, 60):
            v = ws.cell(pole_row, c).value
            if v is None:
                continue
            s = str(v).strip()
            m2 = re.match(r"(\d+)\s*极", s)
            if m2:
                poles_raw.append(int(m2.group(1)))
            elif s.isdigit():
                poles_raw.append(int(s))
        if not poles_raw:
            return None, start_row + 1
        dims = []
        for p in poles_raw:
            if p not in dims:
                dims.append(p)
        dim_desc = "poles"
        data_start = start_row + 4

    # 数据行
    rows = []
    r = data_start
    max_r = ws.max_row
    total_cols = len(dims) * len(level_starts)
    while r <= max_r:
        pv = ws.cell(r, 1).value
        if pv is None:
            nxt = ws.cell(r + 1, 1).value if r + 1 <= max_r else None
            if nxt is None:
                break
            r += 1
            continue
        s = str(pv).strip()
        if s.startswith("表") or s.startswith("额定功率"):
            break
        pf = to_float(pv)
        if pf is None:
            r += 1
            continue
        eff = {}
        for c in range(2, 2 + total_cols):
            v = ws.cell(r, c).value
            lv_col = max([lc for lc in level_starts if lc <= c], default=None)
            if lv_col is None:
                continue
            lv = level_starts[lv_col]
            idx = (c - lv_col) % len(dims)
            eff.setdefault(str(lv), {})[idx] = to_float(v)
        rows.append({"power_kw": pf, "efficiency": eff})
        r += 1
    info = {
        "title": title,
        "mode": dim_desc,
        "dims": dims,
        "levels": sorted(str(x) for x in level_starts.values()),
        "rows": rows,
    }
    return info, r


def extract_generic(wb, sheet_name, std_code, std_name, eff_date):
    """通用提取：遍历sheet中所有"表N"标题块"""
    ws = wb[sheet_name]
    tables = []
    r = 1
    max_r = ws.max_row
    while r <= max_r:
        v = ws.cell(r, 1).value
        if v is not None and str(v).strip().startswith("表"):
            info, next_r = parse_motor_table(ws, r)
            if info is None:
                print(f"  ⚠ 解析失败跳过: R{r} {str(v).strip()[:40]}")
                r = next_r
                continue
            # 表29在原工作簿分页处重复了90 kW和110 kW两行；相同功率且全部效率值
            # 完全一致时只保留一条，避免把分页重复误当成标准数据。
            if "电梯用永磁同步电动机" in info["title"]:
                unique_rows = []
                seen = set()
                for row in info["rows"]:
                    marker = json.dumps(row, ensure_ascii=False, sort_keys=True)
                    if marker not in seen:
                        seen.add(marker)
                        unique_rows.append(row)
                info["rows"] = unique_rows
            tables.append(info)
            r = next_r
        else:
            r += 1
    return {
        "standard_code": std_code,
        "standard_name": std_name,
        "effective_date": eff_date,
        "unit_note": "效率单位%；efficiency字典: {等级: [按poles顺序的效率数组]}",
        "tables": tables,
    }


def main():
    # 注意：不能用read_only模式（ws.cell随机访问极慢），普通模式加载
    wb = openpyxl.load_workbook(SRC, data_only=True)
    jobs = [
        ("高压电机标准", "GB 30254-2024", "高压三相笼型异步电动机能效限定值及能效等级", "2025-09-01", "motor_hv"),
    ]
    for sheet, code, name, date, key in jobs:
        data = extract_generic(wb, sheet, code, name, date)
        out = STD_DIR / f"{key}.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        nrows = sum(len(t["rows"]) for t in data["tables"])
        print(f"✅ {key}.json: {len(data['tables'])}张表/{nrows}行 -> {out}")
    wb.close()


if __name__ == "__main__":
    main()
