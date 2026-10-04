# PHASE7_EXECUTION_REPORT

Phase 7 — GB19762 分析流程与历史记录最终收口。

**本阶段不是重新设计业务算法**：把产品流程收口为**一条**——

```text
选择泵型 → 填写参数 → 点击「分析」→ 显示清晰结果
         → 合法结果**自动**形成不可变历史记录
         → 以后从「分析记录」打开并查看当时的输入、结果和依据
```

## 0. 平台预检查

| 项 | 值 |
|---|---|
| 仓库 | `https://github.com/adgo07/EquipEffi.git` |
| Base | `master@6ead21fb6757d5d92ba81851f23e3c41d86598af`（= Phase 6 的 PR #14 merge） |
| 分支 | `phase7/gb19762-analysis-history-closure` |
| PR | 见 §9 的 PR 链接（本报告所在提交的 head） |
| locked central SHA | `ee5feb0cc34dbd99790500fadd0c4c932e202a20`（**未变更**） |
| 相关 Frozen Contract | Architecture `V2.1 FROZEN`、Numeric Contract `v1 FROZEN` |
| 适用 MUST / MUST NOT | UI 中文优先、普通 UI 不泄露内部 ID/JSON、技术信息渐进展示不删审计能力、按真实用户任务组织页面；不得复制第二套算法、不得为显示提前 ROUND 影响业务比较 |
| 冲突分类 | 无 `LOCAL DEFECT`；版本字段语义问题登记 `REGISTERED_DEVIATION`；**无** `CENTRAL CONTRACT GAP` |
| 是否需改中央 Contract | 否。**本任务不涉及中央公共 Contract。** |

**Standard Issue**：不存在新的标准问题，台账仍只有 `EQP-STD-GB19762-001`（已 `RESOLVED`）。
本 Phase **未改变**任何既有软件解释，也未新增标准问题。

## 1. G00 — Phase 6 收口 + Phase 7 rebaseline

新增 [docs/phase6_acceptance_record.md](docs/phase6_acceptance_record.md)：

| 记录项 | 值 |
|---|---|
| Phase 6 | `PHASE_6_PASS` |
| accepted head | `05b40f91086bbdbe196793075e440de4473cbf96` |
| PR | `#14` |
| merge SHA | `6ead21fb6757d5d92ba81851f23e3c41d86598af` |
| acceptance date | 2026-10-04 |

来源说明明确写出：**Phase 6 PASS 为产品负责人收到独立验收后作出的验收决定，
不是执行者自行宣告 PASS**；并如实记录两轮 blocker（`analysis.py` 泄露
`issue_codes`；共享门禁声明与代码不符；治理状态未同步）与 CI-only 编码缺陷经过。

同步 `Phase 6 = PHASE_6_PASS` / `Phase 7 = IN_PROGRESS`：`AGENTS.md`、`ROADMAP.md`、
`REFERENCE_STANDARD_ROADMAP.md`、`TASK_STATE.md`、`HANDOFF.md`、
`UI_CURRENT_STATE_AUDIT.md`、`QA_BACKLOG.md`。

**Owner 产品规则正式落档**：`AGENTS.md` 新增 **§2.8**，逐条记录本次 9 条产品决定
与 records.sqlite 原则。

**重审两条 QA**：

| 编号 | 重审结论 |
|---|---|
| `QA-P4-001` | 明确**不**建立正式 Reproduce / Attempt 模型 / 通用 Audit·Lineage Framework，也不为理论上的未来能力扩展数据库。保持 `REGISTERED_DEVIATION`，长期目标**不再自动继承**后续 Phase；将来若确需「基于历史记录重新分析」，须作为独立明确需求单独设计。 |
| `QA-P6-003` | 原问题为「草稿名称即 identity」。Phase 7 已取消普通用户「分析草稿」概念，因此**不新增** `workspace.display_name` / `rename_workspace` 等草稿产品能力；只保证**内部** identity 稳定（create/update/load/list/delete 契约与修订号语义不变，自动记录不依赖 Workspace）。改为 `CLOSED`。 |

