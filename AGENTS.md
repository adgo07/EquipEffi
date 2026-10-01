# EquipEffi Agent 纪律

## 当前治理

- 当前路线只有 `EquipEffi V2.3`。
- 当前 Phase 为 `Phase 1`；Phase 0 已完成并作为不可变基线保留。
- Phase 1 必须按 `P1-G01 → G02 → G03 → G04 → G05 → G06` 顺序执行；本阶段最终只能交付 `READY_FOR_SOL_REVIEW` 或明确 `BLOCKED`，不得自行宣布 Phase 1 PASS。
- v15 / T04.xx / 历史 HANDOFF 不拥有自动任务调度权。
- 任何 Agent 开始工作前必须读取 `ROADMAP.md`、`TASK_STATE.md`、`HANDOFF.md` 和相关权威审计文件。
- 不得根据旧 HANDOFF 中的“下一边界任务”自动继续。

## 阶段纪律

- 当前 Phase 未完成 Solution/Product Review 前不得越级实施 Phase 2 及以后产品功能。
- Phase 1 不批量迁移 17 个 Profile；先冻结业务规范和数据契约。
- Phase 1 只允许业务规范、数据契约、`pump_water` 标准映射、Golden Case、P0 证据复核、Python/版本/V1 Scope 冻结；不得批量重构 evaluator、搬目录、开发完整 PySide6、SQLite、Excel、报告。
- Phase 0 默认只审计、记录和治理，不重构、不扩功能、不搬目录。
- 旧资产先分类为 `KEEP`、`VERIFY`、`MIGRATE`、`REWORK`、`DEPRECATE`、`DELETE_CANDIDATE` 或 `OBSOLETE`，不得因零引用直接删除。

## 业务正确性

- Canonical JSON 是标准事实候选源；Python 常量不能继续作为标准表格唯一事实源。
- `Legacy Regression` 不等于业务真相；迁移必须由 Approved Golden Case、标准证据和意图变化说明保护。
- 任何可能改变标准选择、表选择、单位、公式、边界、插值、比较方向、缺失语义、适用范围或淘汰结论的改动，必须先登记 QA/P0，并提供证据。
- 未支持的 Profile 必须返回明确的 Support Status，不得伪装成“已支持但无法计算”。

## P0 Hotfix 条件

只有全部满足以下条件才能在 Phase 0B 修改业务代码；Phase 1 默认不修改业务实现：

1. 有明确标准或现有回归测试证据；
2. 已在 `QA_BACKLOG.md` 登记为 P0；
3. 修改范围最小，不改变架构、不顺手清理；
4. 有新增或修改的针对性回归测试；
5. 修改前后结果、标准引用和影响范围均已记录。

本次 Phase 0B 状态为 `NOT_EXECUTED`。Phase 1 的 P0 复核只允许记录 `CONFIRMED_P0`、`NOT_P0` 或 `NEEDS_MORE_EVIDENCE`，不因复核自动授权 Hotfix。

## 文件和测试保护

- 不覆盖原始标准、原始模板、用户工作簿、校对册或发布产物。
- 关键资源修改前后必须更新 `BASELINE.md` 的哈希和 `HANDOFF.md` 的事实。
- 正式 unittest、compileall、package/resource smoke 和性能基线必须按命令、环境、耗时、pass/fail/error/skip/not_run 完整记录。
- 性能问题先登记实测结果，不能在 Phase 0 直接做 Repository 或缓存重构。
- 依赖方向：Domain 不依赖 UI/Excel/SQLite；Presentation 只能通过 Application 契约调用核心；装配层不得制造新的包级环。

## Qingzhou-contracts 公共治理（QZC-A01 / Numeric v1 Adoption）

