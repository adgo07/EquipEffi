# EquipEffi QA_BACKLOG

本页仅登记当前仍需跟踪的工程风险与已登记偏差；详细历史处置不在这里重复归档。

**当前状态：** Phase 1–7 保持已记录的独立验收状态；Phase 8 为 `EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE`，不得自行标为 PASS。Phase 0B = `NOT_EXECUTED`；当前无获准的 Phase 1 Hotfix。

**本轮退役说明：** 旧 API / JSON / JSONL / Web / Android / V4 执行链已退出。仅依赖这些执行表面的缺陷条目从当前台账移除，因为该路径不再属于当前产品；这不代表旧业务算法已修复、复核或获得正确性认证。非泵 Calculator 候选与数值断言、完整设备元数据、`domain/devices` 候选目录、`config/settings.py`、历史记录及标准证据继续保留。

OPEN / VERIFY / REGISTERED_DEVIATION 都按原状态保留，不自动授权代码修改。标准解释、Canonical、Approved Golden、Frozen Contract、历史 Record 与数据库语义不在本轮退役中变更。

## 当前风险与偏差

### QA-TR-004：公共页面仍只呈现离心泵信息（CLOSED，2026-10-23）

Owner在普通目录验收成功后指出首页仅展示泵标准和“开始新的离心泵分析”。核实HomePage只接收泵服务，未接通变压器概览；新建分析页已按设备分别装配服务。修复限首页入口、标准概览和确定设备的导航，复用现有共享历史记录，不重构业务壳、不改变标准解释、支持状态或数据库。补主页到泵/变压器实际表单的切换回归及双标准显示核验。

已从两个真实服务显示标准概览，增加变压器入口；两个按钮显式携带自己的标准号，避免沿用上次选择的设备。真实MainWindow的泵→变压器→泵回归及双标准显示通过，Qt/产品壳相关73项通过。1000×720、640×480离屏检查无文字或按钮截断；离屏检查不冒充原生包人工操作。随后公共页面检查发现设置/关于同类遗漏，已按真实服务补充双标准和变压器状态，去除运行信息中的“草稿”残留；不改变共享历史存储。双标准信息增多后发现640×480裁切，已补纵向滚动、长路径换行及刷新高度；设置页7项、产品壳与变压器Qt共75项通过，小窗及正常窗口图像已复核。

### QA-TR-003：合法命名空间前缀工作簿的结果 Sheet 定位（CLOSED，2026-10-23）

PR31 最终验收发现，artifact-tool 导出的合法 XLSX 可被 `UnifiedWorkbookReader` 读取，但 `UnifiedResultWorkbookWriter` 写回时报告找不到目标 Sheet。根因为 `xl/workbook.xml` 使用带 `x:` 前缀的 SpreadsheetML 元素（如 `<x:sheet>`），公共 `_sheet_target` 原正则仅识别无前缀标签。现改为按标准 QName 解析 SpreadsheetML `sheet`、Office Document Relationships `r:id` 与 Package Relationships `Relationship`，同名扩展标签不会抢先命中。`test_pr31_output_integrity.py` 定向回归 8/8 通过，覆盖前缀 XML、同名扩展、泵与变压器同次写回及非目标 ZIP 部件逐字节保持；真实 artifact-tool 验收工作簿通过 Reader 和 Writer，59 个非目标 ZIP 部件保持字节一致；完整批量服务复验为2行、5台（1级3台、不在范围2台），历史错误为空。范围仅为 OOXML 目标部件定位，不改变标准业务、模板、数据库或输入内容。

### QA-TR-002：PR31 独立审查修复（CLOSED，2026-10-23）

以58ba70e4为复现基线：核实明确范围排除被缺项遮蔽、逐行查表依据投影缺失、模板阻抗说明及损耗小数格式、清空输入残留旧结果、50Hz适用提示、变压器合并单元格检查。修复限既有冻结规则与25列契约，不修改冻结件/Golden/数据库；先确认足够排除的证据再调整判断顺序，表15等仍按真实分支约束。共同清空行缺陷同时覆盖泵输出，不改泵业务算法/正式模板。旧历史不追溯改写。六项修复及预置第14行样式补齐已完成；固定c303060e的Windows CI 1130项全通过，原生包独立目录启动自检与资源审计通过。证据与四项处理决定见[PR31修复记录](docs/standards/gb20052_2024/PR31_REVIEW_FIXES.md)。本条按工程缺陷修复关闭，不代替QA-TR-001正式支持与真实窗口验收。

