# 软件简化首批独立验收（2026-10-19～20）

> 2026-10-20 外部复验发现六项缺口，主会话已独立确认并撤回下方首轮通过结论。下方测试数字保留为历史事实；本地 R1 复验已完成，见文末；最终远端门禁状态以 PR #24 对当前 Head 的检查为准。

范围：按 Owner 授权验收 C / X / P 三条执行线，并准备提交 PR；不是整个软件简化计划完成，也不是 Phase 8 独立验收或正式发布。执行由 gpt-6-luna / max 子会话完成，设计与验收由主会话完成。

## 平台预检查与边界

- 仓库：adgo07/EquipEffi，默认 master；基线 `2c7807f32ef08d18554014328efd4ceaa356726f`。
- 最终运行代码固定于 `39eaf1d29cf4d082dee812dd8fce649355cf9c36`；其后仅测试、QA、治理和本验收证据更新。最终完整套件代码与测试 SHA：`265a808d8bc8d922c87a876cf9f7bf4916e6e151`。
- Frozen central SHA：`ee5feb0cc34dbd99790500fadd0c4c932e202a20`；Architecture V2.1 / Numeric v1 按锁读取。ACTIVE 指南按中央 `c5fc6d438c9200060649e47c016b9b48218de72c` 的 GUIDE_INDEX 路由读取。
- 适用 MUST / MUST NOT：Domain 不依赖 UI/Excel/SQLite；Qt/Excel 通过 Application；Excel 不复制业务算法；不改变 Pump Decimal50/全值比较；不升级 Frozen；不追溯改写历史快照；系统失败不能伪装为合法业务终态。
- 分类：本次修复为 LOCAL DEFECT；Pump Decimal50 保留为 ALLOWED PROJECT DIFFERENCE；历史非正式表面差异继续按 QA 台账登记。无 CENTRAL CONTRACT GAP，不需修改中央 Contract。
- Standard Issue：检查现有台账，本批不新增或变更标准解释。用户明确批准结果显示用语，底层状态、记录资格与已批准业务真值不变。
- 源 checkout 的未提交映射资料未纳入；Canonical、Approved Golden、变压器冻结双文件、原始 V6 Workbook、锁文件均无修改。无数据库 migration、支持状态提升或 Phase 推进。

## 首轮退回与闭环

| 问题 | 修复 | 独立验证 |
|---|---|---|
| C 将输入/系统错误合并显示为无法判定 | 输入错误、执行失败分别显示；资料不足/不确定类别仍无法判定 | 19 项 C 回归，覆盖 live/snapshot/实际 Qt/批次 Workbook，全部通过 |
| X 将 data_version 当标准版本、rule_profile 当规则集版本，混合批次只记首个 Profile | 标准号/年份、数据版本、实际 Profile 集合分开；未提供的独立版本明确 null | 实际包引用、混合清水/化工批次回归及模板输入字段/单位 Gate |
| P 未随包声明 X 新的 TEMPLATE_MANIFEST.json | wheel/sdist 与必需资源检查加入清单；增强实际导入烟测 | 本会话四类实际构建产物审计和三类隔离导入通过 |

问题归档沿用 QA-SIMP-C-001、QA-SIMP-X-001、QA-SIMP-P-001，不另造长期状态台账。

## 验证记录

环境：Windows，CPython 3.12.14，PySide6 6.11.2，Qt offscreen。测试夹具使用本会话实际构建的 wheel，放入既有测试指定的两个本地临时路径；没有修改测试基线或放宽断言。

