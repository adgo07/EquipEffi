# 已完成：8处登记类型字段非阻断维护建议

范围仅根 `STANDARD_ISSUES_REGISTER.md` 的字段整理，验收者未修改来源。49项编号/双向回链/OPEN均核验；下列字段漏转或混入定位，不是标准数值错误，不需改变业务解释，不得借修字段关闭问题。

|稳定编号|当前问题类型|应忠实转录类型|原请求依据|
|---|---|---|---|
|EQP-STD-GB30253-001|待确认|TYPO / CONFLICT|docs/standards/gb30253_2024/ISSUE_REGISTRATION_REQUEST.md:7，原建议类型|
|EQP-STD-GB24500-001|待确认|IMPLEMENTATION / AMBIGUITY|docs/standards/gb24500_2020/ISSUE_REGISTRATION_REQUEST.md，请求A|
|EQP-STD-GB24500-002|REFERENCE / IMPLEMENTATION 后混入“标准同上；定位：第4章，印刷1/PDF3”|REFERENCE / IMPLEMENTATION|同上请求B；定位内容归入标准原文事实/定位，信息保留|
|EQP-STD-GB29541-001|待确认|MISSING / AMBIGUITY|docs/standards/gb29541_2013/ISSUE_REGISTRATION_REQUEST.md，001|
|EQP-STD-GB29541-002|待确认|MISSING / AMBIGUITY|同上002|
|EQP-STD-GB29541-003|待确认|IMPLEMENTATION / REFERENCE|同上003|
|EQP-STD-GB29541-004|待确认|REFERENCE|同上004|
|EQP-STD-GB29541-005|待确认|AMBIGUITY|同上005主类型|

按稳定编号定位，不依赖修复时可能变化的行号。仅修8个类型字段，锅炉002定位移入正确字段；其余事实、判断、待决建议、编号、版本与OPEN状态保留。原“待确认”如需保留，可表达确认程度但不能充当类型代码。

修后最低复验：8类型逐条值检查；49项编号唯一/回链完整/状态仍OPEN；根文件修前后差异仅上述范围；前后SHA稳定。业务原PDF/映射/工作簿的全量复验不因这个元数据修订重复执行。当前15项映射事实结论为 `MAPPING_FACTS_PASS`；8项字段规范化不阻断该结论，不要求新增审批或流程。


最终状态：8/8已维护并独立短复验PASS；49登记保持OPEN，其他根文本与旧完整快照完全相同。见register_type_final_check.json；本文件表格保留修复前历史。
