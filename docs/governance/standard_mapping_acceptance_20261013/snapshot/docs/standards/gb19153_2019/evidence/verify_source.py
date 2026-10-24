"""Second PDF text engine, with original source-cell bounding boxes; not independent acceptance."""
from pathlib import Path
import json, csv, re, unicodedata
import pypdfium2 as pdfium
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'tmp/table_data.json').read_text(encoding='utf-8'))
pdf=pdfium.PdfDocument(str(ROOT.parents[2]/'标准原文'/'5. GB 19153-2019 容积式空气压缩机能效限定值及能效等级.pdf'))
pages={};cache={};audit=[]
for r in data['records']:
    pn=r['pdf_page'];box=r['bbox'];key=(pn,box)
    if pn not in pages: pages[pn]=(pdf[pn-1],pdf[pn-1].get_textpage())
    p,tp=pages[pn]
    if key not in cache:
        x0,y0,x1,y1=map(float,box.split(','));h=p.get_height()
        s=tp.get_text_bounded(x0+.1,h-y1+.1,x1-.1,h-y0-.1)
        s=re.sub(r'\s+','',unicodedata.normalize('NFKC',s))
        cache[key]=s
    s=cache[key]; vals=re.findall(r'\d+\.\d+',s)
    observed=vals[1 if r['source_kind']=='方括号液冷值' else 0] if vals else '—' if '—' in s else s
    audit.append({'xlsx_cell':r['xlsx_cell'],'table':r['table'],'power_kw':r['power_kw'],'pressure_mpa':r['pressure_gauge_mpa'],'grade':r['grade'],'cooling':r['cooling'],'pdf_page':pn,'printed_page':pn-2,'source_row':r['source_row'],'source_col':r['source_col'],'bbox':box,'pdfplumber_text':r['value_text'],'pdfium_text':observed,'result':'MATCH' if r['value_text']==observed else 'MISMATCH','method':'两种PDF文本引擎逐源格比较；非独立人工验收'})
with (ROOT/'evidence/numeric_crosscheck.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
bad=[r for r in audit if r['result']!='MATCH']
print(json.dumps({'checks':len(audit),'mismatches':len(bad),'first_mismatches':bad[:8]},ensure_ascii=False))
assert not bad
