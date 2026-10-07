# 当前 UI 状态盘点

> **Phase 6 重新盘点；Phase 7 已按新的分析流程事实更新。** 本文档此前记录的是 Phase 2 时期的 **legacy Tkinter / ttk**
> 窗口事实。自 Phase 6 起，Windows V1 的正式桌面 Shell 是 **PySide6 Qt Desktop**，
> 因此本文档已**按当前 `master` 的真实 Qt 实现重新盘点**。
>
> 历史 Tk 事实保留在 §11（标注 **historical**），**不得**再作为当前 UI 事实引用。

Reference Standard：`GB 19762—2025 离心泵能效限定值及能效等级`

状态：**Phase 6 盘点（按 Qt 实现）**

## 1. 审计依据与边界

- 审计对象：`src/equipeffi/presentation/qt/`（正式桌面 Shell）。
- 启动入口：`main.py` → `equipeffi.entrypoint.main`；无参数 / `--gui` / `--qt`
  都进入 `equipeffi.composition.launch_qt`（唯一正式入口）。
- 事实来源：当前代码 + `tests/unit/test_phase6_product_shell.py`（Phase 6 专项测试）
  + `tests/unit/test_phase2_qt.py` / `test_phase3_qt_unified.py` / `test_phase5_chemical_stage_d.py`。
- 本文件**只描述现状**，不构成重构授权；也不改变业务结论、Phase 门禁或锁文件。

## 2. A — 技术栈

| 项 | 事实 |
|---|---|
| 正式桌面技术栈 | **PySide6（Qt）** |
| 入口模块 | `src/equipeffi/presentation/qt/app.py`（`run`）、`shell.py`（`MainWindow`） |
| 页面模块 | `pages/home.py` / `standards.py` / `analysis.py` / `records.py` / `settings.py` |
| 公共组件 | `widgets/collapsible.py`（默认收起的折叠区）、`tokens.py`（尺寸令牌）、`labels.py`（中文文案表）、`navigation.py`（一级导航 + 极小导航契约） |
| 窗口状态 | 经 `SettingsService` 持久化 `window.geometry` / `window.state`（base64） |
| legacy Tk | `presentation/desktop/main_window.py` **保留但不接线**，不是任何用户入口（见 §11） |

## 3. B — 当前导航

一级导航固定五项，顺序即产品任务顺序：

```text
首页 → 标准库 → 新建分析 → 分析记录 → 设置
```

- **五项都是真实页面**；`placeholder_page` 已删除，运行时不存在占位页。
- 不含 `Excel 导入`（属 Phase 8）、不含 `参数库`（GB 19762 无独立用户参数库需求；
  标准参数 / 限值 / 依据归「标准库 → 标准详情」）。
- 跨页导航契约极小，只有五个方法，只承担「切页 / 选择目标对象 / 载入已有对象」：

```text
open_home()
open_standards(standard_code=None)
open_analysis(workspace_id=None)
open_records(record_id=None)
open_settings()
```

- **未引入**：事件总线、通用 Router Framework、Page Base Class 体系、
  全局 DI 容器、导航状态机。

## 4. C — 首页

| 项 | 事实 |
|---|---|
| 承载任务 | 开始新的离心泵分析 / 打开最近历史记录 / 查看当前正式标准（Phase 7 起**无草稿入口**） |
| 数据来源 | **复用**现有 `list_records()`；未新增 records schema，也未新增第二套 persistence |
| 空状态 | 显示「暂无正式记录」，打开按钮置灰 |
| 不做 | 不堆 KPI / Dashboard / 无业务价值图表 |
| 导航 | 「开始新的离心泵分析」→ 新建分析；「查看当前正式标准」→ 标准库；双击记录可直达该记录 |

## 5. D — 标准库

真实产品页面，展示当前正式标准并允许基于它开始分析。