## 2. G01 — 新建分析页面最终收口

### 2.1 删除草稿 UI（先证明再删）

从 `新建分析` 页面删除：分析草稿区域、草稿名称、保存草稿、新建草稿、已有草稿、
载入、刷新、删除草稿；首页同步删除「继续最近的草稿」及 `_open_draft*`。

**先证明再删除**（按任务要求逐项检查）：

| 检查项 | 结论 |
|---|---|
| Finalize 一致性 | `finalize(workspace_id=None)` 本就可用——安全性由**输入指纹比对 + 业务状态白名单 + Canonical provenance** 保证，不依赖 Workspace。故普通流程**不需要** Workspace。 |
| 旧 Workspace 兼容 | `WorkspaceRepository` / `create·update·load·list·delete_workspace` / `evaluate_workspace` / `request_from_workspace` / `save_workspace_from_request` **全部保留**，旧数据仍可读，修订号校验语义不变。 |
| 测试引用 | 既有草稿用户流程测试改写为「草稿已退出产品表面」的机械门禁 + 「底层能力仍可用」断言。 |
| 历史资产 | Phase 3～6 的 Workspace 数据与 Record 均未删除、未迁移、未改写。 |

### 2.2 删除评价日期输入

页面不再显示评价日期，`as_of` 在构造 Request 时自动取 `date.today()`；
不要求用户确认、不因日期早于实施日拒绝计算、不自动切换标准版本。
历史 Record 仍保存并显示评价日期。

### 2.3 泵型 → 字段联动完整审计（8 个正式泵型）

约束的**唯一权威**是既有领域路由 `domain/evaluation/evaluators/pump.py`：

- 级数：`"多级" in category` 为假 → 必须恰为 `1`；为真 → 用户填写且必须 `> 1`。
- 吸入方式：类别名含「双吸」→ 必须 `双吸`；含「单吸」→ 必须 `单吸`；
  否则领域层按「设备类别与单双吸字段冲突」拒绝计算。

据此在 **Application 层**（`CATEGORY_FIELD_CONSTRAINTS` /
`category_field_constraints`）声明约束，UI 只读取，**不新造第二套业务规则真值**：

| 泵型 | 级数 | 吸入方式 |
|---|---|---|
| 单级单吸清水离心泵 | `1` 自动锁定 | `单吸` 自动锁定 |
| 单级双吸清水离心泵 | `1` 自动锁定 | `双吸` 自动锁定 |
| 管道清水离心泵 | `1` 自动锁定 | **用户选择**（类别名未唯一决定） |
| 多级清水离心泵 | 用户填 `>1` | 用户选择 |
| 轻型多级清水离心泵（立式） | 用户填 `>1` | 用户选择 |
| 轻型多级清水离心泵（卧式） | 用户填 `>1` | 用户选择 |
| 单级石油化工离心泵 | `1` 自动锁定 | `单吸` 自动锁定 |
| 多级石油化工离心泵 | 用户填 `>1` | 用户选择 |

锁定字段在 `_collect_request` 中**强制取权威值**（不依赖控件状态），
因此用户改不动、也绕不过；页面同时给出中文锁定说明。

### 2.4 普通结果显示精度

新增 Presentation 层 `format_display_number`，把连续型派生量按 **2 位小数**显示，
只作用于本页文本。**未改变**：Decimal 原始值、Numeric Profile、等级比较值、
Record 精确快照、calculation trace、Golden business truth。
标准原始限值保持原文精度（未强行统一两位）。

### 2.5 删除新建分析页技术详情

移除该页的折叠技术详情区。`provenance` / `rule_profile` / `matched_rule_id` /
pack hash / Numeric Profile / calculation trace / result contract **全部继续保存在
Result 与 Record**，只是普通分析页不展示；审计入口移至「分析记录」页。

## 3. G02 — 分析即自动保存 Record

