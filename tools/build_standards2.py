# -*- coding: utf-8 -*-
"""三来源复核后整理 standards2。

选择原则：
1. 对已有结构化 JSON 的设备，优先使用已按分析表/PDF修正并通过规则检查的 JSON；
2. 对 JSON 尚未覆盖或为空的设备，保留之前批量转换的 Excel，并明确标注为待进一步逐格复核；
3. 对低压和高压电机，额外从“标准”sheet重新重建并与 JSON 比较。

永磁同步电机旧JSON、粗校对Excel和旧分析表明确禁止进入本脚本；其唯一
数据生成入口是 tools/rebuild_pmsm_pdf.py。
"""
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SOURCE_JSON = ROOT / "standards"
OUT = ROOT / "standards2"
CONVERTED = Path(r"G:\Python Project\project\TRFM md\TRFM md\重点设备能效标准_Excel")
FOURTH = Path(r"C:\Users\WANGWEI\Documents\EquipEffi\能效标准表格提取")
ANALYSIS = Path(r"G:\标准  规范\02_能耗限额_终端产品\用能设备\（无图片)用能设备能效分析表V1.11.xlsx")

MOTOR_JOBS = {
    "motor_lv": ("电动机标准", "GB 18613-2020", "电动机能效限定值及能效等级"),
    "motor_hv": ("高压电机标准", "GB 30254-2024", "高压三相笼型异步电动机能效限定值及能效等级"),
}

CONVERTED_MAP = {
    "transformer": "1. GB 20052-2024 电力变压器能效限定值及能效等级.xlsx",
    "motor_lv": "2. GB 18613-2020 电动机能效限定值及能效等级.xlsx",
    "motor_hv": "3. GB 30254-2024 高压三相笼型异步电动机能效限定值及能效等级（2025.9.1实施）.xlsx",
    "compressor": "5. GB 19153-2019 容积式空气压缩机能效限定值及能效等级.xlsx",
    "pump": "6 7. GB 19762-2025 离心泵能效限定值及能效等级.xlsx",
    "fan": "8. GB 19761-2020 通风机能效限定值及能效等级.xlsx",
    "blower": "9. GB 28381-2012 离心鼓风机能效限定值及节能评价值.xlsx",
    "submersible": "10. GB 32030-2022_潜水电泵能效限定值及能效等级.xlsx",
    "boiler": "11. GB 24500-2020 工业锅炉能效限定值及能效等级.xlsx",
    "heat_treatment": "12. GB／T 36561-2018 清洁节能热处理装备技术要求及评价体系.xlsx",
    "heat_pump_chiller": "13. GB 19577-2024 热泵和冷水机组能效限定值及能效等级.xlsx",
    "heat_pump_water_heater": "14. GB 29541 2013 热泵热水机（器）能效限定值及能效等级.xlsx",
    "duct_ac": "15. GB_37479-2019 风管送风式空调机组能效限定值及能效等级.xlsx",
    "unitary_ac": "16. GB 19576_2019 单元式空气调节机能效限定值及能效等级.xlsx",
    "multi_split_ac": "17. GB 21454-2021 多联式空调（热泵）机组能效限定值及能效等级.xlsx",
}

DISPLAY = {
    "transformer": "变压器", "motor_lv": "低压电动机", "motor_hv": "高压电动机",
    "compressor": "空压机", "pump": "泵",
    "fan": "通风机", "blower": "鼓风机", "submersible": "潜水电泵",
    "boiler": "工业锅炉", "heat_treatment": "热处理设备",
    "heat_pump_chiller": "热泵和冷水机组", "heat_pump_water_heater": "热泵热水机",
    "duct_ac": "风管送风式空调", "unitary_ac": "单元式空调", "multi_split_ac": "多联式空调",
}


