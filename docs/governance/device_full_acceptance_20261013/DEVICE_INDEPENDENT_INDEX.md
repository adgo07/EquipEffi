# 设备类第三方独立验收与复验索引

## 当前最终复验状态（优先于下方批次历史）

15项128表均完成来源对照与变化语义核验。GB/T36561四项修复通过（恰好11格变化）；49项编号/回链/OPEN全核。**15项均为MAPPING_FACTS_PASS；49项登记覆盖通过。** 3标准的8个类型字段仅列非阻断维护建议，业务未决解释另列，不附加验收门禁。具体：[当前复验结论](reverification/FINAL_REVIEW_STATUS.md)、[完整15项资产清单](reverification/FORMAL_DELIVERABLES.md)、[263源文件SHA](reverification/final_source_manifest.json)、[8字段修复单](reverification/REGISTER_TYPE_FIX_REQUEST.md)。

范围外保全证据：[5资产原SHA检查](reverification/excluded_asset_preservation.json)；[泵候选说明](pump/查漏补缺候选_20261013/README.md)、[变压器不完整候选说明](transformer/查漏补缺候选_未完成/README.md)。候选均非正式交付，不重开原验收。

本索引建立于修复进行中，首轮历史不覆盖。正式范围按用户最新纠正为2026-10-13北京时间15个新编设备标准版本、128原文表；首轮实际17项/166表中，泵及变压器另作补充查漏附件；后续修复执行会话为01a135a1-ee12-7625-9a1e-82ff5f4cc023（Sol/medium请求配置），独立复验由原Astra/medium验收组执行。

**当前正式15项映射事实复验通过，8处登记类型字段为非阻断建议；泵/变压器不在本轮范围。** 首轮固定审计证据：[ACCEPTANCE_SUMMARY](ACCEPTANCE_SUMMARY.md)、[输入SHA](preflight_inventory.json)、[52项首轮结束稳定性](source_stability_end.json)、[修复交接](CONFIRMED_REPAIR_HANDOFF.md)。本索引机器可读数据：[independent_index.json](reverification/independent_index.json)。

表中映射/工作簿链接只定位受验资产的当前工作树路径，**不表示链接处正在变动的文件已经验收**。首轮接受或发现均绑定preflight_inventory及各组manifest中的旧SHA；修复后接受清单仅含GB/T36561 batch1三项目标及所绑定SHA。固定报告与旧SHA联合构成审计证据。收到修复执行报告及新文件SHA，捕获复验前后SHA并确认稳定后，才登记该批新结论。

