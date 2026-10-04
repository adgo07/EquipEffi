# PHASE5_EXECUTION_REPORT

Phase 5 — pump_chemical Stage D 正式支持与发布门禁收口。

**本阶段不是重新开发 pump_chemical**：在已有 Phase 3/4 实现基础上完成 Stage D
正式支持证据闭环，形成 **support promotion candidate** 并交独立验收。

## 0. 平台预检查

| 项 | 值 |
|---|---|
| 仓库 | `https://github.com/adgo07/EquipEffi.git` |
| Base | `master@d6112ea9c7c1c16f95d798c2229cdc54aaf6240a`（= Phase 4 的 PR #12 merge） |
| 分支 | `phase5/pump-chemical-stage-d-support` |
| PR | **#13** — https://github.com/adgo07/EquipEffi/pull/13 |
| locked central SHA | `ee5feb0cc34dbd99790500fadd0c4c932e202a20`（未变更） |
| 相关 Frozen Contract | Architecture `V2.1 FROZEN`、Numeric Contract `v1 FROZEN` |
| 适用 MUST / MUST NOT | Stage D 须有独立验收证据方可声明 `SUPPORTED`；不得无证据跳级；各设备按自身证据声明 Numeric Profile |
| 冲突分类 | 无 `LOCAL DEFECT`；`pump_chemical` 的发布表面差异为 `REGISTERED_DEVIATION`（已逐项登记）；**无** `CENTRAL CONTRACT GAP` |
| 是否需改中央 Contract | 否。**本任务不涉及中央公共 Contract。** |

**Standard Issue**：不存在 chemical 新标准问题。台账仅 `EQP-STD-GB19762-001`
（标准实施日期与软件评价日期 `as_of` 的关系），已 `RESOLVED`。本 Phase
**不改变**任何既有软件解释——`as_of` 规则在 Phase 3 R3 已定为"评价日期不是业务门禁"，
Phase 5 只把提示文案按 Owner 要求缩短。

**证据口径（不得误述）**：本阶段仍是**一个 GB19762 产品级 E2E 样板，其中有
`water` + `chemical` 两个真实内部 rule profile**。
**不得**表述为"已经有两个独立设备 / 标准 E2E 样板"。

## 1. G00 — Phase 4 治理收口

| 记录项 | 值 |
|---|---|
| Phase 4 | `PHASE_4_PASS` |
| accepted head | `a4034ef3751590b52a821d6a3bdbebcbca6a8ec9` |
| PR | #12 |
| merge SHA | `d6112ea9c7c1c16f95d798c2229cdc54aaf6240a` |
| Phase 5 | `IN_PROGRESS` |

新增极简 [docs/phase4_acceptance_record.md](docs/phase4_acceptance_record.md)，
只记录 `phase` / `verdict` / `acceptance date` / `accepted head` / `PR`+`merge SHA` /
independent acceptance 来源说明，**不复制**验收报告正文。

来源说明明确写出：

> **Phase 4 PASS 为产品负责人收到独立验收后作出的验收决定，不是执行者自行宣告 PASS。**

并如实记录两次 `PHASE_4_BLOCKED`（head `855f259` 的导入耦合、head `51b7b79` 的
旧 Workspace 缺字段兼容性回归）及其修复出处 `PHASE4_EXECUTION_REPORT.md` §4.1 / §4.2。

同步文件：`AGENTS.md`、`HANDOFF.md`、`ROADMAP.md`、
`REFERENCE_STANDARD_ROADMAP.md`、`TASK_STATE.md`、`V1_SCOPE.md`、`README.md`。

**ADR-002 lineage / audit 继续保留** `REGISTERED_DEVIATION`，`target_phase = Phase 7`
（`QA_P4-001`）；Phase 5 **未实现** lineage / audit / reproduce，也未因此修改
`records.sqlite`。

## 2. Owner 产品规则 — 评价日期

Owner 决定：**评价日期不是业务门禁**。正式 Qt 产品路径：

