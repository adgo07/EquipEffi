from pathlib import Path
import json,hashlib,re,collections,subprocess
R=Path.cwd();O=R/'docs/governance/device_round3_review_20261013/hvac'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
claims=json.loads((O/'claim_verification.json').read_text('utf8'))
alias={'B1':['ROUND3-A5','ROUND3-H1'],'B2':['ROUND3-B2','ROUND3-H2'],'M1':['ROUND3-A2','ROUND3-H3','OLD19577-F01'],'M2':['ROUND3-A3','ROUND3-H4','OLD21454-8'],'M3':['ROUND3-H5'],'M4':['ROUND3-H5'],'M6':['ROUND3-H6'],'M7':['ROUND3-B7','ROUND3-H7'],'M8':['ROUND3-H8'],'m1':['ROUND3-B5'],'i2':['ROUND3-B3']}
for x in claims['claims']:x['source_opinion_ids']=[x['original_id']]+alias.get(x['original_id'].removeprefix('HVAC-R3-'),[])
(O/'claim_verification.json').write_text(json.dumps(claims,ensure_ascii=False,indent=2),encoding='utf8')
# Check count sets exactly, not third-party prose.
root=(R/'STANDARD_ISSUES_REGISTER.md').read_text('utf-8-sig');ids=set(re.findall(r'^### (EQP-STD-\S+)',root,re.M));f=R/'docs/governance/device_full_acceptance_20261013/reverification/issue_registration_audit.csv'
print('audit file exists',f.exists())
for p in (R/'docs/governance/device_full_acceptance_20261013/reverification').glob('*.csv'):print(p.name)
# fresh provenance for supplemental inputs and images actually viewed this turn
extras=[R/'docs/governance/device_full_acceptance_20261013/third_party_executor_verification_20261013/EXECUTOR_VERIFICATION.md',R/'docs/governance/device_round3_review_20261013/DISPATCH_INITIAL.md',R/'docs/governance/device_round3_review_20261013/INPUT_MANIFEST.json',R/'docs/standards/gb29541_2013/evidence/REVIEW_20261013_independent_review.md']
viewed={'29541':[4],'19576':[3,4],'37479':[4,5],'21454':[9,13,14],'19577':[8,9,10,11,14,16,17]}
for s,ps in viewed.items():
 for p in ps:extras.append(R/f'docs/governance/device_full_acceptance_20261013/hvac/{s}/p{p:02}.png')
extras += list(O.glob('*.png'))
(O/'supplemental_evidence_manifest.json').write_text(json.dumps([dict(path=str(p),sha256=sha(p)) for p in extras],ensure_ascii=False,indent=2),encoding='utf8')
print('owner count',len(json.loads((O/'owner_items.json').read_text('utf8'))))
