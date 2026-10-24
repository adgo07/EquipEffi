from pathlib import Path
import json,csv
from decimal import Decimal
b=Path(__file__).parent; d=json.loads((b/'pdf_tables.json').read_text(encoding='utf8')); w=json.loads((b/'workbook_values.json').read_text(encoding='utf8'))
source={}; seq=0
for page,tables in d.items():
 for tab in tables:
  seq+=1;source[seq]=(int(page),tab)
checks=[];coverage=[]
def number(v): return Decimal(str(v).replace(' ',''))
for n,(page,t) in source.items():
 rows=[(i+1,r) for i,r in enumerate(w[f'表{n:02}']) if len(r)>6 and isinstance(r[1],(int,float))]
 expected=[]
 if n in [1,2,30,32,34]:
  start=4 if n in [1,2] else 3
  for col in range(start,len(t[-1])):
   if not t[-1][col] or not t[-1][col].replace(' ','').isdigit():continue
   cap=number(t[-1][col]);cores=['电工钢带','非晶合金'] if n in [1,2] else [None]
   for core in cores:
    variants=['Dyn11/Yzn11','Yyn0'] if n==1 else ['B','F','H']
    for variant in variants:
     vals=[];refs=[]
     for g in range(1,4):
      if n==1:
       p0=(3-g)*6+(6 if core=='电工钢带' else 3)
       pk=p0-(1 if variant=='Dyn11/Yzn11' else 2)
       if t[pk][col] is None:pk-=1 # merged shared cell, visually verified page7
      elif n==2:
       p0=(3-g)*8+(8 if core=='电工钢带' else 4);pk=p0-({'B':1,'F':2,'H':3}[variant])
      else:
       p0=(3-g)*4+4;pk=p0-({'B':1,'F':2,'H':3}[variant])
      vals.extend([number(t[p0][col]),number(t[pk][col])]);refs.extend([f'p{page}:r{p0+1}c{col+1}',f'p{page}:r{pk+1}c{col+1}'])
     group=('4.0%' if col<16 else '6.0%～8.0%') if n==2 else None
     expected.append((cap,core,variant if n==1 else None,variant if n!=1 else None,group,vals,refs))
 else:
  idx=0
  for ri,r in enumerate(t):
   if not r[0] or not r[0].replace(' ','').isdigit():continue
   cap=number(r[0]);begin=2 if n==15 else 1;vals=[number(v) for v in r[begin:begin+6]]
   group=('普通组' if idx<8 else '低压66/69kV特殊组') if n==15 else ('ABC'[idx//5] if n in [27,28] else None)
   expected.append((cap,None,None,None,group,vals,[f'p{page}:r{ri+1}c{c+1}' for c in range(begin,begin+6)]));idx+=1
 for cap,core,vector,thermal,group,vals,refs in expected:
  candidates=[(i,r) for i,r in rows if number(r[1])==cap and r[2]==core and r[3]==vector and (not thermal or (r[4] or '').startswith(thermal)) and (group is None or (str(r[5]).replace('～','~').replace('6.0%~8.0%','6.0~8.0%')==group.replace('～','~').replace('6.0%~8.0%','6.0~8.0%')))]
  if not candidates and n==15 and group!='普通组':candidates=[(i,r) for i,r in rows if number(r[1])==cap and r[5]!='普通组']
  if len(candidates)!=1:print('BAD MATCH',n,cap,core,vector,thermal,group,len(candidates));continue
  i,r=candidates[0]
  for j,(val,ref) in enumerate(zip(vals,refs)):
   observed=number(r[6+j]);checks.append([n,page,str(cap),core,vector,thermal,group,f'表{n:02}!{chr(71+j)}{i}',ref,str(val),str(observed),'PASS' if observed==val else 'FAIL'])
  unit='W' if n in [1,2,29,30,31,32] else 'kW'
  for j in [12,13]:checks.append([n,page,str(cap),core,vector,thermal,group,f'表{n:02}!{chr(65+j)}{i}','PDF表头',unit,r[j],'PASS' if r[j]==unit else 'FAIL'])
 coverage.append([n,page,len(expected),len(rows),len([x for x in checks if x[0]==n]),len([x for x in checks if x[0]==n and x[-1]=='FAIL'])])
with (b/'cell_comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
 c=csv.writer(f);c.writerow(['table','pdf_page','capacity_kVA','core','vector','thermal','branch','workbook_cell','pdf_extracted_cell','pdf_value','workbook_value','result']);c.writerows(checks)
with (b/'table_coverage.csv').open('w',encoding='utf-8-sig',newline='') as f:
 c=csv.writer(f);c.writerow(['table','pdf_page','expected_logical_rows','workbook_logical_rows','checks_loss_and_unit','fail']);c.writerows(coverage)
print('TOTAL',len(checks),'FAIL',len([x for x in checks if x[-1]=='FAIL']));print(coverage)
print([x for x in checks if x[-1]=='FAIL'][:20])
