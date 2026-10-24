"""Reproduce local extraction/rendering; source PDF stays read-only and untracked."""
from pathlib import Path
import hashlib, subprocess, sys
from pypdf import PdfReader
root=Path(__file__).resolve().parent
pdf=Path(sys.argv[1]) if len(sys.argv)>1 else root.parents[2]/'标准原文/17. GB 21454-2021 多联式空调（热泵）机组能效限定值及能效等级.pdf'
assert hashlib.sha256(pdf.read_bytes()).hexdigest()=='ae091115094de6dcc2f587e35bd5a9389708fb37714804ef510ea831613a7331'
(root/'tmp').mkdir(exist_ok=True)
reader=PdfReader(pdf)
(root/'tmp/pdf_text.txt').write_text('\n'.join(f'\n---PHYSICAL PAGE {i+1}---\n'+p.extract_text() for i,p in enumerate(reader.pages)),encoding='utf-8')
subprocess.run(['pdftoppm','-scale-to','1600','-png',str(pdf),str(root/'tmp/page')],check=True)
print('pages',len(reader.pages))
