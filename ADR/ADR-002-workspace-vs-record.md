# ADR-002 Workspace 与 Record

## Decision

`Workspace` 是可变分析草稿，`Record` 是不可变正式记录。Finalize 时输入快照、结果快照、数据引用、规则引用、lineage 和 audit event 必须在同一事务中写入。

## Context

当前仓库只有 `DeviceDraft`、JSON/API 返回和一个抛出 `FeatureNotEnabledError` 的 SQLite 项目仓储，没有可恢复的 Workspace/Record 生命周期。

## Reason

可变输入与历史事实混用会破坏历史复现；显式分离才能支持跨启动恢复、从 Record 创建新 Workspace 和可审计重算。

## Consequence

Phase 1/2 设计契约和事务边界，Phase 3 用纵向样板验证；Phase 0 不建立最终 SQLite 表。