| 展示项 | 事实 |
|---|---|
| 标准号 / 标准名称 | `GB 19762-2025` / `离心泵能效限定值及能效等级` |
| 状态 / 实施日期 / 数据版本 | 来自标准包 |
| 支持类别 | 来自 Application 类别目录 |
| 软件支持状态 | 来自发布门禁，用中文显示（「正式支持」/「当前版本未支持」） |
| 生命周期状态 | 由**真实日期**（本机当天 / 给定评价日期）与 Canonical `effective_date` 推导，不硬编码 |
| 官方 / 权威来源 | 标准包 `source_file` |
| 替代关系 | 当前标准数据未提供 → **如实说明**，不编造 |
| 生命周期提示 | 仅当评价日期**早于**实施日期时显示「该标准尚未实施」；达到实施日期后不显示（仅提示，不阻止计算） |
| 动作 | 「基于该标准开始分析」 |

**数据来源链**：标准事实全部来自 **Application read model**
（`CentrifugalPumpAnalysisService.standard_overview()`），它组合的是既有权威数据
（Canonical 标准包 + 产品类别目录 + 发布门禁）。

**禁止（已在测试中固化）**：

- Presentation 自己维护第二份标准表；
- 解析 Markdown / PDF 决定运行时业务真值；
- 为展示方便硬编码第二套标准数据。

## 6. E — Reference Standard：GB 19762—2025 离心泵

### 6.1 页面数量

`新建分析` **单页**（`AnalysisPage`），内部用 `QScrollArea` 承载纵向内容；Phase 7 起该页**没有**分析草稿、评价日期输入、「保存为正式记录」与技术详情区；
`pump_water` 与 `pump_chemical` **共用同一页面、同一类别选择器、同一 Application
Use Case**（不做成两个产品）。

### 6.2 结果信息层级（Phase 6 规范化）

普通结果区按五层组织：

```text
第一层：最终结论 / 等级 / 不适用 / 无法判定（含判定说明）
第二层：关键实际值与对应限值（用用户可理解名称，如「1级能效效率限值（%）」）
第三层：普通工程语言解释「为什么是这个结果」
第四层：所选标准及已有标准依据（标准号、名称、数据版本、标准依据、关键计算参数）
（Phase 7 起分析页不含技术详情；内部证据继续保存在 Result / Record，审计入口在「分析记录」）
```

- 第二 / 三 / 四层只用 Result Contract 已提供的信息；**不由 UI 发明业务解释**。
  若所需信息契约未提供，登记 Phase 7，不得在 UI 内推导。
- 第五层（`CollapsibleSection`，默认**真正收起**）保留 `rule_profile` /
  `matched_rule_id` / `ruleset_version` / canonical 数据版本 / Numeric Profile /
  calculator 版本 / 结果契约 / 输入指纹 / 草稿修订号 —— 审计能力不删。

### 6.3 必填输入

类别、规定点流量 `Q_BEP`、规定点扬程 `H_BEP`、规定点转速 `n`、规定点泵效率 `η`、
吸入方式；级数在多级类别下启用。企业 / 项目名称、设备编号为可选。

### 6.4 可自动生成或默认的信息

- **评价日期自动记录本机当前日期**（Phase 7 起页面不显示、用户不可填；仅用于历史追溯）。
- 记录编号在 Finalize 时生成。

### 6.5 内部字段泄露

**普通用户界面不得出现** `pump_water` / `pump_chemical` / `rule_profile` /
`matched_rule_id` / `internal_id` / `field_id` / canonical 版本 / Numeric Profile /
原始 JSON / Python 变量；这些只允许出现在**明确折叠的技术详情区**。
Phase 6 机械门禁在 `test_phase6_product_shell.py` 固化该约束。

### 6.6 技术信息位置

折叠区（第五层），默认收起；`is_expanded()` 可被测试断言。

### 6.7 结果醒目程度

结论位于结果区首位（第一层），使用标题级字号加粗。

