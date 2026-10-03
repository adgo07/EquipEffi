# PHASE3_EXECUTION_REPORT

任务：**EquipEffi Phase 3 — GB 19762—2025 离心泵统一正式纵向闭环**
分支：`phase3/gb19762-unified-vertical-slice`
状态：**EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE**（R3：已修复 PR #11 独立验收的全部阻塞点）
停止点：**等待独立验收；不自行合并 PR、不宣布 Phase 3 PASS、不进入 Phase 4。**

> **修订记录**
>
> - **R1/R2**：初次交付（`cf22e11`…`c4543b5`）。
> - **R3（本次）**：PR #11 独立验收结论为 `PHASE_3 = BLOCKED`。本报告已按该结论修复并在
>   第 28 节逐条记录处置。**R3 之前的"READY_FOR_INDEPENDENT_ACCEPTANCE"是被验收否决的
>   状态**，不得据其认为 Phase 3 已通过。

---

## 1. start master SHA

```text
7e16418aa32ced5512e26bd70227f01a329fbdfc
```

（= 任务授权书预期值；PR #10 "Phase 2：最小正式工程底座" 的合并提交。）

## 2. commit 清单与 CI 验证点

独立验收指出 R1/R2 报告只列了 7 个缩写 SHA，而 GitHub Compare 显示 `ahead_by=9`。
**完整清单以 `git log --oneline 7e16418..HEAD` 为唯一权威**；下表为 R1/R2 部分（9 个提交）：

```text
cf22e11  统一 golden-case-0.5 schema + 11 条 pump_chemical Approved Golden + owner 批准证据
107fe7c  治理基线：Phase 2 PASS / Phase 3 IN_PROGRESS / V2.3 8.2 增量修正 / EQP-STD-GB19762-001 更正
6299cbd  P3-G01/G03：统一 Application 契约 + records.sqlite + Workspace/Record/History/Reopen + docs/32
9b7cb3c  P3-G02：统一 GB 19762 Qt 分析页 + 分析记录页
c284b16  P3-G04：29/29 Golden 回放 + 生成边界 + CI 接线 + QA 处置 + 本报告
b049205  docs：记录 final head
4ca0f84  fix(ci)：恢复 CI 作用域已知回归基线并记录该更正（见 25.1）
ae7c389  docs：记录 effective final head 与提交序列
c4543b5  docs：澄清 CI 验证点 head 与提交序列
```

R1/R2 的 CI 验证点：`4ca0f84135561954bda5bc4ace622a07bd5fb1bd` —— `Windows Core`
（windows-core / whitespace-check gating + full-suite-baseline 非 gating）与
`Pump Conformance` 全部 success。

**R1/R2 的最终 head `c4543b5a7045d9427c7ee4a397fc4bba313c2a28` 也通过了同样的四道 job。**

R3 的提交与 CI 验证点见第 28 节（R3 提交：`840a305`）。

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

---

# 28. R3：PR #11 独立验收阻塞点处置

独立验收对 R1/R2 的结论为 **`PHASE_3 = BLOCKED`**。下表逐条给出处置。**全部阻塞点已修复**，
但结论仍是 `READY_FOR_INDEPENDENT_ACCEPTANCE`——**修复本身不等于通过验收**。