新增 Application 用例 `analyze_and_record(request, record_id=None)` 与
`AnalysisOutcome` DTO，`record_status` 三态：

```text
RECORDED       已自动形成不可变历史 Record
NOT_RECORDED   合法评价但按业务规则不固化（业务拒绝）
SAVE_FAILED    计算结果已产生，但历史记录**保存失败**（系统失败）
```

- 删除「保存为正式记录」按钮；用户点击「分析」后自动固化。
- **未放宽任何安全门禁**：固化仍走既有 `finalize()`，业务状态白名单
  （`SUCCESS` / `OUT_OF_STANDARD_SCOPE` / `INSUFFICIENT_DATA`）、输入指纹比对、
  类别与日期一致性、Canonical provenance 检查一条不减。触发者从「用户点击」
  变为「合法评价完成后自动执行」。
- 每次分析生成**新** `record_id`（`ANALYSIS-<uuid12>`），连续分析不覆盖历史。
- 持久化失败**不吞异常**：`SAVE_FAILED` 时 UI 明确显示
  「计算结果已产生，但历史记录保存失败，本次结果未被记录。」，
  **不得**显示为已保存。

## 4. G03 / G04 — 历史 Record 最小自足与分析记录页

### 4.1 记录详情可自足还原

从 Record 自身即可还原：评价日期、企业/项目名称、设备编号、产品类别、原始输入、
最终结论、等级、关键计算结果、当时采用的标准、标准数据版本、Canonical 包哈希、
Numeric Profile、Result Contract、命中数据依据。

标准依据只冻结运行时**真实存在且可信**的部分（标准表 / 条款 / `data_id`），
不快照整张标准表、不建 Citation Framework、**不为不存在的数据编造条款或页码**。

### 4.2 旧 Record 降级显示

Phase 3～6 形成的旧 Record：**不**追溯 UPDATE、**不**补写当前数据、**不**重新计算、
**不**伪造 provenance。缺少依据字段时降级显示
「该历史记录保存时未包含完整标准依据。」，并可正常打开不崩溃。

### 4.3 普通区与审计信息的边界

普通详情展示业务事实；`workspace_id` / `rule_profile` / `matched_rule_id` /
pack hash / Numeric Profile ID / 内部 schema ID / JSON / Python 字段名
**不出现**在普通区。内部标识集中在页面最底部**默认折叠**的「审计信息」入口
（含命中数据 ID 与输入指纹），保留审计能力但不再是普通页面重点。

### 4.4 Reopen 硬规则

打开历史 Record：**绝不**调用 evaluator、**绝不**重新计算、**绝不**按今天日期重新解释、
**绝不**读取当前 Canonical 覆盖历史结果。机械测试把
`EVALUATOR_FACTORIES` patch 为 raise，`open_record` 仍必须成功。

### 4.5 版本字段语义审查

审查确认：`RecordSnapshot.ruleset_version` 与 `calculator_version`
**实际存的是 rule profile 标识**（如 `pump_water`），不是真正的版本号；
且当前 Result 契约中**没有**任何可信的规则集 / 计算器版本字符串。

处理：**不伪造**版本值；Presentation 不再把它们当作版本展示（审计信息区标注为
「规则集标识」）；只对新 Record 修正语义需要 schema 变更，而本 Phase 默认不改
schema，故不自行变更。登记 `QA-P7-001`（`REGISTERED_DEVIATION`）。

## 5. G05 — 系统异常与业务结论分离

| 类别 | 行为 |
|---|---|
| 业务资料不足 `INSUFFICIENT_DATA` | **合法业务终态**，可形成 Record；文案为业务语义（缺哪些资料） |
| Python 异常 / 数据库失败 / 标准包读取失败 / 内部执行错误 | **系统异常**：不转成 `INSUFFICIENT_DATA`、不转成「无法判定」、**不生成 Record**；UI 统一提示「分析未能完成，请检查输入或联系技术人员。」，真实 traceback 进日志（`logger.exception`） |

