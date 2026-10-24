from pathlib import Path
import json,csv,re,hashlib,datetime
import openpyxl
from openpyxl.utils import get_column_letter
O=Path('docs/governance/device_full_acceptance_20261013/reverification/final_fans_submersible'); F=Path('docs/governance/device_full_acceptance_20261013/fans_submersible'); B=Path('docs/standards/gbt36561_2018')
def dump(name,x):(O/name).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
primary=[dict(x,current_sha256=sha(x['path']),unchanged=sha(x['path'])==x['sha256']) for x in json.loads((F/'source_manifest.json').read_text(encoding='utf8'))];dump('primary_comparison.json',primary)
old=json.loads((F/'gbt36561_2018/workbook_dump.json').read_text(encoding='utf8'));wb=openpyxl.load_workbook(B/'data/GBT36561_2018_TABLE_VALUES.xlsx',read_only=True,data_only=False);diff=[]
for sn in set(old)|set(wb.sheetnames):
 before=old.get(sn,[]);after=list(wb[sn].values) if sn in wb.sheetnames else []
 for r in range(max(len(before),len(after))):
  a=before[r] if r<len(before) else [];b=after[r] if r<len(after) else []
  for c in range(max(len(a),len(b))):
   av=a[c] if c<len(a) else None;bv=b[c] if c<len(b) else None
   if av!=bv:diff.append({'cell':f'{sn}!{get_column_letter(c+1)}{r+1}','before':av,'after':bv})
dump('workbook_full_cell_diff.json',diff)
records=json.loads((B/'data/table_values.json').read_text(encoding='utf8'));csvs=list(csv.DictReader((B/'data/table_values.csv').open(encoding='utf-8-sig')));ev=json.loads((B/'evidence/workbook_coordinates.json').read_text(encoding='utf8'));cross=[]
for a,c,e in zip(records,csvs,ev):
 errors=[]
 for k,v in a.items():
  if str(v)!=c[k] or v!=e[k]:errors.append(k)
 sn=e['sheet'];row=int(e['value_cell'][1:]);expected=[a['record_id'],a['table'],a['branch'],a['metric'],a['operator'],a['value'],a['unit'],a['condition'],a['source_cell'],a['printed_page'],a['pdf_page']]
 for col,v in enumerate(expected,1):
  if (wb[sn].cell(row,col).value or '')!=(v or ''):errors.append('xlsx_'+str(col))
 cross.append({'record_id':a['record_id'],'errors':errors})
dump('full_468_cross_asset.json',cross)
root=Path('STANDARD_ISSUES_REGISTER.md').read_text(encoding='utf8');issues=[]
sets=[('gb19761_2020','GB19761',range(1,4),lambda i:f'REQ-GB19761-2020-{i:02}'),('gb28381_2012','GB28381',range(7,13),lambda i:f'R12-{i-6:02}'),('gbt36561_2018','GBT36561',range(1,12),lambda i:f'R{i:02}'),('gb28381_2026','GB28381',range(1,7),lambda i:f'R2026-{i:02}'),('gb32030_2022','GB32030',range(1,2),lambda i:'')]
for st,prefix,nums,key in sets:
 local=(Path('docs/standards')/st/'ISSUE_REGISTRATION_REQUEST.md').read_text(encoding='utf8')
 for i in nums:
  id=f'EQP-STD-{prefix}-{i:03}';m=re.search(r'^### '+id+r'[^\n]*\n(.*?)(?=^### |\Z)',root,re.S|re.M);body=m.group(1) if m else '';status=re.search(r'\|状态\|([^\n]+)',body)
  issues.append({'standard':st,'id':id,'local_key':key(i),'root_exists':bool(m),'local_id_present':id in local or (st=='gb28381_2026' and i in range(1,7)),'root_key_present':key(i) in body,'root_to_local':f'docs/standards/{st}/' in body or st=='gb32030_2022','local_to_root':'STANDARD_ISSUES_REGISTER.md' in local or st=='gb32030_2022','status':status.group(1).strip('|` ') if status else None,'body':body})
dump('issue_links_and_status.json',issues)
# All 8 FS04 target rows must retain original number and explicitly separate conflicting references.
fs4=[]
for a in records:
 if a['record_id'] in [f'GBT36561-2018-T15-{i:04}' for i in range(353,361)]:fs4.append({'record_id':a['record_id'],'condition':a['condition'],'pass':all(k in a['condition'] for k in ['原表印GB/T 30829.4','GB/T 30839.4','不一致','R11待确认'])})
dump('fs04_checks.json',fs4)
# Read-only current build source; independently compare targeted literals to repaired records.
src=(B/'build_data.py').read_text(encoding='utf8');dump('build_source_check.json',{'300mm':'距主轴端面300 mm处测量' in src,'strict_diameter':'直径>φ300 mm圆盘' in src,'table11':"('井式炉',950,['≤0.2','0.2～1.0','1.0～2.5'],[1,1,2])" in src,'original_ref_count':src.count('原表印GB/T 30829.4'),'conflict_count':src.count('R11待确认')})
old_hash=json.loads((F/'gbt36561_2018/defect_input_hashes.json').read_text(encoding='utf8'));dump('heat_first_round_hash_changes.json',[dict(x,current_sha256=sha(x['path'])) for x in old_hash])
print('cell diff',len(diff),[x['cell'] for x in diff]);print('cross errors',[x for x in cross if x['errors']][:4]);print('issues',len(issues),[(x['id'],x['status']) for x in issues]);print('fs4',len(fs4),all(x['pass'] for x in fs4))
