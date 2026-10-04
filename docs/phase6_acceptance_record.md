# Phase 6 Acceptance Record

轻量验收落档：**只记录验收事实，不复制验收报告**。
格式沿用 `docs/phase3_acceptance_record.md` / `phase4_...` / `phase5_...`，
后续每个 Phase 沿用同一格式，不建立重治理流程。

| 字段 | 值 |
|---|---|
| phase | `Phase 6` — 完整 GB 19762 Product Shell |
| verdict | `PHASE_6_PASS` |
| acceptance date | 2026-10-04 |
| accepted head | `05b40f91086bbdbe196793075e440de4473cbf96` |
| PR | `#14` |
| merge SHA | `6ead21fb6757d5d92ba81851f23e3c41d86598af`（master） |
| independent acceptance 来源说明 | 见下 |

## independent acceptance 来源说明

**Phase 6 PASS 为产品负责人收到独立验收后作出的验收决定，不是执行者自行宣告 PASS。**

- 独立验收**第一轮**对 head `df7ba11b9a107e54eb737851263b9239ba8a593f` 提出
  3 个 blocker：① `QA-P5-001` / `QA-P5-002(b)` / `QA-P3-003` 三条入口语义 QA
  未真正关闭（以"存在 blocker"替代关闭）；② 标准库无条件硬编码显示
  「该标准尚未实施」（实际实施日期为 `2026-03-01`，当前已实施）；
  ③ 设置页把 `SettingsService.KEYS` 直接拼进 UI，普通用户看到
  `last.directory` / `window.geometry` / `window.state` / `log.level` 等内部机器键名，
  且正式 composition **从未**传入数据目录（此前只有测试手工注入 `data_location`，
  掩盖了未接线）。
- 执行者修复后形成 head `40b1e60`；该轮 CI 曾暴露一个 **CI-only 缺陷**
  （跨进程读取中文输出未指定编码，`charmap` 解码失败），已修正并记录。
- 独立验收**第二轮**对 head `40b1e60` 复验，又提出 3 项：① `analysis.py`
  把 `issue_codes` 直接展示给普通用户（实测显示 `提示：CATEGORY_UNCERTAIN`）；
  ② 统一服务的共享门禁**声明与代码不符**——`CentrifugalPumpAnalysisService._release_support`
  仍硬编码，未调用新增的 `pump_release_gate`，内存替换共享策略后两条路径分叉，
  执行报告与 QA 台账中"共同使用单一事实源"当时不成立；③ `TASK_STATE.md`
  仍写 `P6-G06: PARTIAL` 并把相关 QA 标为 `BLOCKER`，与关闭记录矛盾。
- 执行者逐项修复后形成 head `05b40f91086bbdbe196793075e440de4473cbf96`，
  该 head 的 Required CI 全绿（`Windows Core` / `Pump Conformance` /
  `Whitespace check` / `Full suite baseline`）。
- 产品负责人在收到独立验收结论后作出 `PHASE_6_PASS` 决定，并授权以 PR #14
  合并于 `6ead21fb6757d5d92ba81851f23e3c41d86598af`。
- 仓库内未另存独立验收报告正文，故以产品负责人验收决定 + PR #14 合并事实
  为记录来源。

## 说明

- 本 Record **不构成** Phase 6 执行报告的副本，也不替代
  `PHASE6_EXECUTION_REPORT.md`（其中含两轮 blocker 修复的完整记录）。
- `Phase 6 implementation = EXECUTION_COMPLETE`（执行状态）与
  `Phase 6 = PHASE_6_PASS`（独立验收结论）是两个维度，不得混用。
- **`PHASE_7_PASS` 尚未产生，不得提前书写。**
- Phase 6 遗留的已登记偏差**不因本次验收而全部关闭**：`QA-P6-001`
  （legacy Tk 保留但不接线，disposition Phase 8）与 `QA-P6-004`
  （非正式 adapter 未升级为正式 UI，disposition Phase 8 / 9）保持
  `REGISTERED_DEVIATION`；Phase 7 对 `QA-P6-003` 的重新判断见
  `QA_BACKLOG.md`。
- ADR-002 的完整 lineage / audit event 长期目标**继续有效但尚未实现**，
  登记为 `REGISTERED_DEVIATION`（见 `QA_BACKLOG.md` 的 `QA-P4-001`）；
  Phase 7 明确**不**实现正式 Reproduce / Attempt / 通用 Audit Framework。
