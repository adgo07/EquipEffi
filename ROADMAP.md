# EquipEffi 当前路线

## 权威状态

- **Current Roadmap:** EquipEffi V2.3
- **路线原文:** [docs/28_EquipEffi 后续开发总体路线 V2.3.md](docs/28_EquipEffi%20后续开发总体路线%20V2.3.md)
- **V2.2 继承基线:** [docs/28_EquipEffi 后续开发总体路线 V2.2.md](docs/28_EquipEffi%20后续开发总体路线%20V2.2.md)
- **Current Phase:** Phase 1 (complete)
- **State:** `PHASE_1_PASS`
- **Next State:** `PHASE_2_READY`
- **Automatic continuation:** `DISABLED`
- **Allowed Work:** Numeric Contract v1 adoption/compatibility verification only. Phase 2 is READY but has not started; begin Phase 2 only after explicit user authorization. Automatic continuation remains DISABLED.

## 治理切换

V2.3 在 V2.2 阶段骨架不变的前提下完成路线校准，并成为当前正式总体路线。V2.2 保留为 V2.3 的继承基线；旧 v15 / T04.xx、旧 HANDOFF、编号执行清单和历史测试数字仍保留事实价值，但统一标记为：

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
PLATFORM_BASELINE.md
platform-lock.json
ADR/
```

## Roadmap V2.3 Alignment（2026-09-28；Numeric v1 adoption 更新于 2026-10-01）

V2.3 不重新编号或改变 Phase 0～10。它只把已经发生的真实进展反馈回总体路线：Phase 0 PASS、Phase 1 PASS、QZC-A01 COMPLETE、Phase 2 READY/NOT_STARTED；用 Phase 1 已验证的多维状态模型替代旧单一 Support Status；明确 Phase 1 `pump_water` 是业务真相样板、Phase 3 `pump_water` 是工程/生命周期纵向样板；正式 Excel 仍在 Phase 8，但 Phase 2～4 必须保持 contract-driven 输入/结果接口。

Qingzhou-contracts 当前显式锁定 `ee5feb0cc34dbd99790500fadd0c4c932e202a20`。Architecture 继续为 `V2.1 FROZEN`；Numeric Contract 已正式采用 `v1 / FROZEN`（`contracts/numeric/NUMERIC_CONTRACT_V1_FROZEN.md`）；Unit、Module/Capability、Workspace/Attempt/Record/Result、qzpack 等其余公共 Contract 仍为 `DRAFT / NOT YET RELEASED`，不得借 Numeric adoption 一并升级。EquipEffi Pump 保留 `EQUIPEFFI_PUMP_DECIMAL50_V2`，但 Decimal50/ROUND_HALF_EVEN 不是平台全局默认，其他设备按自身证据声明 Numeric Profile。中央升级仍须显式更新 `PLATFORM_BASELINE.md` 与 `platform-lock.json`。

## Phase 0 结论

Phase 0A 的治理切换、不可变起始 tag、真实基线、资产审计、第三方 55 项入库、风险重新分级、17 Profile 注册、Windows V1 Scope 草案、Golden Candidate 盘点和首个纵向样板选择已完成。2026-09-22 验收曾因交付物未提交、证据字段不完整、QA 表结构不统一和产品需求/商业价值证据缺失而暂时阻塞；治理补正和复验已完成，未修改业务代码。

R01–R07 的技术独立复验固定 SHA 为 3101e05abd7f33262a9449c390d61ec00008fb75；本次 P1-G04 审批基线为 3e8ff4eb3f13593d2d223e7b98373311d2e85d7f。王玮作为 GB 19762—2025 离心泵标准负责人，于 2026-09-28T11:03:04+08:00 正式批准了 18 条 pump_water Golden 0.4。正式记录位于 specs/equipment_efficiency/golden/pump_water/，均为三个 APPROVED 状态、review_owner=王玮、review_flags=[]，逐条保留已批准的输入、预期结果、Decimal50 trace、证据 sidecar 与候选 provenance。Golden 0.1 七例、原 0.3 的 26 条候选和 3 条 replacement candidates 均未改写；8 条 pump_chemical 候选仍未获 V1 Golden 批准。精确表3边界由 generated boundary test 负责，首批人工 Golden 不要求重复穷举端点。FIXED_SHA_INDEPENDENT_REVIEW=RESOLVED（7aaf7058273353237a36d03a05679d807cddcf07）；GOLDEN_CASE_NAMED_HUMAN_APPROVAL=RESOLVED；SOLUTION_PRODUCT_REVIEW=RESOLVED（P1-SR01 PASS，评审基线 38bdfc28e078fee067743d30055fb39337881c7c）。Phase 1 Exit Gate 已满足，状态为 PHASE_1_PASS；Phase 2 为 PHASE_2_READY，须经用户明确授权后才能开始。

> **P1-SR01 = PASS；Solution/Product Review = RESOLVED。Phase 1 Exit Gate 已满足并进入 PHASE_1_PASS；Phase 2 状态为 PHASE_2_READY，但不会自动开始，必须等待用户明确授权。**

Phase 1 建立并验证了业务规范 V0.1、Canonical Schema、Product/Profile Schema、Import Contract、Golden Case Schema、多维状态模型和 `pump_water` 样板标准映射；未批量迁移 17 个 Profile。

## Phase 1 当前执行

Phase 1 按 `docs/29_Phase 1 业务规范与数据契约.md` 的既定顺序执行：

```text
P1-G01 → P1-G02 → P1-G03 → P1-G04 → P1-G05 → P1-G06
```

P1-G01 至 P1-G03、P1-G05、P1-G06 的既有交付保持不变。P1-G04 明确区分三层：Golden 0.1 的 7 例为历史冻结且不批准；原始 0.3 的 26 例继续为 DRAFT/PENDING（18 条清水 Application E2E、8 条石化 technical-only）；从 18 条清水 review records 生成的正式 0.4 共 18 例，已由王玮在 2026-09-28T11:03:04+08:00 具名批准。review package 保留为原始审批依据，三条 replacement provenance 和全部字段/hash 由注册表及 validator 验证。精确表3边界由 generated boundary test 负责，首批人工 Golden 不要求重复穷举端点。Golden 批准门禁、固定 SHA 独立复验和 Solution/Product Review 均为 RESOLVED；Phase 1 Exit Gate 已满足，状态为 PHASE_1_PASS。Phase 2 为 PHASE_2_READY，只有在用户明确授权后才能开始；已知 Legacy Regression 失败继续保留。

## Phase 1 Review Boundary

P1-SR01 状态模型契约对齐已通过 Solution/Product Review。FIXED_SHA_INDEPENDENT_REVIEW、GOLDEN_CASE_NAMED_HUMAN_APPROVAL、SOLUTION_PRODUCT_REVIEW 均为 RESOLVED；Phase 1 Exit Gate 已满足。当前状态为 PHASE_1_PASS，下一状态为 PHASE_2_READY。Phase 2 不会自动开始，须先取得用户明确授权。

## Phase 2 设计输入（尚未授权实施）

未来 Excel 批量导入/回写必须采用 contract-driven 方式：
Product/Profile Contract 为字段类型、单位、枚举和约束真相源；
Import Contract 只负责外部字段映射；
Excel 不复制评价算法；
批量行统一进入 EvaluationService；
结果长期按 stable result_field_id 回写。

Phase 2 只建立最小正式工程底座：Python 3.12、PySide6 薄 AppShell、Design Token、Repository Protocol、三库职责、Migration 基础、Logging 和有限工程结构清理。不得在 Phase 2 批量迁移 17 Profile、批量重写 evaluator、实现完整 Excel、完整产品 Shell、移动端、Suite，或一次性实现全部中央 DRAFT Contract。

以上仅作为 Phase 2 设计输入；Phase 2 READY 不代表自动开始或授权开发 Excel 功能，进入 Phase 2 前仍须取得用户明确授权。

## Phase 0 Exit Gate

| Gate | result | evidence |
|---|---|---|
| Governance | PASS | V2.3 权威入口、V2.2 作为继承基线、旧路线失去调度权、Phase 0 状态和可复现治理提交 |
| Baseline | PASS | `BASELINE.md`、`pre-v2-rebaseline`、真实 unittest/compile/package/smoke/performance |
| Assets | PASS | `ASSET_AUDIT.md`；运行链、双实现、空壳和 release surface 已登记 |
| QA | PASS（开放项已入库） | `QA_BACKLOG.md`；第三方 55 项、历史路线和当前失败均有 ID |
| Metadata | PASS | Canonical / Product Schema / Import Contract / Ruleset / UI Metadata 边界 |
| Scope | PASS | `V1_SCOPE.md`；17 Profile、已批准多维状态模型，以及用户需求/商业价值的显式证据状态 |
| Vertical Slice | PASS | `pump_water` 已与 3 个替代候选比较并记录风险/必须证明项 |
| Phase 0B | N/A | 没有满足条件的 Hotfix 被批准；无额外重构混入 |

Phase 0 保持 PHASE_0_PASS；Phase 1 Exit Gate 已满足，当前为 PHASE_1_PASS；下一状态为 PHASE_2_READY。Windows V1 产品决策与 Profile 映射保持不变；Phase 2 不会自动启动，须由用户明确授权。

## Phase 0 保护边界

- 默认不重构、不扩功能、不批量修改 evaluator。
- 只保留当前正式运行链；兼容层和空壳先标记，不在 Phase 0 大规模删除。
- `Legacy Regression` 保护旧行为；`Approved Golden Case` 才保护业务真相。
- P0 只有在有明确标准/测试证据、修改最小、不改变架构且有回归测试时才可进入 0B。本次没有执行 0B。
- Windows V1 Scope 采用显式状态；未进入 Scope 的 Profile 必须显示“当前版本未支持”。
