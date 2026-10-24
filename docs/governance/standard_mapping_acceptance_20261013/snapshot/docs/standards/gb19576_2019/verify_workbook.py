"""Read-only checks; PDF text comparison is not independent visual acceptance."""
from pathlib import Path
from decimal import Decimal
import csv, hashlib, json, unicodedata
import pdfplumber
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
PDF = REPO / '标准原文/16. GB 19576_2019 单元式空气调节机能效限定值及能效等级.pdf'
XLSX = ROOT / 'data/GB19576_2019_TABLE1.xlsx'
expected_hash = '1c5c97fd39351ed9708fd69f45c9b37dfba8fccea3cc4f810b32de3522876026'
assert hashlib.sha256(PDF.read_bytes()).hexdigest() == expected_hash
with pdfplumber.open(PDF) as doc:
    assert len(doc.pages) == 4
    t3 = doc.pages[2].extract_tables()
    t4 = doc.pages[3].extract_tables()
    assert len(t3) == len(t4) == 1
    rows = t3[0][2:] + t4[0][2:-1]
    assert len(rows) == 13
    expected = [[unicodedata.normalize('NFKC', v) for v in r[-3:]] for r in rows]
wb = load_workbook(XLSX, data_only=False)
assert wb.sheetnames == ['表1']
ws = wb['表1']
audit = list(csv.DictReader((ROOT / 'evidence/cell_audit.csv').open(encoding='utf8')))
assert len(audit) == 39
checks=[]
for i, row in enumerate(expected):
    for j, lex in enumerate(row):
        cell = ws.cell(i+6, j+7)
        a = audit[i*3+j]
        ok = (cell.data_type == 'n' and Decimal(str(cell.value)) == Decimal(lex)
              and cell.number_format == '0.00' and a['source_lexical'] == lex
              and a['xlsx_cell'] == f'表1!{cell.coordinate}')
        checks.append({'cell':f'表1!{cell.coordinate}','pdf_lexical':lex,
                       'xlsx_value':str(cell.value),'display_format':cell.number_format,'pass':ok})
assert all(c['pass'] for c in checks)
assert [ws.cell(i,1).value for i in range(6,19)] == list(range(1,14))
assert all(ws.cell(i,c).value is not None for i in range(6,19) for c in range(1,12))
assert not any(c.data_type == 'f' for row in ws for c in row)
assert [ws['D10'].value,ws['D11'].value] == ['CC>14000','7000≤CC≤14000']
assert len(set((ws.cell(i,2).value,ws.cell(i,3).value,ws.cell(i,4).value) for i in range(6,19))) == 13
report={'source_sha256':expected_hash,'workbook_sha256':hashlib.sha256(XLSX.read_bytes()).hexdigest(),
        'pdf_pages':4,'logical_tables':1,'page_table_fragments':2,'branches':13,
        'numeric_cells':{'pass':len(checks),'fail':0,'error':0,'skip':0,'not_run':0},
        'independent_acceptance':'NOT_RUN','cells':checks}
(ROOT/'evidence/verification_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='cells'},ensure_ascii=False))
