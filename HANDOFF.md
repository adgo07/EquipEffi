# EquipEffi 当前交接

路线 EquipEffi V2.3；Phase 1 = PHASE_1_PASS；Phase 2 = PHASE_2_PASS；**Phase 3 = PHASE_3_PASS**（PR #11 合并 @ `87d9ef1bf32fb3f765d4f8ef3f97aa222913152a`）；**Phase 4 = PHASE_4_PASS**（PR #12 合并 @ `d6112ea9c7c1c16f95d798c2229cdc54aaf6240a`）；**Phase 5 = PHASE_5_PASS**（PR #13 合并 @ `f3e32f84123937ed6caa2b84b7cc0cd04c3100e0`，验收落档 `docs/phase5_acceptance_record.md`）；**Phase 6 = IN_PROGRESS**；automatic_continuation = DISABLED。

## 当前任务

用户已明确授权执行 **Phase 6：完整 GB 19762 Product Shell**——把 Phase 2～5 已成立的完整 GB 19762（`pump_water` + `pump_chemical`）业务能力组织成正式、完整、可长期使用的 Windows PySide6 产品 Shell。**不是重新设计业务算法。**

**状态**：`Phase 6 implementation = EXECUTION_COMPLETE` / `READY_FOR_INDEPENDENT_ACCEPTANCE`。**不得**自行宣布 `PHASE_6_PASS`；不得合并 PR；不得进入 Phase 7。

- 分支 `phase6/gb19762-product-shell`；base `f3e32f84123937ed6caa2b84b7cc0cd04c3100e0`
- Stage D 证据矩阵：`docs/phase5_stage_d_evidence_matrix.md`
- FORMAL_APPLICATION_E2E 证据：`specs/equipment_efficiency/evidence/phase5_chemical_stage_d_e2e.json`
- **正式发布用户表面（Owner 决定）= PySide6 Qt Desktop（`--qt`）**；`--json` / `ApplicationApi` / `--web` / JSONL / legacy Tk `--gui` / Android bridge / V4·Excel 是现存的 compatibility / development / future-adapter surfaces，其 support 差异登记为 `REGISTERED_DEVIATION`（`QA-P5-001`～`005`）
- 本阶段证据口径：**一个 GB19762 产品级 E2E 样板，其中有 water + chemical 两个真实内部 rule profile**（**不得**表述为已经有两个独立设备/标准 E2E 样板）

## Phase 4（已完成）

- 结论 `PHASE_4_PASS`；accepted head `a4034ef3751590b52a821d6a3bdbebcbca6a8ec9`；PR #12 merge `d6112ea9`
- 验收落档见 `docs/phase4_acceptance_record.md`；执行细节见 `PHASE4_EXECUTION_REPORT.md`

## Phase 3（已完成）

- 结论 `PHASE_3_PASS`；accepted head `728680dabf7b18e47ce9a5a23b296e405bc644a8`；PR #11 merge `87d9ef1b`
- 验收落档见 `docs/phase3_acceptance_record.md`（轻量格式，后续每个 Phase 沿用）
- 分支 `phase3/gb19762-unified-vertical-slice`；start master SHA `7e16418aa32ced5512e26bd70227f01a329fbdfc`
- 设计见 [docs/32_Phase 3 GB19762离心泵统一正式纵向闭环.md](docs/32_Phase%203%20GB19762%E7%A6%BB%E5%BF%83%E6%B3%B5%E7%BB%9F%E4%B8%80%E6%AD%A3%E5%BC%8F%E7%BA%B5%E5%90%91%E9%97%AD%E7%8E%AF.md)

## 阶段语义增量修正（2026-10-02）

产品负责人明确：清水泵与石油化工泵必须在**同一个正式 UI** 中出现，因为普通用户通常无法预先判断自己属于 water 还是 chemical。因此：

- **Phase 3** = 统一的 GB 19762 纵向闭环（两个 Profile 同页/同链）；两条规则**不得强行合并成一个巨型 evaluator**，`pump_water` / `pump_chemical` 只作为内部 rule profile identity；
- **Phase 5** 不再承担 `pump_chemical` 的「首次接入」，改为承担其**正式发布支持收口（Stage D）**；其余职责暂不重新设计；
- **不创建 V2.4**、不改变 Phase 0～10 编号、不提前 Phase 4/6/7/8/9。

完整记录见路线原文第 8.2 节。

## 产品状态

