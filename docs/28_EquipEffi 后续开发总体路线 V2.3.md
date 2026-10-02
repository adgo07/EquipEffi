# EquipEffi 后续开发总体路线 V2.3

**文档版本：** V2.3
**适用项目：** EquipEffi 设备能效分析软件
**文档性质：** 当前正式总体路线（V2.2 增量校准版）
**状态：** Approved for Phase 2 readiness
**继承基线：** `docs/28_EquipEffi 后续开发总体路线 V2.2.md`
**上位治理：** `Qingzhou-contracts` 锁定基线 + 本仓 `PLATFORM_BASELINE.md` / `platform-lock.json`

---

# 1. V2.3 的定位

V2.3 **不推翻、不重写** V2.2，也不改变 Phase 0～10 的总体阶段结构。

V2.2 中未被本文件明确修改的章节、原则、门禁和阶段定义继续有效。V2.3 只把 Phase 0、Phase 1 已完成事实、Qingzhou-contracts 接入结果、Phase 1 已验证的多维状态模型，以及未来 Contract-driven Excel 约束反馈到总体路线。

V2.2 的核心策略继续保持：

> **冻结旧基线 → 建立业务真相 → 保护现有正确行为 → 渐进改造工程结构 → 用真实纵向样板验证新体系 → 分 Profile 迁移 → 完成 Windows V1 产品闭环。**

继续坚持：

> **业务真相先于代码结构。**

> **受证据、Approved Golden Case 和回归基线保护的渐进式改造。**

---

# 2. V2.3 生效时的项目事实

```text
master baseline:
b336fd313ea8e3ee1c688786c05d126d76dc2699

Phase 0:
PASS

Phase 1:
PASS

QZC-A01:
COMPLETE

Phase 1 业务真相样板:
pump_water / GB 19762—2025

pump_water Approved Golden 0.4:
18

Windows V1 IN_V1 Profile:
transformer
pump_water

Qingzhou-contracts locked commit:
0cd74d783fa23add6dc881b408a8c8ba8503f8e8

Architecture:
V2.1 FROZEN

Phase 2:
READY / NOT_STARTED

automatic continuation:
DISABLED
```

> **口径更正（2026-10-01）**：上方摘要中的 `Qingzhou-contracts locked commit` 为 V2.3 校准当时（2026-09-28）口径；历史口径 `0cd74d783fa23add6dc881b408a8c8ba8503f8e8` 已被 2026-10-01 的 Numeric Contract v1 Adoption 取代。当前 locked commit 为 `ee5feb0cc34dbd99790500fadd0c4c932e202a20`。当前权威来源：`platform-lock.json`、`PLATFORM_BASELINE.md`、`ROADMAP.md`、`docs/governance/NUMERIC_CONTRACT_V1_ADOPTION_REPORT.md`。历史正文保留不改写。

Phase 2 只有在用户明确授权后才能开始。

---

# 3. 上位治理校准：Qingzhou-contracts

治理层级正式明确为：

```text
Qingzhou-contracts 锁定基线
        ↓
EquipEffi 总体路线 V2.3
        ↓
当前 Phase 执行方案
        ↓
Goal / Task
```

当前锁定：

```text
repository:
https://github.com/adgo07/Qingzhou-contracts.git

commit:
0cd74d783fa23add6dc881b408a8c8ba8503f8e8

Architecture:
V2.1 FROZEN
```

Numeric、Unit、Module/Capability、Workspace/Attempt/Record/Result、qzpack 等公共 Contract 当前仍为：

```text
DRAFT / NOT YET RELEASED
```

> **口径更正（2026-10-01）**：本节“当前锁定”的 commit 与 Contract 状态均为 V2.3 校准当时（2026-09-28）口径。当前 locked commit 为 `ee5feb0cc34dbd99790500fadd0c4c932e202a20`；Numeric Contract 已由本仓正式采用为 `v1 / FROZEN`，Unit、Module/Capability、Workspace/Attempt/Record/Result、qzpack 仍为 `DRAFT / NOT YET RELEASED`。当前权威来源：`platform-lock.json`、`PLATFORM_BASELINE.md`、`ROADMAP.md`、`docs/governance/NUMERIC_CONTRACT_V1_ADOPTION_REPORT.md`。历史正文保留不改写。

因此：

