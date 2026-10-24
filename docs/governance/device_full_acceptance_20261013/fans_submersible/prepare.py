from pathlib import Path
import pymupdf as fitz,json,hashlib,openpyxl
out=Path('docs/governance/device_full_acceptance_20261013/fans_submersible'); roots=['gb19761_2020','gb28381_2012','gb28381_2026','gb32030_2022','gbt36561_2018']; nums=['19761','28381-2012','28381-2026','32030','36561']
manifest=[]
for key,num in zip(roots,nums):
 p=next(x for x in Path('标准原文').glob('*.pdf') if num in x.name);d=fitz.open(p); dest=out/key;dest.mkdir(exist_ok=True)
 (dest/'source_text.txt').write_text('\n'.join(f'=== PDF {i+1} ===\n'+pg.get_text() for i,pg in enumerate(d)),encoding='utf-8')
 for i,pg in enumerate(d):pg.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(str(dest/f'page_{i+1:02}.png'))
 files=[p,Path('docs/standards')/key/'STANDARD_MAPPING.md',*list((Path('docs/standards')/key).rglob('*.xlsx'))]
 for f in files:manifest.append(dict(standard=key,path=str(f.resolve()),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),pages=len(d) if f==p else None))
 for f in files:
  if f.suffix=='.xlsx':
   w=openpyxl.load_workbook(f,data_only=False); (dest/'workbook_dump.json').write_text(json.dumps({s.title:[[c.value for c in row] for row in s] for s in w},ensure_ascii=False,indent=2),encoding='utf-8')
 print(key,len(d),[(s.title,s.max_row,s.max_column) for s in w])
(out/'source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
