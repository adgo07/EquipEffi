from pathlib import Path
import json,hashlib,datetime
base=Path('docs/governance/device_full_acceptance_20261013'); root=Path.cwd()
inv=json.loads((base/'preflight_inventory.json').read_text(encoding='utf-8-sig'))
excluded_parts={'node_modules','tmp','_tmp','_work','__pycache__','.cache','.git','.venv','venv','renders','rendered','preview','previews'}
allowed={'.md','.xlsx','.csv','.json','.py','.mjs','.js','.txt','.yaml','.yml','.toml'}
files={}; groups=[]
for std in inv['standards']:
 if '19762' in std['key'] or '20052' in std['key']:continue
 paths=set()
 d=Path(std['directory'])
 for p in d.rglob('*'):
  if p.is_file() and p.suffix.lower() in allowed and not any(x.lower() in excluded_parts for x in p.relative_to(d).parts):paths.add(p)
 for f in std['source_pdfs']:paths.add(Path(f['absolute_path']))
 for p in paths:
  rel=p.relative_to(root).as_posix(); files[rel]={'absolute_path':str(p.resolve()),'relative_path':rel,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'standard':std['key']}
 groups.append({'standard':std['key'],'files':sorted(p.relative_to(root).as_posix() for p in paths)})
p=root/'STANDARD_ISSUES_REGISTER.md';files[p.name]={'absolute_path':str(p),'relative_path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'standard':'shared-register'}
out={'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'15 formal standards; excludes pump/transformer and dependency caches/rendered images','files':list(sorted(files.values(),key=lambda x:x['relative_path'])),'groups':groups}
(base/'reverification'/'final_source_manifest_start.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print('standards',len(groups),'files',len(files))
