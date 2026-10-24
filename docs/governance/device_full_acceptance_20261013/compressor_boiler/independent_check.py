from pathlib import Path
import csv,json,re,unicodedata,hashlib
import pdfplumber,openpyxl
OUT=Path(__file__).parent; ROOT=Path.cwd()
def norm(x): return re.sub(r'\s+','',unicodedata.normalize('NFKC',x or '')).replace('犘','P')
audit=[]; failures=[]
pdf=next((ROOT/'标准原文').glob('5. GB 19153*')); wb=openpyxl.load_workbook(ROOT/'docs/standards/gb19153_2019/data/GB19153_2019_标准表值.xlsx',data_only=False)
# Independent fresh geometric PDF reconstruction; no author CSV/JSON imported.
with pdfplumber.open(pdf) as doc:
 for page_no,table_idx,number in [(5,0,1),(6,0,1),(7,0,1),(8,0,2),(9,0,2),(10,0,2),(10,1,3),(11,0,3),(12,0,3),(12,1,4),(13,0,4),(14,0,5),(15,0,6)]:
  t=doc.pages[page_no-1].find_tables()[table_idx]; ext=t.extract(); cells={bbox:norm(ext[r][c]) for r,row in enumerate(t.rows) for c,bbox in enumerate(row.cells) if bbox}
  xs=sorted(set(v for b in cells for v in (b[0],b[2]))); ys=sorted(set(v for b in cells for v in (b[1],b[3])))
  def at(r,c):
   x=(xs[c]+xs[c+1])/2;y=(ys[r]+ys[r+1])/2
   hits=[(b,s) for b,s in cells.items() if b[0]<=x<b[2] and b[1]<=y<b[3]]
   assert len(hits)==1
   return hits[0]
  gc=2 if number>=5 else 1; start=gc+1
  # derive pressure headers by locating numeric pressure row from PDF, rather than implementation constants
  head=None
  for r in range(len(ys)-1):
   seq=[at(r,c)[1] for c in range(start,len(xs)-1)]
   if all(re.fullmatch(r'0\.\d+|1(?:\.\d+)?',s) for s in seq): head=seq;break
  assert head is not None,(page_no,'pressure headers')
  lookup={}
  for row in wb[f'表{number}'].iter_rows(min_row=6):
   key=(float(row[0].value),int(row[2].value),float(row[3].value),row[4].value)
   assert key not in lookup
   lookup[key]=row
  for r in range(len(ys)-1):
   if at(r,gc)[1] not in ['1','2','3']:continue
   p=float(at(r,0)[1]);g=int(at(r,gc)[1]);actual=at(r,1)[1] if gc==2 else ''
   for c in range(start,len(xs)-1):
    bbox,raw=at(r,c); pressure=float(head[c-start]); vals=re.findall(r'\d+\.\d+',raw) if raw!='—' else ['—']
    assert vals and len(vals)<=2,(page_no,r,c,raw)
    for ix,val in enumerate(vals):
     cooling=('风冷' if (c-start)%2==0 else '液冷') if number<3 else '风冷' if number==3 else ('液冷' if ix else '表内非括号值') if number==4 else '表内未分冷却'
     key=(p,g,pressure,cooling);row=lookup[key];target=row[6].value
     ok=(target=='—' if val=='—' else float(target)==float(val)) and (norm(str(row[1].value or ''))==actual)
     audit.append(dict(standard='GB19153-2019',table=number,pdf_page=page_no,bbox=str(bbox),key=str(key),source=val,sheet=f'表{number}',cell=row[6].coordinate,actual=target,result='PASS' if ok else 'FAIL'))
     if not ok:failures.append(audit[-1])
 # table 7 from original table text
 weights=doc.pages[16].find_tables()[0].extract()[1:]
 for r,vals in enumerate(weights,5):
  for c,token in enumerate(vals,1):
   expected=float(norm(token).replace('%',''))/100;cell=wb['表7权重与说明'].cell(r,c);ok=cell.value==expected
   audit.append(dict(standard='GB19153-2019',table=7,pdf_page=17,bbox='table 7',key=f'row{r-4}',source=expected,sheet=cell.parent.title,cell=cell.coordinate,actual=cell.value,result='PASS' if ok else 'FAIL'))
   if not ok:failures.append(audit[-1])
assert len({(a['sheet'],a['cell']) for a in audit})==2925
assert sum(wb[f'表{n}'].max_row-5 for n in range(1,7))==2919
# Boiler values independently transcribed from this session's reviewed original page images.
boiler=openpyxl.load_workbook(ROOT/'docs/standards/gb24500_2020/data/GB24500_2020_TABLE_VALUES.xlsx',data_only=False)
expected={
 '表1 层状燃煤':[(85,86),(82,83),(80,81),(87,89),(84,86),(82,84),(85,86),(82,83),(80,81),(85,86),(82,83),(80,81),(85,86),(82,83),(80,81),(85,87),(82,84),(80,82)],
 '表2 流化床燃煤':[(x,) for x in [89,85,82,90,89,86,91,90,88,90,88,86,89,88,86,90,88,86,91,89,86]],
 '表3 生物质':[(88,91),(84,88),(80,86)],
 '表4 室燃':[(x,) for x in [96,94,92,103,101,98,93,91,88,95,93,90,92,90,88]]}
for tn,(sheet,values) in enumerate(expected.items(),1):
 for r,vs in enumerate(values,6):
  for c,exp in enumerate(vs,6):
   cell=boiler[sheet].cell(r,c);ok=cell.value==exp
   audit.append(dict(standard='GB24500-2020',table=tn,pdf_page={1:4,2:5,3:5,4:6}[tn],bbox='independent original-image transcription',key=f'row{r}',source=exp,sheet=sheet,cell=cell.coordinate,actual=cell.value,result='PASS' if ok else 'FAIL'))
   if not ok:failures.append(audit[-1])
cell=boiler['限定值与来源']['B5'];audit.append(dict(standard='GB24500-2020',table='5.2',pdf_page=6,bbox='clause 5.2',key='minimum',source=97,sheet=cell.parent.title,cell=cell.coordinate,actual=cell.value,result='PASS' if cell.value==97 else 'FAIL'))
with (OUT/'independent_cells.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
counts={}
for a in audit:
 key=a['standard']+'/table'+str(a['table']);counts.setdefault(key,{'pass':0,'fail':0,'dash':0});counts[key][a['result'].lower()]+=1;counts[key]['dash']+=a['source']=='—'
report={'checks':len(audit),'counts':counts,'failures':failures,'formula_cells':sum(c.data_type=='f' for book in [wb,boiler] for s in book for row in s for c in row),'method':'Fresh PDF geometry and header reconstruction for compressor; independent image transcription for boiler; no author evidence CSV/JSON used.'}
(OUT/'independent_summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=False))
# Read all non-value workbook fields for human condition/units review; read-only.
lines=[]
for book in [boiler]:
 for s in book:
  lines.append(s.title)
  for row in s:
   lines.append(' | '.join(str(c.value) for c in row))
(OUT/'boiler_workbook_readback.txt').write_text('\n'.join(lines),encoding='utf8')
