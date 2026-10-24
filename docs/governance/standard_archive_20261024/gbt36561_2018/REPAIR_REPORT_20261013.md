# GB/T 36561—2018 四项转录缺陷修复交接

2026-10-13。修复范围仅为本标准Stage A映射资产及其生成来源；不改正式Calculator、Canonical、Golden、其他标准或产品支持状态。此报告是执行记录，不是独立复验PASS。

## 原文依据及真实坐标

原PDF SHA256 `f1a6b29aa25d13b69f16006dd822e4ad2641830468bd6c395056e6751095ba37`。已直接查看独立验收保存的原PDF页图，证据见[确认发现](../../device_full_acceptance_20261013/fans_submersible/gbt36561_2018/CONFIRMED_FINDINGS.md)。

|编号|原PDF页|XLSX坐标|修复前→后|
|---|---|---|---|
|FS-36561-01|物理8/印5，表6注a|正文表值!H90|距主轴端面500 mm → 300 mm|
|FS-36561-02|物理8/印5，表6注b|正文表值!H91|直径≥φ300 mm → >φ300 mm|
|FS-36561-03|物理14/印11，表11井式炉950℃、0.2～1.0m³|正文表值!F294|≤1.5 h → ≤1.0 h；F293=1、F295=2保持|
|FS-36561-04|物理17/印14，表15两项各四等级|正文表值!H354:H361|静默写GB/T 30839.4 → 原表GB/T 30829.4，并注明与第2章/7.3/7.5冲突；实际采用口径仍待确认|

## 同源与范围核验

`build_data.py`已修源值；重新生成CSV、JSON、XLSX和坐标清单。`verify_assets.py`增加对应记录ID/真实单元格断言。逐项核对Excel、CSV、JSON、坐标清单一致；用验收时保存的旧工作簿全量值快照比较，只有上述11个单元格值改变。表6两行的0.3 mm阈值、表11相邻行F293/F295及表15分值均未改变。R11和根台账`EQP-STD-GBT36561-011`只登记原文内部冲突，不把任何猜测提升为正式解释。

本目录`verify_assets.py`：468/468坐标/值一致，42/42既有数值样本一致，29/29表覆盖，XLSX公式0；正式unittest/compileall/smoke/性能均NOT_RUN（无业务代码改动）。独立人员按新SHA复验仍待进行。

## 文件SHA256（原始字节）

|文件|修复前|修复后|
|---|---|---|
|`build_data.py`|`13fddc46795f0656668c90f0b5e506fe884502a0214bab6db3e993db708f2da2`|`eea27e16a4d78640f5c420ac119dafac126cf4787040f799b610fd8aa267e147`|
|`verify_assets.py`|`见首次交付清单；本次前后值以验收清单及当前本地哈希为准`|`5f29cb5a90a771c255d05b9602696dd2eb6410b3a5fb5cf5503b51b8a1285623`|
|`ISSUE_REGISTRATION_REQUEST.md`|`见首次交付清单；本次前后值以验收清单及当前本地哈希为准`|`272f5348f8d73d41f82757e50749d28cd2d19b880d93aa9373584468e4414852`|
|`README.md`|`见首次交付清单；本次前后值以验收清单及当前本地哈希为准`|`37efdb50af6c35e44497399e0824b6ecc427d57504a2d4d9a4025a1273609bef`|
|`HANDOFF.md`|`见首次交付清单；本次前后值以验收清单及当前本地哈希为准`|`29e7abdb5c93493feb1f1b55d5e755f9fccdf8410d74e91cb09b601a9382546b`|
|`data/table_values.csv`|`f3daad132955707b3153e2592134c57d3d62b53df2dfc5d506658fcba47a2fe9`|`666be11ae0de0fb1886b735f1e765f9e2038a26a938ce6e89f398f9188c14677`|
|`data/table_values.json`|`01048799230ae5316d7d3ebae78cefd640961778f61404e3e72821ab1e1d9031`|`83e614c64558436eacd6bf0aaeea5d042b865276bff2fc03ee0171dc258d7af6`|
|`data/GBT36561_2018_TABLE_VALUES.xlsx`|`284ceebe8b76f2b20cbbfe3ebb144e2abd4e85a6f598d6d389510e13f410af0a`|`8178e66e9a40aaf1cddfd38c33344dce28dff0c73d5e1ed07a386c8700ff40d7`|
|`evidence/workbook_coordinates.json`|`a27018fa98b85306f1af4e2f9e1c474b688ea2bcee7a33026a913c18b3fbc1f7`|`55bb7ca7867e1025c18f74f55b9c8eaceb9e2766a639075d16fb2e48aa5d8006`|
|`evidence/check_results.json`|`见首次交付清单；本次前后值以验收清单及当前本地哈希为准`|`1dea0fab5e13cba336e915020a260d2ff7f308b317d9ce72fb615dfc6606a508`|
