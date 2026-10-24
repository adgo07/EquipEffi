"""Independent values transcribed by reviewer from freshly rendered original PDF pages.
Does not import execution-stage expected data or validators. Read-only on workbooks.
"""
from pathlib import Path
from decimal import Decimal
import csv,json,hashlib,openpyxl
root=Path.cwd();out=Path(__file__).parent
checks=[]
def check(sid,sheet,row,col,val,page,kind='table_value'):
 std=next((root/'docs/standards').glob('gb'+sid+'_*'))
 path=next((std/'data').glob('*.xlsx'))
 if str(path) not in books: books[str(path)]=openpyxl.load_workbook(path,data_only=False)
 cell=books[str(path)][sheet].cell(row,col); actual=cell.value
 try: good=Decimal(str(actual))==Decimal(str(val))
 except: good=actual==val
 checks.append(dict(standard=sid,sheet=sheet,coordinate=cell.coordinate,source_pdf_page=page,expected=str(val),actual=str(actual),number_format=cell.number_format,kind=kind,result='PASS' if good else 'FAIL'))
def matrix(sid,sheet,start,col,rows,page):
 for r,line in enumerate(rows.split(';')):
  for c,v in enumerate(line.split()):check(sid,sheet,start+r,col+c,v,page)
books={}
matrix('29541','表1_能效限值',6,6,'4.60 4.40 4.10 3.90 3.70;4.20 4.00 3.80 3.60 3.40;3.80 3.60 3.40 3.20 3.00;4.60 4.40 4.10 3.90 3.70;4.60 4.40 4.10 3.90 3.70;4.50 4.30 4.00 3.80 3.60;3.90 3.70 3.50 3.30 3.10;3.90 3.70 3.50 3.30 3.10;3.80 3.60 3.40 3.20 3.00',4)
for r,v in enumerate([10,5,10,.95,.95,1.10,5,2,2,1,2],6):check('29541','条款数值与条件',r,3,v,5 if r>=15 else 4,'clause_number')
matrix('19576','表1',6,7,'4.50 3.80 2.90;3.60 3.00 2.70;3.50 3.10 2.70;3.40 3.00 2.60',3)
matrix('19576','表1',10,7,'4.50 4.30 3.70;4.00 3.70 3.30;4.00 3.60 3.00;4.20 4.00 3.50;3.90 3.70 3.20;3.60 3.40 2.90;4.10 3.90 3.40;3.20 3.00 2.80;4.00 3.70 3.00',4)
matrix('37479','表1_风管机组',6,9,'4.20 3.80 3.00;4.00 3.60 2.90;3.80 3.40 2.80;3.20 3.00 2.60;3.80 3.40 2.90;3.60 3.20 2.80;3.40 3.00 2.70;3.00 2.80 2.40;4.20 4.00 3.40;4.00 3.80 3.30',4)
matrix('37479','表2_全新风机组',6,9,'3.40 3.20 3.00;3.20 3.00 2.80;3.00 2.80 2.60;2.80 2.60 2.40;3.20 3.00 2.80;3.00 2.80 2.60;2.80 2.60 2.40;2.60 2.40 2.20;4.70 4.50 4.30;4.50 4.30 4.10;4.40 4.20 4.00;4.20 4.00 3.80',4)
for r,v in enumerate([0,0,.95,1.10,2,29,35,1.077,.914],2):check('37479','条款数值',r,2,v,3 if r==2 else 5,'clause_number')
matrix('21454','表1',6,2,'3.60 5.50 2.90 5.10 2.10 4.80;— 5.10 — 4.70 — 4.40;— 4.90 — 4.50 — 4.20;— 4.80 — 4.40 — 4.10;— 4.70 — 4.30 — 4.00',4)
matrix('21454','表2',6,2,'3.50 5.20 2.80 4.40 2.00 3.60;— 4.80 — 4.30 — 3.50;— 4.50 — 4.20 — 3.40;— 4.20 — 4.00 — 3.30;— 4.00 — 3.80 — 3.20',4)
matrix('21454','表3',6,4,'7.00 5.90 5.20;6.80 5.80 5.00;4.60 4.20 3.80;5.00 4.50 4.30',5)
matrix('21454','表4',6,2,'3.40 3.20 3.00 2.20 1.80;3.20 3.00 2.80 1.90 1.50',5)
matrix('21454','表A.1',6,2,'1.30 -20 — 20 <15;1 -12 -13.5 20 <15;.81 -7 -8 20 <15;.48 2 1 20 <15;.30 7 6 20 <15',9)
matrix('21454','表A.2',6,2,'1.32 -20 — 20 15;1 -12 -13.5 20 15;.80 -7 -8 20 15;.44 2 1 20 15;.24 7 6 20 15',9)
for sheet,hours,total in [('表A.3',[1,1,3,6,14,14,30,39,36,62,76,98,120,155,145,180,242,271,242,211,192,181,195,206,181,137,119,130,83,84,76,45,48,40],3663),('表A.4',[0,0,1,0,1,3,5,2,6,15,12,26,32,30,32,52,52,64,66,65,46,66,66,60,54,41,33,45,35,38,44,23],1015)]:
 for i,h in enumerate(hours):
  page=9 if sheet=='表A.3' and i<12 else 10
  for col,val in enumerate([i+1,i-19,h],1):check('21454',sheet,i+6,col,val,page)
 check('21454',sheet,len(hours)+6,3,total,10)
 assert sum(hours)==total
