# EquipEffi 当前路线

## 权威状态

- **Current Roadmap:** EquipEffi V2.2
- **路线原文:** [docs/28_EquipEffi 后续开发总体路线 V2.2.md](docs/28_EquipEffi%20后续开发总体路线%20V2.2.md)
- **Current Phase:** Phase 1
- **State:** `BLOCKED`
- **Next State:** PENDING_SR01_REVIEW
- **Automatic continuation:** `DISABLED`
- **Allowed Work:** P1-SR01 is limited to business-contract, V1-scope and governance Markdown alignment. The fixed-SHA independent technical review and named Golden approval are RESOLVED; Solution/Product Review is PENDING_SR01_REVIEW. After documenting, validating, pushing and confirming Windows CI, stop for that review. Do not merge, declare Phase 1 PASS, or begin Phase 2.

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

R01–R07 的技术独立复验固定 SHA 为 3101e05abd7f33262a9449c390d61ec00008fb75；本次 P1-G04 审批基线为 3e8ff4eb3f13593d2d223e7b98373311d2e85d7f。王玮作为 GB 19762—2025 离心泵标准负责人，于 2026-09-28T11:03:04+08:00 正式批准了 18 条 pump_water Golden 0.4。正式记录位于 specs/equipment_efficiency/golden/pump_water/，均为三个 APPROVED 状态、review_owner=王玮、review_flags=[]，且逐条保留已批准的输入、预期结果、Decimal50 trace、证据 sidecar 与候选 provenance。Golden 0.1 七例、原 0.3 的 26 条候选和 3 条 replacement candidates 均未改写；8 条 pump_chemical 候选仍未获 V1 Golden 批准。候选注册表继续锁定来源文件、SHA、schema、baseline 和记录数。精确表3边界由generated boundary test负责，首批人工Golden不要求重复穷举端点。治理门禁：FIXED_SHA_INDEPENDENT_REVIEW = RESOLVED（7aaf7058273353237a36d03a05679d807cddcf07）；GOLDEN_CASE_NAMED_HUMAN_APPROVAL = RESOLVED；SOLUTION_PRODUCT_REVIEW = PENDING_SR01_REVIEW。当前 Phase 1 仍为 BLOCKED；不得声明 Phase 1 PASS 或启动 Phase 2。

> **P1-SR01 文档修订、验证、提交并核查 Windows CI 后，停止等待 Solution/Product Review；不得宣布 Phase 1 PASS 或进入 Phase 2。**

Phase 1 只允许建立业务规范 V0.1、Canonical Schema、Product/Profile Schema、Import Contract、Golden Case Schema、Support Status 和 `pump_water` 样板的标准映射；不得批量迁移 17 个 Profile。

## Phase 1 当前执行

Phase 1 按 `docs/29_Phase 1 业务规范与数据契约.md` 的既定顺序执行：

```text
P1-G01 → P1-G02 → P1-G03 → P1-G04 → P1-G05 → P1-G06
```

P1-G01 至 P1-G03、P1-G05、P1-G06 的既有交付保持不变。P1-G04 明确区分三层：Golden 0.1 的 7 例为历史冻结且不批准；原始 0.3 的 26 例继续为 DRAFT/PENDING（18 条清水 Application E2E、8 条石化 technical-only）；从 18 条清水 review records 生成的正式 0.4 共 18 例，已由王玮在 2026-09-28T11:03:04+08:00 具名批准。review package 保留为原始审批依据，三条 replacement provenance 和全部字段/hash 由注册表及 validator 验证。精确表3边界由generated boundary test负责，首批人工Golden不要求重复穷举端点。Golden 批准门禁为 RESOLVED；固定 SHA 独立复验和 Solution/Product Review 仍未完成，因此 Phase 1 状态仍为 BLOCKED。已知 Legacy Regression 失败继续保留；不得声明 Phase 1 PASS 或启动 Phase 2。

## Phase 1 Review Boundary

P1-SR01 只修改业务规范、V1_SCOPE 与治理 Markdown。固定 SHA 独立技术复验和 Golden named-human approval 均为 RESOLVED；当前唯一待办门禁是 SOLUTION_PRODUCT_REVIEW = PENDING_SR01_REVIEW。本轮取得新提交 SHA 并确认 Windows CI 后停止等待该评审；不得宣布 Phase 1 PASS、合并 PR 或进入 Phase 2。

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

因此 Phase 0 保持 PHASE_0_PASS，Phase 1 当前状态仍为 BLOCKED。Windows V1 产品决策已记录；0.1 的 7 个历史案例不会晋升，18 条正式 0.4 已由具名标准负责人批准，仍须固定 SHA 独立复验及 Solution/Product Review，不授权进入 Phase 2。

## Phase 0 保护边界

- 默认不重构、不扩功能、不批量修改 evaluator。
- 只保留当前正式运行链；兼容层和空壳先标记，不在 Phase 0 大规模删除。
- `Legacy Regression` 保护旧行为；`Approved Golden Case` 才保护业务真相。
- P0 只有在有明确标准/测试证据、修改最小、不改变架构且有回归测试时才可进入 0B。本次没有执行 0B。
- Windows V1 Scope 采用显式状态；未进入 Scope 的 Profile 必须显示“当前版本未支持”。
