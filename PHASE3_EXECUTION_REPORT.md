# PHASE3_EXECUTION_REPORT

任务：**EquipEffi Phase 3 — GB 19762—2025 离心泵统一正式纵向闭环**
分支：`phase3/gb19762-unified-vertical-slice`
状态：**EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE**
停止点：**等待独立验收；不自行合并 PR、不宣布 Phase 3 PASS、不进入 Phase 4。**

---

## 1. start master SHA

```text
7e16418aa32ced5512e26bd70227f01a329fbdfc
```

（= 任务授权书预期值；PR #10 "Phase 2：最小正式工程底座" 的合并提交。）

## 2. final head SHA

```text
4ca0f84135561954bda5bc4ace622a07bd5fb1bd
```

（分支 `phase3/gb19762-unified-vertical-slice` 的 final head，已推送到 `origin`；PR #11 的 head 与此一致。）

本次提交序列（相对 Phase 3 基线 `7e16418aa32ced5512e26bd70227f01a329fbdfc`）：

```text
cf22e11  统一 golden-case-0.5 schema + 11 条 pump_chemical Approved Golden + owner 批准证据
107fe7c  治理基线：Phase 2 PASS / Phase 3 IN_PROGRESS / V2.3 8.2 增量修正 / EQP-STD-GB19762-001 更正
6299cbd  P3-G01/G03：统一 Application 契约 + records.sqlite + Workspace/Record/History/Reopen + docs/32
9b7cb3c  P3-G02：统一 GB 19762 Qt 分析页 + 分析记录页
c284b16  P3-G04：29/29 Golden 回放 + 生成边界 + CI 接线 + QA 处置 + 本报告
b049205  docs：记录 final head
4ca0f84  fix(ci)：恢复 CI 作用域已知回归基线并记录该更正（见 25.1）
```

## 3. actual diff

| 提交 | 内容 |
|---|---|
| `cf22e11` | 统一 `golden-case-0.5` schema + 11 条 `pump_chemical` Approved Golden + owner 批准证据 |
| `107fe7c` | 治理基线：Phase 2 PASS / Phase 3 IN_PROGRESS / V2.3 8.2 增量修正 / `EQP-STD-GB19762-001` 更正 |
| `6299cbd` | P3-G01/G03：统一 Application 契约 + `records.sqlite` + Workspace/Record/History/Reopen + `docs/32` |
| `9b7cb3c` | P3-G02：统一 GB 19762 Qt 分析页 + 分析记录页 |
| 本提交 | P3-G04：29/29 Golden 回放 + 边界 + CI 接线 + QA 处置 + 本报告 |

**未修改**：`pump.py` 等 Pump evaluator、Canonical `pump.json`、18 条 `golden-case-0.4`、11 条 `golden-case-0.5` 的业务真值、Numeric Profile、`platform-lock.json`、`transformer` 资产、Excel 实现。
（P3-G02 有意修改了 `tests/contract/test_architecture_boundaries.py` 的 Qt 允许契约，以纳入新的 Application 契约；Architecture V2.1 与 `platform-lock` 未变。）

## 4. Python 3.12 exact environment

```text
sys.executable : G:\Python Project\EquipEffi\.venv\Scripts\python.exe
sys.version    : 3.12.14 (main, Sep  1 2026, 14:17:39) [MSC v.1944 64 bit (AMD64)]
PySide6        : 6.11.2
QT_QPA_PLATFORM: offscreen（GUI 断言）
platform-lock  : ee5feb0cc34dbd99790500fadd0c4c932e202a20（未变更）
Windows CI 起点: 945 run / 9 fail / 5 error / 3 skip（run 36970415483，Phase 2 基线）
```

## 5. Phase 2 PASS 治理纠正

`AGENTS.md` / `TASK_STATE.md` / `HANDOFF.md` / `ROADMAP.md` / `REFERENCE_STANDARD_ROADMAP.md` 由 `EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE` 更新为 **`PHASE_2_PASS`**，并记录 PR #10 独立验收 + 合并（`7e16418a`）。

## 6. Phase 3 scope amendment

在路线原文与路线入口新增**有日期、有 decision owner** 的增量修正（`docs/28` 第 8.2 节）：

- Phase 3 = **GB 19762—2025 离心泵统一正式纵向闭环**（`pump_water` + `pump_chemical` 同一产品/UI/Use Case/Workspace/Record/History/Result Contract）；
- Phase 5 不再承担「首次接入」，改为承担 `pump_chemical` 的**正式发布支持收口（Stage D）**；其余职责暂不重新设计；
- 不创建 V2.4、不改 Phase 0～10 编号、不提前 Phase 4/6/7/8/9；
- 三个状态维度数值不变。