| # | 验收项 | R1/R2 结论 | R3 处置 |
|---|---|---|---|
| 1 | 报告只列 7 个 SHA（Compare 为 9） | BLOCKED（报告缺陷） | 第 2 节给出完整 9 提交清单，并声明 `git log` 为唯一权威 |
| 3 | 治理状态未同步 | **BLOCKED** | `AGENTS.md`（2 处）、`HANDOFF.md`、`ROADMAP.md`、`REFERENCE_STANDARD_ROADMAP.md`（状态行 + 5 处"正在实现/尚未完成"）全部改为 `EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE`，并显式写明**不是** `PHASE_3_PASS` |
| 7 | Qt 预选清水类别 | **BLOCKED** | 首项改为"请选择产品类别…"且初始 `currentData()` 为 `None`；未选类别不计算；`test_no_category_is_preselected` 断言 |
| 8 / 12 / 15 | Qt 保存按钮是占位 | **BLOCKED** | `finalize()` 走**真实** Finalize：写草稿 → 重评价 → 绑定修订号 → 落 Record；返回 `SAVED / NO_RESULT / NOT_FINALIZABLE / STALE_RESULT / REJECTED` |
| 10 | 迁移缺"已有 Record 保留"与"回滚"证据 | **BLOCKED** | 新增迁移 002（`revision`）+ 4 项证据：旧库升级保留 Record/Workspace、001 checksum 不变、升级幂等、**失败迁移整体回滚**（不登记历史、不留半套列） |
| 11 | 跨进程证明只覆盖 chemical 且未重新装配 | **BLOCKED** | 新证明改为 **water**、**重新装配 Application**（`create_pump_analysis_service`）、**逐一核对全部 8 个输入字段** + 指纹 + revision |
| 12 | Finalize 不核对 revision，可错配 | **BLOCKED** | `finalize()` 现在核对：输入指纹、product_category、as_of、草稿 revision，且**固化结果自带的输入**而非调用方传入的输入；Qt 侧再加一层表单未改动检查 |
| 15 | 普通结果区显示 `matched_rule_id` | BLOCKED | 复合指标移入折叠的"技术详情"；普通结果区只留结论/等级/阈值/计算参数/依据 |
| 16 | 化学边界覆盖不足 | **BLOCKED** | 新增 Q=3000/3000+ε/30000（ns 固定在各档）、ns 20/60/120/210/300 各 ±ε、未覆盖的 **16 行唯一命中**、级数冲突、Δη 分支（含 `eta0_uses_delta` 直接断言） |
| 9 | 缺"新建页面本机日期默认值"测试 | 部分通过 | **已修复**：`test_new_analysis_defaults_to_local_current_date` 断言新建页面 `as_of == date.today()` 且可编辑；`test_user_edited_date_is_used_instead_of_the_default` 断言用户改动生效 |
| 21 | Stage D eligibility | 证据不足 | 仍为 `NOT_IN_RELEASE_SCOPE`，**未**提升；见下方 |

## 28.1 一个**未**修复项（如实声明，不掩盖）

**Stage D eligibility——尚不具备提交 Owner 决策的完整证据。**
`pump_chemical` 的 `support_status` 仍为 `NOT_IN_RELEASE_SCOPE`（有测试断言）。
R3 未提升它，也**不**声称它现在是 `ELIGIBLE_FOR_SUPPORT_PROMOTION`。

（原第 9 项的 `as_of` 默认值证据缺口已在 R3 补齐，不再是未修项。）

## 28.2 化学边界的两个事实更正（影响测试设计）

独立验收要求"Q=3000 / >3000 的生成边界"。实测发现两个必须尊重的业务事实：

1. **Q 分档与 ns 分档不是独立约束。** ns 由 Q、H、n 与级数派生；在 H 固定时把 Q 从 300
   增到 3000 会把 ns 推过 300，得到的是"ns 超出范围"而不是"Q 超出范围"。
   `interval_boundaries.flow_q` 只有 `5<Q≤300` 与 `Q>300`（无 Q 上界）；
   **Q>300 档的真实约束来自 ns=20~300**。因此正确的边界测试必须**反推 H 以固定 ns**。
   R3 两种情形都覆盖：固定 ns 时 Q=3000/30000 均 `SUCCESS`；固定 H 时 Q=3000 为
   `OUT_OF_STANDARD_SCOPE / 不适用`（`test_large_flow_with_constant_head_falls_out_of_scope_by_ns`）。
2. **级数与类别必须一致。** `单级` 类别要求 `stages=1`，`多级` 类别要求 `stages>1`；
   不一致返回 `INVALID_INPUT / STAGE_CATEGORY_CONFLICT`（不猜测）。
   16 行 = `单级/多级 × {5<Q≤300, Q>300} × 4 个 ns 档`。

同时更正一处 R1 测试缺陷：比转速公式中 `q_ns = Q / suction_factor / 3600`
**不除以级数**，`h_ns = H_total / stage_count`。R1 的辅助函数错误地把 Q 除以级数。

## 28.3 R3 验证（Python 3.12.14 / PySide6 6.11.2 / `QT_QPA_PLATFORM=offscreen`）

