from pathlib import Path
import pymupdf as fitz,hashlib,json,openpyxl
root=Path.cwd(); out=root/'docs/governance/device_full_acceptance_20261013/hvac'
manifest=[]
for sid in ['29541','19577','37479','19576','21454']:
 p=next((root/'标准原文').glob('*'+sid+'*.pdf')); d=fitz.open(p)
 folder=out/sid;folder.mkdir(exist_ok=True)
 for i,page in enumerate(d):
  page.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(folder/f'p{i+1:02}.png')
 (folder/'pdf_text.txt').write_text('\n'.join(f'\nPAGE {i+1}\n'+x.get_text() for i,x in enumerate(d)),encoding='utf-8')
 std=next((root/'docs/standards').glob('gb'+sid+'_*'))
 files=[p,*[x for x in std.rglob('*') if x.suffix in ['.md','.xlsx','.csv'] and not any(t in x.parts for t in ['tmp','_tmp'])]]
 for f in files: manifest.append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
 lines=[]
 for f in std.rglob('*.xlsx'):
  wb=openpyxl.load_workbook(f,data_only=False)
  for ws in wb:
   lines.append(f'SHEET {ws.title} {ws.max_row}x{ws.max_column}')
   for row in ws:
    vals=['%s=%s'%(c.coordinate,c.value) for c in row if c.value is not None]
    lines.append(' | '.join(vals))
 (folder/'workbook.txt').write_text('\n'.join(lines),encoding='utf-8')
 print(sid,len(d),'pages')
(out/'source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
