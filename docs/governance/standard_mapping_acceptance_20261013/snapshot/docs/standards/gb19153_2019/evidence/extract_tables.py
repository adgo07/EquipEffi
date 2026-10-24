"""Stage A only: geometric extraction from the owner's read-only PDF. No production data."""
from pathlib import Path
import csv, json, re, unicodedata, hashlib
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
(ROOT/'tmp').mkdir(exist_ok=True)
PDF = ROOT.parents[2] / '标准原文' / '5. GB 19153-2019 容积式空气压缩机能效限定值及能效等级.pdf'
def norm(s):
    return unicodedata.normalize('NFKC', s or '').replace('犘','P').strip()
def compact(s): return re.sub(r'\s+', '', norm(s))
PLAN = [(5,0,1),(6,0,1),(7,0,1),(8,0,2),(9,0,2),(10,0,2),(10,1,3),(11,0,3),(12,0,3),(12,1,4),(13,0,4),(14,0,5),(15,0,6)]
records=[]
source=[]
structures=[]
with pdfplumber.open(PDF) as doc:
    for pn, ti, tn in PLAN:
        p=doc.pages[pn-1]; t=p.find_tables()[ti]; extracted=t.extract()
        xs=sorted({v for b in t.cells for v in [b[0],b[2]]})
        ys=sorted({v for b in t.cells for v in [b[1],b[3]]})
        # Use a point at each atomic grid row/column centre to resolve the original merged cell.
        cache={}
        for ri,row in enumerate(t.rows):
            for ci,b in enumerate(row.cells):
                if b: cache[b]=(compact(extracted[ri][ci]),ri+1,ci+1)
        def source_at(ri,ci):
            y=(ys[ri]+ys[ri+1])/2; x=(xs[ci]+xs[ci+1])/2
            matches=[b for b in t.cells if b[0] <= x < b[2] and b[1] <= y < b[3]]
            assert len(matches)==1,(pn,ri,ci,matches)
            b=matches[0]; raw,sr,sc=cache[b]
            return raw, sr, sc, b
        gradecol=2 if tn in [5,6] else 1
        start=gradecol+1
        pressures=([.3,.5,.7,.8,1,1.25] if tn<3 else [.25,.4,.5,.7,.8,1,1.25,1.4] if tn==3 else [.4,.5,.7,.8,1,1.25,1.4] if tn==4 else [.2,.25,.4,.5,.7,.8,1])
        n=0
        for ri,row in enumerate(t.rows):
            grade=source_at(ri,gradecol)[0]
            if grade not in ['1','2','3']: continue
            power=float(source_at(ri,0)[0]); actual=source_at(ri,1)[0] if tn in [5,6] else ''
            for ci in range(start,len(t.columns)):
                raw,sr,sc,b=source_at(ri,ci)
                pressure=pressures[(ci-start)//2 if tn<3 else ci-start]
                cooling=('风冷' if (ci-start)%2==0 else '液冷') if tn<3 else '风冷' if tn==3 else '表内非括号值' if tn==4 else '表内未分冷却'
                vals = re.findall(r'\d+\.\d+',raw)
                if raw=='—': vals=[None]
                else: assert len(vals) in [1,2],(pn,ri,ci,raw)
                for vi,v in enumerate(vals):
                    branch='液冷' if vi==1 else cooling
                    record={'table':tn,'power_kw':power,'actual_input_range_kw':actual,'grade':int(grade),'pressure_gauge_mpa':pressure,'cooling':branch,'value':None if v is None else float(v),'source_text':raw,'value_text':v or '—','pdf_page':pn,'printed_page':pn-2,'source_row':sr,'source_col':sc,'bbox':','.join(f'{x:.3f}' for x in b),'source_kind':'源表破折号' if v is None else '方括号液冷值' if vi else '数值','atomic_row':ri+1,'atomic_col':ci+1}
                    records.append(record); n+=1
        structures.append({'table':tn,'pdf_page':pn,'grid_rows':len(t.rows),'grid_cols':len(t.columns),'expanded_records':n})
    weights=doc.pages[16].find_tables()[0].extract()[1:]
    weights=[[float(compact(a).replace('%',''))/100,float(compact(b).replace('%',''))/100] for a,b in weights]

for tn in range(1,7):
    rows=[r for r in records if r['table']==tn]
    for idx,r in enumerate(rows,6):
        r['xlsx_cell']=f'表{tn}!G{idx}'
    assert len({(r['power_kw'],r['grade'],r['pressure_gauge_mpa'],r['cooling']) for r in rows})==len(rows)

out={'pdf_sha256':hashlib.sha256(PDF.read_bytes()).hexdigest(),'records':records,'weights':weights,'structures':structures}
(ROOT/'tmp/table_data.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
with (ROOT/'evidence/source_cells.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
print(json.dumps({'total':len(records),'numeric':sum(r['value'] is not None for r in records),'by_table':{i:sum(r['table']==i for r in records) for i in range(1,7)},'structures':structures},ensure_ascii=False))
