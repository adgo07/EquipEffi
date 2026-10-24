# 五项热工标准最终复验报告

日期：2026-10-13。范围：GB29541—2013、GB19576—2019、GB37479—2019、GB21454—2021、GB19577—2024。

**最终口径：五项 MAPPING_FACTS_PASS_WITH_NONBLOCKING_REGISTER_NOTES；GB29541五个类型字段为非阻断台账维护建议，不影响已核实的映射事实、唯一编号、OPEN及未批准边界。** 首轮四项稳定ID/双向回链缺口已补齐，GB29541类型文案待规范化（非阻断）；本轮没有发现需修改表值、公式或映射事实的新差异。通过只指给定标准PDF对应的映射资料与问题登记出口，不批准未决软件解释、不宣布冻结/READY_FOR_IMPLEMENTATION/SUPPORTED，也不批准后续阶段。

## 证据复用与变化复核

以首轮54来源SHA逐文件比较：50份字节未变，4份变更。五份原PDF、五份主映射、五份XLSX全部字节未变，故复用首轮47/47原页、23/23原表、24/24编号公式及824项位置独立对照证据。没有把本轮登记检查冒充重新视觉核验47页或重新执行824项。本轮没有必要重复运行未变化工作簿的数值核验。

完整对比见baseline_comparison.json；首轮证据绝对路径/哈希见reused_first_round_evidence.json。核心三件套绝对路径/哈希见core_artifact_manifest.json。

4份变更均为ISSUE_REGISTRATION_REQUEST.md追加“正式编号回链”：29541、19576、37479、21454。通过截取新增标题前正文、恢复原终止换行，所得字节SHA与首轮记录逐份完全一致，证明原正文没有潜在改写。新增全部文字及逐行diff保存在changed_file_semantics.json和各标准_semantic.diff；逐项阅读确认仅补登记映射，并明确旧“未登记”为历史、根台账唯一权威、登记不批准建议亦不关闭问题。

## 正式编号逐项对照

|标准|本地请求→根ID|核验|
|---|---|---|
|29541—2013|001/002/003/004/005 → EQP-STD-GB29541-001/002/003/004/005|5项一一对应，OPEN|
|19576—2019|R01/R02 → EQP-STD-GB19576-001/002|2项一一对应，OPEN|
|37479—2019|请求A/请求C/请求B → EQP-STD-GB37479-001/002/003|按A/C/B实际顺序，非误用A/B/C，OPEN|
|21454—2021|R1/R2/R3/R4 → EQP-STD-GB21454-001/002/003/004|4项一一对应，OPEN|
|19577—2024|既有EQP-STD-GB19577-001～006|6项仍OPEN，各问题块正文与既有round2根台账快照完全一致|

14项均检查：根台账标题只出现一次、版本对应、根→专属请求文件链接存在、专属本地键→稳定ID配对正确、专属→根路径可达、待决/未批准说明仍在。GB19577六项无重复新建、误关或擅批。机器检查见issue_links_check.json；其中19577采用标题边界抽取问题块，排除后续新章节标题，避免把新增其他设备章节误算作006正文改变。

人工语义核验：29541的静态10kW/低温静态/修约/外部试验/额定实测选组五项事实和候选意见保持；19576的日期公开证据及试验依赖保持；37479的5.1漏引表2、日期、试验/修约保持；21454的SEER冲突、精度、逐bin容量、外部引用保持。根台账新增条目没有把建议写成已批准软件决定。发现GB29541-001/002应转录原请求MISSING / AMBIGUITY、003 IMPLEMENTATION / REFERENCE、004 REFERENCE、005 AMBIGUITY，根台账均为待确认。已报协调修复，字段规范化为非阻断维护事项，49项登记事实覆盖不因此被否定。

## 未决解释与接入边界

OPEN不自动使Stage A资料验收失败；本轮确认的是疑点已被登记和完整保留。后续实际实现仍需按受影响分支处理原证据缺口：29541静态和选组、数值修约；19576/37479完整测试依据和37479最低限定值引用；21454多指标路由、修约、逐bin容量及测试依据；19577耗量方向/单位、组合指标、B点32.25/32.3、圆整、外部工况/压力/43℃及历史日期疑点。

首轮已注明的GB19577 A.13可通过测试获得CD的补充说明仍属非阻断提示。五项外部引用全文、完整季节重算、官方全文同一性与XLSX视觉排版未在本轮新增核验，不据本次PASS声称已覆盖。根台账日期延期条目仍OPEN，本轮不把公开事实交Owner投票，亦不修改Catalog。

## 当前环境与稳定性

实际HEAD d9f711068bde583138a7f3dded6f64dcaa339761，origin=https://github.com/adgo07/EquipEffi.git；共享分支不切换、不提交。locked central SHA ee5feb0cc34dbd99790500fadd0c4c932e202a20。本任务不涉及中央公共Contract。复用首轮中央ACTIVE在线blob一致性及业务仓fetch TLS失败的限制记录，不声称本轮刷新远端。适用MUST：原文和证据分层、疑点登记、变更定向复验；MUST NOT：静默批准解释、改源、升支持或Frozen锁。无新增LOCAL DEFECT/CENTRAL CONTRACT GAP。

