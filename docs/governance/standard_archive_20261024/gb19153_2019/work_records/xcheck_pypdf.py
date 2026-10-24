"""第三引擎（pypdf）独立按源格 bbox 复核工作簿 N/G 列字面。"""
import re, sys, logging
from collections import defaultdict
from openpyxl import load_workbook
from pypdf import PdfReader

logging.disable(logging.CRITICAL)

PDF = r"G:\Python Project\EquipEffi\标准原文\5. GB 19153-2019 容积式空气压缩机能效限定值及能效等级.pdf"
WB = r"G:\Python Project\EquipEffi\docs\standards\gb19153_2019\data\GB19153_2019_标准表值.xlsx"

FULL = {chr(0xFF10 + i): chr(0x30 + i) for i in range(10)}
FULL.update({chr(0xFF0E): ".", chr(0xFF0D): "-", chr(0x3000): "", "．": ".", "。": "."})


def norm(s):
    if s is None:
        return ""
    s = str(s)
    s = "".join(FULL.get(ch, ch) for ch in s)
    s = s.replace("—", "-").replace("–", "-").replace("―", "-").replace("−", "-")
    s = re.sub(r"\s+", "", s)
    return s


reader = PdfReader(PDF)
H = float(reader.pages[0].mediabox.height)

# 每页收集文本块: (text, x_center, y_top, x0, x1, ytop0, ytop1)
page_glyphs = defaultdict(list)
for pno in range(1, 19):
    page = reader.pages[pno - 1]
    chunks = []

    def visitor(text, cm, tm, font_dict, font_size, _chunks=chunks):
        t = text.strip()
        if not t:
            return
        x = tm[4]
        y = tm[5]
        _chunks.append((t, x, y, font_size))

    page.extract_text(visitor_text=visitor)
    for t, x, y, fs in chunks:
        # 文本基线在左下原点体系；转成左上原点
        ytop = H - y
        w = max(len(t) * (fs or 8) * 0.55, 4)
        page_glyphs[pno].append((t, x, x + w, ytop - (fs or 8), ytop + (fs or 8) * 0.3))

print("chunks per page:", {p: len(v) for p, v in sorted(page_glyphs.items())})

wb = load_workbook(WB, data_only=True)
stats = defaultdict(lambda: [0, 0, []])
miss = []
for name in ["表1", "表2", "表3", "表4", "表5", "表6"]:
    ws = wb[name]
    for r in range(6, ws.max_row + 1):
        page = ws.cell(row=r, column=9).value
        bbox = ws.cell(row=r, column=13).value
        lit = norm(ws.cell(row=r, column=14).value)
        val = norm(ws.cell(row=r, column=7).value)
        if page is None or bbox is None:
            continue
        x0, y0, x1, y1 = [float(v) for v in str(bbox).split(",")]
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        found = []
        for (t, gx0, gx1, gy0, gy1) in page_glyphs[int(page)]:
            if gx0 - 1 <= cx <= gx1 + 1 and gy0 - 3 <= cy <= gy1 + 3:
                found.append(t)
        joined = norm("".join(found))
        ok = (joined == lit) or (lit and lit in joined)
        st = stats[name]
        if ok:
            st[0] += 1
        else:
            st[1] += 1
            if len(st[2]) < 5:
                st[2].append((r, page, bbox, lit, joined, val))

print("\n=== 表1~6 按源格 bbox 的 pypdf 字面比对 ===")
tot_ok = tot_bad = 0
for name, (ok, bad, ex) in stats.items():
    print(f"{name}: pass={ok} fail={bad}")
    tot_ok += ok
    tot_bad += bad
    for e in ex:
        print("   FAIL row=%s page=%s bbox=%s expect=%r got=%r" % e)
print("TOTAL pass=%d fail=%d" % (tot_ok, tot_bad))
