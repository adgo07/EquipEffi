# EquipEffi 参考标准开发路线

状态：**CURRENT INVENTORY / GOVERNANCE ROADMAP**
盘点日期：2026-10-01
盘点基线：`master@66835d2ae2e0a8eaee50260f43ee0c52b4858d85`
参考标准：`GB 19762—2025 离心泵能效限定值及能效等级`

> 本文件只盘点当前真实状态并固定后续交付顺序，不启动 Phase 2，不修改 Pump evaluator、Canonical、Golden、数据库、Excel、UI 或 Numeric Profile。

## 1. 平台 / Contract 预检查

| 项目 | 结果 |
|---|---|
| 当前业务仓 SHA | `66835d2ae2e0a8eaee50260f43ee0c52b4858d85` |
| 当前默认分支 | `master` |
| `platform-lock.json` | 锁定中央 `ee5feb0cc34dbd99790500fadd0c4c932e202a20` |
| 中央 Contract | Architecture V2.1 FROZEN；Numeric Contract v1 FROZEN；Unit/Module/Workspace-Record/qzpack 仍 DRAFT |
| 当前项目 Numeric Profile | `EQUIPEFFI_PUMP_DECIMAL50_V2`，项目专属，不是平台全局默认 |
| 适用 MUST | Profile 显式、full-value business comparison、operation order/reference procedure、Windows-first、Excel 共用同一业务内核 |
| 适用 MUST NOT | 不自动跟随 central `main`；不把 Decimal50 推给所有设备；不把 Excel 另写一套算法；不越级启动 Phase 2 |
| 是否发现中央 Contract 冲突 | 否 |
| 是否需要修改中央 Contract | 否 |

中央产品交付治理文件：`Qingzhou-contracts/docs/governance/PRODUCT_DELIVERY_POLICY_V1.md`。该治理 Policy 不改变本仓 Frozen Contract lock。

## 2. 当前阶段事实

当前权威状态来自 `ROADMAP.md` / `TASK_STATE.md`：

```text
Phase 1: PHASE_1_PASS
Phase 2: PHASE_2_READY / NOT STARTED
Automatic continuation: DISABLED
```

Phase 1 已冻结/验证业务规范、Canonical/Product/Profile/Import Contract、Golden Case Schema、多维状态模型和 `pump_water` 样板标准映射；正式 PySide6 产品工程、记录生命周期和正式 Excel 仍属于后续阶段。

## 3. 状态定义

| 状态 | 中文解释 |
|---|---|
| `DONE` | 已完成，并有当前可核对证据 |
| `PARTIAL` | 部分完成；已有业务/工程资产但尚未形成完整产品交付 |
| `NOT STARTED` | 尚未按当前路线进入正式实现 |
| `BLOCKED` | 被明确依赖或治理条件阻塞 |

## 4. 参考标准现状盘点

