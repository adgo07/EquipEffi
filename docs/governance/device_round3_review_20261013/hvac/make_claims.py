from pathlib import Path
import json,hashlib,re
R=Path.cwd();O=R/'docs/governance/device_round3_review_20261013/hvac';manifest=json.loads((O/'source_manifest_start.json').read_text('utf8'))
raw='''B1|all|部分成立|映射错漏|P1|旧PASS未覆盖外部前轮全部发现；15条全部悬空及全部MAJOR不准确|新报告收窄完整映射结论；824值一致仍成立，37479漏6.2及21454单位口径确需补；不因OPEN判失败|旧报告§结论/规则及本轮M2/M4；第三方§2有24行历史意见|无新增标准ID；报告勘误|Sol A5部分成立，一致；原字串零命中不是有效语义检索
B2|all|部分成立|第三方误解或证据不足|P2|两种首轮基线确不同；不等于哈希自相矛盾|named_baselines.json明确12项旧快照与HVAC54清单；三映射前者变、后者未变；29541不在12范围|12项accepted_revision_manifest；HVAC source_manifest；核心15件SHA|无需标准Issue；报告具名基线|Sol B2成立；本组同意须具名，但未变断言在限定基线内为真
M1|19577|核心不成立；可读性建议可采纳|第三方误解或证据不足|P2|PDF9表1/2三级表头横跨主季节指标和COPc，J5三级值归属正确|不可改成无等级归属；I6=COPc、J6=4.2等逐行绑定保留语义；可另增多级表头示意，不必重存XLSX|PDF9；表1/2 I5/J5/I6/J6；本目录两张表头放大图|既有002仍OPEN；不机械新开007|Sol A2否定无等级归属，一致；Sol称扁平化必须修转录，本组收窄为可读性建议，无证据证明指标/级别丢失
M2|21454|成立（单位说明缺口）|映射错漏|P1|B6存1.3、显示130%，公式LD/100要130；映射“数值百分比”易重复除100|补ratio和percent-number换算契约；原表/公式/XLSX值均不改；此为适配说明错漏而非标准错误|PDF9表A.1/2；PDF14 A.9；表A.1 B6:B10、A.2 B6:B10；映射62/98|新增候选LOCAL-HVAC-N01；旧005/007只是建议不抢号|Sol A3成立，一致
M3|37479|原文疑点成立；未登记断言不成立|标准原文疑错歧义|P1|PDF4 §5.1只引表1且涵盖两类；根001及映射已有明确保留|保留Owner，不要求审计者修标准；登记通过可与解释OPEN并存；旧报告已明确说明该限制|PDF4 §5.1及两表题；根001；映射§5|EQP-STD-GB37479-001 OPEN 已完整登记|Sol延伸未定；本组原页确认，否定“未登记”和必须先修正原文才能StageA
M4|37479|成立|映射错漏|P2|主映射遗漏原§6.2辅热测试→GB21455|补原句/路由；它影响完整符合性证据，不改变66等级阈值；旧本组§规则误称已保留须纠正|PDF5 §6.2；映射§5；SOURCE_AND_VERIFICATION页内清单|既有003涵盖外部21455但缺显式路由；N02建议补子项|Sol延伸待核；现以原页核实
M5|19577|核心不成立；拆分仅管理建议|第三方误解或证据不足|P2|“附加指标只在三级表头下”指附加列，不是所有COPc列；表2一级二级主COPc不反证|002多指标底线/通道/数据中心三个子问题及005外部子问题均已保留；不必换号拆三条|PDF9表1/2；根002/005；工作簿E/F/G与I/J|002/005 OPEN；本轮Owner清单分项问题|Sol A2同意原表三级归属；分拆未定；本组不把拆分当实质缺陷
M6|19576|差异留痕成立；缺页未证|第三方误解或证据不足|P2|本地4页有结束线；旧审计8页来自外部出版目录，不能推出多4页正文|具体登记8/4证据差异，取官方全文；不宣称官方完整性已确认，也不撤销本PDF39值一致|PDF1～4尤其PDF4结束线/印刷2；旧F-01外部链接|N03待来源问题登记，非日期001已充分承载|Sol延伸待核；本组确认本地4页，8页原站本轮未认证
M7|19576,37479,21454,19577|部分成立|软件解释待Owner|P1|G1/O1/O2/O4/H5/H6跨标准风险未专门登记，但不是一律标准冲突|N06～N10区分无两标准匹配/同名不同设备/静压用途；不能宣布全体系无标准或自建无适用终态|19576 PDF3/4；37479 PDF3/4；21454 PDF3/4/5/11；19577 PDF8/9|联合候选未正式登记；既有引用问题不能替代路由决定|Sol B7证据不足；本组进一步看本组原页，局部事实确认，仍不接受全体系10/6/7总数
M8|19576,37479|矛盾定性不成立|第三方误解或证据不足|P2|静压0一般范围句加风管明确排除是正常包含/排除关系，不是同一规则自相矛盾|确认G1边界需身份判定；不得因为0Pa包含字样忽视明确排除；无必要制造新的标准笔误|19576 PDF3 §1完整两段；37479 PDF3 §1|与N06同候选，不重复开问题|Sol延伸待核；本组原页否定“互相矛盾”
m1|19576,37479|成立|映射错漏|P2|四类型字段混描述元数据|清理类型字段即可，不影响20编号/OPEN，不升级业务门禁|根001/002(19576)、001/003(37479)|原ID不变；非标准解释|Sol B5成立，一致
m2|all|成立（时点标识建议）|映射错漏|P2|旧报告两处末次根SHA对应维护前后|明确4989190f为补type前，670f9644为补type后；旧快照有效不应覆盖|FINAL_HVAC_REPORT稳定性段/末尾；root_scope_stability|无需Issue；文档时点澄清|Sol B2相关，一致
m3|19577|不成立|第三方误解或证据不足|P2|正确块终止条件到下一个1～3级标题；006后接##章节不是###|本轮复算006得到0d96c083ba59f18d2ec9fbc2013a5bbd74c5cc32c45ab618f75c7973ef55e9b8，与原相同；第三方算法吸收后续##|本目录collect.py/root_blocks.json；旧diff_and_links.py|不改Issue，补算法说明即可|Sol未逐项核；本组可机械反证
m4|21454|部分成立|第三方误解或证据不足|P2|442回读格与376源格不是同一集合；原VERIFICATION已明写含条件/源位文字|建议明确并列计数，不能说442数值造假；本组336是另一个指定坐标集合，均不互加|VERIFICATION原句“440个数据区域格（含条件、源位文字）加2个总计”；comparison_summary|无需标准Issue；报告覆盖说明|Sol延伸待核；本组认可透明计数建议，否定未经说明的全数错误
m5|21454|成立|映射错漏|P2|PDF13/14无可见印刷页码，映射PDF13写印刷11|统一物理页13（顺序第11页、未印）；公式转写不受影响|本轮重看PDF13/14整页；映射§3/§5.2；VERIFICATION已写顺序|新定位维护候选；不需Owner判公式|Sol延伸待核，本组确认
m6|21454|部分成立|映射错漏|P2|项目列未展开到数据区，A13称展开；但类别在A2表题和映射已保留；G列来源是PDF5表注|应修说明准确性并标G为表注派生；不是漏掉户用/工商业整个分支，不强制添加重复列|PDF9表A.1/2；XLSX A2/A13、表4 G5:G7/A10；PDF5表4注|文档表示维护候选；无新标准疑问|Sol延伸待核；本组实读确认部分
m7|21454,19576|成立（版本标记建议）|映射错漏|P2|三映射相对12项快照改变；21454仍A.1，响应另有SHA留痕|建议后续升修订号，不能说现SHA无法识别或数字已变|named_baselines.json；各ACCEPTANCE_RESPONSE/修订字段|无需标准Issue；历史不覆盖|Sol B2相关一致
m8|19576|成立（整理用语标记）|映射错漏|P2|原文无普通二字；当前映射§2作为区分专用分支的简称|标整理用语即可，不影响阈值；R3自称某处已删普通但当前仍含，应以当前全文为准|PDF3/4表1；映射§2第17/19行|文档维护不新批范围|Sol未逐项核
m9|29541|部分成立（来源说明）；排除HVAC清单断言不成立|第三方误解或证据不足|P2|12项确未包括29541；HVAC54清单明确含其PDF/映射/XLSX|本组独立full验47页/23表包括29541，另有专项原审计；不是冒用12项证据。R3一行自称不含又承认含矛盾|本组source_manifest、ACCEPTANCE_REPORT、independent_compare.py；29541专项报告|既有001～005不变；说明不同审计归属|Sol未逐项核；本组直接机器清单反证
i1|all|第三方拆分错误|第三方误解或证据不足|P2|实际56+39+75+336+318=824；R3正文56+39+75+376+288=834，建议278也不是实际集合|总数824正确；本组旧报告已明确21454=336/19577=318；以CSV/summary真实坐标计数|comparison_summary.json及independent_cell_comparison.csv|无需Issue；第三方计数勘误|Sol未逐项核
i2|all|部分成立；第三方集合列错|第三方误解或证据不足|P2|总73=49+24正确，但其历史名单含28381-007～012与本轮49重叠，列表相加30|另24为19577六、28381-001～006六、32030一、19762二、20052九；15标准既有其他项13不含泵变压器|根73标题与issue_registration_audit.csv49集合差|无需Issue；集合精确说明|Sol B3接受73/49/24，一致；本组纠正第三方所列历史名单
i3|all|既有报告已披露；可更清楚|第三方误解或证据不足|P2|root false因并发修改；54源和锁稳定|旧报告明确说根因并发变化未声称全程稳定；本轮再列时点即可|旧final_stability.json 56项；旧报告§当前环境|无需Issue|Sol未逐项核
i4|19577|不采纳错误前提|第三方误解或证据不足|P2|建议合并M1/M5维护建立在无等级归属误读|保留002，可增加表头示意；不新增无等级归属007|PDF9两表头|002 OPEN|Sol A2同意不机械新开007
i5|19576|两处均成立|标准原文疑错歧义|P2|PDF3 APF与PDF4机房AEER各双右括号|本轮4倍渲染AEER确认，R3仅一处疑虑解除；两处疑似排版错误提交Owner，不自关|19576_AEER_parenthesis.png；原PDF3/4|LOCAL-HVAC-N04待登记|Sol延伸未核，本组补原页放大证据'''
rows=[]
for line in raw.splitlines():
 id,s,con,cat,prio,op,finding,loc,reg,sol=line.split('|')
 artifacts=[{'path':x['path'],'sha256':x['sha256']} for x in manifest if s=='all' and (Path(x['path']).name in ['STANDARD_ISSUES_REGISTER.md','comparison_summary.json','ACCEPTANCE_REPORT.md']) or s!='all' and any(k in x['path'] for k in s.split(',')) and (Path(x['path']).suffix in ['.pdf','.xlsx'] or Path(x['path']).name=='STANDARD_MAPPING.md')]
 rows.append(dict(original_id='HVAC-R3-'+id,standard=s,original_opinion=op,classification=cat,conclusion=con,impact_and_priority_reason=prio+'：'+finding,source_location=loc,current_artifacts=artifacts,registration=reg,sol_conclusion_and_comparison=sol))
