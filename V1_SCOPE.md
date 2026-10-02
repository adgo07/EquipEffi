# Windows V1 Scope

**状态：** 产品范围已于 2026-10-02 由产品负责人正式收口并取代 2026-09-23 范围映射；Phase 1 Solution/Product Review 结论（P1-SR01=PASS；review baseline 38bdfc28e078fee067743d30055fb39337881c7c）继续有效。当前 `Phase 1 = PHASE_1_PASS`、`Phase 2 = PHASE_2_READY / NOT_STARTED`；本次范围收口**不构成 Phase 2 启动授权**，Phase 2 仍须用户明确授权。
**原则：** 不默认 15 类公共设备或 17 个内部 Profile 全部首发；不允许“半支持”。

## 0. Windows V1 正式产品目标（2026-10-02）

> **首个正式版完整支持 `GB 19762—2025《离心泵能效限定值及能效等级》`。**

“完整”不得仅指 `pump_water`。Windows V1 必须最终覆盖当前 GB 19762—2025 软件设计中的**全部 Profile**：

```text
pump_water     清水离心泵
pump_chemical  石化（化工）离心泵
```

并覆盖各 Profile 的：适用范围；类别；输入；校验；公式；查表；修正；等级；未达标；不适用；无法判定 / 输入不足；标准依据；结果解释；Record；历史恢复；Excel。

`transformer`（变压器）本轮**暂缓**：保留其全部代码、标准数据、测试与历史资产，不删除、不重构，本轮 Windows V1 不再继续开发 transformer。详见第 8 节产品决策记录。

## 1. 状态模型与产品范围字段边界

Windows V1 的产品范围决策（`scope_status`）、发布能力（`support_status`）、标准开发成熟度（中央 Standard Development Guide 支持状态）与运行时评价结果分开记录，**四个维度不得互相冒充**。以下运行时状态定义对应当前已验证的 pump_water V2；其他 Profile 按自己的业务契约定义类别状态，不要求完全相同。

| 字段/维度 | 语义 | 当前术语 | 定义来源 |
|---|---|---|---|
| `scope_status` | 产品范围决策（本仓维度） | `IN_V1` / `UNDER_REVIEW` / `POST_V1` | 本仓产品决策，见本文件 |
| `support_status` | 发布能力是否可用 | `SUPPORTED` / `NOT_IN_RELEASE_SCOPE` | 本仓发布门禁；pump_water V2 已验证 |
| 标准开发成熟度 | 标准接入的阶段成熟度 | `CATALOG_ONLY` / `MAPPING` / `READY_FOR_IMPLEMENTATION` / `IMPLEMENTED` / `SUPPORTED` | 中央 `STANDARD_DEVELOPMENT_GUIDE_V0.1.md` §19 |
| `category_status` | 类别解析/适用性 | pump_water：`APPLICABLE` / `NOT_APPLICABLE` / `UNRESOLVED` | 本仓业务规范 |
| `evaluation_status` | 本次评价执行结果 | pump_water：`SUCCESS` / `OUT_OF_STANDARD_SCOPE` / `INSUFFICIENT_DATA` / `INVALID_INPUT` | 本仓业务规范 |
| `grade` / `conclusion` | 等级和对外结论 | 独立于以上状态字段；`BELOW_MINIMUM` 是 pump_water 的评价等级结果 | 本仓业务规范 |
| `REQUIRES_REVIEW` | 人工评审流程处置/提示 | 不属于任何运行结果枚举，也不替代 `scope_status` 或 `support_status` | 本仓业务规范 |

### 1.1 维度边界（重要）

