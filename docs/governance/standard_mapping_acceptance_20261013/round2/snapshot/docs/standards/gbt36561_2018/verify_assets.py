"""只读XLSX核验；不写工作簿。数值样本预期来自执行者原PDF页图自核。"""
from pathlib import Path
import csv,json,hashlib,re
from collections import Counter
from decimal import Decimal
from openpyxl import load_workbook
R=Path(__file__).resolve().parent
source=R.parents[2]/'标准原文/12. GBT+36561-2018 清洁节能热处理装备技术要求及评价体系.pdf'
sha=hashlib.sha256(source.read_bytes()).hexdigest()
assert sha=='f1a6b29aa25d13b69f16006dd822e4ad2641830468bd6c395056e6751095ba37'
records=json.loads((R/'evidence/workbook_coordinates.json').read_text(encoding='utf-8'))
wb=load_workbook(R/'data/GBT36561_2018_TABLE_VALUES.xlsx',read_only=False,data_only=False)
fail=[];checks=0
for r in records:
    actual=wb[r['sheet']][r['value_cell']]
    checks+=1
    if actual.value!=r['value']:fail.append([r['record_id'],actual.value,r['value']])
    assert actual.data_type!='f'
    if isinstance(r['value'],(int,float)):
        assert actual.data_type=='n'
        assert Decimal(str(actual.value))==Decimal(r['source_numeric_text'])
    row=int(r['value_cell'][1:]); sh=wb[r['sheet']]
    assert sh[f'A{row}'].value==r['record_id']
    assert sh[f'C{row}'].value==r['branch']
    assert sh[f'D{row}'].value==r['metric']
    assert sh[f'J{row}'].value==r['printed_page']
    assert sh[f'K{row}'].value==r['pdf_page']==r['printed_page']+3
assert not fail,fail
assert len({r['record_id'] for r in records})==468
assert set(r['table'] for r in records)==set(map(str,range(1,18)))|{f'A.{i}' for i in range(1,13)}
# 这些预期是单独写下的原图读值，不从待核JSON取值，不等于独立人员复核。
samples=[
('1','ⅢA','温度均匀性',8),('1','Ⅵ','记录仪表准确度级别',1.),
('2','真空热处理/淬火、回火、时效','炉温均匀性',5),
('3','Ⅰ','系统准确度校验周期',2),('3','ⅢA','最大允许调整量/最高工作温度百分数',.38),
('4','电子管式及其他','输出电压',2.5),('5','≤1 s','综合精度',.10),
('6','顶尖连线对滑板移动平行度','顶尖连线对滑板移动平行度',.3),
('7','大型井式渗碳炉','加热元件',10000),
('8','r01 传送式连续炉','一等可比单耗上限',330),
('8','r14 井式炉/气体渗碳(氮)炉','二等可比单耗上限',1230),
('8','r26 罩式炉','三等可比单耗上限',200),
('9','r3 发生炉煤气','热值下限',586),('9','r2 发生炉煤气','α',.95),
('9','r5 天然气','α',1.10),
('10','真空电阻炉/外热式','炉门或炉盖三等',60),
('11','底装料立式多用炉','升温时间',2.),
('12','间歇式/电热浴炉','三等',40),('12','真空电阻炉/淬火、回火、热处理和钎焊、烧结、渗碳、退火','二等',26),
('13','汞','排放限值',.010),('14','11 钒','最高容许排放浓度',1.),
('14','12 钡','最高容许排放浓度',5.),
('15','可比能耗或单位产品能耗','二等分值',20),
('16','源序号8/9 感应、激光加热装置/激光热处理、激光器','分值',2),
('16','源序号13 空炉升温时间','分值',13),('17','二级(良好)','综合评价指数下限',70),
('A.1','淬火-中温(>350～450℃)回火','K1',1.50),
('A.2','渗碳','K1',2.5),('A.3','渗碳层深度≥0.8～1.4 mm','K8',1.2),
('A.4','工件单件重≤0.2～0.07 kg(原序照录)','K9',1.6),
('A.5','退火保温≥20 h','K1',1.7),('A.6','铝合金淬火','K1',1.4),
('A.6','回火温度≤350℃','K11',.6),('A.7','碳氮共渗','K1',.81),
('A.7','气体渗氮/≤0.4 mm','K8',.9),('A.8','均匀化退火','K1',2.6),
('A.9','工具、模具、机修热处理车间(不含专业生产厂)','K10',1.2),
('A.10','淬火+回火/回火温度≥500℃','K1',1.7),
('A.11','等温退火/球化退火/合金钢','K1',1.2),
('A.11','去氢处理>25 h/100 mm','K1',2.4),('A.12','计算工件尺寸≤300 mm','K4',0.),
('A.12','计算工件尺寸>800～1000 mm','K4',2.5)]
audit=[]
for t,b,m,expected in samples:
    matches=[r for r in records if (r['table'],r['branch'],r['metric'])==(t,b,m)]
    assert len(matches)==1,(t,b,m,len(matches))
    r=matches[0];actual=wb[r['sheet']][r['value_cell']].value
    audit.append(dict(pdf_sha256=sha,table=t,printed_page=r['printed_page'],pdf_page=r['pdf_page'],source_cell=r['source_cell'],sheet=r['sheet'],cell=r['value_cell'],expected=expected,actual=actual,result='MATCH' if actual==expected else 'MISMATCH',method='执行者原页图像读值自核；非独立验收',reviewer='Codex本会话',date='2026-10-13'))