```text
Phase 3 四个模块（含新增 R3）        100 tests OK
   test_phase3_unified_analysis / test_phase3_qt_unified /
   test_phase3_golden_and_boundaries / test_phase3_r3_closure（29 项）
回归门禁集（架构/装配/phase2/entrypoint/Golden/API）  183 tests OK
compileall                          exit 0
全量                                1075 run / 1068 pass / 3 fail / 1 error / 3 skip
已知回归比较器                       gate PASS（new_failures/new_errors/worsened/missing 全为空；
                                    baseline_tightening_hint=true 为信息性提示，按设计不使 gate 失败）
```

既有失败仍是既有失败（3 项 V4 reader/writer + 1 项 release audit 错误），**未修复也未隐藏**。

## 28.4 R3 变更文件

```text
治理     AGENTS.md, HANDOFF.md, ROADMAP.md, REFERENCE_STANDARD_ROADMAP.md
契约     application/services/centrifugal_pump_analysis_service.py（指纹/修订号/一致性核对）
迁移     infrastructure/persistence/records_migrations.py（新增 002）
仓储     infrastructure/persistence/sqlite_records_repository.py（revision 读写）
UI       presentation/qt/pages/analysis.py（无预选、技术详情、真实保存、载入草稿）
         presentation/qt/app.py, presentation/qt/shell.py, composition.py（workspace_id 注入）
测试     tests/unit/test_phase3_r3_closure.py（新，29 项）
         tests/unit/test_phase3_qt_unified.py（+11 项）、tests/unit/test_phase3_unified_analysis.py（2 处随契约更新）
CI       .github/workflows/pump-conformance.yml（加入 R3 模块）
设计     docs/32（新增 10.1 迁移 002、10.2 Finalize 一致性、B 节无预选规则）
```

**未修改**：Pump evaluator、Canonical、18 条 water Golden 0.4、11 条 chemical Golden 0.5
业务真值、Numeric Profile、`platform-lock.json`、`transformer`、Excel 实现、
`pump_chemical` 的 `support_status`。

## 28.5 R3 停止点

```text
status                 = EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE
r3_blockers_fixed      = 11 / 11（另 1 项如实声明为未修复：Stage D eligibility）
phase_3_pass_declared  = false
phase_4_started        = false
merge_authorized       = false
pump_chemical_support_status = NOT_IN_RELEASE_SCOPE（未提升）
```

## 28.6 R3 CI 结果（head `97d62e2156d69004bd6bece34bd45d015e7445b6`）

```text
Pump Conformance (gating)                       -> success
Windows Core  windows-core (gating)             -> success
Windows Core  whitespace-check (gating)         -> success
Windows Core  Full suite baseline (NON-GATING)  -> success
```

**CI 全量真实数字**：`Ran 1077 tests` → `FAILED (failures=9, errors=5, skipped=3)`，
且 CI 报告的失败/错误**逐条**等于基线登记的固定 id：

```text
errors   (5): build_lock, jsonl_smoke ×2, release_audit(source_and_bundled_wheel), zipapp
failures (9): desktop_form_model, release_audit ×4, v4_reader, v4_template_resource, v4_writer ×2
```

与 Phase 2 基线（9 fail / 5 error / 3 skip）**完全一致**，因此
`new_failures / new_errors / worsened_failure_to_error / missing_baseline_tests` 全为空。

**这同时证明第 25.1 节"恢复 CI 作用域基线"是正确的**：本机全量为 1075 run / 3 fail / 1 error
（10 项 CI 环境特有失败在本机通过），若按本机数字收紧基线，CI 反而会 gate FAIL。

本机 `Ran 1075` 与 CI `Ran 1077` 相差 2 项，是环境相关的条件收集差异（与本 Phase 新增测试无关；
R1/R2 时本机 1036 与其 head CI 同样存在 2 项差异）。

PR #11 在 R3 后：`open` / `merged=false` / head `97d62e2` / 11 commits / 41 files / +7685 −118。

---

# 29. R4：第二次独立验收阻塞点处置

第二次独立验收（head `e628b5e`）结论仍为 **`PHASE_3 = BLOCKED`**，并给出 3 个关键阻塞。
R4 逐条修复。**修复不等于通过验收。**

