# AGENTS.md — EquipEffi Agent 纪律

> 中央规则只在中央保留完整正文；本仓只保留中央规则入口 + 本仓增量。

## 1. 仓库身份

- 产品：EquipEffi 设备能效分析工具（Module ID `qz.equipment_efficiency`）。
- Canonical repository：`https://github.com/adgo07/EquipEffi.git`。
- 当前 Reference Standard：`GB 19762—2025 离心泵能效限定值及能效等级`。
- 当前主要产品阶段：`EquipEffi V2.3` 下 `Phase 1 = PHASE_1_PASS`、`Phase 2 = PHASE_2_READY`。
- 本仓独立开发、发布、离线运行，不是中央仓的第四个业务产品。

### 1.1 仓库身份与本地执行环境

**仓库身份**以 GitHub owner/repository 与 `git origin` 为准，**不以本地文件夹名或绝对路径为准**：

| 仓库 | Canonical repository |
|---|---|
| 本仓（EquipEffi） | `https://github.com/adgo07/EquipEffi.git` |
| 中央治理仓（Qingzhou-contracts） | `https://github.com/adgo07/Qingzhou-contracts.git` |
| 兄弟业务仓 | `https://github.com/adgo07/ECQuota-Insight.git`、`https://github.com/adgo07/GHGTOOL.git` |

规则：