- `scope_status` 是**本仓产品范围维度**，回答“这个 Profile 属不属于 Windows V1 正式范围”。它**不是**中央支持状态，也不得被当作发布能力声明。
- `support_status` 回答“当前版本是否提供该 Profile 的正式评价能力”。它**只能**由本仓发布门禁决定，且**不得**在缺少独立验收证据时写为 `SUPPORTED`。
- 标准开发成熟度是**中央 ACTIVE 指南**的维度，回答“该标准的接入走到了 Stage A/B/C/D 的哪一步”。它是**开发阶段记录**，不得替代 `support_status`。
- 旧草案中的 `UNSUPPORTED_STANDARD` 不再作为共享 `support_status` 值。标准证据不足应记录在 Profile/标准证据和评审资料中；若没有可发布能力，运行时发布门禁使用 `NOT_IN_RELEASE_SCOPE`。`REQUIRES_REVIEW` 属于评审流程，Profile 的 `UNDER_REVIEW` 可在 UI 显示“需要复核”提示，但两者都不是 `evaluation_status`。
- `UNDER_REVIEW` 只在 `scope_status` 维度使用，不是中央承认的支持状态名（中央 `STANDARD_DEVELOPMENT_GUIDE_V0.1.md` §19 的 5 个状态中不含该值）。

`POST_V1` 或 `UNDER_REVIEW` 的 Profile 不得仅凭范围登记显示为运行时已支持；UI 必须按 Profile 分别展示范围决策、当前发布能力与标准开发成熟度。

## 2. 15 公共类型与 17 Profile

| public_device_type | 中文 | internal profiles |
|---|---|---|
| transformer | 变压器 | transformer |
| motor | 电动机 | motor_lv；motor_hv；motor_pmsm |
| compressor | 空压机 | compressor |
| centrifugal_pump | 离心泵 | pump_water；pump_chemical |
| centrifugal_fan | 离心通风机 | fan |
| axial_fan | 轴流通风机 | fan |
| blower | 鼓风机 | blower |
| submersible_pump | 潜水电泵 | submersible |
| industrial_boiler | 工业锅炉 | boiler |
| heat_treatment | 热处理设备 | heat_treatment |
| heat_pump_chiller | 热泵和冷水机组 | heat_pump_chiller |
| heat_pump_water_heater | 热泵热水机 | heat_pump_water_heater |
| duct_ac | 风管送风式空调 | duct_ac |
| unitary_ac | 单元式空调 | unitary_ac |
| multi_split_ac | 多联式空调 | multi_split_ac |

## 3. 17 Profile 注册表

`legacy_tests` 是 Phase 0 对命中测试模块的粗盘点，不等于 Approved Golden Case 数量；`known_P0` 只表示已登记风险，不表示已经确认标准错误。