- 本仓采用 `https://github.com/adgo07/Qingzhou-contracts.git` 的公共治理基线；精确锁定以 `PLATFORM_BASELINE.md` 和 `platform-lock.json` 为准，不得实时跟随中央仓 `main`。
- 当前中央基线为 `ee5feb0cc34dbd99790500fadd0c4c932e202a20`：Architecture `V2.1 FROZEN`；Numeric Contract `v1 FROZEN`；Unit、Module/Capability、Workspace/Attempt/Record/Result、qzpack 等仍保持 `DRAFT / NOT YET RELEASED`。
- Numeric Contract v1 冻结的是 Numeric Profile 机制、full-value 比较默认、rounding/tolerance taxonomy、Profile consistency、ambient independence、nonlinear/reference-procedure 与 operation-order 等公共语义；它不规定全平台统一 precision、rounding mode 或 epsilon。
- EquipEffi Pump 使用 `EQUIPEFFI_PUMP_DECIMAL50_V2`：Decimal、working precision=50、`ROUND_HALF_EVEN` working context、full-value business comparison、display rounding 隔离、`PUMP-RP-0.1` nonlinear reference procedure，numerical tolerance 只用于 Conformance；Decimal50 不是平台全局默认。
- 变压器、电机、风机及未来设备不得因本次 adoption 被强制改成 Decimal50；每个 Calculator 应按自身证据声明有效 Numeric Profile。
- 公共治理只约束跨产品的架构和公共外围 Contract，不覆盖标准原文、Canonical、已批准 Golden、单标准规则、EquipEffi 业务结果语义或 V1 Scope 决策。
- Phase 1 的已批准治理和业务结论仍由当前 `master` 上的 `ROADMAP.md`、`TASK_STATE.md`、`HANDOFF.md`、业务规范及其明确引用的冻结资产共同记录；Numeric v1 adoption 不得删除、弱化或重新解释 P1-G01～G06、Solution/Product Review、Pump Numeric & Decision Contract、Canonical/Golden/QA 要求或 Phase 2 进入条件。
- 当前 Phase 1 `PHASE_1_PASS` 是既有独立复验和 Solution/Product Review 后记录的状态，不是本次 adoption 自行批准。`PHASE_2_READY` 不代表开始或授权；自动继续保持 `DISABLED`，只有用户明确授权后才能进入 Phase 2。
- 发现跨产品公共语义缺口时，在本仓记录 RFC candidate 并交由 Qingzhou-contracts 治理；普通设备能效业务问题仍在本仓处理。
- 本次 Numeric v1 adoption 只允许必要治理、锁文件、Conformance/验证和最小兼容修复，不授权重设计泵、批量迁移其他设备、修改 Schema/Canonical/Golden、数据库、Excel、UI 或 Phase 2 功能。

## 青舟平台开发前置检查（Qingzhou Platform Contract Preflight）

本节是后续所有正式设计、开发、重构、修复、标准接入、Calculator、Numeric、Excel、Record、数据库、Schema、Module、Package、跨平台和导入导出任务的统一前置要求。

### 1. 开工前检查顺序

```text
读取本仓 platform-lock.json
→ 确认锁定的 Qingzhou-contracts commit SHA
→ 按 locked SHA 读取相关 Frozen Contract
→ 提取适用于当前任务的 MUST / MUST NOT
→ 检查冲突并分类
→ 确认后再开始设计或编码
```

不得直接读取中央 `main` 最新内容并认为本仓必须自动跟随。只有用户明确授权中央 Contract 升级任务时，才允许通过独立治理变更 `PLATFORM_BASELINE.md` 和 `platform-lock.json`。

中央产品交付治理文件：

`docs/governance/PRODUCT_DELIVERY_POLICY_V1.md`

它是 Architecture V2.1 下的 **ACTIVE GOVERNANCE POLICY**，不是 Frozen Contract，不改变本仓锁定的 Frozen Contract SHA。

### 2. 当前产品交付优先级

- **Windows-first**：Windows Desktop 是当前第一功能、GUI、测试、打包、文件/Excel 和用户验收平台；
- **Reference Standard first**：当前参考标准为 `GB 19762—2025 离心泵能效限定值及能效等级`；
- **Product-core-first**：先完成离心泵软件核心纵向闭环，再完成参考标准 Excel 闭环；
- **Excel-as-adapter**：Excel 只承担 Import/Export Adapter 角色，必须通过 Application 契约调用同一个 evaluator/Calculator，不得复制第二套能效算法；
- **Cross-platform-ready**：当前不全面开发 Android/iOS/HarmonyOS，但 Domain/Application 不得依赖 Windows UI 或 Windows-only API；
- **逐标准扩展**：Reference Standard 完成正式 Windows + Excel 闭环前，不以批量迁移 17 个 Profile 或大量增加标准为主要目标。

当前真实状态统一见：

`REFERENCE_STANDARD_ROADMAP.md`