稳定性见final_stability.json：54受验文件及锁文件稳定。根台账整文件因并发改动而变化，不声称全程SHA稳定；本组20问题块换行归一后的内容全部未变，末次快照立即重读SHA稳定，见root_scope_stability.json。末次根SHA `4989190f141d482dbb00c3fedb5c0ac2b52d8560e24ec4c66ccf02c36f1bc79e`。后续仅对五个类型字段和根SHA短复验，无需重跑未变全量数据。所有写入限于本目录。生产unittest/compileall/smoke/性能均not_run（无代码改变）；首轮数值检查824 pass原结果复用，不重新累计。Knowledge capture：无。

## 核心三件套固定清单

|绝对路径|SHA-256|
|---|---|
|`G:\Python Project\EquipEffi\标准原文\14. GB 29541 2013 热泵热水机（器）能效限定值及能效等级.pdf`|`94d5f6cc5502e76da01fc030a00d2acd54f40dd83cb967886149fb6b158e15df`|
|`G:\Python Project\EquipEffi\docs\standards\gb29541_2013\STANDARD_MAPPING.md`|`814934c48ebc7bd9b3e4fa3cf502fb32d811cc545acb3b44b446e43233c15c7f`|
|`G:\Python Project\EquipEffi\docs\standards\gb29541_2013\data\GB29541_2013_标准表值.xlsx`|`a7f92d9ab87aa90d44d80d72754d3ee1ce63266276d5ed06cdded9f4380e4b54`|
|`G:\Python Project\EquipEffi\标准原文\13. GB 19577-2024 热泵和冷水机组能效限定值及能效等级.pdf`|`809170a5c226d35c29a34dc73299c1589e6dc2acfdcb7b0241d0cbb00bfa58d9`|
|`G:\Python Project\EquipEffi\docs\standards\gb19577_2024\STANDARD_MAPPING.md`|`c8e891198f47315e9cac82d0ca869daa3f8df5ed394cd1c48e90ecd98a138c83`|
|`G:\Python Project\EquipEffi\docs\standards\gb19577_2024\data\GB19577_2024_TABLE_VALUES.xlsx`|`0ebf428916f51a8c1c462149ec4582e916e9cfbefcbfc39435077dcc8011633e`|
|`G:\Python Project\EquipEffi\标准原文\15. GB_37479-2019 风管送风式空调机组能效限定值及能效等级.pdf`|`cf4bef6fca2b88c5ed1a78006c0a6c411fa74330241e9b373c76d8684a338fde`|
|`G:\Python Project\EquipEffi\docs\standards\gb37479_2019\STANDARD_MAPPING.md`|`9e58abd111ccbbcb841b2197c18b90d6bca174a75845e3c4c20dc7d41d04cadf`|
|`G:\Python Project\EquipEffi\docs\standards\gb37479_2019\data\GB37479_2019_TABLE_VALUES.xlsx`|`e10747bf85ade8f062848c67db7261d0f6c25ec447b963535ff084223ecbfcb4`|
|`G:\Python Project\EquipEffi\标准原文\16. GB 19576_2019 单元式空气调节机能效限定值及能效等级.pdf`|`1c5c97fd39351ed9708fd69f45c9b37dfba8fccea3cc4f810b32de3522876026`|
|`G:\Python Project\EquipEffi\docs\standards\gb19576_2019\STANDARD_MAPPING.md`|`c63430b55aaa995ab5f22f5c3dc2280423d362939d63c9aeefd8650df160cd63`|
|`G:\Python Project\EquipEffi\docs\standards\gb19576_2019\data\GB19576_2019_TABLE1.xlsx`|`7ee299877c7ed5ab70f2b5c732a20df7056de7e6eec7e75eac9070c9d1df377d`|
|`G:\Python Project\EquipEffi\标准原文\17. GB 21454-2021 多联式空调（热泵）机组能效限定值及能效等级.pdf`|`ae091115094de6dcc2f587e35bd5a9389708fb37714804ef510ea831613a7331`|
|`G:\Python Project\EquipEffi\docs\standards\gb21454_2021\STANDARD_MAPPING.md`|`0134539630497ad3b20d17570857d6a3f49810695a4998d61ba64bd6869e1105`|
|`G:\Python Project\EquipEffi\docs\standards\gb21454_2021\data\GB21454_2021_标准表值.xlsx`|`7c85f6b7b7955e6c15df4fdbb012824b21dcc010d44b90067ed83556065efcc6`|


最终口径说明：此前将type字段分类遗漏标作CHANGES_REQUIRED属于过度门禁；事实/值/编号/OPEN/决定未变，现调整为映射事实通过并保留非阻断建议。原证据不变、验收者未改源。


末次统一短复验：根台账8类型字段已修复通过，最终SHA `670f9644cd8c9d428e1676c9620c6e7fc573a3ecb9959dac40994971f9b97908`；其他全文与已保存旧快照完全相同，49编号/回链/OPEN通过。见上级register_type_final_check.json。当前本组MAPPING_FACTS_PASS，前述类型维护待办现已完成；未改源、未重跑表值。
