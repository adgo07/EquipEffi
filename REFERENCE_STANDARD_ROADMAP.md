# EquipEffi 参考标准开发路线

状态：**CURRENT INVENTORY / GOVERNANCE ROADMAP**
盘点日期：2026-10-02（本次同步）
首次盘点日期：2026-10-01
盘点基线：`master@7e16418aa32ced5512e26bd70227f01a329fbdfc`（Phase 2 已 PASS 并合并）；Phase 3 执行中
参考标准：`GB 19762—2025 离心泵能效限定值及能效等级`
参考标准覆盖范围：**`pump_water`（清水离心泵）与 `pump_chemical`（石化离心泵）** —— 见 `V1_SCOPE.md` 第 0 节

> 本文件只盘点当前真实状态并固定后续交付顺序，不修改 Pump evaluator、Canonical、Golden 数据库、Excel、UI 或 Numeric Profile。

## 1. 平台 / Contract 预检查

| 项目 | 结果 |
|---|---|
| 当前业务仓 SHA | `7e16418aa32ced5512e26bd70227f01a329fbdfc`（`master`；Phase 3 分支基线） |
| 当前默认分支 | `master` |
| `platform-lock.json` | 锁定中央 `ee5feb0cc34dbd99790500fadd0c4c932e202a20`；未变更，`auto_follow_main = false` |
| 中央 Frozen Contract | Architecture `V2.1 FROZEN`；Numeric Contract `v1 FROZEN`；Unit / Module / Workspace-Record / qzpack 仍 `DRAFT`。按 locked SHA 读取 |
| 中央 ACTIVE / EVOLVING 指南 | `docs/GUIDE_INDEX.md`、`PRODUCT_DELIVERY_POLICY_V1.md`、`STANDARD_DEVELOPMENT_GUIDE_V0.1.md`、`UI_DESIGN_GUIDELINES_V0.1.md`；按 `GUIDE_INDEX.md` 第 2.1 B 类读取中央当前合并版（核对快照 `origin/main@4516e204ab20ca61c5931a46c0b28d1c06459727`）。这些文件在 locked SHA `ee5feb0` 上**不存在**，不得按 locked SHA 读取 |
| 当前项目 Numeric Profile | `EQUIPEFFI_PUMP_DECIMAL50_V2`，项目专属，不是平台全局默认 |
| 适用 MUST | Profile 显式且一致；full-value business comparison；operation order / reference procedure；Windows-first；Excel 与 GUI 共用同一业务内核；`SUPPORTED` 必须有 Stage D 独立验收证据 |
| 适用 MUST NOT | 不自动跟随 central `main`；不把 Decimal50 推给所有设备；不把 Excel 另写一套算法；不越级启动 Phase；不得无证据宣称标准开发跳级到 `SUPPORTED`；不得自行提升 `pump_chemical` 的 `support_status` |
| 冲突分类 | `LOCAL DEFECT`：治理指针滞后（本阶段校准）；`ALLOWED PROJECT DIFFERENCE`：Pump Decimal50；`REGISTERED DEVIATION`：无新增；`CENTRAL CONTRACT GAP`：无 |
| 是否发现中央 Contract 冲突 | 否 |
| 是否需要修改中央 Contract | 否 |

中央 ACTIVE 治理文件正文只在中央仓保留：`Qingzhou-contracts/docs/governance/PRODUCT_DELIVERY_POLICY_V1.md`、`docs/governance/STANDARD_DEVELOPMENT_GUIDE_V0.1.md`、`docs/ui/UI_DESIGN_GUIDELINES_V0.1.md`、`docs/GUIDE_INDEX.md`。这些指南不改变本仓 Frozen Contract lock。

## 2. 当前阶段事实

当前权威状态来自 `ROADMAP.md` / `TASK_STATE.md`：

```text
Phase 1: PHASE_1_PASS
Phase 2: PHASE_2_PASS            (PR #10 独立验收并合并)
Phase 3: IN_PROGRESS             (GB 19762-2025 离心泵统一正式纵向闭环)
Automatic continuation: DISABLED
```

