# PUMP_NUMERIC_AND_DECISION_CONTRACT_V2

状态：`DRAFT_FOR_INDEPENDENT_REVIEW`。本版本由王玮 2026-09-27 明确冻结为本项目离心泵工程计算契约，并授权 Phase 1 最小实现。它不声称 Decimal50 或总流量/总扬程换算是 GB 19762—2025 原文新增规定；标准公式、表行和系数仍以标准 PDF 与当前 Canonical JSON 为依据。执行者未批准任何 Golden，也未宣布 Phase 1 PASS。

## 1. 生效范围和事实边界

- 仅适用于 `pump_water` 和 `pump_chemical`；其他设备不受影响。
- GB 标准证据：PDF SHA-256 `7F515D8B9D6B4D2AB97FFA7BECB78520BA0579CFBD6D5ECA10C7E7CC77895FEC`，公式(1)–(7)、表2/表3见标准印刷页1–5。
- Canonical 标准候选：`src/equipeffi/resources/standards/pump.json`；其标准数值和稳定 `data_id` 是表格映射来源。T3-08 多级清水泵 `100<Q≤3000 m³/h` 的 C2=`142.33`；T3-09 C3=`144.33` 保留。
- `Decimal50`、半吸/级数换算和精确等级比较是项目级工程约定；不是 GB 对计算精度、舍入模式或软件实现的规定。
- Golden 0.1/0.2、原7例、原始341案例及旧验收证据保持原样；旧版本不再充当新业务输入的隐式补值来源。

## 2. 数值输入和计算

规范原始输入使用十进制文本，单位固定为 `QBEP:m³/h`、`HBEP:m`、`speed:r/min`、`efficiency:%`、`suction:单吸|双吸`、`stages:正整数`。不得先解析成 binary float 再构造 Decimal。正式泵 API 接受十进制字符串、精确整数或 Decimal；拒绝 Python float。新的 Golden 0.3 数值输入一律为原始文本或显式 `null`。

正式及参考计算统一使用 Decimal 上下文 `precision=50`，舍入模式 `ROUND_HALF_EVEN`。标准 JSON 的小数原文以 Decimal 解析，不经 float。标准常数从其十进制源文本构造。公式中间值不按显示位数舍入，不加 epsilon；只在明确的显示字段使用显示格式化。

比转速派生量定义：

```text
S = 1 (单吸) 或 2 (双吸)
N = stages
Q_ns = QBEP / S / 3600            # m³/s
H_ns = HBEP / N                   # m
ns_raw = 3.65 × speed × sqrt(Q_ns) / H_ns^0.75
```

`QBEP`、`HBEP` 始终代表原始总流量、总扬程；`Q_ns`、`H_ns`、`S`、`N` 是派生计算量。`Q_ns` 不用于表2/表3流量分档，也不代替公式(2)–(5)中的 `QBEP`；公式(1)比转速中的单级扬程使用 `HBEP/N`。清水与石化公式(2)–(7)使用同一 `ns_raw`。

`ns_raw` 直接参与范围检查、表行选择、公式分支、`Δη` 和等级阈值计算。正式路径废止 `ROUND(ns,6)`。`ns_display` 仅用于界面、报告和调试，不参与任何业务判断。原 ROUND(ns,6) 案例、4个半微反算案例和旧 Excel 边界差异归为 `historical/numerical diagnostic`，不作为正式 Golden 真值。

效率阈值以完整内部 Decimal 精度比较：

```text
actual_efficiency >= threshold
```

先按1级、2级、3级顺序确定最高满足级别，否则 `BELOW_MINIMUM`。禁止 epsilon、显示值比较、先将阈值保留6位/2位再比较，或修改输入迎合旧工作簿。展示限值允许四舍五入；比较轨迹和内部计算迹必须保留完整阈值。

## 3. 类别、原始字段和状态

“类别未解析”与“已确认的其他类别”分别处理：

| 输入 | category_status | evaluation_status | issue_code | UI结论 | 标准公式 |
|---|---|---|---|---|---|
| 类别缺失/未知、无法唯一路由 | `UNRESOLVED` | 缺失为 `INSUFFICIENT_DATA`；未知为 `INVALID_INPUT` | `CATEGORY_UNRESOLVED`，缺失另带 `CATEGORY_MISSING` | `无法判定` | 不执行 |
| 明确选择 `OTHER` / `其他类别` / `其他（请备注说明）` | `NOT_APPLICABLE` | `OUT_OF_STANDARD_SCOPE` | `CATEGORY_NOT_APPLICABLE` | `不适用` | 不执行 |
| 已知泵型，且所有必需输入有效 | `APPLICABLE` | `SUCCESS` | 无 | 等级或`未达标` | 执行 |
| 已知泵型的流量或比转速超出标准范围 | `APPLICABLE` | `OUT_OF_STANDARD_SCOPE` | `OUT_OF_STANDARD_SCOPE` | `不适用` | 不外推；按现有范围策略返回 |

结果分层如下：

- `support_status`: `SUPPORTED` / `NOT_IN_RELEASE_SCOPE`。它由产品发布门禁提供，不从“标准包 active”推断。
- `category_status`: `APPLICABLE` / `NOT_APPLICABLE` / `UNRESOLVED`。
- `evaluation_status`: `SUCCESS` / `INSUFFICIENT_DATA` / `INVALID_INPUT` / `OUT_OF_STANDARD_SCOPE`；Profile尚未进入发布支持范围时可为 `null`（没有执行评估）。
- 仅 `SUCCESS` 可以带 `grade`：`1` / `2` / `3` / `BELOW_MINIMUM`。其他状态 `grade=null`。
- UI 映射：`1→1级`、`2→2级`、`3→3级`、`BELOW_MINIMUM→未达标`、`INSUFFICIENT_DATA→无法判定`、`INVALID_INPUT→无法判定`、`OUT_OF_STANDARD_SCOPE→不适用`、`NOT_APPLICABLE→不适用`、`NOT_IN_RELEASE_SCOPE→当前版本未支持`。
- 原有 `OUT_OF_STANDARD_SCOPE` 范围政策及“不适用”展示保持；本轮不改成别的状态名。
- `issue_codes` 单独记录原因。类别/单双吸/级数冲突不得继续计算；K/L缺失不补默认值。确认 OTHER 后不运行公式。

