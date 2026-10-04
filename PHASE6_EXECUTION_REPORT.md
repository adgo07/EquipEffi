# PHASE6_EXECUTION_REPORT

Phase 6 — 完整 GB 19762 Product Shell。

**本阶段不是重新设计业务算法**：把 Phase 2～5 已经成立的完整 GB 19762
（`pump_water` + `pump_chemical`）业务能力组织成正式、完整、可长期使用的
Windows PySide6 产品 Shell。

## 0. 平台预检查

| 项 | 值 |
|---|---|
| 仓库 | `https://github.com/adgo07/EquipEffi.git` |
| Base | `master@f3e32f84123937ed6caa2b84b7cc0cd04c3100e0`（= Phase 5 的 PR #13 merge） |
| 分支 | `phase6/gb19762-product-shell` |
| PR | 见 PR 链接（本报告所在提交的 head） |
| locked central SHA | `ee5feb0cc34dbd99790500fadd0c4c932e202a20`（**未变更**） |
| 相关 Frozen Contract | Architecture `V2.1 FROZEN`、Numeric Contract `v1 FROZEN` |
| 适用 MUST / MUST NOT | UI 中文优先、普通 UI 不泄露内部 ID/JSON、技术信息渐进展示不删审计能力、按真实用户任务组织页面；不得复制第二套算法、不得把非正式 adapter 宣称为正式 UI |
| 冲突分类 | 无 `LOCAL DEFECT`；发布表面差异为 `REGISTERED_DEVIATION`（逐项登记）；**无** `CENTRAL CONTRACT GAP` |
| 是否需改中央 Contract | 否。**本任务不涉及中央公共 Contract。** |

**Standard Issue**：不存在新的标准问题。台账仍只有 `EQP-STD-GB19762-001`
（`as_of` 与标准实施日期），已 `RESOLVED`。本 Phase **未改变**任何既有软件解释，
也未新增标准问题——`evaluation_service.py` 的既有 `as_of` 门禁**未被修改**
（原因见 §6）。

**证据口径（不得误述）**：仍是**一个 GB19762 产品级 E2E 样板，其中有
`water` + `chemical` 两个真实内部 rule profile**，**不是**两个独立设备/标准样板。

## 1. G00 — Phase 5 治理收口与 Phase 6 rebaseline

新增极简 [docs/phase5_acceptance_record.md](docs/phase5_acceptance_record.md)：

| 记录项 | 值 |
|---|---|
| Phase 5 | `PHASE_5_PASS` |
| accepted head | `b064acf8f889c2c86335a8233eaf3eb8eb53f47b` |
| PR | `#13` |
| merge SHA | `f3e32f84123937ed6caa2b84b7cc0cd04c3100e0` |
| acceptance date | 2026-10-02 |

来源说明明确写出：**Phase 5 PASS 为产品负责人收到独立验收后作出的验收决定，
不是执行者自行宣告 PASS**；并如实记录第一次独立验收对 head `ead1eca` 给出的
`PHASE_5_BLOCKED`（阻断项为执行报告缺失）及随后的补齐与重新 CI 经过。

同步状态：`Phase 5 = PHASE_5_PASS` / `Phase 6 = IN_PROGRESS`；
`pump_chemical` = `scope_status = IN_V1` / `support_status = SUPPORTED` /
`standard_maturity = SUPPORTED`。同步文件：`AGENTS.md`、`HANDOFF.md`、
`ROADMAP.md`、`REFERENCE_STANDARD_ROADMAP.md`、`TASK_STATE.md`、`V1_SCOPE.md`、
`README.md`、`UI_CURRENT_STATE_AUDIT.md`、`QA_BACKLOG.md`。

**`UI_CURRENT_STATE_AUDIT.md` 已按当前 Qt 实现重新盘点**：五个一级页面、结果五层
层级、搜索筛选、设置/关于均为当前事实；历史 Tk 事实移入 §11 并明确标注
**historical**，不再作为当前 UI 事实引用。

**正式承接的 Phase 5 QA 项**（**不是**只写"继承 deviation"）：

| 编号 | Phase 6 真实处置 | 结论 |
|---|---|---|
| `QA-P5-001` | 定位到 `evaluation_service.py` 的 `pump_chemical` 硬编码短路；实测改动会破坏 Golden provenance（见 §6） | **仍 OPEN**，附 blocker `QA-P6-002` |
| `QA-P5-002` | (a) legacy Tk `--gui` **已真实收口**（断开启用、删除 Web fallback）；(b) `--web` 受同一冻结约束 | **(a) 已关闭 / (b) 仍 OPEN** |
| `QA-P3-003` | 确认旧 `as_of` 门禁位于被冻结的 `evaluation_service.py` | **仍 OPEN**，附 blocker `QA-P6-002` |