def json_counts(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if "tables" in data:
        return len(data["tables"]), sum(len(t.get("rows", [])) for t in data["tables"])
    if "rows" in data:
        return 1, len(data["rows"])
    return 0, 0


def json_normalize(value):
    """将内存对象和 JSON 读回对象统一为 JSON 语义，消除 int/string 键差异。"""
    if isinstance(value, dict):
        return {str(k): json_normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_normalize(v) for v in value]
    return value


def workbook_quality(path):
    """统计转换工作簿的明显编码异常，不把它误当作数值正确性证明。"""
    bad_re = re.compile(r"\(cid_|[犌犅]|[’‘]|[#$%&*+]|[!@]")
    values = []
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None:
                    values.append(str(cell.value))
    bad = sum(bool(bad_re.search(v)) for v in values)
    return len(wb.sheetnames), len(values), bad


def fourth_matches(key):
    tokens = {
        "transformer": ("20052",), "motor_lv": ("18613",), "motor_hv": ("30254",),
        "compressor": ("19153",), "pump": ("19762",),
        "fan": ("19761",), "blower": ("28381-2012",), "submersible": ("32030",),
        "boiler": ("24500",), "heat_treatment": ("36561",), "heat_pump_chiller": ("19577",),
        "heat_pump_water_heater": ("29541",), "duct_ac": ("37479",),
        "unitary_ac": ("19576",), "multi_split_ac": ("21454",),
    }
    hits = []
    for f in FOURTH.glob("*.xlsx"):
        name = f.name.replace("+", " ").replace("_", " ")
        if any(token in name for token in tokens.get(key, ())):
            hits.append(f)
    return sorted(hits)


def fourth_audit():
    """读取第四套自带的 PDF-Excel 校对汇总。"""
    result = {}
    report = FOURTH / "校对报告.xlsx"
    if not report.exists():
        return result
    wb = openpyxl.load_workbook(report, read_only=True, data_only=True)
    ws = wb["校对汇总"]
    code_to_key = {"20052": "transformer", "18613": "motor_lv", "30254": "motor_hv", "19153": "compressor", "19762": "pump", "19761": "fan", "28381-2012": "blower", "32030": "submersible", "24500": "boiler", "36561": "heat_treatment", "19577": "heat_pump_chiller", "29541": "heat_pump_water_heater", "37479": "duct_ac", "19576": "unitary_ac", "21454": "multi_split_ac"}
    for row in ws.iter_rows(min_row=2, values_only=True):
        name = str(row[0] or "").replace("+", " ").replace("_", " ")
        key = next((v for token, v in code_to_key.items() if token in name), None)
        if key:
            result[key] = {"pages": row[1], "tables": row[2], "cells": row[3], "equal": row[4], "format_diff": row[5], "manual": row[6], "conclusion": row[7]}
    wb.close()
    return result


def compare_motors():
    """用分析表标准sheet重建低压/高压电机；永磁电机禁止走本链路。"""
    from tools.extract_standards import extract_motor_lv
    from tools.extract_motor_tables import extract_generic

    wb = openpyxl.load_workbook(ANALYSIS, data_only=True)
    rebuilt = {
        "motor_lv": extract_motor_lv(wb),
        "motor_hv": extract_generic(wb, "高压电机标准", "GB 30254-2024", "高压三相笼型异步电动机能效限定值及能效等级", "2025-09-01"),
    }
    results = {}
    for key, expected in rebuilt.items():
        actual = json.loads((SOURCE_JSON / f"{key}.json").read_text(encoding="utf-8"))
        results[key] = {
            "equal": json_normalize(actual) == json_normalize(expected),
            "expected_tables": len(expected.get("tables", [])),
            "actual_tables": len(actual.get("tables", [])),
            "expected_rows": sum(len(t.get("rows", [])) for t in expected.get("tables", [])) if "tables" in expected else len(expected.get("rows", [])),
            "actual_rows": sum(len(t.get("rows", [])) for t in actual.get("tables", [])) if "tables" in actual else len(actual.get("rows", [])),
        }
    wb.close()
    return results


def main():
    OUT.mkdir(exist_ok=True)
    raw_dir = OUT / "原始转换Excel_按设备"
    raw_dir.mkdir(exist_ok=True)
    raw4_dir = OUT / "第四来源Excel_按设备"
    raw4_dir.mkdir(exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    for key, source_name in CONVERTED_MAP.items():
        src = CONVERTED / source_name
        if src.exists():
            shutil.copy2(src, raw_dir / f"{key}.xlsx")
        hits = fourth_matches(key)
        if hits:
            shutil.copy2(hits[0], raw4_dir / f"{key}.xlsx")

    # 复制现有结构化结果；永磁同步电机旧JSON必须排除。
    selected = {}
    for src in sorted(SOURCE_JSON.glob("*.json")):
        key = src.stem
        if key == "motor_pmsm":
            continue
        tables, rows = json_counts(src)
        if rows > 0:
            shutil.copy2(src, OUT / src.name)
            selected[key] = {"设备": DISPLAY.get(key, key), "选择": "结构化 JSON（标准sheet重建；来源4逐格校对作证据）", "表数": tables, "行数": rows}

    # 空结构或尚未有结构化结果的设备，明确保留批量转换 Excel，避免伪造 JSON。
    for key in CONVERTED_MAP:
        src = SOURCE_JSON / f"{key}.json"
        if not src.exists() or json_counts(src)[1] == 0:
            selected[key] = {"设备": DISPLAY.get(key, key), "选择": "来源4 Excel（PDF逐格校对结果）", "表数": None, "行数": None}

    motor_results = compare_motors()
    fourth_results = fourth_audit()
    report = OUT / "三来源设备对比报告.md"
    lines = [
        "# 三来源设备数据对比报告",
        "",
        f"生成日期：{date.today().isoformat()}",
        "",
        "## 来源",
        "",
        "1. `G:\\Python Project\\EquipEffi\\standards`：当前结构化 JSON。",
        "2. `G:\\Python Project\\project\\TRFM md\\TRFM md\\重点设备能效标准_Excel`：批量转换 Excel。",
        "3. `G:\\标准  规范\\02_能耗限额_终端产品\\用能设备\\（无图片)用能设备能效分析表V1.11.xlsx`：主分析表及标准 sheets。",
        "4. `C:\\Users\\WANGWEI\\Documents\\EquipEffi\\能效标准表格提取`：带 PDF 逐格校对报告的转换结果。",
        "",
        "## 设备选择结果",
        "",
        "| 设备 | 采用来源 | 结构规模 | 说明 |",
        "|---|---|---:|---|",
    ]
    for key in CONVERTED_MAP:
        item = selected.get(key, {"设备": DISPLAY.get(key, key), "选择": "未覆盖", "表数": None, "行数": None})
        note = ""
        fourth = fourth_results.get(key)
        fourth_note = ""
        if fourth:
            fourth_note = f"来源4：{fourth['conclusion']}，{fourth['cells']}单元格，人工复核{fourth['manual']}"
        if key in motor_results:
            m = motor_results[key]
            note = f"标准 sheet 重建比对：{'一致' if m['equal'] else '不一致'}（{m['actual_tables']}表/{m['actual_rows']}行）；{fourth_note}"
        elif item["选择"].startswith("来源4"):
            note = f"当前 JSON 为空或未覆盖，优先保留来源4；{fourth_note}"
        else:
            note = f"结构化结果已保留；{fourth_note}"
        size = f"{item['表数']}表/{item['行数']}行" if item["表数"] is not None else "—"
        lines.append(f"| {item['设备']} | {item['选择']} | {size} | {note} |")

    lines += ["", "## 三类电机独立重建结果", ""]
    for key, result in motor_results.items():
        lines.append(f"- {DISPLAY[key]}：{'一致' if result['equal'] else '不一致'}；标准表 {result['expected_tables']} / {result['expected_rows']} 行，JSON {result['actual_tables']} / {result['actual_rows']} 行。")

    lines += [
        "",
        "## 转换 Excel 质量提示",
        "",
        "批量转换 Excel 中，高压电机工作表存在明显字体编码乱码（如 `$`、`#`、`(cid_` 等），不能作为首选依据。永磁同步电机被本脚本完全排除，只能使用PDF独立重建包。",
        "",
        "第四来源自带 PDF-Excel 校对报告：23 个文字型标准共 45,235 个单元格，45,224 个完全一致，11 个为换行/上下标等格式差异，0 个需人工复核；通风机的 11 个差异仍保留原文，不擅自改写。扫描件标准仍需结合原 PDF 图像复核。",
        "",
        "## 数值规律检查原则",
        "",
        "- 等级列：1级效率应不低于2级，2级应不低于3级；",
        "- 同一等级同一维度下，功率增加时效率不应出现无理由的大幅下降；",
        "- 极数/转速必须作为独立维度，不能把多个维度拼成一个字符串；",
        "- 功率、等级、单位、空值和重复行分别检查；",
        "- 规律检查只能发现异常，不能替代原表逐单元格比对。",
        "",
        "## 输出内容",
        "",
        "- 根目录 JSON：当前可结构化的设备数据；",
        "- `原始转换Excel_按设备`：按设备类型重新命名归档的批量转换 Excel；",
        "- `第四来源Excel_按设备`：第四来源按设备类型归档的 Excel；",
        "- `校对表_全部设备_三来源复核.xlsx`：可视化校对表；",
        "- 本报告：来源选择、规模和残余风险。",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "来源选择.json").write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")

    # 复用校对表构建器，输出到 standards2。
    import tools.build_review_sheets as review
    review.STD_DIR = OUT
    review.date = date
    review.FILES = [f for f in review.FILES if (OUT / f).exists()]
    review.main()
    generated = OUT / f"校对表_全部设备_{date.today().strftime('%Y%m%d')}.xlsx"
    target = OUT / "校对表_全部设备_三来源复核.xlsx"
    if generated.exists():
        generated.replace(target)
    print(f"✅ standards2 已生成: {OUT}")
    print(f"✅ 报告: {report}")
    print(f"✅ 电机重建: {motor_results}")


if __name__ == "__main__":
    main()
