"""第三引擎（PyMuPDF/MuPDF）独立按源格 bbox 逐格复核 GB19153 工作簿。"""
import re, sys, json
from collections import defaultdict, Counter
from openpyxl import load_workbook
import fitz

PDF = r"G:\Python Project\EquipEffi\标准原文\5. GB 19153-2019 容积式空气压缩机能效限定值及能效等级.pdf"
WB = r"G:\Python Project\EquipEffi\docs\standards\gb19153_2019\data\GB19153_2019_标准表值.xlsx"

FULL = {chr(0xFF10 + i): chr(0x30 + i) for i in range(10)}
FULL.update({chr(0xFF0E): ".", chr(0x3000): "", "．": "."})


def norm(s):
    if s is None:
        return ""
    s = str(s)
    s = "".join(FULL.get(ch, ch) for ch in s)
    for d in "—–―−":
        s = s.replace(d, "-")
    return re.sub(r"\s+", "", s)


doc = fitz.open(PDF)
print("fitz pages:", doc.page_count)
words = {}
for pno in range(doc.page_count):
    pg = doc[pno]
    ws_ = pg.get_text("words")  # x0,y0,x1,y1,word,block,line,word_no
    words[pno + 1] = [(w[0], w[1], w[2], w[3], w[4]) for w in ws_]
    print("page", pno + 1, "words:", len(ws_), "rect:", pg.rect)

wb = load_workbook(WB, data_only=True)
res = {}
page_tokens = defaultdict(Counter)

for name in ["表1", "表2", "表3", "表4", "表5", "表6"]:
    ws = wb[name]
    ok = bad = 0
    fails = []
    tok_expected = Counter()
    for r in range(6, ws.max_row + 1):
        page = ws.cell(row=r, column=9).value
        bbox = ws.cell(row=r, column=13).value
        lit = norm(ws.cell(row=r, column=14).value)
        if page is None or bbox is None:
            continue
        x0, y0, x1, y1 = [float(v) for v in str(bbox).split(",")]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        got = []
        for (wx0, wy0, wx1, wy1, wtext) in words[int(page)]:
            wcx, wcy = (wx0 + wx1) / 2, (wy0 + wy1) / 2
            if x0 - 1.5 <= wcx <= x1 + 1.5 and y0 - 2.5 <= wcy <= y1 + 2.5:
                got.append(wtext)
        joined = norm("".join(got))
        tok_expected[norm(ws.cell(row=r, column=14).value)] += 1
        if joined == lit or (lit and lit in joined):
            ok += 1
        else:
            bad += 1
            if len(fails) < 8:
                fails.append((r, int(page), bbox, lit, joined))
    res[name] = (ok, bad, fails, tok_expected)

tot = [0, 0]
print("\n=== 逐源格 MuPDF 复核（第三引擎）===")
for name, (ok, bad, fails, te) in res.items():
    print(f"{name}: pass={ok} fail={bad}")
    for f in fails:
        print("   FAIL row=%s page=%s bbox=%s expect=%r got=%r" % f)
    tot[0] += ok
    tot[1] += bad
print("TOTAL pass=%d fail=%d" % tuple(tot))

# 页级数值多重集比对：比较页面全部数字字面与工作簿该页全部字面
print("\n=== 页级字面多重集比对（数字/破折号）===")
for pno in sorted(page_tokens):
    pass
# 建立工作簿每页期望多重集
exp = defaultdict(Counter)
for name in ["表1", "表2", "表3", "表4", "表5", "表6"]:
    ws = wb[name]
    for r in range(6, ws.max_row + 1):
        page = ws.cell(row=r, column=9).value
        lit = norm(ws.cell(row=r, column=14).value)
        if page is None:
            continue
        exp[int(page)][lit] += 1

for pno in sorted(exp):
    got = Counter()
    for (wx0, wy0, wx1, wy1, wtext) in words[pno]:
        n = norm(wtext)
        if re.fullmatch(r"\d+(\.\d+)?", n) or n == "-":
            got[n] += 1
    # 工作簿期望里，合并破折号是展开的，需按唯一 bbox 折叠
    e = Counter(exp[pno])
    missing = e - got
    extra = got - e
    print(f"page {pno}: expected_kinds={len(e)} expected_total={sum(e.values())} "
          f"pdf_total={sum(got.values())} missing_total={sum(missing.values())} extra_total={sum(extra.values())}")
    if missing:
        print("   missing sample:", list(missing.items())[:12])
    if extra:
        print("   extra sample:", list(extra.items())[:12])