## 7. docs/32

新增 `docs/32_Phase 3 GB19762离心泵统一正式纵向闭环.md`，含 19 节：Scope / Non-goals / Product Capability Model / Internal Rule Profile Model / Unified Category Routing / Application Analysis Contract / Workspace Contract / Record Contract / `records.sqlite` schema / forward-only migration policy / Unified Qt Analysis UI / Finalize policy / History-Reopen policy / `as_of` policy / Golden approval evidence / P3-G01～G04 / Tests / Exit Gates / Phase 4 boundary。含平台预检查与 Standard Issue 声明。

## 8. 18 条 water owner reconfirmation evidence

**18 / 18 PASS**（2026-10-02）。证据：`specs/equipment_efficiency/golden/owner_approvals/pump_water_owner_reconfirmation_2026-10-02.json`，逐案记录 `case_id`、`review_owner`、`approved_at`、`review_flags` 与文件 SHA-256。

**18 条 `golden-case-0.4` 内容字节未修改**（`git status` 对该目录为空）。

## 9. 11 条 chemical owner approval evidence

**C1–C11，11 / 11 PASS**（2026-10-02）。证据：`specs/equipment_efficiency/golden/owner_approvals/pump_chemical_owner_approval_2026-10-02.json`（含 candidate-derived 8 条与 owner-defined 3 条分组、逐案文件 SHA-256）。

## 10. chemical Golden formalization

新增统一 `specs/equipment_efficiency/schemas/golden_case_0_5.schema.json`（最小通用化；**未**新建 chemical 专用 schema）：

- `profile_id` ∈ `{pump_water, pump_chemical}`；`case_id` `^GC-PUMP-V5-(WATER|CHEMICAL)-…`；
- `evaluation_layer` ∈ `{APPLICATION_E2E, PROFILE_EVALUATOR_TECHNICAL}`；
- `provenance` 为 tagged `oneOf`：
  - `CANDIDATE_DERIVED` → 必须给候选文件/行/规范化 SHA；
  - `OWNER_DEFINED` → 记录 owner 批准证据 ID + `standard_evidence` + `canonical_evidence`，**不伪造候选文件/行**。

11 条正式 Golden 位于 `specs/equipment_efficiency/golden/pump_chemical/`：

| 组 | 数量 | provenance | evaluation_layer | support_status |
|---|---|---|---|---|
| C1–C8 | 8 | `CANDIDATE_DERIVED`（源自 0.3 技术候选） | `PROFILE_EVALUATOR_TECHNICAL` | `null` |
| C9–C11 | 3 | `OWNER_DEFINED` | `PROFILE_EVALUATOR_TECHNICAL` | `null` |

**为何不是 `APPLICATION_E2E`**：公开 Application 发布门禁对 `pump_chemical` 仍短路返回 `NOT_IN_RELEASE_SCOPE` 且不计算（由 `tests/unit/test_pump_golden_case_0_3.py` 冻结）。写成 `APPLICATION_E2E` 会谎报当前可复现层级。升级为 `APPLICATION_E2E` 的正确时点是 Stage D 之后。

生成器 `tools/build_phase3_chemical_golden.py`：**每个预期值都重新由当前 evaluator 派生；与 owner 批准真值不符时拒绝写出**（机制上防止"改 Golden 让测试绿"）。

C9/C10/C11 观察值（与 owner 批准一致）：

```text
C9  ns=243.74941676825332898685… → SUCCESS / 2级 / GB19762-R000014
C10 ns=313.71812592103329751618… → OUT_OF_STANDARD_SCOPE / 不适用
C11 ns=19.723982951529394947075… → OUT_OF_STANDARD_SCOPE / 不适用
```

## 11. Application contract

新增 `src/equipeffi/application/services/centrifugal_pump_analysis_service.py`（application 层，未导入 `sqlite3` / infrastructure / presentation）：