### 6.8 结果解释

直接采用契约给出的 `explanation`，不另写一套判定理由。

### 6.9 标准依据

第四层显式给出所选标准、标准数据版本与标准依据文本。

### 6.10 生命周期提示（非阻断）

所选标准与评价日期不匹配时只显示**几个字**（如「该标准尚未实施」），
单独一行、样式弱化；**不改变** `evaluation_status`、`grade`、Finalize 权限，
也不自动切换标准版本，无复杂确认流程。

## 7. F — 分析记录

| 项 | 事实 |
|---|---|
| 列表 | 清水泵与石化泵记录在**同一列表** |
| 搜索 | 按记录编号 / 设备类别 / 标准 / 结论 |
| 筛选 | 按泵型、按结论（映射 `evaluation_status`）、按评价日期前缀 |
| 筛选作用域 | 只筛选**快照里已有字段**；不新增 schema、不重算、不修改历史记录 |
| 详情 | 业务结果、关键输入、标准、评价日期、评价结论 / 等级、原等级阈值、原关键计算参数、原标准依据、保存时间 |
| 技术详情 | 折叠区：评价状态、命中规则、类别状态、**支持状态（取自不可变快照）**、规则集、标准包、数据版本、数值配置、结果契约、输入指纹、草稿修订号 |
| 历史冻结 | Reopen **只读原快照**，不调用 evaluator、不按今天日期重算、**不追溯改写支持状态** |
| 不做（Phase 7） | 完整 lineage、audit event、reproduce、历史重算、复杂 Attempt history、基于历史记录重新开始 |

## 8. G — 设置 / 关于 / 运行信息

| 项 | 事实 |
|---|---|
| 真实可配置项 | 日志级别（`log.level`，真实持久化） |
| 只读信息 | 上次使用的目录、应用设置项清单 |
| 关于 | 应用版本、当前正式标准、适用产品 |
| 运行信息 | 数据存储位置（由正式 composition 解析并传入；用户不见内部机器键名） |
| **不得**作为用户设置或展示 | Numeric precision、rule profile、calculator、internal ID、canonical version、算法开关，以及 `last.directory` / `window.geometry` / `window.state` / `log.level` 等内部机器键名 |
| 不做 | 不提前做 installer / update system |

## 9. 问题登记

| 编号 | 内容 | 状态 |
|---|---|---|
| `QA-P6-001` | legacy Tk 实现保留但不接线；`main_window.py` 仍被表单模型测试引用，非零引用可盲删 | `REGISTERED_DEVIATION` → Phase 8 |
| `QA-P6-002` | 候选层 Golden 的历史实现证据登记缺口（曾被误判为实现文件被永久冻结） | `CLOSED`（Phase 6 R1：补登记历史哈希，实现可演进） |
| `QA-P6-003` | 草稿 identity「名称即 ID / 改名等价于新建」 | `REGISTERED_DEVIATION` → Phase 7 |
| `QA-P6-004` | 非正式 adapter 保留但未升级为正式 Windows UI | `REGISTERED_DEVIATION` → Phase 8 / 9 |
| `QA-P5-001` / `QA-P5-002` / `QA-P3-003` | 共享 Application/CLI 语义与旧 `as_of` 门禁 | `CLOSED`（Phase 6 R1） |

详见 `QA_BACKLOG.md`。

## 10. 三软件一致性观察

历史结论继续有效：本工具与另外两个青舟业务产品**不做像素级统一**，
各自在中央 `UI_DESIGN_GUIDELINES_V0.1.md` 的推荐模式内按自身真实用户任务组织页面。
Phase 6 **未**为三软件表面统一重构任何已正确的页面。

## 11. 历史 Tk 事实（**historical**，不再是当前 UI 事实）

以下为 Phase 2 时期记录的 legacy Tkinter / ttk 窗口事实，**仅供追溯**：

