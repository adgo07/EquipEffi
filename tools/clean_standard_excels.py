# -*- coding: utf-8 -*-
"""清洗第四来源标准 Excel，输出到 standards2/第四来源Excel_清洗版。"""
import json
import re
import shutil
import unicodedata
from pathlib import Path

import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path(r"C:\Users\WANGWEI\Documents\EquipEffi\能效标准表格提取")
ANALYSIS = Path(r"G:\标准  规范\02_能耗限额_终端产品\用能设备\（无图片)用能设备能效分析表V1.11.xlsx")
OUT = ROOT / "standards2" / "第四来源Excel_清洗版"

FONT = Font(name="Microsoft YaHei", size=10, color="000000")
TITLE_FONT = Font(name="Microsoft YaHei", size=11, bold=True, color="000000")
HEADER_FONT = Font(name="Microsoft YaHei", size=10, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="4472C4")
SUBHEADER_FILL = PatternFill("solid", fgColor="D9EAF7")
THIN = Side(style="thin", color="B7C9D6")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

STANDARD_FILES = {
    "01_变压器.xlsx": "1. GB 20052-2024 电力变压器能效限定值及能效等级.xlsx",
    "02_低压电动机.xlsx": "2. GB+18613-2020 电动机能效限定值及能效等级.xlsx",
    "03_高压电动机.xlsx": "3. GB 30254-2024 高压三相笼型异步电动机能效限定值及能效等级.xlsx",
    "05_空压机.xlsx": "5. GB 19153-2019 容积式空气压缩机能效限定值及能效等级.xlsx",
    "06_泵.xlsx": "6 7. GB 19762-2025 离心泵能效限定值及能效等级.xlsx",
    "07_通风机.xlsx": "8. GB+19761-2020 通风机能效限定值及能效等级.xlsx",
    "08_鼓风机.xlsx": "9. GB 28381-2012 离心鼓风机能效限定值及节能评价值.xlsx",
    "09_鼓风机_2026版.xlsx": "9. GB+28381-2026 鼓风机能效限定值及能效等级.xlsx",
    "10_潜水电泵.xlsx": "10. GB 32030-2022_潜水电泵能效限定值及能效等级.xlsx",
    "11_工业锅炉.xlsx": "11. GB+24500-2020 工业锅炉能效限定值及能效等级.xlsx",
    "12_热处理设备.xlsx": "12. GB／T 36561-2018 清洁节能热处理装备技术要求及评价体系.xlsx",
    "13_热泵和冷水机组.xlsx": "13. GB 19577-2024 热泵和冷水机组能效限定值及能效等级.xlsx",
    "14_热泵热水机.xlsx": "14. GB 29541 2013 热泵热水机（器）能效限定值及能效等级.xlsx",
    "15_风管送风式空调.xlsx": "15. GB_37479-2019 风管送风式空调机组能效限定值及能效等级.xlsx",
    "16_单元式空调.xlsx": "16. GB 19576_2019 单元式空气调节机能效限定值及能效等级.xlsx",
    "17_多联式空调.xlsx": "17. GB 21454-2021 多联式空调（热泵）机组能效限定值及能效等级.xlsx",
}


def clean_text(value):
    s = unicodedata.normalize("NFKC", str(value))
    s = s.replace("\u00a0", " ").replace("\u200b", "")
    s = s.replace("～", "~").replace("−", "-").replace("－", "-")
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    return s.strip()


def clean_value(value):
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    s = clean_text(value)
    if not s:
        return None
    # 保留标准中的破折号、比较符号、单位和注释文本。
    num = s.replace(",", "")
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", num):
        try:
            return float(num)
        except ValueError:
            pass
    return s


