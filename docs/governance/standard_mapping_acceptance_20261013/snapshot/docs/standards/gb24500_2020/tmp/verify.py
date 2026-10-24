"""Read-only verification: actual XLSX coordinates against PDF positioned text."""
from pathlib import Path
import csv, hashlib, json, re, unicodedata
import pdfplumber
from openpyxl import load_workbook
root=Path(__file__).resolve().parents[1]
repo=root.parents[2]
pdf=repo/'标准原文/11. GB+24500-2020 工业锅炉能效限定值及能效等级.pdf'
xlsx=root/'data/GB24500_2020_TABLE_VALUES.xlsx'
book=load_workbook(xlsx,data_only=False)
pages=pdfplumber.open(pdf)
def words(page,x0,x1,y0,y1):
 return [dict(w,text=unicodedata.normalize('NFKC',w['text'])) for w in pages.pages[page-1].extract_words() if x0<w['x0']<x1 and y0<w['top']<y1]
sources={}
def add(sheet,col,ws,start=6,part=None):
 for i,w in enumerate(ws):
  value=int(re.findall(r'\d+',w['text'])[part or 0])
  sources[(sheet,f'{col}{start+i}')]=(value,w)
add('表1 层状燃煤','F',words(4,405,420,245,640));add('表1 层状燃煤','G',words(4,478,490,245,640))
add('表2 流化床燃煤','F',words(5,490,505,180,550))
add('表3 生物质','F',words(5,385,403,695,740));add('表3 生物质','G',words(5,476,491,695,740))
add('表4 室燃','F',words(6,390,405,223,270))
add('表4 室燃','F',words(6,459,470,223,270),9,0)
add('表4 室燃','F',words(6,459,470,223,270),12,1)
add('表4 室燃','F',words(6,430,446,278,376),15)
expected=json.loads((root/'tmp/expected_cells.json').read_text())
assert len(expected)==len(sources)==78
rows=[]
for e in expected:
 key=(e['sheet'],e['cell']); value,w=sources[key]; actual=book[e['sheet']][e['cell']].value
 assert value==actual==e['value'],(key,value,actual,e['value'])
 rows.append([e['sheet'],e['cell'],e['branch'],e['grade'],e['pdf_page'],f"{w['x0']:.2f},{w['top']:.2f},{w['x1']:.2f},{w['bottom']:.2f}",w['text'],value,actual,'MATCH','执行者AI；2026-10-13；非独立验收'])
assert book['限定值与来源']['B5'].value==97
assert '97%' in unicodedata.normalize('NFKC',pages.pages[5].extract_text())
assert not any(c.data_type=='f' for s in book for row in s for c in row)
assert len(book.sheetnames)==5
with (root/'evidence/cell_verification.csv').open('w',encoding='utf-8-sig',newline='') as f:
 wr=csv.writer(f);wr.writerow(['sheet','cell','branch','grade','pdf_physical_page','pdf_bbox_pt','source_token','source_value','xlsx_value','result','review']);wr.writerows(rows)
report={'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'xlsx_sha256':hashlib.sha256(xlsx.read_bytes()).hexdigest(),'source_table_count':4,'normalized_rows':[18,21,3,15],'threshold_cells':78,'pass':78,'fail':0,'error':0,'skip':0,'clause_5_2_cell':'限定值与来源!B5','clause_5_2_value':97,'clause_5_2_result':'PASS','formula_cells':0,'independent_acceptance':'NOT_RUN','native_excel':'NOT_RUN','production_tests':'NOT_RUN (documentation only)'}
(root/'evidence/verification_summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
