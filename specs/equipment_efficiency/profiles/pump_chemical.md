# `pump_chemical` / GB 19762-2025 石油化工泵映射 V0.2 候选

状态：**Phase 5 更新**。11 条 Golden 已于 2026-10-02 获 Owner 具名批准（11/11），
Stage D 证据闭环已完成并交独立验收
（`docs/phase5_stage_d_evidence_matrix.md`、
`specs/equipment_efficiency/evidence/phase5_chemical_stage_d_e2e.json`）。

- **统一正式产品路径**（`CentrifugalPumpAnalysisService`，PySide6 Qt Desktop `--qt`）
  的 `support_status` 为 `SUPPORTED`（**支持提升候选**）；
- 治理状态为 `SUPPORT_PROMOTION_CANDIDATE` / `READY_FOR_INDEPENDENT_ACCEPTANCE`，
  **独立验收通过前不得写成"正式支持已经生效"**；
- **非正式表面**（`--json` / `ApplicationApi` / JSONL / CLI / `--web` /
  legacy Tk `--gui` / V4·Excel）仍返回 `NOT_IN_RELEASE_SCOPE`，登记为
  `REGISTERED_DEVIATION`（`QA_BACKLOG.md` 的 `QA-P5-001`～`005`）。

数值与状态以 `PUMP_NUMERIC_AND_DECISION_CONTRACT_V2` 为当前契约。
本 Phase **未**修改任何公式 / 边界 / 等级 / Canonical 数据。

## 1. 身份和证据

| 项目 | 映射 |
|---|---|
| 公共设备类型 | `centrifugal_pump` |
| Profile | `pump_chemical` |
| 标准 | GB 19762-2025《离心泵能效限定值及能效等级》 |
| 标准包 | `gb19762_2025_chemical_v1` |
| Canonical 候选 | `src/equipeffi/resources/standards/pump.json` 的 `chemical` 节 |
| 当前目录数据版本 | `2026.09.26-t3-08-c2-142.33-v1`（manifest） |
| Canonical SHA-256（仓库文本 CRLF→LF 规范） | `5D91F01B1C5F26DC4F364A3156C4E974B159FA1005BD840489C0BC3465C18C0F` |
| 标准 PDF SHA-256 | `7F515D8B9D6B4D2AB97FFA7BECB78520BA0579CFBD6D5ECA10C7E7CC77895FEC` |
| 适用范围 | 标准印刷页1；PDF页7 |
| 表2 | 标准印刷页2；PDF页8 |
| 公式(1) | 标准印刷页3；PDF页9 |
| 公式(4)–(7) | 标准印刷页4–5；PDF页10–11 |

`active` 是可加载状态，不表示数据或 Profile 已获业务批准。原始标准 PDF 不随仓库提交；其 `source_id`、注册相对定位符和 SHA 固定在 `specs/equipment_efficiency/evidence_registry.json`。验证时由 `--external-evidence-root` 或 `EQUIPEFFI_EXTERNAL_EVIDENCE_ROOT` 提供本机证据目录。表2包括标准列出的单级和多级石油化工离心泵，表内数据以规范 `单级`/`多级` 表示。

## 2. 产品字段与规定点

原始字段为 `product_type`、总 `QBEP`、总 `HBEP`、`speed`、`efficiency`、`suction`、`stages` 和 `as_of`；数值通过十进制文本转为 Decimal50。兼容别名不改变总流量/总扬程语义。石化公式输入须对应同一标准规定点/BEP；合成候选使用显式 `STANDARD_BEP/BEP` 测试前提，真实设备仍需来源证明。

石化类别只接受“单级石油化工离心泵”和“多级石油化工离心泵”。单级要求 `stages=1`；多级要求级数大于1。`suction` 和 `stages` (K/L) 均必须显式提供；按标准公式(1)对双吸以总 Q 的一半计算比转速。K/L缺失为 `INSUFFICIENT_DATA`，非法值或类别/输入冲突为 `INVALID_INPUT`，均不出等级；不根据历史源表补值。

公共 `centrifugal_pump` 路由只接受这两个完整标准名称，或显式 `pump_profile=chemical`/`pump_chemical`。未登记文本不得通过“石化”“化工”“多级”等子串被猜测为此 Profile。公共 Application 仍返回 `NOT_IN_RELEASE_SCOPE`；技术诊断需显式指定 Profile，不能因此视为发布支持。

## 3. 标准公式与表2

比转速按统一契约以 Decimal50 从十进制原始输入计算：

```text
S           = 1（单吸）或 2（双吸）
N           = stages
Q_ns        = QBEP / S / 3600
H_ns        = HBEP / N
ns_raw      = 3.65 × speed × sqrt(Q_ns) / H_ns^0.75
```

