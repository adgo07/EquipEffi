"""Reproduce Stage A data and coordinate-level self-check from the user-owned PDF.
Run with the bundled Python. No production assets are read or written.
"""
from pathlib import Path
import csv, hashlib, json, unicodedata
import pdfplumber

ROOT = Path(__file__).resolve().parent
PDF = ROOT.parents[2] / '标准原文/8. GB+19761-2020 通风机能效限定值及能效等级.pdf'
SHA = '4ff8e7dd5b7adb86e33bcce49b60879e8c037f7178bb8f9091f1b5294d40f301'
assert hashlib.sha256(PDF.read_bytes()).hexdigest() == SHA
for d in ['data', 'evidence', '_tmp']:
    (ROOT/d).mkdir(exist_ok=True)
doc = pdfplumber.open(PDF)
tables = {(4,0):doc.pages[3].find_tables()[0], (4,1):doc.pages[3].find_tables()[1],
          (5,0):doc.pages[4].find_tables()[0], (5,1):doc.pages[4].find_tables()[1],
          (6,0):doc.pages[5].find_tables()[0]}
rows=[]
checks=[]

def add(table, page, ti, ri, condition, ns, sizes, values, cols, note=''):
    """Manual source transcription cross-checked against physical PDF cells.
    ri/cols are explicit zero-based pdfplumber geometric row/column positions.
    No nonempty-cell-index addressing is used.
    """
    t=tables[page,ti]
    raw=t.extract()
    for b,size in enumerate(sizes):
        v=values[b*3:b*3+3]
        sheet=f'表{table}'
        wr=5+sum(x['table']==table for x in rows)
        ident=f'T{table}-R{ri+1:02}-B{b+1}'
        # PDF4 and PDF5 continuation rows can share geometric row numbers.
        ident=f'T{table}-P{page}-R{ri+1:02}-B{b+1}'
        row=dict(table=table,id=ident,condition=condition,ns=ns,size=size,g3=v[0],g2=v[1],g1=v[2],
                 metric='ηe (%)' if table==4 else 'ηr (%)',pdf_page=page,printed_page=page-2,
                 source=f'表{table} PDF{page}/印刷{page-2} 几何行{ri+1}',note=note,
                 sheet=sheet,xlsx_row=wr)
        rows.append(row)
        for k,grade in enumerate([3,2,1]):
            ci=cols[b*3+k]
            actual=unicodedata.normalize('NFKC',raw[ri][ci] or '').strip()
            bbox=t.rows[ri].cells[ci]
            expected='—' if v[k] is None else str(v[k])
            assert actual==expected,(ident,grade,actual,expected)
            checks.append(dict(id=ident,grade=grade,pdf_page=page,printed_page=page-2,
                               geometric_row=ri+1,geometric_column=ci+1,
                               bbox_pt=','.join(str(round(x,3)) for x in bbox),
                               xlsx_cell=f'{sheet}!{"EFG"[k]}{wr}',expected=expected,actual=actual,
                               result='MATCH',method='manual transcription vs PDF geometric text; author self-check'))