未新建通用 `audit_event` 系统（现有 Record 事务已满足本阶段需求）。

## 6. records.sqlite 原则

**未修改 schema**：无新增 migration，`001` / `002` migration 未改动，
`schema_version` 保持 2。

理由：现有 `input_snapshot_json` / `result_snapshot_json` / `reference_snapshot_json`
**足以**承载本阶段所需的最小历史自足信息。本 Phase **未出现**任何需要 additive
migration 的明确 V1 需求，因此**未触发 STOP 报告流程**。

**未新增**：lineage table、audit_event table、`workspace.display_name`、
Attempt table、任何通用历史框架。

## 7. G06 — Phase 7 专项测试

新增 [tests/unit/test_phase7_analysis_history.py](tests/unit/test_phase7_analysis_history.py)（**36 项**），
覆盖任务要求的全部 11 项：

1. 8 个正式泵型的类别联动：单级类别级数锁定 `1`、单吸/双吸类别吸入方式锁定、
   管道清水泵只锁级数；**锁定值不可被用户绕过**。
2. 普通新建分析页不存在：分析草稿、评价日期输入、「保存为正式记录」、技术详情。
3. 新分析 `as_of` 自动取本机当天，并写入 Record 供追溯。
4. 合法业务终态（`SUCCESS` / `OUT_OF_STANDARD_SCOPE` / `INSUFFICIENT_DATA`）
   分析完成后自动形成 Record。
5. `INVALID_INPUT` / 类别未确认 / 系统异常不得产生 Record。
6. 连续合法分析生成不同 `record_id`，且各条保留当时的输入，不覆盖。
7. 显示 2 位小数；底层完整精度与 Golden 结果不变（含阈值原文精度断言）。
8. 历史 Record Reopen 不调用 evaluator。
9. 冻结结果按原 snapshot 展示；改当前 evaluator 后旧 Record 不漂移。
10. 系统异常不伪装成业务「无法判定」/「资料不足」。
11. 旧 Record 缺新依据字段：可正常打开并降级显示，不崩溃。

另含范围守卫：无持久化层改动（无 migration）、无 Reproduce / Attempt /
Audit Framework、记录页无重算入口。

## 8. 本地实际结果

```text
tests.unit.test_phase7_analysis_history            36   全通过（本 Phase 新增）
CI gating 模块列表（同 CI 形态，pwsh 数组 + *> 重定向）  276  OK / exit 0
全量 unittest                        1301 run / 1294 pass / 3 fail / 1 error / 3 skip
known-regression comparator          gate=PASS
                                     new_failures=0 new_errors=0 worsened=0 missing=0
compileall -q src tools              exit 0
tools/smoke_jsonl.py                 passed=true
git diff --check                     clean
```

既有失败仍是既有失败（3 项 V4 reader/writer + 1 项 release audit 错误），
**未修复也未隐藏，且未把任何新失败加入 known baseline**。

## 9. 实际 GitHub CI / workflow 结果

最终 head 的 Required CI（全部 `success`）：

```text
Windows Core
  [ 6] Compileall                                                          success
  [ 7] Architecture boundaries and metadata contract                       success
  [ 8] Application and core tests                                          success
  [ 9] Phase 2/3/4/5/6/7 settings, lifecycle, Stage D, Product Shell,
       analysis flow, Qt offscreen (gating)                                success
  [10] Full suite known-regression comparator (gating)                     success
Pump Conformance
  [12] pump_chemical Stage D support + Phase 6 product shell (gating)      success
Whitespace check (gating)                                                  success
Full suite baseline (NON-GATING)                                           success
```

### 9.1 过程中发现并修复的一个失败（如实记录）

首次推送后 gating 步骤在 CI 失败，而**本机以完全相同的模块列表与重定向方式通过**。
本仓 GitHub token 为 `gho_` 级别、缺 `actions:read`：job log 与 artifact 下载均 401。
改用 workflow `::error::` 注解（经 check-runs API 读取）定位，确认原因是
**我自己写的治理断言过紧**：

