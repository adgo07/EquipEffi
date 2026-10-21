# 当前任务状态

## 产品状态

- 路线：EquipEffi V2.3；默认分支：`master`。
- Phase 0 为不可变基线；Phase 1–7 已独立验收（PR #10–#15）。Phase 8（GB 19762 Excel 批量评价）已合并 PR [#16](https://github.com/adgo07/EquipEffi/pull/16)，merge SHA `64b656ee4924fbf09f3fd87596ef1a1a779d1f09`；当前为 `EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE`。不得自行声明 `PHASE_8_PASS`，不得开始 Phase 9。

## 当前工作收口

本轮依据 [`docs/governance/SIMPLIFICATION_NEXT_STEPS_20261021.md`](docs/governance/SIMPLIFICATION_NEXT_STEPS_20261021.md) 完成三步简化：

1. [PR #26](https://github.com/adgo07/EquipEffi/pull/26)：删除已授权旧桌面、适配器和重复历史资料。
2. [PR #27](https://github.com/adgo07/EquipEffi/pull/27)：退出 Web、Android、旧 API/JSONL/V4 链，保留 Qt/V6、专业候选与受保护资产。
3. [PR #28](https://github.com/adgo07/EquipEffi/pull/28)：统一测试门禁，修复批量反馈和历史记录展示，完成原生包与无控制台启动核验。

Owner 已确认 ZIP 正常解压后批量评价、记录和外部打开正常，并授权主会话最终核查后按依赖顺序合并。各 PR 的合并结果和最终 CI 以对应 GitHub 页面为准。QA-RET-001/002/003 已按各自证据关闭；不扩大本轮重构范围。

无控制台验收包对应代码提交 `ee64e131`；其后仅更新验收状态文档。原生包 PE Subsystem=2，实际 Qt 首页启动、19项定向测试与资源审计通过。交付使用 ZIP 在普通用户目录正常解压；受限构建目录中 EXE 的 Low 完整性不能作为正常安装环境验收依据，不更改系统权限或用户数据。

当前机器没有干净 Windows / Sandbox；本机隔离及交互验证不等于干净机器验收，也不构成正式发布或 Phase 8 独立 PASS。下一轮须单独确认范围，不自动进入新标准实施或 Phase 9。

## 当前权威入口

- 产品范围与各 Profile 状态：[`V1_SCOPE.md`](V1_SCOPE.md)
- QA 开放项及已登记偏差：[`QA_BACKLOG.md`](QA_BACKLOG.md)
- 中央 Frozen 基线：[`platform-lock.json`](platform-lock.json)、[`PLATFORM_BASELINE.md`](PLATFORM_BASELINE.md)
- 标准问题：[`STANDARD_ISSUES_REGISTER.md`](STANDARD_ISSUES_REGISTER.md)
- Phase 8 执行证据：[基线提交 `332d79c7d999feb4047c920ecb4359655bf9440e` 的 Phase 8 执行报告](https://github.com/adgo07/EquipEffi/blob/332d79c7d999feb4047c920ecb4359655bf9440e/PHASE8_EXECUTION_REPORT.md)；独立验收前不生成 Phase 8 acceptance record。

已批准阶段的原始验收记录固定链接：[Phase 3](https://github.com/adgo07/EquipEffi/blob/332d79c7d999feb4047c920ecb4359655bf9440e/docs/phase3_acceptance_record.md)、[Phase 4](https://github.com/adgo07/EquipEffi/blob/332d79c7d999feb4047c920ecb4359655bf9440e/docs/phase4_acceptance_record.md)、[Phase 5](https://github.com/adgo07/EquipEffi/blob/332d79c7d999feb4047c920ecb4359655bf9440e/docs/phase5_acceptance_record.md)、[Phase 6](https://github.com/adgo07/EquipEffi/blob/332d79c7d999feb4047c920ecb4359655bf9440e/docs/phase6_acceptance_record.md)、[Phase 7](https://github.com/adgo07/EquipEffi/blob/332d79c7d999feb4047c920ecb4359655bf9440e/docs/phase7_acceptance_record.md)。这些链接只承载批准历史，无自动调度权。
