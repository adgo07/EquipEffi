# Phase 2 执行报告

状态：EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE。不是 Phase 2 PASS；不合并、不发布、不进入 Phase 3。

## 1. 基线与平台预检查

- start master SHA：78831af1778255e1b19a904e9135d56a9672eaf2；真实 fetch、checkout master、pull --ff-only 后核对 origin 为 adgo07/EquipEffi，默认分支 master。
- final executable head SHA：0a950064baca6767b56586c64bbdc37708220b0f。完整交付含报告/治理提交的 final head SHA 记录于 PR description 和最终交接（报告不能包含自身提交哈希）。
- 本机正式解释器：G:\Python Project\EquipEffi\.venv\Scripts\python.exe；3.12.14 (main, Sep  1 2026, 14:17:39) [MSC v.1944 64 bit (AMD64)]；x64。
- 实际 Qt：PySide6 6.11.2（optional desktop）；原 tkinterdnd2 依赖保留；包版本仍 0.2.1，没有正式版本发布。
- platform-lock：中央 ee5feb0cc34dbd99790500fadd0c4c932e202a20；未升级；按此 SHA 读 Architecture V2.1 FROZEN 与 Numeric v1 FROZEN。
- ACTIVE 指南：中央 main@4516e204ab20ca61c5931a46c0b28d1c06459727 的 GUIDE_INDEX / PRODUCT_DELIVERY_POLICY / UI_DESIGN_GUIDELINES。
- MUST：核心与 UI/SQL 隔离，外层装配，UI state 与 Workspace 分离，保护 Golden/Conformance，中文优先。MUST NOT：静默数值改变、复制评价器、升级锁、将 DRAFT 当 Frozen、自动 Phase PASS。
- 冲突：034/035 LOCAL DEFECT 已修；Pump Decimal50 ALLOWED PROJECT DIFFERENCE 保留；没有新增 REGISTERED DEVIATION / CENTRAL CONTRACT GAP；不需改中央 Contract。
- Standard Issues 台账已读；EQP-STD-GB19762-001 与本 settings 切片无业务关联，不改变既有标准解释/as_of。Knowledge capture：无。

## 2. 最终范围与实际 diff

权威执行设计：[docs/31_Phase 2 最小正式工程底座.md](docs/31_Phase%202%20最小正式工程底座.md)。Qt 唯一 Application 链是 SettingsService → SettingsRepository → SqliteSettingsRepository。Phase 2 不等于完整离心泵产品、chemical 支持、Record、Excel、transformer 或发布。

实际代码：bootstrap 移到外层 composition；旧 CLI/Tk/API 引用同步；新增 settings 端口与服务、AppDataPaths、user migration、SQLite settings、日志配置和实现、Qt app/shell/navigation/pages/tokens、--qt optional 入口；旧 SQLite 空桩只加 DEPRECATED/NOT_SHIPPED/NOT_WIRED。新增 AST/集成/Qt/Golden 回放/比较器测试、两个 CI workflow 门禁与 exact baseline JSON；治理状态与本报告同步。没有 Domain、evaluation_service/facade、Canonical、Golden 文件 diff。

复核命令：`git diff --stat 78831af1778255e1b19a904e9135d56a9672eaf2`；`git diff --check 78831af1778255e1b19a904e9135d56a9672eaf2`；PR Files changed 为完整逐文件 diff。

## 3. G01 架构证据

正式外层 composition 负责 Infrastructure/Application/Presentation wiring；Application 不再装配外层，bootstrap 删除且全仓运行引用迁移。AST 遍历 Import/ImportFrom，解析相对导入，检查 Domain/Application 禁止外层、PySide6、sqlite3、openpyxl、tkinter；Qt 禁止 Infrastructure/Domain/API/evaluation 链。负例测试证明注释不触发、相对导入会检测。

`test_composition` 证明 core 无模板加载、预期 OOXML/资源/OS/XML 错误 WARNING + fallback、未知 RuntimeError 传播。未重构 V4 或改算法。architecture/metadata/application/core 598 tests PASS（18.246s）；最初装配/CLI/API组171 PASS。

## 4. G02 设置、迁移与日志证据

user.sqlite 两张表仅 settings / migration_history。001_create_settings 首启执行；历史包含 schema_version/migration_id/checksum/applied_at_utc/applied_by_app_version。再启动历史与既有设置不变；checksum mismatch、未来版本、错误 SQL、对 catalog/records 使用 user runner 都被拒绝；失败前向迁移事务回滚；所有连接显式 close，Windows 文件锁测试清理正常。

