"""Expected values independently transcribed from viewed PDF images. Read-only XLSX snapshots."""
from pathlib import Path
from decimal import Decimal
import json,csv,collections
OUT=Path(__file__).resolve().parent/'round2'
rows=[]
def add(key,sheet,cell,value,page,source):
    rows.append(dict(standard=key,sheet=sheet,cell=cell,expected=str(value),pdf_physical_page=page,source=source))
def matrix(key,sheet,start,cols,values,page,source):
    for i,vs in enumerate(values):
        for col,v in zip(cols,vs.split()):add(key,sheet,f'{col}{start+i}',v,page,source)
k='gb19761_2020'
matrix(k,'表2',47,'EFG',['63 73 78','66 78 83','73 82 87','76 84 89','— — —','70 79 84','72 81 86'],5,'表2特殊四机号分支和末行合并横杠')
matrix(k,'表3',5,'EFG',['55 66 69','58 69 72','60 73 77','59 68 71','61 71 74','63 75 79','61 70 73','64 73 76','66 77 81','63 72 75','67 75 78','69 79 83'],5,'表3四轮毂比乘三机号段全部等级限值')
k='gb32030_2022'
matrix(k,'表4',6,'FGHI',['2 3 2.5 3.5','2.5 3 3 —','3 3.5 — —','2.5 3 — —','2 2.5 — —','1 1.5 1.3 1.8','1.3 1.5 1.5 —','1.5 1.8 — —','1.3 1.5 — —','1 1.3 — —']+['-Δηgr -Δηgr -Δηgr -Δηgr']*5,6,'表4全部展开增量/横杠/减容差符号；不是绝对效率。另对照官方扫描PDF8')
k='gbt36561_2018'
matrix(k,'正文表值',196,'F',[str(v) for v in [40193,46055,9600,11000,1,5234,5652,1250,1350,.95,586,9211,1400,2200,1,14654,17585,3500,4200,1.14,34541,41868,8250,10000,1.10]],12,'表9全部热值端点及燃料系数；保留586疑值')
matrix(k,'正文表值',362,'F',[str(v) for v in [15,10,2,2,2,2,2,2,2,5,5,10,13,6,6,6,5,5]],18,'表16全部18个评分单元；源8/9共2分不重复计')
matrix(k,'附录系数',25,'F',[str(v) for v in [1,1.1,1,1.3,1.7,.6,1,1.2,1,1.3,1.4]],23,'A.5/A.6全部系数；重叠条件仍未解释')
k='gb19577_2024'
matrix(k,'表A.1',6,'BCDEF',['1 7 .172 35 —','.75 7 .172 32.25 —','.5 9 .172 29.5 —','.25 11 .172 26.8 —'],14,'表A.1全部工况数字/湿球横杠；负荷率按XLSX百分格式比例值')
matrix(k,'表A.2',6,'BC',[f'{t} {h}' for t,h in zip(range(25,40),[277,205,180,110,94,61,25,20,20,11,4,0,0,0,0])],14,'表A.2温度小时全部15行，含明确0')
add(k,'表A.2','C21','1007',14,'表A.2合计小时')
matrix(k,'表7',6,'FGHJ',['17 14 10 9','22 19 15 13','21 18 14 12','25 22 18 16','16 14 10 <BLANK>','20 17 14 <BLANK>','15 11 9 <BLANK>','20 14 13 <BLANK>','21 15 12 <BLANK>','22 15 14 <BLANK>'],12,'表7全部等级/附加EER；末六行附加列原合并空白')
matrix(k,'表8',6,'FGHJ',['5.4 5 4.4 4','5.6 5 4.8 4.4','5.8 5.4 5.1 4.6','6 5.6 5.2 4.8','4.4 3.9 3.4 2.7','4.2 3.75 3.2 2.7'],12,'表8全部等级及附加COP')
k='gb28381_2026'
matrix(k,'表5',5,'CDEFGHIJK',['29.1 36.9 45.7 55.9 67.9 82.5 — — —','32.6 40.95 51.05 63.1 77.85 96.6 — — —','37 46.1 57.8 72 90 113.5 — — —'],13,'表5 q=1全部等级/压力含两位小数及横杠')
matrix(k,'表4',98,'CDEFGHIJKL',['11.7 22.2 32.9 43.8 55 66.3 77.8 89.4 — —','12.8 23.9 35.3 47 58.9 71.1 83.4 95.9 — —','14.2 26.1 38.5 51.2 64.2 77.4 90.8 104.5 — —'],13,'表4 q=1250末端全部等级/压力；H99原页放大复核为71.1，验收初读71.4已纠正')
data={}
for r in rows:
    k=r['standard']
    if k not in data:data[k]={s['sheet']:s['cells'] for s in json.loads((OUT/'tmp'/f'{k}_cells.json').read_text(encoding='utf-8'))}
    actual=data[k][r['sheet']].get(r['cell'],{}).get('value'); e=r['expected'];r['actual']=actual
    if e=='<BLANK>':ok=actual in [None,''];kind='blank'
    elif e=='—':ok=actual in ['—','-','－'];kind='dash'
    elif e=='-Δηgr':ok=actual==e;kind='symbol'
    else:
        kind='numeric'
        try:ok=Decimal(actual)==Decimal(e)
        except Exception:ok=False
    r['kind']=kind;r['result']='PASS' if ok else 'FAIL'
with (OUT/'independent_visual_cells.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print('Coverage',collections.Counter(r['standard'] for r in rows));print('Kinds',collections.Counter(r['kind'] for r in rows));print('Results',collections.Counter(r['result'] for r in rows))
for r in rows:
    if r['result']=='FAIL':print(r)