|标准|映射路径（当前资产定位）|工作簿路径（当前资产定位）|首轮审计证据|复验状态|
|---|---|---|---|---|
|gb18613_2020|[STANDARD_MAPPING.md](../../standards/gb18613_2020/STANDARD_MAPPING.md)|[GB18613_2020_表1-6校对数据_A1.xlsx](../../standards/gb18613_2020/data/GB18613_2020_表1-6校对数据_A1.xlsx)|[首轮固定报告](motors/GB18613_2020_ACCEPTANCE.md)|MAPPING_FACTS_PASS|
|gb30254_2024|[STANDARD_MAPPING.md](../../standards/gb30254_2024/STANDARD_MAPPING.md)|[GB30254_2024_标准表值.xlsx](../../standards/gb30254_2024/data/GB30254_2024_标准表值.xlsx)|[首轮固定报告](motors/GB30254_2024_ACCEPTANCE.md)|MAPPING_FACTS_PASS|
|gb30253_2024|[STANDARD_MAPPING.md](../../standards/gb30253_2024/STANDARD_MAPPING.md)|[GB30253_2024_TABLE_VALUES.xlsx](../../standards/gb30253_2024/data/GB30253_2024_TABLE_VALUES.xlsx)|[首轮固定报告](motors/GB30253_2024_ACCEPTANCE.md)|MAPPING_FACTS_PASS|
|gb19153_2019|[STANDARD_MAPPING.md](../../standards/gb19153_2019/STANDARD_MAPPING.md)|[GB19153_2019_标准表值.xlsx](../../standards/gb19153_2019/data/GB19153_2019_标准表值.xlsx)|[首轮固定报告](compressor_boiler/ACCEPTANCE_REPORT.md)|MAPPING_FACTS_PASS|
|gb24500_2020|[STANDARD_MAPPING.md](../../standards/gb24500_2020/STANDARD_MAPPING.md)|[GB24500_2020_TABLE_VALUES.xlsx](../../standards/gb24500_2020/data/GB24500_2020_TABLE_VALUES.xlsx)|[首轮固定报告](compressor_boiler/ACCEPTANCE_REPORT.md)|MAPPING_FACTS_PASS|
|gb29541_2013|[STANDARD_MAPPING.md](../../standards/gb29541_2013/STANDARD_MAPPING.md)|[GB29541_2013_标准表值.xlsx](../standard_archive_20261024/gb29541_2013/data/GB29541_2013_标准表值.xlsx)|[首轮固定报告](hvac/ACCEPTANCE_REPORT.md)|MAPPING_FACTS_PASS|
|gb19761_2020|[STANDARD_MAPPING.md](../../standards/gb19761_2020/STANDARD_MAPPING.md)|[GB19761_2020_表1-4核对工作簿.xlsx](../../standards/gb19761_2020/data/GB19761_2020_表1-4核对工作簿.xlsx)|[首轮固定报告](fans_submersible/ACCEPTANCE_REPORT.md)|MAPPING_FACTS_PASS|
|gb28381_2012|[STANDARD_MAPPING.md](../../standards/gb28381_2012/STANDARD_MAPPING.md)|[GB28381_2012_TABLES.xlsx](../../standards/gb28381_2012/data/GB28381_2012_TABLES.xlsx)|[首轮固定报告](fans_submersible/ACCEPTANCE_REPORT.md)|MAPPING_FACTS_PASS|
|gb28381_2026|[STANDARD_MAPPING.md](../../standards/gb28381_2026/STANDARD_MAPPING.md)|[GB28381_2026_TABLE_VALUES.xlsx](../../standards/gb28381_2026/GB28381_2026_TABLE_VALUES.xlsx)|[首轮固定报告](fans_submersible/ACCEPTANCE_REPORT.md)|MAPPING_FACTS_PASS|
|gb32030_2022|[STANDARD_MAPPING.md](../../standards/gb32030_2022/STANDARD_MAPPING.md)|[GB32030_2022_表值映射.xlsx](../../standards/gb32030_2022/data/GB32030_2022_表值映射.xlsx)|[首轮固定报告](fans_submersible/ACCEPTANCE_REPORT.md)|MAPPING_FACTS_PASS|
|gbt36561_2018|[STANDARD_MAPPING.md](../../standards/gbt36561_2018/STANDARD_MAPPING.md)|[GBT36561_2018_TABLE_VALUES.xlsx](../../standards/gbt36561_2018/data/GBT36561_2018_TABLE_VALUES.xlsx)|[首轮固定报告](fans_submersible/ACCEPTANCE_REPORT.md)|MAPPING_FACTS_PASS|
|gb19577_2024|[STANDARD_MAPPING.md](../../standards/gb19577_2024/STANDARD_MAPPING.md)|[GB19577_2024_TABLE_VALUES.xlsx](../../standards/gb19577_2024/data/GB19577_2024_TABLE_VALUES.xlsx)|[首轮固定报告](hvac/ACCEPTANCE_REPORT.md)|MAPPING_FACTS_PASS|
|gb37479_2019|[STANDARD_MAPPING.md](../../standards/gb37479_2019/STANDARD_MAPPING.md)|[GB37479_2019_TABLE_VALUES.xlsx](../standard_archive_20261024/gb37479_2019/data/GB37479_2019_TABLE_VALUES.xlsx)|[首轮固定报告](hvac/ACCEPTANCE_REPORT.md)|MAPPING_FACTS_PASS|
|gb19576_2019|[STANDARD_MAPPING.md](../../standards/gb19576_2019/STANDARD_MAPPING.md)|[GB19576_2019_TABLE1.xlsx](../standard_archive_20261024/gb19576_2019/data/GB19576_2019_TABLE1.xlsx)|[首轮固定报告](hvac/ACCEPTANCE_REPORT.md)|MAPPING_FACTS_PASS|
|gb21454_2021|[STANDARD_MAPPING.md](../../standards/gb21454_2021/STANDARD_MAPPING.md)|[GB21454_2021_标准表值.xlsx](../../standards/gb21454_2021/data/GB21454_2021_标准表值.xlsx)|[首轮固定报告](hvac/ACCEPTANCE_REPORT.md)|MAPPING_FACTS_PASS|

