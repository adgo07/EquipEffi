# 2026-10-13设备标准映射独立验收汇总

## 当前最终结论（后续复验，优先于下方首轮历史）

正式15项128表已完成复验，结论 **MAPPING_FACTS_PASS**。GB/T36561四项修复通过、49项登记覆盖通过，8处类型分类/排版仅非阻断维护建议；业务解释OPEN仍保留。详见[最终报告](reverification/FINAL_REVIEW_STATUS.md)、[15项完整资产清单](reverification/FORMAL_DELIVERABLES.md)。下方首轮缺陷与批次未完成文字保留历史事实，不代表当前未完成。泵/变压器原确认继续有效，仍排除正式范围。

首轮历史状态：**当前正式范围为15项新编标准、128张原文表；首轮核验完成，GB/T36561修复及48项登记后需定向复验。**本文件为本轮验收结果索引，不替代根问题台账、Profile支持状态、冻结决定或Phase验收。日期按北京时间2026-10-13；原编制与本轮验收分离，Astra/medium请求配置由总协调留证。

## 最新范围纠正（优先于本文历史范围）

用户确认泵和变压器早已确认，不属于本轮正式验收。**正式范围仅15项新编标准版本、128表（166−泵3−变压器35）**。首轮实际额外查看17版本/166表的事实与旧SHA证据保留，不追溯删除或改写；泵/变压器原确认状态继续有效，额外发现仅列查漏补缺建议，撤销其本轮必修/重验身份，不阻断15项验收，不安排二者复验。此前修复候选只作为候选保留，不替换已确认资产。

## 首轮实际审计对象、预检查与方法

本地工作树G:\Python Project\EquipEffi，origin=https://github.com/adgo07/EquipEffi.git，分支codex/six-standard-mappings，HEAD=d9f711068bde583138a7f3dded6f64dcaa339761。受验映射多为未提交资产，逐文件绝对路径/SHA见[PREFLIGHT_INVENTORY](PREFLIGHT_INVENTORY.md)及各组source_manifest，不能仅用HEAD复现。共17个标准版本（15个今日新编版本＋泵双分支同一版本＋变压器冻结双文件），16本XLSX。源PDF由用户提供，保持只读。

locked central SHA=ee5feb0cc34dbd99790500fadd0c4c932e202a20不变。本任务不涉及中央公共Contract。三份ACTIVE指南已线上blob核对一致，见central_guide_online_metadata.json；业务仓fetch TLS失败，远端新鲜度不能确认。适用MUST为范围、分类、输入单位、表值公式、修正、判定、边界、试验依据及原文定位完整；疑点登记；分离标准事实、技术判断、软件决定。MUST NOT为静默改标准、变更Frozen/Golden/支持状态、将自比或Excel作为标准真值。本轮问题是LOCAL DEFECT/本地映射覆盖缺口，不需中央Contract升级。

各组重新从给定PDF逐页看图，再以独立原页转录或独立坐标提取对照真实XLSX/Canonical位置。没有复用旧报告729抽样作为本轮PASS依据。机械数字一致不代替人工表结构、合并格、条件、脚注和公式审查。不同组计数含展开合并格、功率/温度/单位/横杠等，**不合并包装成独立标准数值格总数**。

17项官方题录本轮独立核查见[OFFICIAL_METADATA](OFFICIAL_METADATA.md)：不证明本机PDF官方全文同一性、不覆盖全部外部引用全文，也不冒充全量替代链核查。各组早期报告里“本轮未核官方题录”的限制由这份统一题录核查补充；延期公告全文和其他标准全文仍按各报告未覆盖范围保留。

## 正式15项逐标准结果

