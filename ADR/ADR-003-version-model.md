# ADR-003 Version Model

## Decision

使用 `app_version`、`business_spec_version`、`catalog_data_version`、`standard_pack_id/version/hash`、`ruleset_version`、`result_contract_version`、`schema_version`、`formula_id/revision` 等明确版本字段；不再使用含义模糊的全局 `algorithm_version`。

## Context

当前项目已有包版本、manifest data_version、trace schema 和多处硬编码版本；它们尚未形成正式契约。

## Reason

业务结论变化、标准数据变化、UI 变化和应用打包变化的兼容含义不同，必须能分别追溯。

## Consequence

Phase 1 冻结字段语义；仅 UI 改动不升级 ruleset，查表/边界/插值/比较/结论逻辑改变必须升级。

