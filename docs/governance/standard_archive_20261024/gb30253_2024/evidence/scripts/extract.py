import json, hashlib
from pathlib import Path
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from fontTools.cffLib import CFFFontSet
from fontTools.pens.recordingPen import RecordingPen
import pdfplumber

ROOT=Path(__file__).resolve().parents[2]/'tmp'
ROOT.mkdir(exist_ok=True)
original=ROOT.parent.parents[2]/'标准原文/4. GB 30253-2024 永磁同步电动机能效限定值及能效等级.pdf'
assert hashlib.sha256(original.read_bytes()).hexdigest()=='6e6878b22b125c86efb31e6e198b941b15bb25ae8e79a63993a9361c914f3053'
reader=PdfReader(original); writer=PdfWriter()
for pi,page in enumerate(reader.pages): writer.add_page(page.rotate(90) if pi>=6 else page)
writer.write(ROOT/'rotated.pdf')
src=ROOT/'rotated.pdf'
r=PdfReader(src)
def fonts(page):
    for obj in page['/Resources']['/XObject'].values():
        obj=obj.get_object()
        if obj.get('/Subtype')=='/Form' and '/Font' in obj.get('/Resources',{}):
            return obj['/Resources']['/Font']
    return page['/Resources']['/Font']
def glyphs(f):
    f=f.get_object()
    if f.get('/Subtype')!='/Type1': return {}
    c=CFFFontSet(); c.decompile(BytesIO(f['/FontDescriptor']['/FontFile3'].get_data()),None)
    top=c.topDictIndex[0]; out={}; code=0
    for v in f['/Encoding']['/Differences']:
        if isinstance(v,int): code=v;continue
        pen=RecordingPen(); top.CharStrings[str(v)[1:]].draw(pen)
        out[code]=hashlib.sha256(repr(pen.value).encode()).hexdigest();code+=1
    return out
seed=glyphs(fonts(r.pages[6])['/F11'])
truth=dict(zip(range(33,47),'kW%1234680.597'))
byhash={h:truth[k] for k,h in seed.items()}
maps={}; hashes={}
for pi,p in enumerate(r.pages[6:],7):
    for f in fonts(p).values():
        name=str(f.get_object().get('/BaseFont',''))[1:]
        gs=glyphs(f)
        maps[(pi,name)]={k:byhash.get(h) for k,h in gs.items()}
        hashes[(pi,name)]=gs
# pdfminer StandardEncoding returns curly quote for code39 etc.
codes={'’':39,'‘':96,'“':170,'”':186}
def decode(c):
    ch=c['text']; code=codes.get(ch,ord(ch) if len(ch)==1 else -1)
    return maps.get((c['page_number'],c['fontname']),{}).get(code) or ch
doc=pdfplumber.open(src)
out=[]
for idx in range(6,51):
    p=doc.pages[idx]
    ts=p.find_tables()
    for ti,t in enumerate(ts):
        rows=[]; boxes=[]
        for row in t.rows:
            rr=[];bb=[]
            for box in row.cells:
                if box is None: rr.append(None);bb.append(None);continue
                x0,y0,x1,y1=box
                chars=[c for c in p.chars if x0<=(c['x0']+c['x1'])/2<x1 and y0<=(c['top']+c['bottom'])/2<y1]
                chars.sort(key=lambda c:(round(c['top']/3)*3,c['x0']))
                rr.append(''.join(decode(c) for c in chars));bb.append(list(box))
            rows.append(rr);boxes.append(bb)
        out.append({'page':idx+1,'part':ti+1,'rows':rows,'boxes':boxes})
    print(idx+1,[(len(t.rows),len(t.columns)) for t in ts],flush=True)
(ROOT/'tables.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'font_maps.json').write_text(json.dumps({str(k):v for k,v in maps.items()},ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'tables.txt').write_text('\n\n'.join(f"PAGE {t['page']} PART {t['part']}\n"+'\n'.join(' | '.join(x or '_' for x in row) for row in t['rows']) for t in out),encoding='utf-8')
