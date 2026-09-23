# Windows V1 Scope（Phase 1 Review Package）

**状态：** `READY_FOR_SOL_REVIEW`；产品负责人已作出 Windows V1 范围决策，但仍需 Solution/Product Review，不能视为 Phase 1 PASS，也不能自动启动 Phase 2。
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

| public type | profile_id | standard / pack | current evaluator | legacy tests | known P0 | known P1 | data quality | source quality | canonical readiness | golden candidates | release surface | scope status |
|---|---|---|---|---:|---|---|---|---|---|---:|---|---|
| transformer | transformer | GB 20052-2024 / `gb20052_2024_v1` | TransformerEvaluator | 14 | 0 confirmed | shared architecture | 546 rows | MEDIUM | REVIEW | 2 | V1_RUNTIME | IN_V1 |
| motor | motor_lv | GB 18613-2020 / `gb18613_2020_v1` | MotorEvaluator | 22 shared | V4 P0 candidate | shared architecture | 42 rows | MEDIUM | REVIEW | 2 | V1_RUNTIME | POST_V1 |
| motor | motor_hv | GB 30254-2024 / `gb30254_2024_v1` | MotorEvaluator | 22 shared | 0 confirmed | shared architecture | tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | POST_V1 |
| motor | motor_pmsm | GB 30253-2024 / `gb30253_2024_pdf_verified_v1` | PmsmEvaluator | 22 shared | 0 confirmed | provenance/contract | 29 tables | HIGH | REVIEW | 1 | V1_RUNTIME | POST_V1 |
| compressor | compressor | GB 19153-2019 / `gb19153_2019_v1` | CompressorEvaluator | 10 | 0 confirmed | shared architecture | 2469 rows | MEDIUM-HIGH | REVIEW | 1 | V1_RUNTIME | POST_V1 |
| centrifugal_pump | pump_water | GB 19762-2025 / `gb19762_2025_water_v1` | WaterPumpEvaluator | 13 | 0 confirmed | shared architecture | formula + CI | MEDIUM-HIGH | PHASE1_CANDIDATE | 4 | V1_RUNTIME | IN_V1 |
| centrifugal_pump | pump_chemical | GB 19762-2025 / `gb19762_2025_chemical_v1` | ChemicalPumpEvaluator | 13 shared | 0 confirmed | shared architecture | formula + tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW |
| centrifugal_fan / axial_fan | fan | GB 19761-2020 / `gb19761_2020_v1` | FanEvaluator | 9 shared | 0 confirmed | boundary review | 4 tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW |
| blower | blower | GB 28381-2012 / `gb28381_2012_v1` | BlowerEvaluator | 9 | 0 confirmed | missing-input trace | 8 tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW |
| submersible_pump | submersible | GB 32030-2022 / `gb32030_2022_v1` | SubmersibleEvaluator | 11 | 0 confirmed | calculation provenance | 5 tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW |
| industrial_boiler | boiler | GB 24500-2020 / `gb24500_2020_v1` | BoilerEvaluator | 10 | 0 confirmed | input gate | 4 tables | MEDIUM | REVIEW | 1 | V1_RUNTIME | POST_V1 |
| heat_treatment | heat_treatment | GB/T 36561-2018 / `gbt36561_2018_v1` | HeatTreatmentEvaluator | 10 | 0 confirmed | input gate | coefficients + table8 | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW |
| heat_pump_chiller | heat_pump_chiller | GB 19577-2024 / `gb19577_2024_pdf_verified_v1` | HvacEvaluator | 8 | 0 confirmed | source/contract | nested 5-device pack | HIGH | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW |
| heat_pump_water_heater | heat_pump_water_heater | GB 29541-2013 / `gb29541_2013_v1` | HvacEvaluator | 8 shared | 0 confirmed | source/contract | nested HVAC pack | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW |
| duct_ac | duct_ac | GB 37479-2019 / `gb37479_2019_v1` | HvacEvaluator | 8 shared | 0 confirmed | source/contract | nested HVAC pack | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW |
| unitary_ac | unitary_ac | GB 19576-2019 / `gb19576_2019_v1` | HvacEvaluator | 8 shared | 0 confirmed | source/contract | nested HVAC pack | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW |
| multi_split_ac | multi_split_ac | GB 21454-2021 / `gb21454_2021_v1` | HvacEvaluator | 8 shared | 0 confirmed | source/contract | nested HVAC pack | MEDIUM | REVIEW | 1 | V1_RUNTIME | UNDER_REVIEW |