| 检查 | 结果与范围 |
|---|---|
| 首轮核心/Excel/架构定向集成 | 207 pass / 0 fail / 0 error / 0 skip；包括 100、1,000、10,000 行读入容量 |
| Pump Conformance 对应 18 个 unittest 模块 | 196 pass / 0 fail / 0 error / 0 skip，含已批准 Golden、边界、历史与 Finalize 资格 |
| C 退回修复后定向 | 19 pass / 0 fail / 0 error / 0 skip |
| 最终架构边界与元数据 | 113 pass / 0 fail / 0 error / 0 skip |
| QZC N01-B pilot | 25 cases，errors=0；阈值 T−δ / T / T+δ = 2级 / 1级 / 1级，epsilon=false |
| Phase 1 契约负探针及候选校验 | exit 0；使用 --skip-external-evidence，18 项外部原件证据未核查，不能据此声称标准原文全面复核 |
| 正式模板机械一致性 | GATE PASS；输入 field_id/单位、输出 metric ID/单位及模板身份结构一致 |
| 未处理 Sheet | 17 个 Sheet，0 diffs，GATE PASS |
| 实际构建与资产审计 | wheel / sdist / zipapp / portable ZIP 均有效，缺失资源 0，标准源文件发现 0 |
| 产物隔离导入 | wheel / zipapp / portable 内嵌 wheel 均 artifact-v6-ok；使用 -I -S，禁止源码回退 |
| compileall、--status、--list-device-types | exit 0；CLI 为 compatibility smoke，不代表其他 Profile 已正式支持 |
| 全量 unittest + exact-ID 比较 | 10 月 19 日因会话中断未完成，不计为 PASS；10 月 20 日重跑 1,565 项：1,562 pass / 3 fail / 0 error / 0 skip，737.431 秒；exact-ID Gate PASS，无新增回归 |
| 原生 PyInstaller 可执行文件 | NOT_RUN：环境没有 PyInstaller；现有构建器定向单测覆盖资源声明，但不能替代真实原生包验收 |

第一次打包定向测试为 32 run / 31 pass / 1 error（既有 wheel 固定路径夹具缺失，KeyError wheel_pmsm_status，属现有基线 ID）。实际构建 wheel 后提供该夹具，再由最终全量套件复核；没有隐藏第一次结果。

本地详细证据在集成工作树 artifacts 下保留；压缩后的机器可读验收摘要随文档提交。资源基线见 BASELINE.md。

全量首轮还发现四个历史测试模块仍使用旧显示标签或缺少标准身份的旧指纹预期。修订不得改变 Approved Golden，旧快照无参拒绝猜测、显式旧键重放及 Finalize 保护须继续有独立回归覆盖。

## 首轮结论（已撤回，保留历史）

首批独立验收通过，可提交 PR 供审阅；不直接合并或正式发布。全量测试不是全部通过：3 项失败均为既有 V4 Reader/Writer 基线 ID，详见[机器可读证据](SIMPLIFICATION_ACCEPTANCE_20261019.json)，未修改允许名单。100/1,000/10,000 行分别为 3.432/23.411/229.849 秒，采样峰值 22.2/108.7/1000.6 MiB；这是带 tracemalloc 的功能测试，不能作为正常运行性能承诺。

本批不宣告 PHASE_8_PASS；公共 Application 用例/页面骨架、旧路径退出、变压器接入等后续工作包仍未完成。

## 外部复验修复 R1（2026-10-20，本地复验完成）

六项发现：Excel 结果区域冲突合并；首页未接入共享用语；计算器指纹漏掉判级依赖；必需标准数据缺失误归输入错误；报告路径绕过 PDF 排除；Windows 路径别名导致故障注入未触发。C/X/P 各自先登记再修复，固定新 Head 复验。

远端旧 Head 的 Windows Core 为 1,565 run / 1,548 pass / 10 fail / 4 error / 3 skip，精确 ID 比较有 1 项新增失败；后续 Package and resource smoke 被跳过。它与本地 3.12.14 的数字分别记录，不能相互替代。


运行代码 SHA：`34259c0`；缓存测试兼容修订后代码与测试 SHA：`3a30b5700f9a1c221c10700ce7d056e72d97b637`。后续本提交仅整理治理记录。平台预检查沿用上文：不涉及中央公共 Contract 变更，未改变锁定基线或标准解释。