Phase 1 已冻结/验证业务规范、Canonical/Product/Profile/Import Contract、Golden Case Schema、多维状态模型和 `pump_water` 样板标准映射；Phase 2 已建立最小正式工程底座。**参考标准范围已由 `V1_SCOPE.md` 第 4 节收口为 `pump_water` + `pump_chemical`；Phase 3 增量修正把 `pump_chemical` 的正式产品接入前移到 Phase 3（见路线原文第 8.2 节），Phase 5 改为承担其 Stage D 发布支持收口。**

### 2.1 Owner 批准与业务真值（2026-10-02）

| Profile | Owner 决定 | 结果 | 证据 |
|---|---|---|---|
| `pump_water` | Owner Reconfirmation | **18 / 18 PASS** | `specs/equipment_efficiency/golden/owner_approvals/pump_water_owner_reconfirmation_2026-10-02.json` |
| `pump_chemical` | Owner Business-Truth Approval（C1–C11） | **11 / 11 PASS** | `specs/equipment_efficiency/golden/owner_approvals/pump_chemical_owner_approval_2026-10-02.json` |

`pump_chemical` 业务真值 blocker 已关闭；**剩余正式 blocker 仅为中央 Standard Development Guide Stage D 独立验收**。三个状态维度数值不变：

```text
pump_water    : scope_status=IN_V1 | support_status=SUPPORTED             | standard_maturity=SUPPORTED
pump_chemical : scope_status=IN_V1 | support_status=NOT_IN_RELEASE_SCOPE  | standard_maturity=READY_FOR_IMPLEMENTATION
transformer   : scope_status=POST_V1 | support_status=NOT_IN_RELEASE_SCOPE
```

## 3. 状态定义

| 状态 | 中文解释 |
|---|---|
| `DONE` | 已完成，并有当前可核对证据 |
| `PARTIAL` | 部分完成；已有业务/工程资产但尚未形成完整产品交付 |
| `NOT STARTED` | 尚未按当前路线进入正式实现 |
| `BLOCKED` | 被明确依赖或治理条件阻塞 |

本表状态与中央标准开发成熟度（`CATALOG_ONLY` / `MAPPING` / `READY_FOR_IMPLEMENTATION` / `IMPLEMENTED` / `SUPPORTED`）是不同维度，两者不得互相冒充（中央 `STANDARD_DEVELOPMENT_GUIDE_V0.1.md` §19）。

## 4. 参考标准现状盘点

参考标准目标为**完整支持 GB 19762—2025**，即同时覆盖 `pump_water` 与 `pump_chemical`。

