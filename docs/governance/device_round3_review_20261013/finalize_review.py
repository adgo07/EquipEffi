import json,hashlib,re,datetime
from pathlib import Path

out=Path(__file__).resolve().parent
root=out.parents[2]
initial=json.loads((out/'INPUT_MANIFEST.json').read_text(encoding='utf-8'))
changed=[]; missing=[]
for x in initial['files']:
    p=root/x['relative_path']
    if not p.is_file(): missing.append(x['relative_path']); continue
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    if h!=x['sha256']: changed.append(dict(path=x['relative_path'],before=x['sha256'],after=h))
links=[]
for name in ['REVIEW_SUMMARY.md','OWNER_REVIEW_INDEX.md','CONFIRMED_MAINTENANCE.md']:
    p=out/name
    for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if not target.startswith(('http:','https:')) and not (p.parent/target.split('#')[0]).exists():
            links.append({'file':name,'target':target})
extra=[]
for rel in ['docs/governance/device_full_acceptance_20261013/third_party_executor_verification_20261013/EXECUTOR_VERIFICATION.md']:
    p=root/rel
    extra.append(dict(path=rel,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
sources=[]
for p in out.rglob('*'):
    if p.is_file() and p.name not in ['FINAL_VERIFICATION.json','DELIVERABLE_MANIFEST.json']:
        sources.append(dict(path=p.relative_to(out).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(out/'DELIVERABLE_MANIFEST.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf-8')
result=dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),initial_files=len(initial['files']),changed=changed,missing=missing,broken_entry_links=links,supplementary_inputs=extra,deliverable_files=len(sources),owner_coverage=json.loads((out/'OWNER_COVERAGE_CHECK.json').read_text(encoding='utf-8')),production_tests='NOT_RUN; read-only audit, no production code change',sources_changed_by_this_review=False)
(out/'FINAL_VERIFICATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ['initial_files','changed','missing','broken_entry_links','deliverable_files']},ensure_ascii=False))
assert not changed and not missing and not links