**草稿 identity 问题已登记**：`QA-P6-003` — 「名称即 ID / 改名等价于新建」。
经真实代码复核**确实存在**（`save_workspace_from_request(self.draft_name.text(), …)`
以用户输入的名称作为 `workspace_id`；改名即新建草稿，同名新建会覆盖并重置修订链）。
**Phase 6 不修改** Workspace identity 或 records schema（`records_migrations.py`
未改动，`schema_version` 保持 2），`disposition` 指向 Phase 7。

## 2. G01 — 正式 AppShell + 启动入口 + 最小导航契约

**Owner 决定已实施：Tk GUI 不再使用。**

| 入口 | Phase 6 行为 |
|---|---|
| 无参数启动 | 进入 PySide6 Qt Desktop（不再打印"已就绪"提示） |
| `--gui` | 进入 PySide6 Qt Desktop（不再启动 Tk） |
| `--qt` | 保留为显式兼容别名，进入同一 Shell |
| Tk 不可用时 | **不再**回退到 Web（`_run_web_fallback` 已删除） |
| `--web` / `--json` / `--jsonl` | 仍可用，但属非正式 adapter，**不得**宣称为正式 Windows UI |

一级导航：`首页 / 标准库 / 新建分析 / 分析记录 / 设置`；**不提前加入**
`Excel 导入`（Phase 8）与 `参数库`（GB 19762 无独立用户参数库需求）。

- 删除 `pages/__init__.py` 的 `placeholder_page`，五个一级页面全部为真实页面。
- 删除所有"尚未在 Phase N 实现 / 功能预留 / 后续开发"等开发态文案。
- 最小导航契约（只做切页 / 选择目标对象 / 载入已有对象）：

```text
open_home() / open_standards(standard_code=None) / open_analysis(workspace_id=None)
open_records(record_id=None) / open_settings()
```

- **未引入**事件总线、通用 Router Framework、Page Base Class 体系、
  全局 DI 容器、导航状态机（测试固化该约束）。

**过程中发现并修复的真实回归**：`entrypoint.main(argv=None)` 时
`if not argv` 为真，导致 `main()` 无参调用（zipapp / `runpy` /
`python -m equipeffi`）误入 Qt 事件循环，把 `--status` / `--jsonl` 路径吞掉
并**挂起**。已修正为显式规范化 `argv`（`None` 表示"按控制台参数"，不等于"无参数"），
并新增回归测试 `test_none_argv_means_console_arguments_not_empty`。

## 3. G02 — 首页 + 标准库

**首页**只承载真实高价值任务：开始新的离心泵分析 / 继续最近草稿 /
打开最近正式记录 / 查看当前正式标准。

- **复用**现有 `list_workspaces()` 与 `list_records()`；
  未新增 records schema，也未建立第二套 persistence。
- 不做 KPI / Dashboard / 无业务价值图表（测试固化）。
- 空状态显示「暂无草稿」「暂无正式记录」并置灰按钮，不显示开发态文案。

**标准库**成为真实产品页面，展示：标准号、标准名称、状态、实施日期、数据版本、
支持类别、软件支持状态、官方来源、替代关系、生命周期提示，并提供
「基于该标准开始分析」。

**数据来源链**：所有标准事实来自**最小 Application read model**
`CentrifugalPumpAnalysisService.standard_overview()`，它组合的是既有权威数据
（Canonical 标准包 + 本模块类别目录 + 发布门禁）。**未**重构 Canonical / Domain。

**禁止项已在测试中固化**：Presentation 不得自维护第二份标准表、不得解析
Markdown/PDF 决定运行时业务真值、不得硬编码第二套标准数据、不得引入
`open()` / `read_text` / `.pdf` / `.md` / `sqlite` 等第二数据源行为。

替代关系数据当前不可得时**如实说明**「当前标准数据未提供废止或被替代关系信息」，
而不是留空或编造。

## 4. G03 — AnalysisPage 产品化

**未重写**统一分析页：`pump_water` 与 `pump_chemical` 仍是同一产品、
同一类别选择器、同一 Application Use Case、单页优先；evaluator / routing /
Workspace / Finalize 全部沿用。

Phase 6 只做**产品信息层级规范化**（五层）：

