from pathlib import Path
import pymupdf as fitz,openpyxl,csv,json,re
out=Path('docs/governance/device_full_acceptance_20261013/fans_submersible/gb28381_2026');p=next(Path('标准原文').glob('*28381-2026*.pdf'));d=fitz.open(p);w=openpyxl.load_workbook('docs/standards/gb28381_2026/GB28381_2026_TABLE_VALUES.xlsx')
# Page/table order independently established by source images. No executor CSV/JSON imported.
layout={7:[1],8:[1,2],9:[2,3],10:[3,4],11:[4],12:[4],13:[4,5],14:[5],15:[5],16:[5],17:[5,6],18:[6],19:[6]}
rows={i:5 for i in range(1,7)};records=[];audit=[]
for pg,ns in layout.items():
 tabs=d[pg-1].find_tables().tables;assert len(tabs)==len(ns),(pg,len(tabs),ns)
 for tab,n in zip(tabs,ns):
  grid=tab.extract();prevq=None
  for gr,row in enumerate(grid):
   good=(len(row)==4 and re.fullmatch(r'[\d\s.]+',row[0] or '') and re.fullmatch(r'\d+\.\d+',row[1] or '')) if n<4 else (len(row)>4 and row[1] in ['1','2','3'])
   if not good:continue
   rr=rows[n];s=w[f'表{n}'];start=1 if n<4 else 2
   if row[0] is not None:prevq=row[0].replace(' ','').replace('\n','')
   assert float(prevq)==float(s.cell(rr,1).value),(pg,n,rr,prevq,s.cell(rr,1).value)
   if n>=4:assert int(row[1])==s.cell(rr,2).value
   for j,v in enumerate(row[start:],start+1):
    expected=(v or '').replace(' ','').replace('\n','');actual=s.cell(rr,j).value
    eq=expected==str(actual)
    try:eq=float(expected)==float(actual)
    except (TypeError,ValueError):pass
    records.append(dict(table=n,pdf_page=pg,source_grid_row=gr+1,source_column=j,workbook_cell=f'{s.title}!{s.cell(rr,j).coordinate}',source_token=expected,workbook_value=actual,match=eq,method='independent_PyMuPDF_grid_plus_source_page_visual_review'))
   audit.append(dict(table=n,pdf_page=pg,source_grid_row=gr+1,workbook_row=rr,q=prevq,grade=row[1] if n>=4 else '1/2/3',source_values=' '.join(str(v) for v in row[start:])))
   rows[n]+=1
with (out/'independent_all_cells.csv').open('w',encoding='utf-8-sig',newline='') as f:
 wr=csv.DictWriter(f,fieldnames=records[0]);wr.writeheader();wr.writerows(records)
(out/'source_rows.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(rows,len(records),'mismatches',[r for r in records if not r['match']])
