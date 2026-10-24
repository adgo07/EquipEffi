"""复现只读原PDF渲染和文字层诊断。输出仅在本目录被忽略的tmp内。"""
from pathlib import Path
import argparse,hashlib,json,subprocess
from pypdf import PdfReader
p=argparse.ArgumentParser()
p.add_argument('pdf',type=Path)
p.add_argument('--pdftoppm',default='pdftoppm')
a=p.parse_args()
root=Path(__file__).resolve().parent
out=root/'tmp';out.mkdir(exist_ok=True)
raw=a.pdf.read_bytes()
sha=hashlib.sha256(raw).hexdigest()
if sha!='f1a6b29aa25d13b69f16006dd822e4ad2641830468bd6c395056e6751095ba37':
    raise SystemExit('Source hash mismatch; do not replace evidence silently')
d=PdfReader(a.pdf)
(out/'text.txt').write_text('\n'.join(f'=== PDF {i+1} ===\n'+p.extract_text() for i,p in enumerate(d.pages)),encoding='utf-8')
subprocess.run([a.pdftoppm,'-r','120','-png',str(a.pdf),str(out/'page')],check=True)
print(json.dumps({'sha256':sha,'pdf_pages':len(d.pages),'rendered_pages':len(list(out.glob('page-*.png')))}))