- `CentrifugalPumpAnalysisService`：**唯一**离心泵产品级入口，清水/石化共用同一 Use Case、同一输入契约、同一结果契约；**未**建 Water/Chemical 两个服务；
- 输入：`PumpAnalysisRequest(product_category, as_of, QBEP, HBEP, speed, efficiency, suction, stages, project_name, equipment_no, record_id, standard_code)`；`rule_profile` 由类别**精确派生**，用户不得直接选择；**`as_of` 必填，无隐式默认**；
- 结果：`PumpAnalysisResult` 统一骨架（`evaluation_status` / `grade` / `ui_conclusion` / `issue_codes` / `missing_fields` / `matched_rule_id` / `thresholds` / `calculation_trace` / `extra_metrics` / `references` / `finalizable`）；
- 派生量与阈值按**白名单**投影并转用户可理解名称；`Decimal` 递归归一为十进制文本，保证快照可 JSON 序列化且不依赖隐式 float（Numeric v1 §2）；
- 发布门禁：`pump_water = SUPPORTED`、`pump_chemical = NOT_IN_RELEASE_SCOPE`；
- 早于标准实施日期（`2026-03-01`）不计算，返回 `INSUFFICIENT_DATA` + `STANDARD_NOT_YET_EFFECTIVE`。

## 12. unified category routing

10 个用户可见类别（8 正式 + 其他类别 + 不确定类别），分组展示但**同一选择器/同一页面**。

| 用户可见类别 | 内部 rule profile |
|---|---|
| 单级单吸清水离心泵 / 单级双吸清水离心泵 / 管道清水离心泵 / 多级清水离心泵 / 轻型多级清水离心泵（立式）/ 轻型多级清水离心泵（卧式） | `pump_water` |
| 单级石油化工离心泵 / 多级石油化工离心泵 | `pump_chemical` |

- 路由只做**精确名称**匹配，复用 `domain/evaluation/device_types.py` 的登记表；**未**在 UI/Application 新建第二份映射；
- 已测试合成文本（`某多级清水化工离心泵`、`清水化工两用泵`、`石油化工清水泵` 等）**不会**被猜测为任一 profile；
- 用户**不能**选择 `pump_water` / `pump_chemical`。

## 13. records.sqlite schema / migration

`infrastructure/persistence/records_migrations.py`：

- **独立** runner 与**独立**历史表 `record_schema_migration_history`；与 `user.sqlite` 的 `migrate_user_database` 完全分离（后者按文件名显式拒绝非 `user.sqlite`）；
- `schema_version / migration_id / checksum / applied_at_utc / applied_by_app_version`；checksum = `sha256("\n".join(statements))`；
- `BEGIN IMMEDIATE` + 单连接上下文；forward-only；**幂等**；
- 防御性拒绝破坏性语句（`DROP TABLE` / `DROP INDEX` / `DROP COLUMN` / `TRUNCATE` / `DELETE FROM`）；
- 未知更高版本、历史缺口、checksum 变更均**明确报错**，不静默重建或降级。

表：`workspace`（可变草稿）与 `record`（不可变正式记录，稳定关系字段 + versioned JSON snapshots）。

## 14. Workspace cross-process proof

`tests.unit.test_phase3_unified_analysis.WorkspaceRoundTripTests.test_workspace_inputs_survive_a_separate_process`：

进程 A 经 `create_workspace` 写入 `W-proc`；进程 B 在**全新解释器**中直接打开同一 `records.sqlite` 读回，断言：

```text
product_category = 单级石油化工离心泵
as_of            = 2026-08-23
rule_profile     = pump_chemical
HBEP             = 14
project_name     = 跨进程项目
equipment_no     = P-777
```

**不是**同一 Repository 对象内 set/get。

## 15. Finalize matrix proof

| 状态 | 结果 | 测试 |
|---|---|---|
| `SUCCESS` | 允许 | `test_finalize_allowed_for_success_and_out_of_scope` |
| `OUT_OF_STANDARD_SCOPE` | 允许（有效专业结论） | 同上 |
| `INSUFFICIENT_DATA` | 允许（不强制手填原因） | `test_finalize_allowed_for_insufficient_data` |
| `INVALID_INPUT` | **拒绝** | `test_finalize_rejected_for_invalid_input` |
| 类别未确认 | **拒绝** | `test_finalize_rejected_for_uncertain_category` |

## 16. Record immutability proof

- `SqliteRecordRepository` **只有** `append_record` / `load_record` / `list_records`；**没有** update / delete 记录的方法；
- 重复 `record_id` 写入被显式拒绝：`test_record_is_immutable_and_cannot_be_overwritten`（`AnalysisError`）；
- 删除 Workspace 草稿不影响已 Finalize 的 Record：`test_records_are_not_deleted_by_workspace_delete`。

## 17. History proof