|标准|全表核验范围/结果|本轮整体映射结论|证据入口|
|---|---|---|---|
|GB18613—2020|6表，1290源格一致|NEEDS_INFO：4项疑点请求待根登记|[电机报告](motors/GB18613_2020_ACCEPTANCE.md)|
|GB30254—2024|6表，3582源格一致|NEEDS_INFO：2项请求待根登记|[电机报告](motors/GB30254_2024_ACCEPTANCE.md)|
|GB30253—2024|29表，11510源格一致|NEEDS_INFO：3项请求待根登记|[电机报告](motors/GB30253_2024_ACCEPTANCE.md)|
|GB19153—2019|7表，2925位置一致|NEEDS_INFO：R01—R04待根登记|[压缩机锅炉报告](compressor_boiler/ACCEPTANCE_REPORT.md)|
|GB24500—2020|4表78阈值及97%共79位置一致|NEEDS_INFO：A/B请求待根登记|[压缩机锅炉报告](compressor_boiler/ACCEPTANCE_REPORT.md)|
|GB29541—2013|1表及条款数值56位置一致|NEEDS_INFO：001—005待根登记|[热工报告](hvac/ACCEPTANCE_REPORT.md)|
|GB19761—2020|4表405位置一致，全文/脚注已核|NEEDS_INFO：3项请求待根登记|[风机潜水报告](fans_submersible/ACCEPTANCE_REPORT.md)|
|GB28381—2012|8表480位置一致，全文/脚注已核|NEEDS_INFO：6项请求待根登记|[风机潜水报告](fans_submersible/ACCEPTANCE_REPORT.md)|
|GB28381—2026|6表2970位置一致，全文/脚注已核|本PDF映射内容一致；001—006已登记保留，后续公式实现未决|[风机潜水报告](fans_submersible/ACCEPTANCE_REPORT.md)|
|GB32030—2022|6表279位置一致，全文/脚注已核|主标准内容一致；001已登记，外部真实性/完整效率链未验|[风机潜水报告](fans_submersible/ACCEPTANCE_REPORT.md)|
|GB/T36561—2018|29表468记录位置发现1错值；另2条件错误及1静默引用改写已确认|CHANGES_REQUIRED；未修复，发送未确认|[已确认缺陷](fans_submersible/gbt36561_2018/CONFIRMED_FINDINGS.md)|
|GB19577—2024|10表318位置、15编号公式核对|PASS（限定本标准映射事实）；001—006已登记保留，外部依赖不升级|[热工报告](hvac/ACCEPTANCE_REPORT.md)|
|GB37479—2019|2表及条款75位置一致|NEEDS_INFO：A/B/C待根登记|[热工报告](hvac/ACCEPTANCE_REPORT.md)|
|GB19576—2019|1表39位置一致|NEEDS_INFO：R01/R02待根登记|[热工报告](hvac/ACCEPTANCE_REPORT.md)|
|GB21454—2021|9表336位置、9公式核对|NEEDS_INFO：R1—R4待根登记|[热工报告](hvac/ACCEPTANCE_REPORT.md)|

NEEDS_INFO仅指已发现疑点尚未登记根台账，不要求全部OPEN先关闭。已忠实保留且已登记的原文歧义可以作为映射事实验收通过，未决的软件解释仍限制接入。缺少外部试验全文不能被本表值一致抹掉，但也不凭空增加“所有外部依赖解决后才可Stage A”的门禁。

## 已确认需处理问题

1. GB/T36561：表6注a 300mm被写500mm；注b >φ300mm被写≥φ300mm；表11井式炉950℃、0.2～1.0m³的≤1.0h被写≤1.5h。另表15把原文GB/T30829.4静默改为30839.4，未分开原文冲突与技术判断。共4项；XLSX真实坐标及JSON/CSV/构建源传播位置见CONFIRMED_FINDINGS，原会话01a13342-438a-7001-820e-ff5f2fbfc969。总协调向原会话sol/medium发送失败，状态FIX_DISPATCH_UNCONFIRMED，见REPAIR_DISPATCH_RECEIPT；不是已修或复验通过。
2. 【正式范围外补充查漏，不是本轮必修】GB19762：PUMP-A01—A05为额外复查建议和原文附录疑点。表值本轮无差异，原文A.2的2950/2960矛盾不得静默更正或改Approved Golden；原编制会话ID尚未可靠定位。
3. 【正式范围外补充查漏，不是本轮必修】GB20052：TR-F01为24表辅助阻抗参数补全建议，不是损耗错值；原确认有效，本轮不要求新版本或重验，候选保留，不能据额外复查替换V2.1。TR-N01旧段与后续Owner决定依既定优先级解释，不作新业务冲突；D-06温度换算继续DEFERRED。
4. 多标准登记请求未进入唯一根台账；由总协调登记并回链即可复核该出口，不借验收擅批解释。

## 未覆盖与保护边界

