# EquipEffi 当前路线

## 权威状态

- **Current Roadmap:** EquipEffi V2.2
- **路线原文:** [docs/28_EquipEffi 后续开发总体路线 V2.2.md](docs/28_EquipEffi%20后续开发总体路线%20V2.2.md)
- **Current Phase:** Phase 1
- **State:** `BLOCKED`
- **Next State:** `REVIEW_BLOCKER_RESOLUTION`
- **Automatic continuation:** `DISABLED`
- **Allowed Work:** 仅 Golden Case 批准阻塞收口和 Solution/Product Review 输入；不得启动 Phase 2；Phase 0B/Phase 1 Hotfix 均未执行

## 治理切换

V2.2 已取代旧 v15 / T04.xx 路线。旧路线、旧 HANDOFF、编号执行清单和历史测试数字仍保留事实价值，但统一标记为：

```text
HISTORICAL
NOT AUTHORITATIVE FOR NEXT TASK
```

下一任务必须只从以下权威入口读取：

```text
ROADMAP.md
HANDOFF.md
TASK_STATE.md
AGENTS.md
BASELINE.md
ASSET_AUDIT.md
QA_BACKLOG.md
V1_SCOPE.md
ADR/
```

## Phase 0 结论

Phase 0A 的治理切换、不可变起始 tag、真实基线、资产审计、第三方 55 项入库、风险重新分级、17 Profile 注册、Windows V1 Scope 草案、Golden Candidate 盘点和首个纵向样板选择已完成。2026-09-22 验收曾因交付物未提交、证据字段不完整、QA 表结构不统一和产品需求/商业价值证据缺失而暂时阻塞；治理补正和复验已完成，未修改业务代码。

当前唯一合法下一步是：

> **Solution/Product Review：审查 Phase 1 业务规范、数据契约、`pump_water` 映射、Golden Case、P0 证据和 Windows V1 Scope。**

Phase 1 只允许建立业务规范 V0.1、Canonical Schema、Product/Profile Schema、Import Contract、Golden Case Schema、Support Status 和 `pump_water` 样板的标准映射；不得批量迁移 17 个 Profile。

## Phase 1 当前执行

Phase 1 按 `docs/29_Phase 1 业务规范与数据契约.md` 的既定顺序执行：

```text
P1-G01 → P1-G02 → P1-G03 → P1-G04 → P1-G05 → P1-G06
```

`P1-G01` 已形成业务规范草案，`P1-G02` 已形成契约 Schema，`P1-G03` 已形成 `pump_water` / GB 19762-2025 映射，`P1-G04` 已形成并通过增强验证的 7 个首批 Golden Case，但正式批准字段仍待具名标准复核负责人，`P1-G05` 已对四项 Phase 1 P0 风险完成证据复核且未执行 Hotfix，`P1-G06` 已形成 Python/版本语义/Windows V1 Scope 评审包。验收 HEAD `df9f53e468d49ac7d9c6419fe89fb99c25d9f30c` 的 CPython 3.12.14 x64 门禁已复验；王玮（总经理）已于 2026-09-23 记录 Windows V1 产品决策。当前状态为 `BLOCKED`，唯一阻塞是 Golden Case 批准授权缺失；不得声明 Phase 1 PASS 或启动 Phase 2。已知 Legacy Regression 失败必须原样保留并显式记录。

## Phase 1 Review Boundary

Phase 1 的唯一合法下一步是补齐 Golden Case 的具名标准复核负责人和批准记录，再提交 Solution/Product Review。本次独立复算和来源验证只能证明技术证据充分，不能替代正式批准。任何评审前的代码重构、目录搬迁、完整 UI/SQLite/Excel/报告和批量 Profile 迁移均越界。

## Phase 0 Exit Gate

| Gate | result | evidence |
|---|---|---|
| Governance | PASS | V2.2 权威入口、旧路线失去调度权、Phase 0 状态和可复现治理提交 |
| Baseline | PASS | `BASELINE.md`、`pre-v2-rebaseline`、真实 unittest/compile/package/smoke/performance |
| Assets | PASS | `ASSET_AUDIT.md`；运行链、双实现、空壳和 release surface 已登记 |
| QA | PASS（开放项已入库） | `QA_BACKLOG.md`；第三方 55 项、历史路线和当前失败均有 ID |
| Metadata | PASS | Canonical / Product Schema / Import Contract / Ruleset / UI Metadata 边界 |
| Scope | PASS（Phase 1 冻结前为草案） | `V1_SCOPE.md`；17 Profile、Support Status 草案，以及用户需求/商业价值的显式证据状态 |
| Vertical Slice | PASS | `pump_water` 已与 3 个替代候选比较并记录风险/必须证明项 |
| Phase 0B | N/A | 没有满足条件的 Hotfix 被批准；无额外重构混入 |

因此 Phase 0 保持 `PHASE_0_PASS`，Phase 1 当前状态为 `BLOCKED`。Windows V1 的产品决策已记录，但 7 个 Golden Case 尚未完成正式批准，不授权进入 Phase 2。

## Phase 0 保护边界

- 默认不重构、不扩功能、不批量修改 evaluator。
- 只保留当前正式运行链；兼容层和空壳先标记，不在 Phase 0 大规模删除。
- `Legacy Regression` 保护旧行为；`Approved Golden Case` 才保护业务真相。
- P0 只有在有明确标准/测试证据、修改最小、不改变架构且有回归测试时才可进入 0B。本次没有执行 0B。
- Windows V1 Scope 采用显式状态；未进入 Scope 的 Profile 必须显示“当前版本未支持”。