必填泵字段非空但无法解析、超出允许范围或不满足离散类型时，属于 `INVALID_INPUT`，不得再放入 `missing_fields` 或报告成 `INSUFFICIENT_DATA`。当前逐字段代码为：流量 `FLOW_INVALID`、扬程 `HEAD_INVALID`、转速 `SPEED_INVALID`、级数 `STAGES_INVALID`、效率 `EFFICIENCY_INVALID`、单双吸 `SUCTION_INVALID`。字段确实为空时仍报告相应 missing code。技术 Profile evaluator 不拥有产品发布门禁，其 `support_status` 保持 `null`；公共 Application 路由负责输出发布状态：已准入清水泵为 `SUPPORTED`，化工泵以及缺失/未知/OTHER 等无已批准 Profile 路由的请求为 `NOT_IN_RELEASE_SCOPE`。

`EV_SUCTION` 为兼容冻结 V4 表单投影仍包含“单吸”“双吸”“不适用”“其他（请备注说明）”四项；后两项不是可用于本标准公式的 suction 值。非空提交后按非法输入处理，并停止公式计算。

## 4. Golden 0.3 与输入兼容

新增 `specs/equipment_efficiency/schemas/golden_case_0_3.schema.json`。顶层 `raw_inputs` 明确保存 `product_type`、`suction`、`stages`、`QBEP`、`HBEP`、`speed`、`efficiency`、`input_basis`、`measurement_point`。合法泵输入为文本；缺失/非法负例保留原始 null 或原始错误文本。类别/单双吸/级数校验由 profile/evaluator 负责；不得静默修正。

`expected_calculation_trace` 独立保存派生值、匹配规则ID和内部阈值；原始数值不得放入派生区域。`source_sidecar` 只允许标准/Canonical/历史诊断来源证据，不允许放入替代输入的业务参数。仓库文本来源（`.json`、`.jsonl`、`.py`、`.md` 等）计算 SHA-256 前将 CRLF 规范为 LF，以免 Git 的 Windows checkout 设置造成同一提交出现不同来源指纹；外部文件及仓库非文本文件仍使用原始字节 SHA-256。Golden 0.1、0.2 schema 和原7例身份保留，只可作为显式兼容读取或历史/诊断输入；读取旧数据不能推断缺失 suction/stages，不能静默改变 schema 状态。

新0.3候选共26条：18条清水泵通过公共 Application E2E（覆盖1/2/3级、轻型立式/卧式及管道泵），8条化工泵仅运行技术 Profile evaluator 并明确 `support_status=null`。所有候选均为 `DRAFT/PENDING`，这组回放只证明候选与当前实现一致，不构成业务批准。每条候选的 source sidecar 固定标准 PDF、Canonical Pack 和参与回放的当前实现文件及 SHA-256；版本化 validator 对0.3代码来源执行精确哈希校验。旧6个 `EFF-EXACT` 降为数值比较诊断，不纳入业务 Golden；旧12个 Excel“等号”例保留来源ID和原始缺项（尤其 K/L），不补 suction/stages，降为历史兼容诊断。旧7个0.1案例保持原ID和文件不变。

## 5. 测试分层

| 层 | 目标 | 人工 Golden |
|---|---|---|
| A. Canonical/rule integrity | 表2/表3、C1/C2/C3、边界开闭、系数、稳定 data_id、不插值/不外推 | 否 |
| B. Mathematical Decimal unit | 原始文本解析、float拒绝、Decimal50、ln/sqrt/幂、ns及η/Δη公式、直接 `T−δ/T/T+δ` 的 `>=` | 否 |
| C. Generated boundary | 从 Canonical min/max/inclusive/exclusive 自动生成边界点、内侧和外侧点 | 否 |
| D. End-to-end Golden候选 | 18条清水公共 Application E2E；8条化工技术诊断不冒充发布支持 | 是；仍需具名批准 |

数值测试使用 Decimal 阈值直接构造阈值前、阈值本身、阈值后三点，不经 Q/H/n 反算。自动边界覆盖不要求每个生成点成为人工 Golden。

## 6. Windows V1范围

pump_chemical 保持 V1_SCOPE 冻结的 UNDER_REVIEW；本次仅用其现有 Profile 做技术诊断，不承诺首发发布支持。公共 Application 在同等 Phase 1 门槛完成前返回 NOT_IN_RELEASE_SCOPE、界面显示“当前版本未支持”。pump_water 的既有 V1 候选状态不变；本次不扩大产品范围。

## 7. 实施范围和治理状态

本轮授权仅覆盖离心泵 evaluator、直接应用/输入/结果适配、Golden schema/候选、针对性测试和 Phase 1 文档。未覆盖其他设备、完整 PySide6、SQLite、Excel工作簿、报告产品或 Phase 2。Canonical 标准数值未修改；T3-08 C2=`142.33` 保持。旧 DRAFT 不转 APPROVED。R01–R06 定点修订完成后仍须原独立验收会话按固定 commit SHA 复验；当前治理状态保持 `BLOCKED`。只有满足治理出口后才能转 `READY_FOR_SOL_REVIEW`，执行者不得宣布 Phase 1 PASS。
