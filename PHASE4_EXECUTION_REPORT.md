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
而 Phase 4 **不允许新增列 / 新增迁移**。

### 4.1 独立验收阻塞的修复（`PHASE_4_BLOCKED`，head `855f259`）

独立验收在 head `855f259` 上复现的阻塞是**真实缺陷**，本轮已修复。

**缺陷**：首版实现用**进程内全局注册**（`register_business_keys`）让生命周期层
在跨进程恢复时取得业务键集合。结果是：

```text
只 import Repository 的新进程（未 import 泵 service）
  → 注册为空 → 旧 Workspace 无参指纹漂移
  → 不同业务输入（efficiency 90 / 70）得到**相同**指纹
  → 只有 import 泵 service 后指纹才恢复
```

即：源码 import 已解耦，**运行时指纹仍耦合**，且是全局可变状态。
验收复现结果（修复前）：

```text
W-water    expected e23ffa0d…  actual 23833c30…   DRIFT
W-chem     expected 36f260c0…  actual 5dabec10…   DRIFT
W-water-b  expected 60a1ed8c…  actual 23833c30…   DRIFT（与 W-water 碰撞）
distinct fingerprints = 2（应为 3）
```

**修复**：彻底移除进程内注册，改为**自描述持久化 + 快照内确定性回退**：

1. 业务键集合作为保留元数据键 `_business_keys` 随快照写入**既有的
   `payload_json` 列**——不新增列、不新增迁移、不依赖导入顺序、无全局状态；
2. 无参 `request_fingerprint()` 优先读该元数据；
3. Phase 4 之前、未携带元数据的历史快照，回退为"载荷中除生命周期级登记键
   （`project_name` / `equipment_no` / `product_type`）以外的全部键"——
   该规则**只由快照自身内容决定**，因此同一快照在任意进程、任意导入顺序下
   得到同一指纹。历史快照里"当时为空的字段"本就未写入载荷，
   故回退值与写入当次 `PumpAnalysisRequest.request_fingerprint()` 一致。

**修复后复现结果**：

```text
W-water    OK   e23ffa0dc130b4b8d0a8d28fd3eb9a8c9c66bb47338e325f86e112670c6513d3
W-chem     OK   36f260c0936c2616a575631abc47f65902c7865f839df644854f72f4cdb169de
W-water-b  OK   60a1ed8cfa88209769faadf63fbd080b2fee3ed8a0c7299894fd906fd8395458
distinct fingerprints = 3 ✓
（子进程断言泵 service 未被导入）
```

**真实 base 数据库兼容验证**（`tools/verify_phase4_fingerprint_compat.py`）：
用 **base 提交 `87d9ef1b` 的代码**写出真实 `records.sqlite`（其 workspace 行
**不含**元数据），再用当前代码走完整链路，结果 **全部一致、无漂移**：

```text
W-base-water  base=e23ffa0d…  无参指纹一致  重建输入一致  Finalize Record 一致  Reopen SUCCESS/1级
W-base-chem   base=36f260c0…  无参指纹一致  重建输入一致  Finalize Record 一致  Reopen SUCCESS/2级
更新一次草稿后带上 _business_keys，指纹仍与 base 一致
```

**新增回归测试**：`tests/unit/test_phase4_fingerprint_decoupling.py`（8 tests）
把上述复现固定下来：只加载 Repository 的无参指纹不漂移、不同业务输入不碰撞、
业务键随快照持久化、旧快照由快照自身确定性推出、回退跨进程一致、
生命周期层不存在全局可变注册点。

> 说明：业务键集合因此同时存在于“持久化元数据”与产品模块常量中，
> 但两者由同一处常量写入（`_pump_payload()` 使用 `PUMP_FINGERPRINT_KEYS`），
> 且元数据是**数据**而非第二处声明。

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

`tests/unit/test_phase4_lifecycle_generalization.py`（22 tests / 5 类）：

```text
InfrastructureDecouplingGateTests               3  架构门禁（AST 级）
WorkspaceSnapshotIsDeviceNeutralTests           3  生命周期模型设备无关 + 字段集合唯一
FingerprintSingleSourceTests                    4  单一算法 / 单一业务键 / Phase 3 逐字节一致
Phase3WorkspaceFixtureCompatibilityTests        3  旧 fixture load→rebuild→evaluate→finalize
PersistenceRootCauseTests                       3  根因保留 + RecordConflictError
```

`tests/unit/test_phase4_fingerprint_decoupling.py`（8 tests）——
`PHASE_4_BLOCKED` 阻塞的回归：