| # | 验收项 | R3 结论 | R4 处置 |
|---|---|---|---|
| 1 | **草稿不能经用户流程保存并在重启后恢复** | BLOCKED | 新增"分析草稿"区（草稿名称 / 保存草稿 / 新建草稿 / 已有草稿列表 + 载入 / 刷新 / 删除草稿）。草稿在**分析之前**即可独立保存；`launch_qt` **不再生成随机 session id**；启动时列出全部历史草稿，用户可载入继续。删除草稿不影响正式记录 |
| 2 | **chemical 跨进程证明不完整** + 名为 restart 的测试未启动子进程 | BLOCKED | 新增 `ChemicalWorkspaceCrossProcessTests`：全新解释器**重新装配 Application**、逐一核对**全部 8 个输入字段** + 指纹 + revision，并在子进程内真实评价（断言 `SUCCESS / 2级 / grade=2`）。原误导性测试更名为 `..._in_the_same_process` 并明确声明不声称跨进程；`test_phase3_unified_analysis` 中原名 `..._separate_process` 但实际未起子进程的测试更名为 `..._across_a_fresh_connection`，同时补齐全部字段断言 |
| 3 | **ns 生成样本不能证明区间归属** | BLOCKED | 端点/±ε 全部改为**断言具体规则行**：期望档位由标准开闭语义显式给出，规则行由 `NS_RULE_TABLE` 推出，并用 `_canonical_band_index` 独立复核。删除"允许 SUCCESS 或 OOS"的模糊断言。新增 Canonical 开闭标志断言与区间判定谓词直测 |
| 12 | EXECUTION_ERROR 矩阵证明不足 | 部分 | 保留：`FINALIZABLE_STATUSES` 不含 `INVALID_INPUT`/`EXECUTION_ERROR`，且构造的 `EXECUTION_ERROR` 结果被拒绝。**仍非真实 evaluator 异常链**，如实声明 |
| 14 / 15 | 历史页普通详情仍显示内部字段名 / rule ID | 部分 | 记录页拆为"记录详情"（业务语言，含中文参数名）与折叠的"技术详情"（命中规则、规则集、数据包、数值配置、输入指纹、修订号）。新增测试断言普通详情不含 `GB19762-T3-01` / `pump_water` / `EQUIPEFFI_PUMP_DECIMAL50_V2`，且技术详情仍可审计 |

## 29.1 ns 边界的一条重要方法论更正

R3 的 ns 边界测试是**无效证据**，验收指出的问题成立且比表面更严重：

- 用 float 反推 H 再截为 10 位小数，会产生约 1e-10 量级的 ns 偏差——**远大于**测试声称的
  `±1e-4` 意图，端点样本实际上落在"端点附近"而不是端点；
- R4 改为对**完整精度字符串**（`.50f`）二分搜索，实测可把实际 ns 收敛到目标端点约
  **2e-25** 以内；
- 但即便如此，**精确命中端点仍不可达**（HBEP 字符串与 Decimal 计算链限制）。若在端点
  附近断言"某一侧"，样本会因 2e-25 的方向不确定而变成噪声。因此 R4 的样本设计是：
  - **±ε 样本**（ε=1e-15，比可达精度大 10 个数量级）：断言**确定的**目标档位；
  - **端点探针**（±5e-16）：同样断言确定的档位；
  - 断言前先检查 `|actual - target| <= 1e-24`，精度不足则**测试失败并说明样本无效**，
    绝不静默放宽。

## 29.2 R4 验证（Python 3.12.14 / PySide6 6.11.2 / `QT_QPA_PLATFORM=offscreen`）

```text
Phase 3 四个模块                   112 tests OK
  test_phase3_qt_unified          33（新增草稿用户流程 7 项 + 历史技术分层 1 项）
  test_phase3_r3_closure          39（化学跨进程 1 项 + ns 端点/±ε 重写）
门禁集（架构/元数据/装配/设置/日志/Qt/批准 Golden/API/entrypoint/矩阵）  578 tests OK
compileall                         exit 0
全量                               1087 run / 1080 pass / 3 fail / 1 error / 3 skip
已知回归比较器                      gate PASS（无新增/恶化/缺失）
```

既有失败仍是既有失败（3 项 V4 reader/writer + 1 项 release audit 错误），**未修复也未隐藏**。

## 29.3 R4 变更文件

