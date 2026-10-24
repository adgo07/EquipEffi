from pathlib import Path
import json,hashlib,re,collections
R=Path.cwd();O=R/'docs/governance/device_round3_review_20261013/hvac'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
first=json.loads((O/'source_manifest_start.json').read_text('utf8')); earliest=json.loads((R/'_acceptance_20261013/accepted_revision_manifest.json').read_text('utf-8-sig'))
out=[]
for x in first:
 p=Path(x['path'])
 if p.name=='STANDARD_MAPPING.md' or p.suffix=='.xlsx':
  k=p.parent.name if p.name=='STANDARD_MAPPING.md' else p.parent.parent.name
  rel=p.relative_to(R/'docs/standards'/k).as_posix();e=earliest['standards'].get(k,{}).get('files',{}).get(rel)
  out.append(dict(path=str(p),current_sha256=sha(p),hvac_full_review_sha256=x.get('first_hvac_sha256'),earlier_12_standard_sha256=e['sha256'] if e else None,comparison='not_in_12_scope' if not e else 'unchanged' if e['sha256']==sha(p) else 'changed'))
(O/'named_baselines.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
# snapshot format inspection
p=R/'_acceptance_20261013/round3/evidence_snapshots/gb19577_2024__GB19577_2024_TABLE_VALUES.txt';print(p.read_text('utf-8-sig')[:1800])
print('baseline',[(Path(x['path']).parent.name,x['comparison']) for x in out])
print('root count',len(re.findall(r'^### (EQP-STD-\S+)',(R/'STANDARD_ISSUES_REGISTER.md').read_text('utf-8-sig'),re.M)))
