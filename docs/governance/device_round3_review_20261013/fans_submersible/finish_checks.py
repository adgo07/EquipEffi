from pathlib import Path
import json,re,hashlib,datetime,openpyxl
O=Path('docs/governance/device_round3_review_20261013/fans_submersible');s=Path('docs/governance/device_full_acceptance_20261013/third_party_executor_verification_20261013/EXECUTOR_VERIFICATION.md');solhash=hashlib.sha256(s.read_bytes()).hexdigest()
d=json.loads((O/'round3_findings.json').read_text(encoding='utf8'))
for x in d:
 i=int(x['original_id'].split('-')[-1]);x['sol_conclusion']='延伸项未在Sol本轮逐项原页核查；不以Sol未反对当成证据';x['comparison_to_sol']='Sol未形成独立结论，本报告补充原页/文件证据'
 if i==1:x['sol_conclusion']='A5部分成立，不能把旧问题全部未修照搬';x['comparison_to_sol']='一致；本轮逐项限定并纠正计数'
 if i==4:x['sol_conclusion']='A4部分成立：行段定位补强，非错误阈值或BLOCKER';x['comparison_to_sol']='一致；本轮加原图核查'
 if i==10:x['sol_conclusion']='A6成立：数据层已修，主映射冲突未同步';x['comparison_to_sol']='一致'
 if i==13:x['sol_conclusion']='B3成立：49新增含R11，另24历史，根73';x['comparison_to_sol']='一致；本组27另分20+7无冲突'
 if i==16:x['sol_conclusion']='B7总量证据不足，部分边界值得登记';x['comparison_to_sol']='一致；只列本组已核具体边界'
 x['evidence_manifest']='start_hashes.json（按standard关联当前PDF/映射/工作簿的绝对路径SHA）；Sol SHA '+solhash
(O/'round3_findings.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
a=json.loads((O/'owner_questions.json').read_text(encoding='utf8'));out=[]
for x in a['existing']:
 id=x['existing_issue_id'];op=[q['original_id']+'/'+q['problem_list_id'] for q in d if id in q.get('existing_issue_id','')]
 out.append({'id':id,'existing_issue_id':id,'standard':x['standard'],'source_location':x['source_excerpt_and_location'],'ambiguity':x['impact'],'impact':x['impact'],'options':x['question_and_options_recommendation'],'recommendation':x['question_and_options_recommendation'],'evidence_strength':x['evidence_strength'],'approval_status':x['approval_status'],'owner_question':x['question_and_options_recommendation'],'source_opinion_ids':op or ['既有根Issue及专属登记请求，非R3新发现'],'priority':x['priority'],'verified_values_require_new_approval':False})
for x in a['additional_candidates']:
 out.append({'id':x['candidate_id'].replace('NEW-','LOCAL-'),'existing_issue_id':None,'standard':x['standard'],'source_location':x['source_excerpt_and_location'],'ambiguity':x['question_and_options_recommendation'],'impact':x['impact'],'options':x['question_and_options_recommendation'],'recommendation':x['question_and_options_recommendation'],'evidence_strength':x['evidence_strength'],'approval_status':x['approval_status'],'owner_question':x['question_and_options_recommendation'],'source_opinion_ids':['F5' if 'SCOPE' in x['candidate_id'] else 'AUDIT§5-16/B7'],'priority':'P1','verified_values_require_new_approval':False})
(O/'owner_items.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
# Compare 5 of the supplied 12 snapshots to current workbook values, retaining exact display differences.
primary=json.loads(Path('docs/governance/device_full_acceptance_20261013/fans_submersible/source_manifest.json').read_text(encoding='utf8'));snap=[]
for x in primary:
 if not x['path'].endswith('.xlsx'):continue
 st=x['standard'];p=next(Path('_acceptance_20261013/round3/evidence_snapshots').glob(st+'__*.txt'));txt=p.read_text(encoding='utf8');wb=openpyxl.load_workbook(x['path'],read_only=False,data_only=False);sn=None;changes=[];count=0
 for line in txt.splitlines():
  if line.startswith('==== SHEET '):sn=line.split('==== SHEET ')[1].split('  max_row')[0]
  elif line.startswith('R') and ' | ' in line:
   for segment in line.split(' | ')[1:]:
    m=re.match(r'([A-Z]+\d+)=(.*)',segment)
    if not m:continue
    cell,old=m.groups();v=wb[sn][cell].value;count+=1
    if str(v)!=old:
     try:eq=float(v)==float(old)
     except (ValueError,TypeError):eq=False
     if not eq:changes.append({'sheet':sn,'cell':cell,'old':old,'current':v})
 snap.append({'standard':st,'snapshot_path':str(p.resolve()),'snapshot_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'cells_compared':count,'differences':changes,'note':'已记录旧非空格逐格比较；该txt不证明旧时间戳、样式或XML字节，不替代本组首轮全sheet快照差异'})
(O/'snapshot_comparison.json').write_text(json.dumps(snap,ensure_ascii=False,indent=2),encoding='utf8');print([(x['standard'],x['cells_compared'],len(x['differences'])) for x in snap])
# Supplement current verification facts without writing sources.
w=openpyxl.load_workbook(next(Path('docs/standards/gb19761_2020/data').glob('*.xlsx')));facts={'fan':{sh.title:{'worksheet_filter':sh.auto_filter.ref,'table_filters':[t.autoFilter.ref if t.autoFilter else None for t in sh.tables.values()],'merged_ranges':list(map(str,sh.merged_cells.ranges))} for sh in w},'dash_note':w['表2']['J51'].value,'ns_cells':[w['表1']['C17'].value,w['表1']['C23'].value],'sol_sha256':solhash}
(O/'target_checks.json').write_text(json.dumps(facts,ensure_ascii=False,indent=2),encoding='utf8')
