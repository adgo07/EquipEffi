# ADR-005 Three Database Responsibilities

## Decision

保留三库职责方向：`catalog.sqlite` 保存可重建的标准目录，`user.sqlite` 保存设置/自定义参数/设备档案，`records.sqlite` 保存 Workspace、Record、Snapshot、Lineage 和 Audit。

## Context

当前运行时主要使用 JSON，SQLite 标准仓储和项目仓储仍是占位；完整持久化表结构尚未设计。

## Reason

标准事实、用户配置和不可变分析记录的生命周期、写权限和备份策略不同，不能合并为一个含义混杂的数据库。

## Consequence

Phase 0 只登记职责和 `Workspace=mutable / Record=immutable` 原则；具体表结构、迁移和事务留给 Phase 1/2/3。

