"""Read XLSX XML at actual coordinates; verify transport, not standard truth."""
from pathlib import Path
import csv,json,hashlib,zipfile,xml.etree.ElementTree as E
from collections import Counter
O=Path(__file__).resolve().parent
X=O/'data/GB32030_2022_表值映射.xlsx'
N={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
checks=[]
with zipfile.ZipFile(X) as z:
 ss=[]
 if 'xl/sharedStrings.xml' in z.namelist():
  ss=[''.join(e.itertext()) for e in E.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',N)]
 sheets={}
 formulas=0
 for n in range(1,7):
  root=E.fromstring(z.read(f'xl/worksheets/sheet{n}.xml'));vals={}
  for c in root.findall('.//s:sheetData/s:row/s:c',N):
   if c.find('s:f',N) is not None:formulas+=1
   v=c.find('s:v',N); raw=v.text if v is not None else None
   if c.get('t')=='s':v=ss[int(raw)]
   elif c.get('t')=='inlineStr':v=''.join(c.find('s:is',N).itertext())
   elif c.get('t') in ('str','e'):v=raw
   elif raw is not None:v=float(raw)
   else:v=None
   vals[c.get('r')]=v
  sheets[f'表{n}']=vals
 tables=json.loads((O/'data/tables.json').read_text(encoding='utf8'))
 for t in tables:
  for i,r in enumerate(t['rows']):
   for j,want in enumerate(r):
    if j>=5 and want is None:want='—'
    elif j>=5 and want=='-Δη' and t['base']=='ηgr':want='-Δηgr'
    addr=f'{chr(65+j)}{i+6}';got=sheets[f"表{t['n']}"] .get(addr)
    ok=(got==want or (got is None and want==''))
    checks.append(dict(kind='xlsx_transport',sheet=f"表{t['n']}",cell=addr,expected=want,actual=got,result='PASS' if ok else 'FAIL'))
 records=list(csv.DictReader((O/'evidence/cell_trace.csv').open(encoding='utf-8-sig')))
 for r in records:
  got=sheets[r['xlsx_sheet']].get(r['xlsx_cell'])
  want=float(r['increment_pp']) if r['value_kind']=='BASE_PLUS_INCREMENT' else '—' if r['value_kind']=='PRINTED_DASH' else ('-Δηgr' if int(r['table']) in [4,6] else '-Δη') if r['value_kind']=='BASE_MINUS_TOLERANCE' else r['expression']
  checks.append(dict(kind='csv_coordinate',sheet=r['xlsx_sheet'],cell=r['xlsx_cell'],expected=want,actual=got,result='PASS' if got==want else 'FAIL'))
# Explicit second-look anchors read visually from main PDF pages 4-8.
anchors=[(1,'J6',1.5),(1,'K11',1.8),(1,'F7','—'),(1,'G8',3.5),(1,'J9',.8),(1,'F14','-Δη'),
 (2,'F7',3),(2,'G8',1.5),(2,'H7',2),(2,'I7',2.5),(2,'G13',.5),(2,'I17','-Δη'),
 (3,'G6','—'),(3,'F8',2.5),(3,'I9',5.5),(3,'I10',5),(3,'G16',2),(3,'F21','-Δη'),
 (4,'G7',3),(4,'H8','—'),(4,'I11',1.8),(4,'G15',1.3),(4,'F20','-Δηgr'),
 (5,'F6','1B'),(5,'F7','1U'),(5,'F10','2B'),(5,'F11','2U'),
 (6,'F9',4.5),(6,'F12',2.3),(6,'G13',2),(6,'F20','-Δηgr')]
audit=[]
for n,c,w in anchors:
 r=next(x for x in records if x['xlsx_sheet']==f'表{n}' and x['xlsx_cell']==c)
 g=sheets[f'表{n}'].get(c)
 audit.append(dict(sheet=f'表{n}',cell=c,expected_from_visual=w,actual=g,source_cell=r['source_cell'],pdf_page=r['pdf_page'],printed_page=r['printed_page'],method='SECOND_LOOK_SAME_EXECUTOR',result='PASS' if w==g else 'FAIL'))
with (O/'evidence/numeric_spot_check.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
counts=Counter(c['result'] for c in checks)
out=dict(xlsx_sha256=hashlib.sha256(X.read_bytes()).hexdigest(),grid_transport_checks=sum(c['kind']=='xlsx_transport' for c in checks),csv_coordinate_checks=len(records),checks=dict(counts),spot_checks=len(audit),spot_results=dict(Counter(r['result'] for r in audit)),formula_count=formulas,independent_numeric_acceptance='NOT_RUN',production_unittest='NOT_RUN',compileall='NOT_RUN',smoke='NOT_RUN',performance='NOT_RUN')
(O/'evidence/verification_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(out,ensure_ascii=False,indent=2))
assert counts['FAIL']==0 and all(r['result']=='PASS' for r in audit)
