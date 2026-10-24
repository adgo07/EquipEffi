from pathlib import Path
import json,re,csv,hashlib,collections
R=Path.cwd();O=R/'docs/governance/device_round3_review_20261013/hvac';f=R/'_acceptance_20261013/round3/final_hvac_AUDIT.md';lines=f.read_text('utf-8-sig').splitlines();start=next(i for i,l in enumerate(lines) if l.startswith('## 5.'))
d=json.loads((O/'claim_verification.json').read_text('utf8'))
for x in d['claims']:
 id=x['original_id'].replace('HVAC-R3-',''); hits=[(i+1,l) for i,l in enumerate(lines) if i>start and re.match(r'\| '+re.escape(id)+r' \|',l)]
 assert len(hits)==1,(id,hits)
 x['verified_fact_summary']=x['original_opinion'];x['original_source_row']=hits[0][1];x['source_line']=hits[0][0];x['source_path']=str(f);x['source_sha256']=hashlib.sha256(f.read_bytes()).hexdigest();x['original_opinion']=hits[0][1]
for x in d['history_crosswalk']:
 x['source_line']=lines.index(x['verbatim_opinion_row'])+1;x['source_path']=str(f)
(O/'claim_verification.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
p=O/'CLAIM_VERIFICATION.md';s=p.read_text('utf8').replace('原意见要点：','核实事实要点（原意见逐字见JSON original_source_row/source_line）：');p.write_text(s,encoding='utf8')
root=(R/'STANDARD_ISSUES_REGISTER.md').read_text('utf-8-sig');ids=set(re.findall(r'^### (EQP-STD-\S+)',root,re.M));added={r['id'] for r in csv.DictReader((R/'docs/governance/device_full_acceptance_20261013/reverification/issue_registration_audit.csv').open(encoding='utf-8-sig'))};print(len(ids),len(added),len(ids-added));print(sorted(ids-added))
(O/'registration_set_check.json').write_text(json.dumps(dict(root_count=len(ids),registered_batch_count=len(added),other_count=len(ids-added),other_ids=sorted(ids-added)),ensure_ascii=False,indent=2),encoding='utf8')
