# `pump_water` / GB 19762-2025 样板映射 V0.1

状态：`DRAFT_FOR_INDEPENDENT_REVIEW`。数值、输入和结果以 [`PUMP_NUMERIC_AND_DECISION_CONTRACT_V2`](../../../docs/PUMP_NUMERIC_AND_DECISION_CONTRACT_V2.md) 为当前契约；本文件下文早期映射记录中与 V2 冲突的精度/状态描述已由 V2 取代。

本文件是 Phase 1 的首个 Profile 映射。它把标准包、Product/Profile 字段、输入别名、查表边界、公式、输出状态和审计证据连起来。本轮已按用户授权的 V2 契约对 pump evaluator 作最小修改；代码通过针对性测试仍不等于 Golden 或产品批准。

## 1. 身份与证据

| 项目 | 映射 |
|---|---|
| 公共设备类型 | `centrifugal_pump`（离心泵） |
| Profile | `pump_water` |
| 标准 | GB 19762-2025《离心泵能效限定值及能效等级》 |
| 标准包 | `gb19762_2025_water_v1` |
| 当前 Canonical 候选 | `src/equipeffi/resources/standards/pump.json` 的 `water` 节 |
| `catalog_data_version` | `2026.09.26-t3-08-c2-142.33-v1`（manifest） |
| `standard_pack_version` | `v1`（由 pack id 后缀得到；需在版本冻结时显式确认） |
| 当前包 SHA-256（仓库文本 CRLF→LF 规范） | `5D91F01B1C5F26DC4F364A3156C4E974B159FA1005BD840489C0BC3465C18C0F` |
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

输入契约原字段为 `product_type`；旧 `category` 仅作兼容别名。`其他类别` 表示已确认不适用；类别缺失或未知为 `UNRESOLVED`，两者均不执行标准公式。明确为石化泵时由 profile 路由选择 `pump_chemical`。

## 3. Product/Profile 字段映射

| 稳定字段 | 数据类型/单位 | 必填语义 | 当前别名/来源 | 规则责任 |
|---|---|---|---|---|
| `product_type` | enum / `unitless` | 必填；必须是标准列出的六类之一 | `product_type`；旧 `category` 为兼容别名 | Profile + Ruleset |
| `suction` | enum / `unitless` | 必填；必须与类别的单/双吸一致 | `suction`、单双吸；`单吸`/`双吸` | Profile 一致性规则 |
| `flow_m3h` | decimal / `m3/h` | 必填且大于 0；必须是标准/样机最高效率点流量 `Q_BEP` | `flow_m3h`、流量、`flow` | Product/Profile + Ruleset |
| `head_m` | decimal / `m` | 必填且大于 0；必须与该最高效率点和同一泵配置对应 | `head_m`、扬程、`head` | Product/Profile + Ruleset |
| `rated_speed_rpm` | decimal / `rpm` | 必填且大于 0；必须是同一标准规定点/试验条件的转速 | `rated_speed_rpm`、额定转速、`speed` | Product/Profile + Ruleset |
| `rated_power_kw` | decimal / `kW` | 可选；本 Profile 公式不使用 | `rated_power_kw`、额定功率、`power` | 仅输入契约 |
| `stages` | positive integer / `stage` | 必填；单级为 1、多级大于 1；不得缺省或按类别代填 | `stages`、级数 | Ruleset |
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

- 新契约原始字段为 `QBEP`、`HBEP`、`speed`、`efficiency`；旧字段 `flow_m3h`、`head_m`、`rated_speed_rpm`、`pump_efficiency` 只作为兼容别名。
- 比转速派生量为 `Q_ns=QBEP/S/3600`、`H_ns=HBEP/stages`、`ns_raw=3.65×speed×sqrt(Q_ns)/H_ns^0.75`；S 由显式单双吸给出，N 由显式级数给出。
- 表 3 流量分档及公式(2)/(3)使用原始总流量 `QBEP`；不得用 `Q_ns` 替代。
- `efficiency` 是百分数数值，例如 `80` 表示 `80%`，不是 `0.80`。
- Golden Case 和跨端结果中的十进制值使用字符串；显示层可按 locale 格式化，但不得改变数值含义。