- 主窗口类 `EquipmentEfficiencyWindow`（`presentation/desktop/main_window.py`），
  使用 `tkinter` / `ttk`；含「设备类型」下拉、`as_of` 输入、淘汰判定口径下拉、
  参数填写区（`Canvas` + `Scrollbar`）、判定结果区与结果文本框。
- 其 `as_of` 输入曾参与"判定基准日期"语义。

**Phase 6 变化**：`--gui` 不再启动 Tk；该窗口不再是任何用户产品入口；
Tk 不可用时**不再**回退到 Web。实现与 `DesktopCallbacks` 辅助函数（表单模型、
`result_summary`、`capability_status_text` 等）仍被 `tests/unit/test_desktop_form_model.py`
引用，故按 Owner 规则保留并登记 `QA-P6-001`。

## 12. 最终摘要

- 正式 Windows 桌面 Shell = **PySide6 Qt Desktop**；无参数 / `--gui` / `--qt` 同一入口。
- 五个一级页面全部为真实页面，无 placeholder、无开发态文案。
- 首页复用现有 Workspace / Record 能力，未新增 persistence。
- 标准库无第二真值源，标准事实全部来自 Application read model。
- 分析页单页、双 rule profile 共用；结果五层分级，技术详情默认折叠。
- 记录页具备搜索与筛选；历史快照不漂移、Reopen 不重算。
- 设置页只暴露真实可配置项；关于 / 运行信息齐备。
- 未引入事件总线 / Router Framework / Page 基类体系 / DI 容器。

## Phase 8 增量：批量评价页

| 项 | 事实 |
|---|---|
| 页面 | `Excel导入`（`BatchPage`），Phase 8 新增的一级页面，真实页面、无 placeholder |
| 承载任务 | 输出空白模板 → 选择 Excel → 导入检查 → 批量评价 → 结果保存 → 批次总结 |
| 数据来源 | 正式 Application 契约 `PumpBatchEvaluationService`（复用同一个离心泵分析服务） |
| 结果呈现 | 数据行数 / 设备数量总计 / 完成正式评价台数；输入错误与执行失败行数；**按数量加权**的结论分布；需要关注的行；批次总结记录号；结果工作簿路径 |
| 刻意不做 | **不**逐 Sheet 询问行数、**不**要求扩容；容量由模板的 Excel Table 与语义式 Reader 承担 |
| 导航 | 一级导航顺序为 首页 / 标准库 / 新建分析 / **Excel导入** / 分析记录 / 设置 |

`新建分析`（单台）语义**未变**：一次合法分析 → 一条单台 Record。
Excel 批量评价**不**创建单台 Record，只形成**一条**批次总结记录。

## Phase 8 R1 增量：Qt 产品表面简化（Owner 决定）

| 变更 | 落点 | 是否影响业务 |
|---|---|---|
| UI01 术语简化 | `新建分析`：「规定点参数（BEP）」→「**设备参数**」；标签改为 流量 Q / 扬程 H / 转速 n / 泵效率 η；不再出现「规定点」与 `Q_BEP`/`H_BEP`/`η_BEP` | 否（仅 Presentation；内部字段名与计算契约未改） |
| UI02 结果区简化 | `新建分析` 结果区删除「判定说明」「为什么」「所选标准」「标准依据」；保留 最终结论/等级、**关键计算参数**、**对应等级效率限值**（限值 2 位小数显示） | 否（`explanation` / `references` 仍完整保存在 Result 与 Record） |
| UI03 记录页 | `分析记录` 详情**不再展示**「审计信息」区域 | 否（provenance / snapshot / hash / numeric profile / matched rule / canonical references 全部继续保存） |
| UI04 设置页 | 日志级别显示中文（调试 / 信息 / 警告 / 错误 / 严重错误，按严重程度排序），内部仍保存正式枚举值 | 否（未迁移 settings schema；映射可稳定往返恢复） |
