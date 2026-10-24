"""Compare acceptance input byte identities; no writes to source files."""
from pathlib import Path
import json,hashlib
from datetime import datetime,timezone,timedelta
root=Path(__file__).resolve().parent
inventory=json.loads((root/'preflight_inventory.json').read_text(encoding='utf-8'))
checks=[]
for standard in inventory['standards']:
 for kind in ('mapping_files','workbooks','source_pdfs'):
  for item in standard[kind]:
   p=Path(item['absolute_path'])
   actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
   checks.append({'standard':standard['key'],'kind':kind,'path':str(p),'initial_sha256':item['sha256'],'current_sha256':actual,'unchanged':actual==item['sha256']})
result={'checked_bjt':datetime.now(timezone(timedelta(hours=8))).isoformat(),'total':len(checks),'unchanged':sum(c['unchanged'] for c in checks),'changed':[c for c in checks if not c['unchanged']],'checks':checks}
(root/'source_stability_end.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('checked_bjt','total','unchanged','changed')},ensure_ascii=False))