| public type | profile_id | standard / pack | current evaluator | legacy tests | known P0 | known P1 | data quality | source quality | canonical readiness | golden candidates | release surface | scope status | standard maturity |
|---|---|---|---|---:|---|---|---|---|---|---|---:|---|---|---|
| transformer | transformer | GB 20052-2024 / `gb20052_2024_v1` | TransformerEvaluator | 14 | 0 confirmed | shared architecture | 546 rows | MEDIUM | REVIEW | 2 | V1_RUNTIME | POST_V1 | 未进入本轮标准开发流程 |
| motor | motor_lv | GB 18613-2020 / `gb18613_2020_v1` | MotorEvaluator | 22 shared | V4 P0 candidate | shared architecture | 42 rows | MEDIUM | REVIEW | 2 | V1_RUNTIME | POST_V1 | 未进入本轮标准开发流程 |
| motor | motor_hv | GB 30254-2024 / `gb30254_2024_v1` | MotorEvaluator | 22 shared | 0 confirmed | shared architecture | tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | POST_V1 | 未进入本轮标准开发流程 |
| motor | motor_pmsm | GB 30253-2024 / `gb30253_2024_pdf_verified_v1` | PmsmEvaluator | 22 shared | 0 confirmed | provenance/contract | 29 tables | HIGH | REVIEW | 1 | V1_RUNTIME | POST_V1 | 未进入本轮标准开发流程 |
| compressor | compressor | GB 19153-2019 / `gb19153_2019_v1` | CompressorEvaluator | 10 | 0 confirmed | shared architecture | 2469 rows | MEDIUM-HIGH | REVIEW | 1 | V1_RUNTIME | POST_V1 | 未进入本轮标准开发流程 |
| centrifugal_pump | pump_water | GB 19762-2025 / `gb19762_2025_water_v1` | WaterPumpEvaluator | 13 | 0 confirmed | shared architecture | formula + CI | MEDIUM-HIGH | PHASE1_CANDIDATE | 4 | V1_RUNTIME | IN_V1 | SUPPORTED |
| centrifugal_pump | pump_chemical | GB 19762-2025 / `gb19762_2025_chemical_v1` | ChemicalPumpEvaluator | 13 shared | 0 confirmed | shared architecture | formula + tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | IN_V1 | READY_FOR_IMPLEMENTATION |
| centrifugal_fan / axial_fan | fan | GB 19761-2020 / `gb19761_2020_v1` | FanEvaluator | 9 shared | 0 confirmed | boundary review | 4 tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW | 未进入本轮标准开发流程 |
| blower | blower | GB 28381-2012 / `gb28381_2012_v1` | BlowerEvaluator | 9 | 0 confirmed | missing-input trace | 8 tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW | 未进入本轮标准开发流程 |
| submersible_pump | submersible | GB 32030-2022 / `gb32030_2022_v1` | SubmersibleEvaluator | 11 | 0 confirmed | calculation provenance | 5 tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW | 未进入本轮标准开发流程 |
| industrial_boiler | boiler | GB 24500-2020 / `gb24500_2020_v1` | BoilerEvaluator | 10 | 0 confirmed | input gate | 4 tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | POST_V1 | 未进入本轮标准开发流程 |
| heat_treatment | heat_treatment | GB/T 36561-2018 / `gbt36561_2018_v1` | HeatTreatmentEvaluator | 10 | 0 confirmed | input gate | coefficients + table8 | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW | 未进入本轮标准开发流程 |
| heat_pump_chiller | heat_pump_chiller | GB 19577-2024 / `gb19577_2024_pdf_verified_v1` | HvacEvaluator | 8 | 0 confirmed | source/contract | nested 5-device pack | HIGH | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW | 未进入本轮标准开发流程 |
| heat_pump_water_heater | heat_pump_water_heater | GB 29541-2013 / `gb29541_2013_v1` | HvacEvaluator | 8 shared | 0 confirmed | source/contract | nested HVAC pack | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW | 未进入本轮标准开发流程 |
| duct_ac | duct_ac | GB 37479-2019 / `gb37479_2019_v1` | HvacEvaluator | 8 shared | 0 confirmed | source/contract | nested HVAC pack | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW | 未进入本轮标准开发流程 |
| unitary_ac | unitary_ac | GB 19576-2019 / `gb19576_2019_v1` | HvacEvaluator | 8 shared | 0 confirmed | source/contract | nested HVAC pack | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW | 未进入本轮标准开发流程 |
| multi_split_ac | multi_split_ac | GB 21454-2021 / `gb21454_2021_v1` | HvacEvaluator | 8 shared | 0 confirmed | source/contract | nested HVAC pack | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW | 未进入本轮标准开发流程 |

## 4. 产品决策记录（2026-10-02，现行有效）

本节记录 Windows V1 产品范围的**现行**产品决策。它**取代** `USER_PROVIDED_PRODUCT_DECISION_2026-09-23` 的范围映射；2026-09-23 的决定作为历史证据在第 5 节原样保留，不改写、不删除。

```text
decision_owner: 王玮
decision_role: 总经理
decision_date: 2026-10-02
risk_acceptor: 王玮（总经理）
evidence_id: USER_PROVIDED_PRODUCT_DECISION_2026-10-02
evidence_type: PRODUCT_OWNER_DECISION
supersedes: USER_PROVIDED_PRODUCT_DECISION_2026-09-23
automatic_scope_expansion: DISABLED
```

| 决策项 | 决策内容 | 记录理由 |
|---|---|---|
| Windows V1 正式产品目标 | 首个正式版**完整支持** `GB 19762—2025《离心泵能效限定值及能效等级》` | 以单一参考标准的完整闭环收敛产品目标，符合 Windows-first 与 Reference Standard first |
| “完整”的范围定义 | 必须覆盖 `pump_water` **与** `pump_chemical` 两个 Profile 及其适用范围、类别、输入、校验、公式、查表、修正、等级、未达标、不适用、无法判定/输入不足、标准依据、结果解释、Record、历史恢复、Excel | 不得把“完整支持 GB 19762—2025”缩窄为只支持 `pump_water` |
| `transformer`（变压器） | **本轮暂缓**：本轮 Windows V1 不再继续开发 transformer；保留其全部代码、标准数据、测试与历史资产，**不删除、不重构** | 资源集中于参考标准的完整闭环；变压器资产保留待后续独立规划 |
| 风险接受人 | 王玮，总经理 | 与产品决策负责人相同 |

