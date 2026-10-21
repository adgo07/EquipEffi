# 开发参考

本页仅记录跨任务仍适用的工程与业务事实；当前状态、范围、QA 和中央基线分别见 `TASK_STATE.md`、`V1_SCOPE.md`、`QA_BACKLOG.md` 与 `PLATFORM_BASELINE.md`。

## 标准与数值

- 标准原文是标准条款的首要证据。映射须保留条号、表/公式、边界与单位；标准事实、技术判断、软件决定分别记录。不得静默修正原文、插值、外推或补造默认值。
- Canonical 是标准数据的机器化表达，Approved Golden 是已批准业务真值。两者各有职责：不能以旧实现回归替代标准证据，也不能通过修改 Golden 使实现通过。
- Pump 使用 Decimal Numeric Profile。数值应从原始词法准确解析并保留计算全精度；展示舍入不能影响比较、快照或 Golden。业务等级采用全值比较，不使用 epsilon。
- 对缺失、未知类别、标准范围外、业务资料不足和系统执行失败分别保留语义。异常或资源读取失败不能伪装成业务不可判定。

## 工程边界

- Domain 不依赖 UI、Excel 或数据库；Presentation 通过 Application 契约访问业务能力；适配器不能复制第二套业务算法。
- 评价结果与历史 Record 的输入、结果、标准依据快照必须保持其产生时的事实。历史记录展示不得重算或追溯改写。
- 默认沿用现有 records schema。不得仅为未来通用化引入 Attempt、Audit/Lineage 框架、额外表或复杂抽象；有明确迁移需求时按 Owner 决策边界处理。
- Qt 是 Windows V1 正式桌面表面。Excel 是批量输入/输出适配器，调用同一正式 Application / Calculator；结果写入新文件，输入工作簿不覆盖。

## 任务前入口

先确认 Git 身份和工作区；阅读 `AGENTS.md`、`TASK_STATE.md`、`V1_SCOPE.md`、`QA_BACKLOG.md`，再按任务范围读取标准与代码。涉及中央公共语义时按 `PLATFORM_BASELINE.md` 执行 Contract Preflight。新标准或实质扩展支持范围须遵循中央 Standard Development Guide 的 Stage A–D。普通维护只记录必要变更与真实验证结果，不复制历史长报告。