## 产品决策记录（2026-09-23）

本节记录产品负责人提供的 Windows V1 决策输入。它是产品决策证据，不伪装成量化市场研究；最终 Phase 1 状态仍须经过 Solution/Product Review。

```text
decision_owner: 王玮
decision_role: 总经理
decision_date: 2026-09-23
risk_acceptor: 王玮（总经理）
evidence_id: USER_PROVIDED_PRODUCT_DECISION_2026-09-23
evidence_type: PRODUCT_OWNER_DECISION
```

| 决策项 | 决策内容 | 记录理由 |
|---|---|---|
| Windows V1 首发支持 | 变压器、离心泵 | 实际用户需求和成熟度优先；标准证据、评价器成熟度和工作量满足首发选择原则 |
| 暂不承诺、继续评审 | 通风机、鼓风机、潜水电泵、热处理、热泵和冷水机、热泵热水机、风管送风空调、单元式空调、多联式空调 | 继续补齐业务证据、标准复核和 Profile 级风险判断 |
| 明确放到 V1 之后 | 电动机、永磁电机、高压电机、空压机、工业锅炉 | 本次不纳入 Windows V1，后续单独规划 |
| 实际用户需求 | 变压器和离心泵最成熟，优先它们 | 产品负责人已确认的定性需求判断 |
| 商业价值 | 优先变压器和离心泵，其他后面补 | 产品负责人已确认的首发价值排序 |
| 风险接受人 | 王玮，总经理 | 与产品决策负责人相同 |

### 公共设备类型到内部 Profile 的映射解释

`centrifugal_pump`（离心泵）在仓库中对应 `pump_water` 和 `pump_chemical` 两个内部 Profile。本次按 Phase 1 已完成证据的最小解释处理：

- `pump_water` 标记为 `IN_V1`，因为本阶段已完成 GB 19762-2025 清水泵映射、7 个 Golden Case 和标准来源复核；
- `pump_chemical` 标记为 `UNDER_REVIEW`，不因公共类型“离心泵”四个字自动获得同等首发资格；
- Windows V1 UI 必须按 Profile 显示状态，不能把整个 `centrifugal_pump` 直接显示成无条件 `SUPPORTED`。

如果产品负责人意图同时承诺化工泵，应在后续产品决策中明确写出 `pump_chemical`；本次不静默扩大范围。

## 用户需求与商业价值证据状态

以下状态已根据 `USER_PROVIDED_PRODUCT_DECISION_2026-09-23` 更新。需求和商业价值是产品负责人的定性决策证据；本阶段没有把它夸大为订单、收入或市场规模的量化分析。

| dimension | evidence status | evidence / source | effect on scope |
|---|---|---|---|
| 实际用户需求 | `CONFIRMED_BY_PRODUCT_DECISION` | 王玮（总经理）确认“变压器和离心泵最成熟，优先他们” | 支持将变压器和离心泵列为公共类型首发优先范围；仍按 Profile 证据执行 |
| 商业价值 | `CONFIRMED_BY_PRODUCT_DECISION` | 王玮（总经理）确认“优先变压器和离心泵，其他的后面补” | 支持首发价值排序；不代表其他 Profile 永久淘汰 |
| 工程就绪度 | `VERIFIED` | 本次 Phase 0 的真实测试、标准资源、风险分级、Profile 注册和样板比较 | 可作为候选排序依据，但不能替代产品决策 |
| 产品决策负责人 | `CONFIRMED` | 王玮，总经理；决策日期 2026-09-23；风险接受人同为王玮 | 解除产品信息阻塞；范围仍需 Solution/Product Review |

因此，以下 `IN_V1 / UNDER_REVIEW / POST_V1` 是已记录产品决策后的 Profile 级 Review Package。定性需求和商业价值已由产品负责人确认；Solution/Product Review 仍可要求补充量化证据，但 Agent 不得自行扩大范围。

## Phase 1 Scope Freeze Package

### 冻结类型与决策状态

本节记录 Windows V1 的**产品决策边界和 Profile 级映射**，同时保留 Solution/Product Review 作为 Phase 1 出口；它不授权自动进入 Phase 2。

```text
scope_freeze_status: READY_FOR_SOL_REVIEW
scope_freeze_kind: PRODUCT_DECISION_RECORDED_PROFILE_BOUNDARY
commercial_approval: APPROVED_BY_PRODUCT_OWNER
product_decision_owner: 王玮（总经理）
decision_date: 2026-09-23
risk_acceptor: 王玮（总经理）
automatic_scope_expansion: DISABLED
```

