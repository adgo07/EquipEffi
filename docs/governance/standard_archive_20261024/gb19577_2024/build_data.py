"""Rebuild review data and source-cell comparisons from the authorized local PDF.
No production imports. Numeric literals below were transcribed from rendered pages.
Run with bundled Python; --pdf may override the local source location.
"""
from pathlib import Path
import argparse, csv, hashlib, json
from decimal import Decimal
import pdfplumber

ROOT = Path(__file__).resolve().parent
repo = ROOT.parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--pdf', type=Path, default=repo/'标准原文/13. GB 19577-2024 热泵和冷水机组能效限定值及能效等级.pdf')
args = parser.parse_args()
sha = hashlib.sha256(args.pdf.read_bytes()).hexdigest()
assert sha == '809170a5c226d35c29a34dc73299c1589e6dc2acfdcb7b0241d0cbb00bfa58d9'
pdf = pdfplumber.open(args.pdf)
assert len(pdf.pages) == 19
rows = {str(t): [] for t in range(1,9)}
def add(t, standard, branch, capacity, metric, values, aux='', aux2='', note=''):
    v=values.split(); rid=len(rows[str(t)])+1
    rows[str(t)].append(dict(source_row=rid, standard=standard, branch=branch, capacity=capacity, metric=metric,
        values=v[:3], aux=aux, aux_value=v[3] if len(v)>3 else None, aux2=aux2, aux2_value=v[4] if len(v)>4 else None, note=note))
std='GB/T18430.1、GB/T18430.2'
capacities=['CC≤300','300<CC≤528','528<CC≤1163','CC>1163']
for cap,v in zip(capacities,['6.00 5.60 5.20 4.20','7.80 7.20 5.70 5.00','8.10 7.50 6.20 5.40','8.50 8.10 6.30 5.60']): add(1,std,'舒适型/水冷式',cap,'IPLV',v,'COPc')
for cap,v in zip(['CC≤50','CC>50'],['4.50 4.0 3.50 2.70','4.30 3.85 3.30 2.80']): add(1,std,'舒适型/风冷式',cap,'CSPF',v,'COPc')
for cap,v in zip(['CC≤300','CC>300'],['5.40 5.00 4.40 4.00','5.80 5.40 5.10 4.60']): add(1,std,'舒适型/蒸发冷却式',cap,'IPLV',v,'COPc')
for cap,v in zip(['CC≤528','528<CC≤1163','CC>1163'],['8.20 7.50 6.80 6.00','10.00 8.00 7.40 6.50','12.00 10.00 8.00 7.00']): add(1,std,'数据中心专用型/水冷式',cap,'ACCOP',v,'COPc',note='COPc原表有值；与§3.1注的关系见EQP-STD-GB19577-002')
add(1,std,'数据中心专用型/风冷式','—','ACCOP','6.80 5.80 4.80 3.00','COPc',note='容量原格为横线，不是0；COPc关系待确认')
for cap,v in zip(capacities,['5.30 5.10 5.20 4.20','5.80 5.60 5.70 5.00','6.20 6.00 6.20 5.40','6.40 6.20 6.30 5.60']): add(2,std,'舒适型/水冷式',cap,'1/2级COPc；3级IPLV',v,'COPc',note='不得将3级IPLV当作COPc；组合口径待确认')
add(2,std,'舒适型/风冷式','CC>50','1/2级COPc；3级CSPF','3.40 3.20 3.30 2.80','COPc',note='无CC≤50表2分支')
for cap,standard,values in [('≤35','GB/T25127.2',['3.60 3.20 2.80 2.00 2.30','3.05 2.85 2.65 1.80 2.10','2.60 2.40 2.30 1.50 1.70']),('>35','GB/T25127.1',['3.40 3.20 3.00 2.10 2.50','3.30 3.10 3.00 1.80 2.30','2.60 2.40 2.30 1.50 1.80'])]:
    for b,v in zip(['地板采暖型','风机盘管型','散热器型'],values): add(3,standard,b,cap,'APF' if b=='风机盘管型' else 'HSPF',v,'COPdh','COPh',note='容量为名义制热量kW，原容量格各合并3行')