| 项目 | 状态 | 证据与说明 |
|---|---|---|
| 标准库 | `PARTIAL` | Phase 1 已建立 Canonical/Product/Profile Schema 与 `pump_water` 标准映射，标准事实层已具备；Phase 2 已建立最小正式工程底座。正式 Windows 产品中的“标准库发现→查看→选择→进入分析”纵向闭环正由 Phase 3 实现。 |
| 新建设备分析 | `PARTIAL` | 已有正式 evaluator/API、输入输出契约、业务规范和 Golden；Phase 3 正在建立统一的 GB 19762 分析入口（`pump_water` + `pump_chemical` 同页），尚未完成。 |
| 分类 | `PARTIAL` | `pump_water` 有 18 条正式 Golden 0.4；`pump_chemical` 的 C1–C11 已于 2026-10-02 获 Owner **11/11** 业务真值批准，并形式化为 11 条 `golden-case-0.5`。统一类别路由（8 类 + 其他/不确定）正由 Phase 3 实现，故本项未达 `DONE`。 |
| 输入 | `PARTIAL` | Product/Profile/Import Contract 与 Golden 输入模型已建立；统一 GUI 输入页/用户流程正由 Phase 3 实现。`pump_chemical` 的必要输入字段已由映射与 C1–C11 覆盖。 |
| 校验 | `PARTIAL` | Pump evaluator 与 Phase 1 契约已有大量校验、边界测试和 Numeric tests；产品层输入错误提示/GUI 闭环正由 Phase 3 实现。 |
| Calculator | `PARTIAL` | `pump_water`：Pump evaluator API 回归 PASS，N01-B 实际执行 Decimal50、sqrt/ln/fractional pow、precision/operation-order sensitivity。`pump_chemical`：`ChemicalPumpEvaluator` 存在、有共享回归，且其业务真值已获 **11/11** Owner 批准；仍缺统一产品闭环与 Stage D，故未达 `DONE`。 |
| 能效等级 | `PARTIAL` | `pump_water` 由 Approved Golden、generated boundary tests、Pump evaluator 回归和 N01-B 对 rule/bucket/grade 正式校验；`pump_chemical` 的等级判定已由 11 条批准 Golden 覆盖（含 1/2/3 级、未达标与范围外），仍待统一产品闭环。 |
| 不适用 | `PARTIAL` | 多维状态模型/业务规范已建立并通过 Solution/Product Review；`pump_chemical` 的 ns>300 与 ns<20 “不适用”已由 C10/C11 具名批准。正式产品页面的完整交互与展示正由 Phase 3 实现。 |
| 无法判定 | `PARTIAL` | 业务状态模型/契约已有明确语义；正式产品层输入不足/无法判定提示、结果页与记录边界正由 Phase 3 实现。 |
| 结果解释 | `PARTIAL` | Golden/trace/规则证据可解释技术结果；面向用户的统一结果解释、标准依据与来源展示正由 Phase 3 实现。 |
| 正式记录 | `PARTIAL` | Phase 3 首次正式启用 `records.sqlite`（独立 forward-only、`NEVER_DESTRUCTIVE_RECORD_ASSET`）与 Workspace/Record/History/Reopen。中央 Record Contract 仍 DRAFT，本路线未擅自采用其未冻结字段。 |
| Windows | `PARTIAL` | Windows V1 是明确产品目标；Phase 2 已提供最小 PySide6 薄壳，Phase 3 正在把"新建分析"与"分析记录"变为真实统一页面。 |
| Excel | `NOT STARTED` | Phase 1 已有 Import Contract，证明未来 Excel 应 contract-driven；现行 V2.3 仍把正式 Excel 放在 Phase 8。当前未进入正式 Excel 开发。Excel 数值入口的公共无损方案仍 OPEN，且本仓读取器存在 float 物化点（见 `QA-EXCEL-001`），正式开发前须先设计并验证。 |
| Conformance | `PARTIAL` | N01-B Independent Acceptance PASS；Pump Numeric/Decision Contract、precision/operation-order/reference procedure 和 Numeric v1 adoption 均有执行测试证据。`pump_chemical` 的 Conformance 已由 Phase 3 的 generated boundary tests（Q/ns 端点与 ±epsilon）与 11 条批准 Golden 增强，尚未完成统一端到端验收。 |
| Golden Case | `PARTIAL` | `pump_water`：18 条 Golden 0.4 具名批准 + 2026-10-02 Owner Reconfirmation **18/18 PASS**。`pump_chemical`：C1–C11 于 2026-10-02 获 Owner **11/11 PASS**，形式化为 11 条 `golden-case-0.5`（8 条候选派生 + 3 条 owner-defined）。两端业务真值均已批准；剩余为产品闭环与 Stage D。 |
| 下一标准准备状态 | `NOT STARTED` | Phase 1 明确没有批量迁移 17 个 Profile。按新产品交付治理，先完成离心泵（`pump_water` + `pump_chemical`）核心 Windows 产品闭环和 Excel 闭环，再选第二个标准验证架构扩展性；本任务不启动第二标准。 |

## 5. 当前结论

GB 19762—2025 的 `pump_water` **业务规则、Pump Calculator、Numeric Conformance 与 Golden Case 已经是当前最成熟资产**；`pump_chemical` 的 Calculator 与标准包已存在，且其业务真值已于 2026-10-02 获 **11/11** Owner 批准并形式化为正式 Golden。参考标准的剩余缺口集中在**产品工程层**与 **Stage D**：

