# 压缩机/锅炉最终复验

2026-10-13；范围：GB 19153—2019、GB 24500—2020 Stage A资料。只写本目录，未修改受验资料/台账/生产资产，未提交。

## 结论

**两标准数值、结构与映射事实复验通过；首轮“疑点未登记”待办已完成。** 六项请求均有唯一稳定编号与双向回链，仍为OPEN；登记没有批准解释，也没有关闭问题。OPEN本身不阻断Stage A映射事实验收。锅炉两项台账的问题类型字段存在规范化待办（下述），不构成表值或业务解释失败。

本结论不提升SUPPORTED或READY_FOR_IMPLEMENTATION，不替代Stage B/C/D，不宣布Phase PASS。试验引用全文及未决实现口径继续按首轮报告所列范围限制保留。

## 前置与证据复用

实际根目录 `G:\Python Project\EquipEffi`；origin=`https://github.com/adgo07/EquipEffi.git`，HEAD=`d9f711068bde583138a7f3dded6f64dcaa339761`。共享分支/远端新鲜度及中央指南证据沿用总协调本轮预检查；未切换分支。本任务不涉及中央公共 Contract；locked SHA=`ee5feb0cc34dbd99790500fadd0c4c932e202a20`不变。必须保持原文事实、判断、软件决定分开；不得通过登记自动批准解释或改业务资产。冲突分类：无中央契约冲突，无需改中央。

首轮证据为本目录上两级的[完整验收报告](../../compressor_boiler/ACCEPTANCE_REPORT.md)、[全量逐格CSV](../../compressor_boiler/independent_cells.csv)、[计数JSON](../../compressor_boiler/independent_summary.json)和[source_manifest](../../compressor_boiler/source_manifest.json)。它们的绝对路径及本轮SHA见 `reverification_manifest.json`，不冒充重新看图或重新跑全量表值。

原PDF18+6页、全部表值/公式/范围/单位/53项边界候选的首轮证据有效：压缩机2,502数值+417横杠+6比例；锅炉78表值+97%限定值，共3,004位置无差异。本轮没有业务源变更，不重复执行相同核验。官方题录见[OFFICIAL_METADATA](../../OFFICIAL_METADATA.md)，两项均现行，仅为题录证据，不证明官方全文与本地PDF同一性。

已阅读 `docs/standards/gbt36561_2018/REPAIR_REPORT_20261013.md`，其四项修复属于其他标准，本组19项受验清单除登记回链外未受影响；本报告不验收或转授该修复结果。

## SHA差异与定向验证

`manifest_comparison.json`覆盖首轮19项：17项字节完全一致，2项改变。两原PDF、两主映射、两XLSX、全部候选及原证据文档均未变。清单中每项有来源绝对路径、首轮SHA、当前SHA与一致标记。

|变化文件|首轮SHA|当前SHA|语义差异与验证|
|---|---|---|---|
|gb19153_2019/ISSUE_REGISTRATION_REQUEST.md|e63171d461fe6d08ff655c98726fc378fda354ee4348de0ff46b789e26da0ffa|3952456cddde101fc67f04a251b9f8fc68b0086de4cff31cc53a80a547344543|换行变化+末尾正式编号回链；截去新增章节、统一LF及原末尾换行后，重建SHA等于首轮SHA，证明旧正文无语义修改。|
|gb24500_2020/ISSUE_REGISTRATION_REQUEST.md|fbeef4ae280bd738476d421a0841eefb7aa5b7dc41af9be1263bffc3f633beb4|051b806a6d0c6b5589bc891e06b78075f4978f5771409d2e06a9b16895dde6b8|同上；旧正文没有删除或改写，新增章节解释旧“尚未登记”为历史时点。|

完整新增文字及重建哈希证据见 `append_only_diff.json`。没有数字、边界、公式、单位、物理分支或候选预期的变化，故无需重新渲染原PDF或重跑值核验。

## 六请求逐项治理核验

|本地请求|正式稳定ID|对应事实|核验结果|
|---|---|---|---|
|R01|EQP-STD-GB19153-001|非表列点/冷却/缺指标|唯一标题、根→专属和专属→根回链、OPEN、建议未批准，全部符合|
|R02|EQP-STD-GB19153-002|大一档依据|同上|
|R03|EQP-STD-GB19153-003|变转速e与q配对|同上|
|R04|EQP-STD-GB19153-004|部分负荷±5%|同上|
|请求A|EQP-STD-GB24500-001|特殊限定值/等级组合|同上；类型字段待规范化|
|请求B|EQP-STD-GB24500-002|初始排放前提|同上；类型字段待规范化|

逐项读根台账正文并对照专属请求：六项均保留来源/技术判断/待决建议，没有改写为正式软件决定；六个ID标题各出现一次，没有重复分配。本地请求键“请求 A”与回链“请求A”的空格差异不改变身份。压缩机类型MISSING/TERM/AMBIGUITY/AMBIGUITY与请求一致。

锅炉字段规范化待办已报总协调，未自行修：

- GB24500-001根台账类型是“待确认”，专属请求已有IMPLEMENTATION / AMBIGUITY，应保留已知分类；不需Owner另批业务解释才能规范化。
- GB24500-002类型字段含`REFERENCE / IMPLEMENTATION`后串入“标准同上；定位：第4章，印刷1/PDF3。”，建议分回定位字段。实际事实/来源和OPEN状态可追溯，没有业务误判。

根台账快照SHA、各项机器核验布尔结果见 `reverification_manifest.json`。本轮未将六项未决解释判为已解决。后续接入需要的外部试验/档位/工况/组合/排放依据继续由各稳定ID承载；它们不自动阻断本次已完整保存原文事实的Stage A验收。

## 稳定性与未执行项

本组19受验文件开始/结束SHA稳定结果见 `final_stability.json`；根台账作为共享文件另记其前后SHA，不把他人合法修改混为本组源变化。完整源清单不依赖固定跨机器盘符，绝对路径仅记录本次环境。

生产unittest/compileall/smoke/性能：NOT_RUN；全量数值重跑：NOT_RUN（17项完全不变，复用首轮PASS）；两变更文件原正文重建哈希核验：2/2 PASS；问题唯一编号/回链/OPEN/未批准检查：6/6 PASS。没有源资产修复。Knowledge capture：无。


末次统一短复验：根台账8类型字段已修复通过，最终SHA `670f9644cd8c9d428e1676c9620c6e7fc573a3ecb9959dac40994971f9b97908`；其他全文与已保存旧快照完全相同，49编号/回链/OPEN通过。见上级register_type_final_check.json。当前本组MAPPING_FACTS_PASS，前述类型维护待办现已完成；未改源、未重跑表值。
