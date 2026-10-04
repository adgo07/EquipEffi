# Phase 5 — pump_chemical Stage D Evidence Matrix

依据：中央 `STANDARD_DEVELOPMENT_GUIDE_V0.1`（`ACTIVE / EVOLVING`）Stage D；
`AGENTS.md`；`V1_SCOPE.md`；`docs/32_Phase 3 GB19762离心泵统一正式纵向闭环.md`。

**先证后改**：本矩阵逐项基于当前 Base 的**真实代码与实测证据**判断，
不是计划声明。任何未取得证据的项不得写 `PASS`。

Base：`master@d6112ea9c7c1c16f95d798c2229cdc54aaf6240a`（= Phase 4 PR #12 merge）。

状态取值：`PASS` / `BLOCKED` / `NOT_APPLICABLE` /
`DEFERRED_BY_ROADMAP_TO_PHASE_8` / `DEFERRED_BY_ROADMAP_TO_PHASE_9`。

---

## 1. 逐项证据矩阵

| # | 项目 | 状态 | 证据 |
|---|---|---|---|
| 1 | 标准来源 | `PASS` | `GB 19762—2025《离心泵能效限定值及能效等级》`；证据登记 `specs/equipment_efficiency/evidence_registry.json` 的 `GB19762-2025-PDF`（含 SHA-256）；台账 `STANDARD_ISSUES_REGISTER.md` |
| 2 | Mapping | `PASS` | `specs/equipment_efficiency/profiles/pump_chemical.md`（石化类别只接受"单级石油化工离心泵"/"多级石油化工离心泵"；单级 `stages=1`、多级 `stages>1`）；Canonical `src/equipeffi/resources/standards/pump.json`；`PUMP_NUMERIC_AND_DECISION_CONTRACT_V2` |
| 3 | Standard Issues | `PASS` | 台账仅 `EQP-STD-GB19762-001`（实施日期与 `as_of` 关系），已 `RESOLVED`（软件产品决定 + R3 补充决定）。**无 chemical 新问题**；本 Phase 未制造 issue |
| 4 | Rule | `PASS` | Canonical `stable_data_ids`：`GB19762-R000011`～`R000014`（石化表 2 的 ns 分档唯一规则行）；由 `test_phase3_golden_and_boundaries` 端点断言覆盖 |
| 5 | Calculator | `PASS` | `ChemicalPumpEvaluator`（Decimal50、`ROUND_HALF_EVEN`）；本 Phase **未改动**任何公式 / 边界 / 等级 |
| 6 | Approved Golden | `PASS` | `specs/equipment_efficiency/golden/pump_chemical/` 11 条 `golden-case-0.5`（`APPROVED`）；`test_phase3_golden_and_boundaries` 14 tests OK（含 18 water + 11 chemical） |
| 7 | generated boundaries | `PASS` | 端点/分档边界由 `test_phase3_golden_and_boundaries` 的 ns 端点断言（20/60/120/210/300 的 inclusive/exclusive 与唯一规则行）与 `test_pump_numeric_contract_v2` 覆盖；本 Phase 边界数值零漂移 |
| 8 | Numeric / Conformance | `PASS` | `test_pump_numeric_contract_v2` + `test_numeric_contract_v1_adoption` 15 tests OK；`platform-lock.json` 未修改；Numeric Profile `EQUIPEFFI_PUMP_DECIMAL50_V2` 未修改 |
| 9 | regression | `PASS` | 全量 unittest + `tools/check_windows_regressions.py`；known baseline 未放宽（详见执行报告实测数字） |
| 10 | Qt Windows UI | `PASS` | 正式发布用户表面 = PySide6 Qt Desktop（`--qt`）；`test_phase5_chemical_stage_d.QtChemicalStageDTests` 验证 单级/多级 × 正常/OOS/INSUFFICIENT_DATA/INVALID_INPUT，并验证支持状态在只读辅助信息区展示 |
| 11 | Application | `PASS` | 统一入口 `CentrifugalPumpAnalysisService`（`pump_water` + `pump_chemical` 共用）；发布门禁 `_release_support` 本 Phase 提升为候选 |
| 12 | Workspace / Finalize / Record / Reopen | `PASS` | `test_phase3_r2_final_closure`（Finalize 全状态矩阵 11）、`test_phase3_r3_closure`（Workspace/Record/Reopen 31）、`test_phase3_r3_as_of_lifecycle`（18）均 OK |
| 13 | 标准依据 / 结果解释 | `PASS` | 结果契约 `references.standard`（`pack_id` / `data_version` / `pack_hash`）；Qt 结果区"标准依据：GB 19762—2025…"；`explanation` 逐案说明 |
| 14 | provenance / traceability | `PASS` | `calculation_trace` + `matched_rule_id` + `references`；`PumpAnalysisResult.provenance`（`ruleset_executed` / `rule_profile` / `no_ruleset_reason`）；`formula_hash` / `pack_hash` |
| 15 | Excel | `DEFERRED_BY_ROADMAP_TO_PHASE_8` | 见 §2 |
| 16 | Windows 交付层（安装包 / 签名 / 正式发布产物） | `DEFERRED_BY_ROADMAP_TO_PHASE_9` | 见 §3 |

**未解释的 `BLOCKED`：无。**

---

## 2. Excel — `DEFERRED_BY_ROADMAP_TO_PHASE_8`

`V4 / Excel adapter` 当前不是 Phase 5 的正式支持提升表面。它保留为
`future-adapter surface`，不是"历史废代码"。