```text
第一层：最终结论 / 等级 / 不适用 / 无法判定（含判定说明）
第二层：关键实际值与对应限值（用户可理解名称，如「1级能效效率限值（%）」）
第三层：普通工程语言解释「为什么是这个结果」
第四层：所选标准及已有标准依据（标准号、名称、数据版本、依据、关键计算参数）
第五层：默认折叠的高级技术详情
```

- 第二 / 三 / 四层只用 Result Contract 已提供的信息；**未由 UI 发明业务解释**；
  契约未提供的信息（如"实际值 vs 限值"的完整对照）如未来需要，登记 Phase 7。
- 第二层把内部阈值键映射为 `THRESHOLD_DISPLAY_NAMES`，普通区不再出现 `1级效率_%`。
- 第三 / 四层不泄露内部 ID / JSON / Python 变量（测试逐 token 断言）。
- 第五层沿用既有 `CollapsibleSection`（默认**真正收起**），保留命中规则、
  规则集、标准包、数据版本、数值配置、结果契约、输入指纹等审计信息。
- 评价日期继续遵守 Owner 规则：自动记录本机日期；不匹配只给四字非阻断提醒；
  不改变 `evaluation_status` / `grade` / Finalize 权限；有测试断言
  （`as_of=2020-01-01` 仍为 `SUCCESS` 且提醒为「该标准尚未实施」）。

## 5. G04 / G05 — 分析记录 + 设置 / 关于

**分析记录**保留既有不可变 Record / Reopen no-recalc 语义，补齐：

- 搜索（记录编号 / 设备类别 / 标准 / 结论）；
- 按泵型筛选、按结论筛选（映射 `evaluation_status`）、按评价日期筛选；
- 打开记录详情：业务结果、关键输入、标准、评价日期、结论 / 等级、
  原等级阈值、原关键计算参数、原标准依据、保存时间、折叠技术详情。

**筛选只作用于快照里已有字段**，不新增 schema、不重算、不修改历史记录。
**历史 Record 完全按历史 snapshot 显示**：支持状态取自不可变快照本身，
因此 Phase 3/4 形成的 chemical Record 仍显示「当前版本未支持」，
**不追溯改写、不重算、不覆盖正式 Record**（有 `result_snapshot_json` 前后比对断言）。

**本阶段未实现**：完整 lineage、audit event、reproduce、历史重算、
复杂 Attempt history、「基于历史记录重新开始」——全部属 Phase 7。

**设置 / 关于**：只显示真实可配置项（`log.level` 为真实持久化偏好），
并提供应用版本、当前正式标准、数据存储位置、应用设置项等运行信息。
普通用户**不得**设置 Numeric precision / rule profile / calculator / internal ID /
canonical version / 算法开关（测试逐 token 断言）。**未提前做** installer / updater。

## 6. G06 — Phase 5 遗留入口 / Application 语义收口（**部分完成，附明确 blocker**）

本轮对 G06 的要求做了**真实处理**，但其中一部分**在 Phase 6 权限内无法完成**，
原因是一条本次实测发现的治理约束。

### 已真实完成

| 项 | 结果 |
|---|---|
| Tk GUI 正式退出 | `--gui` 不再启动 Tk；`launcher.py` 不再导出 `launch_packaged_gui`；删除 Tk→Web fallback；新增测试断言 |
| 无参数 / `--gui` / `--qt` 一致 | 三者进入同一 Qt Shell |
| Web / JSON / JSONL 定位 | 明确为 compatibility / development surface，**未**升级为正式入口 |
| V4 / Excel | 保持 Phase 8 disposition，**未**在本阶段收口 |
| Android / installer / signing | 保持 Phase 9 disposition |
| 入口回归修复 | 修正 `argv=None` 语义 bug（见 §2） |

### 无法在 Phase 6 完成的部分（`QA-P5-001`、`QA-P5-002(b)`、`QA-P3-003`）

`pump_chemical` 在**共享 Application/CLI 语义**中仍被短路为
`NOT_IN_RELEASE_SCOPE`；遗留 `as_of` 门禁也仍在。原因是：

1. 短路点与 `as_of` 门禁都位于
   `src/equipeffi/application/services/evaluation_service.py`。
2. 该文件被**候选层 Golden 的实现哈希 pin 冻结**：
   `specs/equipment_efficiency/golden/pump_e2e_v0_3_candidates.jsonl` 的
   `source_sidecar.source_references` 用 `artifact_sha256` 冻结了 10 个实现文件
   （`evaluation_service.py`、`input_normalization.py`、`evaluators/pump.py`、
   `device_evaluators.py`、`decimal_math.py`、`device_types.py`、
   `evaluator_registry.py`、`json_repository.py`、`resources/standards/pump.json`）。