```text
FingerprintImportDecouplingTests
  只加载 Repository 的无参指纹不漂移（子进程断言泵 service 未导入）
  不同业务输入（efficiency 90 / 70）不得碰撞
  业务键集合随快照持久化，而非进程内注册
  无元数据旧快照由快照自身确定性推出，且等于写入当次指纹
  真实旧库路径仍能 evaluate → finalize → Reopen
  回退分支跨进程一致
  生命周期级登记键必须设备无关
  生命周期层不存在全局可变注册点
```

### 8.1.1 新增验证工具

`tools/verify_phase4_fingerprint_compat.py`——用 **base 提交代码**写真实数据库、
再用当前代码走完整 Use Case 的兼容验证入口（`git worktree` 临时检出，运行后清理）。
退出码 0 表示无漂移。

### 8.2 Phase 3 关键测试：**未修改任何业务期望**

```text
git diff --name-only -- tests   （相对 base）
```

**Phase 3 既有测试文件全部零改动**，也**无需**任何机械性导入路径迁移——
因为没有任何 Phase 3 测试从 `centrifugal_pump_analysis_service` 导入被迁出的
快照模型（它们只从 `infrastructure` 导入 SQLite 仓储实现）。
本次唯一新增的测试文件即 8.1。

### 8.3 本地实际结果

受影响套件（全部 0 fail / 0 error）：

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
test_phase4_lifecycle_generalization 22
test_phase4_fingerprint_decoupling    8
```

其他门禁：

```text
validator（--skip-external-evidence --negative-probe）  cases=25 errors=0
                                                         negative_probe_errors=3
tools/verify_phase4_fingerprint_compat.py                exit 0（base 数据库零漂移）
compileall -q src tools tests                            exit 0
git diff --check                                         clean
全量 unittest                                            1166 run / 1159 pass
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

## 10. GitHub 交付

| 项 | 值 |
|---|---|
| Repo | `https://github.com/adgo07/EquipEffi.git` |
| Base SHA | `87d9ef1bf32fb3f765d4f8ef3f97aa222913152a`（master） |
| Branch | `phase4/minimal-lifecycle-generalization` |
| PR | **#12** — https://github.com/adgo07/EquipEffi/pull/12 |
| final Head SHA | 见文末「Final Head」一节（本报告与 final Head 同属一个提交） |

### 10.1 Base → final Head 实际 diff 摘要

```text
18 files changed, 1924 insertions(+), 150 deletions(-)
```

（此前版本误写为 `16 files / +1134 / −144`：既漏计了后续提交，也未包含
`PHASE_4_BLOCKED` 修复。上表为对 base 的实际统计。）

> 统计口径说明：本报告本身也在该 diff 内，因此任何"精确到行的总数"都会随
> 报告文本微调而变。**权威数字以 GitHub PR #12 的 diff 为准**；上表由
> `git diff --numstat 87d9ef1b <final head>` 得出。逐文件增量见 10.2。

### 10.2 changed files

| 状态 | 文件 |
|---|---|
| A | `PHASE4_EXECUTION_REPORT.md` |
| A | `docs/phase3_acceptance_record.md` |
| A | `src/equipeffi/application/lifecycle/__init__.py` |
| A | `src/equipeffi/application/lifecycle/errors.py` |
| A | `src/equipeffi/application/lifecycle/models.py` |
| A | `src/equipeffi/application/lifecycle/ports.py` |
| A | `tests/unit/test_phase4_fingerprint_decoupling.py` |
| A | `tests/unit/test_phase4_lifecycle_generalization.py` |
| A | `tools/verify_phase4_fingerprint_compat.py` |
| M | `.github/workflows/windows-core.yml` |
| M | `AGENTS.md` |
| M | `HANDOFF.md` |
| M | `QA_BACKLOG.md` |
| M | `REFERENCE_STANDARD_ROADMAP.md` |
| M | `ROADMAP.md` |
| M | `TASK_STATE.md` |
| M | `src/equipeffi/application/services/centrifugal_pump_analysis_service.py` |
| M | `src/equipeffi/infrastructure/persistence/sqlite_records_repository.py` |

### 10.3 实际 GitHub CI / workflow 结果

见文末「Final Head」一节（本报告与 final Head 同属一个提交，CI 在最终 head 上重跑）。

## 11. 状态

```text
Phase 4 implementation = EXECUTION_COMPLETE
READY_FOR_INDEPENDENT_ACCEPTANCE
```

**不合并 PR。不自宣 `PHASE_4_PASS`。不进入 Phase 5。**

## 12. Final Head

独立验收的**唯一对象**：

```text
final Head SHA = e070f3e 系列之后的本报告最终提交（见 GitHub PR #12 的 head）
```

权威取值请以 `https://github.com/adgo07/EquipEffi/pull/12` 的 head SHA 为准
（本报告无法自指自身提交哈希）。报告完成后**不得**再向该分支追加提交。
如 final Head 改变，必须重新声明新的 final Head 并重新等待对应 CI。
