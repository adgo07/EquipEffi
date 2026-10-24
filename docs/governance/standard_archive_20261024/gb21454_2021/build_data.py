"""GB21454-2021 page-image transcription. Only writes this standard folder.
Not a production calculator. Numeric entries were transcribed against PDF pages.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
SHA = 'ae091115094de6dcc2f587e35bd5a9389708fb37714804ef510ea831613a7331'
tables = []
def add(name, title, page, headers, rows, notes, numeric, formats=None):
    tables.append(dict(name=name,title=title,page=page,headers=headers,rows=rows,notes=notes,numeric=numeric,formats=formats or {}))

bands=['CC≤14000','14000<CC≤28000','28000<CC≤50000','50000<CC≤68000','CC>68000']
for name,title,metric,values in [
 ('表1','风冷式单冷型多联机','SEER',[[3.60,5.50,2.90,5.10,2.10,4.80],['—',5.10,'—',4.70,'—',4.40],['—',4.90,'—',4.50,'—',4.20],['—',4.80,'—',4.40,'—',4.10],['—',4.70,'—',4.30,'—',4.00]]),
 ('表2','风冷式热泵型多联机','APF',[[3.50,5.20,2.80,4.40,2.00,3.60],['—',4.80,'—',4.30,'—',3.50],['—',4.50,'—',4.20,'—',3.40],['—',4.20,'—',4.00,'—',3.30],['—',4.00,'—',3.80,'—',3.20]])]:
    add(name,title,4,['名义制冷量 CC (W)','1级 EERmin (W/W)',f'1级 {metric} (Wh/Wh)','2级 EERmin (W/W)',f'2级 {metric} (Wh/Wh)','3级 EERmin (W/W)',f'3级 {metric} (Wh/Wh)'],[[b]+v for b,v in zip(bands,values)],['来源：GB 21454—2021 '+name+'，印刷2 / PDF4。','—：原表不作指标要求，不是0或缺失。CC≤14000时两个指标均须满足。','不同静压按GB/T18837—2015、GB/T18836—2017修正；外部方法待补证。'],list(range(1,7)))

add('表3','水冷式多联机',5,['指标 (W/W)','物理类型','名义制冷量 CC (W)','1级','2级','3级'],[
 ['IPLV(C)','水环式','CC≤28000',7.00,5.90,5.20],['IPLV(C)','水环式','CC>28000',6.80,5.80,5.00],
 ['EER','地埋管式','—',4.60,4.20,3.80],['EER','地下水式','—',5.00,4.50,4.30]],
 ['来源：GB 21454—2021 表3，印刷3 / PDF5。','原表IPLV(C)与水环式分别跨第1～2数据行合并；EER跨第3～4行合并。本表逐行展开。','地埋管式/地下水式容量栏保留原—；表3未另给符号释义，不据此增加容量门槛。'],[3,4,5])

add('表4','低温多联机',5,['名义制热量 HC (W)','1级 HSPF (Wh/Wh)','2级 HSPF (Wh/Wh)','3级 HSPF (Wh/Wh)','COP−12℃ (W/W)','COP−20℃ (W/W)','类别'],[
 ['HC≤18000',3.40,3.20,3.00,2.20,1.80,'户用型'],['HC>18000',3.20,3.00,2.80,1.90,1.50,'工商业用型']],
 ['来源：GB 21454—2021 表4，印刷3 / PDF5。','原表3级表头覆盖HSPF、COP−12℃、COP−20℃；表注明确各等级COP均满足最低等级限值。','不同静压按指定引用标准修正；HSPF试验和计算按附录A。'],[1,2,3,4,5])

for sheet,title,rates,wet in [('表A.1','户用型试验工况',[1.30,1,0.81,0.48,0.30],'<15'),('表A.2','工商业用型试验工况',[1.32,1,0.80,0.44,0.24],15)]:
    add(sheet,title,9,['测试点','负荷率','热源干球 (℃)','热源湿球 (℃)','使用侧干球 (℃)','使用侧湿球 (℃)'],
      [[p,r,t,w,20,wet] for p,r,t,w in zip('ABCDE',rates,[-20,-12,-7,2,7],['—',-13.5,-8,1,6])],
      ['来源：GB 21454—2021 '+sheet+'，印刷7 / PDF9。','项目类别及使用侧干/湿球原格跨A～E五行合并；此处展开保留关联，不是五个独立源格。','A点热源湿球—：湿度过低，不作要求。'+('使用侧<15仅适用于湿球影响室内侧换热的装置（脚注b）。' if sheet=='表A.1' else '使用侧湿球15无表A.1脚注b，不得复制为<15。')], [1,2,3,4,5],{'B':'0%','C':'0.0','D':'0.0','E':'0','F':'0'})

home=[1,1,3,6,14,14,30,39,36,62,76,98,120,155,145,180,242,271,242,211,192,181,195,206,181,137,119,130,83,84,76,45,48,40]
commercial=[0,0,1,0,1,3,5,2,6,15,12,26,32,30,32,52,52,64,66,65,46,66,66,60,54,41,33,45,35,38,44,23]
for name,title,vals,total in [('表A.3','户用型各温度发生时间',home,3663),('表A.4','工商业用型各温度发生时间',commercial,1015)]:
    rows=[]
    for j,h in enumerate(vals,1):
        if name=='表A.3':
            p=9 if j<=12 else 10
            block='左' if j<=6 or 13<=j<=24 else '右'
            srcrow=j if j<=6 else j-6 if j<=12 else j-12 if j<=24 else j-24
        else:
            p=10; block='左' if j<=17 else '右';srcrow=j if j<=17 else j-17
        rows.append([j,j-20,h,f'PDF{p} / 印刷{p-2} / {block}块第{srcrow}行'])
    add(name,title,9 if name=='表A.3' else 10,['温度区间 j','室外温度 (℃)','小时数 (h)','原表定位'],rows,
      [f'来源：GB 21454—2021 {name}，'+('印刷7～8 / PDF9～10。' if name=='表A.3' else '印刷8 / PDF10。'),f'原文总计 {total} h；原表左右栏展开按j保序。合计与各行分别核对。','0小时是原表数值，不能改为空白；户用与工商业相同温度仍保留各自时数。'],[0,1,2],{'A':'0','B':'0','C':'0'})
    tables[-1]['sourceTotal']=total

add('表A.5','室内机最多连接数量',11,['名义制热量 HC (W)','最多室内机 (台)'],[
 ['HC≤10000',3],['10000<HC≤18000',4],['18000<HC≤32000',6],['HC>32000',10]],
 ['来源：GB 21454—2021 表A.5，印刷9 / PDF11。','A.3.1.1b另规定：HC≤10000最少2台，HC>10000最少3台；本表仅存最多台数。'],[1],{'B':'0'})

(ROOT/'data').mkdir(exist_ok=True)
(ROOT/'data/table_values.json').write_text(json.dumps({'standard':'GB 21454-2021','source_sha256':SHA,'verification':'执行者页图自核；非独立验收','tables':tables},ensure_ascii=False,indent=2),encoding='utf-8')
print('tables',len(tables),'data_rows',sum(len(t['rows']) for t in tables),'hours',sum(home),sum(commercial))
