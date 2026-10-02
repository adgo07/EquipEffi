# EquipEffi 当前路线

> 本文件只回答五件事：① 当前路线是什么；② 当前产品目标是什么；③ 当前 Phase 是什么；④ Phase 2～10 接下来怎么走；⑤ 哪些旧路线只是 historical。
>
> **历史执行细节不在本文件承载**（Phase 0 全过程、P1-G01～G06 执行过程、固定 SHA 审批历史、Golden 审批过程、Numeric Adoption 过程、各 review gate 逐项展开）—— 这些由 `docs/governance/` 报告、各 manifest 与 `HANDOFF_20260831.md` 承载，本文件只保留链接。

## 1. 当前路线

- **Current Roadmap：** EquipEffi V2.3
- **路线原文：** [docs/28_EquipEffi 后续开发总体路线 V2.3.md](docs/28_EquipEffi%20后续开发总体路线%20V2.3.md)
- **V2.2 继承基线：** [docs/28_EquipEffi 后续开发总体路线 V2.2.md](docs/28_EquipEffi%20后续开发总体路线%20V2.2.md)
- 旧 v7–v15、T04.xx、旧 HANDOFF、编号执行清单统一标记为 `HISTORICAL / NOT AUTHORITATIVE FOR NEXT TASK`：保留事实价值，不拥有任务调度权。

## 2. 当前产品目标（2026-10-02 产品决定）

> **首个正式版完整支持 `GB 19762—2025《离心泵能效限定值及能效等级》`。**

“完整”必须覆盖 **`pump_water` 与 `pump_chemical`** 两个 Profile 及其适用范围、类别、输入、校验、公式、查表、修正、等级、未达标、不适用、无法判定/输入不足、标准依据、结果解释、Record、历史恢复与 Excel。

| Profile | `scope_status` | `support_status`（当前） | 标准开发成熟度 | 目标 |
|---|---|---|---|---|
| `pump_water` | `IN_V1` | `SUPPORTED` | `SUPPORTED` | 已达成 |
| `pump_chemical` | `IN_V1` | `NOT_IN_RELEASE_SCOPE` | `READY_FOR_IMPLEMENTATION` | `SUPPORTED` |
| `transformer` | `POST_V1` | `NOT_IN_RELEASE_SCOPE` | 未进入本轮标准开发流程 | 本轮暂缓，资产保留 |

三个维度（`scope_status` / `support_status` / 标准开发成熟度）**不得互相冒充**。`pump_chemical` 在 Golden 具名批准与 Stage D 独立验收通过前，`support_status` 不得写为 `SUPPORTED`。

- 权威范围文件：[V1_SCOPE.md](V1_SCOPE.md)
- 参考标准真实状态：[REFERENCE_STANDARD_ROADMAP.md](REFERENCE_STANDARD_ROADMAP.md)（当前总体 `PARTIAL`）

## 3. 当前 Phase

```text
Phase 0 = PASS
Phase 1 = PASS          (PHASE_1_PASS)
Phase 2 = PHASE_2_READY / NOT_STARTED
Automatic continuation = DISABLED
```

Phase 2 **不会自动开始**，进入 Phase 2 须用户明确授权。当前允许的工作是治理/范围/文档与 CI 收口，不是 Phase 2 执行。

## 4. Phase 2～10 接下来怎么走

| Phase | 语义 | 说明 |
|---|---|---|
| Phase 2 | 最小正式工程底座 | Python 3.12、PySide6 薄 AppShell、Design Token、Repository Protocol、三库职责、Migration 基础、Logging、有限工程清理。不得批量迁移 Profile、批量重写 evaluator、实现完整 Excel/产品 Shell/移动端/Suite，或一次性实现全部中央 DRAFT Contract。 |
| Phase 3 | `pump_water` 正式工程/生命周期纵向样板 | **Phase 3 PASS 不等于完整 GB 19762 PASS。** 不得重新设计泵算法；Approved Golden 是业务 Oracle。 |
| Phase 4 | 基于 `pump_water` 真实样板做必要通用化 | 只通用化已被样板证明的重复结构。 |
| Phase 5 | `pump_chemical` 接入同一正式工程链，完成 GB 19762—2025 全标准业务能力覆盖 | **`transformer` 不进入 Phase 5。** 完成前 `pump_chemical` 保持 `NOT_IN_RELEASE_SCOPE`。 |
| Phase 6 | 围绕完整 GB 19762 建立完整产品 Shell | 按真实用户任务组织。 |
| Phase 7 | 完整 GB 19762 的 Record、历史、恢复、结果解释、标准依据、异常状态与质量收口 | — |
| Phase 8 | 完整 GB 19762 Excel 闭环 | 必须同时覆盖 `pump_water` + `pump_chemical`；GUI/Excel 共用同一业务内核；数值入口须先完成设计与证据验证。 |
| Phase 9 | 完整 GB 19762 Windows V1 正式验收与发布 | `pump_chemical` 通过 Stage D 后切换 `support_status = SUPPORTED`。 |
| Phase 10 | 后续标准、公共包、综合版、多平台 | 参考标准闭环通过后再逐个扩展。 |

