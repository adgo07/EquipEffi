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
| `pump_chemical` | `IN_V1` | `SUPPORT_PROMOTION_CANDIDATE`（统一 Qt 正式路径取值 `SUPPORTED`） | `IMPLEMENTED`（`SUPPORTED` 为候选） | `SUPPORTED` |
| `transformer` | `POST_V1` | `NOT_IN_RELEASE_SCOPE` | 未进入本轮标准开发流程 | 本轮暂缓，资产保留 |

三个维度（`scope_status` / `support_status` / 标准开发成熟度）**不得互相冒充**。

**Phase 5 状态说明（不得误读）**：`pump_chemical` 的 Golden 早已具名批准（11/11），
Stage D 证据闭环已在 Phase 5 完成并交独立验收。**独立验收通过前，`support_status`
只能写 `SUPPORT_PROMOTION_CANDIDATE`，不得写"正式支持已经生效"。**
正式发布用户表面 = PySide6 Qt Desktop（`--qt`）；非正式表面的 support 差异
登记为 `REGISTERED_DEVIATION`（见 `QA_BACKLOG.md` 的 `QA-P5-001`～`005`）。

- 权威范围文件：[V1_SCOPE.md](V1_SCOPE.md)
- 参考标准真实状态：[REFERENCE_STANDARD_ROADMAP.md](REFERENCE_STANDARD_ROADMAP.md)（当前总体 `PARTIAL`）

## 3. 当前 Phase

```text
Phase 0 = PASS
Phase 1 = PHASE_1_PASS
Phase 2 = PHASE_2_PASS          (PR #10 独立验收并合并 @ 7e16418a)
Phase 3 = PHASE_3_PASS          (PR #11 独立验收并合并 @ 87d9ef1b)
          accepted head = 728680dabf7b18e47ce9a5a23b296e405bc644a8
          merge SHA     = 87d9ef1bf32fb3f765d4f8ef3f97aa222913152a
          acceptance record = docs/phase3_acceptance_record.md
Phase 4 = PHASE_4_PASS          (PR #12 独立验收并合并 @ d6112ea9)
          accepted head = a4034ef3751590b52a821d6a3bdbebcbca6a8ec9
          merge SHA     = d6112ea9c7c1c16f95d798c2229cdc54aaf6240a
          acceptance record = docs/phase4_acceptance_record.md
Phase 5 = IN_PROGRESS           (pump_chemical Stage D 正式支持与发布门禁收口)
          branch = phase5/pump-chemical-stage-d-support
          base   = d6112ea9c7c1c16f95d798c2229cdc54aaf6240a
          stage D candidate = READY_FOR_INDEPENDENT_ACCEPTANCE
Automatic continuation = DISABLED
```

Phase 2 已由独立验收通过并合并（PR #10）。**Phase 3 已由独立验收通过（`PHASE_3_PASS`）并以 PR #11 合并于 `87d9ef1b`**；验收落档见 `docs/phase3_acceptance_record.md`（轻量格式，后续每个 Phase 沿用）。Phase 4 已获用户明确执行授权，范围限于**最小生命周期通用化**：执行者**不得**自行宣布 Phase 4 PASS、不得合并 PR、不得进入 Phase 5、不得发布、不得把 `pump_chemical` 的 `support_status` 提升为 `SUPPORTED`。Phase 3 设计见 `docs/32_Phase 3 GB19762离心泵统一正式纵向闭环.md`。

### 3.1 增量修正：Phase 3 前移 pump_chemical 正式产品接入（2026-10-02）

产品负责人已明确：清水泵与石油化工泵必须在**同一个正式 UI** 中出现，因为普通用户通常**无法预先判断**自己属于 water 还是 chemical。

- **Phase 3** = GB 19762—2025 离心泵**统一**正式纵向闭环（`pump_water` + `pump_chemical` 共用同一产品、UI、Application Use Case、Workspace、Record、History、Result Contract）；
- 两条规则**不得强行合并成一个巨型 evaluator**；`pump_water` / `pump_chemical` 只作为**内部 rule profile / ruleset identity**，不得再设计为两个独立用户产品；
- **Phase 5** 不再承担 `pump_chemical` 的「首次接入」，改为承担其**正式发布支持收口（Stage D）**；Phase 5 其余职责暂不重新设计；
- **不创建 V2.4**，**不改变 Phase 0～10 编号**，**不提前 Phase 4/6/7/8/9**；
- 三个状态维度数值以第 2 节表格为唯一权威（Phase 5 起 `pump_chemical` 为
  `SUPPORT_PROMOTION_CANDIDATE` / `IMPLEMENTED`，候选 `SUPPORTED`）。

完整修正记录见路线原文第 8.2 节。

## 4. Phase 2～10 接下来怎么走

| Phase | 语义 | 说明 |
|---|---|---|
| Phase 2 | 最小正式工程底座 | **已完成**（`PHASE_2_PASS`）。Python 3.12、PySide6 薄 AppShell、设计 Token、Repository Protocol、三库职责、Migration 基础、Logging、有限工程清理。 |
| Phase 3 | **GB 19762—2025 离心泵统一正式纵向闭环**（`pump_water` + `pump_chemical`） | 产品层/UI/Application Use Case/Workspace/Record/History/Result Contract **合并**；两条规则不合并成巨型 evaluator。**Phase 3 PASS 不等于完整 GB 19762 的产品发布 PASS。** 不得重新设计泵算法；Approved Golden 是业务 Oracle。 |
| Phase 4 | 基于 `pump_water` 真实样板做必要通用化 | 只通用化已被样板证明的重复结构。 |
| Phase 5 | `pump_chemical` 的**正式发布支持收口（Stage D）**（不再承担首次接入，首次接入已前移到 Phase 3） | **`transformer` 不进入 Phase 5。** Phase 5 完成 Stage D 证据闭环并交独立验收；**独立验收通过前** `pump_chemical` 的治理状态保持 `SUPPORT_PROMOTION_CANDIDATE`（统一 Qt 正式路径取值 `SUPPORTED`）。 |
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
