"""Explicit visual transcription of GB32030-2022 tables, not a calculator."""
from pathlib import Path
import json,csv
O=Path(__file__).resolve().parent
# Values are percentage-point increments. None is a printed dash, not zero.
T=[]
def add(n,name,branches,bounds,g1,g2,base,pages,merges):
    rows=[]
    for grade,values in [(1,g1),(2,g2),(3,[['-Δη']*len(branches) for _ in bounds])]:
        for j,(lo,hi) in enumerate(bounds):
            rows.append([grade,lo,'>' if lo is not None else '',hi,'≤' if hi is not None else '',*values[j]])
    T.append(dict(n=n,name=name,branches=branches,rows=rows,base=base,pages=pages,merges=merges))
add(1,'小型潜水电泵',['QDX和QD','QX和Q','QY','QS','QXR','QXL','其他'],[(None,3),(3,11),(11,22)],
 [[2,3,2.5,2,1.5,2.5,3],[None,3.5,3,2.5,2,3,3.5],[None,3.5,3,2.5,2.5,3.5,3.5]],
 [[1,1.5,1.3,1,.8,1.3,1.5],[None,1.8,1.5,1.3,1,1.5,1.8],[None,1.8,1.5,1.3,1.3,1.8,1.8]],'ηDB',{1:4,2:4,3:4},
 [[1,2,2,3],[1,3,2,3],[1,4,2,3],[1,7,2,3],[2,2,2,3],[2,3,2,3],[2,4,2,3],[2,7,2,3]]+[[3,c,1,3] for c in range(1,8)])
add(2,'大中型潜水电泵',['离心式','轴流式','混流式（蜗壳）','混流式（导叶）'],[(22,100),(100,185),(185,355),(355,None)],
 [[3,1.5,2.5,2],[3,2,2,2.5],[2.5,1.5,2,2],[2,1,1.5,1.5]],
 [[1.5,.8,1.3,1],[1.5,1,1,1.3],[1.3,.8,1,1],[1,.5,.8,.8]],'ηDB',{1:4,2:4,3:5},
 [[1,1,1,2],[2,1,1,2],[1,3,2,3],[2,3,2,3]]+[[3,c,1,4] for c in range(1,5)])
add(3,'污水污物潜水电泵',['旋流式','轴流式','混流式','其他式'],[(None,7.5),(7.5,22),(22,100),(100,185),(185,355),(355,None)],
 [[2,None,None,4],[2.5,3,3.5,4.5],[2.5,3.5,4,5],[None,4,4.5,5.5],[None,4,4.5,5],[None,3.5,4,4.5]],
 [[1,None,None,2],[1.3,1.5,1.8,2.3],[1.3,1.8,2,2.5],[None,2,2.3,2.8],[None,2,2.3,2.5],[None,1.8,2,2.3]],'ηDB',{1:5,2:5,3:6},
 [[g,1,2,3] for g in [1,2]]+[[g,c,4,5] for g in [1,2] for c in [2,3]]+[[3,c,1,6] for c in range(1,5)])
add(4,'井用潜水电泵',['充水式','充油式','屏蔽式','单相'],[(None,11),(11,30),(30,100),(100,185),(185,None)],
 [[2,3,2.5,3.5],[2.5,3,3,None],[3,3.5,None,None],[2.5,3,None,None],[2,2.5,None,None]],
 [[1,1.5,1.3,1.8],[1.3,1.5,1.5,None],[1.5,1.8,None,None],[1.3,1.5,None,None],[1,1.3,None,None]],'ηgr',{1:6,2:6,3:6},
 [[g,2,1,2] for g in [1,2]]+[[3,c,1,5] for c in range(1,5)])
add(6,'混流潜水电泵',['蜗壳式','导叶式'],[(None,22),(22,100),(100,185),(185,355),(355,None)],
 [[3.5,3],[4,3.5],[4.5,4],[4.5,3.5],[3.5,3]],
 [[1.8,1.5],[2.3,1.8],[2.3,2],[2,1.8],[1.8,1.5]],'ηgr',{1:7,2:8,3:8},
 [[1,1,3,4],[2,1,2,3]]+[[3,c,1,5] for c in [1,2]])
records=[]
for t in T:
    count=len(t['rows'])//3
    for i,row in enumerate(t['rows']):
        g,lo,lop,hi,hop,*vals=row;j=i%count+1
        for c,(branch,v) in enumerate(zip(t['branches'],vals),1):
            span=next(((a,b) for grade,col,a,b in t['merges'] if grade==g and col==c and a<=j<=b),(j,j))
            source=f"T{t['n']}-G{g}-C{c}-R{span[0]}:{span[1]}"
            expression='—' if v is None else (t['base']+('-Δηgr' if t['base']=='ηgr' else '-Δη') if g==3 else f"{t['base']}+{v:.1f}")
            records.append(dict(table=t['n'],grade=g,branch=branch,lower_kw=lo,lower_operator=lop,upper_kw=hi,upper_operator=hop,
                value_kind='PRINTED_DASH' if v is None else 'BASE_MINUS_TOLERANCE' if g==3 else 'BASE_PLUS_INCREMENT',
                increment_pp=v if isinstance(v,(int,float)) else None,expression=expression,
                source_cell=source,source_row=j,source_span=f'{span[0]}:{span[1]}',pdf_page=t['pages'][g],printed_page=t['pages'][g]-2,
                official_pdf_page=t['pages'][g]+2,xlsx_sheet=f"表{t['n']}",xlsx_cell=f'{chr(69+c)}{i+6}',
                self_check='VISUAL_TRANSCRIPTION_SELF_CHECK',independent_check='NOT_RUN'))
T.insert(4,dict(n=5,name='井用流量扬程容差等级',base='GB/T12785-2014 表7',branches=['容差系数等级'],rows=[
 [1,None,'',100,'≤','1B'],[1,100,'>',None,'','1U'],[2,None,'',100,'≤','2B'],[2,100,'>',None,'','2U'],[3,None,'',100,'≤','2B'],[3,100,'>',None,'','2U']],pages={1:7,2:7,3:7},merges=[]))
for i,r in enumerate(T[4]['rows']):
 records.append(dict(table=5,grade=r[0],branch='流量及扬程',lower_kw=r[1],lower_operator=r[2],upper_kw=r[3],upper_operator=r[4],value_kind='REFERENCE_CLASS',increment_pp=None,expression=r[5],source_cell=f'T5-R{i+1}',source_row=i+1,source_span=f'{i+1}:{i+1}',pdf_page=7,printed_page=5,official_pdf_page=9,xlsx_sheet='表5',xlsx_cell=f'F{i+6}',self_check='VISUAL_TRANSCRIPTION_SELF_CHECK',independent_check='NOT_RUN'))
(O/'data/tables.json').write_text(json.dumps(T,ensure_ascii=False,indent=2),encoding='utf8')
with (O/'evidence/cell_trace.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
from collections import Counter
summary=dict(logical_cells=len(records),value_kinds=dict(Counter(r['value_kind'] for r in records)),physical_source_cells=len(set(r['source_cell'] for r in records)),tables={str(t['n']):dict(rows=len(t['rows']),branches=len(t['branches'])) for t in T})
(O/'evidence/structure_counts.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf8')
print(summary)