| 要求 | 现状 |
|---|---|
| 新建评价自动记录本机当前日期 | 已满足（`analysis.py` `QLineEdit(date.today().isoformat())`） |
| 用户无需关注评价日期 | 已满足（tooltip 改为"评价日期用于记录与追溯；不影响所选标准的计算"） |
| 标准与日期不匹配时仅几字非阻断提醒 | 已改为四字短语 **"该标准尚未实施"** |
| 尚未实施 / 已废止 / 已被替代仍允许正常评价 | 已满足（无 `as_of` 短路门禁） |
| 不得改变 `evaluation_status` / `grade` / Finalize 权限 / 自动切换标准 | 已满足（有测试断言） |
| 不设计复杂确认流程 | 已满足（无确认对话框） |

**已废止 / 已被替代暂未提供短语**：判定它们需要标准生命周期元数据
（`superseded_by` / 废止日期），当前 Canonical Pack 只提供 `effective_date`。
Owner 规则明确**不为此私造公共规则**，故不对"晚于实施日期"做推测性提示；
补齐须走标准映射流程，已登记 `QA-P3-002`。

遗留 `EvaluationService` / `--json` / `ApplicationApi` / `--web` / JSONL / V4
入口的旧 `as_of` 门禁登记为 `REGISTERED_DEVIATION`（`QA-P3-003`），
**不借 Phase 5 扩大重构**。

## 3. G01 — Stage D Evidence Matrix

见 [docs/phase5_stage_d_evidence_matrix.md](docs/phase5_stage_d_evidence_matrix.md)。
15 项逐项基于**当前 Base 的真实代码与实测证据**判断（先证后改）：

| 状态 | 数量 | 项 |
|---|---|---|
| `PASS` | **14** | 标准来源 / Mapping / Standard Issues / Rule / Calculator / Approved Golden / generated boundaries / Numeric·Conformance / regression / Qt Windows UI / Application / Workspace·Finalize·Record·Reopen / 标准依据·结果解释 / provenance·traceability |
| `DEFERRED_BY_ROADMAP_TO_PHASE_8` | 1 | Excel（并明确 Phase 8 **必须**调用同一 Application / Calculator，**不得**建立第二套业务算法） |
| `DEFERRED_BY_ROADMAP_TO_PHASE_9` | 1 | Windows 交付层（安装包 / 签名 / 正式发布产物） |
| **未解释 `BLOCKED`** | **0** | — |

**Standard Issues**：按真实证据检查既有台账即可，**未重新审计全部历史标准**；
`pump_chemical` **无新问题**，也**未为了 Stage D 人工制造 issue**。

**成熟度两次转移分开记证据**（不得从 `READY_FOR_IMPLEMENTATION` 跳写为 `SUPPORTED`）：

1. `READY_FOR_IMPLEMENTATION → IMPLEMENTED`：真实核心实现（`ChemicalPumpEvaluator`
   + 统一 `CentrifugalPumpAnalysisService`）、11 条 Approved Golden、统一 Application、
   generated boundaries、Numeric / Conformance。
2. `IMPLEMENTED → SUPPORTED`：本 Phase Stage D 正式产品路径验证 +
   `FORMAL_APPLICATION_E2E` evidence + **最终独立验收结论（尚未产生）**。

因此本 Phase 结束时成熟度停在 `IMPLEMENTED`，`SUPPORTED` 作为**候选**移交独立验收。

## 4. G02 — support promotion candidate

G01 无真实 blocker 后修改 release gate。目标候选行为：

```text
pump_chemical:
  scope_status      = IN_V1
  support_status    = SUPPORTED          （候选；治理状态见下）
  standard_maturity = SUPPORTED          （候选）
```

治理状态只写：

```text
SUPPORT_PROMOTION_CANDIDATE
READY_FOR_INDEPENDENT_ACCEPTANCE
```

**未写**"正式支持已经生效"。

盘点并同步的 release / support gate：