AppDataPaths 默认解析在 Infrastructure，可注入 TemporaryDirectory；tests 无开发者 LocalAppData 写入。SettingsService 只收 window.geometry/window.state/log.level/last.directory，业务键拒绝。catalog REBUILDABLE_DERIVED，不 forward migrate；records NEVER_DESTRUCTIVE_RECORD_ASSET，不创建业务表。两个旧仓储未被 composition 实例化。

LoggingConfig 路径可注入；console + rotating file，级别来自设置，traceback 可查；sys.excepthook、Qt message handler 接入并在退出恢复。日志测试验证过滤、轮转、异常堆栈、重复初始化释放 handler。Logging != Record Audit；无完整企业输入记录。设置7项、日志3项，全部 PASS。

## 5. G03 Qt 和跨启动证据

--qt 启动明确 optional Qt；--gui 继续旧 Tk。五页：首页/标准库/新建分析/分析记录/设置，全部显示“尚未在 Phase 2 实现”；没有泵输入、评价日期、grade/formula 等业务字段。Token 只是语义尺寸起点。

Qt 单窗口测试验证导航、保存恢复、坏设置警告、保存失败拒绝关闭并记录 traceback、Qt warning 入日志、CLI route 不构造业务 API。独立 Python 进程 write → restore → entry，通过真实 QApplication/窗口/event loop/QTimer/关闭/exit=0；窗口 640×480 恢复、window state 字节一致，log level/last directory 保留，外层启动后 excepthook 恢复。使用 QT_QPA_PLATFORM=offscreen，不需要显示器。

真实完整 Qt+settings+logging+composition+比较器+18批准回放组：30 tests PASS（3.872s）。offscreen 虚拟屏幕会限制超屏幕宽度，因此恢复测试采用屏幕可容纳尺寸；没有以截图代替行为测试。

## 6. G04 真实 Windows 基线与比较机制

