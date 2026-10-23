# Windows V1 产品范围

本文件是 Windows V1 Profile `scope_status`、`support_status` 与标准开发成熟度的唯一权威。三者分别表示产品范围、当前发布能力及标准开发阶段，不得互相推断。扩大范围或将任何 Profile 提升至 `SUPPORTED` 必须遵守 `AGENTS.md` 的 Owner 决策边界。

## 产品目标与当前状态

Windows V1 目标是完整支持 `GB 19762—2025《离心泵能效限定值及能效等级》`，包含 `pump_water` 与 `pump_chemical` 两个 Profile 的适用范围、输入校验、公式/查表、评价结论、标准依据、单台历史记录和批量 Excel 流程。

| Profile | `scope_status` | `support_status` | 标准开发成熟度 | 依据 |
|---|---|---|---|---|
| `pump_water` | `IN_V1` | `SUPPORTED` | `SUPPORTED` | 已批准的 18 条 Golden 与正式产品闭环 |
| `pump_chemical` | `IN_V1` | `SUPPORTED` | `SUPPORTED` | Phase 5 Stage D 独立验收，PR [#13](https://github.com/adgo07/EquipEffi/pull/13)；Stage D 证据见下方 |
| `transformer` | `POST_V1` | `NOT_IN_RELEASE_SCOPE` | Stage A双文件已冻结；下一版本Stage B设计中 | 当前V1尚未接入；2026-10-23 Owner已授权下一版本纳入，见下节 |

`pump_chemical` Stage D 证据：[`docs/phase5_stage_d_evidence_matrix.md`](docs/phase5_stage_d_evidence_matrix.md) 与 [`specs/equipment_efficiency/evidence/phase5_chemical_stage_d_e2e.json`](specs/equipment_efficiency/evidence/phase5_chemical_stage_d_e2e.json)。其 11 条 Golden 已获 Owner 具名批准。该批准只记录既有事实，不替代未来范围或真值变更所需的授权。

## 下一版本已授权范围（2026-10-23）

Owner已明确下一版本加入 `GB 20052—2024 transformer`，现有 `pump_water / pump_chemical` 保持稳定。实施按“接入设计 → 变压器内核 → 产品接通与验收”推进，当前只做第一步；UI美化、多端客户端、自动温度换算不在本轮范围。

- 接入依据为已冻结V2.1主映射与35表工作簿，二者不修改；不重新开启Stage A。
- 所有设备仍共用一个工作簿、各自Sheet；当前正式V6的离心泵Sheet已确定不修改，变压器输入Sheet待确认。
- [接入设计与Excel兼容方案](docs/standards/gb20052_2024/INTEGRATION_DESIGN.md)给出字段、24列提案、旧新模板矩阵、数值及测试设计。提案完成不等于Sheet已批准、软件已实现或支持状态已提升。
- 上表与现有 `scope_status` 枚举继续描述当前Windows V1，不以未来范围改写当前发布能力。变压器正式实现及验收完成后，再按Owner决定更新当前产品状态。

### 其他已登记 Profile

- `UNDER_REVIEW`：`fan`、`blower`、`submersible`、`heat_treatment`、`heat_pump_chiller`、`heat_pump_water_heater`、`duct_ac`、`unitary_ac`、`multi_split_ac`。
- `POST_V1`：`motor_lv`、`motor_hv`、`motor_pmsm`、`compressor`、`boiler`、`transformer`。
- 上述 Profile 当前均不因此文件而获得发布支持；`active` pack、存在 evaluator 或历史测试均不等于 `SUPPORTED`。

## 状态定义与边界

- `scope_status`：本仓产品范围决定，取 `IN_V1`、`UNDER_REVIEW`、`POST_V1`。
- `support_status`：当前发布能力。只有正式实现和所需独立验收证据齐备后才能为 `SUPPORTED`；否则不得宣称可用。
- 标准开发成熟度：遵循中央 ACTIVE `STANDARD_DEVELOPMENT_GUIDE_V0.1.md` 的 Stage A–D 状态。它不代替发布支持决定。
- 运行时类别状态、评价状态和等级属于单次业务结果，不用于反推以上三项。

## 受保护事实

- 批准的 pump Golden 是业务真值；不得通过修改 Golden 让实现测试通过。标准映射以标准原文证据为准，区分标准事实、技术判断与软件决定。
- 既有历史 Record 必须按其保存时的快照展示；不得追溯改写、补造 provenance 或重新计算。
- 标准范围变化、`UNDER_REVIEW`/`POST_V1` 移入 V1 或任何新增 `SUPPORTED` 决定均须 Owner 明确授权。Phase 状态只见 [`TASK_STATE.md`](TASK_STATE.md)。