| 位置 | 处理 |
|---|---|
| `CentrifugalPumpAnalysisService._release_support` | `pump_chemical → SUPPORTED`（候选），并写明候选状态与 deviation 指向 |
| profile / capability metadata | `specs/equipment_efficiency/profiles/pump_chemical.md` 状态段更新 |
| Qt result projection | `analysis.py` 技术详情区新增"支持状态"行 |
| Qt record detail | `records.py` 技术详情区新增"支持状态"行（取自**快照**） |
| release audit tooling | `tools/audit_release.py` 的过期注释同步候选事实（该步骤走 evaluator，本身不经发布门禁） |
| 相关测试 / 治理记录 | 见 §7、§8 |

`tools/audit_release.py` 此前注释冻结"`pump_chemical` route intentionally remains
`NOT_IN_RELEASE_SCOPE`"——**已同步当前 candidate 事实**，并说明该烟测绕开发布门禁、
因此不受影响。

## 5. G03 — Qt 正式产品 E2E 与历史 Record 冻结

**正式发布用户表面 = PySide6 Qt Desktop（`--qt`）**。

新增 [src/equipeffi/presentation/qt/labels.py](src/equipeffi/presentation/qt/labels.py)：

```text
SUPPORTED              -> "正式支持"
NOT_IN_RELEASE_SCOPE   -> "当前版本未支持"
（未知取值 / 缺失 -> "—"，绝不展示内部英文枚举）
```

机械验证矩阵（`tests/unit/test_phase5_chemical_stage_d.py`）：

| 类别 | 结论状态 |
|---|---|
| 单级石油化工离心泵 | 正常等级 `SUCCESS` / `OUT_OF_STANDARD_SCOPE` / `INSUFFICIENT_DATA` / `INVALID_INPUT` |
| 多级石油化工离心泵 | 正常等级 `SUCCESS`（`stages=3`）/ 同上四类 |

新计算结果 `support_status = SUPPORTED`，并在 Qt 结果 / 记录详情的**只读辅助信息区**
以"支持状态：正式支持"简洁显示；**不作为主业务结论**（有断言证明它不出现在
`conclusion` / `summary` / `basis`）。

**历史 Record 冻结**：`records.py` 的支持状态取自**不可变快照本身**
（`result_snapshot.support_status`），因此：

- Phase 3/4 期间形成的 chemical Record（快照为 `NOT_IN_RELEASE_SCOPE`）
  Reopen 后仍显示"支持状态：当前版本未支持"；
- **不追溯改成 `SUPPORTED`、不重算、不改写 snapshot**
  （测试对 `result_snapshot_json` 做前后逐字节比对）；
- 同一类别下新 Record 为 `SUPPORTED`、历史 Record 保持旧值——两者并存可验证。

`NOT_IN_RELEASE_SCOPE` 枚举**保留**（`enums.py` 未改），仍用于历史 Record、
其他未发布 Profile（如 `transformer`）与已登记 deviation。

## 6. G04 — 当前 Application E2E 证据

新增 [tools/build_phase5_chemical_e2e_evidence.py](tools/build_phase5_chemical_e2e_evidence.py)
与 [specs/equipment_efficiency/evidence/phase5_chemical_stage_d_e2e.json](specs/equipment_efficiency/evidence/phase5_chemical_stage_d_e2e.json)。

链路：

```text
11 条 Approved Golden 的历史业务真值
  -> 统一 Application 入口（CentrifugalPumpAnalysisService）
  -> 实际 evaluator
  -> 结果契约
  -> 与历史真值逐字段比对
```

比对字段：`evaluation_status` / `grade` / `ui_conclusion` / `issue_codes` /
`category_status`。结果：**11/11 `business_truth_consistent = true`**。

**未修改**：

- `expected` business truth（Golden 业务真值）；
- 历史 provenance；
- 未批量改写 `evaluation_layer`（11 条仍为 `PROFILE_EVALUATOR_TECHNICAL`、
  `support_status = null`）。

历史 Golden 继续表示**历史批准来源**；本证据表示**今天的正式产品链已经成立**。
证据文件记录每条 Golden 的文本 SHA-256（UTF-8、CRLF→LF、大写十六进制），
测试断言该哈希与当前文件一致——**可检测真值被改写**。

## 7. 已登记 deviation（不得误报为 Phase 5 已修复）

以下表面**不是**本阶段的正式支持提升表面，且**不是**历史废代码，
而是现存的 compatibility / development / future-adapter surfaces：

