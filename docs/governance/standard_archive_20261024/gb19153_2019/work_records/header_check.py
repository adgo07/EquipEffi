"""核对压力表头文字 x 位置 与 工作簿 压力→列 x 的对应关系。"""
import re
from openpyxl import load_workbook
import pymupdf

PDF = r"G:\Python Project\EquipEffi\标准原文\5. GB 19153-2019 容积式空气压缩机能效限定值及能效等级.pdf"
WB = r"G:\Python Project\EquipEffi\docs\standards\gb19153_2019\data\GB19153_2019_标准表值.xlsx"
FULL = {chr(0xFF10 + i): chr(0x30 + i) for i in range(10)}
FULL[chr(0xFF0E)] = "."


def nz(s):
    return "".join(FULL.get(c, c) for c in str(s))


doc = pymupdf.open(PDF)
wb = load_workbook(WB, data_only=True)

# 每个表：表头所在的 PDF 页
HEAD = {"表1": 5, "表2": 8, "表3": 10, "表4": 12, "表5": 14, "表6": 15}
for tname, pno in HEAD.items():
    pg = doc[pno - 1]
    ws = wb[tname]
    # 工作簿：压力 -> 该压力第一列（风冷/首个分支）的 x0
    colx = {}
    for r in range(6, ws.max_row + 1):
        p = ws.cell(row=r, column=4).value
        bbox = ws.cell(row=r, column=13).value
        if p is None or bbox is None:
            continue
        x0 = float(str(bbox).split(",")[0])
        colx.setdefault(p, set()).add(round(x0, 1))
    # PDF：在表头区域（含"额定排气压力"字样的行附近）找压力数字及其 x
    labels = []
    for w in pg.get_text("words"):
        t = nz(w[4])
        if re.fullmatch(r"\d+\.\d+", t) and w[1] < 260:
            labels.append((round(w[0], 1), t, round(w[1], 1)))
    labels.sort()
    print(f"--- {tname} (PDF {pno})")
    print("   PDF 表头数字（x, 值, y）:", [(x, v) for x, v, y in labels])
    print("   工作簿 压力->列x0:", {k: sorted(v) for k, v in sorted(colx.items())})
