"""Verify unchanged source hashes and refresh a local delivery manifest."""
from pathlib import Path
import hashlib,json,re
O=Path(__file__).resolve().parent
ROOT=O.parents[2]
inventory_path=O/'evidence/source_inventory.json'
inventory=json.loads(inventory_path.read_text(encoding='utf8'))
for row in inventory:
    assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'],row['id']
    row.pop('cover_text',None)
inventory_path.write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf8')
p=O/'ISSUE_REGISTRATION_REQUEST.md'
p.write_text(p.read_text(encoding='utf8').replace('AMBI\u00adGUITY','AMBIGUITY'),encoding='utf8')
p=O/'SOURCE_AUTHENTICITY.md'
p.write_text(p.read_text(encoding='utf8').replace('末页空白，需另核正文终止页','正文终止于PDF9参考文献结束线，PDF10—11空白'),encoding='utf8')
for p in O.rglob('*.md'):
    if 'node_modules' in p.parts or 'tmp' in p.parts:continue
    for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf8')):
        if '://' in link or link.startswith('#'):continue
        target=(p.parent/link.split('#')[0]).resolve()
        assert target.exists() or target==O/'evidence/delivery_manifest.json',(p,link)
items=[]
for p in sorted(O.rglob('*')):
    if not p.is_file() or any(x in p.relative_to(O).parts for x in ('tmp','node_modules','__pycache__')):continue
    if p.name=='delivery_manifest.json' or p.name.endswith('.inspect.ndjson'):continue
    items.append(dict(path=p.relative_to(O).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(O/'evidence/delivery_manifest.json').write_text(json.dumps(dict(date='2026-10-13',algorithm='SHA-256',excludes=['self','tmp/','node_modules/','__pycache__/','*.inspect.ndjson'],files=items),ensure_ascii=False,indent=2),encoding='utf8')
print(f'PASS: {len(inventory)} source hashes unchanged; local Markdown links resolve; {len(items)} delivery hashes recorded.')
