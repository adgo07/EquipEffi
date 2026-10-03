# PHASE4_EXECUTION_REPORT

Phase 4 — GB19762 真实样板后的最小生命周期通用化。

## 0. 平台预检查

| 项 | 值 |
|---|---|
| 仓库 | `https://github.com/adgo07/EquipEffi.git` |
| Base | `master@87d9ef1bf32fb3f765d4f8ef3f97aa222913152a`（= Phase 3 的 PR #11 merge） |
| 分支 | `phase4/minimal-lifecycle-generalization` |
| locked central SHA | `ee5feb0cc34dbd99790500fadd0c4c932e202a20`（未变更） |
| 相关 Frozen Contract | Architecture `V2.1 FROZEN`、Numeric Contract `v1 FROZEN` |
| 适用 MUST / MUST NOT | 依赖方向（Application 不得依赖 Infrastructure/Presentation；Infrastructure 不得依赖具体产品模块）；Numeric Profile 不得全局化 |
| 冲突分类 | `LOCAL DEFECT`（infrastructure 反向依赖具体产品 service）→ 本次修复。**无** `CENTRAL CONTRACT GAP` |
| 是否需改中央 Contract | 否。**本任务不涉及中央公共 Contract。** |

**Standard Issue**：不存在与本任务相关的新标准问题；不改变任何既有软件解释。
`EQP-STD-GB19762-001` 的 R3 补充决定（`as_of` 不是标准执行门禁）在 Phase 4 未被改动。

## 1. 目标与证据口径

唯一目标：把 Phase 3 已真实证明属于公共工程结构、但当时仍寄生在
`centrifugal_pump_analysis_service.py` 中的生命周期能力抽离到设备无关的
Application 生命周期模块，同时保证 GB 19762 的：

```text
业务行为      零漂移
数据库形态    零漂移（schema / migration / schema_version 完全未变）
历史记录语义  零漂移（Record 不可变、Reopen 不重算、指纹逐字节一致）
```

**证据口径（不得误述）**：本阶段仍是**一个 GB19762 产品级 E2E 样板，其中有
`water` + `chemical` 两个真实内部 rule profile**。
**不得**表述为"已经有两个独立设备 / 标准 E2E 样板"。

## 2. G00 — Phase 3 治理收口

| 记录项 | 值 |
|---|---|
| Phase 3 | `PHASE_3_PASS` |
| accepted head | `728680dabf7b18e47ce9a5a23b296e405bc644a8` |
| PR #11 merge | `87d9ef1bf32fb3f765d4f8ef3f97aa222913152a` |
| Phase 4 | `IN_PROGRESS` |

- 新增**极简** Phase 3 Acceptance Record：`docs/phase3_acceptance_record.md`，
  只记录 `phase` / `verdict` / `acceptance date` / `accepted head` / `PR`+`merge SHA` /
  independent acceptance 来源说明；**不复制**验收报告正文，不建立重治理流程。
  该轻量落档方式供后续每个 Phase 沿用。
- `pump_chemical` 支持状态治理同步：`support_status` 仍为 `NOT_IN_RELEASE_SCOPE`，
  `target_support_status = SUPPORTED`，`standard_maturity = READY_FOR_IMPLEMENTATION`；
  Owner 业务真值批准（11/11）已记录，剩余正式 blocker 仅为中央
  `STANDARD_DEVELOPMENT_GUIDE_V0.1` Stage D 独立验收。
  **未**提升为 `SUPPORTED`（Phase 4 无此授权）。
- ADR-002 lineage / audit 登记：`QA_BACKLOG.md` 新增 `QA-P4-001`，
  状态 `REGISTERED_DEVIATION`，`target_phase = Phase 7`。
  ADR-002 要求 Finalize 时把输入快照、结果快照、数据引用、规则引用、
  lineage 与 audit event 在**同一事务**写入；当前只实现输入/结果/引用快照与不可变追加，
  **没有** lineage 表与 audit event。Phase 4 **不实现** lineage / audit / reproduce，
  且**不因此修改** `records.sqlite`。

治理状态文件更新：`AGENTS.md`、`HANDOFF.md`、`ROADMAP.md`、
`REFERENCE_STANDARD_ROADMAP.md`、`TASK_STATE.md`。

## 3. G01 — 生命周期契约抽离

新增设备无关的 Application 生命周期模块：

```text
src/equipeffi/application/lifecycle/
  __init__.py   契约导出
  models.py     WorkspaceSnapshot / RecordSnapshot / 稳定指纹算法
  ports.py      WorkspaceRepository / RecordRepository Protocol
  errors.py     LifecycleError / AnalysisError / RecordConflictError / LifecyclePersistenceError
```

从 `centrifugal_pump_analysis_service.py` **迁出**（该文件 1013 → 约 955 行）：

```text
WorkspaceSnapshot
RecordSnapshot
WorkspaceRepository
RecordRepository
（以及 _opt 取值规则 → normalize_fingerprint_value）
```