1. 本仓长期身份以 GitHub owner/repository + `git origin` 为准；**本地绝对路径只是当前运行环境，不是仓库身份**；
2. **不得**把某台电脑的 `C:\` / `D:\` / `E:\` / `G:\` 等绝对路径当成跨机器固定路径；
3. 历史 HANDOFF / 报告中的绝对路径只是**历史执行环境记录**，不得直接作为当前 checkout 地址；本仓历史文档中的盘符与目录记录同理；
4. **不得仅凭文件夹名判断仓库**；
5. **不得假设** `Qingzhou-contracts` 一定位于 `../Qingzhou-contracts` 或任何固定相对位置。

**本地正式任务开始前必须实际确认**（不得凭记忆或上次会话推断）：

```powershell
git rev-parse --show-toplevel      # 实际工作树根
git remote get-url origin          # 实际 origin
git branch --show-current          # 当前分支
git rev-parse HEAD                 # 当前 head
git status --short                 # 工作区状态
git fetch origin                   # 同步远端
```

6. 必须确认当前 `origin` 与本任务指定的 GitHub 仓库**一致**；
7. **若 `origin` 不一致，必须 `BLOCKED` 停止，不得继续修改错误仓库**；
8. `fetch` 后检查默认分支 / `origin` 默认分支是否同步，并核对默认分支名（**本仓默认分支为 `master`，不是 `main`**）；
9. 需要读取 `Qingzhou-contracts` 或其他青舟仓库时：
   - **已存在本地 clone**：先验证其 `origin` 指向预期 GitHub 仓库，再读取；
   - **没有可信本地 clone**：从 GitHub 读取；
   - 不得仅凭文件夹名判断仓库；
   - 不得假设中央仓位于任何固定相对路径。

## 2. 本仓专属硬规则（完整保留，不得弱化）

### 2.1 Phase 与顺序纪律

- 路线只有 `EquipEffi V2.3`；Phase 0 已完成，作为不可变基线。
- 状态继续按此记录：`Phase 1 = PHASE_1_PASS`；`Phase 2 = PHASE_2_READY`；automatic continuation = `DISABLED`。
- `PHASE_1_PASS` 是既有独立复验与 Solution/Product Review 后的记录，不是任何 adoption / 治理任务自行批准；`PHASE_2_READY` 不代表开始或授权。
- Phase 1 按 `P1-G01 → G02 → G03 → G04 → G05 → G06` 顺序执行，只能交付 `READY_FOR_SOL_REVIEW` 或 `BLOCKED`，不得自行宣布 Phase 1 PASS；未完成 Solution/Product Review 不得越级实施 Phase 2，进入 Phase 2 须用户明确授权。
- v15 / T04.xx / 历史 HANDOFF / 编号清单无自动调度权，不得据其“下一边界任务”自动继续。
- Phase 1 只允许业务规范、数据契约、`pump_water` 映射、Golden Case、P0 复核与 Python/版本/V1 Scope 冻结；不批量迁移 17 个 Profile、不批量重构 evaluator，不开发 PySide6 / SQLite / Excel / 报告。
- 旧资产先分类（KEEP / VERIFY / MIGRATE / REWORK / DEPRECATE / DELETE_CANDIDATE / OBSOLETE），不因零引用直接删除。

### 2.2 P0 Hotfix 条件

全部满足才可改业务代码，Phase 1 默认不改业务实现：① 有明确标准或回归测试证据；② 已在 `QA_BACKLOG.md` 登记 P0；③ 范围最小、不改架构、不顺手清理；④ 有针对性回归测试；⑤ 修改前后结果、标准引用、影响范围均已记录。Phase 0B = `NOT_EXECUTED`；P0 复核只允许 `CONFIRMED_P0` / `NOT_P0` / `NEEDS_MORE_EVIDENCE`，不自动授权修改。

### 2.3 业务正确性与受保护资产

- Canonical JSON 是标准事实候选源，Python 常量不得继续作为标准表格唯一事实源；`Legacy Regression` 不等于业务真相，迁移须由 Approved Golden Case、标准证据与意图变化说明保护。
- 可能改变标准选择、表选择、单位、公式、边界、插值、比较方向、缺失语义、适用范围或淘汰结论的改动，必须先登记 QA/P0 并提供证据。
- 未支持 Profile 必须返回明确 Support Status，不得伪装成“已支持但无法计算”。
- 继续保护：18 条具名批准的 `pump_water` Golden 0.4、Golden 0.1 历史冻结层、原始 0.3 的 DRAFT/PENDING 层、Canonical、Golden Case Schema 与 V1 Scope 决策；不覆盖原始标准、模板、用户工作簿、校对册与发布产物。

### 2.4 文件、测试与依赖方向

- 关键资源修改前后必须更新 `BASELINE.md` 哈希与 `HANDOFF.md` 事实。
- 正式 unittest / compileall / smoke / 性能基线须完整记录 pass/fail/error/skip/not_run；性能问题先登记实测，不做 Repository 或缓存重构。
- 依赖方向：Domain 不依赖 UI/Excel/SQLite；Presentation 只能经 Application 契约调用核心；装配层不得制造新的包级循环。

### 2.5 本仓 Numeric Profile 事实

- Pump 使用 `EQUIPEFFI_PUMP_DECIMAL50_V2`：Decimal、precision=50、`ROUND_HALF_EVEN`、full-value business comparison、`PUMP-RP-0.1` nonlinear reference procedure；numerical tolerance 只用于 Conformance，不作业务 epsilon。
- Decimal50 / `ROUND_HALF_EVEN` 是 Pump Profile 的证据支撑配置，不是平台全局默认；变压器、电机、风机及未来设备不得因 adoption 被强制改成 Decimal50，各 Calculator 按自身证据声明 Numeric Profile。

### 2.6 本仓 UI 事实

- 现有桌面主窗口实际为遗留 **Tkinter / ttk**（`EquipmentEfficiencyWindow`），事实见 `UI_CURRENT_STATE_AUDIT.md`；不得因中央指南把 PySide6 列为默认技术栈就在无授权任务中重写，PySide6 迁移与正式 UI 重构须由后续独立任务显式授权。

## 3. 青舟中央治理入口

- 中央仓 `https://github.com/adgo07/Qingzhou-contracts.git`；锁定见本仓 `platform-lock.json` / `PLATFORM_BASELINE.md`，当前 locked SHA = `ee5feb0cc34dbd99790500fadd0c4c932e202a20`（Architecture `V2.1 FROZEN`、Numeric Contract `v1 FROZEN`，其余 Contract 仍 `DRAFT`）。
- 按中央 `docs/GUIDE_INDEX.md` 第 2.1 节：**Frozen 权威文件**（Frozen Contract / Schema / Conformance）按本仓 locked SHA 读取；**ACTIVE / ACTIVE-EVOLVING 指南**按 GUIDE_INDEX 路由，读中央当前已合并版本。
- 三条“不得”：不得自动升级 Frozen Contract（只能由显式治理任务更新 `PLATFORM_BASELINE.md` / `platform-lock.json`）；不得把 ACTIVE 指南当 Frozen Contract；不得用它覆盖本仓 locked Frozen Contract——冲突以 locked Frozen 权威文件为准。读 ACTIVE 指南不修改锁文件、不构成 adoption、不改变业务语义。
- 公共治理只约束跨产品架构与公共外围 Contract，不覆盖标准原文、Canonical、已批准 Golden、单标准规则或 V1 Scope 决策；公共语义缺口登记 RFC candidate 交中央治理。

