# Phase 2 最小正式工程底座

状态：执行设计；路线 EquipEffi V2.3；授权：用户本次 Phase 2 execution authorization。

## 1. Phase 2 Scope

以 master@78831af1778255e1b19a904e9135d56a9672eaf2 为起点，建立外层装配、可验证依赖边界、设置持久化、迁移、日志、可选 Qt 薄壳和按测试编号比较的 Windows 回归门禁。正式证据使用 Python 3.12；本机 3.12.14，起点 Windows CI 3.12.10。

### 平台 / Contract 预检查

中央锁 ee5feb0cc34dbd99790500fadd0c4c932e202a20 不变。按此 SHA 读取 Architecture V2.1 FROZEN、Numeric Contract v1 FROZEN；按当前合并版本读取 GUIDE_INDEX、PRODUCT_DELIVERY_POLICY、UI_DESIGN_GUIDELINES。

MUST：Domain/Application 与具体 UI、SQL 和外层实现隔离；外层统一装配；中文优先；UI 状态与业务 Workspace 分离；既有业务结果受 Golden/Conformance 保护。MUST NOT：隐式改变数值配置、业务比较、标准事实；把 DRAFT 契约当 Frozen；自动升级锁或 Phase。

冲突分类：QA-AUD-034/035 属 LOCAL DEFECT，本阶段修复；Pump Decimal50 属 ALLOWED PROJECT DIFFERENCE，保留；无新增 REGISTERED DEVIATION 或 CENTRAL CONTRACT GAP，不需改中央 Contract。Standard Issue：已读取台账；EQP-STD-GB19762-001 的评价日期问题不涉及本切片，不改变其解释。Qt 来源为 V2.3 §5.1 与用户明确授权，中央 UI 指南 §4 是设计方向，不是迁移授权。

## 2. Non-goals

Phase 2 != pump_water 完整产品闭环；!= pump_chemical 支持；!= Record 正式生命周期；!= Excel；!= transformer 开发；!= 发布。不得修改泵算法、Approved Golden、Canonical、Numeric Profile、support_status、platform-lock、as_of；不得建 Workspace/Record 业务表或保存草稿。保留 Tk 默认入口、Web/JSON/ApplicationApi/EvaluationFacade 的业务行为。docs/planning/ 不读作权威、不修改、不提交。

## 3. P2-G01～G04

| Goal | 实施 | 证明 |
|---|---|---|
| P2-G01 | composition.py 外层装配、AST 依赖测试、SettingsRepository/Service、运行契约、QA 处置 | AST 含相对导入检测；旧业务启动/API 回归；已知模板损坏警告与未知异常传播 |
| P2-G02 | AppDataPaths、user.sqlite 设置、001_create_settings、日志 | 真 SQLite 集成、重启幂等、校验和检测、事务回滚、轮转与 traceback |
| P2-G03 | optional PySide6、--qt、五页占位、语义 Token、设置恢复 | offscreen 导航/关闭、跨进程恢复；--gui 仍 Tk |
| P2-G04 | exact Windows baseline、按 ID 比较、Required CI、执行报告 | 全量真实结果与已知/新增差异；Pump、18 Golden、Numeric、compile、whitespace |

## 4. Qt Application Contract Decision

唯一正式链：Qt Presentation → SettingsService → SettingsRepository Protocol → SqliteSettingsRepository。Qt 不导入 Infrastructure、ApplicationApi、EvaluationFacade、EvaluationService 或 Domain evaluator。外层 composition 注入 SettingsService；设备分析 use-case 留 Phase 3，不新增第三套评价接口。五页均显示“尚未在 Phase 2 实现”，不含设备评价字段。

## 5. per-DB Persistence Policy

| 数据库 | 策略 | 本阶段 |
|---|---|---|
| catalog.sqlite | REBUILDABLE_DERIVED | 仅路径/策略；权威仍 Canonical；不走 ordinary forward migration |
| user.sqlite | MIGRATABLE_USER_ASSET | 设置表与迁移历史，真实 001_create_settings |
| records.sqlite | NEVER_DESTRUCTIVE_RECORD_ASSET | 仅路径/策略；不创建文件/业务表，不执行破坏迁移 |

迁移历史记录 schema_version、migration_id、checksum、applied_at_utc、applied_by_app_version。事务内执行与登记；已应用 checksum 不同或未知版本明确报错，不能悄悄重建用户库。旧 SqliteProjectRepository/SqliteStandardRepository 保留为 DEPRECATED / NOT_SHIPPED / NOT_WIRED，不装配。

## 6. Settings Thin Slice

最小 get/set 字符串端口。SettingsService 仅接受 window.geometry、window.state、log.level、last.directory；校验日志级别。Qt 字节状态使用 base64 表示，仅为 presentation state。启动读取、关闭保存；重新启动恢复。数据库与日志路径可注入 TemporaryDirectory，测试不触及开发者 LocalAppData。

## 7. Logging Policy

外层初始化 console + rotating file logging，日志路径显式注入；从设置读取级别。Domain 不配 handler。安装 sys.excepthook 与 Qt message handler，异常保留 traceback；不记录完整企业输入。Logging != Record Audit。测试关闭 handler，避免文件锁与真实用户目录写入。

## 8. QA_BACKLOG Phase 2 Disposition

完整编号和处置同步到 QA_BACKLOG 的 Phase 2 处置表。034/035/036/037 CLOSE_IN_P2；022/024 PARTIAL_IN_P2；其余按实际职责 DEFER_TO_P3/P4/P8 或 KEEP_OPEN_FUTURE。延期不等于关闭；不为清空台账改业务算法或扩大范围。

## 9. Known Regression Baseline Mechanism

起点 Windows Core run 36970415483，full-suite job 110723018633，artifact 11212005437：945 tests、9 failures、5 errors、3 skips。原始日志从该 CI 下载；tests/baselines/windows_full_suite_known.json 保存 source master SHA、Python 版本和全部编号。比较实际 unittest 结果的 ID 与类型，不只计数。既有失败/错误继续存在允许；已修复提示收紧；新增失败/错误/skip 或 failure→error 恶化失败。已知 error 改为 failure 属改善但仍记录。缺失测试不得当已修复；发现未执行基线编号失败。原始结果与比较报告均上传；比较器为 Required/Gating。

## 10. Exit Gate

G01～G04 证据完整，正式 Python 3.12 测试与比较门禁通过，受保护资源字节不变，旧业务入口保持，Qt 仅 settings 切片。记录真实 pass/fail/error/skip/not_run，不把已知全量失败报为全量 PASS。执行完成只写 Phase 2 = EXECUTION_COMPLETE、next = READY_FOR_INDEPENDENT_ACCEPTANCE；push、创建 PR、不合并，停止等待独立验收，不启动 Phase 3。
