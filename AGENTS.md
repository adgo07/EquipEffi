# EquipEffi Agent 纪律

本仓只保留项目专属规则与中央治理入口；中央规则正文以 Qingzhou-contracts 为准。

## 仓库与任务状态

- 产品：EquipEffi（Module ID `qz.equipment_efficiency`）；Canonical 仓库：<https://github.com/adgo07/EquipEffi.git>；默认分支 `master`。
- 开工前核对工作树根、`origin`、分支、HEAD、工作区状态，并同步远端；`origin` 不符时停止。路径只表示本机环境，不代表仓库身份。
- 当前 Phase 状态见 [`TASK_STATE.md`](TASK_STATE.md)；Windows V1 Profile 范围唯一权威为 [`V1_SCOPE.md`](V1_SCOPE.md)；QA 唯一状态源为 [`QA_BACKLOG.md`](QA_BACKLOG.md)。旧任务卡、HANDOFF 和报告无自动调度权。
- Phase 1–7 已通过独立验收；Phase 8 已执行并合并 PR #16（`64b656ee`），仅为 `EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE`。不得自行声明 `PHASE_8_PASS` 或进入 Phase 9。
- Owner 于2026-10-23明确纳入变压器并确认25列输入方案，2026-10-27授权v0.2.1正式发布后要求收口泵、变压器、电机。实际发布与候选边界见 [`V1_SCOPE.md`](V1_SCOPE.md)；旧“下一版本实施中”文字不覆盖已完成实现。本轮0.2.2收尾按V1_SCOPE记录的后续授权推进变压器／电机正式支持、电机默认开放和已有V6.2切换；其余设备不自动提升或开放。

## Owner 决策边界

在已批准范围内可自主处理普通实现、测试、重构和文档。以下事项须先取得 Owner 明确决定：产品范围变化；影响正式结果的标准解释变化；Approved Golden 真值变化；Frozen Contract 基线升级；不可逆用户数据/数据库迁移；正式发布；将 `support_status` 提升为 `SUPPORTED`。

可能影响标准选择、字段、单位、公式、边界、插值、比较、缺失语义、范围或结论的工作，先登记 QA/标准问题并核对标准原文、Canonical 与 Golden 证据，提供针对性回归和修改前后影响范围；标准解释变化仍须 Owner 决定。不得静默纠正标准、补造缺失依据、用历史回归代替业务真值，或把执行错误伪装成 `INSUFFICIENT_DATA`。Frozen transformer 主映射与表1–35校对工作簿是一体基线，未经针对具体变更的 Owner 授权不得修改。Canonical、Approved Golden、原始标准、正式模板和发布资产均受保护。

## 本仓业务约束

- 标准/模板资产状态必须分开：**变压器V2.1主映射与35表校对工作簿已成套冻结；当前正式V6的离心泵Sheet及其共享配置依赖已确定、不修改；变压器25列V6.1已实现并随v0.2.1发布，工程及人工证据见实施记录；v0.2.1发布时为IMPLEMENTED，0.2.2候选已按Owner授权提升为SUPPORTED（未发布），默认统一使用V6.2并兼容V6/V6.1输入**。原A—U保留位置，I填额定双绕组/高中阻抗数字；V/W填高/低额定电压，X/Y填高低/中低额定阻抗数字。禁止单元格拼接多个数字；不加适用条件或单位列，损耗统一W。类别包含“其他类别”（不在范围）和“不确定类别”（无法判定），适用型式由明确类别选择表达。35表校对工作簿不是用户输入模板。唯一入口见 [`gb20052_2024/README.md`](docs/standards/gb20052_2024/README.md)。
- Pump Numeric Profile 为 `EQUIPEFFI_PUMP_DECIMAL50_V2`：Decimal、精度 50、`ROUND_HALF_EVEN`、全值比较及 `PUMP-RP-0.1` 参考过程。容差仅用于 Conformance；不得把此配置推为平台默认。
- Windows V1 正式桌面表面为 PySide6 Qt。评价日期不是业务门禁；Qt 新评价自动取本机日期，标准生命周期仅作简短非阻断提示。合法终态分析自动追加不可变 Record；资料不足可形成 Record，系统执行失败不得形成业务结果。普通用户没有“草稿”概念或技术详情；派生数值通常显示2位小数，标准限值沿用其精度，展示舍入不改变比较、精确快照或Golden。不删除内部trace/provenance证据，不增加 Reproduce/Attempt/通用 Audit 框架。
- 默认不改 `records.sqlite`；若明确需求确需 schema 迁移，先停止并交 Owner 决定。既有 Record 不追溯改写，不补造 provenance。
- Excel 使用 Owner 指定的 V6 全设备工作簿；清水泵与化工泵共用“离心泵”Sheet。Excel 是输入/输出适配器，正式评价必须调用同一 Application / Calculator，不得建立第二套业务算法。类别选项与 Qt 契约一致（8 个正式泵型、“其他类别”、“不确定类别”）；“不确定类别”是合法选择。当前固定展示结论为“1级 / 2级 / 3级 / 未达3级 / 不在范围 / 无法判定”，Qt 与 Excel 一致；此展示映射不改变底层状态、资格或快照。数量必填且为正整数。模板一次下载并提供统一容量策略；少量、100、1,000、10,000 行均无需用户按 Sheet 配置行数。未授权的其他 Sheet 不得删除、重排或改变业务内容。
- 每个 Workbook 批次形成一条 `batch_record`，不为每行创建普通单台 Record；输出另存为新 Workbook，不得覆盖输入。Phase 8 细节见本轮合并的 PR [#16](https://github.com/adgo07/EquipEffi/pull/16)。标准原件不得进入正式安装包。
- 不得修改已冻结的 `records.sqlite` migrations `001` / `002`；不经明确授权不得将 `support_status` 提升为 `SUPPORTED`。

## 中央治理入口

中央仓：<https://github.com/adgo07/Qingzhou-contracts.git>。`platform-lock.json` 是锁定事实源；升级 Frozen Contract 仅能由显式治理任务完成。Frozen 文件按 locked SHA 读取；ACTIVE / ACTIVE-EVOLVING 指南依据中央 `docs/GUIDE_INDEX.md` 路由读取当前版本。UI 规则也按该索引读取，不在本仓钉死指南版本。当前锁与读取边界见 [`PLATFORM_BASELINE.md`](PLATFORM_BASELINE.md)。不得把 ACTIVE 指南当 Frozen，也不得自动跟随中央 `main`。

新标准或实质扩大既有支持范围须依次完成 Standard Development Stage A–D。标准解释台账见 [`STANDARD_ISSUES_REGISTER.md`](STANDARD_ISSUES_REGISTER.md)，标准归档入口见 [`docs/standards/README.md`](docs/standards/README.md)。中央公共语义缺口提交中央治理，不在本仓私造规则。

长期开发事实见 [`docs/DEVELOPMENT_REFERENCE.md`](docs/DEVELOPMENT_REFERENCE.md)。文档优先中文；稳定 API、枚举、schema 和机器字段保持既有标识。