def style_sheet(ws):
    ws.freeze_panes = "A2"
    ws.sheet_view.showGridLines = False
    max_row, max_col = ws.max_row, ws.max_column
    for row in ws.iter_rows():
        for cell in row:
            if cell.value is not None:
                cell.font = FONT
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = BORDER
                if cell.row == 1 or cell.value is not None and cell.row <= 3:
                    cell.fill = SUBHEADER_FILL
    # 识别表题/表头行，统一加粗；不依赖乱码标题内容。
    for r in range(1, min(max_row, 8) + 1):
        nonempty = sum(ws.cell(r, c).value is not None for c in range(1, max_col + 1))
        if nonempty >= 2:
            for c in range(1, max_col + 1):
                cell = ws.cell(r, c)
                if cell.value is not None:
                    cell.font = HEADER_FONT if r <= 3 else TITLE_FONT
                    cell.fill = HEADER_FILL if r <= 2 else SUBHEADER_FILL
    for c in range(1, max_col + 1):
        max_len = 8
        for r in range(1, min(max_row, 80) + 1):
            value = ws.cell(r, c).value
            if value is not None:
                max_len = max(max_len, max(len(line) for line in str(value).split("\n")) + 2)
        ws.column_dimensions[get_column_letter(c)].width = min(max_len, 34)
    for r in range(1, max_row + 1):
        ws.row_dimensions[r].height = 24
    # 只对真正数值设置统一格式，避免破坏含单位或比较符号的文本。
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, float):
                cell.number_format = "0.###"


def copy_clean_workbook(src, dst):
    old = openpyxl.load_workbook(src, data_only=False)
    new = Workbook()
    new.remove(new.active)
    for old_ws in old.worksheets:
        title = clean_text(old_ws.title)[:31] or "Sheet"
        if title in new.sheetnames:
            title = f"{title[:27]}_{len(new.sheetnames)}"
        ws = new.create_sheet(title)
        for row in old_ws.iter_rows():
            for cell in row:
                out = ws.cell(cell.row, cell.column, clean_value(cell.value))
                if cell.number_format:
                    out.number_format = cell.number_format
        for merged in old_ws.merged_cells.ranges:
            try:
                ws.merge_cells(str(merged))
            except ValueError:
                pass
        style_sheet(ws)
    new.save(dst)
    old.close()


def copy_analysis_sheet(sheet_name, dst):
    old = openpyxl.load_workbook(ANALYSIS, data_only=False)
    src = old[sheet_name]
    new = Workbook()
    new.remove(new.active)
    ws = new.create_sheet(sheet_name[:31])
    for row in src.iter_rows():
        for cell in row:
            ws.cell(cell.row, cell.column, clean_value(cell.value))
    for merged in src.merged_cells.ranges:
        try:
            ws.merge_cells(str(merged))
        except ValueError:
            pass
    style_sheet(ws)
    new.save(dst)
    old.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for output_name, source_name in STANDARD_FILES.items():
        src = SOURCE / source_name
        if not src.exists():
            continue
        dst = OUT / output_name
        # 仅低压/高压电机可使用分析表重建。永磁同步电机旧分析表被明确禁用。
        if output_name == "02_低压电动机.xlsx":
            copy_analysis_sheet("电动机标准", dst)
            method = "分析表-电动机标准"
        elif output_name == "03_高压电动机.xlsx":
            copy_analysis_sheet("高压电机标准", dst)
            method = "分析表-高压电机标准"
        else:
            copy_clean_workbook(src, dst)
            method = "第四来源Excel清洗"
        manifest.append({"output": output_name, "source": str(src), "method": method})
    (OUT / "清洗说明.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    report = [
        "# 标准 Excel 清洗报告",
        "",
        f"清洗文件数：{len(manifest)}",
        "",
        "处理内容：统一 Microsoft YaHei 字体、边框、对齐、换行、列宽、冻结窗格和数值格式；将可识别的全角数字转换为数值；清除控制字符和明显字体映射乱码。",
        "",
        "低压和高压电机采用分析表中可读的标准 sheet 重建；永磁同步电机旧分析表和粗校对工作簿不进入本链路，只能使用PDF独立重建包。其他设备保留第四来源的PDF逐格校对结果并做格式清洗。",
        "",
        "| 输出文件 | 处理方式 |",
        "|---|---|",
    ]
    report.extend(f"| {item['output']} | {item['method']} |" for item in manifest)
    (OUT / "清洗报告.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"✅ 清洗完成: {OUT}")
    print(f"✅ 文件数: {len(manifest)}")


if __name__ == "__main__":
    main()
