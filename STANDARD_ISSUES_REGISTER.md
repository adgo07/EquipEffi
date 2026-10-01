# 标准问题与解释台账

状态：**ACTIVE REGISTER**

本台账用于记录标准原文事实、技术判断与软件实现决定。不得用本台账改写标准原文，也不得把内部判断或软件选择表述成发布机构正式解释。

## 1. 类型代码

| type code | 中文解释 |
|---|---|
| `TYPO` | 疑似笔误 |
| `AMBIGUITY` | 歧义 |
| `CONFLICT` | 条款、公式或表格冲突 |
| `MISSING` | 标准未规定 |
| `TERM` | 术语或现实对象对应不清 |
| `REFERENCE` | 引用标准、版本或外部依据问题 |
| `IMPLEMENTATION` | 软件实现解释问题 |

## 2. 状态代码

| status code | 中文解释 |
|---|---|
| `OPEN` | 待解决 |
| `PROVISIONAL` | 已有临时处理口径 |
| `RESOLVED` | 已有充分依据确认 |

`RESOLVED` 不自动等于发布机构官方确认；是否有官方解释必须在“确认程度”中单独说明。

## 3. 登记规则

- 问题编号采用 `EQP-STD-<标准号简写>-NNN`，一旦使用不得改号或复用。
- 每个问题必须分开记录“标准原文事实”“当前技术判断”“软件当前处理方式”。
- 无法准确复制标准原文时，不得凭记忆补写；应记录准确定位、事实摘要或“未复制原文”，并保留证据来源。
- 影响正式业务结果的问题必须可追踪：`Standard Issue → Software Decision → Rule / Calculator → Test / Golden Case`。
- 后续修改既有解释时，必须检查相关测试和历史结果兼容性。
- 当前只登记已有明确证据的问题，不重新审计全部标准，也不为填表制造问题。

## 4. 当前问题

### EQP-STD-GB19762-001 — 标准实施日期与软件默认 `as_of` 的关系尚未完成产品级决定

| 字段 | 记录 |
|---|---|
| 问题编号 | `EQP-STD-GB19762-001` |
| 标准编号及名称 | GB 19762—2025《离心泵能效限定值及能效等级》 |
| 标准版本 | 2025 |
| 条款 / 表 / 公式 / 页码 | 标准实施日期及软件标准版本选择；现有 `pump_water` 映射记录实施日期为 `2026-03-01`，本问题不涉及泵公式或表 3 数值 |
| 标准原文 | 本台账不复制标准全文。当前可追溯事实为：`specs/equipment_efficiency/profiles/pump_water.md` 记录该标准实施日期为 `2026-03-01`；原文证据由该映射登记的 `GB19762-2025-PDF` 外部证据注册项追溯 |
| 问题类型 | `IMPLEMENTATION`（软件实现解释问题） |
| 问题说明 | 软件多处存在评价日期 `as_of` 的默认行为。标准实施日期可以决定某日期是否允许使用该版本，但标准本身并不会自动给软件定义默认 `as_of`。若默认来源不明确，可能选择错误的标准生效状态 |
| 支持证据 | `QA_BACKLOG.md` 的 `QA-AUD-031`；`specs/equipment_efficiency/profiles/pump_water.md`；现有 Pump Golden Cases 全部显式记录 `as_of` |
| 当前技术判断 | `as_of` 应作为可审计的标准版本选择依据；是否允许兼容默认、默认日期来源以及结果如何展示来源仍是产品/治理决定，不能写成 GB 19762 明文规定 |
| 软件当前处理方式 | 当前默认/显式 `2026-08-23` 可使用该标准；显式 `2026-02-28` 会因早于 `2026-03-01` 实施日而拒绝；Golden Cases 均显式记录 `as_of`。本任务不修改这些行为 |
| 确认程度 | 标准实施日期与现有运行行为有仓库证据；默认 `as_of` 的产品口径仍未最终确认；**不存在发布机构对软件默认日期的官方解释** |
| 业务影响 | 高：错误默认日期可能导致在标准未实施时使用该版本，或在版本切换时选择错误标准，进而影响正式评价结果 |
| 关联 Rule / Calculator | 标准版本选择 / Application request；`pump_water`；Pump Calculator/evaluator 路由 |
| 关联测试 / Golden Case | `QA-AUD-031` 记录的日期 probe；18 条已批准 `pump_water` Golden 0.4 均显式携带 `as_of`；本台账不新增测试 |
| 状态 | `PROVISIONAL`（已有临时处理口径） |
| 首次发现日期 | 2026-09-22（`QA_BACKLOG.md` Phase 1 P0 Evidence Review） |
| 最后更新日期 | 2026-10-01 |

### 追踪链

```text
EQP-STD-GB19762-001
→ Software Decision: 当前保留既有日期选择行为，Golden 明确记录 as_of；默认来源待后续产品决策
→ Rule / Calculator: standard-version selection / pump_water / Pump evaluation path
→ Test / Golden Case: QA-AUD-031 date probes + approved pump_water Golden 0.4 cases
```

本登记只把既有 `QA-AUD-031` 纳入标准解释治理，不在本任务中修改 `as_of` 默认值、Evaluator、Golden Case 或标准映射。
