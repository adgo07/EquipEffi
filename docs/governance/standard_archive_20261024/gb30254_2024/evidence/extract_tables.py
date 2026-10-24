"""Stage A extraction only. Source PDF is read-only; no production data generated.
Glyph anchors transcribed from Poppler-rendered original PDF pages on 2026-10-13.
Run with the bundled Python runtime from repository root.
"""
from pathlib import Path
import json, re, csv, hashlib
import pdfplumber
from pypdf import PdfReader, PdfWriter

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]
SOURCE = ROOT / '标准原文/3. GB 30254-2024 高压三相笼型异步电动机能效限定值及能效等级.pdf'
WORK = BASE / '_work'
WORK.mkdir(exist_ok=True)
ANCHORS = {
7: ['200 94.0 93.1 92.3 93.9 93.0 92.1 93.7 92.8 91.9 93.4 92.5 91.4 93.2 92.2 91.1 92.9 91.8 90.7'],
8: ['2000 96.7 96.3 95.8 96.6 96.2 95.7 96.5 96.1 95.6 96.2 95.8 95.2 95.9 95.4 94.8 95.7 95.1 94.5'],
9: ['20000 — — — 97.9 97.6 97.2 — — — — — — — — — — — —', '22400 — — — 97.9 97.6 97.2 — — — — — — — — — — — —', '25000 — — — 97.9 97.6 97.2 — — — — — — — — — — — —', '200 93.7 92.8 92.0 93.6 92.7 91.9 93.4 92.5 91.6 93.1 92.2 91.1 92.9 91.9 90.8 92.6 91.6 90.4'],
10: ['630 95.4 94.8 94.2 95.3 94.7 94.1 95.2 94.5 93.9 94.9 94.2 93.4 94.6 94.0 93.1 94.3 93.6 92.7'],
11: ['6300 97 96.6 96.1 97 96.6 96.1 96.9 96.5 96.0 96.7 96.2 95.7 96.3 95.8 95.3 — — —', '7100 97.1 96.7 96.2 97.1 96.7 96.2 97.0 96.6 96.1 96.8 96.3 95.8 96.4 95.9 95.3 — — —'],
12: ['250 93.7 92.9 92.1 93.6 92.8 92.0 93.4 92.6 91.8 93.2 92.3 91.3 93.0 92.0 91.0 92.6 91.7 90.6'],
13: ['2500 96.2 95.8 95.3 96.2 95.7 95.3 96.0 95.5 95.0 95.8 95.3 94.8 95.6 95.1 94.5 95.2 94.7 94.0', '2800 96.2 95.8 95.3 96.2 95.7 95.3 96.1 95.6 95.2 95.8 95.3 94.8 95.6 95.1 94.5 95.2 94.7 94.0', '3150 96.3 95.9 95.4 96.2 95.8 95.4 96.1 95.6 95.2 95.9 95.4 94.9 95.7 95.2 94.6 95.3 94.8 94.2'],
14: ['200 93.1 92.3 91.5 93.0 92.1 91.3 92.8 91.9 91.1 92.6 91.6 90.6 92.4 91.4 90.3 92.0 91.0 89.9'],
15: ['2000 95.8 95.4 94.9 95.8 95.3 94.8 95.7 95.2 94.7 95.4 94.9 94.3 95.1 94.5 93.9 94.8 94.3 93.6'],
16: ['200 94.4 93.5 92.7 94.2 93.4 92.5 94.1 93.2 92.3 93.8 92.8 91.8', '220 94.5 93.7 92.9 94.4 93.5 92.7 94.2 93.3 92.5 93.9 93.0 91.9', '250 94.7 93.9 93.1 94.6 93.7 92.9 94.4 93.5 92.7 94.1 93.2 92.2'],
17: ['2000 97.1 96.6 96.2 97.0 96.6 96.1 96.9 96.5 96.0 96.6 96.1 95.6', '2240 97.1 96.7 96.2 97.0 96.6 96.1 97.0 96.5 96.0 96.6 96.1 95.6', '2500 97.2 96.8 96.3 97.1 96.7 96.2 97.0 96.5 96.0 96.7 96.3 95.7'],
18: ['500 95.4 94.8 94.1 95.3 94.7 94.0 95.2 94.5 93.8 94.9 94.2 93.4', '560 95.6 95.0 94.3 95.5 94.9 94.2 95.4 94.7 94.1 95.0 94.3 93.5'],
}
ANCHORS[7].append('220 94.1 93.3 92.5 94.0 93.2 92.3 93.8 93.0 92.1 93.5 92.6 91.5 93.3 92.3 91.2 93.0 92.0 90.8')
ANCHORS[14].append('220 93.3 92.5 91.7 93.2 92.3 91.5 93.0 92.1 91.3 92.7 91.8 90.7 92.5 91.5 90.4 92.1 91.1 90.0')

