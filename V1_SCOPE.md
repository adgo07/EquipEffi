# Windows V1 产品范围

本文件是 Windows V1 Profile `scope_status`、`support_status` 与标准开发成熟度的唯一权威。三者分别表示产品范围、当前发布能力及标准开发阶段，不得互相推断。扩大范围或将任何 Profile 提升至 `SUPPORTED` 必须遵守 `AGENTS.md` 的 Owner 决策边界。

## 三个已确认标准收口与当前发布状态（2026-10-27）

Owner要求先收口离心泵、变压器、电动机三个已确认标准。本轮统一现有证据和当前状态，不重新审批已确认映射；没有将该要求解释为自动提升`SUPPORTED`、开放电机正式入口或修改冻结资产。

当前正式版本为[v0.2.1](https://github.com/adgo07/EquipEffi/releases/tag/v0.2.1)，源码`e140283b110e77992099836fddcb34f018e01009`。该版本的实际装配与下表一致；后文Windows V1枚举记录早期范围，不覆盖本节的实际发布事实。

|标准|已确认的映射与工程证据|v0.2.1实际能力|收口边界|
|---|---|---|---|
|GB 19762—2025 离心泵|清水、石化两个Profile的既有批准映射及Golden继续有效|默认开放，`SUPPORTED`，统一V6.1|附录A.2的2950/2960示例矛盾保留EQP-STD-GB19762-002；不更改公式、输入转速或Golden|
|GB 20052—2024 变压器|V2.1主映射与35表工作簿冻结；25列V6.1、内核和产品接入已有工程及人工验收证据|默认开放，`IMPLEMENTED`，已随正式软件发布|工程实现与正式支持提升分开；QA-TR-001保留支持决定。自动温度换算暂缓，辅助阻抗补录建议不重开既有冻结确认|
|GB 18613—2020 电动机|A.2映射与A.1六表、1290格核验，PR33—35内核及产品工程验收已有记录|候选`IMPLEMENTED`；正式启动关闭电机，显式候选使用V6.2／`motor-input.v2`|正式开放、默认模板切换和支持提升尚未执行；006供电对象来源待核，但已批准非阻断选路继续有效|

证据沿用[泵Stage D](docs/phase5_stage_d_evidence_matrix.md)、[变压器实施记录](docs/standards/gb20052_2024/IMPLEMENTATION_REPORT.md)、[变压器复核](docs/standards/gb20052_2024/PR31_REVIEW_FIXES.md)、[电动机实施记录](docs/standards/gb18613_2020/IMPLEMENTATION_REPORT.md)。发布主分支完整Windows CI [40509874376](https://github.com/adgo07/EquipEffi/actions/runs/40509874376)为1225项通过、exit0；发布附件`release-manifest.json`记录包校验、独立状态检查及业务复核边界，不替代各标准的业务批准。

本轮复核六个既有测试模块，覆盖泵数值契约、变压器35表派生与运行资源、电机全源格边界及变压器／电机产品流：25项通过、20.510秒、exit0。首次运行因临时目录权限失败，保留日志；使用项目独立可写临时目录重跑通过，未修改测试。日志在`outputs/three-standards-closure-20261027/`，不作为新增Golden或全量原文重审。

本轮另实际执行默认和`--motor-candidate`两种状态检查，均ready=true、exit0：默认V6.1且电机关闭，候选V6.2且电机可用；泵与变压器状态如上。源码比转速函数分别输入2950和2960时返回178.918560938…与179.525064534…，与独立算术一致，无转速替换。状态检查不冒充新原生窗口人工验收。

提交Owner的收尾建议：下一版本将变压器、电动机列为正式支持，电机转为默认开放，统一模板使用已有V6.2；泵保持不变，V6/V6.1兼容及既有历史快照不变。该建议尚未实施；确认后针对装配、支持投影及模板选择修改并复验，不重发或覆盖已发布v0.2.1。125%系统缩放和另一台干净Windows尚未验证，保留此限制，不重新要求已经完成的本机人工操作。其余标准不在本次收口范围。

## Windows V1原始目标与范围枚举（历史基线）

Windows V1 目标是完整支持 `GB 19762—2025《离心泵能效限定值及能效等级》`，包含 `pump_water` 与 `pump_chemical` 两个 Profile 的适用范围、输入校验、公式/查表、评价结论、标准依据、单台历史记录和批量 Excel 流程。

| Profile | `scope_status` | `support_status` | 标准开发成熟度 | 依据 |
|---|---|---|---|---|
| `pump_water` | `IN_V1` | `SUPPORTED` | `SUPPORTED` | 已批准的 18 条 Golden 与正式产品闭环 |
| `pump_chemical` | `IN_V1` | `SUPPORTED` | `SUPPORTED` | Phase 5 Stage D 独立验收，PR [#13](https://github.com/adgo07/EquipEffi/pull/13)；Stage D 证据见下方 |
| `transformer` | `POST_V1` | `NOT_IN_RELEASE_SCOPE` | Stage A双文件已冻结；25列设计已确认，下一版本实施中 | 当前发布能力不变；Owner已授权下一版本实施，验收前不提升SUPPORTED |

`pump_chemical` Stage D 证据：[`docs/phase5_stage_d_evidence_matrix.md`](docs/phase5_stage_d_evidence_matrix.md) 与 [`specs/equipment_efficiency/evidence/phase5_chemical_stage_d_e2e.json`](specs/equipment_efficiency/evidence/phase5_chemical_stage_d_e2e.json)。其 11 条 Golden 已获 Owner 具名批准。该批准只记录既有事实，不替代未来范围或真值变更所需的授权。

## 下一版本已授权范围（2026-10-23）

Owner已明确下一版本加入 `GB 20052—2024 transformer`，现有 `pump_water / pump_chemical` 保持稳定。实施按“接入设计 → 变压器内核 → 产品接通与验收”推进，25列设计已确认并已授权实施；UI美化、多端客户端、自动温度换算不在本轮范围。

- 接入依据为已冻结V2.1主映射与35表工作簿，二者不修改；不重新开启Stage A。
- 所有设备仍共用一个工作簿、各自Sheet；当前正式V6的离心泵Sheet已确定不修改，变压器25列输入方案已获Owner确认，成品待实施验收。
- [接入设计与Excel兼容方案](docs/standards/gb20052_2024/INTEGRATION_DESIGN.md)给出已确认字段、25列布局、旧新模板矩阵、数值及测试设计。设计批准不等于软件已实现或支持状态已提升。
- 上表与现有 `scope_status` 枚举继续描述当前Windows V1，不以未来范围改写当前发布能力。变压器正式实现及验收完成后，再按Owner决定更新当前产品状态。

### 电动机第一步设计授权（2026-10-25）

Owner随后确认方案无新增待决项即可开始实施，已授权GB18613作为下一版本第三项设备标准按PR33修订稿推进。当前进入Stage C；保留当前Windows V1发布状态，候选实现不等于正式SUPPORTED或发布授权。效率1～100防呆决定继续有效。

Owner已确认开展GB 18613—2020电动机第一步接入设计，依据PR32已合并的A.2主映射及A.1六表校对工作簿。范围为该标准六类电机，不包括GB 30254高压或GB 30253永磁同步；其它标准存在归档文件不代表已获确认。

[第一步设计稿](docs/standards/gb18613_2020/INTEGRATION_DESIGN.md)提出20列电动机Sheet、统一单位、六表选路、数值规则和模板兼容方案。本轮不改当前`motor_lv`的`POST_V1`状态，不开放产品入口，不提升支持状态；设计评审后再开展实现。后续产品集成仅在明确标记的验收候选构建开放电机，正式发布配置保持关闭，直到取得下一版本范围授权及相应验收/发布决定；候选实现不自动等于SUPPORTED。泵、变压器映射及输入契约保持稳定。

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