1. EquipEffi 不实时跟随 `Qingzhou-contracts/main`；
2. 只有显式升级 `PLATFORM_BASELINE.md` 与 `platform-lock.json` 后，新公共 Contract 才对本项目生效；
3. 中央 DRAFT Contract 只能作为兼容方向和设计约束；
4. 不得因为已经接入中央治理，就在 EquipEffi 中提前一次性完整实现全部 DRAFT Contract；
5. 国家/行业标准原文、Canonical 标准事实、单 Profile 专属算法和已批准 Golden 仍由 EquipEffi 专业业务治理负责；
6. 跨产品/跨平台的公共 Contract 缺口进入 Qingzhou-contracts RFC/决策流程，不在 EquipEffi 永久私自定义公共规则。

---

# 4. 状态模型校准

V2.2 第 28 节中将多种不同性质状态混入单一 Support Status 的早期表述，被 Phase 1 的真实 `pump_water` 样板取代。

V2.3 正式采用多维状态模型：

```text
scope_status
support_status
category_status
evaluation_status
grade
conclusion
REQUIRES_REVIEW（独立评审流程）
```

## 4.1 scope_status

产品范围决策：

```text
IN_V1
UNDER_REVIEW
POST_V1
```

## 4.2 support_status

发布能力维度。当前经 `pump_water` 验证的公共 Application 契约至少使用：

```text
SUPPORTED
NOT_IN_RELEASE_SCOPE
```

## 4.3 category_status

类别解析/业务适用性维度。`pump_water` 当前使用：

```text
APPLICABLE
NOT_APPLICABLE
UNRESOLVED
```

未来其他 Profile 可按自身业务契约定义，不要求机械复制该枚举。

## 4.4 evaluation_status

本次评价执行结果维度。`pump_water` 当前使用：

```text
SUCCESS
OUT_OF_STANDARD_SCOPE
INSUFFICIENT_DATA
INVALID_INPUT
```

未来其他 Profile 可按自身业务契约定义。

## 4.5 grade / conclusion / review

`grade` 与 `conclusion` 独立于上述状态。

`REQUIRES_REVIEW` 属于人工评审/治理流程，不是运行结果枚举，不得重新塞回单一 Support Status。

V2.3 不修改任何已批准的 `pump_water` 行为、Golden、数值契约或 V1 Scope 决策。

---

# 5. Phase 2 校准：最小正式工程底座

V2.2 对 Phase 2 的总体方向继续有效。

Phase 2 的目标仍然是建立**最小正式工程底座**，而不是开始大规模业务迁移。

## 5.1 Phase 2 允许

```text
Python 3.12
PySide6 薄 AppShell
Design Token
Repository Protocol
catalog / user / records 三库职责
Migration 基础
Logging
有限、可证据化的工程结构清理
```

可以继续处理已经登记的：

- 双正式架构；
- 循环依赖；
- 包级反向依赖；
- 大型 metadata 职责拆分；
- 已确认的 DELETE_CANDIDATE。

## 5.2 Phase 2 禁止

```text
批量迁移 17 Profile
批量重写 evaluator
完整 Excel 产品功能
完整产品 Shell
Android / HarmonyOS / iOS
Suite
一次性实现全部中央 DRAFT Contract
为了“统一架构”修改已批准 pump_water 业务真值
```

Phase 2 的工程改造必须继续受 Legacy Regression、Approved Golden、Canonical 和 Phase 1 已冻结业务契约保护。

---

# 6. Phase 1 与 Phase 3 的 pump_water 样板职责不同

## Phase 1 pump_water

Phase 1 已完成的是**业务真相样板**，回答：

> 正确业务到底是什么？

已经形成的事实包括：

```text
标准证据
输入契约
状态契约
Numeric & Decision Contract
公式与边界
Canonical 映射
Approved Golden
V1 Scope
```

## Phase 3 pump_water

Phase 3 仍然是**正式工程/生命周期纵向样板**，回答：

> 新正式架构能否完整承载已经批准的业务真相？

Phase 3 继续验证：

```text
规范
↓
Canonical
↓
Product/Profile Schema
↓
Ruleset
↓
Approved Golden
↓
Domain
↓
Application
↓
PySide6
↓
Workspace
↓
Record
↓
Reopen / Reproduce
```

Phase 3 **不得重新研究或重新设计 GB 19762—2025 离心泵算法**。Phase 1 已批准的 `pump_water` Golden 0.4 是 Phase 3 的业务 Oracle。

---

# 7. Contract-driven Excel 跨阶段原则

正式 Excel 产品能力仍保持在 **Phase 8**，不提前到 Phase 2。

V2.2 已冻结的唯一允许链路继续有效：

```text
Excel
 ↓
Import Contract
 ↓
Parser
 ↓
Domain Input
 ↓
Application Service
 ↓
Domain
 ↓
Workspace / Record
```