def main():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == '53a6d2e8098fea9f81adf6a12fe3298707bf6b22cc8c972110aacdcd8a168135', 'Source changed: glyph anchors must be reviewed again'
    reader = PdfReader(SOURCE)
    writer = PdfWriter()
    for page in reader.pages[6:18]:
        page.rotate(90)
        page.transfer_rotation_to_content()
        writer.add_page(page)
    writer.write(WORK / 'rotated.pdf')
    all_rows, mappings, visual = [], {}, []
    with pdfplumber.open(WORK / 'rotated.pdf') as pdf:
        for page_no, page in enumerate(pdf.pages, 7):
            lines = page.extract_text(x_tolerance=1, y_tolerance=2).splitlines()
            if page_no == 11:
                lines = [l[2:] if l.startswith('7 $$) ') else l for l in lines]
            nc = 19 if page_no < 16 else 13
            raw_rows = [l.split()[:nc] for l in lines if len(l.split()) >= nc and len(l.split()[0]) >= 3]
            mapping = {}
            for raw, anchor in zip(raw_rows, ANCHORS[page_no]):
                for a,b in zip(raw,anchor.split()):
                    if b == '—': continue
                    assert len(a)==len(b), (page_no,a,b)
                    for ga, gb in zip(a,b):
                        assert ga not in mapping or mapping[ga]==gb, (page_no,ga,gb,mapping)
                        mapping[ga]=gb
            # Dash uses a different embedded font and can share an extracted code with a digit.
            # All body single-glyph tokens are dashes (visually checked in source pages).
            decoded = []
            for raw in raw_rows:
                dec = ['—' if len(v)==1 else ''.join(mapping.get(c, '?') for c in v) for v in raw]
                decoded.append(dec)
            mappings[page_no] = mapping
            visual.append('PAGE '+str(page_no)+'\n'+'\n'.join(' '.join(r) for r in decoded))
            for i,(raw,dec) in enumerate(zip(raw_rows,decoded)):
                table = {7:1,8:1,9:1 if i<3 else 2,10:2,11:2 if i<12 else 3,12:3,13:3,14:4,15:4,16:5,17:5 if i<5 else 6,18:6}[page_no]
                all_rows.append(dict(table=table,pdf_page=page_no,printed_page=page_no-4,page_row=i+1,raw=raw,values=dec))
    (WORK/'decoded.txt').write_text('\n\n'.join(visual),encoding='utf-8')
    (WORK/'decoded_rows.json').write_text(json.dumps(all_rows,ensure_ascii=False,indent=2),encoding='utf-8')
    (BASE/'evidence/glyph_anchors.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),anchors=ANCHORS,mappings=mappings),ensure_ascii=False,indent=2),encoding='utf-8')
    assert len(all_rows)==204 and not any('?' in str(r['values']) for r in all_rows)
    print('rows:',len(all_rows),'unknown:',sum('?' in str(r['values']) for r in all_rows))
    print((WORK/'decoded.txt').read_text(encoding='utf-8'))

if __name__=='__main__': main()
