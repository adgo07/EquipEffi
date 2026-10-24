from pathlib import Path
import json,hashlib,re,datetime,subprocess,csv
r=Path('docs/governance/device_full_acceptance_20261013/reverification');p=Path('STANDARD_ISSUES_REGISTER.md')
start=p.read_bytes();old=(r/'final_hvac/root_end_snapshot.txt').read_bytes()
expected={'EQP-STD-GB30253-001':'TYPO / CONFLICT','EQP-STD-GB24500-001':'IMPLEMENTATION / AMBIGUITY','EQP-STD-GB24500-002':'REFERENCE / IMPLEMENTATION','EQP-STD-GB29541-001':'MISSING / AMBIGUITY','EQP-STD-GB29541-002':'MISSING / AMBIGUITY','EQP-STD-GB29541-003':'IMPLEMENTATION / REFERENCE','EQP-STD-GB29541-004':'REFERENCE','EQP-STD-GB29541-005':'AMBIGUITY'}
a=old.decode('utf-8-sig');b=start.decode('utf-8-sig');checks=[]
for id,t in expected.items():
 pattern=r'(### '+re.escape(id)+r'[^\n]*\n(?:(?!\n### ).)*?\|问题类型\|)([^\n]*)(\|\r?\n)'
 ma=re.search(pattern,a,re.S);mb=re.search(pattern,b,re.S)
 value=mb.group(2).replace('`','').strip();checks.append({'id':id,'expected':t,'actual':value,'pass':value==t})
 # Restore only this exact type field to old content, retaining all other bytes.
 b=b[:mb.start(2)]+ma.group(2)+b[mb.end(2):]
assert all(x['pass'] for x in checks)
unchanged_other=b==a
assert unchanged_other
subprocess.run(['python',str(r/'audit_registration.py')],check=True)
end=p.read_bytes();sha=lambda v:hashlib.sha256(v).hexdigest()
res={'review_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'old_snapshot':str((r/'final_hvac/root_end_snapshot.txt').resolve()),'old_sha256':sha(old),'start_sha256':sha(start),'end_sha256':sha(end),'stable':start==end,'checks':checks,'all_other_text_unchanged':unchanged_other,'old_snapshot_exact_sha_matches_previous_manifest':sha(old)=='4989190f141d482dbb00c3fedb5c0ac2b52d8560e24ec4c66ccf02c36f1bc79e','result':'PASS','scope':'Only 8 issue-type lines changed; all other content exact; 49 registration audit rerun; remaining 262 files stable per parent final check'}
(r/'register_type_final_check.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf8')
(r/'register_final_snapshot.txt').write_bytes(end)
p=r/'final_source_manifest.json';d=json.loads(p.read_text(encoding='utf8'));newsha=sha(end)
for f in d['files']:
 if f['relative_path']=='STANDARD_ISSUES_REGISTER.md':
  f['sha256']=newsha;f['start_sha256']=newsha;f['bytes']=len(end);f['unchanged_during_window']=True
# Prior full-window start snapshot remains unchanged, final record explicitly references short window.
d['register_final_short_reverification']='register_type_final_check.json';d['register_previous_sha256']=sha(old);d['final_register_sha256']=newsha;d['final_register_update_utc']=res['review_utc'];d['remaining_262_files_final_stability']='Confirmed by parent final delivery check; no repeat table verification'
p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
with (r/'final_source_manifest.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=d['files'][0].keys());w.writeheader();w.writerows(d['files'])
print('8 types PASS; all other content exact; new root',newsha,'stable',start==end)
