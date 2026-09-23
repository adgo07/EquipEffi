# `pump_water` / GB 19762-2025 样板映射 V0.1

状态：`DRAFT_FOR_SOLUTION_REVIEW`

本文件是 Phase 1 的首个 Profile 映射。它把标准包、Product/Profile 字段、输入别名、查表边界、公式、输出状态和审计证据连起来；不修改现有 evaluator，也不把当前实现自动批准为最终业务规范。

## 1. 身份与证据

| 项目 | 映射 |
|---|---|
| 公共设备类型 | `centrifugal_pump`（离心泵） |
| Profile | `pump_water` |
| 标准 | GB 19762-2025《离心泵能效限定值及能效等级》 |
| 标准包 | `gb19762_2025_water_v1` |
| 当前 Canonical 候选 | `src/equipeffi/resources/standards/pump.json` 的 `water` 节 |
| `catalog_data_version` | `2026.08.23`（manifest） |
| `standard_pack_version` | `v1`（由 pack id 后缀得到；需在版本冻结时显式确认） |
| 当前包 SHA-256 | `D1FAB8310AA5ADE7ACCCB379BD347F442D51202E0EE2EEF4CA6E34F5A2F3EA00` |
| 外部标准原文证据 | `G:/标准  规范/02_能耗限额_终端产品/用能设备/重点设备能效标准/6 7. GB 19762-2025 离心泵能效限定值及能效等级.pdf`；SHA-256 `7F515D8B9D6B4D2AB97FFA7BECB78520BA0579CFBD6D5ECA10C7E7CC77895FEC` |
| 标准实施日期 | `2026-03-01` |
| 表/来源页 | 表 1、表 3；当前包标注标准页 `9-10` |
| 当前正式运行路径 | `EvaluationFacade` → `EvaluationService` → `WaterPumpEvaluator` → `JsonStandardRepository` |
| 当前实现文件 | `src/equipeffi/domain/evaluation/evaluators/pump.py` |
| 旧测试证据 | `tests/unit/test_device_evaluator_matrix.py`；只能验证当前行为，不能单独证明标准事实 |

标准 PDF 原件不随本仓库提交；当前工作区外部证据文件及其 SHA-256 已在上表和 Golden Case `source_reference` 中固定。标准所有者或 Solution Review 仍可要求补充具名复核，不能把文件存在或指纹一致单独解释为业务批准。

## 2. 公共类型路由

`centrifugal_pump` 只在类别或用户选择明确表明为清水离心泵时路由到本 Profile。当前输入归一化支持以下别名：

| Product/Profile 值 | V4/展示别名 | 标准表类型 |
|---|---|---|
| `单级单吸` | `单级单吸清水离心泵` | `单级单吸` |
| `单级双吸` | `单级双吸清水离心泵` | `单级双吸` |
| `管道` | `管道清水离心泵` | `管道` |
| `多级` | `多级清水离心泵` | `多级` |
| `轻型多级立式` | `轻型多级清水离心泵（立式）` | `轻型多级立式` |
| `轻型多级卧式` | `轻型多级清水离心泵（卧式）` | `轻型多级卧式` |

`其他（请备注说明）` 不能默认映射到 `单级单吸`。类别为空、化工类别、或水泵/化工泵无法区分时，必须路由为 `REQUIRES_REVIEW` 或由上层选择另一个 Profile。

## 3. Product/Profile 字段映射

| 稳定字段 | 数据类型/单位 | 必填语义 | 当前别名/来源 | 规则责任 |
|---|---|---|---|---|
| `category` | enum / `unitless` | 必填；必须是标准列出的六类之一 | `category`、设备类别、V4 泵型 | Profile + Ruleset |
| `suction` | enum / `unitless` | 可选；若填写必须与类别的单/双吸一致 | `suction`、单双吸；`单吸`/`双吸` | Profile 一致性规则 |
| `flow_m3h` | decimal / `m3/h` | 必填且大于 0；必须是标准/样机最高效率点流量 `Q_BEP` | `flow_m3h`、流量、`flow` | Product/Profile + Ruleset |
| `head_m` | decimal / `m` | 必填且大于 0；必须与该最高效率点和同一泵配置对应 | `head_m`、扬程、`head` | Product/Profile + Ruleset |
| `rated_speed_rpm` | decimal / `rpm` | 必填且大于 0；必须是同一标准规定点/试验条件的转速 | `rated_speed_rpm`、额定转速、`speed` | Product/Profile + Ruleset |
| `rated_power_kw` | decimal / `kW` | 可选；本 Profile 公式不使用 | `rated_power_kw`、额定功率、`power` | 仅输入契约 |
| `stages` | positive integer / `stage` | 多级必填；单级按显式 1 进入 Golden | `stages`、级数 | Ruleset；默认行为待评审 |
| `pump_efficiency` | decimal / `%` | 等级比较必填，1–100；必须是与 `flow_m3h`、`head_m` 同一点的泵效率 | `pump_efficiency`、泵效率、`efficiency` | Ruleset |
| `as_of` | date | 评价审计必填；兼容入口的默认日期必须被显式记录 | Application 请求 | 版本/标准选择 |

