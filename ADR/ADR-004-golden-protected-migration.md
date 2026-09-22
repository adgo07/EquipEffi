# ADR-004 Golden-protected Migration

## Decision

Profile 迁移遵循：Legacy Regression → Golden Candidate → 标准复核 → Approved Golden Case → 新实现 → Parity/Intentional Change Verification → 切换 → Legacy Removal。Approved Golden Case 未建立前不得删除旧正式实现。

## Context

当前有 17 个内部 Profile、历史单元测试和多层兼容代码，但 Golden Case Schema 尚未建立。

## Reason

旧代码可能包含错误，重写也可能丢失已验证的专业知识；黄金案例保护业务真相，而不是保护 Python 的内部结构。

## Consequence

Phase 1 先定义 Golden Case Schema；Phase 3 只验证首个样板；Phase 5 再按 Profile 迁移，不批量重写。