**Phase 8 硬约束**：Excel / V4 必须**调用同一 Application / Calculator**，
**不得**建立第二套业务算法。既有登记 `QA-EXCEL-001`（Excel 数值入口
Decimal→float）在 Phase 8 前必须关闭。

`V1_SCOPE.md` 与 `ROADMAP.md` 已把 Excel 收口排在 Phase 8；本 Phase 不动它。

---

## 3. Windows 交付层 — `DEFERRED_BY_ROADMAP_TO_PHASE_9`

安装包、代码签名、正式发布产物属于 Phase 9。
本 Phase **不**产生任何对外发布产物，**不**声明可发布。

---

## 4. 标准成熟度：两次状态转移必须分开记证据

不得从 `READY_FOR_IMPLEMENTATION` 直接"跳写"为 `SUPPORTED`。

### 4.1 转移一：`READY_FOR_IMPLEMENTATION` → `IMPLEMENTED`

| 证据类别 | 具体证据 |
|---|---|
| 当前真实核心实现 | `ChemicalPumpEvaluator` + `CentrifugalPumpAnalysisService`（统一 Application）；`test_pump_numeric_contract_v2` 15 tests OK |
| 11 条 Approved Golden | `specs/equipment_efficiency/golden/pump_chemical/` 11 条 `golden-case-0.5`（`APPROVED`，Owner 11/11 @ 2026-10-02） |
| 统一 Application | `pump_water` + `pump_chemical` 共用同一 Use Case / 输入契约 / 结果契约 |
| generated boundaries | ns 端点与唯一规则行断言（`test_phase3_golden_and_boundaries`） |
| Numeric / Conformance | `EQUIPEFFI_PUMP_DECIMAL50_V2` + `platform-lock.json` 一致；conformance 套件 OK |

**结论**：`IMPLEMENTED` 成立（Stage C 证据完备）。

### 4.2 转移二：`IMPLEMENTED` → `SUPPORTED`

| 证据类别 | 具体证据 | 状态 |
|---|---|---|
| 本 Phase Stage D 正式产品路径验证 | 本矩阵 §1 第 10–14 项（Qt E2E / Application / Workspace·Finalize·Record·Reopen / 标准依据 / provenance） | `PASS` |
| `FORMAL_APPLICATION_E2E` evidence | `specs/equipment_efficiency/evidence/phase5_chemical_stage_d_e2e.json`（11 条历史真值经当前正式 Application 链一致复现，`business_truth_consistent` 全为 true） | `PASS` |
| 最终独立验收结论 | **尚未产生** | **PENDING** |

**因此当前成熟度写为**：`IMPLEMENTED`（已成立）→ `SUPPORTED`（**候选**）。

治理状态只允许：

```text
SUPPORT_PROMOTION_CANDIDATE
READY_FOR_INDEPENDENT_ACCEPTANCE
```

**不得**写成"正式支持已经生效"，**不得**自宣 `Stage D PASS` 或
`pump_chemical officially SUPPORTED`。

---

## 5. 历史 Golden 与当前 Stage D 证据的分工

| | 历史 Golden | 当前 Stage D 证据 |
|---|---|---|
| 文件 | `specs/equipment_efficiency/golden/pump_chemical/GC-PUMP-V5-*.json` | `specs/equipment_efficiency/evidence/phase5_chemical_stage_d_e2e.json` |
| `evaluation_layer` | `PROFILE_EVALUATOR_TECHNICAL` | 记录当前 `formal_application_e2e` |
| `support_status` | `null`（历史来源，未声明发布支持） | `SUPPORTED`（候选） |
| 含义 | **历史批准来源** | **今天的正式产品链已经成立** |

本 Phase **未修改**任何 Golden 业务真值、历史 provenance，**未批量改写**
`evaluation_layer`。证据文件记录了每条 Golden 的文本 SHA-256，可检测真值被改写。

---

## 6. 非正式发布表面的 support 差异

以下表面**不是** Phase 5 的正式支持提升表面，若仍返回
`pump_chemical = NOT_IN_RELEASE_SCOPE`，登记为 `REGISTERED_DEVIATION`
（见 `QA_BACKLOG.md` 的 `QA-P5-001` / `QA-P5-002` / `QA-P5-003`）：

| 表面 | 处置 |
|---|---|
| `--json` / `ApplicationApi` | Phase 6：产品入口 / Shell / shipped surface 收口 |
| `--web` | Phase 6 |
| JSONL smoke / CLI | Phase 6 |
| legacy Tk `--gui` | Phase 6 |
| Android bridge | Phase 9（正式发布前消除未声明的发布表面语义分歧） |
| V4 / Excel adapter | Phase 8 |

**不得**用"历史兼容代码"含糊带过。
**不得**把这些已登记 deviation 误报为 Phase 5 PASS 范围内已修复。

---

## 7. 矩阵最终状态（Phase 5 执行完成时）

```text
PASS                                14 项
DEFERRED_BY_ROADMAP_TO_PHASE_8       1 项（Excel）
DEFERRED_BY_ROADMAP_TO_PHASE_9       1 项（Windows 交付层）
BLOCKED                              0 项
未解释的 BLOCKED                     0 项
```

`IMPLEMENTED → SUPPORTED` 的最终一步依赖独立验收结论，因此本 Phase 结束时
成熟度停在 `IMPLEMENTED`，并把 `SUPPORTED` 作为候选移交独立验收。