| 外部发现 | 修复与独立核查 |
|---|---|
| Excel 合并结果单元格导致数值丢失 | 读入时拒绝覆盖输入/结果列的数据区合并；无 Table、缩表后第 5 行及扩表第 150 行仍可读；结果 Workbook 重开限值完整 |
| 首页历史用语未统一 | 复用快照投影，显示 1级/2级/3级、未达3级、不在范围；不改写历史记录 |
| 计算器指纹缺依赖 | 静态清单纳入判级、数值、区间查表、结果投影与发布门禁；指纹单测校验实际源码，无运行时扫描 |
| 必需标准表缺失被当成输入问题 | 活动清水/化工泵按 Profile 校验结构，失败抛 StandardPackError；同源文件按 Profile 分别缓存校验 |
| 报告目录可绕过 PDF 排除 | 安装产物内实际 PDF 一律拒绝，不按文件名或路径豁免；用户运行时输出报告不属于安装资产 |
| Windows 路径别名使异常注入失效 | 注入比较使用 resolve，并断言故障确实被注入；未跳过测试或放宽基线 |

主会话独立验证：

- X/P 相关 96 项：96 pass / 0 fail / 0 error / 0 skip。
- C、Golden、历史和架构共 217 项：首轮 216 pass / 1 fail / 0 error / 0 skip。唯一失败是旧 M3 测试要求共享文件只校验一次；退回 C 线修订为各 Profile 首次一次、重复访问零次，完整 M3 模块复跑 12 pass / 0 fail / 0 error / 0 skip。其余代码未再改动，未修改业务 Golden 或回归允许名单。
- compileall 通过；模板机械一致性 GATE PASS；17 个未处理 Sheet 为 0 diffs。
- 最终运行代码构建 wheel / sdist / zipapp / portable ZIP，四类实际产物各 18 项运行资产、0 缺失、0 标准原文/PDF 发现；便携 ZIP 完整性通过。
- wheel / zipapp / 便携 ZIP 内嵌 wheel 三类 `-I -S` 隔离导入通过，确认 V6 模板有效、空白输入 0 行、计算器版本为最终指纹。PyInstaller 原生构建 NOT_RUN（环境未安装），不据此宣称原生安装包验收。
- 本轮本地不重复运行耗时全量/万行测试；由 PR 当前 Head 的 Windows Core 全量套件和 Pump Conformance 完成远端复核。提交此记录时远端新一轮尚未运行，不能提前记为 PASS；实际 run、计数和结论更新到 PR #24 说明。

本地六项修复复验通过，QA-SIMP-C/X/P-002 收口；PR 仍须通过远端无新增回归门禁，不自动合并、不发布、不宣布 PHASE_8_PASS。首轮撤回事实与旧 CI 失败记录保留。


## 本地补充意见 R2（2026-10-20）

Owner 授权采纳本地意见的两项补充，QA-SIMP-X-003。运行代码与测试 SHA：`7fd740b916c19da395400286fa2fe25f04a8449b`；本节后续提交仅整理证据。本任务不涉及中央公共 Contract；locked SHA 仍为 `ee5feb0cc34dbd99790500fadd0c4c932e202a20`。沿用上文平台 MUST/MUST NOT，分类 LOCAL DEFECT，无新增 Standard Issue，不改变标准解释。

- Reader 把实际识别的 `identity_source` 传至 `batch_record.summary.template`，区分 `declared` 与 `legacy-structure`；输入没有证据时为空，即使默认模板声称 `declared` 也不回退。保留历史快照，不增加数据库字段或迁移。
- 数量非法值回归的输出文件名改用确定性序号，消除随机 hash 取模碰撞，业务断言不变。
- 主会话独立运行 Reader、批次、Phase 8 R1、架构与元数据共 **228 run / 228 pass / 0 fail / 0 error / 0 skip**，213.440 秒；包含实际 SQLite 批次快照、两种来源及无来源防伪、Table 缺失/扩缩兼容。compileall 与 git diff --check 通过。
- 子会话另验证模板 Gate 39/39；未改模板资产、Canonical、Approved Golden、冻结文件、锁或持久化 schema。本轮不重复构建未受影响的分发资产；R1 产物审计保留原 SHA 适用范围。
- 本地补充复验通过；当前最终 Head 的 CI 结论及 run 继续以 PR #24 说明和检查为准，未运行前不提前宣称通过。不合并、不发布、不宣布 Phase 8 PASS。原本地验收草稿保持原位，不改写其历史结论。
