# GB/T 36561—2018 首三项修复独立复验（batch1）

结论：FS-36561-01、02、03 本批定向复验通过。仅此三项，不构成全标准、全组或 Stage A 终局 PASS；FS-36561-04 不在本批结论内，待修复最终材料后另验。首轮报告保留原样。

平台预检查沿用父报告：EquipEffi HEAD d9f711068bde583138a7f3dded6f64dcaa339761，locked central SHA ee5feb0cc34dbd99790500fadd0c4c932e202a20。origin 已核验，业务仓 fetch TLS 失败；中央 ACTIVE 指南在线一致性由父报告确认。本任务不涉及中央公共 Contract，无需升级；不改解释、不改生产代码、不重存工作簿、不提交。

## 原图与定向复验

本轮重新实际查看首轮由同一原 PDF 渲染的 table6_note_zoom.png 和 table11_zoom.png。PDF SHA256 为 f1a6b29aa25d13b69f16006dd822e4ad2641830468bd6c395056e6751095ba37，首尾未变；绝对来源路径见 start_hashes.json。原图位于 ../../fans_submersible/gbt36561_2018/。

| 问题 | PDF 原文 | 工作簿坐标 | 本批结果 |
|---|---|---|---|
| FS-36561-01 | 物理8/印刷5，表6注a，距主轴端面300 mm | 正文表值!H90；T6-0089 | 已为300 mm，XLSX/CSV/JSON/坐标证据/构建源一致 |
| FS-36561-02 | 同页注b，直径>φ300 mm，半径150 mm | 正文表值!H91；T6-0090 | 已为严格大于，五层一致 |
| FS-36561-03 | 物理14/印刷11，表11，井式炉950℃，容积0.2～1.0m³，空炉升温时间≤1.0h | 正文表值!F294；T11-0293 | 值1，运算符≤、单位h，五层一致 |

构建源采用只读 AST 字面量/文本检查，未执行生成器。表6及表11全部20条记录的 JSON、CSV、坐标证据各字段以及工作簿值/条件一致，0失败。另以首轮独立原图人工读值底稿对当前工作簿全部468个值槽做数值回归：468通过、0失败；此回归不等于重新完成468次读图，也不评价FS04文本引用。

生产证据 SHA256SUMS.json 所列现存文件校验全部通过；check_results.json声明468坐标值一致，其自核仍明确 independent_review=NOT_RUN。numeric_review.csv 未含本批三个目标坐标，不能用其42项抽核替代本次独立复验；本批具体证据由 checks.json 和本报告承担，不将该抽核缺口误称为数据错。

## 输入稳定性

开始：2026-10-13T14:33:56.329098+00:00；结束：2026-10-13T14:38:06.051482+00:00。开始清单内全部文件结束重算，无变化（hash_changes.json为空）。清单包含标准目录递归文件及原PDF，node_modules等辅助文件也被保守纳入；本批直接依赖如下，完整绝对路径与SHA见 start_hashes.json/end_hashes.json。未检测新文件创建；本批结论仅约束所列已验文件，不冻结仍在进行的其他修复。

| 本批输入 | SHA256 |
|---|---|
| build_data.py | `eea27e16a4d78640f5c420ac119dafac126cf4787040f799b610fd8aa267e147` |
| build_workbook.mjs | `edfd1216d7927a47ceb4639446517de06ae66a2b2033ec9fd63cef2c89245186` |
| data/GBT36561_2018_TABLE_VALUES.xlsx | `8178e66e9a40aaf1cddfd38c33344dce28dff0c73d5e1ed07a386c8700ff40d7` |
| data/table_values.csv | `666be11ae0de0fb1886b735f1e765f9e2038a26a938ce6e89f398f9188c14677` |
| data/table_values.json | `83e614c64558436eacd6bf0aaeea5d042b865276bff2fc03ee0171dc258d7af6` |
| evidence/workbook_coordinates.json | `55bb7ca7867e1025c18f74f55b9c8eaceb9e2766a639075d16fb2e48aa5d8006` |
| evidence/check_results.json | `59f995657eeaf352739015be9021225937b75826cd313d700f5a0e4af6d56c43` |
| evidence/numeric_review.csv | `8deaf3319798f84f2655a69abfb0844dd1840ad6d9fb87b65db39339e6c30e16` |
| evidence/SHA256SUMS.json | `f214cff05b416ac5bf88b6118f4e38f2b8ad9e80a684e975cbcd5a258cd480ac` |

复验产物：checks.json（逐问题与20记录交叉检查）、numeric_regression.json（468槽）、verify_batch1.py（可复现只读脚本）、start_hashes.json、end_hashes.json、hash_changes.json。软件unittest/compileall/smoke/性能为NOT_RUN，原因是只读文档复验，无生产改动。首轮缺陷状态可由父按本批证据更新；本报告不自行关闭根台账，也不批准未决标准解释。