| issue_id | 表面 | 状态 | disposition |
|---|---|---|---|
| `QA-P5-001` | `--json` / `ApplicationApi` / JSONL / CLI 仍对 `pump_chemical` 返回 `NOT_IN_RELEASE_SCOPE` | `REGISTERED_DEVIATION` | **Phase 6**（产品入口 / Shell / shipped surface 收口） |
| `QA-P5-002` | `--web` 与 legacy Tk `--gui` 同源未同步 | `REGISTERED_DEVIATION` | **Phase 6** |
| `QA-P5-003` | V4 / Excel adapter | `REGISTERED_DEVIATION` | **Phase 8**（且必须调用同一 Application / Calculator） |
| `QA-P5-004` | Android bridge 未纳入正式支持表面 | `REGISTERED_DEVIATION` | **Phase 9**（发布前消除未声明语义分歧） |
| `QA-P5-005` | 安装包 / 代码签名 / 正式发布产物未产生 | `REGISTERED_DEVIATION` | **Phase 9** |
| `QA-P3-003` | 遗留入口的旧 `as_of` 门禁 | `REGISTERED_DEVIATION` | **Phase 6** |

**不得**用"历史兼容代码"含糊带过；**不得**把这些已登记 deviation 误报为
Phase 5 PASS 范围内已修复。

## 8. 本地实际结果

受影响套件（全部 0 fail / 0 error）：

```text
test_phase3_golden_and_boundaries      14   （18 water + 11 chemical，29/29 回放）
test_phase3_unified_analysis           34
test_phase3_qt_unified                 33
test_phase3_r1_blockers                20
test_phase3_r2_final_closure           11   （Finalize 全状态矩阵）
test_phase3_r3_as_of_lifecycle         18
test_phase3_r3_closure                 31   （Workspace / Record / Reopen）
test_phase4_lifecycle_generalization   20
test_phase4_fingerprint_decoupling     10
test_phase5_chemical_stage_d           27   （发布门禁 / 历史冻结 / 文案 / Stage D 证据 / Qt E2E）
test_pump_golden_case_0_3               4   （遗留 EvaluationService 仍返回 NOT_IN_RELEASE_SCOPE）
tests.contract.test_architecture_boundaries  11
test_composition                        3
```

其他门禁：

```text
全量 unittest                        1193 run / 1186 pass / 3 fail / 1 error / 3 skip
known-regression comparator           gate=PASS
                                      new_failures=0 new_errors=0 worsened=0 missing=0
compileall -q src tools               exit 0
git diff --check                      clean
tools/build_phase5_chemical_e2e_evidence.py   11 条，不一致 0 条
```

既有失败仍是既有失败（3 项 V4 reader/writer + 1 项 release audit 错误），
**未修复也未隐藏，且未把任何新失败加入 known baseline**。

## 9. GitHub CI / workflow 实际结果

final head 的 Required CI：

```text
Pump Conformance                     success
  JOB Pump Conformance (gating)      success
    [ 9] Approved Golden 0.4/0.5 and unified boundary gates                  success
    [11] Historical provenance, Finalize state matrix and as_of lifecycle     success
    [12] pump_chemical Stage D candidate evidence (gating)                   success  ← 本 Phase 新增
Windows Core                         success
  JOB Windows Core (gating)          success
    [ 6] Compileall                                                          success
    [ 7] Architecture boundaries and metadata contract                       success
    [ 9] Phase 2/3/4/5 settings, migrations, lifecycle, Stage D, Qt offscreen success  ← 本 Phase 扩展
    [10] Full suite known-regression comparator (gating)                     success
  JOB Whitespace check (gating)      success
  JOB Full suite baseline (NON-GATING) success
```

## 10. Base → final Head diff 与 changed files

```text
24 files changed, 1428 insertions(+), 96 deletions(-)
```

