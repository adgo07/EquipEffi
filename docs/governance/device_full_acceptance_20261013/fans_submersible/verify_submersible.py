import openpyxl,csv
from pathlib import Path
# Visual transcription of main standard PDF4-8; repeated symbols reflect visually verified merged spans.
raw={1:'''2 3 2.5 2 1.5 2.5 3
— 3.5 3 2.5 2 3 3.5
— 3.5 3 2.5 2.5 3.5 3.5
1 1.5 1.3 1 .8 1.3 1.5
— 1.8 1.5 1.3 1 1.5 1.8
— 1.8 1.5 1.3 1.3 1.8 1.8''',2:'''3 1.5 2.5 2
3 2 2 2.5
2.5 1.5 2 2
2 1 1.5 1.5
1.5 .8 1.3 1
1.5 1 1 1.3
1.3 .8 1 1
1 .5 .8 .8''',3:'''2 — — 4
2.5 3 3.5 4.5
2.5 3.5 4 5
— 4 4.5 5.5
— 4 4.5 5
— 3.5 4 4.5
1 — — 2
1.3 1.5 1.8 2.3
1.3 1.8 2 2.5
— 2 2.3 2.8
— 2 2.3 2.5
— 1.8 2 2.3''',4:'''2 3 2.5 3.5
2.5 3 3 —
3 3.5 — —
2.5 3 — —
2 2.5 — —
1 1.5 1.3 1.8
1.3 1.5 1.5 —
1.5 1.8 — —
1.3 1.5 — —
1 1.3 — —''',5:'1B 1U 2B 2U 2B 2U',6:'''3.5 3
4 3.5
4.5 4
4.5 3.5
3.5 3
1.8 1.5
2.3 1.8
2.3 2
2 1.8
1.8 1.5'''}
w=openpyxl.load_workbook('docs/standards/gb32030_2022/data/GB32030_2022_表值映射.xlsx');records=[]
for n,txt in raw.items():
 vals=txt.split();s=w[f'表{n}'];cols={1:7,2:4,3:4,4:4,5:1,6:2}[n];rows={1:9,2:12,3:18,4:15,5:6,6:15}[n]
 if n!=5: vals+=['-Δηgr' if n in [4,6] else '-Δη']*(rows//3*cols)
 cells=[s.cell(r,c) for r in range(6,6+rows) for c in range(6,6+cols)];assert len(cells)==len(vals)
 for val,c in zip(vals,cells):
  eq=str(c.value)==val
  try:eq=float(c.value)==float(val)
  except (TypeError,ValueError):pass
  records.append(dict(table=s.title,cell=c.coordinate,visual_source_value=val,workbook_value=c.value,match=eq))
p=Path('docs/governance/device_full_acceptance_20261013/fans_submersible/gb32030_2022/independent_visual_cells.csv')
with p.open('w',encoding='utf-8-sig',newline='') as f:
 wr=csv.DictWriter(f,fieldnames=records[0]);wr.writeheader();wr.writerows(records)
print(len(records),[r for r in records if not r['match']])