### 4.1 Profile 级范围映射（本次冻结）

| Profile | `scope_status` | `support_status`（当前） | 标准开发成熟度 | 目标 |
|---|---|---|---|---|
| `pump_water` | `IN_V1` | `SUPPORTED` | `SUPPORTED` | 已达成 |
| `pump_chemical` | `IN_V1` | `NOT_IN_RELEASE_SCOPE` | `READY_FOR_IMPLEMENTATION` | `support_status = SUPPORTED` |
| `transformer` | `POST_V1` | `NOT_IN_RELEASE_SCOPE` | 未进入本轮标准开发流程 | 本轮不排期；资产保留 |

**`pump_chemical` 的当前状态说明（重要）：**

- `scope_status = IN_V1` 表示 `pump_chemical` **已确定属于 Windows V1 正式范围**，本轮必须完成其标准开发与产品实现；
- `support_status = NOT_IN_RELEASE_SCOPE` 是**当前**发布能力事实，**在以下两项完成前不得改写为 `SUPPORTED`**：
  1. `pump_chemical` Golden Case 获得具名业务批准（当前 8 条候选仍为 technical-only，未获 V1 Golden 批准）；
  2. 中央 `STANDARD_DEVELOPMENT_GUIDE_V0.1.md` §3/§18 要求的 Stage D 正式验收通过，并有独立验收证据。
- 中央指南 §19 明确 **不得无证据跳级**、`SUPPORTED` 定义为“完整要求通过独立验收”。因此“进入了产品范围”**不等于**“已经正式支持”。
- 达到验收后，切换 `support_status` 为 `SUPPORTED` 并同步本文件、`REFERENCE_STANDARD_ROADMAP.md` 与 Results/Record 契约。

### 4.2 中央标准开发成熟度对照

`pump_chemical` 的成熟度按中央 `STANDARD_DEVELOPMENT_GUIDE_V0.1.md` §19 记录为 `READY_FOR_IMPLEMENTATION`（“Mapping、主要输入输出和业务规则已明确，可以进入实现”）。该值属于**标准开发阶段维度**，不是 `support_status`，不得互相冒充（中央指南 §19–20）。

## 5. 历史产品决策记录（2026-09-23，已被第 4 节取代）

> 本节为**历史证据**，原样保留以便追溯。其 Profile 级范围映射已被 2026-10-02 决定取代，**不再作为当前产品范围依据**。

```text
decision_owner: 王玮
decision_role: 总经理
decision_date: 2026-09-23
risk_acceptor: 王玮（总经理）
evidence_id: USER_PROVIDED_PRODUCT_DECISION_2026-09-23
evidence_type: PRODUCT_OWNER_DECISION
status: SUPERSEDED_BY_USER_PROVIDED_PRODUCT_DECISION_2026-10-02
```

| 决策项 | 当时的决策内容 | 记录理由 |
|---|---|---|
| Windows V1 首发支持 | 变压器、离心泵 | 实际用户需求和成熟度优先；标准证据、评价器成熟度和工作量满足首发选择原则 |
| 暂不承诺、继续评审 | 通风机、鼓风机、潜水电泵、热处理、热泵和冷水机、热泵热水机、风管送风空调、单元式空调、多联式空调 | 继续补齐业务证据、标准复核和 Profile 级风险判断 |
| 明确放到 V1 之后 | 电动机、永磁电机、高压电机、空压机、工业锅炉 | 本次不纳入 Windows V1，后续单独规划 |
| 实际用户需求 | 变压器和离心泵最成熟，优先它们 | 产品负责人已确认的定性需求判断 |
| 商业价值 | 优先变压器和离心泵，其他后面补 | 产品负责人已确认的首发价值排序 |

