# EquipEffi 仓库检查报告

> 历史检查报告：以下发现与数字仅对应 `2c7807f`。后续 PR #24 已实施部分修复，PR #25 已完成装配去重；当前完成情况以 [首批验收](SIMPLIFICATION_ACCEPTANCE_20261019.md)、[第二批验收](SIMPLIFICATION_BATCH2_20261021.md)及 QA_BACKLOG 为准。不得将本报告的旧缺陷描述当成当前未修复结论。

检查日期：2026年10月18日。对象：王玮及后续负责 EquipEffi 的 AI 执行者。

## 一 总体结论

**建议保留现有计算底座，先收敛标准身份、批准依据和公共应用入口，再接入变压器并重构 UI。仓库需要有针对性的整理，不需要推倒重写。**

现有项目已建立 Domain、Application、Infrastructure 分层，已规定标准原文、技术判断和软件决定分别记录，也已明确单人轻治理。正式 Qt 和 V6 Excel 的离心泵计算已经走同一条服务链。主要缺口在于：正式产品入口仍以离心泵组织，专业字段与输出名称仍在多处维护，旧 API 与正式表面不同，Word 报告尚未形成正式能力。

本次复现了三个具体行为问题：标准号与实际计算器可以错配并进入记录；Excel 表头单位改动后仍按原单位计算；仅改变阈值显示名称就可能使 Excel 阈值列漏写。另复现了标准资源缺失被误报为用户输入错误。这些问题应优先于大规模 UI 改造处理。

### 检查基线

| 对象 | 本次使用的准确基线 |
|---|---|
| EquipEffi 默认主分支 | `master`，不是 `main`；仓库不存在 `main` 分支 |
| EquipEffi 提交 | `2c7807f32ef08d18554014328efd4ceaa356726f`，2026年10月13日合并 PR 22 |
| 中央当前合并版本 | `854b544563260f9e79c73e714c85f6589e0f19b3`，用于 ACTIVE 指南 |
| 本仓已采用的中央锁 | `ee5feb0cc34dbd99790500fadd0c4c932e202a20`，用于 Frozen Contract |
| 文件盘点 | 544 个 Git 跟踪文件，共 11,765,637 字节，约 11.22 MiB，不含 Git 历史 |
| 标准资产盘点 | manifest 含 17 个内部 Profile 条目、16 个标准号、12 个 JSON 源文件；标准档案总入口目前只列泵和变压器 |