`test_phase6_product_shell.py::test_governance_docs_record_the_closures` 断言
`TASK_STATE.md`（**当前状态**文件）必须永久保留 Phase 6 的措辞与 `CLOSED` 字样。
Phase 7 合法地把该文件演进为当前阶段状态后，断言即失败。

修复：断言改为锚定**不可变事实**——`docs/phase6_acceptance_record.md` 的
`PHASE_6_PASS` 与 accepted head、`QA_BACKLOG.md` 中四项仍为 `CLOSED`，
并只要求活跃状态文件不把这些项描述成 `BLOCKER`；同时在 `TASK_STATE.md` 新增
`phase_6_closure` 块承载关闭事实，使其不依赖当前阶段措辞。

教训：**「当前状态」文件不得被当作永久记录来断言**；阶段关闭事实应落在
不可变的 acceptance record / closure 块中。

## 10. Base → final Head diff 与 changed files

权威数字以 PR 的 diff 为准（本报告自身也在该 diff 内，属自指）。

主要新增：

| 文件 | 说明 |
|---|---|
| `src/equipeffi/presentation/qt/pages/analysis.py` | 分析页最终形态（无草稿/日期/保存/技术详情；8 泵型联动；2 位小数显示） |
| `tests/unit/test_phase7_analysis_history.py` | Phase 7 专项测试（36 项） |
| `docs/phase6_acceptance_record.md` | Phase 6 极简验收落档 |
| `PHASE7_EXECUTION_REPORT.md` | 本报告 |

主要修改：

| 文件 | 说明 |
|---|---|
| `src/equipeffi/application/services/centrifugal_pump_analysis_service.py` | `CATEGORY_FIELD_CONSTRAINTS` / `category_field_constraints`、`analyze_and_record`、`AnalysisOutcome` |
| `src/equipeffi/presentation/qt/pages/home.py` | 删除草稿入口 |
| `src/equipeffi/presentation/qt/pages/records.py` | 详情自足、标准依据归属、审计信息折叠、依据降级 |
| `src/equipeffi/presentation/qt/shell.py` | `open_analysis` 不再载入草稿 |
| `.github/workflows/windows-core.yml` | 接入 Phase 7 测试模块 |
| `tests/unit/test_phase3_qt_unified.py` / `test_phase3_r1_blockers.py` / `test_phase3_r3_as_of_lifecycle.py` / `test_phase5_chemical_stage_d.py` / `test_phase6_product_shell.py` | 断言更新到 Phase 7 真实行为 |
| `AGENTS.md` / `HANDOFF.md` / `ROADMAP.md` / `REFERENCE_STANDARD_ROADMAP.md` / `TASK_STATE.md` / `QA_BACKLOG.md` / `UI_CURRENT_STATE_AUDIT.md` | 治理与状态同步 |

**受保护资产零漂移**（`git diff` 为空）：18 条 water + 11 条 chemical Approved Golden
业务真值、Canonical `resources/standards/pump.json`、Numeric Profile、
pump 公式 / 边界 / 等级判断、`platform-lock.json` / `PLATFORM_BASELINE.md`、
known baseline、`records_migrations.py`、legacy Tk 表单模型依赖链。

## 11. QA 条目变动

| 动作 | 条目 | 说明 |
|---|---|---|
| **关闭** | `QA-P6-003` | 草稿 identity 问题随「分析草稿」概念退出产品表面而消解；未新增草稿产品能力 |
| **重审** | `QA-P4-001` | 明确不建 Reproduce / Attempt / 通用 Audit·Lineage Framework；长期目标不再自动继承后续 Phase |
| **新增** | `QA-P7-001` | `ruleset_version` / `calculator_version` 实际存 profile 标识；不伪造版本，Presentation 改为标注「规则集标识」 |
| **新增** | `QA-P7-002` | Phase 3～6 旧 Record 未冻结完整标准依据；降级显示，不追溯改写 |
| 保留 | `QA-P6-001` / `QA-P6-004` | legacy Tk 保留但不接线；非正式 adapter 未升级为正式 UI（disposition Phase 8 / 9） |
| 保留 | `QA-P5-003`～`005` | V4·Excel → Phase 8；Android bridge / installer·signing → Phase 9 |

