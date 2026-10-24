"""Recorded visual samples read by the executing agent from PDF page images, 2026-10-13.
Comparison is reproducible; selecting/reading original page images is not automated.
"""
from pathlib import Path
import csv, json
from openpyxl import load_workbook
B=Path(__file__).resolve().parent
samples={
1:[(1,1,'51.0'),(1,5,'54.0'),(2,2,'68.0'),(5,4,'73.0'),(8,5,'71.5')],
2:[(1,1,'50.5'),(2,1,'49.5'),(5,3,'69.5'),(10,1,'70.0'),(16,5,'70.5')],
3:[(1,1,'51.5'),(2,2,'68.0'),(2,3,'69.0'),(5,5,'74.5'),(8,5,'72.0')],
4:[(1,1,'51.0'),(3,2,'68.5'),(13,5,'73.0'),(16,1,'68.0'),(16,5,'71.0')],
5:[(1,1,'55.0'),(3,5,'76.0'),(4,1,'73.5'),(5,5,'78.0'),(8,5,'75.5')],
6:[(2,1,'54.0'),(4,2,'71.0'),(8,1,'72.5'),(10,1,'73.0'),(16,5,'74.5')],
7:[(1,1,'55.5'),(2,2,'72.5'),(2,3,'73.5'),(5,5,'78.5'),(8,5,'76.0')],
8:[(1,1,'55.0'),(3,2,'72.0'),(13,5,'76.5'),(16,1,'70.0'),(16,5,'75.0')]}
source={x['source_id']:x for x in csv.DictReader((B/'evidence/source_cells.csv').open(encoding='utf-8-sig'))}
wb=load_workbook(B/'data/GB28381_2012_TABLES.xlsx',data_only=False)
rows=[]
for t,checks in samples.items():
    for r,c,v in checks:
        key=f'GB28381-2012-T{t}-R{r:02}-C{c}'
        s=source[key]; actual=wb[s['xlsx_sheet']][s['xlsx_cell']].value
        rows.append({**s,'visually_read_lexical':v,'xlsx_actual':actual,'result':'PASS' if actual==float(v) and s['value_lexical']==v else 'FAIL','reviewer':'执行Agent自核，非独立验收','date':'2026-10-13'})
with (B/'evidence/visual_spot_checks.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
assert len(rows)==40 and all(r['result']=='PASS' for r in rows)
print(json.dumps({'visual_samples':40,'pass':40,'fail':0,'remaining_not_independently_visually_checked':440}))