```text
产品工程缺口（两个 Profile 共同）—— Phase 3 正在闭合
  统一的 GB 19762 分析入口（pump_water + pump_chemical 同页）
  + 统一类别路由（8 类 + 其他/不确定）
  + 统一 Workspace / Record / History / Reopen
  + as_of 显式化与 Finalize/Reopen 冻结

发布支持缺口（仅 pump_chemical）—— 属 Phase 5
  Standard Development Guide Stage D 正式验收
  → 通过后方可切换 support_status = SUPPORTED

后续阶段缺口
  完整 GB 19762 产品 Shell（Phase 6）
  + 生命周期与质量收口（Phase 7）
  + Reference Standard Excel 闭环（Phase 8）
```

因此当前 Reference Standard 总体状态：

`PARTIAL`

这不是中央 Contract 阻塞。当前阶段门禁是：**Phase 3 执行中，完成后须经独立验收**；`pump_chemical` 的 `support_status` 提升须待 Phase 5 的 Stage D 独立验收。

## 6. 后续交付顺序

Phase 2 已完成（`PHASE_2_PASS`）。Phase 3 增量修正把 `pump_chemical` 的正式产品接入前移到 Phase 3，因此顺序调整为：

1. ~~进入 Phase 2~~ **已完成**（`PHASE_2_PASS`）；
2. **Phase 3（执行中）**：建立统一的 GB 19762—2025 分析链——统一类别路由（8 类 + 其他/不确定）、统一 `AnalysisService` 契约、统一 Workspace / Record / History / Reopen、`records.sqlite` 首次启用、统一 Qt 分析页与分析记录页；`pump_water` 与 `pump_chemical` 同页共存；
3. **Phase 4**：基于 Phase 3 真实样板做必要通用化；
4. **Phase 5**：完成 `pump_chemical` 的 **Stage D 正式验收与发布支持收口**，通过后方可切换 `support_status = SUPPORTED`；
5. **Phase 6～7**：围绕完整 GB 19762 建立完整产品 Shell，并完成生命周期与质量收口；
6. **Phase 8**：正式 Excel 阶段，只实现 Import/Export Adapter，统一调用同一 evaluator；Excel 数值入口必须先完成设计与证据验证（`QA-EXCEL-001`）；
7. **Phase 9**：完整 GB 19762 Windows V1 正式验收与发布；
8. **Phase 10**：Reference Standard Gate PASS 后，再选择第二标准验证扩展架构。

**`pump_chemical` 的 `support_status` 只有在 Stage D 独立验收通过后才可切换为 `SUPPORTED`**；在此之前保持 `NOT_IN_RELEASE_SCOPE`。其业务真值 blocker 已于 2026-10-02 关闭（Owner **11/11** PASS）。

## Phase 2 执行增量（2026-10-02；状态已更新为 PASS）

Phase 2 的 G01～G04 已完成，并经独立验收通过、以 PR #10 合并于 `7e16418aa32ced5512e26bd70227f01a329fbdfc`；当前状态为 **`PHASE_2_PASS`**（此前本节记录的 `EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE` 为交付当时状态，已被取代）。Phase 2 交付：Qt 占位导航、应用设置 SQLite、迁移、日志与 CI 工程底座。

**Phase 2 不等于参考标准闭环**：标准库/分析/记录页面当时没有业务功能，正式记录未实现，Excel 未实现，`as_of` 未决定，两个 Profile 的业务能力不变；因此 GB 19762 总体仍为 `PARTIAL`，不把工程底座当作参考标准闭环 PASS。历史执行证据见 `PHASE2_EXECUTION_REPORT.md`。

## Phase 3 执行增量（2026-10-02，执行中）

Phase 3 已获用户明确执行授权，状态 `IN_PROGRESS`。范围与设计见 `docs/32_Phase 3 GB19762离心泵统一正式纵向闭环.md`；阶段语义增量修正见路线原文第 8.2 节。本文件第 4 节已按 Phase 3 当前进展更新；**未完成的项不得在此标记为 `DONE`**。
