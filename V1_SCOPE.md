# Windows V1 Scope（Phase 1 冻结候选）

**状态：** `BLOCKED`；工程候选边界已冻结，但 Windows V1 尚未获得产品/商业批准，不得视为 Phase 1 PASS、`READY_FOR_SOL_REVIEW` 或商业承诺。
**原则：** 不默认 15 类公共设备或 17 个内部 Profile 全部首发；不允许“半支持”。

## Support Status 草案

正式命名留给 Phase 1，当前先统一使用：

```text
SUPPORTED
NOT_IN_RELEASE_SCOPE
UNSUPPORTED_STANDARD
OUT_OF_STANDARD_SCOPE
INSUFFICIENT_DATA
INVALID_INPUT
NOT_APPLICABLE
REQUIRES_REVIEW
```

`POST_V1` 或 `UNDER_REVIEW` 的 Profile 不得在 Windows V1 UI 中显示为已支持；应明确显示“当前版本未支持”或“需要复核”。

## 15 公共类型与 17 Profile

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

## 17 Profile 注册表

`legacy_tests` 是 Phase 0 对命中测试模块的粗盘点，不等于 Approved Golden Case 数量；`known_P0` 只表示已登记风险，不表示已经确认标准错误。

| public type | profile_id | standard / pack | current evaluator | legacy tests | known P0 | known P1 | data quality | source quality | canonical readiness | golden candidates | release surface | draft scope |
|---|---|---|---|---:|---|---|---|---|---|---:|---|---|
| transformer | transformer | GB 20052-2024 / `gb20052_2024_v1` | TransformerEvaluator | 14 | 0 confirmed | shared architecture | 546 rows | MEDIUM | REVIEW | 2 | V1_RUNTIME | IN_V1 |
| motor | motor_lv | GB 18613-2020 / `gb18613_2020_v1` | MotorEvaluator | 22 shared | V4 P0 candidate | shared architecture | 42 rows | MEDIUM | REVIEW | 2 | V1_RUNTIME | UNDER_REVIEW |
| motor | motor_hv | GB 30254-2024 / `gb30254_2024_v1` | MotorEvaluator | 22 shared | 0 confirmed | shared architecture | tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW |
| motor | motor_pmsm | GB 30253-2024 / `gb30253_2024_pdf_verified_v1` | PmsmEvaluator | 22 shared | 0 confirmed | provenance/contract | 29 tables | HIGH | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW |
| compressor | compressor | GB 19153-2019 / `gb19153_2019_v1` | CompressorEvaluator | 10 | 0 confirmed | shared architecture | 2469 rows | MEDIUM-HIGH | REVIEW | 1 | V1_RUNTIME | IN_V1 |
| centrifugal_pump | pump_water | GB 19762-2025 / `gb19762_2025_water_v1` | WaterPumpEvaluator | 13 | 0 confirmed | shared architecture | formula + CI | MEDIUM-HIGH | PHASE1_CANDIDATE | 4 | V1_RUNTIME | IN_V1 |
| centrifugal_pump | pump_chemical | GB 19762-2025 / `gb19762_2025_chemical_v1` | ChemicalPumpEvaluator | 13 shared | 0 confirmed | shared architecture | formula + tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | POST_V1 |
| centrifugal_fan / axial_fan | fan | GB 19761-2020 / `gb19761_2020_v1` | FanEvaluator | 9 shared | 0 confirmed | boundary review | 4 tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | POST_V1 |
| blower | blower | GB 28381-2012 / `gb28381_2012_v1` | BlowerEvaluator | 9 | 0 confirmed | missing-input trace | 8 tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | POST_V1 |
| submersible_pump | submersible | GB 32030-2022 / `gb32030_2022_v1` | SubmersibleEvaluator | 11 | 0 confirmed | calculation provenance | 5 tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | POST_V1 |
| industrial_boiler | boiler | GB 24500-2020 / `gb24500_2020_v1` | BoilerEvaluator | 10 | 0 confirmed | input gate | 4 tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | POST_V1 |
| heat_treatment | heat_treatment | GB/T 36561-2018 / `gbt36561_2018_v1` | HeatTreatmentEvaluator | 10 | 0 confirmed | input gate | coefficients + table8 | MEDIUM | REVIEW | 1 | V1_RUNTIME | POST_V1 |
| heat_pump_chiller | heat_pump_chiller | GB 19577-2024 / `gb19577_2024_pdf_verified_v1` | HvacEvaluator | 8 | 0 confirmed | source/contract | nested 5-device pack | HIGH | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW |
| heat_pump_water_heater | heat_pump_water_heater | GB 29541-2013 / `gb29541_2013_v1` | HvacEvaluator | 8 shared | 0 confirmed | source/contract | nested HVAC pack | MEDIUM | REVIEW | 1 | V1_RUNTIME | POST_V1 |
| duct_ac | duct_ac | GB 37479-2019 / `gb37479_2019_v1` | HvacEvaluator | 8 shared | 0 confirmed | source/contract | nested HVAC pack | MEDIUM | REVIEW | 1 | V1_RUNTIME | POST_V1 |
| unitary_ac | unitary_ac | GB 19576-2019 / `gb19576_2019_v1` | HvacEvaluator | 8 shared | 0 confirmed | source/contract | nested HVAC pack | MEDIUM | REVIEW | 1 | V1_RUNTIME | POST_V1 |
| multi_split_ac | multi_split_ac | GB 21454-2021 / `gb21454_2021_v1` | HvacEvaluator | 8 shared | 0 confirmed | source/contract | nested HVAC pack | MEDIUM | REVIEW | 1 | V1_RUNTIME | POST_V1 |

