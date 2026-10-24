"""只读用户PDF；提取校对资料，非运行时标准数据或业务算法。
运行目录为仓库根；全部输出限制到本标准目录。
"""
from pathlib import Path
import csv, hashlib, json, re, unicodedata
import pdfplumber
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
(ROOT/'_work').mkdir(exist_ok=True)
REPO = ROOT.parents[2]
SOURCE = REPO / '标准原文/2. GB+18613-2020 电动机能效限定值及能效等级.pdf'
EXPECTED_SHA = 'ba617a76b79cecdda57fab3950ecccaecbb1b2997645192f0429395468167304'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED_SHA
N = lambda s: unicodedata.normalize('NFKC', s or '').replace(' ', '').replace('\n', '')
specs = [
    (1,4,0,3,31,'三相异步电动机','kW',[2,4,6,8]),
    (2,5,0,3,11,'电容起动异步电动机','W',[2,4,6]),
    (3,5,1,3,9,'电容运转异步电动机','W',[2,4,6]),
    (4,6,0,3,9,'双值电容异步电动机','W',[2,4]),
    (5,6,1,3,17,'空调器风扇用电容运转电动机','W',[4,6,8]),
    (5,7,0,3,7,'空调器风扇用电容运转电动机','W',[4,6,8]),
    (6,7,1,4,18,'空调器风扇用无刷直流电动机','W',[]),
    (6,8,0,4,6,'空调器风扇用无刷直流电动机','W',[]),
]
tables, audit, structure, headers = {}, [], [], []
pdf = pdfplumber.open(SOURCE)
reader = PdfReader(SOURCE)
for tid, page, ti, skip, count, title, unit, poles in specs:
    table = pdf.pages[page-1].find_tables()[ti]
    raw = table.extract()
    for hi in range(skip):
        for ci, box in enumerate(table.rows[hi].cells):
            if box is None: continue
            headers.append(dict(table=tid,pdf_page=page,header_row=hi+1,source_column=ci+1,
                text=N(raw[hi][ci]),source_bbox_pt=','.join(f'{x:.3f}' for x in box),
                note='源表头矩形覆盖；源数据体格边界与独立列标签见source_cell_audit.csv'))
    body = raw[skip:skip+count]
    assert len(body) == count
    labels = ([f'{g}级/{p}极' for g in [1,2,3] for p in poles] if tid != 6 else
              [f'{s}/{g}级' for s in ['≤500','500～700','700～1000','1000～1300','>1300'] for g in [1,2,3]])
    t = tables.setdefault(tid, dict(id=tid,title=title,unit=unit,labels=labels,rows=[],sources=[]))
    independent_text = re.sub(r'\s+', '', N(reader.pages[page-1].extract_text()))
    for ri, row in enumerate(body):
        row = [N(x) for x in row]
        assert len(row) == len(labels)+1, (tid,ri,row)
        assert ''.join(row) in independent_text, ('pypdf row mismatch',tid,page,ri,row)
        xrow = len(t['rows'])+6
        t['rows'].append(row)
        t['sources'].append([page,page-2,ri+1])
        for ci, v in enumerate(row):
            box = table.rows[skip+ri].cells[ci]
            assert box is not None, ('unexpected body merge',tid,ri,ci)
            kind = ('EMPTY_SOURCE' if v=='' else 'DASH_SOURCE' if v=='—' else 'POWER_RANGE' if ci==0 and '~' in v else 'NUMBER')
            # 工作簿保留百分数点值，显示0.0；空白保持空白，横杠保持文本。
            col = chr(65+ci)
            audit.append(dict(source_sha256=EXPECTED_SHA,table=tid,pdf_page=page,printed_page=page-2,
                source_body_row=ri+1,power=row[0],power_unit=unit,source_column=ci+1,
                branch='额定功率' if ci==0 else labels[ci-1],source_bbox_pt=','.join(f'{x:.3f}' for x in box),
                source_lexeme=v,source_kind=kind,sheet=f'表{tid}',cell=f'{col}{xrow}',
                pdfplumber_pypdf_check='MATCH_ROW_ORDER',visual_review='AUTHOR_PAGE_REVIEW',
                independent_acceptance='NOT_PERFORMED'))
    structure.append(dict(table=tid,pdf_page=page,printed_page=page-2,body_rows=count,
                          threshold_columns=len(labels),bbox=table.bbox,header_rows=skip,
                          body_merged_cells=0))
assert [len(t['rows']) for t in tables.values()] == [31,11,9,9,24,24]
assert sum(a['source_kind']=='EMPTY_SOURCE' for a in audit)==1
out = dict(source_sha256=EXPECTED_SHA,source_relative_path=str(SOURCE.relative_to(REPO)).replace('\\','/'),tables=list(tables.values()))
(ROOT/'_work/tables.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
with (ROOT/'evidence/source_cell_audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(audit[0])); w.writeheader(); w.writerows(audit)
with (ROOT/'evidence/header_geometry.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(headers[0])); w.writeheader(); w.writerows(headers)
stats = dict(source_sha256=EXPECTED_SHA,pages=8,tables=6,table_parts=8,power_rows=108,
             threshold_slots=sum(len(t['rows'])*len(t['labels']) for t in tables.values()),
             numeric_thresholds=sum(a['source_column']>1 and a['source_kind']=='NUMBER' for a in audit),
             dashes=sum(a['source_kind']=='DASH_SOURCE' for a in audit),blanks=1,
             audited_cells=len(audit),pypdf_row_checks=108,pypdf_row_failures=0,parts=structure,
             method='pdfplumber grid + pypdf ordered row text; author page-image review; not independent acceptance')
(ROOT/'evidence/structure_check.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in stats.items() if k!='parts'},ensure_ascii=False))