起点 Windows CI：[run 36970415483](https://github.com/adgo07/EquipEffi/actions/runs/36970415483)，job110723018633、artifact11212005437。原始日志下载核对，Python3.12.10，945 run / 928 pass / 9 fail / 5 error / 3 skip。全部已知 ID 固定于 tests/baselines/windows_full_suite_known.json，未手写数量代替取证。

比较器依据 unittest TestResult 与 executed_ids；已知失败允许，修复可收紧，但缺失测试不当修复；新增 failure/error/skip、failure→error、unexpectedSuccess/expectedFailure 隐藏均使 gate FAIL，9 个负例/规则测试 PASS。Windows Core 中设置/迁移/日志/Qt/架构/核心/全量比较/compile/whitespace 均 gating，Pump Conformance 继续 gating。原始全量 nongating job 保留真实日志，不能据 workflow green 宣称 raw full suite PASS。

本机最终真实：975 run / 968 pass / 3 failure / 1 error / 3 skip；236.203s；expected_fail=0，unexpected_success=0。比较 gate PASS，new_failures=[]、new_errors=[]、unexpected_skips=[]、worsened=[]、missing_baseline_tests=[]。

本机有10个 Windows起点已知问题未重现，仅提示收紧候选，不能凭本机就宣称 Windows 问题修复；基线未擅自收紧。最终 GitHub Windows CI 已核对，详见第11节。

既有3失败：V4 reader copied-row、V4 writer1500rows、writer locked-results；1错误：release audit source_and_bundled_wheel；3跳过：未构建 release wheel 的 portable bundle。保持 QA-P0-001/002 与 QA-P1-003，不扩范围修复。

## 7. Pump / Numeric / Golden 证据

独立 Pump/Numeric/Golden9模块：59 tests PASS（3.097s）；run_qzc_n01_b_pilot exit0（T-delta=2级，T=1级，T+delta=1级，epsilon_used=false）；validate_phase1_contracts exit0、候选26+3 errors0、approval-review18 errors0、open_evidence_flags0。额外正式 Approved Golden 0.4 直接回放18子案例 PASS：状态、等级、问题码、full-value派生值、表行与阈值一致。

外部原 PDF 未提供，此次正式命令显式 --skip-external-evidence：历史25处引用、候选26+3、review18 的外部字节核查 not_run；仓库结构/hash/provenance 验证已执行。负例3个预期错误被检测；这不是3个测试失败。Golden0.1历史7例、0.3候选26、replacement3、批准0.4共18的字节/来源均未修改。

## 8. QA 处置

共51项起点 target_phase 包含2（含1/2组合）的 OPEN/VERIFY 项：034/035/036/037 CLOSED；022/024 PARTIAL_IN_P2 保持OPEN；其他 DEFER_TO_P3/P4/P8 或 KEEP_OPEN_FUTURE。完整编号、目标和决定见 QA_BACKLOG 处置表。没有为了清空 Phase2 而关闭 evaluator、Excel、日期、性能、安全或打包风险。

## 9. 全部正式检查汇总

| 检查 | Python | pass/fail/error/skip/not_run | 证据 |
|---|---|---|---|
| AST+metadata+existing application/core |3.12.14|598/0/0/0/0|core-tests.log|
| settings/migration/logging/composition/Qt/comparator/Approved replay |3.12.14|30/0/0/0/0|foundation-tests.log|
| Pump Conformance/Numeric/Golden modules |3.12.14|59/0/0/0/0|pump-tests.log|
| 18 Approved Golden direct replay |3.12.14|18子案例/0/0/0/0|test_phase2_approved_golden|
| full suite |3.12.14|968/3/1/3/0|final-full/full_suite.log + actual.json|
| full comparator |3.12.14|PASS；无新增问题|final-full/comparison.json|
| nonlinear reference runner |3.12.14|exit0|pump-execution-evidence.json|
| repository contracts / negative probes |3.12.14|exit0；外部字节not_run明确记录|contracts.log|
| compileall src tools tests |3.12.14|exit0|本次命令实测|
| git diff --check |N/A|exit0|本次命令实测|

本机原始日志在被忽略的 _codex/phase2；Windows CI 上传 full_suite.log、actual.json、comparison.json，供独立验收重新执行。同一测试跨组重复运行不累加为不同测试数量。

## 10. 严格范围核对

| 问题 | 答案 |
|---|---|
| Pump algorithm changed? |NO|
| Golden changed? |NO|
| Canonical changed? |NO|
| Pump Numeric Profile / platform-lock changed? |NO|
| pump_chemical support changed? |NO|
| Record schema implemented? |NO|
| DeviceDraft/Workspace/项目草稿 implemented? |NO|
| Excel implemented? |NO|
| Transformer developed? |NO|
| as_of 产品口径 changed? |NO|
| Default GUI switched? |NO|
| Phase2 self-declared PASS? |NO|
| Phase3 started / PR merged / released? |NO|

50 个重点 protected文件规范文本 SHA256 与 start master 相同；git diff 对全部 Domain/resources/specs/lock/PLATFORM_BASELINE/evaluation_service/evaluation_facade 为空。BASELINE 已记录关键资源起终同哈希。既有 docs/planning/ 未跟踪且未修改/提交；没有覆盖标准、模板、用户工作簿或发布产物。

退出状态为 READY_FOR_INDEPENDENT_ACCEPTANCE。独立验收前本线程停止，不自动推进。

## 11. GitHub Windows CI 正式证据补记

已执行提交 6b6dc8b6a02a6b41f0467e4f15769655b4423742（含执行报告/治理收口）；PR #10 的当前完整交付 SHA 由 PR description 固定，后续仅补记此 CI 证据，无代码变化。

- Windows Core [run36980446262](https://github.com/adgo07/EquipEffi/actions/runs/36980446262)：architecture/metadata、application/core、settings/migration/logging/Qt offscreen、full-suite comparator、compile、whitespace、package smoke 均 SUCCESS。
- Pump Conformance [run36980446377](https://github.com/adgo07/EquipEffi/actions/runs/36980446377)：Numeric锁一致性、非线性参考过程、边界/规则、批准Golden、仓库契约与API均 SUCCESS。
- 正式远端解释器 C:\hostedtoolcache\windows\Python\3.12.10\x64\python.exe，CPython3.12.10 x64；实际 PySide6 6.11.2。
- Required comparator 实际全量975 run / 958 pass / 9 fail / 5 error / 3 skip；raw_suite_success=false，comparison gate=PASS；new_failures/new_errors/worsened_failure_to_error/unexpected_skips/missing_baseline_tests 均空。远端已知问题未减少，不据本机10项未重现就收紧 Windows 基线。
- 原始 nongating job 独立重跑975项，同样9失败/5错误/3跳过（162.889s）；保持真实失败展示，没有隐藏或宣告 full-suite PASS。
- comparison证据 artifact11215004326：full_suite.log、actual.json、comparison.json 已下载核对；原始证据 artifact11215128945。
- 该 PR 初始实际 diff：45 files，1369 additions / 186 deletions；后续只有报告、治理指针补记，完整最终 diff 以 PR Files changed 为准。

上述是执行和回归证据，不替代独立验收，不宣布 Phase 2 PASS。最终提交保持 PR OPEN / UNMERGED。