### 5.1 当时的公共类型到内部 Profile 映射解释（历史）

`centrifugal_pump`（离心泵）对应 `pump_water` 和 `pump_chemical` 两个内部 Profile。2026-09-23 按 Phase 1 已完成证据的最小解释处理：`pump_water` 标记 `IN_V1`；`pump_chemical` 标记 `UNDER_REVIEW`，不因公共类型“离心泵”四个字自动获得同等首发资格。Windows V1 UI 必须按 Profile 显示状态，不能把整个 `centrifugal_pump` 直接显示成无条件 `SUPPORTED`。

**2026-10-02 决定已明确写出 `pump_chemical` 属于 Windows V1 范围**，即上段所述的“后续产品决策”已经发生；该 Profile 的 `scope_status` 由 `UNDER_REVIEW` 变更为 `IN_V1`。

## 6. 用户需求与商业价值证据状态

需求和商业价值是产品负责人的定性决策证据；本文件没有把它夸大为订单、收入或市场规模的量化分析。

| dimension | evidence status | evidence / source | effect on scope |
|---|---|---|---|
| 实际用户需求 | `CONFIRMED_BY_PRODUCT_DECISION` | 王玮（总经理）2026-10-02 决定以 GB 19762—2025 完整支持为 Windows V1 目标 | 支持 `pump_water` 与 `pump_chemical` 同时进入 Windows V1 范围 |
| 商业价值 | `CONFIRMED_BY_PRODUCT_DECISION` | 王玮（总经理）2026-10-02 决定本轮资源集中于参考标准完整闭环 | 支持 transformer 本轮暂缓；不代表 transformer 永久淘汰 |
| 工程就绪度 | `VERIFIED` | Phase 0/1 的真实测试、标准资源、风险分级、Profile 注册与样板比较 | 可作为候选排序依据，但不能替代产品决策，也不能替代 Stage D 验收 |
| 产品决策负责人 | `CONFIRMED` | 王玮，总经理；现行决策日期 2026-10-02；风险接受人同为王玮 | 范围变化仍须新的产品决策或正式验收证据 |

因此，第 4 节的 `IN_V1` / `POST_V1` 映射是**现行产品决策**；任何扩大范围或把 `support_status` 提升为 `SUPPORTED` 的变化，仍须新的产品决策或 Stage D 独立验收证据。

## 7. Phase 1 Scope Freeze Package

### 7.1 冻结类型与决策状态

本节记录 Windows V1 的产品决策边界和 Profile 级映射。Solution/Product Review 已通过并满足 Phase 1 Exit Gate；这不授权自动进入 Phase 2，仍须用户明确授权。

```text
scope_freeze_status: PRODUCT_SCOPE_CLEANUP_2026-10-02
scope_freeze_kind: PRODUCT_DECISION_RECORDED_PROFILE_BOUNDARY
phase_1_review_status: SOLUTION_PRODUCT_REVIEW_RESOLVED
commercial_approval: APPROVED_BY_PRODUCT_OWNER
product_decision_owner: 王玮（总经理）
decision_date: 2026-10-02
supersedes_decision: USER_PROVIDED_PRODUCT_DECISION_2026-09-23
risk_acceptor: 王玮（总经理）
automatic_scope_expansion: DISABLED
```

| Scope 状态 | 本次冻结的 Profile | Windows V1 UI 语义 |
|---|---|---|
| `IN_V1`（产品已决定） | `pump_water`、`pump_chemical` | 两者都属于 Windows V1 正式范围；UI 必须按 Profile 显示标准、版本、当前 Support Status 与标准开发成熟度。`pump_chemical` 当前仍为 `NOT_IN_RELEASE_SCOPE`，不得显示为已支持 |
| `UNDER_REVIEW` | `fan`、`blower`、`submersible`、`heat_treatment`、`heat_pump_chiller`、`heat_pump_water_heater`、`duct_ac`、`unitary_ac`、`multi_split_ac` | 不显示为已支持；显示需要复核/评审中 |
| `POST_V1` | `transformer`、`motor_lv`、`motor_hv`、`motor_pmsm`、`compressor`、`boiler` | 当前版本未支持；`transformer` 资产保留、本轮不继续开发 |