正式路径以 `ns_raw` 直接做范围/分档、公式(6)/(7)和效率计算；旧 `ROUND(ns,6)` 结果只留作 historical/numerical diagnostic。表2的 Q 轴始终使用原始总流量 QBEP（`5<Q≤300` 和 `Q>300`），不能以 Q_ns 替代。不插值、不外推；无法唯一命中稳定 `data_id` 时不提供等级。

`η_b` 使用 `ln(Q_BEP)` 的六次多项式。标准注释规定仅当 Q_BEP 大于3000 m³/h 时，在 η_b 计算中代入3000；表2查 Q 使用实际流量。当前 Canonical 系数按从六次项到常数项排列：

| 系数组 | 单级石化泵 | 多级石化泵 |
|---|---|---|
| `η_b` | `4.7057338e-5, -0.0066320555, 0.15115754, -1.4023278, 5.5234828, -0.83298912, 41.951745` | `0.00055836234, -0.012499816, 0.099576648, -0.46811292, 1.9459872, 1.4371144, 41.467097` |

标准公式(6) 的 `Δη` 系数（按 `ns^6` 至常数项）为 `3.7873403e-10, -1.7898913e-7, 3.4269717e-5, -0.0034148047, 0.1905063, -6.0391904, 98.970658`。公式(7)为 `-1.1111111e-10, 1.6769231e-7, -0.00010507265, 0.03498704, -6.529872, 647.73909, -26684.155`。公式(6)覆盖20≤ns<120且表行要求修正的组合，公式(7)覆盖210<ns≤300且表行要求修正的组合；120≤ns≤210时 Δ=0，表行未要求修正时也取0。

```text
η0       = η_b - Δη
η_level = η0 + 表2 offsets
```

Canonical JSON 中保留全部16行 stable ID 与系数顺序；原始标准 PDF 的路径、页码和 SHA-256 在本文件身份表中固定，供独立核对。

## 4. 表2规则行

Canonical 候选含16个组合：两种泵级类型 × 两个 Q 区间 × 四个 ns 区间，稳定 ID 为 `GB19762-R000011` 至 `GB19762-R000026`。每行独立保存三级 offsets、是否使用 Δη、闭开端点及 PDF 来源页。实际完整值按原 JSON 字节指纹追溯，不复制成第二份业务事实源。

适用标准类型外的水泵、其他类别、Q≤5、ns<20 或 ns>300 均不映射到“最近”一行。石化9项历史 raw ns / 六位范围差异仅为 Application 与契约候选的诊断，不证明当前 evaluator 应立即修复，也不归为 `pump_water` P0。

## 5. 缺失和冲突语义

状态映射引用 [`PUMP_NUMERIC_AND_DECISION_CONTRACT_V2`](../../../docs/PUMP_NUMERIC_AND_DECISION_CONTRACT_V2.md)：K/L 缺失 → `INSUFFICIENT_DATA`；K/L 非法或类别/单双吸/级数冲突 → `INVALID_INPUT`，均不出等级；Q/H/n/效率缺失 → `INSUFFICIENT_DATA`。Q≤5 可单独证明范围外，即使 H/n 缺失或效率非法/缺失仍返回 `OUT_OF_STANDARD_SCOPE`、结论“不适用”；对依赖 ns 的范围，缺 H/n 时不得推断范围外。类别缺失为 `UNRESOLVED/INSUFFICIENT_DATA/CATEGORY_MISSING`，未知类别为 `UNRESOLVED/INVALID_INPUT/CATEGORY_UNRESOLVED`；明确 OTHER 为 `NOT_APPLICABLE`。缺效率仍可保留由其余有效输入计算的范围/中间结果。应用层在同等 Phase 1 门槛完成前返回 `NOT_IN_RELEASE_SCOPE`；profile evaluator 仅用于技术验证。

本轮 155 条原石化行及新 Golden 0.3 技术候选均不自动成为 Approved Golden。V0.2 候选与旧输入身份按历史文件保留；V0.3 中26个代表候选均为 `DRAFT/PENDING`，其中8个化工泵案例只直接回放技术 Profile evaluator，`support_status=null`，不表示应用层发布支持。公共 Application 对 `pump_chemical` 仍由发布门禁返回 `NOT_IN_RELEASE_SCOPE`。Canonical 标准 JSON 和旧 Golden 0.1 未覆盖或改批。

与清水泵共用的状态区分适用于本 Profile：K/L 等必填值确实缺失时为 `INSUFFICIENT_DATA`；非空但非法时为 `INVALID_INPUT`，例如级数 `STAGES_INVALID`、单双吸 `SUCTION_INVALID`，并从 `missing_fields` 移除。类别/单双吸/级数冲突同样停止公式计算。