## 4. 开工前最小必要读取

读取顺序：本仓 `AGENTS.md` → `platform-lock.json`（locked SHA）→ `HANDOFF.md` / `TASK_STATE.md` → 与任务直接相关的本仓文件 → 中央 `docs/GUIDE_INDEX.md` → 只读路由到的中央文件（Frozen 按 locked SHA；ACTIVE 按中央当前合并版本）。普通业务 Bug、页面调整、单标准专有问题的权威状态在本仓；**不得要求每个普通业务 Bug 都通读整个 Qingzhou-contracts**，只有确认涉及公共语义（Numeric / Unit / Module-Capability / Record / qzpack / Conformance）时才扩展到对应中央文件。

## 5. Contract 冲突分类

- `LOCAL DEFECT`：本地实现违反已采用 Frozen Contract；修本地。
- `ALLOWED PROJECT DIFFERENCE`：中央允许的项目配置差异（如 Pump Decimal50）；不为表面统一强改。
- `REGISTERED DEVIATION`：已登记未关闭；按当前治理状态处理，不假装已解决。
- `CENTRAL CONTRACT GAP`：真实需求无法由当前中央 Contract 表达；不私造公共规则，带证据返回中央仓。

## 6. 中央交付原则与 Contract Preflight（短入口）

中央 ACTIVE 指南（都不是 Frozen Contract；正文只在中央）：`docs/governance/PRODUCT_DELIVERY_POLICY_V1.md`、`docs/governance/STANDARD_DEVELOPMENT_GUIDE_V0.1.md`（见 9、10 节）、`docs/ui/UI_DESIGN_GUIDELINES_V0.1.md`（见 8 节）。

交付原则只留名称，正文以中央 Policy 为准：**Windows-first**；**Reference Standard first**（`GB 19762—2025`）；**Product-core-first**；**Excel-as-adapter**（Excel 只调用同一 evaluator / Calculator，不复制第二套算法）；**Cross-platform-ready**（不依赖 Windows-only API）；**逐标准扩展**（Reference Standard 闭环前不批量迁移 17 个 Profile）。真实状态见 `REFERENCE_STANDARD_ROADMAP.md`。

Contract Preflight（详见中央 Policy 第 12 节）：读 `platform-lock.json` → 确认 locked SHA → 按 locked SHA 读相关 Frozen Contract → 提取适用 MUST / MUST NOT → 按第 5 节分类冲突 → 确认后再设计或编码。不得直接读中央 `main` 并认为本仓须自动跟随；升级须用户明确授权并经独立治理变更锁文件。

## 7. Standard Issues 治理入口（短）

