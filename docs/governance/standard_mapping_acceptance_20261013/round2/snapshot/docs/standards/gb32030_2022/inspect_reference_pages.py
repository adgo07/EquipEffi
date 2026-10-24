from pathlib import Path
import json,pypdfium2
O=Path(__file__).resolve().parent
ROOT=O.parents[2]
sources=json.loads((O/'evidence/source_inventory.json').read_text(encoding='utf8'))
for s in sources[1:]:
 d=pypdfium2.PdfDocument(ROOT/s['path'])
 pages={'S01':[3,5,6,75],'S02':[2,3,25],'S03':[2,3,26],'S04':[2,3,43],'S05':[3,5,9,10],'S06':[2,3,4,5,16],'S07':[2,3,4,5,18]}[s['id']]
 if s['id']=='S01':
  for i in range(len(d)):
   t=d[i].get_textpage().get_text_range().replace(' ','')
   if '表7' in t and '容差' in t:pages.append(i+1)
 for page in sorted(set(pages)):
  d[page-1].render(scale=1.4).to_pil().save(O/f"tmp/{s['id']}_key_p{page:02}.png")
 print(s['id'],sorted(set(pages)))