| Scope 状态 | 本次冻结的 Profile | Windows V1 UI 语义 |
|---|---|---|
| `IN_V1`（产品已决定，待 Solution Review） | `transformer`、`pump_water` | 允许进入 V1 方案评审；必须显示标准、版本和 Support Status |
| `UNDER_REVIEW` | `pump_chemical`、`fan`、`blower`、`submersible`、`heat_treatment`、`heat_pump_chiller`、`heat_pump_water_heater`、`duct_ac`、`unitary_ac`、`multi_split_ac` | 不显示为已支持；显示需要复核/评审中 |
| `POST_V1` | `motor_lv`、`motor_hv`、`motor_pmsm`、`compressor`、`boiler` | 当前版本未支持 |

这 17 个状态是当前 Phase 1 review package 的冻结输入。任何把 `UNDER_REVIEW` 或 `POST_V1` 改为首发的请求，都必须形成新的产品决策记录；不得由 Agent 或 evaluator 成熟度自行扩大。

### 用户需求与商业价值的决策记录

| 决策维度 | 当前证据 | 当前状态 | 对冻结 Scope 的影响 | 需要谁补证 |
|---|---|---|---|---|
| 实际用户需求 | 王玮（总经理）确认变压器和离心泵最成熟，优先它们 | `CONFIRMED_BY_PRODUCT_DECISION` | 支持 `transformer` 与 `pump_water` 进入首发方案评审；不自动覆盖 `pump_chemical` | 王玮/总经理 |
| 商业价值 | 王玮（总经理）确认优先变压器和离心泵，其他后续补 | `CONFIRMED_BY_PRODUCT_DECISION` | 支持首发价值排序；其他 Profile 仍按 `UNDER_REVIEW` 或 `POST_V1` 执行 | 王玮/总经理 |
| 标准重要性 | 各 Profile 的标准包和来源质量登记在本表上方 | `PARTIALLY_VERIFIED` | 可作为工程排序依据，不能替代客户价值 | 技术/标准负责人 |
| evaluator 成熟度 | Phase 0 测试和 ASSET_AUDIT；Legacy Regression 有已知失败 | `VERIFIED_AS_ENGINEERING_EVIDENCE` | 只决定候选工作量，不决定业务首发 | 技术负责人 |
| P0 风险 | `QA_BACKLOG.md` 中登记，Phase 1 已做证据复核 | `OPEN / REVIEWED` | 未关闭风险不得被描述为已发布能力 | 技术/产品共同确认 |

产品决策记录已填写：`decision_owner`、`decision_date`、各 Scope 状态的接受/拒绝理由、需求来源、商业价值判断、风险接受人和自动扩展规则。Solution/Product Review 仍需审查这些记录与技术证据；Agent 不得代替评审结论。

### Remaining review gate

产品决策阻塞已解除，当前状态为 `READY_FOR_SOL_REVIEW`。剩余门禁是 Solution/Product Review 对业务规范、`pump_water` 标准证据、Profile 级范围映射和 QA 中 `NEEDS_MORE_EVIDENCE` 项作出评审结论；在此之前不宣布 Phase 1 PASS，也不启动 Phase 2。

## Python Windows V1 运行环境冻结

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

产品决策将变压器和离心泵列为公共类型首发优先范围。按已完成的 Phase 1 证据，Profile 级 `IN_V1` 为 `transformer`、`pump_water`；`pump_chemical` 保持 `UNDER_REVIEW`。三者都有可加载标准或明确的标准映射，但只有 `pump_water` 已完成本阶段纵向样板证据。

### `UNDER_REVIEW`

`pump_chemical`、`fan`、`blower`、`submersible`、`heat_treatment`、`heat_pump_chiller`、`heat_pump_water_heater`、`duct_ac`、`unitary_ac`、`multi_split_ac` 暂不承诺首发，继续评审。`pump_chemical` 与 `pump_water` 共用公共类型，必须按 Profile 展示，不能造成半支持。

### `POST_V1`

`motor_lv`、`motor_hv`、`motor_pmsm`、`compressor`、`boiler` 明确放到 V1 之后；保留资产和回归价值，但当前版本不支持。

### Public UI 规则

`motor` 和 `centrifugal_pump` 这类一对多公共类型不能直接显示为笼统的 `SUPPORTED`。本次按 Profile 展示：`pump_water` 可进入 V1 方案评审，`pump_chemical` 显示 `REQUIRES_REVIEW`；不能让用户看到“已支持，只是算不出来”。

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