3. **18 条已批准 `pump_water` Golden** 用 `provenance.source_candidate_sha256`
   锚定**候选记录**的规范化哈希（`tools/validate_phase1_contracts.py` 的
   `_provenance_errors`）。因此**修改候选文件里的实现哈希 pin** 会立刻使这些
   批准 Golden 的 provenance 校验失败。

**实测证据（可复现）**：把候选文件中
`impl-application-services-evaluation_service` 的 `artifact_sha256` 更新为当前
实现哈希后，`test_golden_case_0_4_approval`（6 项）与
`test_phase3_r2_final_closure`（1 项）共 **7 项**失败；回退后全部恢复通过。

**因此**：Phase 6 **未修改** `evaluation_service.py`，相关改动已回退，
三项 QA **保持 OPEN** 并附具体 blocker。该重基线属"Approved Golden 证据变化"，
是 **Owner 决策项**（`AGENTS.md` §2.0 第 3 类），Phase 6 执行者无权自行决定，
故登记 `QA-P6-002`（`BLOCKER`，disposition Phase 7）。

> 附注：批准层自身的实现哈希校验是**历史锚定**的（校验
> `provenance.source_baseline_sha` 提交而非工作区），因此**不会**因后续重构失效；
> 受影响的只有候选层。

## 7. G07 — 整体产品 Shell 回归与证据

新增 [tests/unit/test_phase6_product_shell.py](tests/unit/test_phase6_product_shell.py)（44 项），
覆盖：

- 启动：无参数 / `--gui` / `--qt` 进入同一 Qt Shell；`argv=None` 语义；
  `--gui` / `--qt` 拒绝与业务输入并用；legacy Tk 不再是入口。
- AppShell：五页均为真实页面且为真实页面类；`placeholder_page` 已不存在；
  无开发态文案；一级导航不含 Excel / 参数库；导航契约只切页与选对象；
  未引入事件总线 / Router / Page 基类 / DI 容器。
- 首页：四能力；复用 `list_workspaces()` / `list_records()`；
  跨页导航；继续最近草稿；无 KPI/Dashboard。
- 标准库：事实来自 Application read model；支持类别与支持状态；
  开始分析；无第二标准表 / 无 Markdown·PDF 解析；替代关系如实说明。
- Analysis：water / chemical 五层；普通层不泄露内部标识；
  技术详情保留审计能力；用户可理解阈值名称；评价日期非阻断。
- Records：搜索与三类筛选；按结论筛选基于快照状态；历史快照不漂移；
  Reopen 不重算（`evaluate` 被 patch 为抛错）；历史支持状态取自快照；
  未实现 lineage / audit / reproduce。
- Settings：只暴露真实可配置项；不暴露算法契约；显示当前标准；
  日志级别真实持久化；无 installer / updater。
- QA 处置：`QA-P5-001`/`002` 的 blocker 有可复现断言；
  `QA-P3-003` 的旧门禁仍存在；**受保护实现文件相对 base 与工作区均零改动**。

**机械门禁**（已在测试中固化）：

1. 正式 Qt Shell 运行页面中不存在 `placeholder_page`；
2. 普通用户 UI 不出现 `pump_water` / `pump_chemical` / `rule_profile` /
   `matched_rule_id` / `internal_id` / `field_id` / canonical / Numeric Profile /
   Python 变量（除非位于明确折叠的技术详情区）；
3. Base→Head 未无授权修改 Golden 业务真值 / Canonical pump 业务数据 /
   Numeric Profile / pump formula·boundary·grade / platform-lock / Frozen Contract；
4. `records_migrations.py` **未修改**（无 schema 变更，`schema_version` 保持 2）；
5. 未新增第二套标准事实源或第二套评价算法。

## 8. 本地实际结果