并继续禁止：

> **Excel 专用评价算法。**

V2.3 增加以下跨阶段约束：

```text
Product/Profile Contract
= 字段类型、单位、枚举、必填和约束的业务真相源

Import Contract
= 外部 Sheet / 列 / 别名 / 单位转换 → stable field_id

UI Metadata
= 显示和交互投影

Ruleset
= 真正评价逻辑
```

Phase 2～4 必须保证未来 Excel 能够从同一字段契约生成或验证，不得形成：

```text
软件输入校验一套
+
Excel 数据验证一套
+
Python 导入校验又一套
```

未来批量 Excel 的正式方向：

1. 空白模板由版本化契约生成或验证；
2. Excel Data Validation 是 Product/Profile Contract 的投影，不是独立业务规则；
3. Import Contract 只负责外部字段映射和安全解析；
4. 批量行统一进入 `EvaluationService`；
5. Excel 不复制标准公式、查表、等级比较或结论逻辑；
6. 结果长期按 stable `result_field_id` 回写；
7. 正式模板生成、批量读取、逐行错误、结果写回、Word/PDF 等仍在 Phase 8 实施。

---

# 8. Phase 0～10 总体阶段结构保持不变

```text
Phase 0
重新基线与治理切换
        ↓
Phase 1
业务规范与数据契约
        ↓
Phase 2
最小正式工程底座
        ↓
Phase 3
真实纵向样板
        ↓
Phase 4
经过样板验证后的通用化
        ↓
Phase 5
V1 Profile 渐进迁移
        ↓
Phase 6
完整产品 Shell
        ↓
Phase 7
生命周期与质量收口
        ↓
Phase 8
Excel / 报告 / 发布外围能力
        ↓
Phase 9
Windows V1 全量验收
        ↓
Phase 10
公共包 / 综合版 / 多平台
```

V2.3 **不新增阶段、不删除阶段、不重新编号**。

---

# 9. 继续冻结的 V2.2 核心原则

以下内容原样继承，不因 V2.3 改变：

- Canonical JSON 是标准和正式参考数据唯一事实源；
- Python 不作为标准事实数据主源；
- SQLite 是运行时/查询格式，不是标准事实源；
- Golden-protected incremental migration；
- Legacy Regression ≠ Golden Truth；
- 一个业务能力只能存在一个正式实现；
- 旧 evaluator 不允许一次性重写；
- Profile 独立渐进迁移；
- Approved Golden 未建立、新实现未验证前，旧正式实现不得删除；
- Workspace 与 Record 分离；
- Record 不可静默改写；
- 三库职责继续保持；
- 先薄 AppShell，再扩展完整产品页面；
- Phase 4 之前不进行脱离真实样板的理论式大通用化；
- Phase 5 只迁移 IN_V1 Profile；
- Phase 8 正式实现 Excel / 报告等外围能力；
- Phase 9 Windows V1 全量验收；
- Phase 10 才考虑综合版和多平台产品。

---

# 10. 当前唯一允许的下一步

V2.3 生效后：

```text
Phase 0 = PASS
Phase 1 = PASS
QZC-A01 = COMPLETE
Phase 2 = READY / NOT_STARTED
```

当前唯一允许的下一步是：

> **等待用户明确授权后，设计并执行 Phase 2。**

在用户授权 Phase 2 前，不得：

- 自动领取 Phase 2 Goal；
- 开始 PySide6 正式实现；
- 做工程结构清理；
- 开发 Excel；
- 批量迁移 Profile；
- 启动 Suite 或移动端；
- 把中央 DRAFT Contract 擅自实现为本项目永久规则。

`automatic_continuation = DISABLED`。

---

# 11. V2.3 最终路线结论

V2.3 不改变 V2.2 的渐进式工程路线，而是把 Phase 0～1 的真实实践成果、Qingzhou-contracts 上位治理和未来 Contract-driven Excel 要求反馈回总体路线，使 Phase 2～10 在真实基线上继续执行。

继续坚持：

> **保业务真相，不保历史偶然结构。**

> **保正确算法，不保不必要兼容层。**

> **保标准研究成果，不保 Python 硬编码形式。**

> **保经过证据确认的行为，不盲目保旧行为。**

> **任何新实现必须先证明自己没有丢掉旧系统真正有价值的专业知识。**

V2.3 的目标不是继续增加路线版本，而是完成一次必要校准。后续新增问题优先进入 ADR、QA Backlog 或具体 Phase 方案；只有总体阶段骨架本身被实践证明需要改变时，才升级总体路线版本。
