from pathlib import Path
import json,re,hashlib,os
R=Path.cwd();A=R/'docs/governance/standard_archive_20261024';B=R/'docs/standards';O=R/'outputs/standard_consolidation_20261024'
manifest=json.loads((A/'FILE_MANIFEST.json').read_text());rows=manifest['files'];paths={x['old']:x['new'] for x in rows};errors=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(ok,msg):
 if not ok:errors.append(msg)
import subprocess
BASE_REF='13cd242a8999e32997f49123a603cd66f1f259d0'
def git(*args):return subprocess.check_output(['git',*args],text=True,encoding='utf-8').strip()
protected=json.loads((A/'PROTECTED_HASHES.json').read_text())
prior=json.loads((R/'docs/governance/owner_response_20261023/PROTECTED_HASHES.json').read_text())
tracked=set(git('ls-tree','-r','-z','--name-only',BASE_REF).split('\0'))
changed=set(git('diff','-z','--name-only',BASE_REF).split('\0'))
for p,h in {**protected,**prior}.items():
 if p in tracked:check(p not in changed,'protected changed versus PR base '+p)
 elif p in paths:
  t=R/paths[p];check(t.exists() and sha(t)==h,'new preserved evidence '+p)
 # Other old snapshot paths were retired upstream; they are not this PR's protected baseline.
fixed=['docs/standards/gb19762_2025','docs/standards/gb20052_2024','docs/standards/gb20052_v21','specs','src/equipeffi/resources/standards','platform-lock.json','V1_SCOPE.md','ROADMAP.md']
check(not git('diff','--name-only',BASE_REF,'--',*fixed),'protected asset diff against PR base')
latest_index=git('show',BASE_REF+':docs/standards/README.md')
shared=latest_index[latest_index.index('## 当前映射使用边界'):latest_index.index('## 标准总索引')]
check(shared in (B/'README.md').read_text(encoding='utf-8-sig'),'upstream shared Owner decisions')
latest_issues=git('show',BASE_REF+':STANDARD_ISSUES_REGISTER.md')
check((R/'STANDARD_ISSUES_REGISTER.md').read_text(encoding='utf-8-sig').startswith(latest_issues),'upstream issue register prefix')
for row in rows:
 p=R/row['new'];check(p.exists() and sha(p)==row['sha256_after'],'manifest '+row['new'])
 if row['old']!=row['new']:check(not (R/row['old']).exists(),'old file remains '+row['old'])
original={p.parent.parent.name:p.read_text(encoding='utf-8-sig') for p in A.glob('*/before/STANDARD_MAPPING.md')}
def plain(s):return re.sub(r'(!?\[[^\]\n]*\])\([^\n)]*\)',r'\1',s)
for k,old in original.items():
 new=(B/k/'STANDARD_MAPPING.md').read_text(encoding='utf-8')
 old=old.replace('主映射回答选表、选行和判级，工作簿保存源值。','本映射同时保存选表、选行、判级规则与源表值；文中工作簿坐标仅供追溯归档证据。').replace('|配套数据|','|历史数据证据|').replace('配套[工作簿]','归档[工作簿]') if k in {'gb19576_2019','gb29541_2013','gb37479_2019'} else old
 for line in plain(old).splitlines():
  if line.strip():check(line in plain(new),k+' missing content '+line[:90])
 active=[p for p in (B/k).rglob('*') if p.is_file()]
 check(len(active)==(1 if k in {'gb19576_2019','gb29541_2013','gb37479_2019'} else 2),k+' core file count')
items=json.loads((R/'docs/governance/owner_response_20261023/DECISION_APPLICATION.json').read_text())['items']
for item in items:
 s=(B/item['key']/'STANDARD_MAPPING.md').read_text(encoding='utf-8');check(item['rule'] in s,'Owner rule '+item['id'])
# Verify displayed copied rows are present exactly; workbook bytes independently protected above.
transfers=json.loads((A/'TABLE_TRANSFER_CHECKS.json').read_text());grade_count=0
for row in transfers:
 s=(B/row['standard']/'STANDARD_MAPPING.md').read_text(encoding='utf-8')
 if row.get('existing'):check(row['values'] in s,'existing values');grade_count+=3
 else:check('|'+'|'.join(row['values'])+'|'+str(row['row'])+'|' in s,'transferred values');grade_count+=5 if row['standard']=='gb29541_2013' else 3
link=re.compile(r'!?\[[^\]\n]*\]\((<[^>]+>|[^)\n]+)\)');checked_links=0
for p in [B/'README.md',A/'README.md']+[B/k/'STANDARD_MAPPING.md' for k in original]:
 for m in link.finditer(p.read_text(encoding='utf-8-sig')):
  v=m[1].strip('<>')
  if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',v) or v.startswith('#'):continue
  checked_links+=1;check((p.parent/v.split('#')[0]).exists(),'broken link '+str(p)+' -> '+v)
result={'errors':errors,'publication_base':BASE_REF,'protected_files':len(protected),'prior_protected_files':len(prior),'manifest_entries':len(rows),'Owner_rules_preserved':len(items),'grade_values_compared':grade_count,'active_local_links_checked':checked_links,'standard_count':len(original),'production_tests':'NOT_RUN: documentation and file organization only','pdf_reverification':'NOT_RUN: migration fidelity check only'}
(A/'PUBLICATION_VALIDATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(bool(errors))