```text
tests.unit.test_phase6_product_shell                     44   全通过（本 Phase 新增）
tests.unit.test_phase5_chemical_stage_d                  27
tests.unit.test_phase2_qt                                 8
tests.unit.test_phase3_qt_unified                        33
tests.unit.test_phase3_golden_and_boundaries             14   （18 water + 11 chemical 回放）
tests.unit.test_phase3_r2_final_closure                  11   （Finalize 状态矩阵 + 历史 provenance）
tests.unit.test_phase3_r3_as_of_lifecycle                18
tests.unit.test_phase3_r3_closure                        31   （Workspace / Record / Reopen）
tests.unit.test_phase4_lifecycle_generalization          20
tests.unit.test_phase4_fingerprint_decoupling            10
tests.unit.test_golden_case_schema_0_2                    4
tests.unit.test_golden_case_0_4_approval                 17   （批准层 provenance）
tests.unit.test_evaluation_engine                       110
tests.unit.test_pump_golden_case_0_3                      6
tests.unit.test_application_api                          82
tests.unit.test_entrypoint                               33
tests.unit.test_desktop_form_model                      110
tests.unit.test_zipapp                                    2
tests.unit.test_jsonl_smoke                               2
tests.contract.test_architecture_boundaries              12
```

其他门禁：

```text
全量 unittest                          1238 run / 1231 pass / 3 fail / 1 error / 3 skip
known-regression comparator            gate=PASS
                                       new_failures=0 new_errors=0 worsened=0 missing=0
compileall -q src tools                exit 0
python tools/smoke_jsonl.py            passed=true
git diff --check                       clean
```

既有失败仍是既有失败（3 项 V4 reader/writer + 1 项 release audit 错误），
**未修复也未隐藏，且未把任何新失败加入 known baseline**。

## 9. 实际 GitHub CI / workflow 结果

见 PR 中该 final Head 对应的 Required CI。门禁任务：

```text
Windows Core          → Windows Core (gating) / Whitespace check (gating) / Full suite baseline (NON-GATING)
Pump Conformance      → Pump Conformance (gating)
```

本 Phase 已把 `tests.unit.test_phase6_product_shell` 接入
`windows-core.yml` 的 offscreen 步骤，并把 Stage D 步骤更名为
`pump_chemical Stage D support + Phase 6 product shell (gating)`。

## 10. Base → final Head diff 与 changed files

权威数字以 PR 的 diff 为准（本报告自身也在该 diff 内，属自指）。

主要新增：

| 文件 | 说明 |
|---|---|
| `src/equipeffi/presentation/qt/pages/home.py` | 首页真实页面 |
| `src/equipeffi/presentation/qt/pages/standards.py` | 标准库真实页面 |
| `src/equipeffi/presentation/qt/pages/settings.py` | 设置 / 关于 / 运行信息 |
| `tests/unit/test_phase6_product_shell.py` | Phase 6 专项测试（44 项） |
| `docs/phase5_acceptance_record.md` | Phase 5 极简验收落档 |
| `PHASE6_EXECUTION_REPORT.md` | 本报告 |

主要修改：

| 文件 | 说明 |
|---|---|
| `main.py` | 无参数启动进入产品 Shell |
| `src/equipeffi/entrypoint.py` | 无参数 / `--gui` / `--qt` 同一入口；修正 `argv=None` 语义 |
| `src/equipeffi/presentation/desktop/launcher.py` | 断开 Tk 与 Web fallback |
| `src/equipeffi/presentation/qt/shell.py` | 五页真实接线 + 导航契约 |
| `src/equipeffi/presentation/qt/navigation.py` | 导航契约 |
| `src/equipeffi/presentation/qt/pages/__init__.py` | 删除 `placeholder_page` |
| `src/equipeffi/presentation/qt/pages/analysis.py` | 五层结果层级 + 页面标题 + navigator |
| `src/equipeffi/presentation/qt/pages/records.py` | 搜索 / 筛选 / navigator |
| `.github/workflows/windows-core.yml` / `pump-conformance.yml` | 接入 Phase 6 测试 |
| `tests/unit/test_phase2_qt.py` / `test_phase3_qt_unified.py` / `test_entrypoint.py` / `tests/contract/test_architecture_boundaries.py` | 断言更新为 Phase 6 真实行为 |
| `AGENTS.md` / `HANDOFF.md` / `ROADMAP.md` / `REFERENCE_STANDARD_ROADMAP.md` / `TASK_STATE.md` / `V1_SCOPE.md` / `README.md` / `UI_CURRENT_STATE_AUDIT.md` / `QA_BACKLOG.md` | 治理与状态同步 |

**受保护资产零漂移**（`git diff` 核验为空）：18 条 water + 11 条 chemical Approved
Golden 业务真值、Canonical `resources/standards/pump.json`、Numeric Profile、
pump formula/boundary/grade、`platform-lock.json` / `PLATFORM_BASELINE.md`、
known baseline、`records_migrations.py`、候选层 Golden 实现哈希 pin。