## 批次历史（当前结论见页首）

|批次|范围|当前状态|接受的新SHA|
|---|---|---|---|
|GB/T36561 batch1|FS-36561-01/02/03：300mm、严格>φ300mm、1.0h及五层一致性|[定向PASS](reverification/gbt36561_batch1/REPORT.md)；FS04和全标准终局仍待复验|[开始/结束SHA](reverification/gbt36561_batch1/end_hashes.json)|
|48项既有请求|12标准根问题台账及回链|AWAITING_REPAIR_COMPLETION；逐项检查覆盖、版本、事实/判断/决定区分|未登记|

## 验收口径

- 映射事实验收检查原文忠实、范围/表值/公式/条件/脚注完整、来源定位与问题登记，不要求所有标准歧义都关闭。
- 已登记OPEN/DEFERRED单列为业务接入限制；不因这些状态自动判映射FAIL，也不因映射PASS批准解释、Numeric Profile、Golden或SUPPORTED。
- 泵/变压器退出正式验收及修复批次，原确认有效。额外查漏附件只作建议，已有候选不替换已确认版本；不安排重验，不阻断15项。
- 原PDF、业务代码/Canonical/Golden均不在修复权限扩展内。只读复验期间若相关文件SHA变化，结果记TEMPORARY_INPUT_CHANGED，不作为最终验收结论。
- 原官方题录与中央预检复用[OFFICIAL_METADATA](OFFICIAL_METADATA.md)、[PREFLIGHT_INVENTORY](PREFLIGHT_INVENTORY.md)，主标准核验不冒充全部外部引用全文与物理试验验证。

## 范围外补充查漏附件

[泵额外复查](pump/PUMP_ACCEPTANCE.md)、[变压器额外复查](transformer/ACCEPTANCE_REPORT.md)保留历史证据，原确认继续有效。其旧报告中的CHANGES_REQUIRED/NEEDS_COMPLETION仅描述此前扩展核查口径，**不适用于本轮正式15项验收，不重开原验收、不构成本轮必修**。各自原资产路径与旧SHA仍可由首轮清单追溯。



## GB/T36561 batch1历史交付

FS01/02/03定向通过，T6/T11共20记录交叉核验通过，首轮独立原图底稿对当前468值槽回归468/0。14:33:56—14:38:06 UTC所捕获922文件SHA全部稳定；不将辅助文件计数冒充业务数据量。报告绑定XLSX SHA `8178e66e9a40aaf1cddfd38c33344dce28dff0c73d5e1ed07a386c8700ff40d7` 等输入。该批当时FS04、48项登记未完成；现已按页首最终报告完成15项复验。后续新变化须按新SHA另验。


最后更新：8处非阻断类型字段已全部维护且短复验通过；49登记再次通过、其余根文本与旧完整快照完全相同。最终根SHA `670f9644cd8c9d428e1676c9620c6e7fc573a3ecb9959dac40994971f9b97908`。见[最后短复验](reverification/register_type_final_check.json)；此前“待维护”属于历史批次状态。15项当前结论MAPPING_FACTS_PASS。
