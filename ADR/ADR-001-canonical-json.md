# ADR-001 Canonical JSON

## Decision

Windows V1 的标准事实和正式参考数据以版本化 Canonical JSON 为唯一事实源；`catalog.sqlite` 只能由 JSON 校验和构建，不能人工编辑后反向成为事实源。

## Context

当前仓库以 `standard_manifest.json` 显式选择 17 个标准包，数据文件格式仍有 `rows`、`tables`、`devices`、`water/chemical` 等差异，Canonical Schema 尚未冻结。

## Reason

JSON 易审查、可哈希、适合审计和重建；数据库适合运行时查询，不适合承载无法追溯的人工事实修改。

## Consequence

Phase 1 必须定义 Canonical Schema、来源、版本、data_id、单位和审核状态；Phase 0 不迁移现有数据、不创建最终 Schema。

