from pathlib import Path
import pymupdf as fitz,pdfplumber,openpyxl,unicodedata,json,csv,hashlib,re
from io import BytesIO
from fontTools.cffLib import CFFFontSet
from fontTools.pens.recordingPen import RecordingPen
OUT=Path(__file__).parent; ROOT=OUT.parents[3]
def shapes(doc,xref):
 c=CFFFontSet();c.decompile(BytesIO(doc.extract_font(xref)[3]),None); t=c.topDictIndex[0]; out={}
 for code,name in enumerate(t.Encoding):
  if name=='.notdef':continue
  pen=RecordingPen();t.CharStrings[name].draw(pen);out[code]=hashlib.sha256(repr(pen.value).encode()).hexdigest()
 return out
# Page7 numeral font grounded in viewed source image: header 1/2/3, poles 2/4/6/8/10/12/16,
# first rows 0.55,85.9,87.9,86.2,83.9 and 0.75 etc. No workbook values seed decoding.
seed=fitz.open(next((ROOT/'标准原文').glob('*30253*.pdf')))
truth={33:'k',34:'W',35:'%',36:'1',37:'2',38:'3',39:'4',40:'6',41:'8',42:'0',43:'.',44:'5',45:'9',46:'7'}
SH={h:truth[k] for k,h in shapes(seed,259).items()}
CODES={'’':39,'‘':96,'“':170,'”':186}
def norm(s):
 s=unicodedata.normalize('NFKC',str('' if s is None else s)).replace(' ','').replace('\n','').replace('～','~').replace('—','-').replace('−','-')
 try:return float(s)
 except:return s
summaries=[];cells=[];manifest=[]
for sid in ['18613','30254','30253']:
 src=next((ROOT/'标准原文').glob('*'+sid+'*.pdf')); d=fitz.open(src)
 sd=next((ROOT/'docs/standards').glob('gb'+sid+'_*')); xp=next((sd/'data').glob('*.xlsx')); wb=openpyxl.load_workbook(xp,data_only=False)
 for p in [src,xp,sd/'STANDARD_MAPPING.md',sd/'ISSUE_REGISTRATION_REQUEST.md']:
  manifest.append({'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 maps={}
 for pi,page in enumerate(d):
  if sid!='18613' and pi>=6 and pi<(18 if sid=='30254' else 51):page.set_rotation(90)
  for font in page.get_fonts():
   if font[1]!='cff':continue
   try: maps[(pi+1,font[3])]={code:SH[h] for code,h in shapes(d,font[0]).items() if h in SH}
   except:pass
 with pdfplumber.open(BytesIO(d.tobytes())) as pdf:
  table=0; current=[];groups=[]
  for pn,page in enumerate(pdf.pages,1):
   if sid=='18613' and pn<4 or sid!='18613' and pn<7 or sid=='30254' and pn>18:continue
   for part,t in enumerate(page.find_tables(),1):
    rows=[]
    for ri,row in enumerate(t.rows,1):
     vals=[]
     for box in row.cells:
      if box is None:vals.append(None);continue
      x0,y0,x1,y1=box; chars=[ch for ch in page.chars if x0<=(ch['x0']+ch['x1'])/2<x1 and y0<=(ch['top']+ch['bottom'])/2<y1]
      chars.sort(key=lambda c:c['x0'])
      result=''
      for ch in chars:
       c=ch['text'];code=CODES.get(c,ord(c) if len(c)==1 else -1)
       result+=maps.get((pn,ch['fontname']),{}).get(code,c)
      vals.append(unicodedata.normalize('NFKC',result).replace(' ','').replace('\n',''))
     # Numeric source data starts with numerical power or a range; header is not data.
     first=vals[0] or ''
     if sid=='30253':
      # Visually confirmed original power symbols: page8 range and pages21 onward >=3150.
      first=first.replace('!', '~').replace(chr(34)+'3150','≥3150');vals[0]=first
     if re.match(r'^[≥]?[0-9]',first) and all(v is not None for v in vals):rows.append((pn,part,ri,vals,[list(b) for b in row.cells]))
    if rows: groups.append(rows)
  # Explicit source-image table fragment routing, independent of workbook trace columns.
  routing={'18613':[1,2,3,4,5,5,6,6], '30254':[1,1,1,2,2,2,3,3,3,4,4,5,5,6,6], '30253':None}[sid]
  if sid=='30253':
   # Identify continuation by power order; each new table starts again at its branch minimum.
   routing=[];tno=0;last=-1
   for rows in groups:
    first=norm(rows[0][3][0]);fp=float(re.findall(r'\d+(?:\.\d+)?',str(first))[0]);
    if fp<=last:tno+=1
    elif tno==0:tno=1
    routing.append(tno);last=float(re.findall(r'\d+(?:\.\d+)?',str(rows[-1][3][0]))[0])
  assert len(routing)==len(groups),(sid,len(groups),routing)
  merged={}
  for tn,rows in zip(routing,groups):merged.setdefault(tn,[]).extend(rows)
  rawfile=OUT/(sid+'_source_rows.json');rawfile.write_text(json.dumps(merged,ensure_ascii=False,indent=1),encoding='utf8')
  for tn,rows in merged.items():
   sheet='表'+(str(tn).zfill(2) if sid=='30253' else str(tn)); ws=wb[sheet];start={'18613':6,'30254':8,'30253':7}[sid];mismatch=[]
   for ir,(pn,part,ri,vals,boxes) in enumerate(rows):
    for col,v in enumerate(vals,1):
     got=ws.cell(start+ir,col).value; a=norm(v);b=norm(got)
     # Number font is fully decoded; short dash uses a separate font in these sources.
     if sid!='18613' and col>1 and not isinstance(a,float) and len(v or '')==1:a='-'
     ok=a==b
     record={'standard':sid,'table':tn,'pdf_page':pn,'source_part':part,'source_row':ri,'source_column':col,'bbox':json.dumps(boxes[col-1]),'sheet':sheet,'cell':ws.cell(start+ir,col).coordinate,'source':v,'workbook':got,'equal':ok}
     cells.append(record)
     if not ok:mismatch.append(record)
   summaries.append({'standard':sid,'table':tn,'pages':sorted({r[0]for r in rows}),'source_rows':len(rows),'workbook_rows':ws.max_row-start+1,'cells':sum(len(r[3])for r in rows),'mismatches':len(mismatch),'samples':mismatch[:4]})
(OUT/'source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'mechanical_summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2),encoding='utf8')
with (OUT/'independent_cell_comparison.csv').open('w',newline='',encoding='utf-8-sig')as f:
 w=csv.DictWriter(f,fieldnames=cells[0]);w.writeheader();w.writerows(cells)
print(json.dumps(summaries,ensure_ascii=False,indent=1))