# Preserve all 24 historical row IDs as a separate crosswalk, not collapse silently.
links={1:'M1',2:'EX19577',3:'M5',4:'M3',5:'M4',6:'REGISTER37479',7:'M6',8:'i5',9:'m8',10:'REGISTER19576',11:'M2',12:'REGISTER21454-001',13:'REGISTER21454',14:'m6',15:'m4/m6',16:'m5',17:'m7',18:'M7/M8',19:'M7',20:'M7',21:'M7',22:'M7',23:'REGISTER29541',24:'REGISTER19577'}
history=[]
text=(R/'_acceptance_20261013/round3/final_hvac_AUDIT.md').read_text('utf-8-sig');section=text.split('## 2. 上轮发现清单的处置状态')[1].split('## 3.')[0]
for line in section.splitlines():
 m=re.match(r'\| (\d+) \|',line)
 if not m:continue
 n=int(m.group(1));history.append(dict(original_id=f'HVAC-R3-H{n:02}',verbatim_opinion_row=line,review_reference=links[n]))
(O/'claim_verification.json').write_text(json.dumps({'claims':rows,'history_crosswalk':history},ensure_ascii=False,indent=2),encoding='utf8')
lines=['# Round3 HVAC 逐条核实（保留原ID）','','分类不是根状态；P1/P2按具体后续影响，不继承BLOCKER/MAJOR票数。Sol未逐项核查的延伸意见明确写未定；未以人数投票。SHA与绝对路径逐项列于claim_verification.json current_artifacts。','']
for x in rows:
 lines.extend([f"## {x['original_id']} — {x['standard']}",'',f"原意见要点：{x['original_opinion']}",f"分类：{x['classification']}。核实：**{x['conclusion']}**。",f"影响/优先级理由：{x['impact_and_priority_reason']}",f"决定性证据：{x['source_location']}",f"根ID/缺登记：{x['registration']}",f"Sol对照：{x['sol_conclusion_and_comparison']}",''])