| 项目 | 状态 | 证据与说明 |
|---|---|---|
| 标准库 | `PARTIAL` | Phase 1 已建立 Canonical/Product/Profile Schema 与 `pump_water` 标准映射，标准事实层已具备；但正式 Windows 产品中的“标准库发现→查看→选择→进入分析”纵向闭环尚未作为 V2.3 产品交付完成，Phase 2 还未开始。 |
| 新建设备分析 | `PARTIAL` | 已有正式 evaluator/API、输入输出契约、业务规范和 Golden；但新的 Windows PySide6 产品纵向入口属于后续工程阶段，尚未形成新路线要求的完整产品闭环。 |
| 分类 | `DONE` | Phase 1 已完成 `pump_water` 业务规范、Profile/状态模型和离心泵分类映射；18 条正式 `pump_water` Golden 0.4 已具名批准并用于业务真相验证。 |
| 输入 | `PARTIAL` | Product/Profile/Import Contract 与 Golden 输入模型已经建立；正式 Windows GUI 输入页/用户流程仍待 Phase 2 以后产品实现和验收。 |
| 校验 | `PARTIAL` | Pump evaluator 与 Phase 1 契约已有大量校验、边界测试和 Numeric tests；但产品层输入错误提示/GUI 闭环尚未按 Reference Standard 规则完成。 |
| Calculator | `DONE` | Pump evaluator API 回归 408/408 PASS；N01-B 实际执行 Decimal50、sqrt/ln/fractional pow、precision/operation-order sensitivity，Pump Numeric Contract 已采用 Numeric v1。 |
| 能效等级 | `DONE` | Approved Golden、generated boundary tests、Pump evaluator 回归和 N01-B 都对 rule/bucket/grade 进行正式校验。 |
| 不适用 | `PARTIAL` | Phase 1 多维 Support Status/业务规范已建立并通过 Solution/Product Review；但“不适用”在正式 Windows 产品页面中的完整交互和结果展示尚未作为产品闭环验收。 |
| 无法判定 | `PARTIAL` | 业务状态模型/契约已有明确语义；正式产品层输入不足/无法判定提示、结果页与记录边界尚未完成 Reference Standard E2E。 |
| 结果解释 | `PARTIAL` | Golden/trace/规则证据可解释技术结果，但面向用户的 Windows 结果解释、标准依据与来源展示尚未完成产品级纵向验收。 |
| 正式记录 | `NOT STARTED` | 当前 V2.3 Phase 2 尚未开始；正式新产品的 Workspace/Attempt/Record/Result 生命周期没有在 Reference Standard 产品闭环中实现。中央 Record Contract 仍 DRAFT，也没有被本路线擅自采用。 |
| Windows | `PARTIAL` | Windows V1 是明确产品目标，已有旧产品/测试资产；但 V2.3 的最小正式 PySide6 AppShell 仍是 Phase 2 设计输入，当前 Phase 2 尚未开始，因此不能标记 Reference Standard Windows 交付 DONE。 |
| Excel | `NOT STARTED` | Phase 1 已有 Import Contract，证明未来 Excel 应 contract-driven；`ROADMAP.md` 明确正式 Excel 仍在 Phase 8。当前未进入正式 Excel 开发，不得把 Import Contract 当作 Excel 实现完成。 |
| Conformance | `DONE` | N01-B Independent Acceptance PASS；Pump Numeric/Decision Contract、precision/operation-order/reference procedure 和 Numeric v1 adoption 均有执行测试证据。 |
| Golden Case | `DONE` | `pump_water` Golden 0.4 共 18 条，已由具名审核人批准，review_flags 清空，并有 validator/固定 SHA/独立复验与 Solution/Product Review 证据。 |
| 下一标准准备状态 | `NOT STARTED` | Phase 1 明确没有批量迁移 17 个 Profile。按新产品交付治理，先完成离心泵核心 Windows 产品闭环和 Excel 闭环，再选第二个标准验证架构扩展性；本任务不启动第二标准。 |

## 5. 当前结论

GB 19762—2025 的 **业务规则、Pump Calculator、Numeric Conformance 与 Golden Case 已经是当前最成熟资产**；主要缺口位于产品工程层，而不是重新设计泵算法：

```text
正式 Windows 产品壳与导航
+ 标准库→新建分析→输入→结果纵向闭环
+ 不适用/无法判定的产品交互
+ 正式记录/历史生命周期
+ Reference Standard Excel 闭环
```

因此当前 Reference Standard 总体状态：

`PARTIAL`

这不是中央 Contract 阻塞。当前真正的阶段门禁是：Phase 2 尚未获得用户明确启动授权。

## 6. 后续交付顺序

在用户另行授权后，建议继续遵守既有 V2.3 阶段路线，同时把 Reference Standard Gate 作为产品验收主线：

1. 进入 Phase 2，建立最小正式 Windows 工程底座；
2. 后续阶段把 `pump_water` 打通标准库→分析→结果→正式记录的 Core Vertical Slice；
3. 完成 Windows 10/11、中文、高 DPI、路径/文件、SQLite、异常输入、打包验收；
4. 到正式 Excel 阶段时，只实现 Import/Export Adapter，统一调用同一 EvaluationService/evaluator；
5. 完成 GUI↔Excel 同输入同结果验证；
6. Reference Standard Gate PASS 后，再选择第二标准验证扩展架构。

本治理任务不自动启动 Phase 2 或上述实现。
