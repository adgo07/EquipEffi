# EquipEffi 当前交接

路线 EquipEffi V2.3；Phase 1 = PHASE_1_PASS；Phase 2 = PHASE_2_PASS；**Phase 3 = IN_PROGRESS**；automatic_continuation = DISABLED。

## 当前任务

用户已明确授权执行 **Phase 3：GB 19762—2025 离心泵统一正式纵向闭环**（`pump_water` + `pump_chemical` 共用同一产品、UI、Application Use Case、Workspace、Record、History、Result Contract）。

- 分支 `phase3/gb19762-unified-vertical-slice`；start master SHA `7e16418aa32ced5512e26bd70227f01a329fbdfc`
- 设计见 [docs/32_Phase 3 GB19762离心泵统一正式纵向闭环.md](docs/32_Phase%203%20GB19762%E7%A6%BB%E5%BF%83%E6%B3%B5%E7%BB%9F%E4%B8%80%E6%AD%A3%E5%BC%8F%E7%BA%B5%E5%90%91%E9%97%AD%E7%8E%AF.md)
- 执行者**不得**自行宣布 Phase 3 PASS、不得合并最终 PR、不得进入 Phase 4、不得发布、**不得自行把 `pump_chemical` 的 `support_status` 提升为 `SUPPORTED`**

## 阶段语义增量修正（2026-10-02）

产品负责人明确：清水泵与石油化工泵必须在**同一个正式 UI** 中出现，因为普通用户通常无法预先判断自己属于 water 还是 chemical。因此：

- **Phase 3** = 统一的 GB 19762 纵向闭环（两个 Profile 同页/同链）；两条规则**不得强行合并成一个巨型 evaluator**，`pump_water` / `pump_chemical` 只作为内部 rule profile identity；
- **Phase 5** 不再承担 `pump_chemical` 的「首次接入」，改为承担其**正式发布支持收口（Stage D）**；其余职责暂不重新设计；
- **不创建 V2.4**、不改变 Phase 0～10 编号、不提前 Phase 4/6/7/8/9。

完整记录见路线原文第 8.2 节。

## 产品状态

产品目标不变：Windows V1 完整 GB 19762—2025，`pump_water` + `pump_chemical`；`transformer` = `POST_V1`，保留资产。三个维度数值不变：

```text
pump_water    : scope_status=IN_V1 | support_status=SUPPORTED            | standard_maturity=SUPPORTED
pump_chemical : scope_status=IN_V1 | support_status=NOT_IN_RELEASE_SCOPE | standard_maturity=READY_FOR_IMPLEMENTATION
transformer   : scope_status=POST_V1 | support_status=NOT_IN_RELEASE_SCOPE
```

**pump_chemical 业务真值已批准**：Owner 于 2026-10-02 逐条批准 C1–C11，**11/11 PASS**，形式化为 11 条 `golden-case-0.5`（`specs/equipment_efficiency/golden/pump_chemical/`）。**剩余正式 blocker 仅为 Stage D 独立验收**，属 Phase 5。

`pump_water` 于 2026-10-02 完成 Owner Reconfirmation，**18/18 PASS**，18 条 golden-case-0.4 未修改。

## 中央锁

`ee5feb0cc34dbd99790500fadd0c4c932e202a20` 不变；Architecture V2.1 / Numeric v1 FROZEN，其余 DRAFT。ACTIVE 指南按中央当前合并版读取。Numeric adoption PR #5 的独立验收记录仍为 `INDEPENDENT_ACCEPTANCE_RECORD_PENDING`，不以任何执行替代该证据。

## 关键事实（Phase 3 执行中）

- 公开 Application 路径对 `pump_chemical` 仍**短路**返回 `NOT_IN_RELEASE_SCOPE` 且不计算（由 `tests/unit/test_pump_golden_case_0_3.py` 冻结）；因此 11 条化学 Golden 的 `evaluation_layer` 为 `PROFILE_EVALUATOR_TECHNICAL`，`support_status = null`，**未**谎报为 `APPLICATION_E2E`。
- 统一类别路由必须使用**精确名称**映射，不得用“清水/化工/多级”等子串猜测。
- `as_of`：`EQP-STD-GB19762-001` 已按软件产品决定关闭为 `RESOLVED`（新建分析默认本机当前日期、可修改、Finalize 冻结、Reopen 用原日期；`2026-08-23` 只是测试条件）。既有 CLI/API 的兼容默认值登记保留，全局取消须另立任务。
- `date(2026, 8, 23)` 隐式默认现存 6 处源码位置，已登记在 `TASK_STATE.md` 的 `known_blockers.as_of_implicit_default_legacy_entries`。

## 长期操作参考

- [docs/DEVELOPMENT_REFERENCE.md](docs/DEVELOPMENT_REFERENCE.md) — 已踩过的坑、关键文件、关键命令、回报格式
- 历史证据：[HANDOFF_20260831.md](HANDOFF_20260831.md)、[docs/governance/](docs/governance/)、`PUMP_V2_*_MANIFEST.md`、[QZC_N01_B_EXECUTION_REPORT.md](QZC_N01_B_EXECUTION_REPORT.md)
- Phase 2 交付证据：[PHASE2_EXECUTION_REPORT.md](PHASE2_EXECUTION_REPORT.md)

历史 Phase 1/2 审批不重复执行。`docs/planning/` 为既有未跟踪文件，未修改、未删除、未提交。
