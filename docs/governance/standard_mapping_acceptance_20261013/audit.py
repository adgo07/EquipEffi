"""Independent read-only audit. Writes only beside this script; never saves XLSX/PDF."""
from pathlib import Path
import hashlib, json, subprocess, shutil, os, sys, zipfile, re
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
KEYS='gb18613_2020 gb30254_2024 gb30253_2024 gb19153_2019 gb24500_2020 gb29541_2013 gb19576_2019 gb28381_2012 gb37479_2019 gb21454_2021'.split()
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(n,x): (OUT/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def manifest():
    dirs=['docs/standards/'+k for k in KEYS]+['docs/standards/gb19762_2025','docs/standards/gb20052_2024','docs/standards/gb20052_v21']
    names=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard','--',*dirs],cwd=ROOT).decode('utf-8').split('\0')
    names+=['AGENTS.md','platform-lock.json','HANDOFF.md','TASK_STATE.md','STANDARD_ISSUES_REGISTER.md','docs/standards/README.md','docs/standards/_STANDARD_MAPPING_TEMPLATE.md','docs/governance/SIX_STANDARD_MAPPING_COORDINATION_20261013.md']
    result=[]
    for n in sorted(set(filter(None,names))):
        p=ROOT/n
        if p.name.startswith('~$'): continue
        result.append({'path':n,'sha256':sha(p),'bytes':p.stat().st_size})
    return {'utc':datetime.now(timezone.utc).isoformat(),'files':result}
def workbook(p):
    z=zipfile.ZipFile(p); strings=[]
    if 'xl/sharedStrings.xml' in z.namelist():
        strings=[''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml'))]
    rels={r.attrib['Id']:r.attrib['Target'] for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    ans=[]
    for s in ET.fromstring(z.read('xl/workbook.xml')).find('s:sheets',NS):
        target=rels[s.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
        target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
        x=ET.fromstring(z.read(target)); cells={}
        for c in x.findall('.//s:sheetData/s:row/s:c',NS):
            v=c.find('s:v',NS); val=v.text if v is not None else None
            t=c.get('t')
            if t=='s': val=strings[int(val)] if val is not None else None
            if t=='inlineStr': val=''.join(c.find('s:is',NS).itertext())
            f=c.find('s:f',NS)
            cells[c.get('r')]={'value':val,'type':t or 'n','style':c.get('s'),'formula':f.text if f is not None else None}
        ans.append({'sheet':s.get('name'),'xml':target,'dimension':x.find('s:dimension',NS).get('ref') if x.find('s:dimension',NS) is not None else None,'merges':[m.get('ref') for m in x.findall('s:mergeCells/s:mergeCell',NS)],'cells':cells})
    return ans
if sys.argv[1]=='start':
    m=manifest(); dump('manifest_start.json',m)
    for f in m['files']:
        dest=OUT/'snapshot'/f['path']; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/f['path'],dest)
        assert sha(dest)==f['sha256']
    pdfs=[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':sha(p),'bytes':p.stat().st_size} for p in (ROOT/'标准原文').rglob('*.pdf')]
    dump('source_pdf_manifest.json',pdfs)
    print('Snapshot:',len(m['files']),'files; PDFs:',len(pdfs))
elif sys.argv[1]=='inspect':
    index={}; errors=[]; links=[]
    for key in KEYS:
        base=OUT/'snapshot/docs/standards'/key; books=list(base.glob('data/*.xlsx'))
        for p in books:
            data=workbook(p); dump('tmp/'+key+'_cells.json',data)
            index[key]={'workbook':str(p.relative_to(OUT/'snapshot')).replace('\\','/'),'sheets':[{'name':s['sheet'],'dimension':s['dimension'],'merges':s['merges'],'populated_cells':sum(c['value'] is not None for c in s['cells'].values()),'formulas':sum(c['formula'] is not None for c in s['cells'].values()),'error_cells':[a for a,c in s['cells'].items() if c['type']=='e']} for s in data]}
        for p in base.rglob('*.md'):
            if 'tmp' in p.parts or '_work' in p.parts: continue
            for match in re.finditer(r'\[[^\]]*\]\(([^\n)]+)\)',p.read_text(encoding='utf-8-sig')):
                t=match.group(1).strip('<>').split('#')[0]
                if not t or re.match(r'\w+://',t): continue
                from urllib.parse import unquote
                source=ROOT/p.relative_to(OUT/'snapshot')
                links.append({'file':str(p.relative_to(OUT/'snapshot')),'target':t,'exists':(source.parent/unquote(t)).exists()})
    dump('workbook_structure.json',index); dump('link_checks.json',links)
    print(json.dumps(index,ensure_ascii=False,indent=2)); print('Links',len(links),'broken',sum(not x['exists'] for x in links))
elif sys.argv[1]=='end':
    m=manifest(); dump('manifest_end.json',m); old={f['path']:f for f in json.loads((OUT/'manifest_start.json').read_text())['files']}; now={f['path']:f for f in m['files']}
    changes=[{'path':p,'before':old.get(p),'after':now.get(p)} for p in sorted(old.keys()|now.keys()) if old.get(p)!=now.get(p)]
    dump('source_changes.json',changes); print(json.dumps(changes,ensure_ascii=False,indent=2))
