# 15标准Round3独立核实入口

本轮产物只在 `device_round3_review_20261013` 新增，未修映射、工作簿、生成器、根台账、运行时、旧报告，未提交。任务是核实第三方意见及整理未决解释，不是一次新的软件支持批准。泵、变压器不重开验收。

## 分组交付

|分组/正式标准|逐意见证据|Owner解释清单|
|---|---|---|
|电机：18613、30254、30253|[REVIEW](../motors/REVIEW.md)、[Sol逐项对照](../motors/SOL_COMPARISON.md)、original_opinions.json；28条原ID，原页图、快照和SHA见组清单|[owner_items.json](../motors/owner_items.json)：9根ID，另列LOCAL候选|
|压缩机/锅炉：19153、24500|[ROUND3_REVIEW](../compressor_boiler/ROUND3_REVIEW.md)、findings.json/csv；11原条目及4扩展；runtime_discrepancies.json|[owner_items.json](../compressor_boiler/owner_items.json)：6根ID，另列LOCAL候选；[中文解释](../compressor_boiler/UNRESOLVED_INTERPRETATIONS.md)|
|热工：29541、19577、37479、19576、21454|[ROUND3_HVAC_REVIEW](../hvac/ROUND3_HVAC_REVIEW.md)、[CLAIM_VERIFICATION](../hvac/CLAIM_VERIFICATION.md)、claim_verification.json；24条R3与24条历史处置，旧专项意见另在组稿|[owner_items.json](../hvac/owner_items.json)：20根ID及子问题/LOCAL；[中文解释](../hvac/OWNER_UNRESOLVED_INVENTORY.md)|
|风机等：19761、28381—2012、28381—2026、32030、36561|[REPORT](../fans_submersible/REPORT.md)、round3_findings.json；16原条目及继承意见；源图/快照/SHA在组目录|[owner_items.json](../fans_submersible/owner_items.json)：27根ID及LOCAL；[中文解释](../fans_submersible/OWNER_QUESTIONS.md)|

四组正式ID集合=62/62，字段完整性和精确输入SHA见[GROUP_COVERAGE_CHECK.json](GROUP_COVERAGE_CHECK.json)。其中某些LOCAL子问题关联同一已有根ID，不增加稳定编号；跨标准候选还须与父协调的24讨论项去重。行数不是新缺陷数，文本字段齐备也不是解释已批准。

最终四组Owner表为103行：64行关联62个唯一既有编号、39行无正式编号（含设计/维护和跨标准重复）。各组输入稳定窗口分别52/52、147/147、69/69、185/185；集合有交叠，不相加冒称独立文件数。风机五份旧审计全文补读记录见read_coverage.json，A4本轮原页证据见A4_original_p04.png。原意见逐字文本及Sol对照已分别固定在组JSON中。

## 本轮实质纠偏

需客观补充的主映射包括：GB37479 §6.2辅热试验引用；GB21454百分比显示/比值储存与公式LD取值衔接；GB/T36561表15真实30829.4与条文30839.4冲突入口；GB19761两组ns各6机号的展开坐标；30254/30253前言版次变更事实。各项是否纯资料补录或影响解释由组表区分，不能全要求Owner重新批准。

旧运行时资产还有两类关联事实风险：30253把原页0.0陈述成“—”并存null；19153旧JSON把原表有普通/液冷双值的30组合存null。新工作簿正确值不因此变错；本轮也不修运行时、不选择业务返回策略。锅炉天然气左栏“非冷凝”专属性是解释候选，不能把推断当原文。

第三方不能直接采用的建议包括：19577 COPc“无等级归属”（原表三级确跨两列）、19577表4无题（实际有题）、36561表12改9行（实际10数值行）、36561 A.3改小写y（原图大写Y）、36561井式950℃相邻[0.5,1,1.5]（实际[1,1,2]）、30254缺值页被当全表页、batch1窗后变化被当窗内不稳定。第三方自行撤回的3项亦继续保留为撤回，不重新发修。

对GB28381—2026单位/近似式的争论不作擅自关闭：尤其式4原文Ptot为kW，不能换成W后宣告原文单位问题已经证伪。可行实现换算与原文事实分别列入Owner问题。

## 对旧PASS的精确修正

旧总报告 `FINAL_REVIEW_STATUS.md:3` 和各组完整覆盖断言过宽，不能再用来表示“所有历史意见已处理”或“主映射没有漏项”。主映射遗漏由本轮新证据修正，旧文件不改。保留其各自有效的数值、快照、登记核实证据；49项新增登记的编号/回链/OPEN不等于现存62项全部解释批准。详见[旧断言与时点](REVIEW_SCOPE_AND_PRIOR_CLAIMS.md)。

Sol主17项核查与本轮独立结论逐项比较见[MAIN_OPINION_CROSSWALK](MAIN_OPINION_CROSSWALK.md)。Sol自述49仅计数/抽读、B7未全核、A4未重新看原页，不能扩大其证据。B1来源变化不证明验收者修改，是作者主语归责分歧；A2的表头可读性建议也不等同转录等级错误。

本轮不作“15项无条件全PASS”收口，交付逐项核实与待办清单。未取得官方全文同一性、外部引用全文或Owner解释时，明确保留边界；OPEN本身不是映射事实失败或新增门禁。