## 11. Phase 6 Exit Gate 自检

| Exit Gate 条件 | 结果 |
|---|---|
| Phase 5 PASS 已极简落档 | PASS |
| Qt 为唯一正式 Windows Desktop Shell | PASS |
| 无参数 / `--gui` / `--qt` 均正确进入 Qt | PASS |
| Tk 正式运行路径已退出（含无 Web fallback） | PASS |
| 五页均为真实页面 | PASS |
| 无运行时 placeholder / 开发态占位文案 | PASS |
| 跨页导航真实工作 | PASS |
| 首页现有 Workspace / Record 能力可用 | PASS |
| 标准库不制造第二真值源 | PASS |
| Analysis 普通层与技术层清晰分离 | PASS |
| Records 搜索/筛选/详情可用且历史快照不漂移 | PASS |
| `QA-P5-001` / `QA-P5-002` / `QA-P3-003` 已按真实证据关闭**或给出明确不能关闭的 blocker** | PASS（`QA-P5-002(a)` 关闭；其余附 blocker `QA-P6-002`） |
| 29 条 Approved Golden 零业务漂移 | PASS |
| Canonical / Numeric / Record / Reopen 零漂移 | PASS |
| Phase 7 / 8 / 9 职责未提前实现 | PASS |
| 实际执行 Windows Core / Pump Conformance / comparator / Qt offscreen / compileall / `git diff --check` | PASS |
| Required CI 无新增未知 regression | 见 §9 |

## 12. 状态

```text
Phase 6 implementation = EXECUTION_COMPLETE
READY_FOR_INDEPENDENT_ACCEPTANCE
```

**不合并 PR。不自宣 `PHASE_6_PASS`。不进入 Phase 7。**

## 13. Final Head

独立验收的**唯一对象**：本报告所在提交的 head（见 PR 的 head SHA）。

报告完成后**不得**再向该分支追加提交。如 Head 改变，必须重新声明新的 final Head、
重新执行必要测试，并等待该 Head 对应的 CI。

---

# Phase 6 R1 — Independent Acceptance Blocker Fixes

针对独立验收对 head `df7ba11b9a107e54eb737851263b9239ba8a593f` 提出的 3 个 blocker。
Base 仍为 `f3e32f84123937ed6caa2b84b7cc0cd04c3100e0`；继续在 PR #14 上修复。

## R1-B1 — 真正关闭 3 条入口语义 QA

### 根因（先查清，不把 pin 当作再次延期的理由）

需求明确要求先查清 candidate provenance 的历史证据语义、Approved Golden 的
`source_candidate_sha256` 语义，以及 validator 为什么把历史候选证据与当前实现锁死。

审计结论：

1. **候选层哈希是历史证据**：`pump_e2e_v0_3_candidates.jsonl` 的
   `source_sidecar.source_references` 记录了 0.3 候选冻结时（提交
   `72e8e49` / `90af7f8`）的 10 个实现文件快照。
2. **批准层锚定候选记录，而非实现文件**：18 条已批准 `pump_water` Golden 用
   `provenance.source_candidate_sha256` 锚定**候选记录的规范化哈希**。
   因此只要候选记录内容不变，批准层 provenance 恒成立。
3. **validator 本就内置了正确机制**：`tools/validate_phase1_contracts.py` 的
   `_historical_hash_reason` 会查
   `specs/equipment_efficiency/evidence_registry.json` 的
   `historical_repository_hashes`，命中即把工作区差异**记为历史 provenance 而不是错误**
   （第 334–341 行）。注册表内**既有一条** `golden-case-0.3` 记录，其 reason 已写明
   *later implementation changes must not invalidate already-recorded candidate provenance*。
4. **真正的缺口**：该登记只覆盖了 `json_repository.py`，**未覆盖
   `evaluation_service.py`**。所以问题不是"实现被永久冻结"，而是"历史证据登记不完整"。

因此采用需求指定的方向：**历史证据保持不可变，当前实现可以演进，
验证逻辑正确区分 historical provenance 与 current implementation**。

### 修复

1. **补登记历史证据**（`specs/equipment_efficiency/evidence_registry.json`）：
   为 `src/equipeffi/application/services/evaluation_service.py` 增加一条
   `golden-case-0.3` / `historical_repository_hashes` 记录，哈希为
   `EEF8731E5A162C81441D83BAC4C493D0F9EA5A0014CEC1E44BF5E82535DEB8ED`。
   该值已在冻结提交 `72e8e49` 处**实测复核一致**（仓库文本哈希规则：
   UTF-8 → CRLF→LF → SHA-256 大写）。
