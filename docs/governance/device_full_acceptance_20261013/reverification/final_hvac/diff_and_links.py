from pathlib import Path
import json,hashlib,re,difflib
out=Path('docs/governance/device_full_acceptance_20261013/reverification/final_hvac'); base=Path('docs/governance/device_full_acceptance_20261013')
a=json.loads((out/'baseline_comparison.json').read_text(encoding='utf-8')); changes=[]
for x in a:
 if x['unchanged']:continue
 p=Path(x['path']);b=p.read_bytes();idx=b.index('## 正式编号回链'.encode());prefix=b[:idx]; found=None
 # append operation may have normalized line endings; reconstruct only original prefix with terminal whitespace variants.
 text=prefix.decode('utf-8-sig').rstrip()
 for newline in ['\n','\r\n']:
  for n in range(4):
   candidate=text.replace('\r\n','\n').replace('\n',newline).encode()+newline.encode()*n
   for bom in [b'',b'\xef\xbb\xbf']:
    if hashlib.sha256(bom+candidate).hexdigest()==x['first_sha256']: found=bom+candidate
 assert found is not None, str(p)+' historical prefix cannot be proven'
 old=found.decode('utf-8-sig').splitlines(True);new=b.decode('utf-8-sig').splitlines(True)
 diff=''.join(difflib.unified_diff(old,new,fromfile='first/'+p.parent.name,tofile='current/'+p.parent.name))
 (out/(p.parent.name+'_semantic.diff')).write_text(diff,encoding='utf-8')
 changes.append({'path':str(p),'first_content_reconstructed_sha256':hashlib.sha256(found).hexdigest(),'first_content_matches_hash':True,'change':'append formal ID backlinks only; original semantic content unchanged','addition':b[idx:].decode('utf-8')})
(out/'changed_file_semantics.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
root=Path('STANDARD_ISSUES_REGISTER.md').read_text(encoding='utf-8-sig');oldroot=Path('docs/governance/standard_mapping_acceptance_20261013/round2/snapshot/STANDARD_ISSUES_REGISTER.md').read_text(encoding='utf-8-sig')
def block(text,id):
 match=re.search(r'^### '+re.escape(id)+r'\b.*?(?=^#{1,3} |\Z)',text,re.M|re.S)
 return match.group(0).strip() if match else None
rows=[]
for sid,keys in [('29541',['001','002','003','004','005']),('19576',['R01','R02']),('37479',['请求A','请求C','请求B']),('21454',['R1','R2','R3','R4'])]:
 p=next(Path('docs/standards').glob('gb'+sid+'_*'))/'ISSUE_REGISTRATION_REQUEST.md';txt=p.read_text(encoding='utf-8-sig')
 for i,key in enumerate(keys,1):
  id=f'EQP-STD-GB{sid}-{i:03}';b=block(root,id);assert b
  row={'id':id,'local_key':key,'root_heading_count':len(re.findall('^### '+id+r'\b',root,re.M)),'status_open':'|状态|`OPEN`|' in b,'root_to_local':p.as_posix() in b,'local_pair':f'|`{key}`|`{id}`|' in txt,'local_to_root':'../../../STANDARD_ISSUES_REGISTER.md' in txt,'unapproved_preserved':'建议内容未获批准' in b}
  assert row['root_heading_count']==1 and all(row[k] for k in ['status_open','root_to_local','local_pair','local_to_root','unapproved_preserved']);rows.append(row)
for i in range(1,7):
 id=f'EQP-STD-GB19577-{i:03}';b=block(root,id);old=block(oldroot,id)
 rows.append({'id':id,'root_heading_count':len(re.findall('^### '+id+r'\b',root,re.M)),'status_open':'|状态|`OPEN`|' in b,'unchanged_vs_previous_root_snapshot':b==old,'prior_root_snapshot_has_block':old is not None,'current_block_sha256':hashlib.sha256(b.encode()).hexdigest(),'prior_block_sha256':hashlib.sha256(old.encode()).hexdigest() if old else None})
(out/'issue_links_check.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(rows[-6:],ensure_ascii=False));print('changed files append-only proven',len(changes),'14 links valid')