assert all(a['result']=='MATCH' for a in audit)
with (R/'evidence/numeric_review.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=audit[0]);w.writeheader();w.writerows(audit)
tables=list(dict.fromkeys(r['table'] for r in records))
lines=['# 标准表与工作簿真实坐标','', '由verify_assets.py按已导出XLSX核对生成。范围包括同表全部指标记录，不代表原文逐格已独立验证。','', '|源表|记录数|数值记录数|工作簿范围（含条件/定位）|数值坐标|印刷页|PDF物理页|','|---|---:|---:|---|---|---|---|']
for t in tables:
    rs=[r for r in records if r['table']==t];first=rs[0]['value_cell'][1:];last=rs[-1]['value_cell'][1:];s=rs[0]['sheet']
    lines.append(f'|{t}|{len(rs)}|{sum(isinstance(r["value"],(int,float)) for r in rs)}|{s}!A{first}:K{last}|{s}!F{first}:F{last}|'+','.join(map(str,sorted({r['printed_page'] for r in rs})))+'|'+','.join(map(str,sorted({r['pdf_page'] for r in rs})))+'|')
(R/'evidence/TABLE_LOCATIONS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
sum16=sum(r['value'] for r in records if r['table']=='16'); assert sum16==100
result={'source_sha256':sha,'table_count':len(tables),'record_count':len(records),'numeric_records':sum(isinstance(r['value'],(int,float)) for r in records),'symbol_or_dash_records':sum(isinstance(r['value'],str) for r in records),'xlsx_coordinate_value_checks':{'pass':checks,'fail':len(fail),'error':0,'skip':0},'numeric_source_sample':{'match':len(audit),'mismatch':0,'tables':len(set(a['table'] for a in audit)),'not_second_checked_numeric_records':456-len(audit),'independent_review':'NOT_RUN'},'table16_unique_scoring_cells_sum':sum16,'formula_cells':sum(c.data_type=='f' for s in wb for row in s for c in row),'software_unittest':'NOT_RUN - documentation-only','compileall':'NOT_RUN - no production changes','smoke':'NOT_RUN - no production changes','performance':'NOT_RUN - no production changes'}
(R/'evidence/check_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
local_links=0
for md in list(R.glob('*.md'))+list((R/'evidence').glob('*.md')):
    text=md.read_text(encoding='utf-8')
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if target.startswith(('http:','https:','#')):continue
        f=(md.parent/target.split('#')[0]).resolve()
        if f.name=='SHA256SUMS.json':continue
        assert f.exists(),(md.name,target)
        local_links+=1
result['local_markdown_file_links']={'pass':local_links,'fail':0,'note':'file targets checked; heading anchors not parsed'}
(R/'evidence/check_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
files=list(R.glob('*.md'))+list(R.glob('*.py'))+list(R.glob('*.mjs'))+[R/'.gitignore']
files+=list((R/'data').glob('*.csv'))+list((R/'data').glob('*.json'))+list((R/'data').glob('*.xlsx'))
files+=list((R/'evidence').glob('*.md'))+list((R/'evidence').glob('*.csv'))+[R/'evidence/check_results.json',R/'evidence/workbook_coordinates.json']
hashes={str(p.relative_to(R)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
(R/'evidence/SHA256SUMS.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
