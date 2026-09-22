# EquipEffi Agent 纪律

## 当前治理

- 当前路线只有 `EquipEffi V2.2`。
- 当前 Phase 只有 `Phase 0` 的收口和随后 `Phase 1` 的启动。
- v15 / T04.xx / 历史 HANDOFF 不拥有自动任务调度权。
- 任何 Agent 开始工作前必须读取 `ROADMAP.md`、`TASK_STATE.md`、`HANDOFF.md` 和相关权威审计文件。
- 不得根据旧 HANDOFF 中的“下一边界任务”自动继续。

## 阶段纪律

- 当前 Phase 未通过前不得越级实施 Phase 2 及以后产品功能。
- Phase 1 不批量迁移 17 个 Profile；先冻结业务规范和数据契约。
- Phase 0 默认只审计、记录和治理，不重构、不扩功能、不搬目录。
- 旧资产先分类为 `KEEP`、`VERIFY`、`MIGRATE`、`REWORK`、`DEPRECATE`、`DELETE_CANDIDATE` 或 `OBSOLETE`，不得因零引用直接删除。

## 业务正确性

- Canonical JSON 是标准事实候选源；Python 常量不能继续作为标准表格唯一事实源。
- `Legacy Regression` 不等于业务真相；迁移必须由 Approved Golden Case、标准证据和意图变化说明保护。
- 任何可能改变标准选择、表选择、单位、公式、边界、插值、比较方向、缺失语义、适用范围或淘汰结论的改动，必须先登记 QA/P0，并提供证据。
- 未支持的 Profile 必须返回明确的 Support Status，不得伪装成“已支持但无法计算”。

## P0 Hotfix 条件

只有全部满足以下条件才能在 Phase 0B 修改业务代码：

1. 有明确标准或现有回归测试证据；
2. 已在 `QA_BACKLOG.md` 登记为 P0；
3. 修改范围最小，不改变架构、不顺手清理；
4. 有新增或修改的针对性回归测试；
5. 修改前后结果、标准引用和影响范围均已记录。

本次 Phase 0B 状态为 `NOT_EXECUTED`。

## 文件和测试保护

- 不覆盖原始标准、原始模板、用户工作簿、校对册或发布产物。
- 关键资源修改前后必须更新 `BASELINE.md` 的哈希和 `HANDOFF.md` 的事实。
- 正式 unittest、compileall、package/resource smoke 和性能基线必须按命令、环境、耗时、pass/fail/error/skip/not_run 完整记录。
- 性能问题先登记实测结果，不能在 Phase 0 直接做 Repository 或缓存重构。
- 依赖方向：Domain 不依赖 UI/Excel/SQLite；Presentation 只能通过 Application 契约调用核心；装配层不得制造新的包级环。

