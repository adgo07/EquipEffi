from pathlib import Path
import json, re, hashlib, datetime, csv
from decimal import Decimal
import openpyxl
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'read_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'snapshot_checks':[],'timeline':[]}
old=json.loads((ROOT/'_acceptance_20261013/accepted_revision_manifest.json').read_text('utf-8-sig'))
own=json.loads((ROOT/'docs/governance/device_full_acceptance_20261013/motors/source_manifest.json').read_text('utf-8-sig'))
own={x['path']:x['sha256'] for x in own}
for folder in ['gb18613_2020','gb30254_2024','gb30253_2024']:
    base=ROOT/'docs/standards'/folder
    snap=next((ROOT/'_acceptance_20261013/round3/evidence_snapshots').glob(folder+'*.txt'))
    (OUT/snap.name).write_bytes(snap.read_bytes())
    wbpath=next((base/'data').glob('*.xlsx')); wb=openpyxl.load_workbook(wbpath,data_only=False)
    cells={};sheet=None
    for line in snap.read_text('utf-8-sig').splitlines():
        if line.startswith('==== SHEET '):sheet=line[len('==== SHEET '):].split('  max_row=')[0]
        elif re.match(r'^R\d+\s+\| ',line):
            for match in re.finditer(r'(?:^| \| )([A-Z]+\d+)=(.*?)(?= \| [A-Z]+\d+=|$)',line.split('| ',1)[1]):
                cells[(sheet,match[1])]=match[2]
    current={(s.title,c.coordinate):str(c.value).replace('\n','\\n') for s in wb for row in s for c in row if c.value is not None}
    diffs=[{'sheet':k[0],'cell':k[1],'old':cells.get(k),'current':current.get(k)} for k in cells.keys()|current.keys() if cells.get(k)!=current.get(k)]
    result['snapshot_checks'].append({'standard':folder,'snapshot_path':str(snap),'snapshot_sha256':digest(snap),'snapshot_nonempty_cells':len(cells),'current_nonempty_cells':len(current),'diffs':diffs,'xlsx_sha256':digest(wbpath)})
    for name in ['STANDARD_MAPPING.md','README.md','ISSUE_REGISTRATION_REQUEST.md','BOUNDARY_CANDIDATES.md','BOUNDARY_CASES.md',str(wbpath.relative_to(base)).replace('\\','/')]:
        p=base/name
        if p.exists():result['timeline'].append({'path':str(p),'older_12standard_manifest_sha256':old['standards'][folder]['files'].get(name,{}).get('sha256'),'our_full_audit_start_sha256':own.get(str(p)),'current_sha256':digest(p)})
wb=openpyxl.load_workbook(next((ROOT/'docs/standards/gb18613_2020/data').glob('*.xlsx')))
s=wb['表1'];result['BC01']=[next((g for g,c in enumerate(['B6','F6','J6'],1) if Decimal(str(v))>=Decimal(str(s[c].value))),None) for v in ['71.3','71.4','71.5']]
result['BC04']=[str((Decimal(str(s[a].value))+Decimal(str(s[b].value)))/2) for a,b in [('C6','C7'),('G6','G7'),('K6','K7')]]
packpath=ROOT/'src/equipeffi/resources/standards/gb30253_2024_pdf_verified_v1.json'
pack=json.loads(packpath.read_text('utf-8-sig'))
result['A1']={'path':str(packpath),'sha256':digest(packpath),'status':pack['status'],'source_sha256':pack['source_sha256'],'row':pack['tables'][0]['rows'][16],'activation_review':pack['activation_review'],'runtime_executed':False}
root=(ROOT/'STANDARD_ISSUES_REGISTER.md').read_text('utf-8-sig')
result['root_registry']={'sha256':digest(ROOT/'STANDARD_ISSUES_REGISTER.md'),'motor_blocks':re.findall(r'^### EQP-STD-GB(?:18613|30254|30253)-.*?(?=^### |\Z)',root,re.S|re.M),'runtime_filename_registered':'gb30253_2024_pdf_verified' in root}
start=json.loads((OUT/'source_start.json').read_text('utf-8'))
for item in start['files']:
    item['end_sha256']=digest(Path(item['path']));item['stable']=item['end_sha256']==item['sha256']
result['source_stability']=start
(OUT/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'snapshots':[(x['standard'],x['snapshot_nonempty_cells'],len(x['diffs'])) for x in result['snapshot_checks']],'BC01':result['BC01'],'BC04':result['BC04'],'source_stable':all(x['stable'] for x in start['files'])},ensure_ascii=False))
