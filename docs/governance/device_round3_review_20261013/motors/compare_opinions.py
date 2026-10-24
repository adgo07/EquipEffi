from pathlib import Path
import json,re,hashlib,datetime
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
audit=ROOT/'_acceptance_20261013/round3/final_motors_AUDIT.md'
review=(OUT/'REVIEW.md').read_text('utf-8')
sol=ROOT/'docs/governance/device_full_acceptance_20261013/third_party_executor_verification_20261013/EXECUTOR_VERIFICATION.md'
rows=[]
sol_groups={
'A1':('成立；0.0已有001，运行时冲突未明记；不代Owner决定','D1 N1'),
'A7':('成立，文档完整性，未证实表值错误','C2 N2'),
'B9':('部分成立：历史句未必错误，补时间截面/当前链接','D5 N3'),
'A5':('部分成立：缺外部前轮处置表；字面全文零命中不能作结论','N4'),
'B10':('成立，低风险类型标点/标题元数据','N6 N7'),
'延伸':('Sol未全部原页重查，待复核，不继承严重度','C3 C4 C5 D3 D4 N5'),
'撤回':('三处第三方自撤回不得当缺陷；坐标无错位','B2 B3 B4 C1'),
'登记范围':('9项登记/SHA等局部通过保留，不等于全部解释闭合','B1 C6 D2 D8'),
'未核范围':('未重跑全量几何审计或外部引用全文，不认证PDF渠道','D6 D7 N10'),
'结论边界':('本组MAPPING_FACTS_PASS应限定实际登记/数值复验范围','N8 N9')}
for line in audit.read_text('utf-8-sig').splitlines():
 if not line.startswith('|'):continue
 cells=line.split('|');key=cells[1].replace('*','').strip()
 if not re.fullmatch(r'(?:B[1-4]|C[1-6]|D[1-8]|N(?:10|[1-9]))',key):continue
 mine=next((l for l in review.splitlines() if l.startswith('|'+key+'：')),'')
 solkey,soltext=next(((k,v[0]) for k,v in sol_groups.items() if key in v[1].split()),('未覆盖','Sol没有本条独立结论'))
 relation='一致（限已核事实）；本报告补独立证据'
 if solkey in ['延伸','未核范围','未覆盖']:
  relation='Sol未形成该项独立结论；本轮独立补证或明确保留未核，不视为赞同'
 if solkey=='结论边界':
  relation='Sol仅给总体范围提醒，未形成该项独立结论；本轮独立补充'
 if key=='D8':
  relation='Sol未逐项复核R2/R3原文；本轮独立补证，不能表述为逐项一致'
 if key in ['C3','N5']:relation='Sol未决，本轮独立收窄/不成立，不构成已证实分歧'
 if key=='N1':relation='事实一致；软件处置仅待Owner，不将Sol保留需确认建议变成运行门禁'
 if key=='N4':relation='实质一致；本报告不以路径子串检索证明外部审计已对照'
 if key=='N10':relation='范围分开：Sol/第三方本轮未联网不否定我方先前官方题录核验'
 rows.append({'source_id':key,'original_opinion_row':line,'sol_section':solkey,'sol_conclusion':soltext,'independent_conclusion_row':mine,'agreement_or_difference':relation,'evidence':'REVIEW.md该ID行的PDF物理页/印刷页/Sheet!Cell；文件SHA及UTC时点见source_start.json/checks.json'})
assert len(rows)==28,len(rows)
(OUT/'original_opinions.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# Sol逐意见对照','',f'来源：{sol.relative_to(ROOT)}；SHA256 `{hashlib.sha256(sol.read_bytes()).hexdigest()}`。已全文读取；Sol自述延伸未全面原页复核，不把其“待复核”冒充赞同。原第三方每行意见在original_opinions.json完整保留。','', '|原ID|Sol结论/位置|本轮独立结论定位|一致或分歧|','|---|---|---|---|']
for x in rows:lines.append(f"|{x['source_id']}|{x['sol_section']}：{x['sol_conclusion']}|REVIEW.md对应{x['source_id']}行（含源页/表/cell）|{x['agreement_or_difference']}|")
lines.extend(['','A1分两件事：原文0.0及runtime错误声称为横杠是可核事实；未来采用0、null、需确认或其他结果是Owner标准解释/软件决定。本轮只记录风险，不采纳任何自动改返回值指令。',''])
(OUT/'SOL_COMPARISON.md').write_text('\n'.join(lines),encoding='utf-8')
files=[sol,ROOT/'src/equipeffi/standard_manifest.json',ROOT/'src/equipeffi/domain/evaluation/evaluators/motor.py',ROOT/'src/equipeffi/infrastructure/standards/json_repository.py',ROOT/'V1_SCOPE.md',ROOT/'ROADMAP.md',ROOT/'docs/standards/_STANDARD_MAPPING_TEMPLATE.md',ROOT/'docs/governance/device_full_acceptance_20261013/reverification/final_motors/REPORT.md',ROOT/'docs/governance/device_full_acceptance_20261013/motors/table_coverage.csv',ROOT/'docs/governance/device_full_acceptance_20261013/motors/independent_cell_comparison.csv']
(OUT/'additional_sources.json').write_text(json.dumps({'read_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('28 original opinions preserved and Sol-compared')