上述数字不能解释为已正式支持 16 个标准。当前正式范围仍是 GB 19762—2025 清水泵与石油化工泵；变压器映射与35表虽已批准冻结，软件状态仍为 POST_V1 / NOT_IN_RELEASE_SCOPE。映射定稿、数据可加载、计算器存在和正式支持是不同事实。[基线提交](https://github.com/adgo07/EquipEffi/commit/2c7807f32ef08d18554014328efd4ceaa356726f)；[范围与锁定依据](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/TASK_STATE.md#L78-L113)。

本报告检查的是上述生产代码基线。本次文档提交只补充检查结论、映射权威与统一来源条款，并修正 AGENTS 的活跃 UI 阅读入口；它不构成产品阶段验收、正式发布或标准支持状态提升。

### 问题优先级总览

| 编号 | 发现 | 优先级 | 处理时点 |
|---|---|---|---|
| F01 | 核心标准身份可错配，缺少多版本选择 | P1 | 第二标准接入前 |
| F02 | Excel 导入忽略表头单位变化 | P1 | 下一次批量输入维护优先修复 |
| F03 | 显示名称充当结果键，改名称可能漏写结果 | P1 | UI 与输出字段整理前 |
| F04 | 正式应用用例仍以泵为中心，旧 API 契约不同 | P1 | 与最小解耦一起处理 |
| F05 | 批准映射与运行资产关联不足，计算器版本不是真正版本 | P1 | 与标准身份一起处理 |
| F06 | 标准资源故障被误归为输入非法 | P1 | 定向修复即可 |
| F07 | Word 正式输出尚未闭环 | P2 | 统一结果稳定后接入 |
| F08 | 无用包装、未装配骨架和历史工具混在活跃目录 | P2 | 分类后小批清理 |
| F09 | 当前说明、状态和 UI 指南入口过时 | P2 | 最先做轻量文档收口 |
| F10 | CI 绿色包含已知失败，部分测试重复执行 | P2 | 清理现有验证流程时 |
| F11 | 当前 UI 与家族方案仍有差距 | P2 | 公共入口稳定后落地 |
| F12 | 跨平台接口有基础，客户端和发行仍未完成 | P2 | 保留接口，按真实平台需求推进 |

P1 表示有具体结果风险或会被下一阶段放大的接口缺口，不表示所有现有泵结果错误；P2 表示维护、能力或交付缺口，不要求同时大规模重构。

## 二 已经做对的部分应继续保留

**映射与标准异常已有治理基础。** AGENTS 第7节和标准档案入口已经要求先登记疑点，分别写清标准事实、技术判断、Owner 软件决定，并追踪到规则与案例。变压器主映射和35表工作簿已被定义为不可拆分的冻结基准。本次重新计算两份文件的 SHA-256，与冻结清单一致，未发现字节漂移。[标准档案规则](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/docs/standards/README.md#L36-L85)；[冻结清单](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/docs/standards/gb20052_v21/GB20052_V21_FROZEN_BASELINE.md)。

**核心算法已经离开 GUI。** 多设备 evaluator 分文件组织，有17个内部工厂注册；正式批量服务复用离心泵分析服务，下层标准仓库和 Calculator 一致。现有问题主要出在公共应用入口、字段契约和适配器，而非 Excel 还在独立重算正式泵等级。[计算器注册](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/domain/evaluation/evaluator_registry.py)；[正式服务装配](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/composition.py#L137-L219)。

**数值与历史追溯已有重要保护。** 泵保留 Decimal50、完整值判级、真实 Canonical 哈希和不可变历史快照。展示阈值虽然可为6位小数，但完整值仍在 calculation_trace.thresholds_internal 并进入快照；本次没有把展示投影误判为 ROUND6 业务比较或精度丢失。[内部值与显示值](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/application/services/centrifugal_pump_analysis_service.py#L1008-L1040)。

**单人轻治理已写入。** 普通范围内开发、修复、重构和文档维护无需反复确认；历史六关和多角色审批不再常态执行。应把这些规则执行得更简洁，而不是再建一套审批体系。[AGENTS 单人治理](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/AGENTS.md#L54-L74)。

## 三 具体发现与处理建议

### F01 核心标准身份可以错配并保存

**实际复现：** 给正式 CentrifugalPumpAnalysisService 传入合法清水泵参数，但将请求 standard_code 写成 GB 20052-2024。实际仍执行 GB 19762-2025 泵算法并得出1级；analyze_and_record 返回 RECORDED。记录顶层是变压器标准号，reference_snapshot 内却是离心泵标准号。探针只使用内存记录仓储，没有写真实用户数据库。

原因是请求允许任意标准字符串，执行时只按泵类别路由，结果又直接复制请求中的标准号。输入指纹和固化一致性检查没有包含标准身份。现有 Qt 和 V6 使用固定默认标准，因此不能据此断言现有界面普遍错标；但未来通用标准选择会直接遇到此风险。[请求与指纹 394至456行](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/application/services/centrifugal_pump_analysis_service.py#L394-L456)；[执行与结果 769至859行](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/application/services/centrifugal_pump_analysis_service.py#L769-L859)；[记录固化](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/application/services/centrifugal_pump_analysis_service.py#L1230-L1322)。

同一设备多个标准版本也尚未真正支持：JsonStandardRepository 以 device_type 为字典唯一键，重复条目会被后者覆盖；pack_id 参数只是检查当前唯一条目，不是版本选择。[加载索引 58至78行](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/infrastructure/standards/json_repository.py#L58-L78)。

**建议：** 通过标准号、标准版本及 Profile 选中一组明确的 Calculator 和数据包。结果、引用和记录身份均由实际选中对象派生；请求身份不匹配时明确拒绝。新记录冻结该身份，旧记录保持原貌。同一标准的新旧年份不能互相覆盖。

### F02 Excel 表头单位改变后仍按固定单位计算

**实际复现：** 在正式 V6 工作簿的临时副本中，仅把 G3 的“流量 m³/h”改为“流量 m³/s”，填写相同输入：流量100、扬程50、转速2900、效率90、单吸、级数1、数量1。两份工作簿均通过结构校验，Reader 均读为 flow=100，正式分析均返回 SUCCESS 和1级，阈值完全相同。

Reader 只校验表头第一行的中文名称子串，换行后的单位被截掉；随后直接将 flow 映射为固定单位的 QBEP。这是单位错配防护缺口，不是说仓库内置模板的单位写错。[Reader 132至147行](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/infrastructure/excel/pump_workbook_reader.py#L132-L147)；[批量请求投影](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/application/services/pump_batch_evaluation_service.py#L201-L230)。

**建议：** 字段定义统一提供稳定 ID、单位和批准别名。导入时校验实际列身份和单位；单位不兼容就指出具体列并拒绝，或只按已批准的换算规则转换。无需用整工作簿哈希锁住用户填写的文件，也不应新增复杂确认页面。

### F03 中文显示名称承担了机器字段键的职责

正式 PumpAnalysisResult.thresholds 的字典键是“1级能效效率限值（%）”等显示文本，Excel Writer 又硬编码同一文本查找。探针仅在内存将一级显示名称改成“一级能效效率限值（%）”：等级仍为1级，但 U 列待写值从79.786165变成 None，结果会静默漏写。[结果键生成](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/application/services/centrifugal_pump_analysis_service.py#L1008-L1018)；[Writer 键与读取](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/infrastructure/excel/pump_result_writer.py#L65-L170)。

字段定义也分散在新建分析页、记录页、Application 类别约束、Reader 列表、模板生成脚本和旧 metadata 中。新建页确有 Owner 批准的术语简化，不能擅自恢复旧名称；应该将这些批准的展示别名及适用表面统一登记。[新建页字段及批准注释](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/presentation/qt/pages/analysis.py#L61-L74)。

**建议：** 结果使用稳定 metric_id 或 threshold_id，显示名和单位作为元数据。GUI、Excel 和未来 Word 只绑定稳定 ID；改变批准的显示名称不能改变计算、字段定位或输出完整性。业务名称、单位、候选及含义的改变仍需遵循映射与已批准决定，不能当普通美化随意改写。

### F04 正式应用入口仍围绕泵 旧 API 使用另一份契约

正式 CentrifugalPumpAnalysisService 有1382行，包含标准目录、类别、字段约束、输入结果、计算、用户说明和记录操作。Qt Shell、分析页、批量页直接依赖该泵服务；标准库读模型也只提供一个泵标准。另一方面，JSON、JSONL、Web 仍由旧 EvaluationService、EvaluationFacade 和 ApplicationApi 装配。共用下层 evaluator 并不等于共用同一应用用例。[两条装配链](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/composition.py#L58-L94)；[正式泵装配](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/composition.py#L137-L219)。

本次真实调用 create_core_api().schema('centrifugal_pump')，得到以下差异。

| 字段 | 正式 Qt 与 V6 | 现有核心 API schema |
|---|---|---|
| 类别 | 8种正式泵型、其他类别、不确定类别 | 8种正式泵型、其他（请备注说明）；缺少不确定类别 |
| 吸入方式 | 单吸、双吸 | 还包含不适用、其他（请备注说明） |

这些差异位于兼容入口，不能归为当前正式 Qt 的错误；但后续安卓、小程序等若直接使用旧 schema，会继承另一套口径。[旧字段元数据](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/domain/evaluation/metadata.py#L141-L159)；[API schema](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/presentation/api/application_api.py#L408-L429)。

**建议：** 抽取最小公共分析入口，泵与变压器各自注册专用计算器。保留复杂标准的专属表单组件和算法，把标准选择、请求结果、错误分类、记录与导出公共化。不要复制一个同样巨大的 TransformerAnalysisService，也不必开发动态插件市场、微服务或万能公式语言。

### F05 批准依据与运行规则尚未形成完整关联

原标准、映射、Canonical、Golden 已有各自位置，但运行时 manifest 主要记录设备、包路径、状态、数据版本，没有完整关联当前批准映射修订、成套文件哈希和适用的软件决定。泵档案中的主映射仍是导航，分支正文保留早期候选状态、旧运行路径和后续替代说明；AI 需要跨多个文件拼接当前有效依据。页首已经说明历史性质，所以这不是“批准状态被撤销”，而是有效规则入口仍不够直接。[泵映射入口](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/docs/standards/gb19762_2025/STANDARD_MAPPING.md)；[运行清单](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/standard_manifest.json)。

另一个具体问题是 calculator_version 和 ruleset_version 目前都填 rule_profile，即 pump_water 或 pump_chemical。真实数据包哈希虽已保存，纯 Python 算法修改却不会因此产生新的计算器版本，记录难以准确定位所用实现。[版本字段赋值](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/application/services/centrifugal_pump_analysis_service.py#L769-L786)；[记录版本字段](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/application/services/centrifugal_pump_analysis_service.py#L1300-L1322)。

**建议：** 在现有标准入口和注册清单上补齐批准映射、配套数据、决定编号、规则版本及计算器版本的关联，不另建审批数据库。泵整理一份清楚的“当前有效依据”入口，历史修订保留。变压器继续成套使用冻结双文件，不能让旧 transformer.json 反过来替代它们。结果快照使用已有字段或 JSON 承载追溯信息，不为此新增历史表。

标准包哈希回答“当时用了哪份数据”，批准记录回答“哪些业务内容获准”，计算器版本回答“用了哪版算法”，三者各有用途；一个哈希不能自动证明原标准转录正确。

### F06 标准资源故障被误报为输入非法

故障注入把临时 manifest 指向不存在的 pump.json。Repository 返回 status=active 的空壳，正式服务随后把合法类别判成 CATEGORY_UNRESOLVED / INVALID_INPUT，提示“产品类别无法映射”，同时保留 support_status=SUPPORTED。该结果不可固化，本次真实仓库的 pump.json 也并未缺失；问题是错误归因。[缺文件分支](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/infrastructure/standards/json_repository.py#L97-L103)；[类别映射分支](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/domain/evaluation/evaluators/pump.py#L196-L203)。

**建议：** 已登记并激活的标准资源不存在或损坏时，加载边界抛出明确的系统资源错误。资料不足、不适用、无法唯一选表是业务结果；文件缺失和执行异常是系统失败。用一个定向回归保护即可。

### F07 Word 尚未形成正式报告输出

本次未发现运行中的正式 Word 导出器。ReportService 只汇总旧 EvaluationResult，生产链没有调用；ExcelReportExporter 等名字看似有能力的类实际是抛 FeatureNotEnabledError 的空桩。不能据类名或安装了 python-docx 认定 Word 已支持。[报告服务](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/application/services/report_service.py)；[未启用导出器](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/infrastructure/excel/report_exporter.py)。

**建议：** Word 从同一正式结果及冻结快照获取标准、输入、单位、适用性、计算结果、结论和必要来源说明；只负责排版，不重算、不再维护一份阈值与候选字典。用户项目或设备信息属于公共报告信息，可以与标准业务字段分开维护。

### F08 清理重点是无用层次和历史入口

文件总量约11.22 MiB，不能把问题简化为大文件太多。根目录27份 Markdown 约1.33 MiB，其中历史 HANDOFF_20260831.md 约736 KB；它们的主要成本是让 AI 反复读取过时状态，而非运行速度。另有零调用的转发服务、未装配的另一套设备注册骨架，以及仅用于历史取证的模板修复脚本。具体处置见第四节。

两个标注 NOT_SHIPPED 的 SQLite 空桩在本次临时构建的 wheel 中确实存在；这说明状态名称与发行内容不一致，不表示它们正在参与正式计算。模板 manifest 没有进入 wheel，但当前运行时使用 Python 中的模板身份常量，本次没有据此推断启动故障。[打包范围](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/pyproject.toml#L23-L32)；[SQLite 空桩](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/infrastructure/standards/sqlite_repository.py)。

### F09 活跃文档存在过时事实

README 仍描述 Tk、没有 Tk 时回退 Web、Excel 尚未执行；实际无参数、--gui、--qt 都进入 Qt，且已有 V6 批量页。AGENTS 和 UI_CURRENT_STATE_AUDIT 仍有“五页”描述，真实导航为六项。TASK_STATE 的 current_master 是前一任务开始时的提交，而当前整理 PR 已合并。[旧 README](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/README.md#L10-L103)；[真实入口](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/entrypoint.py#L102-L136)；[真实导航](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/presentation/qt/navigation.py#L20-L25)。

本仓活跃 UI 入口还指向中央 v0.1，中央当前 GUIDE_INDEX 已切换为 UI 指南 v0.2、产品家族规格 v0.1和验收清单 v0.1，并将旧 UI v0.1保留为历史。这会直接误导后续 AI。本次小型文档变更修正 AGENTS 的阅读路由；其他旧现状说明列为待收口项，不改写历史报告事实。[中央当前 UI 路由](https://github.com/adgo07/Qingzhou-contracts/blob/854b544563260f9e79c73e714c85f6589e0f19b3/docs/GUIDE_INDEX.md#L176-L195)。

### F10 CI 绿色并不表示所有测试通过

已读取对应检查基线的真实 Windows 日志，结果如下。

| 执行 | 实际结果 |
|---|---|
| Windows 显式架构与元数据测试 | 113条，全部通过 |
| Windows 完整 discover | 1526条：1510通过、9失败、4错误、3跳过 |
| 原始全量结果 | raw_suite_success=false，耗时811.755秒 |
| 已知失败比较器 | PASS，没有新增失败、错误、跳过或已知测试缺失 |
| Pump 专项工作流 | 7组共196条 unittest 全部通过；另有参考工具检查 |

[Windows 原始执行记录](https://github.com/adgo07/EquipEffi/actions/runs/38338535293/job/115104054471)；[Pump 执行记录](https://github.com/adgo07/EquipEffi/actions/runs/38338535265/job/115104054309)。

比较器确实按测试 ID 区分既有问题和新增退化，不是任意放行。不过已有一项 build_lock 测试在本次 Windows 日志中通过，仍留在允许失败清单；应结合稳定证据收紧。Pump 专项与全量中有重复测试，两个专项参考工具仍有独立用途。tests/contract 缺少 __init__.py，目前普通 discover 不包含它，不能在合并 CI 时误删显式执行步骤。[比较器](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/tools/check_windows_regressions.py#L27-L48)；[工作流](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/.github/workflows/windows-core.yml#L12-L103)。

仓内 Phase 8 和 Numeric adoption 仍有验收落档待办。这里说明的是仓库证据状态，不能据此断言从未在其他会话完成过验收。先归档已存在的结论，确实缺少证据时再限定范围补验，不重新执行全部历史流程。

### F11 当前 UI 尚未落实新的家族方案

现有窗口标题、首页和标准详情以离心泵为中心，首页侧栏常驻，导航仍叫“Excel导入”，记录列表与长详情同屏。中央最新家族规格已规定首页无侧栏、标准库优先、业务侧栏顶部 LOGO 与底部设置、统一 SVG、“表格导入”、标准详情单页分区和记录详情两页签。这些是后续 UI 重构的明确输入，不应误称违反 Frozen Numeric Contract。[当前 Shell](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/presentation/qt/shell.py#L40-L110)；[当前家族规格](https://github.com/adgo07/Qingzhou-contracts/blob/854b544563260f9e79c73e714c85f6589e0f19b3/docs/ui/UI_PRODUCT_FAMILY_SPEC_V0.1.md#L28-L49)。

记录页已有 SQL 筛选和加载更多，不应重复提出“只能查看最近100条”这一已不符合当前代码的问题。UI 改造应保留这些现成能力，只调整信息组织和视觉。[现有记录查询](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/presentation/qt/pages/records.py#L145-L223)。

### F12 跨平台有底座但尚非全平台产品

核心包无第三方必需依赖，Qt 和文档工具是可选依赖，平台路径主要在 Infrastructure；这是可保留的方向。Domain 的淘汰目录模块仍有资源读取，可在后续严格拆核时通过已存在的 entries 注入路径，把读取移出计算层。[依赖声明](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/pyproject.toml#L9-L21)；[淘汰目录加载](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/src/equipeffi/domain/evaluation/elimination.py#L43-L83)。

Android 目录是协议与演示工程骨架，不能据此宣称已有可离线运行正式算法的安卓产品。macOS 路径支持也不等于完成安装、打包和签名；iOS、鸿蒙、小程序尚未发现正式客户端实现。[Android 自述](https://github.com/adgo07/EquipEffi/blob/2c7807f32ef08d18554014328efd4ceaa356726f/android/README.md)。

此外，README 的裸 wheel 安装示例不会自动安装 desktop extra 中的 PySide6，直接启动 GUI 在干净环境缺依赖；发行工具还有 Tk 诊断残留。应在正式发行收口时修正，不应为了桌面方便给纯核心强加 Qt 依赖。

## 四 可以怎样清理仓库

以下是清理候选与处置边界，不是删除授权清单。实际清理时检查装配、命令入口、测试用途、发行内容和外部导入承诺；没有 Python import 不等于文件没用。

| 资产 | 现状 | 建议 |
|---|---|---|
| ImportService、CleaningService、IndicatorEngine | 仅转发或复制，未发现运行调用 | 优先待删候选；确认无外部接口承诺后删除 |
| EvaluationEngine | 正式服务未调用，但有旧兼容测试 | 明确是否仍承诺旧扩展接口，再决定合并或退役 |
| domain/devices/registry 与 transformer 子目录 | 与真实 evaluator 并存的未装配骨架 | 明确为未接入资产；接变压器时决定复用或归档 |
| legacy_importer、legacy_writer、report_exporter、template_builder | 明确禁用的空桩，主要测试“会报未启用” | 无兼容承诺时可退役，勿将其当现成功能 |
| 两个旧 SQLite 空桩 | 未装配但仍进入 wheel | 统一状态描述；发布时再决定裁剪 |
| legacy Tk | 存在测试复用的表单模型函数 | 先迁出可复用函数，再处理废弃窗口代码 |
| V4、API、JSONL、Web、Android | 已登记兼容、开发或未来入口 | 新能力统一走新公共用例，迁移后裁剪旧路径 |
| repair_v4、clean_v4、extract、enrich 等工具 | 历史模板修复与数据取证用途，部分仍被测试引用 | 标记适用基线和用途，不自动运行或批删 |
| 历史 Phase 报告与旧 HANDOFF | 证据有价值，日常导航负担较大 | 当前入口短链接，历史材料归档并保留跳转 |
| 批准映射、35表、Golden、原始模板及标准证据 | 业务与追溯依据 | 保留；当前不加载或未正式支持不是删除理由 |

不需要先引入大型死代码检测平台。以实际装配与文件引用为依据，一次处理一类残留即可；纯空壳删除不必新增一套“证明删除正确”的测试。

## 五 单人维护应保留什么减少什么

**保留直接保护业务结果的验证：** 已批准 Golden，等号与边界，缺失和不适用，数值与非线性计算，单位转换，各适配器的一致性，历史快照和实际发布入口。这些即使只有一个维护者也有价值。

**减少重复流程：** 普通任务一份短变更摘要即可，包含做了什么、依据、验证、未完成项。不要重启历史多角色审批；不要同时更新多份长报告；不要因为一行普通说明变更就跑13分钟全量测试或10,000行容量测试。

建议按修改内容选择验证：普通说明查链接和变更范围；标准表值或算法改动跑该标准的真值与边界；适配器改动跑同一输入的结果一致性与格式保存；核心公共入口改动再跑公共契约和受影响标准。CI 可一次执行并按标准输出摘要，保留独有参考工具和显式契约测试。不得用扩大允许失败清单、改 Golden 预期或删除仍有价值的测试来制造绿灯。

AGENTS 保留长期规则，TASK_STATE 只写当前状态，HANDOFF 给短交接，根问题台账保留唯一问题状态。历史报告继续作为当时证据。当前提交号以 Git 为准，文档可写“检查时基线”及日期，不必每次为记录自身 SHA 再造一个提交。

## 六 统一来源与最小公共接口建议

### 业务依据和运行数据各司其职

| 层次 | 应负责的内容 | 维护原则 |
|---|---|---|
| 原标准证据 | 原文、表格、条款、页码与来源身份 | 标准事实最高依据；异常如实保留 |
| 批准的映射及配套数据 | 适用、字段、单位、选项、规则、表值及批准解释 | 软件设计、实现和真值案例的核心业务基准 |
| 可执行标准定义及 Calculator | 稳定字段、单位、输入约束、数据包、算法、版本 | 从批准依据实现；可生成的数据尽量生成，差异有出处 |
| 统一 Application 结果与快照 | 标准身份、输入、指标、适用性、等级、解释、版本来源 | GUI、Excel、Word、API 使用同一结果语义 |
| 各端适配器 | Qt 控件、Excel 列位置、Word 排版、网络传输 | 只做输入映射和展示，不独立维护业务真值 |

“同一来源”不要求软件运行时解析 Markdown，也不要求把所有规则硬塞进一个 JSON。复杂标准保留专用 Calculator；共用的是批准依据、字段身份、入口与结果契约。标准工作簿是已校对表值资产，用户填写的 Excel 是输入载体，两者不能混为一谈。

最小公共入口只需覆盖标准列表、表单定义、单项分析、批量分析、结果与记录导出。选择标准后调用其专有计算器；记录与导出复用公共结果。多个指标分别给出成功、缺数据、不适用、输入非法等状态，最终等级聚合遵循各标准映射，不能为了统一界面发明一个通用“取最差”规则。

现在采用一个 Python 项目内的显式注册表已经足够。利用变压器的选表、插值、多指标特征检验第二标准接入边界，泵专用数学保留在泵计算器内。待这一闭环成立后再逐标准迁移，避免一次性改完17个 Profile。

### 建议写入并执行的长期条款

本次在既有 AGENTS 第7节补强以下含义，完整业务规则仍留在各标准自己的映射与台账中：

1. 经 Owner 批准的标准映射、配套核验数据及明确批准的软件决定，构成本标准软件实现和真值测试的核心业务基准；原标准仍是最高标准事实证据。
2. 原文异常、技术解释和软件选择分别记录；不得静默修正原文，不得将 Owner 软件决定冒称国标明文。
3. GUI、Excel、Word 和未来客户端共同使用同一业务字段与结果来源；标准名称、单位、选项及语义不能各端重复发明。
4. 批准的显示别名可以保留，但须记录依据与适用位置；显示名称不得充当稳定机器 ID。
5. 数据和 Calculator 必须可追溯到适用映射、表值与规则版本；旧 Canonical、历史代码或回归结果不能反过来覆盖批准依据。
6. 遵守现有轻治理，不为这些原则新增多角色审批、专用数据库、重复报告或每标准一套 CI。

## 七 UI 与多平台的推进顺序

中央 Frozen Contract 继续按本仓锁定 SHA 读取；当前 UI 指南按中央 GUIDE_INDEX 路由读取。二者版本不同是既有设计，不是缺陷。当前可用 UI 依据为 v0.2、家族规格和相关验收清单；碳核算正在设计的页面，应在其获准后作为视觉与交互参考，不能把尚未批准方案直接当冻结约束。

三软件统一的是导航、LOGO与图标语义、布局基础、状态样式和公共交互；设备的专业字段、单位和适用规则继续由自身映射决定。中央已经明确不要求建立公共 PySide6 运行时包。可以同步设计令牌和资产文件，附一份短变更说明，无需为三个单人项目建立组件发版平台。[中央 UI 版本与实施边界](https://github.com/adgo07/Qingzhou-contracts/blob/854b544563260f9e79c73e714c85f6589e0f19b3/docs/ui/UI_DESIGN_GUIDELINES_V0.2.md#L12-L81)。

以下为后续建议工作包，表内代码修复、标准接入及 UI 实现均不属于本次文档提交已完成的工作。

| 后续工作包 | 主要交付 | 最小必要验证 |
|---|---|---|
| 1 文档与风险收口 | 当前事实更新；修复 F01、F02、F03、F06；明确映射与计算器版本 | 具体故障探针转定向回归；受影响泵 Golden |
| 2 最小标准解耦 | 公共标准选择、字段定义、结果与记录；泵迁入注册入口 | 旧泵真值不漂移；旧 API 适配到同一用例 |
| 3 变压器纵向接入 | 按批准双文件实现数据、选表、插值、多指标判定和输出 | 来源独立的变压器案例；一条完整 GUI 与 Excel 流程 |
| 4 UI 与 Word 收口 | 按家族方案重组产品壳；Word消费统一快照 | 相关页面人工查看；同一结果三类输出一致 |
| 5 下一个真实平台 | 针对明确平台实现薄适配器与安装交付 | 同一套数值向量；该平台的真实安装与使用烟测 |

UI 的导航、配色和壳层设计可以与工作包2并行；业务页面应在公共字段与结果接口稳定后实现。这样既能推进美观度，也避免先把泵专属页面精修后又重写一次。正式变压器支持仍按现有范围授权与验收推进，不因本报告自动提升状态。

跨平台先保护纯数据请求结果、十进制字符串传输、标准与算法版本、计算器接口和持久化端口。是否采用在线服务、本地桥接或另一个运行时，等具体平台的离线需求明确后再决定。现在不要求 Rust/C++ 重写、每端复制公式或一次搭建全部平台 CI。中央锁定架构本身支持这种渐进路线。[锁定架构](https://github.com/adgo07/Qingzhou-contracts/blob/ee5feb0cc34dbd99790500fadd0c4c932e202a20/docs/architecture/ARCHITECTURE_V2.1_FROZEN.md)。

## 八 验证范围和证据边界

本次完成真实代码与调用链检查、Git 文件盘点、两份变压器冻结文件哈希核对、Windows 当前提交日志核实，以及四项隔离探针：标准身份错配、Excel单位错配、显示名称改变后的输出、标准资源缺失。探针使用临时工作簿或内存记录，未将探针数据写入用户历史记录。

临时 wheel 构建用于核查实际包含文件与依赖声明，成功构建并检查155个成员；它不是正式发布产物或全平台验收。

本地使用 Linux 和 Python 3.12.14 额外运行一次 unittest discover，原始输出为：Ran 1161 tests in 533.318s；FAILED (failures=153, errors=35, skipped=3)。failure计数含子测试，不能直接用总数减去它推算通过数。主要限制包括缺少 PySide6、jsonschema，浅克隆不包含历史基线，以及环境不允许测试监听网络端口；另有旧 V4、发行审计等失败。未将153次失败报告成153个已确认的产品缺陷，也未据此宣布 Linux 已验收。Windows 计数仍以上述同一提交的真实 Actions 日志为准；本次未进行 Windows Qt 视觉复验。

仓库没有提交原标准 PDF，泵的原件通过外部证据根及 SHA 定位。当前 Pump CI 对外部证据明确使用 skip，因此本报告不声称已对所有标准原文和全部表值逐条、逐格重验。变压器双文件哈希一致证明本次读取的资产与批准冻结字节一致，不额外证明本轮完成了独立35表数值审计。

**落实重点：先把标准身份和统一字段结果契约做稳，再让第二个标准验证这套接口；日常维护以真实业务风险选择验证，让当前入口保持简短、准确、可追溯。**