for b,v in zip(['水环式','地下水式','地埋管式、地表水式'],['4.60 4.10 3.70','5.10 4.60 4.00','4.40 4.00 3.80']): add(4,'GB/T19409','冷热风型/热泵型/'+b,'—','ACOP',v,note='容量横线原格覆盖源行1～3；并列型式共用值，不删除物理分支')
for mode,vals in [('单热型',['5.60 5.00 4.60','5.80 5.40 4.40','4.90 4.50 4.00','5.10 4.70 4.40','4.70 4.30 4.20','4.90 4.50 4.20']),('热泵型',['5.10 4.70 4.00','5.80 5.20 4.30','5.70 5.50 5.30','6.20 5.80 5.40','5.10 4.70 4.20','5.60 5.10 4.40'])]:
    for i,v in enumerate(vals): add(4,'GB/T19409','冷热水型/'+mode+'/'+['水环式','地下水式','地埋管式、地表水式'][i//2],['≤260','>260'][i%2],'COP' if mode=='单热型' else 'ACOP',v,note='单热型按名义制热量，热泵型按名义制冷量；并列型式保持')
for pressure,v in zip(['0.4','0.6','0.8'],['1.05 1.10 1.19','1.02 1.05 1.11','1.00 1.02 1.09']): add(5,'GB/T18431','饱和蒸汽压力'+pressure+' MPa','不按容量分档','单位制冷量加热源耗量',v,note='方向≤为待确认技术判断；单位原表未标，见EQP-STD-GB19577-001/005')
add(5,'GB/T18362','直燃型机组','不按容量分档','COP','1.46 1.40 1.30')
for b,v in zip(['H1a','H2a','H3a','H4a','H5a','H1b','H2b','H3b','H4b','H5b'],['4.00 3.80 3.60','4.40 4.20 4.00','4.10 3.90 3.70','3.70 3.50 3.30','3.40 3.20 3.00','4.50 4.20 4.00','4.80 4.50 4.30','4.50 4.10 3.90','4.00 3.70 3.50','3.60 3.30 3.20']): add(6,'GB/T25861',b,'见产品标准名义工况','COPH',v,note='工况代码不替换成猜测温度；超出名义工况范围不以表6考核')
add(6,'JB/T12840','循环供水式热泵高温热水机组','不按容量分档','COP','4.10 3.70 3.40',note='表6注原文保留；边界依据产品标准补证')
for i,v in enumerate(['17.0 14.0 10.0 9.0','22.0 19.0 15.0 13.0','21.0 18.0 14.0 12.0','25.0 22.0 18.0 16.0']): add(7,'JB/T14642','数据中心等类似场所用/'+['标准机型','大温差型'][i//2],['CC≤100','CC>100'][i%2],'AEER',v,'EER',note='AEER试验计算采用寒冷地区(参照北京市)条件，§6.6')
for i,v in enumerate(['16.0 14.0 10.0','20.0 17.0 14.0','15.0 11.0 9.0','20.0 14.0 13.0','21.0 15.0 12.0','22.0 15.0 14.0']): add(7,'JB/T14640',['外冷式','内冷式','内外冷串联式'][i//2],['CC≤100','CC>100'][i%2],'EER',v,note='原最右EER附加列源行5～10为一个合并空白格；不填0、不继承16.0')
for cap,v in zip(capacities,['5.40 5.00 4.40 4.00','5.60 5.00 4.80 4.40','5.80 5.40 5.10 4.60','6.00 5.60 5.20 4.80']): add(8,'JB/T12839','蒸发冷却式、冷却塔式',cap,'IPLVI',v,'COPI',note='两个物理型式共用同一源格，不把冷却塔式删除')
for cap,v in zip(['CC≤50','CC>50'],['4.40 3.90 3.40 2.70','4.20 3.75 3.20 2.70']): add(8,'JB/T12839','风冷式',cap,'IPLVI',v,'COPI')
specs=[('1',9,0,12,4),('2',9,1,5,4),('3',10,0,6,3),('4',10,1,15,5),('5',11,0,4,2),('6',11,1,11,2),('7',12,0,10,4),('8',12,1,6,3)]
audit=[]; source_tables=[]
for key,page,ti,count,col in specs:
    table=pdf.pages[page-1].find_tables()[ti]; raw=table.extract()
    assert len(rows[key])==count
    source_tables.append(dict(table=key,pdf_page=page,printed_page=page-6,bbox=table.bbox,raw=raw))
    for i,row in enumerate(rows[key]):
        row.update(pdf_page=page,printed_page=page-6,sheet='表'+key,excel_row=i+6)
        values=row['values']+[row['aux_value'],row['aux2_value']]
        for j,v in enumerate(values):
            if v is None: continue
            expected=raw[i+3][col+j]
            assert v==expected,(key,i,j,v,expected)
            bbox=table.rows[i+3].cells[col+j]
            audit.append(dict(table=key,source_row=i+1,source_column=col+j+1,pdf_page=page,printed_page=page-6,
                source_bbox_pt=list(bbox),sheet='表'+key,cell=['F','G','H','J','L'][j]+str(i+6),expected_lexical=v,extracted_lexical=expected,result='MATCH',method='图像转录+pdfplumber源格文本交叉，自核'))
a1=[dict(point=p,load=l,outlet=o,flow='0.172',dry=d,wet='—') for p,l,o,d in [('A','100','7','35'),('B','75','7','32.25'),('C','50','9','29.5'),('D','25','11','26.8')]]
hours=[277,205,180,110,94,61,25,20,20,11,4,0,0,0,0]
a2=[dict(j=i+1,temp=i+25,hours=v) for i,v in enumerate(hours)]
assert sum(hours)==1007
tabs=pdf.pages[13].find_tables()
for i,r in enumerate(a1):
    for col,field,xcol in [(1,'load','B'),(3,'outlet','C'),(4,'flow','D'),(5,'dry','E')]:
        sr=2 if field=='flow' else i+2
        text=tabs[0].extract()[sr][col].replace('b','').replace('%','').strip()
        assert text==r[field],(text,r[field])
        audit.append(dict(table='A.1',source_row=i+1,source_column=col+1,pdf_page=14,printed_page=8,source_bbox_pt=list(tabs[0].rows[sr].cells[col]),sheet='表A.1',cell=xcol+str(i+6),expected_lexical=r[field],extracted_lexical=text,result='MATCH',method='图像转录+源格文本；负荷率Excel以0～1存储'))
for i,r in enumerate(a2):
    sr=(i%8)+1; start=0 if i<8 else 3
    for offset,field,xcol in [(0,'j','A'),(1,'temp','B'),(2,'hours','C')]:
        value=str(r[field]); text=tabs[1].extract()[sr][start+offset]
        assert value==text
        audit.append(dict(table='A.2',source_row=i+1,source_column=start+offset+1,pdf_page=14,printed_page=8,source_bbox_pt=list(tabs[1].rows[sr].cells[start+offset]),sheet='表A.2',cell=xcol+str(i+6),expected_lexical=value,extracted_lexical=text,result='MATCH',method='图像转录+源格文本'))
audit.append(dict(table='A.2',source_row='合计',source_column=6,pdf_page=14,printed_page=8,source_bbox_pt=list(tabs[1].rows[8].cells[5]),sheet='表A.2',cell='C21',expected_lexical='1007',extracted_lexical=tabs[1].extract()[8][5],result='MATCH',method='原表合计与15项相加交叉'))
for idx,key in enumerate(['A.1','A.2']): source_tables.append(dict(table=key,pdf_page=14,printed_page=8,bbox=tabs[idx].bbox,raw=tabs[idx].extract()))
payload=dict(standard='GB 19577—2024',revision='Stage A r1',source_sha256=sha,pdf_pages=19,tables=rows,a1=a1,a2=a2)
for name,data in [('data/table_values.json',payload),('evidence/source_tables.json',source_tables),('evidence/cell_audit.json',audit)]:
    (ROOT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with (ROOT/'evidence/cell_audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=audit[0].keys());w.writeheader();w.writerows(audit)
print(json.dumps(dict(table_count=10,energy_rows=sum(map(len,rows.values())),energy_numeric_cells=sum(1 for r in audit if r['table'].isdigit()),all_numeric_checks=len(audit),a1_rows=4,a2_rows=15,source_pdf_pages=19),ensure_ascii=False))