各报告明确未覆盖外部规范性引用全文、完整物理试验/季节计算重建、生产Calculator/Golden回放、Excel桌面打印版式。正式unittest/compileall/smoke/性能为NOT_RUN（只读标准资料验收，无代码变更）。不宣布任何Phase PASS，不提升SUPPORTED，不合并、不提交、不发布，不覆盖原PDF、模板、工作簿或冻结双文件。Knowledge capture：无。

逐表清单分别在motors/table_coverage.csv、compressor_boiler报告、hvac报告、transformer/table_coverage.csv和technical_parameter_coverage.csv；fans_submersible/TABLE_COVERAGE.csv。147个XLSX真实sheet结构清单见workbook_sheet_inventory.json，仅定位证据，不能替代数值和原文审查。


## 受验文件结束稳定性

总协调在北京时间22:17:31对初始52项输入（17原PDF＋19映射/分支＋16XLSX）复算，52/52 SHA不变，见source_stability_end.json。泵另含Canonical及共同数值契约的7项快照7/7不变，见pump/source_stability.json。各组派生CSV/JSON与边界候选的额外来源保护见各自manifest/final_checks。旧专项修正方案、规划和候选案例不是另一个主映射，不重复计入17项。


## 首轮完成数量和待登记范围

首轮实际17版本合计166张原文表已逐表覆盖（其中正式15版本128表，另泵/变压器38表为补充查漏）（电机41、压缩机锅炉11、热工23、风机潜水热处理53、泵3、变压器35）。编号公式、单位/范围/判定/边界/脚注的实际覆盖逐项见各组报告，未覆盖的外部引用不计入完成。GB/T36561为1个数值位置不一致及3项文字/条件/引用缺陷；泵及变压器的额外查漏不计入正式15项缺陷或阻断。

除本轮新增发现外，既有目录请求未根登记共48项：电机9，压缩机锅炉6，热工四标准14，风机2012通风机热处理19。按标准为18613=4、30254=2、30253=3、19153=4、24500=2、29541=5、19576=2、37479=3、21454=4、19761=3、28381-2012=6、36561=10。此为验收时点目录请求计数，不是擅自分配48个正式问题ID；合并或复用编号需总协调判断。19577既有6项、28381-2026既有6项、32030既有1项已根登记，OPEN本身不要求关闭。

原编制消息送达未确认后，用户已授权父协调建立Sol/medium替代修复会话；本验收组不另建修复、不自行改受验资产。首轮报告与旧输入SHA保留；收到修复后的具体文件/SHA再独立复验，不用未来修复覆盖本轮缺陷事实。

具体转交修复范围及原会话身份统一见[CONFIRMED_REPAIR_HANDOFF](CONFIRMED_REPAIR_HANDOFF.md)，不将GB19577 A.13非阻断建议混入确定缺陷。

## 正式范围外附件（不重开原确认）

|已有标准|补充查漏附件|当前地位|
|---|---|---|
|GB19762—2025两泵分支|[额外复查证据](pump/PUMP_ACCEPTANCE.md)|原确认有效；A01—A05仅查漏建议，旧报告范围结论已由本最新说明限缩|
|GB20052—2024|[额外复查证据](transformer/ACCEPTANCE_REPORT.md)|原确认/冻结继续有效；TR-F01仅补充建议，候选不自动取代原版；不阻断15项|



## 后续定向复验更新（不覆盖首轮）

GB/T36561前三项已按新SHA完成batch1定向复验，见[报告](reverification/gbt36561_batch1/REPORT.md)和[第三方索引](DEVICE_INDEPENDENT_INDEX.md)。300mm、严格>φ300mm、1.0h五层一致，20记录交叉核验及468值槽回归通过，所捕获922文件前后SHA稳定。FS04及48项登记仍待复验，15项整体尚未终局PASS。泵/变压器不在后续复验范围。


最后更新：8处非阻断类型字段已全部维护且短复验通过；49登记再次通过、其余根文本与旧完整快照完全相同。最终根SHA `670f9644cd8c9d428e1676c9620c6e7fc573a3ecb9959dac40994971f9b97908`。见[最后短复验](reverification/register_type_final_check.json)；此前“待维护”属于历史批次状态。15项当前结论MAPPING_FACTS_PASS。
