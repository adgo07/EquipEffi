# ADR-003 Version Model

## Decision

使用 `app_version`、`business_spec_version`、`catalog_data_version`、`standard_pack_id/version/hash`、`ruleset_version`、`result_contract_version`、`schema_version`、`formula_id/revision` 等明确版本字段；不再使用含义模糊的全局 `algorithm_version`。

Phase 1 冻结候选语义如下：

| 字段 | 责任 |
|---|---|
| `app_version` | 应用/构建发行版本 |
| `business_spec_version` | 业务对象、状态和流程语义 |
| `catalog_data_version` | Canonical 标准事实内容 |
| `standard_pack_id` | 标准包稳定身份 |
| `standard_pack_version` | 标准包结构/发布修订 |
| `standard_pack_hash` | 实际加载内容指纹 |
| `ruleset_version` | 路由、边界、公式、比较和问题码规则 |
| `result_contract_version` | 对外结果字段和语义 |
| `schema_version` | 所用输入/数据/Golden Schema |
| `formula_id` / `formula_revision` | 公式身份与表达/精度/修约修订 |

`standard_pack_version` 与 `catalog_data_version` 不可互换；`standard_pack_hash` 不能由展示层省略。`algorithm_version` 不再作为跨职责总开关。

## Context

当前项目已有包版本、manifest data_version、trace schema 和多处硬编码版本；它们尚未形成正式契约。

## Reason

业务结论变化、标准数据变化、UI 变化和应用打包变化的兼容含义不同，必须能分别追溯。

## Consequence

Phase 1 冻结字段语义；仅 UI 改动不升级 ruleset，查表/边界/插值/比较/结论逻辑改变必须升级。当前状态是 `READY_FOR_SOL_REVIEW`；产品 Scope 和 Python 3.12 环境验证尚未被本 ADR 自行批准为最终发布承诺。
