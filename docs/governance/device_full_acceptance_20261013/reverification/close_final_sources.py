from pathlib import Path
import json,hashlib,datetime,csv
b=Path('docs/governance/device_full_acceptance_20261013/reverification')
d=json.loads((b/'final_source_manifest_start.json').read_text(encoding='utf8'));changes=[]
for f in d['files']:
 p=Path(f['absolute_path']); new=hashlib.sha256(p.read_bytes()).hexdigest();f['start_sha256']=f['sha256'];f['sha256']=new;f['unchanged_during_window']=new==f['start_sha256']
 if not f['unchanged_during_window']:changes.append({'path':str(p),'before':f['start_sha256'],'after':new})
d['end_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();d['changed_files']=changes
(b/'final_source_manifest.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
with (b/'final_source_manifest.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=d['files'][0].keys());w.writeheader();w.writerows(d['files'])
print('files',len(d['files']),'changed',changes)
