from pathlib import Path
import openpyxl,csv,json
raw={
'1':'3 .1 .1 5 .2 .2 8 .5 .5 10 .5 .5 15 .5 .5 20 .5 .5 25 1 1',
'2':'10 10 15 15 10 10 10 10 5 5 10 10 5',
'3':'3 1.1 .2 1.5 — 2 5 1.7 .3 3 — 1 8 2.2 .4 5 .38 3 10 2.2 .4 6 .38 3 15 2.8 .5 7 .38 3 20 2.8 .5 7 .38 3 25 5.6 1 — .75 6 — 2.8 — 6 — 6',
'4':'2 4 2.5 5','5':'.1 .15','6':'.3 .3 .3 5',
'7':'2 4 1 4 1 4 1 1 5 3 2 1 3 10000 2 5 1 4 2 2 1 5 3000 8',
'8':'''330 390 470
340 400 480
370 460 560
390 480 600
540 680 840
480 630 760
440 560 700
460 590 700
420 550 650
400 510 600
210 270 320
190 250 290
1400 1550 1700
1000 1230 1400
950 1090 1200
400 540 660
350 480 600
390 530 650
680 900 1050
650 850 1000
300 400 500
165 210 290
300 400 520
60 100 170
330 370 450
110 140 200''',
'9':'40193 46055 9600 11000 1 5234 5652 1250 1350 .95 586 9211 1400 2200 1 14654 17585 3500 4200 1.14 34541 41868 8250 10000 1.1',
'10':'''33 36 40 35 40 50
35 40 50 40 45 50
40 45 50 55 60 65
50 60 70 60 70 80
60 70 80 70 80 90
70 80 90 80 90 100
40 45 50 50 55 60
45 50 55 60 65 70
25 30 35 25 30 35
40 45 50 40 50 60''',
'11':'.5 1 1.5 1.5 2 2.5 1.2 1.5 2 .5 1 1.5 1 1 2 2',
'12':'20 23 26 18 22 25 19 23 26 18 22 25 20 25 30 18 24 30 20 22 25 33 36 40 30 34 38 23 26 30',
'13':'200 1 5 850 6 .10 .010 .010 50','14':'150 150 60 .5 1 10 1 5 1 2 1 5 25 10',
'15':'40 20 10 0 30 20 10 0 30 20 10 0','16':'15 10 2 2 2 2 2 2 2 5 5 10 13 6 6 6 5 5','17':'85 70 60',
'A.1':'.3 .5 .7 1 1.05 1.4 1.5 1.3 1.5 1.7 1.9','A.2':'1 2.5 2','A.3':'1 1.2 1.4 1.6 1 1.2','A.4':'1 1.6 2.2','A.5':'1 1.1 1 1.3 1.7','A.6':'.6 1 1.2 1 1.3 1.4','A.7':'1 δ δ 1 ≤0.4 .9 1 >0.4 1.2 .81 — 1 .5 — 1',
'A.8':'1 1.2 1.5 .4 .7 1 1.2 1.5 1.4 2.6 3','A.9':'1 1.1 1.2','A.10':'1 1.1 1.5 1.7','A.11':'1 1.6 1.6 1.8 2 2.4 2.6 .4 .7 1 1.2 1.2 1.5 1.4','A.12':'0 .2 .5 1 2.5 3'}
w=openpyxl.load_workbook('docs/standards/gbt36561_2018/data/GBT36561_2018_TABLE_VALUES.xlsx');records=[];groups={}
for s in list(w)[1:]:
 for row in list(s)[1:]:groups.setdefault(str(row[1].value),[]).append((s,row))
for n,txt in raw.items():
 vals=txt.split();assert len(vals)==len(groups[n]),(n,len(vals),len(groups[n]))
 for val,(s,row) in zip(vals,groups[n]):
  c=row[5];eq=str(c.value)==val
  try:eq=float(val)==float(c.value)
  except (TypeError,ValueError):pass
  records.append(dict(table=n,record_id=row[0].value,cell=f'{s.title}!{c.coordinate}',pdf_page=row[10].value,visual_source_value=val,workbook_value=c.value,match=eq))
out=Path('docs/governance/device_full_acceptance_20261013/fans_submersible/gbt36561_2018')
with (out/'independent_visual_cells.csv').open('w',encoding='utf-8-sig',newline='') as f:
 wr=csv.DictWriter(f,fieldnames=records[0]);wr.writeheader();wr.writerows(records)
print(len(records),[r for r in records if not r['match']])