```text
UI       presentation/qt/pages/analysis.py（草稿区：保存/新建/列表/载入/刷新/删除；finalize 前核对表单）
         presentation/qt/pages/records.py（业务详情与技术详情分层）
         composition.py（移除随机 session id）
契约     application/services/centrifugal_pump_analysis_service.py（delete_workspace）
设计     docs/32（新增 7.1 草稿用户流程与双 Profile 跨进程 Gate）
测试     tests/unit/test_phase3_qt_unified.py（草稿用户流程 + 历史技术分层）
         tests/unit/test_phase3_r3_closure.py（化学跨进程 + ns 端点/±ε 重写）
         tests/unit/test_phase3_unified_analysis.py（测试更名，消除"跨进程"误导）
```

**未修改**：Pump evaluator、Canonical、18 条 water Golden 0.4、11 条 chemical Golden 0.5
业务真值、Numeric Profile、`platform-lock.json`、`transformer`、Excel 实现、
`pump_chemical` 的 `support_status`。

## 29.4 R4 CI 结果（head `e000822d101887e0adc126e8ef24d1432265bdff`）

```text
Pump Conformance (gating)                       -> success
Windows Core  windows-core (gating)             -> success
Windows Core  whitespace-check (gating)         -> success
Windows Core  Full suite baseline (NON-GATING)  -> success
```

**CI 全量真实数字**：`Ran 1087 tests` → `FAILED (failures=9, errors=5, skipped=3)`，
仍与 Phase 2 基线登记的固定 id 一致（`KNOWN BASELINE FAILURES PRESERVED`）。

值得注意：R4 之后 **CI 与本机的 run 数一致（两者均为 1087）**——R1/R3 时存在的 2 项
环境差异在本轮采样中未复现。这不改变基线策略：基线仍按 CI 作用域维护，
`baseline_tightening_hint` 仍可能出现，且按设计不使 gate 失败。

PR #11 在 R4 后：`open` / `merged=false` / head `e000822` / 13 commits / 41 files / +8374 −118。

## 29.5 R4 停止点

```text
status                 = EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE
r4_blockers_fixed      = 3 / 3
known_residual_gaps    = EXECUTION_ERROR 仍为构造结果而非真实 evaluator 异常链（如实声明）
phase_3_pass_declared  = false
phase_4_started        = false
merge_authorized       = false
pump_chemical_support_status = NOT_IN_RELEASE_SCOPE（未提升）
```

---

# 30. R1 — 独立验收确认的 5 个 blocker 修复

独立验收对 PR #11 的结论为 **`PHASE_3_BLOCKED`**，确认 5 个 blocker。本节逐条记录
root cause、修复方式、新增负例与证据。

## 30.1 B1 — Finalize 状态校验（不能只信 `result.finalizable`）

**Root cause**：`finalize()` 只检查 `if not result.finalizable: raise`。`finalizable` 是
**结果对象自报**的字段，而 `evaluation_status` 才是权威状态。二者一旦不一致（伪造、
反序列化、未来改动引入的 bug），自报字段就能单独决定"能否成为正式记录"。

**修复方式**：`finalize()` 改为**独立按状态白名单判断**，并在矛盾时 fail closed：

```text
允许：SUCCESS / OUT_OF_STANDARD_SCOPE / INSUFFICIENT_DATA
拒绝：INVALID_INPUT / EXECUTION_ERROR / None / 未知状态
矛盾（finalizable 与 evaluation_status 不一致）→ 拒绝
```

判定顺序为：白名单 → 自报字段一致性 → 输入指纹 → 类别/日期一致 → Canonical hash → 草稿 revision。

**新增负例**（`tests/unit/test_phase3_r1_blockers.py::FinalizeStatusWhitelistTests`）：

| 负例 | 期望 |
|---|---|
| `INVALID_INPUT` + `finalizable=True` | 拒绝，Record 不增加 |
| `EXECUTION_ERROR` + `finalizable=True` | 拒绝，Record 不增加 |
| 未知状态 + `finalizable=True` | 拒绝，Record 不增加 |
| `None` + `finalizable=True` | 拒绝，Record 不增加 |
| `SUCCESS` + `finalizable=False` | 拒绝，Record 不增加 |

另有正例：三个白名单状态均可正常固化。

## 30.2 B2 — Qt stale result

**Root cause**：`evaluate()` 先调用 `service.evaluate()`，成功后才写 `_last_request` /
`_last_result`。若本次分析失败或抛异常，**旧的 SUCCESS 结果仍留在页面上**，用户点
"保存为正式记录"就会把旧结果当成新输入固化。

