from pathlib import Path
import re,json,csv,hashlib
b=Path('docs/governance/device_full_acceptance_20261013/reverification');b.mkdir(exist_ok=True)
p=Path('STANDARD_ISSUES_REGISTER.md');s=p.read_text(encoding='utf-8-sig')
blocks=re.split(r'(?m)^### (EQP-STD-[A-Z0-9]+-\d+)\s+—\s+',s)
counts={'GB18613':4,'GB30254':2,'GB30253':3,'GB19153':4,'GB24500':2,'GB29541':5,'GB19576':2,'GB37479':3,'GB21454':4,'GB19761':3,'GBT36561':11}
expected={f'EQP-STD-{k}-{i:03}' for k,n in counts.items() for i in range(1,n+1)}|{f'EQP-STD-GB28381-{i:03}' for i in range(7,13)}
rows=[];allids=[]
for i in range(1,len(blocks),2):
 id=blocks[i]; allids.append(id)
 if id not in expected:continue
 text=blocks[i+1];fields={a.strip():v.strip() for a,v in re.findall(r'^\|([^|]+)\|([^\n]+)\|\s*$',text,re.M)}
 field=lambda k:fields.get(k,'')
 evidence=field('支持证据'); link=re.search(r'\]\(([^)]+)\)',evidence)
 path=link.group(1) if link else ''
 local=field('问题编号 / 本地请求').split(' / ',1)[-1].strip('`')
 back=Path(path).read_text(encoding='utf-8-sig') if path and Path(path).exists() else ''
 rows.append({'id':id,'local_request':local,'version':field('标准编号及版本'),'type':field('问题类型'),'status':field('状态'),'source_request':path,'backlink_found':id in back,'has_fact':bool(field('标准原文事实/定位')),'has_judgment':bool(field('当前技术判断')),'has_software_boundary':bool(field('软件当前处理方式/待决建议')),'line':s[:s.find('### '+id)].count('\n')+1})
res={'register_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'expected':49,'found':len(rows),'missing':sorted(expected-set(x['id'] for x in rows)),'duplicate_headers':sorted({x for x in allids if allids.count(x)>1}),'all_open':all(x['status']=='`OPEN`' for x in rows),'all_backlinked':all(x['backlink_found'] for x in rows),'rows':rows}
(b/'issue_registration_audit.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf8')
with (b/'issue_registration_audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
print({k:v for k,v in res.items() if k!='rows'})