当前仍保持：

```text
Phase 1 = PHASE_1_PASS
Phase 2 = PHASE_2_READY / NOT STARTED
Automatic continuation = DISABLED
```

本治理同步不构成 Phase 2 启动授权。

### 3. Contract 冲突分类

发现业务仓与中央规则不一致时，必须使用以下分类：

- `LOCAL DEFECT`：本地实现违反本仓已采用 Frozen Contract；修本地；
- `ALLOWED PROJECT DIFFERENCE`：中央明确允许项目配置差异，例如 Pump Decimal50；不得为表面统一强改；
- `REGISTERED DEVIATION`：偏差已正式登记但未关闭；按当前治理状态处理；
- `CENTRAL CONTRACT GAP`：真实业务需求无法由当前中央 Contract 正确表达；不得在 EquipEffi 私自发明另一套公共规则，应整理实际案例/业务证据/Contract 缺口/Candidate 返回中央仓。

### 4. 正式报告必须包含平台预检查

后续 Design、Execution Report、Acceptance Report 至少记录：

- 当前业务仓 SHA；
- `platform-lock.json` / locked central SHA；
- 本任务相关 Frozen Contract；
- 适用 MUST / MUST NOT；
- 是否发现冲突及其分类；
- 是否需要中央 Contract 修改。

如果任务确实与中央公共语义无关，也必须明确写：`本任务不涉及中央公共 Contract。`

### 5. 中文优先

在不影响 Python/JSON/YAML/schema/API/enum/stable ID、自动化测试和跨平台兼容的前提下，用户界面文字、治理文档、路线、执行/验收报告、PR/Issue 描述、错误/校验提示和面向人的说明应优先使用中文。

机器字段与稳定技术标识继续保持英文；在人阅读的文档中优先采用“中文名称（英文标识）”。

### 6. 标准问题与解释治理

开工前必须读取根目录 `STANDARD_ISSUES_REGISTER.md`，确认当前任务是否涉及已有 Standard Issue。

正式 Design、Execution Report、Acceptance Report 的“平台 / Contract 预检查”必须增加：

```text
是否存在与当前任务相关的 Standard Issue：是 / 否
涉及的问题编号：……
本任务是否改变既有软件解释：是 / 否
```

发现新的标准疑似笔误、歧义、冲突、未规定、术语、引用或软件实现解释问题时，必须先登记台账，再完成正式实现说明。必须分开记录“标准原文事实”“技术判断”“软件实现决定”，不得把内部判断或软件选择写成标准明文，也不得静默纠正标准。

影响正式业务结果的问题必须能追踪：

```text
Standard Issue
→ Software Decision
→ Rule / Calculator
→ Test / Golden Case
```

解释变化时必须同步检查相关测试和历史结果兼容性。本治理同步不授权 Phase 2，也不授权修复台账中的问题。

### 7. UI 设计前置原则

后续涉及桌面 UI 的 Design / Execution / Acceptance 还必须检查中央 `docs/ui/UI_DESIGN_GUIDELINES_V0.1.md` 的当前适用版本，并遵守以下原则：

1. 当前 Windows Desktop 默认 UI 技术栈为 PySide6；本仓现有 Tkinter/ttk 窗口属于当前真实遗留状态，不得仅因本条在无授权任务中重写；
2. 用户可见内容中文优先；
3. 普通 UI 不得默认泄露内部 `key / field / field_id / rule_id / internal_id`、Python 变量、原始 JSON 或调试标识；
4. 简单业务采用 `One-page first`，但不是所有标准强制单页；
5. 技术 trace、Numeric Profile、Calculator version、内部 Rule 等采用渐进展示，不删除审计能力；
6. UI 设计优先满足真实用户任务，不按数据库、JSON 或代码结构组织普通页面；
7. `Qingzhou Desktop UI Guidelines v0.1` 是 **ACTIVE / EVOLVING** 的 Product Design Guideline，不是 Frozen Contract；
8. AI 不得因为 v0.1 的推荐 AppShell、页面示意或当前实现而拒绝合理的页面改进，也不得把推荐模式误当强制布局。

该 UI Guideline 不改变本仓 `platform-lock.json`、Phase 1/Phase 2 门禁或现有业务结论；任何 PySide6 迁移和正式 UI 重构都必须由后续独立任务显式授权。