**修复方式**：`evaluate()` **开头**即清空 `_last_request` / `_last_result` 并禁用 Finalize；
`service.evaluate()` 包在 `try/except` 中，任何异常都走 `_show_error` 且不留下旧结果。

**新增负例**（`QtStaleResultTests`，water 与 chemical 各一组）：

- 成功分析 → 改成非法输入再分析 → 旧 SUCCESS 作废，`finalize()` 返回 `NOT_FINALIZABLE`，Record 数为 0；
- 成功分析 → evaluator 抛异常 → `finalize()` 返回 `NO_RESULT`，Record 数为 0；
- 分析失败后 `_last_request` / `_last_result` 均为 `None`，Finalize 按钮禁用。

## 30.3 B3 — Canonical hash

**Root cause**：`pump.json` 的 `pack_hash` **为空**。`JsonStandardRepository.get_pack()`
只注入 `pack_id` / `device_type` / `status` / `data_version` / `source_file`，从未计算内容
哈希。因此 Record 的 `canonical_package_hash` 一直是空串，正式记录无法证明自己用的是哪份
Canonical 内容。

**修复方式**：在 `get_pack()` 注入由**实际 Canonical 源文件**计算的 SHA-256，使用仓库既有
文本哈希规则（**UTF-8、CRLF→LF 后 SHA-256、大写十六进制**），与
`tools/validate_phase1_contracts.py::_sha256(normalize_repository_text=True)` 及
`tools/build_phase3_chemical_golden.py::canonical_file_sha256` 一致：

```text
repository_text_sha256(data) = sha256(data.replace(b"\r\n", b"\n")).hexdigest().upper()
pack_hash = repository_text_sha256(pump.json 的实际字节)
```

- **未修改 `pump.json` 内容**；
- **未用 commit SHA 冒充**内容哈希；
- 包以 zip 资源导入时从包资源读取字节，同一哈希规则；读取失败**明确报错**，不返回空值；
- `finalize()` 增加第 4 道检查：**实际执行了具体 ruleset 的结果若 hash 缺失即拒绝**。

**证据**：实测 `pack_hash` = `5D91F01B1C5F26DC4F364A3156C4E974B159FA1005BD840489C0BC3465C18C0F`，
与独立对 `pump.json` 计算的值一致；water 与 chemical 两个 Record 的
`canonical_package_hash` 均非空且等于该值；空 `pack_hash` 的结果被拒绝且 Record 不增加。

## 30.4 B4 — 技术详情默认折叠

**Root cause**：用 `QToolBox.setCurrentIndex(-1)` 表达"默认折叠"。该控件会在某些平台上
自行选中第一页，且"折叠"只是当前页为空——内容控件本身仍参与布局，并非真正隐藏。

**修复方式**：新增 `src/equipeffi/presentation/qt/widgets/collapsible.py::CollapsibleSection`：
显式切换按钮 + `content` 容器，构造后 `setVisible(False)`。分析页与记录页均改用它。

**证据**（`CollapsibleTechnicalDetailTests`）：`show()` + `processEvents()` 后
`content.isVisible()` 仍为 `False`；点击一次变为 `True`，再点击回到 `False`；普通默认页面
文本不含 `pump_water` / `pump_chemical` / `rule_id` / `GB19762-T3-01` /
`EQUIPEFFI_PUMP_DECIMAL50_V2`。

## 30.5 B5 — 治理状态一致性

**Root cause**：`TASK_STATE.md` 写 `EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE`，
而 `AGENTS.md` / `HANDOFF.md` / `ROADMAP.md` / `REFERENCE_STANDARD_ROADMAP.md` 仍写
`Phase 3 = IN_PROGRESS` 或含糊的"尚未经独立验收"，与真实状态（已验收且被判 BLOCKED）矛盾。

**修复方式**：五份文件统一为四段式表达：

```text
Phase 3 implementation         = EXECUTION_COMPLETE
Phase 3 independent acceptance = PHASE_3_BLOCKED
Phase 3 R1 status              = READY_FOR_INDEPENDENT_RE_ACCEPTANCE
（不得写 PHASE_3_PASS / PHASE_4_READY）
```

