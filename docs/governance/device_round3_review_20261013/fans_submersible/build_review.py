from pathlib import Path
import json,re,hashlib,openpyxl,datetime,csv
O=Path('docs/governance/device_round3_review_20261013/fans_submersible');B=Path('docs/standards');R=Path('STANDARD_ISSUES_REGISTER.md').read_text(encoding='utf8')
def save(n,x):(O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
# Preserve original audit IDs and claims exactly, do not substitute the condensed list's numbering.
a=Path('_acceptance_20261013/round3/final_fans_submersible_AUDIT.md').read_text(encoding='utf8');sec=a.split('## 5. 新发现的问题')[1].split('## 6.')[0];claims={}
for l in sec.splitlines():
 if re.match(r'\| \d+ \|',l):
  p=l.split('|');claims[int(p[1].strip())]=l
D=[]
def add(i,alias,st,cat,verdict,priority,why,ev,root='无；仅候选，不分配稳定ID'):
 D.append(dict(original_id='AUDIT§5-'+str(i),problem_list_id=alias,standard=st,original_opinion=claims.get(i,''),classification=cat,conclusion=verdict,priority=priority,priority_reason=why,evidence=ev,existing_issue_id=root))
add(1,'F1/A5','组报告','映射错漏','成立范围：旧本组结论“完成主标准全文/逐表整理证据复核”过宽，未承接外部旧审计的文档发现。本报告明确撤回其作为“主映射全覆盖/全部旧发现闭合”的用法；不撤回468及4602数值一致事实。第三方“15项”分组实际相加18，且若干指控下文不成立，不整体照搬。','P1','错误收口会让未决路由进入Stage B','旧final_fans_submersible/REPORT.md首段；CROSS_SUMMARY§4.3～4.7')
add(2,'F2','gb28381_2026','标准原文疑错歧义/软件解释待Owner/第三方证据不足','不得直接接受第三方“001方向近似正确、002缺口已证伪”定论。p20式3的R为J/(kg·K)，hpol标签为kJ/kg；p21式4Ptot明确kW，第三方推导写W不是原文。可用统一SI或kJ链换算解决实现，但原文等式/标注如何表述仍需Owner。006确可细化为先显示值再传递，不能说原台账“示例逐步舍入”完全被证伪；005缺端点问题已有登记，不要求重复编号。','P1','单位链可造成1000倍；不得因另一方结论擅改解释','PDF20/21式1～5、22/23示例；原图已重新读；主映射§5.1','EQP-STD-GB28381-001/002/005/006')
add(3,'F3','gb28381_2026','映射错漏/软件解释待Owner','原图确认表6 q=2低压及高压两端为—，中间有值；q=200末两列—。应补结构描述，但不存在单行有效区内部被两数值夹住的洞；“内部窗口/空洞”需精确定义。原005已覆盖缺端点算法，不把未新建014等同于零登记。','P1','缺端点插值会改变阈值','PDF17表6首行、19末行；工作簿表6对应q=2/200','EQP-STD-GB28381-005')
add(4,'F4/A4','gb19761_2020','映射错漏','成立为定位粒度不足，非值错误。主映射列出两个ns及总块但没单列A17:A22/A23:A28；工作簿C17/C23正确，各6机号。补行段不需改标准解释。','P1','避免下游把两原文行误当两个展开记录','PDF4表1；表1!A17:J28；主映射§4')
add(5,'F5','gb28381_2012','标准原文疑错歧义','原页确认第1章括注仅贴高速项，表1/5低速标题亦有双进气单侧叶轮。需登记范围疑点并由Owner决定，不自行按表标题扩大。第三方同份报告把2012与2026都建议014，编号建议不可直接使用。','P1','可能改变适用设备','PDF3§1，PDF4表1题、PDF6表5题；主映射§2；未见现根对应独立条')
add(6,'F6','gb28381_2012','第三方证据不足/映射补充建议','73.0原值正确且现工作簿表4!H18=73。R12-06现有其他非单调示例，不列尽每个异常不等于漏表值；可补证据，但“缺例即MAJOR”不成立，不修73。','P2','只增强已登记疑点例证，不改变路由','PDF6表4 b2/D2=0.081～0.090,Z=2,>801；H18','EQP-STD-GB28381-012')
add(7,'F清单补充','gb28381_2012','映射错漏','原PDF3§4用“转数”，映射用“转速”，建议加原文字词留痕；不能据此认定转速分类数值错误。','P2','术语来源精度，未给新转速界线','PDF3§4；STANDARD_MAPPING§2；请求R12-04','EQP-STD-GB28381-010（可补事实）')
add(8,'F清单补充','gb32030_2022','映射错漏/第三方证据不足','3.1定义“规定试验条件、规定点最低允许效率”主映射未明确摘录，成立。交叉副本未入source_inventory成立但SOURCE_AUTHENTICITY已有路径来源，不是隐匿源；脚注/编者提示应登记扫描区。“不注日期”是对引用的上下文简称，不足判为标准实质转录错。四项合并升MAJOR不采纳。','P2','定义与追溯补全；绝对效率依赖另由001管控','PDF3§3.1；SOURCE_AUTHENTICITY；source_inventory S00～S07；表1～6末行','EQP-STD-GB32030-001（来源补充）')
add(9,'F8','gbt36561_2018','第三方误解','不成立：batch1有明确开始/结束时间，只约束窗口输入。后续文件变更不能推翻窗口内无变化；最终复验已新取清单。本次不重写历史SHA。第三方“内容完全相同”至多指files数组，时间字段不同。','P2','应纠正审计时序推理，非业务数据缺陷','gbt36561_batch1/start_hashes.json/end_hashes.json/REPORT.md；final复验新清单')
add(10,'F7/A6','gbt36561_2018','映射错漏','成立：主映射全文30829与R11均未出现。§7.3～7.5引用30839.4本身正确，不能改错这一句；应在表15/问题入口补两处原文冲突及R11。数据H354:H361已经正确，不能重复指控未修数据。','P1','主入口无法直接看到真实引用冲突，可能静默采一','PDF17表15；主映射表15行/§5/§8；正文表值!H354:H361','EQP-STD-GBT36561-011')
add(11,'F清单补充','gbt36561_2018','映射错漏','说明!B12的R01～R10及待登记为过时描述，成立；应更新为根001～011而不改变OPEN。','P2','交接状态陈旧，已有可达根权威','XLSX说明!B12；请求正式编号回链','EQP-STD-GBT36561-001～011')
add(12,'F清单补充','gbt36561_2018','第三方误解','两项均不成立：原图p14表12间歇8行，p15续表2行，合计10×3=30，全部当前T12记录为数值，无3条附加条件记录；附录A.3放大原图为大写Y，非小写y。不得按建议把正确映射改成9行/小写。','P2','防止错误审计引入新缺陷','PDF14/15表12；T12-0296～0325；PDF22式A.3；本目录A3_symbol.png')
add(13,'B3/口径','组报告','第三方证据不足','本组27=20新增+7既有，旧报告已如此写；其他49统计边界由父核查，不能归成本组数值不一致。','P2','计数边界解释，不影响事实','本组final REPORT首段、台账27项')
add(14,'F清单补充','组报告','第三方误解','所指当前组报告无“同目录另有子目录”句；batch1为平级事实正确，建议采用../gbt36561_batch1明确链接，不凭不存在句子定错。','P2','文件导航建议','final_fans_submersible/REPORT.md全文；实际目录')
add(15,'F清单补充','组报告','映射补充建议','可承接执行者42抽核/independent_review NOT_RUN边界。独立468全量底稿已另证，执行者NOT_RUN不等于独立验收未做。','P2','证据角色清晰','check_results.json；batch1 checks/numeric_regression；首轮人工底稿')
add(16,'B7','跨标准','软件解释待Owner','两版效率测试口径不同、19761未授权插值而2026规定插值均须隔离；“不可互相折算”宜表述未经依据不能互用，不能断言物理上永远无法换算。2026实施2027-04-01是既知元数据，非阻断选版规则。多级罗茨未由本组这两标准提供确定路径，不能自行移植单级表。','P1','跨版本/类型误路由影响结果','2012 PDF4/6；2026 PDF5/7/20；19761§5；根无独立跨标准条')
save('round3_findings.json',D)
# Additional inherited comments, kept separate from the 16 new audit items.
extras=[('OLD-19761-DASH','19761表2 E51:G51原页单个跨3级横杠展开，J51已明确同源横向合并，主映射也说明非三个独立空白。无Excel合并不等于语义丢失；不要求强制merge。','P2'),('OLD-19761-FILTER','4个sheet确有Excel Table，但sheet.auto_filter及Table.autoFilter均None；“筛选表”至少未证明筛选控件可用，属于说明/交互待验证，不是限值错。','P2'),('OLD-19761-82','主映射§5.2明确89.5/87/82且引§5.3b5；§5.3说最低与对应3级一致。因此不是82遗漏，仅可补直接交叉引用。','P2'),('OLD-2012-Z','单级原表无Z列而工作簿C6起=1，合理派生身份但宜标注技术/规范化字段，非原文新增列。','P2'),('OLD-2012-LABEL','旧审计指出§3/§5技术判断与标准标签混排及表题括注缩写，需在源/推导之间标清；本轮不据此改范围，范围Owner见F5。','P2'),('OLD-2026-ROW','源网格行在每续表从表头重计，主映射已有说明，VERIFICATION可同步，不是错坐标。','P2'),('OLD-ENV','pypdf/artifact-tool复现依赖、node_modules本机junction属执行环境；AGENTS禁止把机器路径当跨机身份，不等于禁止本地临时依赖。提交清洁/重建指引由父统一，不做源删除。','P2'),('OLD-INDEX/B4','标准总索引续批入口缺项由父协调，属于发现落点而非根Standard Issue解释；本组不改。','P2'),('B8','36561已声明表定位清单为完整坐标权威，外置设计本身不是缺陷；A6仍需补表15冲突入口。','P2'),('R3-FS03-EVIDENCE','第三方FS03表中把井式950原图写[0.5,1,1.5]，实际[1,1,2]，其中心值结论正确但相邻证据误抄。','P2')];save('inherited_supplement.json',[{'original_id':i,'conclusion':t,'priority':p} for i,t,p in extras])
print('findings',len(D),'supplements',len(extras))