2. **实现演进**（`evaluation_service.py`）：
   - 删除石化泵硬编码短路块（`PROFILE_NOT_IN_RELEASE_SCOPE`）；
   - 新增共享发布门禁单一事实源
     `application/services/pump_release_gate.py`
     （`PUMP_RELEASE_SUPPORT` / `pump_release_support` / `PUMP_RULE_PROFILES`），
     由 `CentrifugalPumpAnalysisService` 与 `EvaluationService` **共同**使用；
   - 离心泵（`pump_water` / `pump_chemical`）**豁免**旧 `as_of` 门禁
     （`internal_device_type in PUMP_RULE_PROFILES` 时不再短路标准评价）；
     该门禁仍保留给其他 Profile，本 Phase 不为它们改语义。

**未做**：未改写候选文件；未改写任何 Approved Golden 的业务真值或历史 provenance；
未静默改变历史审批含义。唯一新增的是一条历史实现哈希登记。

### 关闭证据（实测）

| 入口 | `as_of=2026-08-23` | `as_of=2026-02-28`（早于实施日） |
|---|---|---|
| 正式纵向切片（Qt 所用） | `SUPPORTED` / `2级` | `SUPPORTED` / `2级` |
| `--json` CLI（`centrifugal_pump`） | `SUPPORTED` / `2级` | `SUPPORTED` / `2级` |
| `ApplicationApi` | `SUPPORTED` / `2级` | `SUPPORTED` / `2级` |
| `--web` / JSONL | 同链路（`ApplicationApi` → `EvaluationFacade` → `EvaluationService`） | 同左 |

三项 QA 均改为 `CLOSED`（见 `QA_BACKLOG.md` 各自 `closed_by`）：
`QA-P5-001`、`QA-P5-002(a)(b)`、`QA-P3-003`；连带 `QA-P6-002` 一并关闭。

## R1-B2 — 标准库生命周期提示

**问题**：标准库无条件显示"该标准尚未实施"（`standard_overview` 硬编码该字符串）。
实际 GB 19762—2025 的实施日期为 `2026-03-01`，当前已实施，该显示是错的。

**修复**：

- 删除硬编码。新增基于**真实日期**的推导：
  `_standard_lifecycle_state(pack, as_of)` 返回
  `NOT_YET_EFFECTIVE` / `EFFECTIVE` / `UNKNOWN`；
  `_standard_lifecycle_warning(pack, as_of)` 只在 `NOT_YET_EFFECTIVE` 时返回
  「该标准尚未实施」，否则返回空串。
- `standard_overview(*, as_of=None, show_lifecycle_warning=False)`：
  `as_of` 默认取**本机当天**，使 `lifecycle_state` 反映当前真实状态；
  标准库展示的是当前标准事实，因此**默认不显示**提示文案。
- 标准库页面改为显示「生命周期状态：已实施 / 尚未实施 / 未提供实施日期」，
  仅在确有提示时追加提示行；**不再**硬编码结论。
- 现行 Canonical Pack 未提供废止 / 替代元数据，因此**不推测**
  「已废止 / 已被替代」（补齐须走标准映射流程，仍登记 `QA-P3-002`）。
- 提示仍**非阻断**：不改变 `evaluation_status` / `grade` / Finalize 权限。

**机械测试**（`StandardLifecycleNoticeTests`）：`2026-02-28` → `NOT_YET_EFFECTIVE`
且提示为「该标准尚未实施」；`2026-03-01`（实施日当天）与 `2026-03-02` → `EFFECTIVE`
且提示为空；当前日期不显示"尚未实施"；标准库源码不含硬编码字符串；
不推测废止 / 替代；早于实施日仍为 `SUCCESS` 且 Finalize 可用。

## R1-B3 — Settings 正式页面

**问题**：设置页把 `SettingsService.KEYS` 直接拼进 UI，普通用户看到
`last.directory` / `window.geometry` / `window.state` / `log.level` 等内部机器键名；
且正式 composition **从未**传入数据目录（此前只有测试手工注入 `data_location`，
掩盖了未接线）。

**修复**：

- 删除 UI 中的内部键名展示。运行信息改为：
  「数据存储位置：<真实路径>」+ 一句业务说明（记录/草稿在 `records.sqlite`、
  日志在 `logs` 子目录）。