`rated_power_kw` 不得被误当作水泵输出功率。评价器计算的 `输出功率_kW` 是由流量、扬程和 `9.81` 派生的审计指标，单位为 `kW`。

### 3.1 标准规定点语义（GB 19762-2025）

GB 19762-2025 的能效公式使用最高效率点（Best Efficiency Point，`BEP`）的流量、扬程和效率。因此本 Profile 的三个核心字段不是任意运行工况的观测值，而必须来自同一个标准规定点/最高效率点：

- `flow_m3h` 必须是最高效率点流量 `Q_BEP`；
- `head_m` 必须是同一 `Q_BEP`、同一泵型/级数配置对应的扬程 `H_BEP`；
- `pump_efficiency` 必须是同一 `Q_BEP` 的泵效率 `η_BEP`；
- `rated_speed_rpm` 必须与上述点和标准试验条件相匹配。

如果来源只给出任意运行点、额定点但不能证明其为标准规定点，或者流量、扬程和效率来自不同工况，则不能直接生成 `SUPPORTED` Golden Case；应返回 `REQUIRES_REVIEW` 或 `INSUFFICIENT_DATA`，并保留缺失的规定点证据。Golden JSON 通过 `input_basis=STANDARD_BEP`、`measurement_point=BEP` 显式声明该前提。

### 3.2 单位与数值语义

- `flow_m3h` 进入标准比转速公式前转换为 `m3/s`；双吸泵取有效流量的一半。
- `head_m` 对多级泵转换为单级扬程 `H / stages`；单级泵不除以级数。
- `rated_speed_rpm` 按 `r/min` 使用。
- `pump_efficiency` 是百分数数值，例如 `80` 表示 `80%`，不是 `0.80`。
- Golden Case 和跨端结果中的十进制值使用字符串；显示层可按 locale 格式化，但不得改变数值含义。

## 4. 标准公式和派生量

### 4.1 中间量

```text
Q_effective = Q / 2                 （双吸）
Q_effective = Q                     （其他类别）
H_stage = H / stages                （多级）
H_stage = H                         （单级）
Q_s = Q_effective / 3600            （m³/s）
ns = 3.65 × n × sqrt(Q_s) / H_stage^0.75
P_out = 9.81 × Q × H / 3600         （kW）
```

### 4.2 清水泵效率阈值

对 `pump_water`，类别为单级时使用单级系数，类别包含多级时使用多级系数：

```text
η_base = a(ln ns)² + b(ln QBEP)²
       + c(ln ns)(ln QBEP)
       + d ln ns + e ln QBEP
η_level_i = η_base - C_i
```

其中 `QBEP` 的单位是 `m3/h`，`C1/C2/C3` 来自表 3 的唯一命中行。当前包系数为：

| 泵型 | a | b | c | d | e |
|---|---:|---:|---:|---:|---:|
| 单级 | -8.44 | -0.48 | 0.09 | 84.63 | 8.5 |
| 多级 | -6.93 | -0.19 | -0.4 | 72.67 | 8.73 |

实际效率按 `η_actual >= η_level_i` 比较。达到 1 级即输出 1 级；否则依次判定 2 级、3 级；没有达到 3 级时应由结果契约给出明确的未达标语义，不能改写为“缺数据”。

当前实现对限值展示保留 6 位小数，对中间值和 trace 保留更高精度；最终契约的修约规则仍需由 Ruleset V0.x 在 Solution Review 冻结。

## 5. 表 3 查表与边界

查表键是 `标准泵型 + flow_m3h`。必须先按类别精确筛选，再按流量区间判断；不能跨类别取最近行，不能在未获标准授权时插值或外推。

| `data_id` | 标准泵型 | 流量范围 (`m3/h`) | C1/C2/C3 | 来源 |
|---|---|---|---|---|
| `GB19762-T3-01` | 单级单吸 | `5 ≤ Q ≤ 300` | 161.33 / 163.33 / 168.33 | GB 19762-2025 表 3，9–10 |
| `GB19762-T3-02` | 单级单吸 | `300 < Q ≤ 10000` | 162.33 / 163.33 / 168.33 | 同上 |
| `GB19762-T3-03` | 单级双吸 | `50 ≤ Q ≤ 600` | 161.33 / 163.33 / 168.33 | 同上 |
| `GB19762-T3-04` | 单级双吸 | `600 < Q ≤ 20000` | 162.33 / 163.33 / 168.33 | 同上 |
| `GB19762-T3-05` | 管道 | `5 ≤ Q ≤ 300` | 163.33 / 165.33 / 171.33 | 同上 |
| `GB19762-T3-06` | 管道 | `300 < Q ≤ 3000` | 164.33 / 165.33 / 171.33 | 同上 |
| `GB19762-T3-07` | 多级 | `5 ≤ Q ≤ 100` | 139.33 / 142.33 / 150.33 | 同上 |
| `GB19762-T3-08` | 多级 | `100 < Q ≤ 3000` | 140.33 / 144.33 / 150.33 | 同上 |
| `GB19762-T3-09` | 轻型多级立式 | `5 ≤ Q ≤ 300` | 137.33 / 139.33 / 144.33 | 同上 |
| `GB19762-T3-10` | 轻型多级卧式 | `5 ≤ Q ≤ 300` | 140.33 / 142.33 / 147.33 | 同上 |

