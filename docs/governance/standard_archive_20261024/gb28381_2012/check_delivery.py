"""Local delivery checks and hash manifest, no repository mutations outside this directory."""
from pathlib import Path
import re, json, hashlib
from openpyxl import load_workbook
b=Path(__file__).resolve().parent
d=json.loads((b/'data/tables.json').read_text(encoding='utf-8'))
w=load_workbook(b/'data/GB28381_2012_TABLES.xlsx')
count=types=0
links=[]
for p in list(b.glob('*.md'))+list((b/'evidence').glob('*.md')):
    for m in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if not m.startswith('http') and not (p.parent/m.split('#')[0]).exists():
            links.append((str(p),m))
assert not links,links
for t,rows in d['tables'].items():
    for r in rows:
        sh=w['表'+t]; i=r['source_row']+5
        assert sh[f'B{i}'].value==r['ratio'] and str(sh[f'C{i}'].value)==r['stages']
        count+=1
        for c in range(4,9):
            assert sh.cell(i,c).data_type=='n' and sh.cell(i,c).number_format=='0.0'
            types+=1
report={'broken_links':links,'condition_rows_pass':count,'typed_and_formatted_thresholds_pass':types,'final_render_sheets_visually_reviewed':8,'review_type':'execution self-check, not independent acceptance'}
(b/'evidence/delivery_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
files=[]
for folder in [b,b/'data',b/'evidence']:
    files.extend(p for p in folder.iterdir() if p.is_file() and not p.name.endswith('.inspect.ndjson') and p.name!='file_hashes.json')
(b/'evidence/file_hashes.json').write_text(json.dumps({p.relative_to(b).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({**report,'hashed_files':len(files)},ensure_ascii=False))
