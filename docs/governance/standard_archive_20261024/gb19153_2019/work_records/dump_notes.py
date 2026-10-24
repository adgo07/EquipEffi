import pymupdf, re, sys

PDF = r"G:\Python Project\EquipEffi\标准原文\5. GB 19153-2019 容积式空气压缩机能效限定值及能效等级.pdf"
doc = pymupdf.open(PDF)
pages = [int(x) for x in sys.argv[1:]] or list(range(5, 16))
for pno in pages:
    pg = doc[pno - 1]
    print(f"\n########## PDF page {pno} ##########")
    d = pg.get_text("dict")
    for block in d["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            txt = "".join(s["text"] for s in line["spans"])
            t = txt.strip()
            if not t:
                continue
            # 只保留含中日韩字符或“注/表”或非纯数字的行
            if re.search(r"[\u4e00-\u9fff]", t) or t.startswith("注") or "注" in t:
                y = round(line["bbox"][1], 1)
                x = round(line["bbox"][0], 1)
                print(f"  y={y:7.1f} x={x:7.1f} | {t}")
