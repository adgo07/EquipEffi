from pathlib import Path
import json,hashlib,collections
R=Path.cwd();O=R/'docs/governance/device_round3_review_20261013/hvac'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
start=json.loads((O/'source_manifest_start.json').read_text('utf8'));end=[]
for x in start:end.append(dict(path=x['path'],start_sha256=x['sha256'],end_sha256=sha(Path(x['path'])),stable=x['sha256']==sha(Path(x['path']))))
(O/'source_stability_end.json').write_text(json.dumps(end,ensure_ascii=False,indent=2),encoding='utf8')
owner=json.loads((O/'owner_items.json').read_text('utf8')); core=[x for x in start if Path(x['path']).suffix in ['.pdf','.xlsx'] or Path(x['path']).name=='STANDARD_MAPPING.md']
summary=json.loads((R/'docs/governance/device_full_acceptance_20261013/hvac/comparison_summary.json').read_text('utf-8-sig')); counts=collections.Counter()
for k,v in summary.items():counts[k.split('/')[0]]+=v['checked']
report='''# 五项热工 Round3 独立核实报告

2026-10-13；独立核实分组 `/root/device_acceptance_astra/hvac`。只写本目录；未改映射、PDF、XLSX、代码、根台账、旧报告，未提交。第三方意见和旧PASS都不是本轮真值。

**结论：原表数值一致的既有证据保留；完整映射资料仍需有针对性的文档补充及未登记事项入账，不给五项整套无条件PASS。** 确认 GB21454 负荷率存储比值与公式LD百分数数值之间缺少明确说明，GB37479主映射遗漏§6.2。GB19577“COPc无等级归属”和“表4无标题”被原页直接证伪；不能按该意见改坏已正确表头。未决标准解释继续保留Owner，登记与解释批准分开。

## 逐条处理与范围

- [CLAIM_VERIFICATION.md](CLAIM_VERIFICATION.md) / [claim_verification.json](claim_verification.json)：R3 B1/B2、M1～M8、m1～m9、i1～i5，共24原意见；另24历史处置行逐一回链。JSON保存原审计行逐字内容、源行号与SHA，核实判断另列，避免把审计意见改写成自己的结论。
- [EARLIER_OPINIONS_CROSSWALK.md](EARLIER_OPINIONS_CROSSWALK.md)：主清单A/B/H相关ID、早期四份热工核验及29541专项R-01～R-11。已修、已有登记、事实不成立和表示建议分别记录；旧建议编号不冒充现根ID。
- [OWNER_UNRESOLVED_INVENTORY.md](OWNER_UNRESOLVED_INVENTORY.md) / [owner_items.json](owner_items.json)：33审阅单元，覆盖20/20既有根ID（29541五、19577六、37479三、19576二、21454四），另13个扩展/候选单元。其中N02/N12分别回连37479-003/19577-005，不新增重复根ID。新候选只用LOCAL-HVAC标识。每项含原文定位/摘录、影响、备选建议、证据强弱、批准状态、具体Owner问题及源绝对路径SHA。

这些计数是审阅单元，不是33个新标准错误。已核实的换算、表头、范围排除不重新要求批准；公开日期不让Owner选择事实；Owner问题仅面向真正未决的软件解释、补证和后续接入边界。

## 关键核实及对旧报告的纠正

|对象|原页/当前证据|本轮结论及优先级|
|---|---|---|
|GB19577表1/2 COPc|PDF9，三级标题明确横跨主季节指标及COPc；本目录两张4倍表头裁图；表1/2 I6=COPc、J5=3级值|第三方核心事实不成立。Sol也否定无等级归属；其“必须改转录”收窄为P2可读性建议。三级底线是否约束高级别及数据中心规则仍由根002承载，不能由表头直接批准组合算法|
|GB19577表4标题|PDF10有“表4 水(地)源热泵机组能效等级指标”；本目录裁图|旧审计F-04/建议010原文判断错误；不登记“无标题”|
|GB21454负荷率|PDF9为130%等；Excel B6=1.3、0%显示；PDF14 A.9为LD/100|P1映射接口说明缺口；Excel比值×100才是该公式LD数值。可用等价ratio入口但必须明示契约。不是PDF公式错、不是XLSX原值错，不自行批准接入|
|GB37479 §6.2|PDF5“辅助电加热的测试方法按GB21455进行”；主映射遗漏|P2完整性缺口（后续符合性测试路由有影响）。**我组旧ACCEPTANCE_REPORT.md“6.2 GB21455…保留”的表述过宽，应纠正为证据页清单有、主映射没有。** 原66阈值一致不受影响|
|GB37479 §5.1|PDF4只引表1但同时说全新风；根001已OPEN|原文疑似漏引属实；“未登记”不成立。保留Owner决定；不得把标准原文未修当本地数值转录错误|
|GB19576来源|当前PDF4页，末页§6.4后结束线/印刷2；早期外部目录称8页|P2具体来源差异应登记。只证明给定PDF内部4页，不证明正文缺4页；官方全文同一性未核，不能替Owner关闭来源疑点|
|GB19576括号|PDF3 APF和PDF4机房AEER各双右括号；本目录AEER放大图|确认两处，R3只确认一处的计数不足。P2原文疑似排版异常保留，未改表值、未自关|
|GB19577 A.13|PDF16“通过测试获得，按公式(A.13)进行计算”|**我组旧建议“试验取得亦可”不能读成与公式任选。** 原句无“或”，映射宜补完整句；测试与公式关系并入005后续补证/Owner，不自定CD算法|
|GB21454页码/类别|PDF13/14无可见印刷页码；A.1/A.2类别在A2表题，数据区无项目列；表4G源自表注|P2定位/表注说明须精确；不得夸大成缺户用/工商业整个分支或错数值|
|跨标准|19576明确排除风管/屋顶/多联；37479要求静压>0；21454静压还作修正；机房指标取决设备结构|候选N06～N11保留。一般包含句加排除句不是矛盾；不能从这几份标准无匹配宣称全国无标准；路由方案待产品身份证据及Owner|

**旧PASS范围纠正**：本组旧完整核对漏识别上述6.2主映射遗漏、负荷率说明不足和部分定位/表示缺口，未对更早12标准意见逐条处置。这是本组复核遗漏，不能用824一致掩盖。保留旧文件为历史，在本报告更正，不伪造旧时已核内容。另一方面第三方15条“悬空MAJOR”并非均成立，详表逐项判断，不全盘继承BLOCKER计数。

## 证据与基线

本轮重新实际看16张原页（29541 PDF4；19576 PDF3/4；37479 PDF4/5；21454 PDF9/13/14；19577 PDF8/9/10/11/12/14/16/17），并从当前PDF新渲染4张决定性裁图。原页渲染来自本组此前全47页证据；已核对应PDF字节SHA不变。全量824位置结果复用已固定来源，不冒称本轮又重抄全部824位置；定向XLSX实读及4份快照全格转储比较另存。

[ snapshot_comparison.json ](snapshot_comparison.json)证明12项旧证据中的四份本组XLSX文本转储与当前一致：19577=1020、19576=159、21454=546、37479=398非空格；包含Sheet尺寸/合并区。它不证明快照真实发生时间或样式/OOXML全字节一致。五份XLSX与本组首次54来源清单SHA完全一致，四份还与更早12项manifest相同。

[named_baselines.json](named_baselines.json)：更早12项与本组全量核对是两个具名基线。相对12项，19576/37479/21454主映射改过文字；相对本组54来源基线，15核心文件均未变，4请求文件仅追加回链的前轮语义核实见reverification/final_hvac。29541不在12项范围，但明确在本组54来源/47页/824对照中，不能据12项未含推成其未验。

当前根SHA为670f9644cd8c9d428e1676c9620c6e7fc573a3ecb9959dac40994971f9b97908；4989190f…是前轮type维护前快照。根共73唯一编号，49登记批次外另24，精确差集见registration_set_check.json（不把2012版28381-007～012重复算入历史24）。本组20根块见root_blocks.json。006块SHA依“直到下一个1～3级标题”可复算为0d96c083…，第三方把后续##章节吸入块导致误报不可复现。

824的真实分组是29541=56、19576=39、37479=75、21454=336、19577=318；R3的376/288或278拆分错误。442工作簿回读格、376旧源格与336本组特定坐标集合各有不同条件列/合并展开/符号范围，不能互换或相加；旧VERIFICATION已写“含条件、源位文字”，不把它污名为442纯数值。

## 平台预检查与限制

复用本轮总协调DISPATCH_INITIAL.md及INPUT_MANIFEST：origin=https://github.com/adgo07/EquipEffi.git，分支codex/six-standard-mappings，HEAD d9f711068bde583138a7f3dded6f64dcaa339761。**本轮父协调fetch已成功**；origin/master=2c7807f32ef08d18554014328efd4ceaa356726f，HEAD领先1/落后0；不沿用上轮TLS失败作为本轮结论。locked central SHA ee5feb0cc34dbd99790500fadd0c4c932e202a20，中央ACTIVE已读854b544563260f9e79c73e714c85f6589e0f19b3。原编制会话/独立角色分工见父DISPATCH，来源被别的执行者修改不等于本验收者修改来源；Sol B1仅据文件变更归因的推断证据不足。

本任务不涉及中央公共Contract。MUST：事实/判断/决定分层、逐项证据、疑点登记、SHA时点具名。MUST NOT：静默改标准、擅批解释、移植Pump数值配置、升scope/support/Frozen。分类为单标准本地映射说明遗漏与待决解释；无中央Contract变更需求。Stage A疑点必须登记，但OPEN本身不是失败；本轮新增尚未入根的真实疑点/路由候选须由协调收录或说明处置，不能冒称整套出口完整。

未新增验证：官方全文同一性、外部引用标准全文、完整季节重算、原生Excel渲染、生产Calculator/Golden。生产unittest/compileall/smoke/性能均NOT_RUN（无代码修改）；未重跑会改源的生成器。没有宣布Phase PASS/READY_FOR_IMPLEMENTATION/SUPPORTED，没有关闭任何疑似标准错。Knowledge capture：无。

## 当前核心文件固定SHA

绝对路径仅为本执行环境证据，不是跨机器仓库身份。全部输入与原意见SHA见source_manifest_start.json、supplemental_evidence_manifest.json；本轮前后稳定性见source_stability_end.json。

|绝对路径|SHA256|
|---|---|
'''
report+='\n'.join('|`'+x['path']+'`|`'+x['sha256']+'`|' for x in core)
report+='\n\n本轮固定输入前后稳定：'+str(sum(x['stable'] for x in end))+'/'+str(len(end))+'；不稳定项：'+str([x['path'] for x in end if not x['stable']])+'。\n'
(O/'ROUND3_HVAC_REVIEW.md').write_text(report,encoding='utf8')
print('stable',sum(x['stable'] for x in end),len(end),'count',dict(counts),'core',len(core))
