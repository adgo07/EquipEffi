# EquipEffi 当前路线

## 权威状态

- **Current Roadmap:** EquipEffi V2.2
- **路线原文:** [docs/28_EquipEffi 后续开发总体路线 V2.2.md](docs/28_EquipEffi%20后续开发总体路线%20V2.2.md)
- **Current Phase:** Phase 1
- **State:** `BLOCKED`
- **Next State:** PENDING_GOLDEN_OWNER_REVIEW
- **Automatic continuation:** `DISABLED`
- **Allowed Work:** P1-G04 only: close the V2 Golden approval schema, validate candidate provenance/hashes, prepare 18 `pump_water` review records, update governance, and run Windows CI. Do not approve cases, declare Phase 1 PASS, or begin Phase 2.

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

R01–R07 的技术独立复验固定 SHA 为 `3101e05abd7f33262a9449c390d61ec00008fb75`。P1-G04-R1 仅收口 Golden provenance：0.1 七例保持历史冻结，原 0.3 的 26 条记录内容不变且仍为 `DRAFT/PENDING`；新增 3 条版本化 replacement candidates，由 18 条清水待审记录引用，`review_flags=0`。正式 0.4 仍未生成或批准。候选注册表锁定允许文件路径、文件 SHA、schema 版本、基线 SHA、记录总数及三条旧/新 ID 映射。精确表3边界由 generated boundary test 负责，首批人工 Golden 不要求重复穷举端点。当前仍 `BLOCKED`，等待具名标准负责人逐条决定、固定 SHA 独立复验和 Solution/Product Review；不得声明 Phase 1 PASS 或启动 Phase 2。

> **提交后核查新固定 SHA 的 Windows CI，然后停止等待人工标准批准与独立复验；不得宣布 Phase 1 PASS 或进入 Phase 2。**

Phase 1 只允许建立业务规范 V0.1、Canonical Schema、Product/Profile Schema、Import Contract、Golden Case Schema、Support Status 和 `pump_water` 样板的标准映射；不得批量迁移 17 个 Profile。

## Phase 1 当前执行

Phase 1 按 `docs/29_Phase 1 业务规范与数据契约.md` 的既定顺序执行：

```text
P1-G01 → P1-G02 → P1-G03 → P1-G04 → P1-G05 → P1-G06
```

`P1-G01` 至 `P1-G03`、`P1-G05`、`P1-G06` 的既有交付保持不变。`P1-G04` 区分三个层次：Golden 0.1 的 7 例只作历史冻结且不批准；原始 0.3 的 26 例继续为 `DRAFT/PENDING`（18 条清水 Application E2E、8 条石化 technical-only）；0.4 review package 是待人工具名复核记录，正式 `golden-case-0.4` schema 只在真实批准后接收正式记录。三条有来源不一致的场景已经有独立、版本化 replacement candidate，原 0.3 行未改；18 条 review record 均无 review flags。精确表3边界由 generated boundary test 负责，首批人工 Golden 不要求重复穷举端点。候选来源路径、文件和记录哈希、schema 版本、基线 SHA 由注册表及 validator 校验。技术基础为固定 SHA `3101e05abd7f33262a9449c390d61ec00008fb75`；当前仍 `BLOCKED`，须由标准负责人逐条决定，随后独立验收和 Solution/Product Review；不得声明 Phase 1 PASS 或启动 Phase 2。已知 Legacy Regression 失败继续保留。

## Phase 1 Review Boundary

本轮提交并取得 Windows CI 后，停止等待具名标准负责人逐条审批及原独立会话复验；Golden 批准前不得推进 Phase 1 状态或 Phase 2。

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

因此 Phase 0 保持 `PHASE_0_PASS`，Phase 1 当前状态为 `BLOCKED`。Windows V1 产品决策已记录；0.1 的 7 个历史案例不会晋升，正式 0.4 仍待具名标准负责人审批，不授权进入 Phase 2。

## Phase 0 保护边界

- 默认不重构、不扩功能、不批量修改 evaluator。
- 只保留当前正式运行链；兼容层和空壳先标记，不在 Phase 0 大规模删除。
- `Legacy Regression` 保护旧行为；`Approved Golden Case` 才保护业务真相。
- P0 只有在有明确标准/测试证据、修改最小、不改变架构且有回归测试时才可进入 0B。本次没有执行 0B。
- Windows V1 Scope 采用显式状态；未进入 Scope 的 Profile 必须显示“当前版本未支持”。
