# GB 19762—2025 离心泵标准档案

本目录为该标准唯一导航入口，覆盖清水离心泵和石油化工离心泵。目录整理不重新批准映射、数据、Golden或产品支持状态。

| 角色 | 当前文件/依据 |
|---|---|
| 主映射入口 | [共同依据与分支导航](STANDARD_MAPPING.md) |
| 清水泵分支 | [pump_water](profiles/pump_water.md) |
| 石油化工泵分支 | [pump_chemical](profiles/pump_chemical.md) |
| 数值与判定工程约定 | [PUMP_NUMERIC_AND_DECISION_CONTRACT_V2](../../PUMP_NUMERIC_AND_DECISION_CONTRACT_V2.md)（原位保留） |
| 原文证据 | [evidence_registry.json](../../../specs/equipment_efficiency/evidence_registry.json) 的 `GB19762-2025-PDF`，含相对定位符与SHA；通过外部证据根定位原PDF |
| 现有表值/系数资产 | [pump.json](../../../src/equipeffi/resources/standards/pump.json) 的water/chemical分支；这是既有Canonical资产，不是独立逐格复核证据 |
| Golden及批准证据 | [water](../../../specs/equipment_efficiency/golden/pump_water/)、[chemical](../../../specs/equipment_efficiency/golden/pump_chemical/)、[批准记录](../../../specs/equipment_efficiency/golden/owner_approvals/) |
| 软件支持与范围 | [V1_SCOPE](../../../V1_SCOPE.md)、[ROADMAP](../../../ROADMAP.md) |
| 验收证据 | [Phase 3](../../phase3_acceptance_record.md)、[Phase 5](../../phase5_acceptance_record.md) |
| 问题与解释 | [根台账](../../../STANDARD_ISSUES_REGISTER.md)：`EQP-STD-GB19762-001`；日期规则同时读取[AGENTS §2.7/2.8](../../../AGENTS.md) |

## 原文与数据边界

标准名称：《离心泵能效限定值及能效等级》；版本2025，实施日期在既有映射登记为2026-03-01。发布日期、官方来源URL和替代关系本次未重新核验，不补写推断值。原PDF SHA与位置复用证据注册，不复制机器绝对路径。

目前本入口不宣称存在一套新批准的水泵全表校对工作簿。后续若补建，须从原PDF核验表格结构和具体表值，记录与映射配套关系及核验范围；不能仅导出pump.json后称其独立标准真值。生产批量输入/结果Workbook与标准表值校对工作簿是不同资产。

## 历史文字的读取方式

两份分支映射保留早期Phase正文及当时的数据指纹、候选状态和运行路径，用于追溯；页首说明区分其与当前状态。当前支持状态看V1_SCOPE/ROADMAP，普通产品日期与记录行为看AGENTS；不从历史“待评审/候选/未发布”文字倒推当前状态。

原`specs/equipment_efficiency/profiles/`路径只保留跳转；历史报告中的原路径继续可达。当前目录不复制共同工程契约或Approved Golden。
