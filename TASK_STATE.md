# 当前任务状态

## 产品状态

- 路线：EquipEffi V2.3；默认分支：`master`。
- Phase 0 为不可变基线；Phase 1–7 已独立验收（PR #10–#15）。Phase 8（GB 19762 Excel 批量评价）已合并 PR [#16](https://github.com/adgo07/EquipEffi/pull/16)，merge SHA `64b656ee4924fbf09f3fd87596ef1a1a779d1f09`；当前为 `EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE`。不得自行声明 `PHASE_8_PASS`，不得开始 Phase 9。

## 当前工作：变压器接入审查修复（2026-10-23）

Owner已明确下一版本纳入GB 20052—2024变压器，已确认25列方案并授权完善设计后实施。按“接入设计 → 变压器内核 → 产品接通与验收”执行，不自动改变当前软件支持能力、Phase状态或正式发布状态。

- 设计检查基线：`master@dd27baba07cf0a41f58c0ab4838cd786a40e05ff`，即PR #28合并后。
- 统一设计：[变压器接入设计与统一Excel兼容方案](docs/standards/gb20052_2024/INTEGRATION_DESIGN.md)。25列：A—U保留位置，I单值额定阻抗，V/W高低电压，X/Y高低及中低阻抗；损耗统一W；类别明确适用型式，其他/不确定分别显示不在范围/无法判定。无拼接数字、适用确认列、单位列或全局试验确认门禁。
- 必须保持：**冻结二件套不改；当前正式V6的泵Sheet及共享依赖不改；变压器Sheet设计已确认、WPS交互经Owner确认正常，原生包流程待验收**。
- 实施工作树分支：`codex/transformer-implementation-20261023`，从PR #29 `20517fe582a76118a77fd33e12d347bb565e7452`起步。根负责集成与验收，子任务分工数据派生、领域内核、模板适配。QA-TR-001已登记。
- 代码已形成设计PR [#29](https://github.com/adgo07/EquipEffi/pull/29)、内核草案PR [#30](https://github.com/adgo07/EquipEffi/pull/30)、产品集成草案PR [#31](https://github.com/adgo07/EquipEffi/pull/31)，按此顺序依赖；PR #31的`04ee50a7`落实Owner表2非630kVA阻抗只留痕决定及全量发现问题的定向修复。未合并；此前1103项全量已通过，独立审查修复c303060e已通过完整CI 1130项，未合并或正式发布。
- 已接通单向派生数据、同核Qt/Excel、V6.1统一模板和单条混合批次记录。不修改冻结资产、数据库迁移、Pump Golden或中央锁。UI美化延后，未验收不得声明SUPPORTED或正式发布。详细证据及待办见[实施记录](docs/standards/gb20052_2024/IMPLEMENTATION_REPORT.md)。

- 收口证据（2026-10-23）：代码提交`dfb2c10d`的Windows CI [run 39932000834](https://github.com/adgo07/EquipEffi/actions/runs/39932000834)全量1103项及编译、包/资源、空白检查通过。Owner确认WPS类别/条件下拉、第104行追加与保存重开正常。隔离包启动自检通过；原生窗口操作及干净机器验收尚未完成，不提升正式支持或发布状态。

- QA-TR-002工程修复已关闭，六项问题与四项处理决定见[审查修复记录](docs/standards/gb20052_2024/PR31_REVIEW_FIXES.md)。新c303060e内部包通过隔离启动/资源自检；旧331b357包不包含本轮修复。实际窗口全流程仍待验收。

- 最终续检：Owner授权验收后依次合并；设计PR #29已合并于`4ae97dac2397756094e56565eb79062bcc3e6a51`，#30已改以master为基准，#30/#31尚未合并。c9ae5c4e的Windows CI再次通过。新增QA-TR-003定位合法`x:sheet`前缀导致结果写回漏查Sheet；修复后真实混合工作簿已完成2行5台、1级3台/不在范围2台且历史保存无错误，仍需定向回归和更新原生包。实际GUI控制受工具截图/坐标限制，已请Owner补交互确认；不将程序启动或可访问性读取当成全流程通过。

- 最新收口：QA-TR-003定向8项通过并关闭，代码`745111b9`已推送。对应新内部ZIP已构建、独立启动自检和资源审计通过，身份及原始超时记录见[审查修复记录](docs/standards/gb20052_2024/PR31_REVIEW_FIXES.md#最终验收续检2026-10-23)。旧c303060e包不含此修复。最新全量CI与Owner真实窗口操作结果尚待收口；后续先核实结果，有问题修复，无问题按#30→#31合并。没有干净Windows的限制继续保留。

## 已收口的简化工作

本轮依据 [`docs/governance/SIMPLIFICATION_NEXT_STEPS_20261021.md`](docs/governance/SIMPLIFICATION_NEXT_STEPS_20261021.md) 完成三步简化：

1. [PR #26](https://github.com/adgo07/EquipEffi/pull/26)：删除已授权旧桌面、适配器和重复历史资料。
2. [PR #27](https://github.com/adgo07/EquipEffi/pull/27)：退出 Web、Android、旧 API/JSONL/V4 链，保留 Qt/V6、专业候选与受保护资产。
3. [PR #28](https://github.com/adgo07/EquipEffi/pull/28)：统一测试门禁，修复批量反馈和历史记录展示，完成原生包与无控制台启动核验。

Owner 已确认 ZIP 正常解压后批量评价、记录和外部打开正常，并授权主会话最终核查后按依赖顺序合并。各 PR 的合并结果和最终 CI 以对应 GitHub 页面为准。QA-RET-001/002/003/004 已按各自证据关闭；不扩大本轮重构范围。

无控制台验收起于代码提交 `ee64e131`；最终复核另修复既有线程收尾重入问题，37项相关检查通过。最终交付包的代码提交与审计结果记于 PR #28。原生包 PE Subsystem=2，实际 Qt 首页启动、19项定向测试与资源审计通过。交付使用 ZIP 在普通用户目录正常解压；受限构建目录中 EXE 的 Low 完整性不能作为正常安装环境验收依据，不更改系统权限或用户数据。

上一轮没有干净 Windows / Sandbox；本机隔离及交互验证不等于干净机器验收，也不构成正式发布或 Phase 8 独立 PASS。后续Windows/WPS验收按本次设计第三步安排如实补齐，不把历史缺口冒称已完成。

## 当前权威入口

- 产品范围与各 Profile 状态：[`V1_SCOPE.md`](V1_SCOPE.md)
- QA 开放项及已登记偏差：[`QA_BACKLOG.md`](QA_BACKLOG.md)
- 中央 Frozen 基线：[`platform-lock.json`](platform-lock.json)、[`PLATFORM_BASELINE.md`](PLATFORM_BASELINE.md)
- 标准问题：[`STANDARD_ISSUES_REGISTER.md`](STANDARD_ISSUES_REGISTER.md)
- Phase 8 执行证据：[基线提交 `332d79c7d999feb4047c920ecb4359655bf9440e` 的 Phase 8 执行报告](https://github.com/adgo07/EquipEffi/blob/332d79c7d999feb4047c920ecb4359655bf9440e/PHASE8_EXECUTION_REPORT.md)；独立验收前不生成 Phase 8 acceptance record。

已批准阶段的原始验收记录固定链接：[Phase 3](https://github.com/adgo07/EquipEffi/blob/332d79c7d999feb4047c920ecb4359655bf9440e/docs/phase3_acceptance_record.md)、[Phase 4](https://github.com/adgo07/EquipEffi/blob/332d79c7d999feb4047c920ecb4359655bf9440e/docs/phase4_acceptance_record.md)、[Phase 5](https://github.com/adgo07/EquipEffi/blob/332d79c7d999feb4047c920ecb4359655bf9440e/docs/phase5_acceptance_record.md)、[Phase 6](https://github.com/adgo07/EquipEffi/blob/332d79c7d999feb4047c920ecb4359655bf9440e/docs/phase6_acceptance_record.md)、[Phase 7](https://github.com/adgo07/EquipEffi/blob/332d79c7d999feb4047c920ecb4359655bf9440e/docs/phase7_acceptance_record.md)。这些链接只承载批准历史，无自动调度权。