## 4. 标准公式和派生量

### 4.1 中间量

```text
S = 1（单吸）或 2（双吸）；N = stages
Q_ns = QBEP / S / 3600              （m³/s）
H_ns = HBEP / N                     （m）
ns_raw = 3.65 × speed × sqrt(Q_ns) / H_ns^0.75
P_out = 9.81 × QBEP × HBEP / 3600   （kW）
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

实际效率按完整内部 Decimal 阈值直接 `>=` 比较。阈值不先按显示精度舍入；不使用 epsilon。`ns_raw` 直接参与范围判断和行/分支选择；显示位数只用于展示。

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
| `GB19762-T3-08` | 多级 | `100 < Q ≤ 3000` | 140.33 / 142.33 / 150.33 | 同上 |
| `GB19762-T3-09` | 轻型多级立式 | `5 ≤ Q ≤ 300` | 137.33 / 139.33 / 144.33 | 同上 |
| `GB19762-T3-10` | 轻型多级卧式 | `5 ≤ Q ≤ 300` | 140.33 / 142.33 / 147.33 | 同上 |

### Phase 1 GB 19762-2025 统一收口补记（2026-09-27）

早期 V0.1 映射记录当时没有修改 evaluator；2026-09-27 V2 实施已按新授权完成。T3-08 多级清水泵 `100 < Q ≤ 3000 m³/h` 的 C2=`142.33`；`GB19762-T3-09` 的合法 C3=`144.33` 保留，不做全局替换。当前 Canonical 文本 SHA-256（仓库文本 CRLF→LF 规范）为 `5D91F01B1C5F26DC4F364A3156C4E974B159FA1005BD840489C0BC3465C18C0F`。

当前数值/状态契约见 [`PUMP_NUMERIC_AND_DECISION_CONTRACT_V2`](../../../docs/PUMP_NUMERIC_AND_DECISION_CONTRACT_V2.md)；此前59+14条 Golden 0.2 v07候选保留为历史评审快照，不替换本目录原有 Golden 0.1。当前D测试包有26条 Golden 0.3 候选：18条清水泵通过公共 Application E2E，8条化工泵仅作技术 Profile 诊断；均为 `DRAFT/PENDING`，尚未批准。

边界验收必须至少覆盖：

- `Q=5`、`Q=300`、`Q=600` 等显式包含端点；
- `Q=300+ε`、`Q=600+ε` 等下一个区间切换；
- `Q<5`、类别对应的上限外流量等未命中；
- 同类别不能命中多个行；命中多个时返回 `REQUIRES_REVIEW`，不能随意选第一行。

### V5 工作表专项计算约定（2026-09-26）

以下约定是用户授权的离心泵 V5 工作表历史快照，不代表对 GB 19762-2025 原文增加修约规则；正式 evaluator 规则现由 V2 契约约束：

- 当 `G/H/I/K/L`（流量、扬程、转速、单吸/双吸、级数）均有效时，N 列按这些物理输入计算并保留原始精度，不以设备类别是否填写作为 N 的前置条件。类别缺失或未知时仍不生成标准阈值或等级。
- 早期 V5 工作表证据中的 `ns_cmp=ROUND(ns,6)` 仅为历史诊断；正式 evaluator 路径不得使用六位舍入值参与范围、规则分支或查表。
- 类别为“其他（请备注说明）”时，判级结果始终为“不适用”，包括泵效率缺失、非法或超范围；资料缺失和功率提醒仍写入备注。
- 类别与明确输入的单双吸或级数冲突时，可保留按实际 `K/L` 计算的原始 N，但状态必须拒绝判级；不得因类别冲突静默改写物理输入。

## 6. 异常、缺失与不支持语义

| 场景 | 规范状态 | 必须保留的证据 |
|---|---|---|
| 泵效率缺失，但类别、流量、扬程、转速可确定 | `INSUFFICIENT_DATA` | 输出功率、比转速、C1–C3、限值、查表记录；不生成等级 |
| 已识别类别的 Q 单独证明超出流量区间，即使 H/n 或效率缺失/非法 | `OUT_OF_STANDARD_SCOPE` | 保留可用输入和范围依据；不因无关缺项回退为数据不足 |
| 流量未命中本类别区间 | `OUT_OF_STANDARD_SCOPE` | 实际效率、可计算派生量、候选 `data_id`、所有边界 |
| `其他（请备注说明）` | `NOT_APPLICABLE` | 结论为“不适用”；不生成等级 |
| 类别缺失 | `UNRESOLVED` / `INSUFFICIENT_DATA` / `CATEGORY_MISSING` | 无法路由到清水或石化 Profile；保留缺失类别，不作默认选择 |
| 类别未知 | `UNRESOLVED` / `INVALID_INPUT` / `CATEGORY_UNRESOLVED` | 与类别缺失区分；不生成等级或默认映射 |
| `suction` 或 `stages` 缺失 | `INSUFFICIENT_DATA` | 保留缺失字段；不得假定 K/L 或生成等级 |
| `suction`/`stages` 非法或与类别冲突 | `INVALID_INPUT` | 冲突字段、候选类型和标准来源；不得静默折半流量或改级数 |
| 多级泵缺少级数 | `INSUFFICIENT_DATA` | 流量候选、缺失 `stages`；不得按 1 级计算单级扬程 |
| 输入非正、效率格式非法或单位不明 | `INVALID_INPUT` | 原始值、字段、校验规则和问题码 |
| `pump_chemical` 输入 | 不属于本 Profile | 路由证据；不得使用清水 C 表 |

非空但非法的必填值不再混入缺失字段：流量=`FLOW_INVALID`、扬程=`HEAD_INVALID`、转速=`SPEED_INVALID`、级数=`STAGES_INVALID`、效率=`EFFICIENCY_INVALID`、单双吸=`SUCTION_INVALID`；状态为 `INVALID_INPUT`，不执行比转速/等级计算。字段为空仍为 `INSUFFICIENT_DATA` 并保留缺失字段。冻结 V4 的 `EV_SUCTION` 投影含“不适用/其他（请备注说明）”；这两项虽可由表单表达，但不是公式有效单双吸值。

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
| `PUMP-WATER-CONSISTENCY-001` | 类别与单双吸/级数冲突为 `INVALID_INPUT`，拒绝等级比较 |
| `PUMP-WATER-STAGES-001` | 多级泵级数是单级扬程和比转速的必要条件 |

## 8. 当前实现差异与待评审项

- `metadata.py`、`device_specs.py`、`input_normalization.py` 和 `pump.py` 目前各自承载部分 Profile、字段、别名和规则信息；Phase 1 只完成职责映射，不迁移或删除。
- 当前包来自 `pump.json`，标准包的独立 `standard_pack_version` 尚未在 manifest 中以单独字段表达；本文件暂用 `v1` 作为可追溯候选，需在 G06 冻结。
- 历史 Application/Legacy Regression 曾对单级泵省略 `stages` 使用兼容缺省；该历史行为不属于本候选契约。当前契约要求 K/L 必填、单级 `stages=1` 显式输入；缺失为 `INSUFFICIENT_DATA`，非法值或类别冲突为 `INVALID_INPUT`。Golden 候选均显式填写 K/L，不把旧兼容行为当标准事实。
- 2026-09-27 V2 实施包含数值解析、ns_raw、状态和别名路由改动；修改摘要、测试结果和未决项见 `IMPLEMENTATION_REPORT.md`。Golden 0.3 的26例仍为 `DRAFT/PENDING`。

## 9. 样板完成条件

`pump_water` 映射只有在以下证据被 Solution Review 接受后才可作为下一阶段输入：

1. Canonical 候选包的表 3 数据、页码和哈希可复现；
2. 所有字段单位、别名、类别路由和缺失语义与 Product/Profile Schema 一致；
3. Golden Case 覆盖正常、边界、缺失效率、未知类别和不外推；
4. 当前实现与标准不一致的地方都有 QA ID 或明确的 `NEEDS_MORE_EVIDENCE`；
5. V1 Scope 和版本字段获得产品/方案评审确认。
