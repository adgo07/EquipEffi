from pathlib import Path
import hashlib,json,datetime
base=Path('docs/standards/gbt36561_2018');out=Path('docs/governance/device_full_acceptance_20261013/reverification/gbt36561_batch1')
files=[p for p in base.rglob('*') if p.is_file() and ('tmp' not in p.relative_to(base).parts) and p.suffix in ['.md','.csv','.json','.py','.mjs','.xlsx']]
files.append(next(Path('标准原文').glob('*36561*.pdf')))
m={'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':[{'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
(out/'start_hashes.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf8')
for rel in ['data/table_values.json','evidence/workbook_coordinates.json','evidence/check_results.json','evidence/SHA256SUMS.json']:
 d=json.loads((base/rel).read_text(encoding='utf8'));print(rel,type(d).__name__, str(d)[:800])