## 12. records schema change

```text
records schema change = NO
```

无新增 migration；`001` / `002` 未修改；`schema_version` 保持 2。
本 Phase **未发生**需要 Owner 授权的 schema 变更。

## 13. Phase 7 Exit Gate 自检

| Exit Gate 条件 | 结果 |
|---|---|
| Phase 6 PASS 已正式落档 | PASS |
| 普通用户完全看不到「分析草稿」 | PASS |
| 普通用户不填写评价日期 | PASS |
| 新分析自动记录电脑当天日期 | PASS |
| 泵型能够唯一决定的参数全部正确自动锁定 | PASS |
| 新建分析页无「保存为正式记录」 | PASS |
| 合法分析自动形成不可变历史 Record | PASS |
| 非法输入 / 系统异常不生成 Record | PASS |
| 普通计算结果采用合理 2 位显示 | PASS |
| 内部精度和业务比较零漂移 | PASS |
| 新建分析页无技术详情 | PASS |
| 必要 provenance 仍完整保存 | PASS |
| 历史 Record 不重新计算 | PASS |
| 历史 Record 可独立显示原输入、原结果和必要依据 | PASS |
| 系统执行失败与业务「资料不足」严格分离 | PASS |
| 不引入无必要 records migration | PASS（NO） |
| 不实现 Reproduce / Attempt / Audit Framework | PASS |
| 29 条 Approved Golden 零业务漂移 | PASS |
| Phase 8 / Phase 9 范围没有被提前实现 | PASS |
| Required CI 无新增未知 regression | PASS（§9） |

## 14. 状态

```text
Phase 7 implementation = EXECUTION_COMPLETE
READY_FOR_INDEPENDENT_ACCEPTANCE
```

**不合并 PR。不自宣 `PHASE_7_PASS`。不进入 Phase 8。**

## 15. Final Head

独立验收的**唯一对象**：本报告所在提交的 head（见 PR #15 的 head SHA）。

报告完成后**不得**再向该分支追加提交。如 Head 改变，必须重新声明新的 final Head、
重新执行必要测试，并等待该 Head 对应的 CI。

---

# Phase 7 复验修复（Re-verification）

独立验收对 head `515229e2e08c8685bed7f8b7c4d0ee28e539f89d` 给出
`PHASE_7_BLOCKED`，提出 3 项阻断。三项**均成立**（其中第 1 项是我无授权改动了
业务输入），逐项修复如下。

## R-B1 类别联动改变合法输入

**问题**：`CATEGORY_FIELD_CONSTRAINTS` 把 `单级石油化工离心泵` 的吸入方式强制锁为
`单吸`。已批准 Golden `GC-PUMP-V5-CHEMICAL-DOUBLE-SUCTION` 的合法输入正是
**「单级石油化工离心泵 + 双吸」**；锁定后 Qt 无法原样输入，Record 被写成单吸，
比转速从 `135.8439…` 变成 `192.1123…`。

**根因**：我把**清水类**的规则错误套用到了石化类。核对域路由
`domain/evaluation/evaluators/pump.py`：

- 清水分支有 `category_suction` 一致性检查（类别含「单吸」/「双吸」必须与字段一致，
  否则按"设备类别与单双吸字段冲突"拒绝）；
- **石化分支没有该检查**，只校验 `suction ∈ {单吸, 双吸}` 并把它用于吸入方式系数。

因此「单级石油化工离心泵 + 双吸」在标准与已批准真值下都是**合法**的，
把它锁死属越权约束。

**修复**：石化类**不再约束吸入方式**（保留级数由类别名中的"单级"唯一决定）：