lines+=['## 历史24行逐条回链','','原行逐字存于JSON history_crosswalk；此处不把24行重复算成24个新缺陷。','']
for h in history:lines += [f"- {h['original_id']} → {h['review_reference']}"]
lines+=['','EX19577（历史H02）逐项：旧建议008不成立为漏语义：主映射§4明确表1D17为容量横线未分档、表4D6:D8为跨三行合并；保留二者结构，不把横线当0。旧建议009：本轮亲看PDF14合计印1 007，XLSX C21=1007正确数值等价，可加词法注记，非标准疑错。旧建议010：本轮亲看PDF10有完整表4标题（本目录图），原“无独立表题”不成立；XLSX A2为通用简称，补全名称仅可读性建议。Sol对此三项未逐项核，本组追加实际原页证据。','','REGISTER各项：当前20ID完整逐一见owner_items.json与root_blocks.json。H06三项=37479-001/A、002/C、003/B；H10两项=19576-001/R01、002/R02；H12=21454-001；H13四项=21454-001～004；H23五项=29541-001～005；H24六项=19577-001～006。全OPEN、登记已完成，不等于解释关闭；Sol对49整体仅做索引，非每条原文复核，不能以其计数替代本组20项阅读。']
(O/'CLAIM_VERIFICATION.md').write_text('\n'.join(lines),encoding='utf8')
print(len(rows),len(history))
