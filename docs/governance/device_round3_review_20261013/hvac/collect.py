from pathlib import Path
import hashlib,json,re,collections,openpyxl,fitz
R=Path.cwd(); O=R/'docs/governance/device_round3_review_20261013/hvac'; prior=R/'docs/governance/device_full_acceptance_20261013/hvac'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=json.loads((prior/'source_manifest.json').read_text('utf-8-sig'))
manifest=[dict(path=x['path'],sha256=sha(Path(x['path'])),first_hvac_sha256=x['sha256'],unchanged=sha(Path(x['path']))==x['sha256']) for x in base]
extra=[R/'STANDARD_ISSUES_REGISTER.md',R/'platform-lock.json',R/'_acceptance_20261013/accepted_revision_manifest.json',R/'_acceptance_20261013/accepted_revision_manifest_secondary.json',R/'_acceptance_20261013/CROSS_STANDARD_ACCEPTANCE_SUMMARY.md',R/'_acceptance_20261013/CROSS_STANDARD_BOUNDARY_AUDIT.md',R/'_acceptance_20261013/round3/final_hvac_AUDIT.md',R/'_acceptance_20261013/round3/ROUND3_PROBLEM_LIST.md',prior/'ACCEPTANCE_REPORT.md',prior/'comparison_summary.json',prior/'independent_cell_comparison.csv']
for k in ['gb19576_2019','gb19577_2024','gb37479_2019','gb21454_2021']:extra.append(R/f'_acceptance_20261013/reviews/{k}_ACCEPTANCE_REVIEW.md')
manifest += [dict(path=str(p),sha256=sha(p)) for p in extra]
(O/'source_manifest_start.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
root=(R/'STANDARD_ISSUES_REGISTER.md').read_text('utf-8-sig')
blocks={m.group(1):m.group(0).strip() for m in re.finditer(r'^### (EQP-STD-GB(?:29541|19577|37479|19576|21454)-\d+)\b.*?(?=^#{1,3} |\Z)',root,re.M|re.S)}
(O/'root_blocks.json').write_text(json.dumps({k:dict(text=v,sha256=hashlib.sha256(v.encode()).hexdigest()) for k,v in blocks.items()},ensure_ascii=False,indent=2),encoding='utf-8')
print('root',sha(R/'STANDARD_ISSUES_REGISTER.md'),'counts',len(blocks),collections.Counter(k.split('-')[2] for k in blocks))
print('006sha',hashlib.sha256(blocks['EQP-STD-GB19577-006'].encode()).hexdigest())
for x in manifest:
 if 'first_hvac_sha256' in x and not x['unchanged']:print('changed since hvac',x['path'])
for x in manifest:
 p=Path(x['path'])
 if p.suffix=='.xlsx':
  wb=openpyxl.load_workbook(p,read_only=False,data_only=False)
  key=p.parent.parent.name
  cells={}
  wanted={'gb19577_2024':{'表1':['I5','J5','D17'],'表2':['I5','J5'],'表4':['A1','A2','D6','D7','D8'],'表A.2':['C21']},'gb21454_2021':{'表4':['G5','G6','G7','A10'],'表A.1':['A2','A5','B6','B7','B8','B9','B10','A13'],'表A.2':['A2','B6','B7','B8','B9','B10','A13']}}.get(key,{})
  for s,cs in wanted.items():
   cells[s]={c:{'value':wb[s][c].value,'format':wb[s][c].number_format} for c in cs}
  (O/f'{key}_cell_evidence.json').write_text(json.dumps(cells,ensure_ascii=False,indent=2),encoding='utf-8')
  if cells:print(key,json.dumps(cells,ensure_ascii=False))
# Save freshly rendered decisive crops (not edited standard pages).
for s,page,rect,name in [('19577',9,(330,210,560,300),'19577_table1_header'),('19577',9,(325,585,558,645),'19577_table2_header'),('19576',4,(65,200,205,280),'19576_AEER_parenthesis'),('19577',10,(170,330,450,350),'19577_table4_title')]:
 pdf=next(Path(x['path']) for x in base if Path(x['path']).suffix=='.pdf' and s in Path(x['path']).name)
 d=fitz.open(pdf); pg=d[page-1]; pix=pg.get_pixmap(matrix=fitz.Matrix(4,4),clip=fitz.Rect(*rect)); pix.save(str(O/(name+'.png')))
