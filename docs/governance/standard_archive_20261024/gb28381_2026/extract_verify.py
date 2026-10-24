"""Stage A source extraction; no runtime evaluator. Run with bundled Python.

Reads only the owner-provided PDF; all outputs stay beside this script.
Two extraction paths compare source tokens, not independent acceptance.
"""
from pathlib import Path
import csv, hashlib, json, re
from collections import Counter
import pypdf
import pdfplumber

ROOT = Path(__file__).resolve().parent
PDF = ROOT.parents[2] / '标准原文/9. GB+28381-2026 鼓风机能效限定值及能效等级.pdf'
SHA = '64a8ef7934933eff49874c5f121db5a1f32f69ff1a16295cd1abe4d740b80d35'
assert hashlib.sha256(PDF.read_bytes()).hexdigest() == SHA
PAGES = {7:[1],8:[1,2],9:[2,3],10:[3,4],11:[4],12:[4],13:[4,5],14:[5],15:[5],16:[5],17:[5,6],18:[6],19:[6]}
NAMES = {1:'机械支撑离心',2:'轴流',3:'悬浮支撑离心',4:'单级正压罗茨',5:'单级负压罗茨',6:'螺杆'}
PRESSURES = {4:['9.8','19.6','29.4','39.2','49.0','58.8','68.6','78.4','88.2','98.0'],5:['9.8','14.7','19.6','24.5','29.4','34.3','39.2','44.1','49.0'],6:['39.2','49.0','58.8','68.6','78.4','88.2','98.0','127.4','147.0','166.6','186.2','205.8','225.4','245.0']}
def clean(s): return re.sub(r'\s+', '', s or '')
def col(n):
    out=''
    while n: n,r=divmod(n-1,26); out=chr(65+r)+out
    return out

# Path 1: line-oriented pypdf; strict shape and explicit table markers.
rows={i:[] for i in range(1,7)}
for page_no, page in enumerate(pypdf.PdfReader(PDF).pages,1):
    if page_no not in PAGES: continue
    table=None; flow=None
    for line in page.extract_text().splitlines():
        line=line.strip()
        m=re.match(r'表\s+([1-6])\s',line)
        if m: table=int(m[1]); flow=None; continue
        if table is None: continue
        tokens=line.split()
        if table<=3 and len(tokens)==4 and all(re.fullmatch(r'\d+(?:\.\d+)?',v) for v in tokens):
            rows[table].append({'flow':tokens[0],'grade':None,'tokens':tokens[1:],'page':page_no})
        elif table>=4:
            if len(tokens)==1 and re.fullmatch(r'\d+(?:\.\d+)?',line): flow=line
            elif len(tokens)==len(PRESSURES[table])+1 and tokens[0] in ['1','2','3']:
                assert flow is not None
                assert all(re.fullmatch(r'\d+(?:\.\d+)?|—',v) for v in tokens[1:])
                rows[table].append({'flow':flow,'grade':int(tokens[0]),'tokens':tokens[1:],'page':page_no})

# Path 2: pdfplumber geometric ruled-cell extraction, retaining merged parents.
geometric={i:[] for i in range(1,7)}
with pdfplumber.open(PDF) as document:
    for page_no, table_ids in PAGES.items():
        tables=document.pages[page_no-1].extract_tables()
        assert len(tables)==len(table_ids),(page_no,len(tables))
        for table, data in zip(table_ids,tables):
            if table>=4: assert [clean(x) for x in data[1][2:]]==PRESSURES[table]
            flow=None
            for source_row, raw in enumerate(data,1):
                vals=[clean(x) for x in raw]
                if table<=3:
                    if len(vals)!=4 or not re.fullmatch(r'\d+',vals[0]): continue
                    flow=vals[0]; grade=None; tokens=vals[1:]
                else:
                    if vals[1] not in ['1','2','3']: continue
                    if vals[0]: flow=vals[0]
                    grade=int(vals[1]); tokens=vals[2:]
                geometric[table].append({'flow':flow,'grade':grade,'tokens':tokens,'page':page_no,'source_row':source_row})

audit=[]; summary=[]
for table in rows:
    assert len(rows[table])==len(geometric[table]),table
    assert len(rows[table])=={1:34,2:24,3:30,4:96,5:96,6:63}[table]
    for idx,(a,b) in enumerate(zip(rows[table],geometric[table]),5):
        assert a=={k:b[k] for k in a},(table,idx,a,b)
        a['source_row']=b['source_row']; a['xlsx_row']=idx
        for j,token in enumerate(a['tokens']):
            grade=j+1 if table<=3 else a['grade']
            pressure='' if table<=3 else PRESSURES[table][j]
            xcol=j+2 if table<=3 else j+3
            audit.append({'table':table,'branch':NAMES[table],'flow':a['flow'],'flow_unit':'m3/h' if table<=3 else 'm3/min','grade':grade,'pressure_kPa':pressure,'source_token':token,'pdf_page':a['page'],'printed_page':a['page']-4,'pdf_grid_row':a['source_row'],'pdf_grid_col':xcol,'xlsx_cell':f'表{table}!{col(xcol)}{idx}','pypdf_token':token,'pdfplumber_token':b['tokens'][j],'two_extractor_check':'MATCH','independent_acceptance':'NOT_RUN'})
    vals=[v for r in rows[table] for v in r['tokens']]
    summary.append({'table':table,'branch':NAMES[table],'flow_points':len(set(r['flow'] for r in rows[table])),'rows':len(rows[table]),'slots':len(vals),'numeric':sum(v!='—' for v in vals),'dashes':vals.count('—'),'pages':sorted(set(r['page'] for r in rows[table]))})
with (ROOT/'CELL_AUDIT.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
payload={'source_sha256':SHA,'tables':[{'id':i,'name':NAMES[i],'pressures':PRESSURES.get(i,[]),'rows':rows[i]} for i in rows],'summary':summary}
(ROOT/'table_values.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(ROOT/'_tmp').mkdir(exist_ok=True)
(ROOT/'_tmp/extraction_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(summary,ensure_ascii=False))
print('TOTAL',len(audit),'slots;',sum(x['numeric'] for x in summary),'numbers;',sum(x['dashes'] for x in summary),'dashes; exact tokens MATCH')