Phase 0～10 **编号与数量不得改变**；详细语义见路线原文第 8 节。

### Contract-driven Excel 跨阶段原则（继续有效）

```text
Product/Profile Contract = 字段类型、单位、枚举、必填和约束的业务真相源
Import Contract          = 外部 Sheet / 列 / 别名 / 单位转换 → stable field_id
UI Metadata              = 显示和交互投影
Ruleset                  = 真正评价逻辑
```

Excel 定位为 Import/Export Adapter，必须调用同一 `EvaluationService`/evaluator；**不得复制第二套评价算法**。

## 5. 权威入口

```text
ROADMAP.md
HANDOFF.md
TASK_STATE.md
AGENTS.md
BASELINE.md
ASSET_AUDIT.md
QA_BACKLOG.md
V1_SCOPE.md
REFERENCE_STANDARD_ROADMAP.md
STANDARD_ISSUES_REGISTER.md
UI_CURRENT_STATE_AUDIT.md
PLATFORM_BASELINE.md
platform-lock.json
ADR/
```

中央治理入口按 `AGENTS.md` 第 3 节与中央 `docs/GUIDE_INDEX.md` 路由：**Frozen 权威文件**（Architecture / Numeric Contract / Schema / Conformance）按本仓 `platform-lock.json` 的 locked SHA 读取；**ACTIVE / ACTIVE-EVOLVING 指南**（`GUIDE_INDEX.md`、`PRODUCT_DELIVERY_POLICY_V1.md`、`STANDARD_DEVELOPMENT_GUIDE_V0.1.md`、`UI_DESIGN_GUIDELINES_V0.1.md`）按中央当前已合并版本读取。两者冲突时以 locked Frozen 权威文件为准。

## 6. 保护边界

- 默认不重构、不扩功能、不批量修改 evaluator。
- `Legacy Regression` 保护旧行为；`Approved Golden Case` 才保护业务真相。
- 关键资源修改前后必须更新 `BASELINE.md` 哈希与 `HANDOFF.md` 事实。
- Windows V1 Scope 采用显式状态；未进入 Scope 的 Profile 必须显示“当前版本未支持”。
- **已暂缓的 `transformer` 属资产保留范围：其代码、标准数据、测试与历史资产不得删除或重构。**
- 不覆盖原始标准、原始模板、用户工作簿、校对册与发布产物。

## 7. Historical 入口

以下文件承载历史事实，**不是下一步调度来源**：

- [HANDOFF_20260831.md](HANDOFF_20260831.md) — 逐任务历史事实
- [docs/governance/](docs/governance/) — 各阶段执行/接入报告
- [PUMP_V2_G04_APPROVAL_MANIFEST.md](PUMP_V2_G04_APPROVAL_MANIFEST.md)、[PUMP_V2_R01_R06_COMMIT_MANIFEST.md](PUMP_V2_R01_R06_COMMIT_MANIFEST.md)、[PUMP_V2_R07_COMMIT_MANIFEST.md](PUMP_V2_R07_COMMIT_MANIFEST.md) — 泵审批与修订清单
- [QZC_N01_B_EXECUTION_REPORT.md](QZC_N01_B_EXECUTION_REPORT.md) — N01-B 实证报告（`HISTORICAL-SUPERSEDED`）
- `docs/23～docs/27` 编号执行清单 — `HISTORICAL`