### QA-TR-001：GB20052 V2.1 接入（OPEN，Owner已授权实施）

依据为冻结主映射与35表校对册、EQP-STD-GB20052-001～008既有决定及Owner确认的25列输入方案。当前候选transformer实现不等同于冻结V2.1；本次从冻结数据单向派生新运行数据，完善选表/分组/插值/双损耗判级及Qt/Excel同核接入。Owner于2026-10-23明确T02非630kVA额定阻抗仅留存、不影响判级；该决定已记入EQP-STD-GB20052-002及集成设计，并由500/565/715/800kVA输入不变性测试验证。影响范围限下一版本变压器及必要多Sheet编排；泵算法、Golden、Sheet与共享配置依赖不变。具体案例/前后差异、验证计数和兼容结果在实施报告记录。不得以待测代码生成权威预期；不修改冻结源、已批准Golden、数据库迁移或中央锁。仅本条登记不代表验收通过或SUPPORTED。

| issue_id | 原状态 | 当前表面 / 目标 | 当前风险与证据边界 |
|---|---|---|---|
| QA-RET-001 | CLOSED | Qt 批量评价验收 | Owner 实测结果 Workbook 正常但完成文案残留、批次历史不可见、打开 WPS 崩溃及文件夹 ShellExecute error 5。已修复完成/失败状态与可复制的打开失败提示；接通既有 batch_record 只读历史、加载更多；真实旧批次 2 行/4台/1级可见且原库哈希不变。补充 frozen Windows 外部启动的 DLL/PATH/Qt 插件路径清理并恢复（PyInstaller 官方说明），69 项集成定向检查通过。Owner 在普通用户目录正常解压 ZIP 后反馈功能正常，完成本机交互复验；不能将之前受限构建目录的失败归为 DLL 污染已证实。无标准解释、算法、Golden 或数据库 schema 变更。 |
| QA-RET-002 | CLOSED | 原生包启动 | Owner 反馈双击仅出现黑框；33e7be11 包在诊断进程默认数据目录复现日志文件 PermissionError，进入 Qt 前退出，同包在隔离数据目录可创建主窗口。修复日志目录/文件不可写时仅降级控制台日志，数据库异常仍原样处理，不改 ACL 或历史数据。日志与装配定向测试 8/8 通过；94bb8330 原生包在相同默认目录保留 PermissionError 警告后持续运行，Computer Use 读到首页、六个导航项及既有历史记录；Owner 双击和外部打开仍待复验。Owner 交互诊断确认父进程为正常用户 Medium；只读进程令牌检查确认其启动的 EXE 进程为 Low，文件 icacls 同时显示继承的 Low Mandatory Level。Windows 按用户与可执行文件完整性级别的较低值创建进程；此证据解释普通用户目录的写入被拒。直接运行受限构建目录 EXE 不构成正常安装验收。下一步由 Owner 在普通用户目录从 ZIP 正常解压后复验，不改 ACL、不提升管理员权限；Owner 按普通目录解压 ZIP 后反馈正常，本机交互复验通过。 |
| QA-RET-003 | CLOSED | Windows 桌面打包 | Owner 确认正常解压后功能正常，但运行时出现控制台黑框；改为 Windows windowed 打包，并将构建资源诊断写入显式状态文件以兼容无 stdout 的环境。ee64e131 新包 PE Subsystem=2（Windows GUI），实际启动并由窗口工具读取首页；19/19 定向测试及无 stdout/stderr 的 Qt 启停检查通过，原生 status/资源审计通过。主会话以 GUI 子系统和实际启动证据完成此项验收；Owner 授权最终核查后合并。无业务规则或数据库变更。 |
| QA-RET-004 | CLOSED | Qt 批量线程收尾 | 最终复核复现既有时序缺陷（332d79c 已存在）：结果回调恢复按钮后、旧线程退出前重跑，旧收尾回调会清掉新线程引用。修复限定为旧线程引用存在时拒绝重入，结果提示立即更新，线程退出清理后才恢复按钮；真实 HeldThread 回归及主会话批量后台/反馈/历史/外部打开/入口/打包共37项检查通过；不改变评价、结果文件或数据库语义。 |
| QA-P1-006 | OPEN | V1_RUNTIME / Future | 资源包标为 `active` 只代表可加载，不等于其来源、范围、Golden 和支持状态均已验收；具体支持范围仍以 `V1_SCOPE.md` 为准。 |
| QA-AUD-001 | OPEN | NOT_SHIPPED / Future | `domain/devices/` 中的候选壳与 `domain/evaluation` 并存；保留供后续边界/调用证据判断，本轮不据此删除专业候选。 |
| QA-AUD-002 | OPEN | V1_RUNTIME / Future | `device_evaluators.py` 兼容门面与延迟反向导入仍增加维护和调用理解成本；保留其现有运行依赖。 |
| QA-AUD-003 | OPEN | V1_RUNTIME / Future | 电机 evaluator 使用字符串 `getattr` 调用 helper；重命名可能静默失效，需静态契约前继续保留回归。 |
| QA-AUD-005 | OPEN | V1_RUNTIME / Future | 公共设备类型、内部 Profile 与旧风机入口的路由可读性仍有结构债务；当前无错误结论证据，不合并映射。 |
| QA-AUD-006 | OPEN | V1_RUNTIME / Future | `EvaluationResult` 仍混合结果、轨迹、淘汰与质量信息；职责收敛属于独立重构，不在本轮改变契约。 |
| QA-AUD-007 | OPEN | V1_RUNTIME / Future | `metadata.py` 体量较大且混合枚举、字段映射、展示元数据与 Profile 构建；保留非泵专业字段和既有外部映射值。 |
| QA-AUD-008 | OPEN | V1_RUNTIME / Future | `device_specs.py` 导入时会就地修改 `DEVICE_SPECS`；目前作为结构风险跟踪，不扩大为规则或算法重写。 |
| QA-AUD-009 | OPEN | V1_RUNTIME / Future | 标准、字段与示例仍有多处 Python 表达，存在数据漂移风险；Canonical 仍是标准数据权威，不因台账而静默删除或改写业务数据。 |
| QA-AUD-010 | VERIFY | V1_RUNTIME / VERIFY_BEFORE_PHASE9 | **P0：** `evaluators/shared.py:_interval_hit` 的边界判定仍需标准原文与跨案例覆盖。既有 12 个开闭端点 probe 未发现错误，但不足以证明所有标准 / Golden 场景安全；无 Hotfix 授权。 |
| QA-AUD-024 | OPEN | V1_RUNTIME / Future | Application ports 的 Protocol、实现接线和导出约定尚未全部统一；保留正式批量链使用的现有端口。 |
| QA-AUD-025 | OPEN | DEV_ONLY / Future | `config/settings.py` 仍保留，但目前仅有架构边界测试读取、无运行时调用；继续跟踪该配置入口的实际用途，不把它与已退役的 V4 模板审计混为一项。 |
| QA-AUD-032 | OPEN | DEV_ONLY / Future | `src/equipeffi/__init__.py`、`pyproject.toml` 与构建入口仍有版本声明分散，可能造成追溯漂移。 |
| QA-AUD-038 | OPEN | V1_RUNTIME / Future | Writer / JSON repository 的异常路径可能丢失底层根因；诊断质量风险，不把执行错误转成业务不可判定。 |
| QA-AUD-041 | OPEN | V1_RUNTIME / VERIFY_BEFORE_PHASE9 | `json_repository.py` 缺键可能抛裸 `KeyError`，缺文件语义与线性查找仍需发布前给出结论；现有发布审计检查只构成部分缓解。 |
| QA-AUD-042 | OPEN | V1_RUNTIME / VERIFY_BEFORE_PHASE9 | V6 批量 Workbook 的高峰内存历史测量需要在最终发布候选复测。基线记录的 10,000 行结果曾达 952.0 MB、266.357 / 287.861 s；固定参考为 [332d79c](https://github.com/adgo07/EquipEffi/commit/332d79c7d999feb4047c920ecb4359655bf9440e)。旧测量不代替当前候选测量。 |
| QA-AUD-047 | OPEN | DEV_ONLY / Future | 仓库发布文档仍缺正式 LICENSE / CHANGELOG 或存在交接式说明，作为发布与维护资料风险跟踪。 |
| QA-AUD-049 | OPEN | DEV_ONLY / Future | `tools/extract_*.py` 中仍有本机 G 盘路径，换环境可能误读本地资料；通用人工校对工具未因 V4 退役而自动删除。 |
| QA-AUD-053 | OPEN | DEV_ONLY / Future | `application/ports/__init__.py` 的导出策略与子端口模块不完全一致；保留具体差异待统一。 |
| QA-P3-002 | OPEN | V1_RUNTIME / 标准映射 | Canonical pack 目前提供 `effective_date`，未提供 `superseded_by` / 废止日期等生命周期字段；软件不应私造标准生命周期规则。补齐须走标准映射流程。 |
| QA-P5-005 | OPEN | Phase 9 | 正式安装包、代码签名与正式发布产物尚未完成；本轮不宣称可发布。 |
| QA-P7-001 | REGISTERED_DEVIATION | RECORD_VERSION_FIELDS | 存量历史记录中的版本字段不一定能追溯到真实源指纹；当前泵版本指纹由 pump_calculator_version.py 提供。不得为历史记录编造或回填版本，沿用既有降级展示。 |
| QA-P7-002 | REGISTERED_DEVIATION | LEGACY_RECORD_BASIS | 较早历史记录缺少完整标准依据字段。不得回填当前版本、重算或追溯改写；按既有降级文案展示。 |
| QA-P1-008 | OPEN | V1_RUNTIME / Owner 决定是否进入 M4 | `get_pack` 每次仍对整包 dict 执行 `deepcopy`；10,000 行实测约 5.759 s、约占端到端 13.6%。在审计调用方不修改返回值之前不得移除复制；固定性能参考同 [332d79c](https://github.com/adgo07/EquipEffi/commit/332d79c7d999feb4047c920ecb4359655bf9440e)。 |

## 电动机接入实施（2026-10-25）

| 编号 | 状态 | 范围 | 依据与验收 |
|---|---|---|---|
| QA-MOTOR-001 | OPEN | GB18613六表唯一内核 | Owner已授权按PR33设计实施；A.2映射/A.1源表不改，替换旧低压链；BC-01—26、数值Conformance及源格核验。效率1～100是Owner防呆决定，不是标准解释变化。 |
| QA-MOTOR-002 | OPEN | Qt/Excel/历史闭环 | V6.2保留20列，保护泵/变压器；旧模板说明固定区及再导入、混合批次、状态投影、候选入口及原生验收。实现前后证据随实施报告记录，不提前宣布SUPPORTED。 |
| QA-MOTOR-003 | OPEN | 人工验收反馈 | 2026-10-25 Owner要求批次总结按设备台数及各结论分布显示，数据行数仅辅助；复用已有summary.sheets快照，不改数据库。后续明确频率允许文本、取消极数下拉并允许正偶数；范围判定与输入校验分开，见EQP-STD-GB18613-009。WPS修订版仍待交互复验。 |

## P0 / Hotfix 状态

当前仍列为 P0 的活动项只有 `QA-AUD-010`，状态 `VERIFY`。未登记获准 Hotfix；该项需补足标准原文与 Golden 证据后再判断是否需要最小修复。

## 退役与历史记录边界

本轮从当前台账移除仅对应已删除旧入口、V4 读写/校验链、Web/Android 上传与旧 JSON/JSONL 服务的问题，以及重复的 Phase 处置、旧 blocker 和已结束复验流水。退役表示不再维护该表面，不表示历史候选算法、非泵计算器、标准数据或旧记录已被重新计算或认证。Approved Golden、Canonical、冻结标准资产及历史记录保持原样。
