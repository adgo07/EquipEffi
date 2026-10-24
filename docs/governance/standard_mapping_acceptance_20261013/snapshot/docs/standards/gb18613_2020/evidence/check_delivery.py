"""本标准资料的相对链接、脚本语法与交付文件清单核对。"""
from pathlib import Path
import ast, hashlib, json, re
ROOT=Path(__file__).resolve().parents[1]
errors=[]; links=0
for p in ROOT.rglob('*.md'):
    if '_work' in p.parts: continue
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if target.startswith(('https:','http:','#')): continue
        links+=1
        if not (p.parent/target.split('#')[0]).exists(): errors.append(f'{p.name}: {target}')
for p in (ROOT/'evidence').glob('*.py'): ast.parse(p.read_text(encoding='utf-8'))
assert not errors, errors
files=[]
for p in sorted(ROOT.rglob('*')):
    if not p.is_file() or '_work' in p.parts or p.name.endswith('.inspect.ndjson') or p.name=='delivery_manifest.json': continue
    files.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
manifest=dict(date='2026-10-13',scope='docs/standards/gb18613_2020/',relative_links_checked=links,
              broken_links=[],python_syntax='PASS',independent_acceptance='NOT_RUN',files=files)
(ROOT/'evidence/delivery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'{links} links verified; {len(files)} files hashed; Python syntax parsed')