`test_history_lists_water_and_chemical_in_one_list`：同一 `list_records()` 返回 2 条，`rule_profile` 集合为 `{pump_water, pump_chemical}`；**未建两个历史库**。
`tests.unit.test_phase3_qt_unified.RecordsPageTests.test_history_shows_water_and_chemical_in_one_list`：同一列表显示两种类别。

## 18. Reopen-no-evaluator proof

把模块级工厂 `build_pump_evaluator` 替换为 `raise RuntimeError` 后：

- `test_reopen_does_not_call_the_evaluator` → `open_record("R-reopen")` 仍成功，返回原 `ui_conclusion=1级`、原 `as_of=2026-08-23`、原 `matched_rule_id=GB19762-T3-01`；
- `tests.unit.test_phase3_qt_unified.RecordsPageTests.test_reopen_does_not_recalculate_when_evaluator_is_broken` → 记录页仍显示原结论 `2级`。

## 19. as_of proof

- `PumpAnalysisRequest` 的 `as_of` 为**必填**；省略会 `TypeError`（`test_as_of_is_mandatory_without_implicit_default`）；
- 早于实施日期 → `INSUFFICIENT_DATA` + `STANDARD_NOT_YET_EFFECTIVE`，`calculation_trace` 为空（`test_as_of_earlier_than_effective_date_does_not_calculate`）；
- Finalize 写入实际 `as_of`；Reopen 保持原值（`test_reopen_preserves_original_as_of_and_result_snapshot`：`as_of = 2026-08-23` 于 record / result_snapshot / input_snapshot 三处一致）；
- 测试 harness 固定 `2026-08-23`；**未**修改 18 条 `golden-case-0.4` 来补 `as_of`（它们本身不携带该字段）。

## 20. Qt unified UI proof

`tests.unit.test_phase3_qt_unified`（13 tests，`QT_QPA_PLATFORM=offscreen`）：

- 8 个正式类别 + 其他 + 不确定全部在**同一选择器**内可见；
- 普通 UI 文本中**不含** `pump_water` / `pump_chemical` / `profile_id` / `rule_id` / `internal_id` / `field_id` / `SUPPORTED` / `NOT_IN_RELEASE_SCOPE`；
- 单级/管道类别自动锁定级数=1（来自既有业务契约）；多级类别保持可编辑；
- 清水与石化在**同一页面**完成分析并渲染统一结果骨架；
- 不确定类别不计算并要求确认；其他类别为"不适用"；
- 非法评价日期被报告且不崩溃。

`Pump Conformance` 目前**未**运行 Qt 测试；Qt 断言在 `Windows Core` 的 offscreen 任务中执行。

## 21. 29/29 Golden replay

`tests.unit.test_phase3_golden_and_boundaries.ApprovedGoldenReplayTests`：

```text
pump_water  golden-case-0.4 : 18 条，经统一 AnalysisService 回放
pump_chemical golden-case-0.5 : 11 条，经统一 AnalysisService 回放
合计 29 / 29，结论 / 等级 / evaluation_status / category_status / issue_codes / matched_rule_id 全部一致
```

另断言：石化案例经统一入口仍为 `support_status = NOT_IN_RELEASE_SCOPE`（Phase 3 未提升）；owner-defined 3 条**不含** `source_candidate_file` / `source_candidate_line`；candidate-derived 8 条保留候选 provenance。

## 22. generated boundaries

`UnifiedBoundaryTests` 新增化学边界覆盖：

```text
Q 下界 Q=5 开区间（不适用） / Q 略大于 5 进入范围
Q=300 与 Q=300.000001 → 不同规则行（阈值不同）
ns 端点 20 / 60 / 120 / 210 / 300 → 期望唯一规则行
ns > 300 与 ns < 20 → OUT_OF_STANDARD_SCOPE / 不适用
210<ns≤300 使用 Δη（公式(7)）；120≤ns≤210 分支不同
water 原生成边界行未回归：Q=300 → GB19762-T3-01，Q=300.000001 → GB19762-T3-02
```

既有 `tests.unit.test_pump_generated_boundaries_v2` 继续通过（water 原集 + chemical 区间）。

## 23. Pump Numeric / Conformance

`Pump Conformance` 门禁集（本机）：**516 tests / OK**

```text
numeric_contract_v1_adoption, qzc_n01_b_transcendental, pump_numeric_contract_v2,
pump_generated_boundaries_v2, pump_rule_integrity_v2, phase2_approved_golden,
pump_golden_case_0_3, golden_case_schema_0_2, golden_case_0_4_approval,
phase3_golden_and_boundaries, pump_source_pages, device_evaluator_matrix,
application_api, phase3_unified_analysis
```