这 17 个 Profile 的范围状态是本次产品范围收口的冻结输入。任何把 `UNDER_REVIEW` 或 `POST_V1` 改为 `IN_V1`、或把 `support_status` 提升为 `SUPPORTED` 的请求，都必须形成新的产品决策记录或通过 Stage D 独立验收；不得由 Agent 或 evaluator 成熟度自行扩大。

### 7.2 产品决策与商业价值记录

| 决策维度 | 当前证据 | 当前状态 | 对冻结 Scope 的影响 | 需要谁补证 |
|---|---|---|---|---|
| 实际用户需求 | 王玮（总经理）2026-10-02 决定以 GB 19762—2025 完整支持为 Windows V1 目标 | `CONFIRMED_BY_PRODUCT_DECISION` | 支持 `pump_water` 与 `pump_chemical` 同时进入 Windows V1 正式范围 | 王玮/总经理 |
| 商业价值 | 王玮（总经理）2026-10-02 决定本轮资源集中于参考标准完整闭环 | `CONFIRMED_BY_PRODUCT_DECISION` | 支持 `transformer` 本轮暂缓并保留资产；其他 Profile 仍按 `UNDER_REVIEW` 或 `POST_V1` 执行 | 王玮/总经理 |
| 标准重要性 | 各 Profile 的标准包和来源质量登记在本表上方 | `PARTIALLY_VERIFIED` | 可作为工程排序依据，不能替代客户价值 | 技术/标准负责人 |
| evaluator 成熟度 | Phase 0 测试和 ASSET_AUDIT；Legacy Regression 有已知失败 | `VERIFIED_AS_ENGINEERING_EVIDENCE` | 只决定候选工作量，不决定业务首发 | 技术负责人 |
| P0 风险 | `QA_BACKLOG.md` 中登记，Phase 1 已做证据复核 | `OPEN / REVIEWED` | 未关闭风险不得被描述为已发布能力 | 技术/产品共同确认 |

产品决策记录已填写 decision_owner、decision_date、各 Scope 状态的接受/拒绝理由、需求来源、商业价值判断、风险接受人和自动扩展规则。本次范围收口由产品负责人于 2026-10-02 作出并取代 2026-09-23 映射；Agent 不得自行扩大范围或提升 `support_status`。

### 7.3 Review result and phase boundary

Windows V1 Profile 范围决策已由 2026-10-02 产品决定收口；Phase 1 的 Solution/Product Review 结论（P1-SR01=PASS）继续有效，Phase 1 Exit Gate 仍为已满足。当前状态为 `PHASE_1_PASS`，下一状态为 `PHASE_2_READY`；Phase 2 不会自动开始，须取得用户明确授权。本次范围收口不构成 Phase 2 启动授权。

## 8. Python Windows V1 运行环境冻结

| 项目 | 冻结值/状态 | 说明 |
|---|---|---|
| Windows V1 开发与验收 | `CPython 3.12.x x64` | 冻结 major/minor 和 64-bit；patch 由可重复构建环境另行 pin |
| Phase 0 基线 | `Python 3.13.3` | 保留为历史/基线证据，不覆盖 V1 验收环境 |
| 当前 3.12 复验 | `REVALIDATED` | CPython 3.12.14 x64；项目 `.venv\Scripts\python.exe` 由 uv 管理运行时建立；887 项回归和 Phase 1 合同/静态门禁已重跑 |
| package metadata | `requires-python >=3.12,<3.13` | 用项目元数据执行冻结；见 `pyproject.toml` |
| 禁止推断 | 不把 3.13 通过数字转写成 3.12 通过 | 版本差异必须保留在验证记录中 |

本次复验使用的可重复入口（项目根目录）：

```powershell
$env:UV_CACHE_DIR = 'G:\Python Project\EquipEffi\_codex\uv-cache'
$env:UV_PYTHON_INSTALL_DIR = 'G:\Python Project\EquipEffi\_codex\python'
uv python install 3.12.14 --install-dir $env:UV_PYTHON_INSTALL_DIR
uv venv --python 3.12.14 .venv
uv pip install --python .venv\Scripts\python.exe -e '.[tools,test]' 'jsonschema>=4.23,<5'
.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py'
```