**继续留在产品模块**（未被通用化）：

```text
PumpAnalysisRequest / PumpAnalysisResult
PUMP_CATEGORIES 与类别目录
resolve_rule_profile / water·chemical routing
build_pump_evaluator
threshold / trace / grade
GB19762 专属 provenance
Finalize 的具体业务允许状态政策（FINALIZABLE_STATUSES）
```

**未创建**（Phase 4 明确禁止）：`GenericAnalysisService` / `UniversalEngine` /
通用 evaluator 基类 / 插件式生命周期框架 / 通用动态表单引擎。

## 4. G02 — fingerprint 单一事实源

Phase 3 中 `PumpAnalysisRequest.request_fingerprint()` 与
`WorkspaceSnapshot.request_fingerprint()` **各自维护一份**相同的业务字段指纹逻辑。

收敛结果：

| 关注点 | 唯一来源 |
|---|---|
| 指纹算法（JSON 排序 + 紧凑分隔符 + UTF-8 + SHA-256） | `lifecycle.models.stable_fingerprint` |
| 取值归一化（`None` → `"None"`） | `lifecycle.models.normalize_fingerprint_value` |
| **业务字段集合** | `centrifugal_pump_analysis_service.PUMP_FINGERPRINT_KEYS`（仅此一处） |

生命周期模型**不知道** `QBEP` / `HBEP` / `suction` / `stages`：它只接受调用方声明的
**不透明键**，并由 `business_key_values(business_keys)` 取值。测试用源码级断言锁定
生命周期包中不出现任何泵专属标识。

**附带发现并修复**：`PumpAnalysisRequest.raw_values()` 原本**硬编码了第二份**
相同字段元组字面量。现已改为遍历 `PUMP_FINGERPRINT_KEYS`，使"业务字段集合只声明一次"
真正成立（否则该门禁只是形式）。

**跨进程恢复**：`WorkspaceSnapshot` 从 `records.sqlite` 读回后必须能自行重建指纹，
而 Phase 4 **不允许新增列 / 新增迁移**，因此字段清单只能来自进程内登记
（`register_business_keys`，由产品模块在模块级调用一次）。
生命周期模型仍不认识字段名——注册点存的是调用方声明的不透明键。
这是为满足"不新增数据库列"而做的**显式且已文档化**的取舍，不是隐藏耦合。

**数据库**：未新增 `input_fingerprint` 列；未新增 migration；未修改既有 checksum。

**向后兼容**：新增 `Phase3WorkspaceFixtureCompatibilityTests`，用 Phase 3 形态的行
（直接 INSERT 到真实 migration 建出的表）走 `load → rebuild PumpAnalysisRequest →
evaluate → finalize`，并断言指纹与 Phase 3 逐字节一致；另断言当前 migration 建出的
`workspace` 列与 Phase 3 建表语句**逐列一致**、`schema_version` 仍为 2。

## 5. G03 — Persistence 解耦与最小错误契约

`sqlite_records_repository.py` **不再 import** `centrifugal_pump_analysis_service`：

```text
- from ...application.services.centrifugal_pump_analysis_service import (...)
+ from ...application.lifecycle import (
+     LifecyclePersistenceError, RecordConflictError, RecordSnapshot, WorkspaceSnapshot)
```

**最小错误语义**（未建立复杂继承树）：

```text
LifecycleError                 生命周期层根错误（不继承 ValueError）
└── AnalysisError              = LifecycleError + ValueError（保留 Phase 3 名称与语义）
    └── RecordConflictError    重复 record_id，记录不可变
LifecyclePersistenceError      持久化失败
```

- `AnalysisError` 同时继承 `ValueError`，因此 Phase 3 既有调用方与测试**无需改动**。
- `RecordConflictError` 继承 `AnalysisError`，按 `AnalysisError` 捕获的既有代码继续成立，
  同时新增了更精确的语义。
- **未**新增 `WorkspaceConflictError`：当前没有真实需要（Workspace 是可变的，
  冲突由 `revision` 机制在 Finalize 判定，不需要新异常）。

**持久化根因保留**：新增 `_persistence(operation, database)` 上下文管理器，
把 `sqlite3.Error` 转成 `LifecyclePersistenceError` 并**始终 `raise ... from error`**，
`__cause__` 与 traceback 不丢失。测试断言未建库时 `save_workspace` / `append_record`
抛出的错误 `__cause__` 是 `sqlite3.Error`——**不允许**失败后让调用方以为保存成功。

**新增架构门禁**（`InfrastructureDecouplingGateTests`，AST 级）：

```text
infrastructure 不得依赖任何具体 *_analysis_service 产品模块
persistence 仓储的 application 依赖只允许 application.lifecycle
lifecycle 包不得依赖 infrastructure / presentation / domain / sqlite3 / PySide6
```

## 6. G04 — GB19762 接回与零漂移

`CentrifugalPumpAnalysisService` 现在消费新的生命周期契约（经 `..lifecycle` 导入
快照模型与端口），但其**业务侧完全未改**：

