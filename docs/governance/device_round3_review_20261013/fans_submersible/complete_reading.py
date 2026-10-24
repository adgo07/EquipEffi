from pathlib import Path
import json,hashlib,datetime,re,csv
O=Path(__file__).parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):(O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
coverage=[]
for s in ['gb19761_2020','gb28381_2012','gb28381_2026','gb32030_2022','gbt36561_2018']:
 p=Path('_acceptance_20261013/reviews')/(s+'_ACCEPTANCE_REVIEW.md')
 coverage.append({'standard':s,'path':str(p.resolve()),'sha256':sha(p),'lines':len(p.read_text(encoding='utf8').splitlines()),'complete_text_read':True,'including_errata_appendices_and_limitations':True,'numeric_full_replay_this_round':False})
save('read_coverage.json',{'completed_utc':now,'files':coverage,'method':'全文分段读取；不是只摘发现章节，不声称重演旧报告全量数值程序'})
d=json.loads((O/'round3_findings.json').read_text(encoding='utf8'))
for idx in [3,9]:
 d[idx]['priority']='P2';d[idx]['priority_reason']='已核事实清楚，当前属于定位/引用补录，不新增Owner算法决定；后续漏读误实现风险仍需防范'
im=O/'A4_original_p04.png'
d[3]['evidence_files'].append({'path':str(im.resolve()),'sha256':sha(im),'source_page':4,'actually_viewed':True})
d[3]['evidence']+='；本轮A4_original_p04.png实际看图：0.95≤ψ<1.05纵向合并，10≤ns<20与20≤ns<30两行，各六机号段；对应A17:J22/A23:J28'
save('round3_findings.json',d)
p=O/'REPORT.md';t=p.read_text(encoding='utf8')
t=t.replace('旧审计全报告很长，本轮定向读取其相关发现、勘误和边界，不声称重新全量复演其数值核验。','五份旧审计均已完整分段读至末尾（含勘误、建议、限制和附录），完整覆盖记录及各文件SHA见read_coverage.json；不声称重新全量复演其数值核验。')
for idx in [3,9]:
 pattern=r'(### '+re.escape(d[idx]['original_id'])+r' .*?)(?=\n### |\Z)'
 t=re.sub(pattern,lambda m:m.group(0).replace('；P1（','；P2（'),t,flags=re.S)
t+='''

## 全文补读后的增补与证据修正

五份旧报告全文已读完：19761 314行、28381-2012 301行、28381-2026 558行、32030 432行、36561 292行（机器清单按实际splitlines记录）。补读不是全量数值重跑。A4、A6统一P2：事实明确，只需定位/引用补录，不需新增Owner算法裁决；16项现为5项P1、11项P2。

A4本轮重新从原PDF物理第4页渲染并实际看图：[A4_original_p04.png](A4_original_p04.png)。表1的0.95≤ψ<1.05纵向合并格跨10≤ns<20、20≤ns<30两行；各行六机号段，所以展开为A17:J22与A23:J28。原PDF与该图SHA见round3_findings.json第4项。Sol未读原页，本项原图证据来自本会话。

补读潜水旧审计E.4发现其算术结论错误：cell_trace首条(pdf_page,printed_page,official_pdf_page)=(4,2,6)，279行均official=pdf+2=printed+4，故official列不是本地S00物理页4，而对应另一12页副本物理页6。旧报告自身§1.2/§1.3已经列出本地p4→副本p6，其E.4却据+2断言S00，混淆了加数基准。不得按旧建议把该列重命名为s00_pdf_page。建议补副本来源清单和列语义，P2；这不证明全文真实性，也不改变279表值核实事实。数据复读证据见supplement_page_offset.json。

旧2012全文还提示§3.1/3.2阈值定义与ηpol计算概念的标签区分、输入表【标准】/【技术判断】标签、README跨版本链接陈旧等。均属文档补全建议，不把正确表值改成新审批要求；转速、等号、修约、外部试验条件继续由既有007—012及后续Numeric Profile设计承载。19761的kp依赖GB/T1236，不能默认1；重复数值不能反推分支。热处理通式/专式、无K值、分母零、温度修正等已由001—011清单覆盖。2026旧报告把第5章插值限定为只有流量的推断不能升为标准明文，附录A.2实际演示压力插值；005仍保留缺端点待定。

另将旧两风机报告共同提醒的“通风机/鼓风机设备归类”单列LOCAL-FAN-BLOWER-IDENTITY，区分设备分类入口与已有跨版本效率/插值问题。潜水产品族重叠、η比例和百分点、附加条件缺失也属于001能力边界下待设计事项，不批准按功率独自归类。所有标准的Numeric Profile均尚待专属设计，不因本次核查自动继承Pump Decimal50。
'''
p.write_text(t,encoding='utf8')
rows=list(csv.DictReader(open('docs/standards/gb32030_2022/evidence/cell_trace.csv',encoding='utf-8-sig')))
save('supplement_page_offset.json',{'path':str(Path('docs/standards/gb32030_2022/evidence/cell_trace.csv').resolve()),'sha256':sha(Path('docs/standards/gb32030_2022/evidence/cell_trace.csv')),'rows':len(rows),'triples':sorted(set(tuple(int(r[k]) for k in ['pdf_page','printed_page','official_pdf_page']) for r in rows)),'all_official_equals_local_plus_two':all(int(r['official_pdf_page'])==int(r['pdf_page'])+2 for r in rows)})
owners=json.loads((O/'owner_items.json').read_text(encoding='utf8'))
if not any(x['id']=='LOCAL-FAN-BLOWER-IDENTITY' for x in owners):
 owners.append({'id':'LOCAL-FAN-BLOWER-IDENTITY','existing_issue_id':None,'standard':'gb19761_2020/gb28381_2012/gb28381_2026','source_location':'19761第1章“本标准适用于一般用途离心通风机和轴流通风机”；28381-2012第1章“离心鼓风机”；2026第1章分透平式与容积式。旧19761§7与2012§7.3分类入口建议。','ambiguity':'用户设备称谓不足以唯一确定通风机或鼓风机及压缩方式；本组不能新增统一压力界线。','impact':'错误归类会选错标准、指标和表。','options':['按设备技术资料与各版适用范围核实','资料不足先保留分类待确认，不凭名称或功率推断'],'recommendation':'Stage B明确设备分类所需证据及未知分类路径；不擅自建立原文没有的通用分界。','evidence_strength':'主标准范围已读；外部设备分类标准未完整取得。','approval_status':'未批准；候选待协调登记','owner_question':'设备分类证据不足或跨称谓时采用何种人工确认及无法匹配处理？是否需补取分类标准？','source_opinion_ids':['旧19761§7','旧2012§7.3','AUDIT§5-16/B7'],'priority':'P1','verified_values_require_new_approval':False})
save('owner_items.json',owners)
with (O/'OWNER_QUESTIONS.md').open('a',encoding='utf8') as f:f.write('\n\n全文补读增补：LOCAL-FAN-BLOWER-IDENTITY，设备归类入口待Owner，具体摘录、选项及证据边界见owner_items.json。现有根27条全部保留，新增候选5条；不重新审批已核表值。\n')
start=json.loads((O/'start_hashes.json').read_text(encoding='utf8'))
end={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':[{'path':x['path'],'sha256':sha(Path(x['path']))} for x in start['files']]}
changes=[{'path':a['path'],'before':a['sha256'],'after':b['sha256']} for a,b in zip(start['files'],end['files']) if a['sha256']!=b['sha256']]
save('end_hashes.json',end);save('hash_changes.json',changes)
t=p.read_text(encoding='utf8');t=re.sub(r'时间为2026-10-13T15:45:21.070753\+00:00至[^。]+。','时间为'+start['utc']+'至'+end['utc']+'。',t);p.write_text(t,encoding='utf8')
save('final_output_hashes.json',{'utc':end['utc'],'input_changes':changes,'files':[{'path':str((O/n).resolve()),'sha256':sha(O/n)} for n in ['REPORT.md','owner_items.json','OWNER_QUESTIONS.md','round3_findings.json','read_coverage.json','A4_original_p04.png']]})
print('input changes',changes,'owner count',len(owners),'priorities',{p:sum(x['priority']==p for x in d) for p in ['P1','P2']})
