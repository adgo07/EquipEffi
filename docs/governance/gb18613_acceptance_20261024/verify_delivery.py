from pathlib import Path
import sys, re, json, hashlib, csv, ast

root=Path(sys.argv[1]).resolve()
archive=root/'docs/governance/gb18613_acceptance_20261024'
for name in ('ROADMAP.md','HANDOFF.md','BASELINE.md'):
    assert not (root/name).exists(),name
hashes=json.loads((archive/'DELIVERY_HASHES.json').read_text(encoding='utf-8'))
for path,digest in hashes.items():
    assert hashlib.sha256((root/path).read_bytes()).hexdigest()==digest,path
for entry in json.loads((archive/'ARCHIVE_MANIFEST.json').read_text(encoding='utf-8'))['files']:
    assert hashlib.sha256((archive/entry['archived_path']).read_bytes()).hexdigest()==entry['sha256']
records=list(csv.DictReader((archive/'evidence/cell_compare.csv').open(encoding='utf-8-sig')))
assert len(records)==1290 and all(r['result']=='PASS' for r in records)
for script in archive.glob('*.py'):
    ast.parse(script.read_text(encoding='utf-8-sig'))
paths=[root/'docs/standards/gb18613_2020/STANDARD_MAPPING.md',root/'docs/governance/gb18613_revision_20261024/REPORT.md',*archive.rglob('*.md')]
links=0
for p in paths:
    for raw in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8-sig')):
        t=raw.strip('<>')
        if '://' in t or t.startswith('#'):continue
        assert not re.match(r'^[A-Za-z]:',t),(p,t)
        dst=(p.parent/t.split('#')[0]).resolve()
        assert dst.is_relative_to(root) and dst.exists(),(p,t)
        links+=1
mapping=paths[0].read_text(encoding='utf-8-sig')
assert not re.search(r'EQP-STD-GB18613-\d+|_gb18613_acceptance|ROADMAP',mapping)
assert len(re.findall(r'^\|BC-\d+',mapping,re.M))==26
print(json.dumps({'status':'PASS','local_links':links,'candidate_groups':26,'archived_cell_records':1290,'source_hashes':'PASS','retired_files_absent':True,'scope':'Clean Git tree document and archive integrity, not production tests'},ensure_ascii=False))