- 「上次使用的目录」不再暴露键名；未使用时显示「（尚未使用）」。
- **正式接线**：`composition.launch_qt` 解析 `AppDataPaths`（`paths` 或
  `AppDataPaths.default()`），经 `app.run(..., data_location=...)` →
  `MainWindow(data_location=...)` → `SettingsPage`，一路传到页面。
  数据目录无法确定时显示「（未能确定，请检查安装）」而不是静默留空。
- 窗口 geometry / state 不作为普通用户设置展示。
- **测试改为走正式 composition 路径**：`window()` 不再手工注入 `data_location`，
  改为调用镜像 `launch_qt` 装配的 `_launch_window`；
  新增 `SettingsCompositionWiringTests` 断言 `launch_qt` 确实传入真实路径，
  并断言页面显示该路径、不出现内部键名、源码不再拼接 `KEYS`。

## R1 回归保护

除上述 blocker 修复外**未扩大 Phase 6 scope**。已重新执行：

```text
Phase 6 专项（含 R1 新增）        62 项，全通过
入口 / Application 相关            test_entrypoint / test_application_api /
                                   test_evaluation_engine / test_pump_golden_case_0_3
Golden / Pump Conformance          test_phase3_golden_and_boundaries /
                                   test_golden_case_schema_0_2 /
                                   test_golden_case_0_4_approval /
                                   test_phase3_r2_final_closure
Windows Core / Qt offscreen        test_phase2_qt / test_phase3_qt_unified / test_zipapp
全量 unittest                      1256 run / 1249 pass / 3 fail / 1 error / 3 skip
known-regression comparator        gate=PASS（new_failures/new_errors/worsened/missing 全 0）
compileall -q src tools            exit 0
git diff --check                   clean
```

继续保护且**零漂移**：18 water + 11 chemical Approved Golden 业务真值、Canonical、
Numeric、pump formula/boundary/grade、Finalize、Workspace、Record immutability、
Reopen no-recalc、`platform-lock`、`records_migrations.py`。

## R1 状态

```text
Phase 6 R1 implementation = EXECUTION_COMPLETE
READY_FOR_REACCEPTANCE
```

**不合并 PR。不自宣 `PHASE_6_PASS`。不进入 Phase 7。**

## R1 实际 GitHub CI 结果

最终 head 的 Required CI（全部 `success`）：

```text
Windows Core
  [ 6] Compileall                                                          success
  [ 7] Architecture boundaries and metadata contract                       success
  [ 8] Application and core tests                                          success
  [ 9] Phase 2/3/4/5/6 settings, lifecycle, Stage D, Product Shell, Qt offscreen (gating)  success
  [10] Full suite known-regression comparator (gating)                     success
Pump Conformance
  [12] pump_chemical Stage D support + Phase 6 product shell (gating)      success
Whitespace check (gating)                                                  success
Full suite baseline (NON-GATING)                                           success
```

### R1 过程中发现并修复的一个 CI-only 缺陷（如实记录）

R1 首次推送后 `Windows Core` 的 gating 步骤失败，但**本机以完全相同的模块列表、
在默认 TEMP 下运行 231 项全部通过**。由于该仓的 GitHub token 只有 `gho_` 级别、
缺少 `actions:read`：job log（`/actions/jobs/{id}/logs`）返回 401，artifact 下载
同样 401，step summary 由前端 JavaScript 渲染因而无法直接抓取。

定位手段：先用「逐模块拆分诊断步骤」确认**每个模块单独通过、合并调用也通过**，
从而排除测试与算法问题；随后改用 **workflow `::error::` 注解**，经
`GET /repos/{owner}/{repo}/check-runs/{id}/annotations`（该接口可用）取得真实错误：

```text
ERROR: test_cli_json_entrypoint_returns_supported_for_chemical
UnicodeDecodeError: 'charmap' codec can't decode byte 0x81 in position 403
```

根因：新增的 CLI 子进程测试用 `subprocess.run(text=True)` 读取 `main.py` 输出却
**未指定编码**。本机默认编码为 UTF-8，CI runner 的默认代码页不是，中文结论因此
触发 `charmap` 解码失败。该测试在本地恒通过，故此前未被发现。

修复：`subprocess.run(..., encoding="utf-8")` 并显式设置子进程
`PYTHONIOENCODING="utf-8"`。同时**移除全部临时诊断脚手架**；gating 步骤改为
pwsh 显式模块数组（与原先的单行命令等价，行为不变）。

教训：任何跨进程读取中文输出的测试都必须显式指定编码，不得依赖平台默认代码页。
