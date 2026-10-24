"""Read-only source/XLSX audit. Run with bundled Python; no workbook authoring."""
from pathlib import Path
import csv, hashlib, json, re, unicodedata, zipfile
from decimal import Decimal
import xml.etree.ElementTree as ET
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
PDF = REPO / '标准原文/15. GB_37479-2019 风管送风式空调机组能效限定值及能效等级.pdf'
XLSX = ROOT / 'data/GB37479_2019_TABLE_VALUES.xlsx'
SHA = 'cf4bef6fca2b88c5ed1a78006c0a6c411fa74330241e9b373c76d8684a338fde'
assert hashlib.sha256(PDF.read_bytes()).hexdigest() == SHA
pdf = PdfReader(PDF)
assert len(pdf.pages) == 5
raw = unicodedata.normalize('NFKC', pdf.pages[3].extract_text())
expected = re.findall(r'(?<!\d)\d\.\d{2}(?!\d)', raw)
assert len(expected) == 66, expected
ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(XLSX) as z:
    strings = []
    if 'xl/sharedStrings.xml' in z.namelist():
        strings = [''.join(si.itertext()) for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
    sheets=[]
    for i in range(1,4):
        xml=ET.fromstring(z.read(f'xl/worksheets/sheet{i}.xml'))
        cells={}
        for c in xml.findall('.//m:sheetData/m:row/m:c',ns):
            v=c.find('m:v',ns)
            value=v.text if v is not None else None
            if c.get('t')=='s': value=strings[int(value)]
            if c.get('t')=='inlineStr': value=''.join(c.find('m:is',ns).itertext())
            cells[c.get('r')]=value
        assert not xml.findall('.//m:f',ns), 'Unexpected calculation formula'
        sheets.append(cells)
rows=json.loads((ROOT/'data/table_rows.json').read_text(encoding='utf-8'))
assert len(rows)==22
audit=[]; pos=0
for rec in rows:
    cells=sheets[0 if rec['table']=='表1' else 1]; row=rec['xlsx_row']
    for col,key in [('B','cooling'),('C','branch'),('D','metric'),('E','unit'),('F','condition')]:
        assert cells[f'{col}{row}']==rec[key]
    for col,key in [('G','lower'),('H','upper')]:
        actual=cells.get(f'{col}{row}')
        assert (actual is None if rec[key] is None else Decimal(actual)==Decimal(rec[key]))
    for grade,col in enumerate('IJK',1):
        coord=f'{rec["sheet"]}!{col}{row}'
        actual=cells[f'{col}{row}']; exp=expected[pos]; pos+=1
        ok=Decimal(actual)==Decimal(exp)
        audit.append([SHA,4,2,rec['table'],rec['source_row'],grade,coord,exp,actual,'PASS' if ok else 'FAIL','PDF文本逐值比对+原页视觉自核；非独立验收'])
        assert ok,(coord,exp,actual)
constants=['0','0','0.95','1.10','2','29','35','1.077','0.914']
for r,value in enumerate(constants,2): assert Decimal(sheets[2][f'B{r}'])==Decimal(value)
with (ROOT/'evidence/clause_numeric_audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['source_sha256','pdf_page','clause','xlsx_cell','visually_transcribed_expected','xlsx_actual','result','scope'])
    for r,(value,clause) in enumerate(zip(constants,['1','5.3','5.4b','5.4d','6.1/6.3','6.1a','6.1a','6.1a','6.1a']),2):
        w.writerow([SHA,3 if r==2 else 5,clause,f'条款数值!B{r}',value,sheets[2][f'B{r}'],'PASS','执行者源页自核后的导出一致性；非独立验收'])
with (ROOT/'evidence/numeric_audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['source_sha256','pdf_page','printed_page','table','source_data_row','grade','xlsx_cell','pdf_expected','xlsx_actual','comparison','method']); w.writerows(audit)
summary={'pdf_pages':5,'tables':2,'physical_branches':7,'table_rows':22,'grade_cells':{'pass':66,'fail':0,'error':0,'skip':0},'clause_values':{'pass':9,'fail':0},'row_identity_checks':110,'endpoint_checks':44,'xlsx_formula_count':0,'independent_cell_acceptance':'NOT_RUN','production_unittest':'NOT_RUN: Stage A only','compileall':'NOT_RUN: no production changes','smoke':'NOT_RUN: no product execution','performance':'NOT_RUN: no performance task','pdf_sha256':SHA,'xlsx_sha256':hashlib.sha256(XLSX.read_bytes()).hexdigest()}
(ROOT/'evidence/check_results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