新增到 CI 的模块：`test_phase3_golden_and_boundaries`（Approved Golden 0.4/0.5 与统一边界步骤）、`test_phase3_unified_analysis`（统一分析契约步骤）。

## 24. Windows Actions

WORKFLOWS 由 Phase 3 起始时已建立的长期语义保持：

```text
Windows Core   : windows-core (gating) / whitespace-check (gating) / full-suite-baseline (NON-GATING)
Pump Conformance: pump-conformance (gating)
```

本 Phase 新增的 CI 接线：

- `windows-core.yml` → Phase 2/3 步骤加入 `tests.unit.test_phase3_qt_unified`；
- `pump-conformance.yml` → Approved Golden 步骤加入 `tests.unit.test_phase3_golden_and_boundaries`；evaluator/API 步骤加入 `tests.unit.test_phase3_unified_analysis`；为该 workflow 增加 `QT_QPA_PLATFORM: offscreen`。

两个 workflow 的 YAML 均已用 PyYAML 解析验证通过。**实际 GitHub Actions 运行结果在推送后产生；本报告不预先声称 CI 结论。**

## 25. full-suite / known-regression comparison

用真实固定结果比较器（`tools/check_windows_regressions.py`，按测试 **ID 与类型**比较，不只计数）：

```text
本机实际 : 1036 run / 1029 pass / 3 fail / 1 error / 3 skip   (Python 3.12.14, 175.9s)
Phase 2 基线(source_counts): 945 run / 9 fail / 5 error / 3 skip (Windows CI 3.12.10)
gate     : PASS
new_failures / new_errors / worsened_failure_to_error / unexpected_skips
/ missing_baseline_tests / unexpected_successes / unexpected_expected_failures : 全为空
```

run 数由 945 增至 1036（Phase 3 新增 91 项测试，全部通过）。

### 25.1 基线收紧尝试与回退（重要，如实记录）

Phase 3 期间我曾按**本机**（Python 3.12.14）重放结果"收紧" `tests/baselines/windows_full_suite_known.json` 的固定 id 列表（`fail 9→3`、`error 5→1`）。**该收紧是错误的，已回退**：

- `windows-core` 的 known-regression gate 运行在 **Windows CI（Python 3.12.10）**；
- 收紧后 CI 上出现 `new_failures` / `new_errors`，gate 为 **FAIL**（run `37006790779`，job `110836841263`，"Full suite known-regression comparator (gating)" 步骤失败）；
- 原因是 10 项 CI 环境特有失败（runner 的 8.3 短名路径 `RUNNER~1` 与控制台编码差异）在本机通过，但它们**只在本机通过**，在 CI 上仍真实失败。

因此基线已**恢复为 Phase 2 真实 CI 观测到的完整列表**（9 fail / 5 error / 3 skip），并新增 `known_id_scope` 显式区分：

```text
applies_to                : Windows CI（windows-latest / Python 3.12.10）
environment_only (10 项)  : 仅 CI 环境失败；本机通过；不得从基线删除
fails_in_both (4 项)      : 本机与 CI 均失败（3 项 V4 reader/writer + 1 项 release audit 错误）
```

比较器在本机重跑：`gate PASS`、`baseline_tightening_hint: true`（该提示是**信息性**的，按 `tools/check_windows_regressions.py` 设计不使 gate 失败）。`source_counts` 仍为 Phase 2 CI 起点计数，**未改写**。

**教训**：gate 的基线必须与被 gate 的运行环境一致；不得用另一个环境的证据删减基线 id。

**既有失败仍是既有失败，未被修复也未被隐藏。** 本机与 Windows CI 的全量结果本来就不同，不得混读。

## 26. QA disposition

见 `QA_BACKLOG.md` 的 **Phase 3 统一纵向闭环处置（2026-10-02）** 一节。摘要：

- 无任何条目被虚假关闭；`CLOSE_IN_P3` 为 0 项（本 Phase 未消除遗留结构债）；
- `PARTIAL_IN_P3`：004/005/006/012/015/016/017/018/038/039/045/031 等按真实进展记录并保留 OPEN；
- `DEFER`：`json_repository` 语义、V4/Excel 相关、性能缓存等；
- `ALREADY_CLOSED_IN_P2`：034/035/036/037 未回退；
- 新增 `QA-P3-001`：遗留兼容默认日期 `date(2026,8,23)` 的 6 处源码位置登记保留。

