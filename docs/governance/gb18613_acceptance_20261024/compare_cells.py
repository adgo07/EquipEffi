import pymupdf, unicodedata, openpyxl, csv, json, os
from decimal import Decimal

PDF = r"G:\Python Project\EquipEffi\标准原文\2. GB+18613-2020 电动机能效限定值及能效等级.pdf"
WB  = r"G:\Python Project\EquipEffi\docs\standards\gb18613_2020\data\GB18613_2020_表1-6校对数据_A1.xlsx"
OUT = r"G:\Python Project\EquipEffi\_gb18613_acceptance\evidence"
os.makedirs(OUT, exist_ok=True)


def norm(s):
    return unicodedata.normalize("NFKC", str(s)).replace("\u3000", "").strip()


def get_spans(page):
    d = page.get_text("rawdict")
    out = []
    for b in d["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                txt = norm("".join(c["c"] for c in s["chars"]))
                if not txt:
                    continue
                x0, y0, x1, y1 = s["bbox"]
                out.append(dict(x0=x0, y0=y0, x1=x1, y1=y1,
                                cy=(y0 + y1) / 2, text=txt, chars=s["chars"]))
    return out


def tokens_in_row(spans, rowcy, xmin, ytol=4.0):
    chars = []
    for s in spans:
        if abs(s["cy"] - rowcy) < ytol:
            for c in s["chars"]:
                if c["bbox"][0] > xmin:
                    chars.append((round(c["bbox"][0], 2),
                                  round(c["bbox"][2], 2), c["c"]))
    chars.sort(key=lambda t: t[0])
    toks, cur, prevx = [], [], None
    for x0, x1, c in chars:
        if prevx is not None and x0 - prevx > 8:
            toks.append(cur)
            cur = []
        cur.append((x0, x1, c))
        prevx = x0
    if cur:
        toks.append(cur)
    return [("".join(t[2] for t in g),
             round((g[0][0] + g[-1][1]) / 2, 2)) for g in toks]


def extract(pno, ymin, ymax, xmin):
    page = doc[pno]
    spans = get_spans(page)
    ps = [s for s in spans
          if s["x0"] < 120
          and all(ch.isdigit() or ch in ".~" for ch in s["text"])
          and ymin < s["cy"] < ymax]
    ps.sort(key=lambda s: (s["cy"], s["x0"]))
    groups = []
    for s in ps:
        if groups and abs(s["cy"] - groups[-1][0]) < 2.0:
            groups[-1][1].append(s)
        else:
            groups.append((s["cy"], [s]))
    out = []
    for cy, ss in groups:
        txt = "".join(x["text"] for x in sorted(ss, key=lambda z: z["x0"]))
        if txt == "3151000":
            txt = "315~1000"
        out.append((txt, tokens_in_row(
            spans, sum(x["cy"] for x in ss) / len(ss), xmin)))
    return out


doc = pymupdf.open(PDF)
wb = openpyxl.load_workbook(WB, data_only=True)

T1_COLS = [f"{g}级{p}极" for g in (1, 2, 3) for p in (2, 4, 6, 8)]
T23_COLS = [f"{g}级{p}极" for g in (1, 2, 3) for p in (2, 4, 6)]
T4_COLS = [f"{g}级{p}极" for g in (1, 2, 3) for p in (2, 4)]
T5_COLS = [f"{g}级{p}极" for g in (1, 2, 3) for p in (4, 6, 8)]
T6_COLS = []
for grp in ("≤500", "500~700", "700~1000", "1000~1300", ">1300"):
    for g in (1, 2, 3):
        T6_COLS.append(f"{grp}/{g}级")

CONFIGS = [
    ("表1", "表1", 12, [(3, 150, 760, 130)], T1_COLS),
    ("表2", "表2", 9, [(4, 150, 420, 125)], T23_COLS),
    ("表3", "表3", 9, [(4, 480, 760, 125)], T23_COLS),
    ("表4", "表4", 6, [(5, 150, 360, 150)], T4_COLS),
    ("表5", "表5", 9, [(5, 400, 760, 125), (6, 150, 340, 125)], T5_COLS),
    ("表6", "表6", 15, [(6, 420, 760, 118), (7, 195, 320, 115)], T6_COLS),
]


def to_dec(s):
    s = norm(s)
    if s in ("—", "-", "–"):
        return "—"
    try:
        return Decimal(s)
    except Exception:
        return s


def pdf_value(tok):
    if tok is None:
        return None
    t = norm(tok)
    if t in ("—", "-", "–"):
        return "—"
    return to_dec(t)


def wb_value(v):
    if v is None:
        return None
    if isinstance(v, str):
        return "—" if v.strip() in ("—", "-", "–") else v.strip()
    return Decimal(str(v))


def cmp(a, b):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if a == "—" and b == "—":
        return True
    if isinstance(a, Decimal) and isinstance(b, Decimal):
        return a == b
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    return False


rows = []
summary = {}
for table, sheet, ncols, segments, colnames in CONFIGS:
    allrows = []
    for (pno, ymin, ymax, xmin) in segments:
        seg = extract(pno, ymin, ymax, xmin)
        for i, (ptxt, toks) in enumerate(seg, start=1):
            allrows.append(dict(page=pno + 1, segrow=i,
                                power=ptxt, toks=toks))
    wrows = []
    for r in range(6, wb[sheet].max_row + 1):
        pw = wb[sheet].cell(row=r, column=1).value
        if pw is None:
            continue
        wrows.append((r, pw, [wb[sheet].cell(row=r, column=c).value
                              for c in range(2, 2 + ncols)]))
    assert len(allrows) == len(wrows), (table, len(allrows), len(wrows))
    base = next(x for x in allrows if len(x["toks"]) == ncols)
    centers = [t[1] for t in base["toks"]]
    nnum = ndash = nblank = 0
    for ar, (wr, pw, vals) in zip(allrows, wrows):
        p_pdf = to_dec(ar["power"])
        p_wb = to_dec(pw) if isinstance(pw, str) else Decimal(str(pw))
        rows.append([table, ar["page"], ar["segrow"], sheet, wr,
                     "额定功率", str(p_pdf), str(p_wb),
                     "PASS" if cmp(p_pdf, p_wb) else "FAIL"])
        assigned = {}
        if len(ar["toks"]) == ncols:
            for j, (txt, cx) in enumerate(ar["toks"]):
                assigned[j] = txt
        else:
            for txt, cx in ar["toks"]:
                j = min(range(ncols), key=lambda k: abs(centers[k] - cx))
                if j in assigned:
                    raise RuntimeError(
                        f"{table} row {ar['segrow']} duplicate column {j}")
                assigned[j] = txt
        for j in range(ncols):
            tok = assigned.get(j)
            pv = pdf_value(tok)
            wv = wb_value(vals[j])
            if pv is None:
                nblank += 1
            elif pv == "—":
                ndash += 1
            else:
                nnum += 1
            rows.append([table, ar["page"], ar["segrow"], sheet, wr,
                         colnames[j], "" if pv is None else str(pv),
                         "" if wv is None else str(wv),
                         "PASS" if cmp(pv, wv) else "FAIL"])
    summary[table] = dict(rows=len(allrows),
                          efficiency_cells=len(allrows) * ncols,
                          numbers=nnum, dashes=ndash, blanks=nblank)

with open(os.path.join(OUT, "cell_compare.csv"), "w",
          encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["table", "pdf_page", "segment_row", "workbook_sheet",
                "workbook_row", "column", "pdf_value",
                "workbook_value", "result"])
    w.writerows(rows)

total = len(rows)
fails = [r for r in rows if r[-1] != "PASS"]
summary["total_cells"] = total
summary["total_pass"] = total - len(fails)
summary["total_fail"] = len(fails)
summary["pdf"] = dict(path=PDF, pages=doc.page_count)
with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print(json.dumps(summary, ensure_ascii=False, indent=2))
print("FAILS", fails[:20])