Windows `py` 启动器不是本次门禁入口；验收统一使用项目 `.venv\Scripts\python.exe`，避免把系统解释器选择和项目运行时混在一起。

## 9. 版本字段冻结与 Scope 状态汇总

结果和 Golden Case 的版本字段按以下职责分离，不再新增含义模糊的全局 `algorithm_version`：

| 字段 | 冻结语义 |
|---|---|
| `app_version` | 应用/构建发行版本，不单独证明业务结果相同 |
| `business_spec_version` | 业务对象、状态和业务流程语义版本 |
| `catalog_data_version` | Canonical 标准事实内容版本 |
| `standard_pack_id` | 标准包稳定身份 |
| `standard_pack_version` | 标准包结构/发布修订；`pump_water` 当前候选为 `v1` |
| `standard_pack_hash` | 实际加载标准包字节指纹 |
| `ruleset_version` | 路由、边界、公式调用、比较方向和问题码规则版本 |
| `result_contract_version` | 对外结果字段和语义版本 |
| `schema_version` | 输入、Canonical、Profile、Import 或 Golden Schema 版本 |
| `formula_id` / `formula_revision` | 公式稳定身份及表达/精度/修约修订 |

`pump_water` 首批 Golden Case 使用 `business_spec_version=0.1`、`standard_pack_version=v1`、`catalog_data_version=2026.08.23`、`ruleset_version=pump_water-rules-0.1`；这些值可被 Solution Review 以新版本 supersede，不得原地改写已批准案例。

### 9.1 `IN_V1`

2026-10-02 产品决策将 Windows V1 正式产品目标统一为“完整支持 GB 19762—2025 离心泵标准”。因此 Profile 级 `IN_V1` 为 **`pump_water` 与 `pump_chemical`** 两者：

- `pump_water` 已完成 Phase 1 纵向样板证据，标准开发成熟度为 `SUPPORTED`，`support_status = SUPPORTED`；
- `pump_chemical` 已确定属于 Windows V1 范围，但标准开发成熟度仅为 `READY_FOR_IMPLEMENTATION`，8 条候选 Golden 未获 V1 批准、Stage D 未验收，因此**当前** `support_status = NOT_IN_RELEASE_SCOPE`。

`transformer` 在本轮由 `IN_V1` 调整为 `POST_V1`（暂缓，资产保留）。

### 9.2 `UNDER_REVIEW`

`fan`、`blower`、`submersible`、`heat_treatment`、`heat_pump_chiller`、`heat_pump_water_heater`、`duct_ac`、`unitary_ac`、`multi_split_ac` 暂不承诺首发，继续评审。

### 9.3 `POST_V1`

`transformer`、`motor_lv`、`motor_hv`、`motor_pmsm`、`compressor`、`boiler` 明确放到 V1 之后；保留资产和回归价值，但当前版本不支持。`transformer` 的代码、标准数据、测试与历史资产**不得删除或重构**。

### 9.4 Public UI 规则

motor 和 centrifugal_pump 这类一对多公共类型不能直接显示为笼统的 SUPPORTED。必须按 Profile 分别展示 `scope_status`、`support_status` 与标准开发成熟度：

- `pump_water`：范围 `IN_V1`，`support_status` 由发布门禁决定（当前 `SUPPORTED`）；
- `pump_chemical`：范围 `IN_V1`，但当前 `support_status = NOT_IN_RELEASE_SCOPE`，UI 必须显示“已纳入 Windows V1 范围、当前版本尚未开放”的明确状态；**不得**显示为已支持，也不得因共享 GB 19762—2025 标准号而让用户看到“已支持，只是算不出来”；
- `transformer`：范围 `POST_V1`，显示“当前版本未支持”。

`REQUIRES_REVIEW` 不是支持、类别或评价状态。

## 10. 纵向样板选择

### 10.1 候选比较（1–5 分，5 为更适合）