## Draft Scope 解释

## 用户需求与商业价值证据状态

以下判断是 Phase 0 的证据状态，不把工程就绪度误写成产品承诺。当前仓库未发现用户访谈、已确认订单/项目清单、使用遥测、收入贡献分析或产品负责人签字的 V1 需求决策，因此需求和商业价值不能在本阶段被假定为“已确认”。

| dimension | evidence status | evidence / source | effect on scope |
|---|---|---|---|
| 实际用户需求 | `UNKNOWN / NEEDS_EVIDENCE` | 当前仓库没有可引用的用户访谈、客户需求单、订单/项目优先级或使用遥测记录 | 不因工程可行而扩展为全量 17 Profile；Phase 1 必须补充需求证据 |
| 商业价值 | `UNKNOWN / NEEDS_EVIDENCE` | 当前仓库没有收入贡献、客户覆盖、交付频率、市场优先级或产品负责人确认记录 | `IN_V1` 仍是工程草案，不构成商业承诺 |
| 工程就绪度 | `VERIFIED` | 本次 Phase 0 的真实测试、标准资源、风险分级、Profile 注册和样板比较 | 可作为候选排序依据，但不能替代产品决策 |
| 产品决策负责人 | `REQUIRED_INPUT` | 当前权威治理文件未指定姓名、角色和决策日期 | 解除阻塞前必须登记具名负责人、证据来源、决定日期和接受/拒绝理由 |

因此，以下 `IN_V1 / UNDER_REVIEW / POST_V1` 是“工程与风险草案”。Phase 1 只允许在指定产品决策负责人补齐实际需求和商业价值证据后，冻结最终业务 Scope；在此之前不得把 `IN_V1` 描述为已获商业批准。

## Phase 1 Scope Freeze Package

### 冻结类型与决策状态

本节冻结的是 Windows V1 的**评审候选边界**，目的是禁止在 Solution/Product Review 前继续扩大范围；它不是产品负责人签字，也不把工程可用性自动转换为商业承诺。

```text
scope_freeze_status: BLOCKED
scope_freeze_kind: ENGINEERING_CANDIDATE_BOUNDARY
commercial_approval: PENDING_PRODUCT_DECISION
product_decision_owner: REQUIRED_INPUT
decision_date: REQUIRED_INPUT
automatic_scope_expansion: DISABLED
```

| Scope 状态 | 本次冻结的 Profile | Windows V1 UI 语义 |
|---|---|---|
| `IN_V1`（工程候选，待产品确认） | `transformer`、`compressor`、`pump_water` | 可进入 V1 候选，但必须显示标准、版本和 Support Status |
| `UNDER_REVIEW` | `motor_lv`、`motor_hv`、`motor_pmsm`、`heat_pump_chiller` | 不显示为已支持；显示需要复核/评审中 |
| `POST_V1` | `pump_chemical`、`fan`、`blower`、`submersible`、`boiler`、`heat_treatment`、`heat_pump_water_heater`、`duct_ac`、`unitary_ac`、`multi_split_ac` | 当前版本未支持 |

