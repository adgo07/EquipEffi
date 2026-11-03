# 当前任务状态

## 当前任务：三设备 Windows 候选包收口（2026-11-03）

Owner已授权更新状态、从最新主线构建并验证Windows包，明确暂不正式发布。源码基线为 `e596ee33546ce340b01e0bb83a76c5fd6d782c6c`；PR #37、#38、#39、#40均已合并。工作分支 `codex/three-device-candidate-20261103`。候选构建、自动验证及状态同步已完成（保留环境与EXE交互验证限制），证据统一见[本轮收口记录](docs/governance/THREE_DEVICE_CANDIDATE_20261103.md)。

- 最新代码：离心泵（清水/石化）、变压器、GB18613电动机默认开放且沿用已有SUPPORTED配置；默认模板V6.3，电机新评价使用额定效率及电压V。
- 当前正式发布仍为v0.2.1；本轮0.2.2仅为未发布候选，不创建Release/标签，不覆盖旧包。
- 高压GB30254与永磁GB30253仅完成Stage B设计，本轮不实施、不开放。
- 本轮结果：1255项完整回归已执行，4项构建锁冲突随后所在模块11项复验通过；包资源/状态、中文路径启动器、Windows Qt源码三设备流程通过。候选ZIP及哈希见收口记录。下一步保留候选，补齐环境与实际EXE交互证据；未经新授权不发布。
- Phase 1–7既有PASS保持；Phase 8仍为EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE，不自行声明PASS或进入Phase 9。
- 另一台干净Windows及真实125%系统缩放验证尚未取得证据，不把本机测试等同这些验收。

## 权威入口与历史

产品范围与发布/候选差异见[V1_SCOPE.md](V1_SCOPE.md)，开放问题见[QA_BACKLOG.md](QA_BACKLOG.md)，标准解释见[STANDARD_ISSUES_REGISTER.md](STANDARD_ISSUES_REGISTER.md)，中央锁见[platform-lock.json](platform-lock.json)。

截至PR #40的历史执行、原有验收证据及阶段记录保留在[基线任务状态](https://github.com/adgo07/EquipEffi/blob/e596ee33546ce340b01e0bb83a76c5fd6d782c6c/TASK_STATE.md)。其中“PR尚未合并”等是当时记录，不代表当前状态。各标准详细实施记录仍原位保留。
