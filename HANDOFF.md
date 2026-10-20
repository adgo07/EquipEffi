# EquipEffi 当前交接

> 职责（M1 收口后）：本文件只放**很短的当前交接摘要 + 必要历史链接**。
> 长期硬规则见 `AGENTS.md`；当前状态（head / 任务 / blocker / next action）见 `TASK_STATE.md`；
> QA 项状态见 `QA_BACKLOG.md`；Profile 状态见 `V1_SCOPE.md` / `ROADMAP.md`。

## 当前状态

- 路线 `EquipEffi V2.3`；本任务起点为默认分支 `master` 的 `f12b5f29b306c769c0f0e56f5fe433fda7d75ba7`（PR #21 合并）；产品Phase状态见下。
- 已验收 Phase：`1 = PHASE_1_PASS`、`2 = PHASE_2_PASS`（PR #10）、`3 = PHASE_3_PASS`（PR #11）、`4 = PHASE_4_PASS`（PR #12）、`5 = PHASE_5_PASS`（PR #13）、`6 = PHASE_6_PASS`（PR #14）、`7 = PHASE_7_PASS`（PR #15）。
- **Phase 8（GB 19762 Excel 批量评价闭环）= `EXECUTION_COMPLETE` / `READY_FOR_INDEPENDENT_ACCEPTANCE`**（PR #16 已合并）。
  **不得**自行宣布 `PHASE_8_PASS`；不得进入 Phase 9。`automatic_continuation = DISABLED`。

## 当前任务

2026-10-19 Owner 授权的软件简化首批：核心结果/标准身份、统一 Excel 版本兼容、原文排除和交付资产检查。
隔离分支 `codex/simplification-integration-20261019`；[任务书](docs/governance/SIMPLIFICATION_IMPLEMENTATION_20261019.md)。
首轮结论因外部六项发现撤回；C/X/P 六项修复及身份来源/测试命名两项补充均已本地独立复验，当前 PR #24 的远端门禁与计数见 PR 检查和说明；[验收记录](docs/governance/SIMPLIFICATION_ACCEPTANCE_20261019.md)保留失败、退回及复验事实。不自动合并或发布。
源 checkout 的未提交标准映射资料保留，未纳入本批；此前[归档整理记录](docs/governance/STANDARD_ARCHIVE_ORGANIZATION_20261013.md)继续保留。
后续公共用例、页面骨架、旧路径退出、第二标准接入不属于本批已完成项。

## 长期关键事实（不随 Phase 变化）

- **正式发布用户表面 = PySide6 Qt Desktop**（无参数 / `--gui` / `--qt` 同一入口）；
  `--json` / `ApplicationApi` / `--web` / JSONL / legacy Tk / Android bridge / V4·Excel 是
  compatibility / development / future-adapter surfaces，差异逐项登记在 `QA_BACKLOG.md`。
- 发布门禁单一事实源：`application/services/pump_release_gate.py`；两条分析链都实际调用它。
- 统一类别路由必须使用**精确名称**映射，不得用“清水/化工/多级”等子串猜测。
- 历史 Record 冻结：Phase 3/4 期间形成的 chemical Record 其 `result_snapshot.support_status`
  仍为 `NOT_IN_RELEASE_SCOPE`，Reopen 不追溯改写、不重算。
- `as_of` 评价日期**不是业务门禁**（Owner，Phase 5；详见 `AGENTS.md` 2.7）。
- 18 条 `pump_water` golden-case-0.4 与 11 条 `pump_chemical` golden-case-0.5 为已批准业务真值，
  `evaluation_layer` 未改写。
- GB 20052—2024变压器后续功能开发以[主映射表 V2.1](docs/standards/gb20052_v21/GB20052_变压器主映射表_V2.1.md)和
  [表1～35人工校对数据工作簿 V2.1](docs/standards/gb20052_v21/GB20052_2024_变压器表1-35人工校对数据工作簿_V2.1.xlsx)为[已批准的一体冻结开发基准](docs/standards/gb20052_v21/GB20052_V21_FROZEN_BASELINE.md)，未经Owner再次批准不得修改；标准PDF仍是原文最高依据，D-08经Owner确认RESOLVED，变压器仍为`POST_V1 / NOT_IN_RELEASE_SCOPE`。

## 中央锁

`ee5feb0cc34dbd99790500fadd0c4c932e202a20` 不变；Architecture `V2.1 FROZEN` / Numeric `v1 FROZEN`，
其余 DRAFT；ACTIVE 指南按中央当前合并版读取。Numeric adoption PR #5 的独立验收记录仍为
`INDEPENDENT_ACCEPTANCE_RECORD_PENDING`，不以任何执行替代该证据。

## 历史与参考（只留链接）

- 已验收 Phase：`docs/phase3_acceptance_record.md` ～ `docs/phase7_acceptance_record.md`
- Phase 8 执行细节：`PHASE8_EXECUTION_REPORT.md`
- 长期操作参考：[docs/DEVELOPMENT_REFERENCE.md](docs/DEVELOPMENT_REFERENCE.md)
- 更早历史：[HANDOFF_20260831.md](HANDOFF_20260831.md)、[docs/governance/](docs/governance/)、
  `PUMP_V2_*_MANIFEST.md`、[QZC_N01_B_EXECUTION_REPORT.md](QZC_N01_B_EXECUTION_REPORT.md)、
  各 `PHASEn_EXECUTION_REPORT.md`

历史 Phase 1/2 审批不重复执行。普通维护改动只写**一份变更摘要**，不再要求多份长报告
（见 `AGENTS.md` 2.0 与 11）。`docs/planning/` 为既有未跟踪文件，未修改、未删除、未提交。