## 27. out-of-scope verification

| 问题 | 必须的回答 | 实际 |
|---|---|---|
| Water Golden changed? | **NO** | `git status` 对 `golden/pump_water/` 为空；18 条 0.4 字节未变 |
| Chemical approved truth changed? | **NO** | 预期结论由 owner 批准值驱动；生成器与批准不符即拒绝写出 |
| Canonical changed? | **NO** | `pump.json` 未修改（SHA-256 仍为 `5D91F01B…C0F`） |
| Numeric Profile changed? | **NO** | `EQUIPEFFI_PUMP_DECIMAL50_V2` 未变 |
| platform-lock changed? | **NO** | 仍锁定 `ee5feb0cc34dbd99790500fadd0c4c932e202a20` |
| Transformer changed? | **NO** | `transformer` 代码/数据/测试未动，`scope_status` 仍 `POST_V1` |
| Excel implemented? | **NO** | 未实现任何 Excel 功能 |
| Water/Chemical separate user-facing products? | **NO** | 同一页面、同一 Use Case、同一 Workspace/Record/History |
| Unified Workspace/Record? | **YES** | 单一 `records.sqlite`，`workspace` + `record` 表 |
| Reopen recalculates? | **NO** | evaluator 被 mock 为抛错时 Reopen 仍成功（第 18 节） |
| `pump_chemical` support_status self-promoted? | **NO** | 仍为 `NOT_IN_RELEASE_SCOPE`，并有测试断言 |
| Phase 3 self-declared PASS? | **NO** | 状态为 `EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE` |

---

## 平台 / Contract 预检查（正式报告汇总）

```text
当前业务仓 SHA（基线） : 7e16418aa32ced5512e26bd70227f01a329fbdfc
platform-lock.json SHA : 锁定 ee5feb0cc34dbd99790500fadd0c4c932e202a20（未变更）
中央 Contract 版本/SHA : Architecture V2.1 FROZEN；Numeric Contract v1 FROZEN；其余 DRAFT
本任务相关 Contract    : ARCHITECTURE_V2.1_FROZEN；NUMERIC_CONTRACT_V1_FROZEN
本任务相关 ACTIVE 指南 : GUIDE_INDEX / PRODUCT_DELIVERY_POLICY_V1 /
                         STANDARD_DEVELOPMENT_GUIDE_V0.1 / UI_DESIGN_GUIDELINES_V0.1
                         （按中央当前已合并版读取；locked SHA 上不存在）
适用 MUST              : Profile 显式且一致；full-value comparison；operation order /
                         reference procedure；Domain-Application 与 UI/SQL 隔离；
                         UI State ≠ 业务 Workspace；Workspace 可变 / Record 不可变；
                         历史 Record 不漂移；Windows-first；中文优先；
                         SUPPORTED 须由 Stage D 支撑
适用 MUST NOT          : 不跟随 central main；不升级 Frozen Contract；不在 UI 复制公式/查表/
                         等级比较/边界；不泄漏内部标识；不用子串猜测类别；
                         不自行提升 support_status；不启动 Phase 4
是否发现冲突           : 是（LOCAL DEFECT：治理指针滞后，本 Phase 起始提交已校准）
冲突类型               : LOCAL DEFECT + ALLOWED PROJECT DIFFERENCE（Pump Decimal50）
是否需要修改中央 Contract : 否
是否存在相关 Standard Issue : 是
涉及的问题编号         : EQP-STD-GB19762-001
本任务是否改变既有软件解释 : 是，且已登记：as_of 产品口径 PROVISIONAL → RESOLVED
                            （软件产品决定，非发布机构官方解释）
```

---

## 停止点

```text
status                 = EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE
automatic_continuation = DISABLED
phase_3_pass_declared  = false
phase_4_started        = false
merge_authorized       = false
pump_chemical_support_status = NOT_IN_RELEASE_SCOPE（未提升）
```

独立验收应至少核对：本分支 HEAD、实际 diff、`docs/32`、18+11 条 owner 批准证据与文件 SHA-256、`golden-case-0.5` schema、统一类别路由的无子串猜测、`records.sqlite` 的非破坏性与幂等、跨进程 Workspace 恢复、Finalize 矩阵、Record 不可变性、Reopen 不重算、`as_of` 显式化、Qt 无内部标识泄漏、29/29 回放、以及第 25 节的真实全量数字与 CI 运行结果。