s1=['2<No≤2.5','2.5<No≤3.5','3.5<No≤4.5','4.5<No≤7','7<No≤10','No>10']
t1=[('1.35≤ψ<1.55','45<ns≤65',[43,58,61,46,59,62,49,60,63,52,61,64,56,64,67,59,65,68]),
('1.05≤ψ<1.35','35<ns≤55',[45,62,65,48,63,66,51,64,67,54,65,68,59,68,71,63,69,72]),
('0.95≤ψ<1.05','10≤ns<20',[49,65,70,52,66,71,55,67,72,58,68,72,62,70,75,65,73,78]),
('0.95≤ψ<1.05','20≤ns<30',[52,66,71,55,67,72,58,68,73,61,69,73,63,71,76,66,75,80])]
for i,(p,n,v) in enumerate(t1): add(1,4,0,i+3,p,n,s1,v,list(range(2,20)), 'ψ末两行共用原文纵向合并源格' if i>=2 else '')
s2=['2<No<5','5≤No<10','No≥10']
t2a=[('5≤ns<15',[62,72,75,65,75,78,69,78,81]),('15≤ns<30',[65,74,77,68,77,80,72,80,83]),('30≤ns<45',[68,76,79,71,79,82,75,82,85])]
for i,(n,v) in enumerate(t2a): add(2,4,1,i+3,'0.85≤ψ<0.95',n,s2,v,list(range(2,11)),'ψ三行共用原文纵向合并源格')
t2b=[('0.75≤ψ<0.85','5≤ns<15',[62,70,75,65,75,78,68,78,81]),
('0.75≤ψ<0.85','15≤ns<30',[65,72,78,68,75,81,70,78,84]),
('0.75≤ψ<0.85','30≤ns<45',[68,75,80,71,78,83,72,81,85]),
('0.65≤ψ<0.75','10≤ns<30',[62,70,77,63,72,79,64,73,83]),
('0.65≤ψ<0.75','30≤ns<50',[65,72,82,66,75,83,67,76,84]),
('0.55≤ψ<0.65','20≤ns<45',[64,74,81,70,76,85,73,80,86]),
('0.55≤ψ<0.65','45≤ns<70',[69,75,82,73,79,86,75,82,87]),
('0.45≤ψ<0.55','10≤ns<30',[67,74,79,69,76,81,71,79,85]),
('0.45≤ψ<0.55','30≤ns<50',[71,77,82,73,79,84,75,81,86]),
('0.45≤ψ<0.55','50≤ns<70',[73,78,83,75,80,85,77,82,87]),
('0.35≤ψ<0.45','50≤ns<65',[70,79,84,72,81,86,75,83,88])]
for i,(p,n,v) in enumerate(t2b): add(2,5,0,i+3,p,n,s2,v,[2,4,6,8,9,10,11,12,13],'ψ依原文合并组；小机号数值格横跨几何子列')
add(2,5,0,16,'0.35≤ψ<0.45','65≤ns<80',['2≤No<3.5','3.5≤No<5','5≤No<10','No≥10'],[63,73,78,66,78,83,73,82,87,76,84,89],list(range(2,14)),'特殊行：No=2包含；前组拆两分支，后两组不拆')
add(2,5,0,17,'0.25≤ψ<0.35','65≤ns<85',s2,[None,None,None,70,79,84,72,81,86],[2,2,2,8,9,10,11,12,13],'小机号为同一横向合并破折号源格；非零值，不跨组补齐')
t3=[('γ<0.3',[55,66,69,58,69,72,60,73,77]),('0.3≤γ<0.4',[59,68,71,61,71,74,63,75,79]),('0.4≤γ<0.55',[61,70,73,64,73,76,66,77,81]),('0.55≤γ<0.75',[63,72,75,67,75,78,69,79,83])]
for i,(p,v) in enumerate(t3): add(3,5,1,i+3,p,'不适用',['2.5≤No<5','5≤No<10','No≥10'],v,list(range(1,10)),'子午加速轴流：轮毂比按轮毂出口直径计算')
s4=['No≤2','2<No≤2.5','2.5<No≤3.5','3.5<No≤4.5','No>4.5']
t4=[[36,43,46,37,50,54,39,50,53,43,55,60,50,60,63],
[35,42,45,35,49,53,38,49,52,42,54,59,49,59,62],
[35,43,46,36,49,52,38,49,52,42,55,59,49,59,62],
[34,42,45,35,48,51,37,48,51,41,54,58,48,58,61],
[33,43,46,35,49,52,37,48,51,41,55,58,48,58,61],
[32,42,45,34,48,51,36,47,50,40,54,57,47,57,61],
[33,42,45,35,48,51,37,47,51,41,54,57,47,57,61],
[31,41,44,33,47,50,35,46,50,39,53,56,46,56,60],
[32,41,44,34,47,50,36,47,51,40,53,56,46,56,60],
[30,40,43,32,46,49,34,46,50,38,52,55,45,55,59]]
for i,v in enumerate(t4): add(4,6,0,i+3,['1.0≤ψ<1.1','1.1≤ψ<1.2','1.2≤ψ<1.3','1.3≤ψ<1.4','1.4≤ψ'][i//2], 'ns>50' if i%2==0 else '30<ns≤50',s4,v,list(range(2,17)),'外转子直联前向多翼；排除单相及三相多速式、三相六极及以上')
assert len(rows)==135 and len(checks)==405
assert len({x['id'] for x in rows})==135
for r in rows:
    assert r['g3'] is None or r['g3']<=r['g2']<=r['g1']
for name,data in [('table_values',rows),('numeric_self_check',checks)]:
    folder='data' if name=='table_values' else 'evidence'
    with (ROOT/folder/f'{name}.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
(ROOT/'data/table_values.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
summary={'source_sha256':SHA,'pdf_pages':8,'tables':4,'branch_rows':135,'numeric_values':402,
         'dash_source_cells':1,'dash_expanded_slots':3,'self_check_match':405,'self_check_fail':0,
         'independent_review':'NOT_RUN','by_table':{str(t):sum(x['table']==t for x in rows) for t in range(1,5)}}
(ROOT/'evidence/check_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
for i,page in enumerate(doc.pages):
    (ROOT/f'_tmp/page_{i+1:02}.txt').write_text(page.extract_text() or '',encoding='utf-8')
    page.to_image(resolution=120).save(ROOT/f'_tmp/page_{i+1:02}.png')
print(json.dumps(summary,ensure_ascii=False))