- 开工前读 `STANDARD_ISSUES_REGISTER.md`，确认是否涉及已有 Issue。
- **先登记再实现**：发现标准疑似笔误、歧义、冲突、未规定、术语、引用或软件实现解释问题时，必须先登记台账，再完成正式实现说明。
- **标准原文事实 / 技术判断 / 软件实现决定必须分开记录**，不得把内部判断或软件选择写成标准明文，不得静默纠正标准。
- 影响正式业务结果的问题必须可追踪 `Standard Issue → Software Decision → Rule / Calculator → Test / Golden Case`，解释变化须检查测试与历史结果兼容性。
- 台账字段 / 状态 / 编号以中央 Policy 第 20 节为准。

## 8. UI 治理入口（短）

涉及桌面 UI 的 Design / Execution / Acceptance 必须读中央 `UI_DESIGN_GUIDELINES_V0.1.md`（`ACTIVE / EVOLVING`，不是 Frozen Contract）。要点：① 用户可见内容中文优先；② 普通 UI 不默认泄露 `key` / `field_id` / `rule_id` / `internal_id`、Python 变量、原始 JSON、调试标识；③ 简单业务 `One-page first`，不强制单页；④ 技术 trace、Numeric Profile、Calculator version、内部 Rule 渐进展示，不删审计能力；⑤ 按真实用户任务而非数据库 / JSON 组织页面；⑥ 推荐模式不等于强制布局。该指南不改变本仓锁文件、Phase 门禁或业务结论，也不授权 UI 重构。

## 9. 新标准开发入口（Standard Development）

任何**新增标准**或**实质修改既有标准支持范围**的任务必须按中央 `STANDARD_DEVELOPMENT_GUIDE_V0.1.md`（`ACTIVE / EVOLVING`）执行：`Stage A 标准整理 → Stage B 软件接入设计 → Stage C 实现 → Stage D 正式验收`，顺序不得颠倒。不得：拿到 PDF 就直接写 Calculator；跳过 Standard Mapping；在 Mapping 中静默纠正标准；UI 先发明业务规则；Excel 建第二套算法；未经正式验收就宣布 `SUPPORTED`。支持状态只允许 `CATALOG_ONLY / MAPPING / READY_FOR_IMPLEMENTATION / IMPLEMENTED / SUPPORTED`，不得无证据跳级。详细规则不复制，以中央指南为准；普通业务 Bug、纯 UI 调整、不改变支持范围的内部重构不进入本流程。

## 10. 知识沉淀入口（Knowledge Capture）

- 标准开发 / Mapping / Calculator / 测试 / UI / Excel 任务中若产生有长期价值且已有证据支持的专业知识，允许顺手记录到本仓知识落点 `src/equipeffi/resources/knowledge/`；不为知识制造条目。
- 新条目默认 `DRAFT`，不得自动 `PUBLISHED`；**不要求**每个任务必须产生知识，允许记录“Knowledge capture：无”。
- 知识只能解释 Calculator，不得作为其权威数据源或规则源，不得运行时解析 Markdown；必须区分标准原文事实 / 官方资料 / 专业技术解释 / 工程实践建议，不得把技术判断写成标准明文。
- 不得为 Knowledge 明显扩大主任务；不得建立复杂 Schema、知识库、向量库、RAG / AI Chat 或知识中心 UI。详细规则见中央指南“知识沉淀”部分。

## 11. 正式报告与中文优先

- 正式 Design / Execution / Acceptance Report 必须含平台预检查：本仓 SHA、locked central SHA、相关 Frozen Contract、适用 MUST / MUST NOT、冲突分类、是否需改中央 Contract；不涉及中央公共语义时写 `本任务不涉及中央公共 Contract。`
- 涉及 Standard Issue 时必须写明：是否存在相关问题；问题编号；是否改变既有软件解释。
- 中文优先：不影响 Python/JSON/YAML/schema/API/enum/stable ID、测试与跨平台兼容时，界面文字、治理文档、路线、报告、PR/Issue 描述优先中文；机器字段保持英文。
