import sys, json
from pypdf import PdfReader

PDF = r"G:\Python Project\EquipEffi\标准原文\5. GB 19153-2019 容积式空气压缩机能效限定值及能效等级.pdf"
r = PdfReader(PDF)
print("PAGES:", len(r.pages))
print("META:", r.metadata)
out = []
for i, p in enumerate(r.pages, 1):
    box = p.mediabox
    t = p.extract_text() or ""
    out.append(t)
    print(f"=== page {i} box={box.width}x{box.height} chars={len(t)} ===")
with open(r"G:\Python Project\EquipEffi\docs\standards\gb19153_2019\tmp\pypdf_text.txt", "w", encoding="utf-8") as f:
    for i, t in enumerate(out, 1):
        f.write(f"\n\n===== PAGE {i} =====\n")
        f.write(t)