| 维度 | pump_water | transformer | motor_lv | blower |
|---|---:|---:|---:|---:|
| 标准证据质量 | 4 | 4 | 3 | 4 |
| evaluator 成熟度 | 4 | 4 | 4 | 3 |
| Legacy Tests | 4 | 4 | 5 | 3 |
| P0 数量/风险可控性 | 4 | 4 | 2 | 2 |
| 数据结构代表性 | 5 | 4 | 4 | 5 |
| 查表复杂度 | 4 | 5 | 5 | 5 |
| 计算复杂度 | 4 | 4 | 4 | 5 |
| 单位处理 | 4 | 3 | 3 | 4 |
| 边界验证价值 | 5 | 5 | 4 | 4 |
| 插值/禁止外推 | 3 | 2 | 3 | 4 |
| 淘汰可测试性 | 4 | 4 | 3 | 5 |
| 工作量可控性 | 4 | 3 | 3 | 2 |
| **合计** | **49** | **46** | **43** | **46** |

### 10.2 VERTICAL_SLICE

```text
chosen_profile: pump_water
alternatives: transformer, motor_lv, blower
why_chosen:
  - GB 19762-2025 资源包含公式、比转速、流量分档、来源页和清水/化工边界。
  - WaterPumpEvaluator 已覆盖派生计算、单位换算、缺失参数、边界和禁止默认类别映射。
  - 当前有泵相关评价、来源页和 V4 校验资产，可升级为 Golden Candidate。
  - 风险和工作量低于 blower；不继承 motor 当前 V4 失败作为样板阻塞。
known_risks:
  - Canonical Schema 尚未冻结，pump.json 仍是历史结构。
  - `pump_water` 与 `pump_chemical` 共用标准文件，公共 `centrifugal_pump` 的 profile 展示语义需要冻结。
  - 淘汰目录是受控子集，非全文；不能把未命中解释为未淘汰。
must_prove:
  - 正常查表、公式、单位、范围边界、缺失参数和不允许外推。
  - Canonical JSON → catalog.sqlite 的重建和版本引用。
  - Product/Profile Schema 与 Import Contract 的分离。
  - Legacy Result 与 Approved Golden Case 的 parity/intentional change。
  - Workspace 保存、Finalize、不可变 Record、重新打开和复现。
```

## 11. Golden Candidate 盘点

| candidate_id | profile | source | category | disposition |
|---|---|---|---|---|
| GC-PUMP-001 | pump_water | `test_evaluation_engine.py`、`test_pump_source_pages.py` | 正常清水泵公式与三级比较 | HIGH_VALUE / GOOD_CANDIDATE |
| GC-PUMP-002 | pump_water | `pump.py` 边界分支与相关回归 | 流量闭开区间、重叠和越界 | GOOD_CANDIDATE |
| GC-PUMP-003 | pump_water | `test_evaluation_engine.py` | 缺少泵效率仍保留计算值和标准阈值 | HIGH_VALUE |
| GC-PUMP-004 | pump_water | `pump.py` | 未知类别不得默认成单级单吸 | NEEDS_STANDARD_REVIEW |
| GC-TRANS-001 | transformer | `test_evaluation_engine.py` | 缺一项/两项损耗的结果和追溯 | GOOD_CANDIDATE |
| GC-MOTOR-001 | motor_lv | `test_v4_reader.py`、`test_v4_writer.py` | 7.5 kW、4 极、1480 rpm、98% 的 1 级结果 | BLOCKED_BY_P0 |
| GC-PMSM-001 | motor_pmsm | PMSM 29 表复核资产 | 55 kW、12 极、等级单元为“—” | HIGH_VALUE / NEEDS_STANDARD_REVIEW |
| GC-BLOWER-001 | blower | `test_evaluation_engine.py`、blower source tests | 缺出口压力/温度仍保留可用轨迹 | BLOCKED_BY_P0 |
| GC-HVAC-001 | HVAC profiles | `test_hvac_boundary_audit.py` | 开闭区间、重叠和缺口 | NEEDS_STANDARD_REVIEW |
| GC-HT-001 | heat_treatment | `test_v4_validation.py` | 燃料能源与电耗字段互斥 | LEGACY_ONLY → review |