边界验收必须至少覆盖：

- `Q=5`、`Q=300`、`Q=600` 等显式包含端点；
- `Q=300+ε`、`Q=600+ε` 等下一个区间切换；
- `Q<5`、类别对应的上限外流量等未命中；
- 同类别不能命中多个行；命中多个时返回 `REQUIRES_REVIEW`，不能随意选第一行。

## 6. 异常、缺失与不支持语义

| 场景 | 规范状态 | 必须保留的证据 |
|---|---|---|
| 泵效率缺失，但类别、流量、扬程、转速可确定 | `INSUFFICIENT_DATA` | 输出功率、比转速、C1–C3、限值、查表记录；不生成等级 |
| 流量未命中本类别区间 | `OUT_OF_STANDARD_SCOPE` | 实际效率、可计算派生量、候选 `data_id`、所有边界 |
| 类别为“其他”或未知 | `OUT_OF_STANDARD_SCOPE` 或 `REQUIRES_REVIEW` | 全部清水候选类型；不得默认单级单吸；不计算虚假的比转速 |
| 类别与 `suction` 冲突 | `REQUIRES_REVIEW` | 冲突字段、候选类型和标准来源；不得静默折半流量 |
| 多级泵缺少级数 | `INSUFFICIENT_DATA` | 流量候选、缺失 `stages`；不得按 1 级计算单级扬程 |
| 输入非正、效率格式非法或单位不明 | `INVALID_INPUT` | 原始值、字段、校验规则和问题码 |
| `pump_chemical` 输入 | 不属于本 Profile | 路由证据；不得使用清水 C 表 |

“未命中淘汰目录”不等于“证明未淘汰”。淘汰结论必须保留独立的 elimination evidence，不得由本 Profile 的能效等级推导。

## 7. Ruleset 规则 ID 候选

这些 ID 是 Phase 1 的稳定命名候选，未授权修改当前业务实现：

| 规则 ID | 语义 |
|---|---|
| `PUMP-WATER-ROUTE-001` | 公共离心泵到清水 Profile 的路由 |
| `PUMP-WATER-CATEGORY-001` | 类别必须命中表 3 标准类型，未知类别无默认映射 |
| `PUMP-WATER-UNIT-001` | 流量、扬程、转速和效率单位/数值范围 |
| `PUMP-WATER-BOUNDARY-001` | 表 3 区间端点的开闭规则 |
| `PUMP-WATER-NO-INTERPOLATION-001` | 表 3 C 值不插值、不外推 |
| `PUMP-WATER-NS-001` | 双吸流量、单级扬程和比转速计算 |
| `PUMP-WATER-THRESHOLD-001` | 公式(1)–(3)和 C1–C3 阈值 |
| `PUMP-WATER-MISSING-001` | 缺少效率时保留合法中间量但不生成等级 |
| `PUMP-WATER-CONSISTENCY-001` | 类别与单双吸冲突需复核 |
| `PUMP-WATER-STAGES-001` | 多级泵级数是单级扬程和比转速的必要条件 |

## 8. 当前实现差异与待评审项

- `metadata.py`、`device_specs.py`、`input_normalization.py` 和 `pump.py` 目前各自承载部分 Profile、字段、别名和规则信息；Phase 1 只完成职责映射，不迁移或删除。
- 当前包来自 `pump.json`，标准包的独立 `standard_pack_version` 尚未在 manifest 中以单独字段表达；本文件暂用 `v1` 作为可追溯候选，需在 G06 冻结。
- 单级泵省略 `stages` 的兼容行为在现有示例中等价于 1 级；正式 Product/Profile 契约是否允许隐式 1 级必须由 Solution Review 决定。Golden Case 全部显式填写 `stages: 1`，避免把兼容行为当成标准事实。
- 当前 Legacy Regression 中的 V4 电机读写失败不属于本 Profile，本阶段不修改、不隐藏。

## 9. 样板完成条件

`pump_water` 映射只有在以下证据被 Solution Review 接受后才可作为下一阶段输入：

1. Canonical 候选包的表 3 数据、页码和哈希可复现；
2. 所有字段单位、别名、类别路由和缺失语义与 Product/Profile Schema 一致；
3. Golden Case 覆盖正常、边界、缺失效率、未知类别和不外推；
4. 当前实现与标准不一致的地方都有 QA ID 或明确的 `NEEDS_MORE_EVIDENCE`；
5. V1 Scope 和版本字段获得产品/方案评审确认。
