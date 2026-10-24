"""Read-only source inventory and private PDF text/render extraction."""
from pathlib import Path
import hashlib,json
import pypdf,pypdfium2
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
(OUT/'tmp').mkdir(exist_ok=True)
(OUT/'evidence').mkdir(exist_ok=True)
files=[ROOT/'标准原文/10. GB 32030-2022_潜水电泵能效限定值及能效等级.pdf']+sorted((ROOT/'标准原文/10.潜水电泵相关').glob('*.pdf'))
inventory=[]
for i,path in enumerate(files):
    reader=pypdf.PdfReader(path)
    pages=[p.extract_text() or '' for p in reader.pages]
    item=dict(id=f'S{i:02}',path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),pages=len(pages),page_chars=[len(t) for t in pages])
    inventory.append(item)
    (OUT/f'tmp/S{i:02}.txt').write_text('\n'.join(f'\n=== PDF {j+1} ===\n{t}' for j,t in enumerate(pages)),encoding='utf-8')
    doc=pypdfium2.PdfDocument(path)
    for j in (range(len(pages)) if i==0 else [0,len(pages)-1]):
        doc[j].render(scale=1.6).to_pil().save(OUT/f'tmp/S{i:02}_p{j+1:02}.png')
(OUT/'evidence/source_inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(inventory,ensure_ascii=False,indent=2))