产品目标不变：Windows V1 完整 GB 19762—2025，`pump_water` + `pump_chemical`；`transformer` = `POST_V1`，保留资产。

```text
pump_water    : scope_status=IN_V1   | support_status=SUPPORTED                    | standard_maturity=SUPPORTED
pump_chemical : scope_status=IN_V1   | support_status=SUPPORTED                     | standard_maturity=SUPPORTED
                                      | 统一 Qt 正式路径取值 SUPPORTED；候选 SUPPORTED
transformer   : scope_status=POST_V1 | support_status=NOT_IN_RELEASE_SCOPE
```

**Phase 5 状态（不得误读）**：`pump_chemical` 的 Stage D 证据闭环已完成并交独立验收。
**独立验收通过前，治理状态只能说"支持提升候选"，不得写成"正式支持已经生效"。**
正式发布用户表面 = **PySide6 Qt Desktop（`--qt`）**。

**pump_chemical 业务真值已批准**：Owner 于 2026-10-02 逐条批准 C1–C11，**11/11 PASS**，形式化为 11 条 `golden-case-0.5`（`specs/equipment_efficiency/golden/pump_chemical/`，`evaluation_layer` 未改写）。**剩余正式 blocker 仅为 Stage D 独立验收结论。**

`pump_water` 于 2026-10-02 完成 Owner Reconfirmation，**18/18 PASS**，18 条 golden-case-0.4 未修改。

## 中央锁

`ee5feb0cc34dbd99790500fadd0c4c932e202a20` 不变；Architecture V2.1 / Numeric v1 FROZEN，其余 DRAFT。ACTIVE 指南按中央当前合并版读取。Numeric adoption PR #5 的独立验收记录仍为 `INDEPENDENT_ACCEPTANCE_RECORD_PENDING`，不以任何执行替代该证据。

## 关键事实（Phase 5 已交付，等待独立验收）

- **发布门禁为单一事实源** `application/services/pump_release_gate.py`；`CentrifugalPumpAnalysisService` 与 `EvaluationService` 都实际调用它。`pump_chemical` 在所有入口均为 `SUPPORTED`。
- **非正式表面语义已同步**：`--json` / `ApplicationApi` / JSONL / CLI / `--web` 对 `pump_chemical` 同样返回 `SUPPORTED` 并正常评价（Phase 6 R1 收口，`QA-P5-001/002` 已 `CLOSED`）。V4·Excel 保持 Phase 8（`QA-P5-003`）；Android bridge 与安装/签名/发布产物保持 Phase 9（`QA-P5-004/005`）。
- 11 条化学 Golden 的 `evaluation_layer` 仍为 `PROFILE_EVALUATOR_TECHNICAL`、`support_status = null`——它们表示**历史批准来源**；当前正式产品链的证据另见 `specs/equipment_efficiency/evidence/phase5_chemical_stage_d_e2e.json`。
- **历史 Record 冻结**：Phase 3/4 期间形成的 chemical Record 其 `result_snapshot.support_status` 仍为 `NOT_IN_RELEASE_SCOPE`，Reopen 不追溯改写、不重算。
- 统一类别路由必须使用**精确名称**映射，不得用"清水/化工/多级"等子串猜测。
- `as_of`：评价日期**不是业务门禁**（Owner，Phase 5）。正式 Qt 路径自动记录本机当前日期，用户无需关注；标准与日期不匹配时只给四字非阻断提醒（如"该标准尚未实施"），不改变 `evaluation_status` / `grade` / Finalize 权限，不自动切换标准。`EQP-STD-GB19762-001` 已 `RESOLVED`；遗留入口的旧门禁已由 Phase 6 R1 对离心泵豁免，`QA-P3-003` 已 `CLOSED`。

## 长期操作参考

- [docs/DEVELOPMENT_REFERENCE.md](docs/DEVELOPMENT_REFERENCE.md) — 已踩过的坑、关键文件、关键命令、回报格式
- 历史证据：[HANDOFF_20260831.md](HANDOFF_20260831.md)、[docs/governance/](docs/governance/)、`PUMP_V2_*_MANIFEST.md`、[QZC_N01_B_EXECUTION_REPORT.md](QZC_N01_B_EXECUTION_REPORT.md)
- Phase 2 交付证据：[PHASE2_EXECUTION_REPORT.md](PHASE2_EXECUTION_REPORT.md)

历史 Phase 1/2 审批不重复执行。`docs/planning/` 为既有未跟踪文件，未修改、未删除、未提交。
