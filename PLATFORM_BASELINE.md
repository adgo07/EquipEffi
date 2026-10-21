# 中央平台基线

本文件概述本仓采用的中央 Frozen Contract 边界；机器可读锁定值唯一以 [`platform-lock.json`](platform-lock.json) 为准。

- 中央仓：<https://github.com/adgo07/Qingzhou-contracts.git>
- 当前锁定 SHA：`ee5feb0cc34dbd99790500fadd0c4c932e202a20`
- Architecture：`V2.1 FROZEN`；Numeric Contract：`v1 FROZEN`。
- Unit、Module/Capability、Workspace/Attempt/Record/Result 与 qzpack Contract 仍为 `DRAFT / NOT YET RELEASED`，不得按已发布契约要求本仓 adoption。
- Pump 项目配置 `EQUIPEFFI_PUMP_DECIMAL50_V2` 是本仓标准证据支撑的差异，不是全平台默认。

Frozen Contract 按 locked SHA 读取；ACTIVE / ACTIVE-EVOLVING 指南通过中央 `docs/GUIDE_INDEX.md` 路由读取中央当前版本。指南更新不自动升级 Frozen Contract，不修改本仓锁。只有 Owner 显式授权的治理变更可以更新 `platform-lock.json` 与本文件。

开工前按中央 Policy 做 Contract Preflight：锁 SHA → 相关 Frozen 条款 → 适用 MUST/MUST NOT → 本仓差异分类。普通本地业务或 UI 修复不必通读整份中央仓；确认涉及公共语义时再读取对应文件。