这 17 个状态是当前 Phase 1 review package 的冻结输入。任何把 `UNDER_REVIEW` 或 `POST_V1` 改为首发的请求，都必须由产品负责人给出实际需求、商业价值、接受风险和决定日期；不得由 Agent 或 evaluator 成熟度自行扩大。

### 用户需求与商业价值的决策缺口

| 决策维度 | 当前证据 | 当前状态 | 对冻结 Scope 的影响 | 需要谁补证 |
|---|---|---|---|---|
| 实际用户需求 | 仓库没有用户访谈、客户需求单、订单/项目优先级或使用遥测 | `UNKNOWN / NEEDS_EVIDENCE` | 不允许把 17 Profile 全量纳入 V1 | 产品负责人/业务负责人 |
| 商业价值 | 仓库没有收入贡献、客户覆盖、交付频率、市场优先级或报价证据 | `UNKNOWN / NEEDS_EVIDENCE` | `IN_V1` 只是工程优先级，不是销售承诺 | 产品负责人/业务负责人 |
| 标准重要性 | 各 Profile 的标准包和来源质量登记在本表上方 | `PARTIALLY_VERIFIED` | 可作为工程排序依据，不能替代客户价值 | 技术/标准负责人 |
| evaluator 成熟度 | Phase 0 测试和 ASSET_AUDIT；Legacy Regression 有已知失败 | `VERIFIED_AS_ENGINEERING_EVIDENCE` | 只决定候选工作量，不决定业务首发 | 技术负责人 |
| P0 风险 | `QA_BACKLOG.md` 中登记，Phase 1 已做证据复核 | `OPEN / REVIEWED` | 未关闭风险不得被描述为已发布能力 | 技术/产品共同确认 |

产品评审需要明确填写：`decision_owner`、`decision_date`、每个 Scope 状态的接受/拒绝理由、需求来源、商业价值证据、风险接受人和是否允许调整本候选边界。在这些字段补齐前，最终状态保持 `BLOCKED`；Agent 不得代填或推断产品批准。

### Acceptance blocker

当前 `IN_V1 / UNDER_REVIEW / POST_V1` 仍是工程候选，不是产品决策。缺少具名负责人、决定日期、实际用户需求证据、商业价值证据和明确接受/拒绝理由，因此本文件不能声明 Windows V1 Scope 已冻结，也不能解除 Phase 1 阻塞。

## Python Windows V1 运行环境冻结

| 项目 | 冻结值/状态 | 说明 |
|---|---|---|
| Windows V1 开发与验收 | `CPython 3.12.x x64` | 冻结 major/minor 和 64-bit；patch 由可重复构建环境另行 pin |
| Phase 0 基线 | `Python 3.13.3` | 保留为历史/基线证据，不覆盖 V1 验收环境 |
| 当前 3.12 复验 | `NOT_REVALIDATED / NEEDS_ENVIRONMENT` | 本阶段不安装或切换解释器；Phase 2 前必须建立可重复环境并重跑门禁 |
| package metadata | `requires-python >=3.12,<3.13` | 用项目元数据执行冻结；见 `pyproject.toml` |
| 禁止推断 | 不把 3.13 通过数字转写成 3.12 通过 | 版本差异必须保留在验证记录中 |

## 版本字段冻结

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

### `IN_V1`

Phase 0 工程草案只将 `transformer`、`compressor`、`pump_water` 放入首发候选。它们都有可加载标准、当前 evaluator、较完整的回归资产，且不受当前 V4 电机失败直接阻断。

### `UNDER_REVIEW`

三个 motor Profile 和 `heat_pump_chiller` 暂不承诺首发。电机公共类型同时路由 3 个内部 Profile，若只支持其中一个会造成半支持；同时当前 V4 电机结果路径有 3 个失败断言。必须先完成 Profile 级 Golden/Scope 决策。

### `POST_V1`

其余 Profile 保留资产和回归价值，但 Phase 0 没有足够的业务需求、Canonical 复核和首发工作量证据将其承诺为 V1。

### Public UI 规则

`motor` 和 `centrifugal_pump` 这类一对多公共类型不能直接显示为笼统的 `SUPPORTED`。Phase 1 必须决定：按 profile 展示，或在公共类型层显示 `REQUIRES_REVIEW`；不能让用户看到“已支持，只是算不出来”。

## 纵向样板选择

### 候选比较（1–5 分，5 为更适合）

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

### VERTICAL_SLICE

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

## Golden Candidate 盘点

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
