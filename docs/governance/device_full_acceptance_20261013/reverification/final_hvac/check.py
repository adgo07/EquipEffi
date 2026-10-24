from pathlib import Path
import json,hashlib
root=Path.cwd();o=root/'docs/governance/device_full_acceptance_20261013/reverification/final_hvac'
m=json.loads((root/'docs/governance/device_full_acceptance_20261013/hvac/source_manifest.json').read_text(encoding='utf-8'))
a=[]
for x in m:
 p=Path(x['path']); h=hashlib.sha256(p.read_bytes()).hexdigest();a.append(dict(path=str(p),first_sha256=x['sha256'],current_sha256=h,unchanged=h==x['sha256']))
(o/'baseline_comparison.json').write_text(json.dumps(a,ensure_ascii=False,indent=2),encoding='utf-8')
for x in a:
 if not x['unchanged']:print(x['path'])
print('total',len(a),'changed',sum(not x['unchanged'] for x in a))
for p in [root/'STANDARD_ISSUES_REGISTER.md',root/'platform-lock.json']:
 (o/(p.stem+'_snapshot.txt')).write_bytes(p.read_bytes())