`TASK_STATE.md` 新增 `previous_acceptance: PHASE_3_BLOCKED` 与 `r1_fixes` 块；
`REFERENCE_STANDARD_ROADMAP.md` 第 4 节相关行同步。

## 30.6 新增/变更文件

```text
新增  src/equipeffi/presentation/qt/widgets/__init__.py
新增  src/equipeffi/presentation/qt/widgets/collapsible.py
新增  tests/unit/test_phase3_r1_blockers.py（B1-B4 对抗性证据）
变更  application/services/centrifugal_pump_analysis_service.py（B1 白名单 + B3 hash 门禁）
变更  infrastructure/standards/json_repository.py（B3 pack_hash 注入与哈希助手）
变更  presentation/qt/pages/analysis.py（B2 stale result + B4 折叠）
变更  presentation/qt/pages/records.py（B4 折叠）
变更  AGENTS.md / HANDOFF.md / ROADMAP.md / REFERENCE_STANDARD_ROADMAP.md / TASK_STATE.md（B5）
变更  .github/workflows/windows-core.yml、pump-conformance.yml（R1 模块接入 Required CI）
```

**未修改**：Golden 真值、Canonical 业务数据（`pump.json` 内容未改）、Numeric Profile、
`platform-lock.json`、known baseline（未放宽）、`pump_chemical` 的 `support_status`。

## 30.7 R1 本地验证

Python 3.12.14，定向驱动已完成的验证：

```text
架构边界门禁（含新增 widgets 子包）   11 tests OK
B1 Finalize 白名单 fail-closed        直接驱动 8/8：5 个伪造/矛盾负例全部拒绝
                                      且 Record 不增加；2 个白名单正例正常固化
B3 Canonical hash                     pack_hash == 独立计算值；
                                      water/chemical Record hash 非空且一致；
                                      空 hash 被拒绝
B4 折叠                               控件级：默认 hidden、show+processEvents 后仍 hidden、
                                      点击展开/收起；分析页与记录页均成立
```

**本机无法完整运行临时目录相关测试**（如实声明）：本会话的 DSH 文件沙箱把
`tempfile.mkdtemp()` 创建的目录设为仅创建者可写，受限令牌随后无法在其中读写或 `chmod`，
导致所有使用 `TemporaryDirectory` 的用例在 `setUp`/`tearDown` 报 `PermissionError`。
这是**沙箱环境限制，不是仓库缺陷**（CI runner 不受影响），因此 B1/B2/B3 的完整套件
以 CI 结果为准。

## 30.8 R1 CI 结果

**R1 代码提交**：`1f8c5a8`（5 个 blocker 的全部代码与测试改动）。
**final head**：**包含本节的提交**（其后仅追加文档更正，不再改代码）。

```text
权威读法：git rev-parse origin/phase3/gb19762-unified-vertical-slice
         git log --oneline 7e16418..HEAD     # 共 18 个提交
```

说明：本报告无法在不产生自引用循环的前提下写出"包含自身的那个提交"的 SHA，因此以
"包含本节的提交"为末次文档提交标识；**R1 的代码改动恒为 `1f8c5a8`**。

**CI 结果：本会话未能核验，如实声明。** 推送完成后，本会话到 `api.github.com` 的网络连接
持续失败（`The SSL connection could not be established`，跨多次共 25+ 次重试、约 10 分钟），
因此**无法读取 `Windows Core` 与 `Pump Conformance` 的运行结论与全量数字**。

本报告**不预填 CI 结论**。请以 PR #11 当前 head 的实际 Actions 运行结果为准；若
`Windows Core (gating)` 或 `Pump Conformance (gating)` 失败，本节即为未完成证据，
需要复验方据此退回。

已知的本地证据见 30.7；其中**临时目录相关用例在本会话沙箱内无法运行**，
这些用例（B1 的 DB 侧负例、B2 全部、B3 的 Record 侧、record 迁移相关）**完全依赖 CI**。

## 30.9 R1 停止点

```text
status                 = EXECUTION_COMPLETE
previous_acceptance    = PHASE_3_BLOCKED
r1_status              = READY_FOR_INDEPENDENT_RE_ACCEPTANCE
r1_blockers_fixed      = 5 / 5
phase_3_pass_declared  = false
phase_4_started        = false
merge_authorized       = false
pump_chemical_support_status = NOT_IN_RELEASE_SCOPE（未提升）
```