for r,v in enumerate([3,4,6,10],6):check('21454','表A.5',r,2,v,11)
# GB19577, grade columns F/G/H, additional columns J and L, not contiguous source arrays.
tables={
1:('6.00 5.60 5.20 4.20;7.80 7.20 5.70 5.00;8.10 7.50 6.20 5.40;8.50 8.10 6.30 5.60;4.50 4.0 3.50 2.70;4.30 3.85 3.30 2.80;5.40 5.00 4.40 4.00;5.80 5.40 5.10 4.60;8.20 7.50 6.80 6.00;10.00 8.00 7.40 6.50;12.00 10.00 8.00 7.00;6.80 5.80 4.80 3.00',9),
2:('5.30 5.10 5.20 4.20;5.80 5.60 5.70 5.00;6.20 6.00 6.20 5.40;6.40 6.20 6.30 5.60;3.40 3.20 3.30 2.80',9),
3:('3.60 3.20 2.80 2.00 2.30;3.05 2.85 2.65 1.80 2.10;2.60 2.40 2.30 1.50 1.70;3.40 3.20 3.00 2.10 2.50;3.30 3.10 3.00 1.80 2.30;2.60 2.40 2.30 1.50 1.80',10),
4:('4.60 4.10 3.70;5.10 4.60 4.00;4.40 4.00 3.80;5.60 5.00 4.60;5.80 5.40 4.40;4.90 4.50 4.00;5.10 4.70 4.40;4.70 4.30 4.20;4.90 4.50 4.20;5.10 4.70 4.00;5.80 5.20 4.30;5.70 5.50 5.30;6.20 5.80 5.40;5.10 4.70 4.20;5.60 5.10 4.40',10),
5:('1.05 1.10 1.19;1.02 1.05 1.11;1.00 1.02 1.09;1.46 1.40 1.30',11),
6:('4.00 3.80 3.60;4.40 4.20 4.00;4.10 3.90 3.70;3.70 3.50 3.30;3.40 3.20 3.00;4.50 4.20 4.00;4.80 4.50 4.30;4.50 4.10 3.90;4.00 3.70 3.50;3.60 3.30 3.20;4.10 3.70 3.40',11),
7:('17.0 14.0 10.0 9.0;22.0 19.0 15.0 13.0;21.0 18.0 14.0 12.0;25.0 22.0 18.0 16.0;16.0 14.0 10.0;20.0 17.0 14.0;15.0 11.0 9.0;20.0 14.0 13.0;21.0 15.0 12.0;22.0 15.0 14.0',12),
8:('5.40 5.00 4.40 4.00;5.60 5.00 4.80 4.40;5.80 5.40 5.10 4.60;6.00 5.60 5.20 4.80;4.40 3.90 3.40 2.70;4.20 3.75 3.20 2.70',12)}
for t,(rows,page) in tables.items():
 for r,line in enumerate(rows.split(';'),6):
  for c,v in zip([6,7,8,10,12],line.split()):check('19577',f'表{t}',r,c,v,page)
for r in range(10,16):check('19577','表7',r,10,None,12,'merged_blank')
matrix('19577','表A.1',6,2,'1 7 .172 35 —;.75 7 .172 32.25 —;.50 9 .172 29.5 —;.25 11 .172 26.8 —',14)
for i,h in enumerate([277,205,180,110,94,61,25,20,20,11,4,0,0,0,0]):
 for col,val in enumerate([i+1,i+25,h],1):check('19577','表A.2',i+6,col,val,14)
check('19577','表A.2',21,3,1007,14)
with (out/'independent_cell_comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(checks[0]));w.writeheader();w.writerows(checks)
summary={}
for x in checks:
 key=x['standard']+'/'+x['sheet']; s=summary.setdefault(key,{'checked':0,'pass':0,'fail':0});s['checked']+=1;s[x['result'].lower()]+=1
(out/'comparison_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False));print('TOTAL',len(checks),'FAIL',sum(x['result']=='FAIL' for x in checks))