- `build_pump_evaluator` 仍为模块级函数，测试接缝保持不变；
- `Reopen` 仍**完全依赖不可变 Record 快照**，不重算；
- 阈值 / trace / grade / provenance / Finalize 业务允许状态政策未动。

**通用化的边界（刻意为之）**：只通用化 Finalize 的**机制**——
`revision`、`fingerprint`、不可变追加、冲突处理、错误语义、端口形状。
**未**把泵的 `SUCCESS` / `OUT_OF_STANDARD_SCOPE` / `INSUFFICIENT_DATA` 白名单
升级为设备级全局规则；`FINALIZABLE_STATUSES` 仍留在泵产品模块内。

## 7. 数据库硬边界核验

| 约束 | 实际 |
|---|---|
| 不新增 records migration | 已满足（`records_migrations.py` 未被修改） |
| 不修改已有 migration checksum | 已满足（文件零改动） |
| `records.sqlite` `schema_version` 保持 2 | 已满足（测试断言 `MAX(schema_version) == 2`） |
| Phase 3 已创建数据库可直接读取 | 已满足（Phase 3 形态 fixture 测试） |
| 不新增 lineage / audit 表 | 已满足 |
| 不做破坏性迁移 | 已满足 |

## 8. 测试与验证

### 8.1 新增测试

`tests/unit/test_phase4_lifecycle_generalization.py`（16 tests / 5 类）：

```text
InfrastructureDecouplingGateTests               3  架构门禁（AST 级）
WorkspaceSnapshotIsDeviceNeutralTests           3  生命周期模型设备无关 + 字段集合唯一
FingerprintSingleSourceTests                    4  单一算法 / 单一业务键 / Phase 3 逐字节一致
Phase3WorkspaceFixtureCompatibilityTests        3  旧 fixture load→rebuild→evaluate→finalize
PersistenceRootCauseTests                       3  根因保留 + RecordConflictError
```

### 8.2 Phase 3 关键测试：**未修改任何业务期望**

```text
git diff --name-only -- tests   （相对 base）
```

**Phase 3 既有测试文件全部零改动**，也**无需**任何机械性导入路径迁移——
因为没有任何 Phase 3 测试从 `centrifugal_pump_analysis_service` 导入被迁出的
快照模型（它们只从 `infrastructure` 导入 SQLite 仓储实现）。
本次唯一新增的测试文件即 8.1。

### 8.3 本地实际结果

受影响的 Phase 3 关键套件（全部 0 fail / 0 error）：

```text
test_phase3_unified_analysis         34
test_phase3_r1_blockers              20
test_phase3_r2_final_closure         11
test_phase3_r3_as_of_lifecycle       18
test_phase3_r3_closure               31
test_phase3_qt_unified               33
test_phase3_golden_and_boundaries    14   （29/29 Approved Golden 回放）
test_architecture_boundaries         11
test_composition                      3
test_phase4_lifecycle_generalization 16
```

其他门禁：

```text
validator（--skip-external-evidence --negative-probe）  cases=25 errors=0
                                                         negative_probe_errors=3
compileall -q src tools tests                            exit 0
git diff --check                                         clean
全量 unittest                                            1152 run / 1145 pass
                                                         3 fail / 1 error / 3 skip
known-regression comparator                              gate=PASS
                                                         new_failures=0 new_errors=0
                                                         worsened=0 missing=0
```

既有失败仍是既有失败（3 项 V4 reader/writer + 1 项 release audit 错误），
**未修复也未隐藏，且未把任何新失败加入 known baseline**。

## 9. Phase 4 Exit Gate 逐项

| Exit Gate 条件 | 结果 |
|---|---|
| lifecycle models / ports 已与 pump service 解耦 | PASS |
| infrastructure 不再依赖具体 pump service | PASS（AST 门禁 + 源码零引用） |
| fingerprint 只剩单一算法和单一业务键来源 | PASS（并修掉了 `raw_values()` 的第二份字面量） |
| 旧 Workspace fixture 兼容 | PASS |
| records schema / migration 完全未变 | PASS |
| GB19762 业务结果零漂移 | PASS（29/29 Golden + 受影响套件全绿 + 未改任何测试期望） |
| Golden / Canonical / Numeric / platform lock 零漂移 | PASS（`specs/`、`platform-lock.json` 未修改） |
| Phase 5/6/7/8 职责未被提前实现 | PASS（未接入其他设备 / 未新增标准 / 未做 Excel / 未做 lineage·audit·reproduce / 未做 qzpack / 未建 Product Shell / 未升级 Frozen Contract） |
| Required CI 无新增未知 regression | 见 §10 |

## 10. 状态

```text
Phase 4 implementation = EXECUTION_COMPLETE
READY_FOR_INDEPENDENT_ACCEPTANCE
```

**不合并 PR。不自宣 `PHASE_4_PASS`。不进入 Phase 5。**