| 状态 | 文件 |
|---|---|
| A | `docs/phase4_acceptance_record.md` |
| A | `docs/phase5_stage_d_evidence_matrix.md` |
| A | `specs/equipment_efficiency/evidence/phase5_chemical_stage_d_e2e.json` |
| A | `src/equipeffi/presentation/qt/labels.py` |
| A | `tests/unit/test_phase5_chemical_stage_d.py` |
| A | `tools/build_phase5_chemical_e2e_evidence.py` |
| A | `PHASE5_EXECUTION_REPORT.md`（本报告） |
| M | `.github/workflows/pump-conformance.yml` |
| M | `.github/workflows/windows-core.yml` |
| M | `AGENTS.md` |
| M | `HANDOFF.md` |
| M | `QA_BACKLOG.md` |
| M | `README.md` |
| M | `REFERENCE_STANDARD_ROADMAP.md` |
| M | `ROADMAP.md` |
| M | `TASK_STATE.md` |
| M | `V1_SCOPE.md` |
| M | `specs/equipment_efficiency/profiles/pump_chemical.md` |
| M | `src/equipeffi/application/services/centrifugal_pump_analysis_service.py` |
| M | `src/equipeffi/presentation/qt/pages/analysis.py` |
| M | `src/equipeffi/presentation/qt/pages/records.py` |
| M | `tests/unit/test_phase3_golden_and_boundaries.py` |
| M | `tests/unit/test_phase3_r3_as_of_lifecycle.py` |
| M | `tests/unit/test_phase3_unified_analysis.py` |
| M | `tools/audit_release.py` |

**受保护资产零漂移**（`git diff` 核验为空）：18 条 water Approved Golden、
11 条 chemical Approved Golden、Canonical `src/equipeffi/resources/standards/pump.json`、
`platform-lock.json` / `PLATFORM_BASELINE.md`、known baseline、
`records_migrations.py`、`NOT_IN_RELEASE_SCOPE` 枚举。

> 统计口径说明：本报告本身也在该 diff 内，因此"精确到行的总数"必然随报告文本
> 微调而变，属自指。**权威数字以 GitHub PR #13 的 diff 为准**。

## 11. Phase 5 Exit Gate 逐项

| Exit Gate 条件 | 结果 |
|---|---|
| Stage D Matrix 无未解释 `BLOCKED` | PASS（0 项） |
| `READY_FOR_IMPLEMENTATION → IMPLEMENTED` 有独立证据 | PASS（§3.1） |
| `IMPLEMENTED → SUPPORTED` 有 Stage D 候选证据 | PASS（§3.2，最终一步待独立验收） |
| 新 chemical Qt 结果为 `SUPPORTED` | PASS |
| 11 条 chemical truth 经正式 Application E2E 一致 | PASS（11/11） |
| water 18/18 无回归 | PASS |
| chemical boundary / Numeric 无漂移 | PASS |
| Workspace / Finalize / Record / Reopen 正确 | PASS |
| 历史 chemical Record 的 `NOT_IN_RELEASE_SCOPE` 不被追溯改写 | PASS |
| Qt 可看到新结果当前支持状态和历史 Record 当时状态 | PASS |
| 其他非正式入口 support 差异均已明确登记 `REGISTERED_DEVIATION` | PASS（`QA-P5-001`～`005`、`QA-P3-003`） |
| Excel 明确 `DEFERRED_TO_PHASE_8` | PASS |
| 安装 / 发布明确 `DEFERRED_TO_PHASE_9` | PASS |
| Canonical / Golden / Numeric / platform-lock 零漂移 | PASS |
| Required CI 无新增未知 regression | PASS |

## 12. 状态

```text
Phase 5 implementation    = EXECUTION_COMPLETE
Stage D candidate         = READY_FOR_INDEPENDENT_ACCEPTANCE
support promotion candidate = READY
```

**不合并 PR。不自宣 `PHASE_5_PASS` / `Stage D PASS` /
`pump_chemical officially SUPPORTED`。不进入 Phase 6。**

## 13. Final Head

独立验收的**唯一对象**：本报告所在提交的 head
（见 https://github.com/adgo07/EquipEffi/pull/13 的 head SHA）。

报告完成后**不得**再向该分支追加提交。如 final Head 改变，必须重新声明新的
final Head 并重新获取该 Head 对应的测试 / CI。