| 泵型 | 级数 | 吸入方式 |
|---|---|---|
| 单级石油化工离心泵 | `1` 自动 | **用户选择**（原为强制单吸） |
| 多级石油化工离心泵 | 用户填 `>1` | **用户选择** |

清水类的锁定**保留**（域层确有一致性检查，且类别名显式声明单/双吸）。

**验证**：以已批准 Golden 原输入走 Qt 路径，`request.suction == "双吸"`、
级数 `1`、`evaluation_status = SUCCESS`、`grade = 1`、
`比转速 ns` 以 `135.84` 开头——与 Golden 完全一致（回归测试
`test_approved_double_suction_chemical_golden_input_is_preserved`）。

## R-B2 两位小数显示未落实

**问题**：`analysis.py` 的 `_TWO_DECIMAL_METRICS` 是一份**按显示名维护的白名单**，
与实际派生量名称不匹配，因此普通结果仍打印数十位小数。

**根因**：白名单必然漏键。实测真实派生量键为
「吸入方式系数 / 级数 / 比转速用流量（m³/s）/ 单级扬程（m）/ 比转速 ns / 输出功率（kW）」，
而白名单里写的是 `比转速` / `输出功率_kW` 等，一个都没命中。

**修复**：改为**基于数值类型**判定（`labels.format_metric`），不再依赖名字白名单：

```text
非数值 / None / 非有限   -> 原样（None -> "—"）
整数值（级数=1 等）       -> 不补小数位（"1"）
其它数值（含小数部分）     -> 固定 2 位小数（"93.82"）
```

分析页的「实际泵效率」「对应等级效率限值」「关键计算参数」与记录页的
「原等级阈值」「原关键计算参数」统一使用该实现。

**验证**：`format_metric` 覆盖整数 / 小数 / 非数值；分析页断言**每一个**派生量
都出现其名称与 2 位格式化值，且不得再出现未格式化的长小数串（回归测试
`test_every_derived_metric_is_rendered_with_two_decimals`）。
**未改变** Decimal 原始值、Numeric Profile、等级比较、Record 快照、Golden 真值。

## R-B3 历史详情不完整

**问题**：`records.py` 未展示冻结的缺失信息与判定解释；资料不足 Record 只显示
「无法判定」，用户看不到原因。派生参数还丢失名称，只显示数值串。

**根因**：

- 详情渲染从未输出 `result_snapshot["missing_fields"]` 与 `["explanation"]`；
- 「原关键计算参数」只 join 了 `derived.values()`，把键名丢掉了。

**修复**：

- 普通详情新增「缺失信息：…」与「判定说明：…」两行（取自不可变快照）；
- 「原关键计算参数」改为 `名称 数值` 成对输出，并使用 R-B2 的格式化。

**验证**：资料不足 Record 的详情包含「缺失信息：泵效率」与
「判定说明：缺少泵效率，无法进行能效等级比较」；派生参数的每个名称都出现在该行，
且不再出现 `：50；1；` 这类只有数值串的形态（回归测试
`test_insufficient_data_record_shows_reason_and_missing_fields`、
`test_record_derived_parameters_keep_their_names`）。

## 复验修复后的本地结果

```text
tests.unit.test_phase7_analysis_history                44 项，全通过（含本轮新增 8 项）
CI gating 模块列表（同 CI 形态）                          284 项  OK / exit 0
全量 unittest                        1309 run / 1302 pass / 3 fail / 1 error / 3 skip
known-regression comparator          gate=PASS（new_failures=0 new_errors=0）
compileall -q src tools              exit 0
git diff --check                     clean
```

**未修改**：Golden 业务真值、候选文件、Approved Golden provenance、Canonical、
Numeric Profile、pump 公式 / 边界 / 等级判断、`platform-lock`、
`records_migrations.py`（records schema 仍为 **NO**）。

## 复验修复后的状态

```text
Phase 7 implementation = EXECUTION_COMPLETE
READY_FOR_INDEPENDENT_ACCEPTANCE
```

**不合并 PR。不自宣 `PHASE_7_PASS`。不进入 Phase 8。**
