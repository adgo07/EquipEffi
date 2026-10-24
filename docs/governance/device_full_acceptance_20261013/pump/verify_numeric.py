from pathlib import Path
import json,csv,hashlib
from decimal import Decimal as D
out=Path('docs/governance/device_full_acceptance_20261013/pump')
p=Path('src/equipeffi/resources/standards/pump.json'); d=json.loads(p.read_text(encoding='utf-8'),parse_float=D)
# Transcribed directly from PDF p8 table2 and p9-10 table3 after visual reading.
ci=[('单级单吸',5,300,True,[161.33,163.33,168.33]),('单级单吸',300,10000,False,[162.33,163.33,168.33]),('单级双吸',50,600,True,[161.33,163.33,168.33]),('单级双吸',600,20000,False,[162.33,163.33,168.33]),('管道',5,300,True,[163.33,165.33,171.33]),('管道',300,3000,False,[164.33,165.33,171.33]),('多级',5,100,True,[139.33,142.33,150.33]),('多级',100,3000,False,[140.33,142.33,150.33]),('轻型多级立式',5,300,True,[137.33,139.33,144.33]),('轻型多级卧式',5,300,True,[140.33,142.33,147.33])]
rows=[]
def record(table,location,expected,actual,source):
 rows.append([table,location,str(expected),str(actual),'PASS' if str(expected)==str(actual) else 'FAIL',source])
for i,(typ,lo,hi,inc,vals) in enumerate(ci):
 a=d['water']['ci'][i]
 for key,val in [('type',typ),('q_min',lo),('q_max',hi),('min_inclusive',inc),('max_inclusive',True)]: record('T3',f'water.ci[{i}].{key}',val,a[key],f'PDF{9 if i<4 else 10};printed{3 if i<4 else 4}')
 for j,val in enumerate(vals): record('T3',f'water.ci[{i}].ci[{j}]',D(str(val)),a['ci'][j],f'PDF{9 if i<4 else 10}')
offsets=[[10,5,-4],[4,1,-6],[3,1,-6],[3,1,-6],[11,5,-5],[5,1,-5],[3,2,-5],[3,2,-5],[5,3,-5],[6,4,-4],[1,-1,-5],[1,-1,-5],[3,1,-4],[3,1,-4],[1,-1,-5],[1,-1,-5]]
for i,vals in enumerate(offsets):
 a=d['chemical']['level_offsets'][i]
 for j,val in enumerate(vals): record('T2',f'chemical.level_offsets[{i}].offsets[{j}]',val,a['offsets'][j],'PDF8;printed2')
 for key,val in [('pump','单级' if i<8 else '多级'),('q_min',5 if i%8<4 else 300),('q_max',300 if i%8<4 else None),('ns_min',[20,60,120,210][i%4]),('ns_max',[60,120,210,300][i%4]),('eta0_uses_delta',i%4!=2)]: record('T2',f'chemical.level_offsets[{i}].{key}',val,a[key],'PDF8;printed2')
formulas={'water':{'单级':['-8.44','-0.48','0.09','84.63','8.5'],'多级':['-6.93','-0.19','-0.4','72.67','8.73']},'eta_b':{'单级':['4.7057338e-5','-6.6320555e-3','1.5115754e-1','-1.4023278','5.5234828','-8.3298912e-1','4.1951745e1'],'多级':['5.5836234e-4','-1.2499816e-2','9.9576648e-2','-4.6811292e-1','1.9459872','1.4371144','4.1467097e1']},'delta_eta':{'ns_20_120':['3.7873403e-10','-1.7898913e-7','3.4269717e-5','-3.4148047e-3','1.9050630e-1','-6.0391904','9.8970658e1'],'ns_210_300':['-1.1111111e-10','1.6769231e-7','-1.0507265e-4','3.4987040e-2','-6.5298720','6.4773909e2','-2.6684155e4']}}
for group,branches in formulas.items():
 for branch,vals in branches.items():
  actual=list(d['water']['formulas'][branch].values()) if group=='water' else d['chemical'][group][branch]
  for i,(v,a) in enumerate(zip(vals,actual)):
   rows.append(['formula',f'{group}.{branch}[{i}]',v,str(a),'PASS' if D(v)==D(a) else 'FAIL','PDF9' if group=='water' else 'PDF10'])
with (out/'independent_numeric_comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f); w.writerow(['table','json_pointer','visual_source_expected','canonical_actual','result','source_page']);w.writerows(rows)
files=[next(Path('标准原文').glob('*19762*')),p,*Path('docs/standards/gb19762_2025').rglob('*.md'),Path('docs/PUMP_NUMERIC_AND_DECISION_CONTRACT_V2.md')]
(out/'source_hashes.json').write_text(json.dumps([{'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],ensure_ascii=False,indent=2),encoding='utf-8')
print('checks',len(rows),'fail',sum(r[4]=='FAIL' for r in rows))
