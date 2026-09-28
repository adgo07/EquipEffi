# EquipEffi Agent 治理

本文件在 QZC-A01 中新增，用于建立 EquipEffi 与 `Qingzhou-contracts` 的上位治理关系。

当前默认分支原先没有 `AGENTS.md`。因此本文件只增加公共治理约束，不替代 `HANDOFF.md` 中已有的业务事实、阶段状态和执行纪律。若后续与包含更完整业务治理的分支合并，必须保留该分支既有结论，并将本文件的 Qingzhou Contracts 章节合并进去，不能反向覆盖。

## 当前业务治理入口

- 当前业务事实、完成度、已知阻塞和下一步，以本仓 `HANDOFF.md` 及其明确引用的现有治理文件为准；
- 本次 QZC-A01 不授权修改业务公式、Canonical 标准数据、evaluator/calculator、数据库、UI 或跨平台产品实现；
- Qingzhou Contracts 公共治理只约束公共外围 Contract，不覆盖更具体的标准原文和 EquipEffi 合法的设备能效 Domain 自治。

# Qingzhou Contracts 上位治理

1. 本项目受 `https://github.com/adgo07/Qingzhou-contracts.git` 的公共架构与 Contract 治理约束；当前批准基线必须以 `PLATFORM_BASELINE.md` 和 `platform-lock.json` 为准。
2. 本项目不得实时采用 `Qingzhou-contracts/main` 的最新内容。中央仓后续提交不会自动对 EquipEffi 生效。
3. 只有显式升级 `PLATFORM_BASELINE.md` 与 `platform-lock.json`，并完成兼容检查和必要回归后，新的公共 Contract 才对本项目生效。
4. 普通设备能效业务问题、单标准专属规则、产品 Bug 和页面问题继续在 EquipEffi 仓库解决，不需要上升为公共 Contract。
5. 如果发现跨三个产品、跨平台或公共外围语义的 Contract 缺口，不得在 EquipEffi 中永久私自定义同名但不同义的公共规则；应先在本仓记录 RFC candidate，再由 `Qingzhou-contracts` 统一处理。
6. `Qingzhou-contracts` 中标记为 `DRAFT` 的内容必须继续标记为 DRAFT，不得在本仓描述成 FROZEN、RELEASED 或正式 `contracts-v1.0.0`。
7. `Architecture V2.1 FROZEN` 是已冻结架构约束；DRAFT Contract 仅按当前锁定 SHA 作为 bootstrap/兼容基线观察，不因本次 adoption 自动升级为冻结业务语义。
8. 公共 Contract 不得覆盖国家/行业标准原文、已批准标准映射、单标准专有适用逻辑、设备能效结果语义或本项目合法自治范围。
9. 任何公共 Contract 升级必须显式记录中央 release/tag（存在时）、精确 commit SHA、版本状态和升级日期；禁止使用“latest main”作为版本。
10. 当前接入不要求重构业务代码，不要求合仓，不要求公共 Python package，不要求 qzpack 全量迁移，不要求 Suite、Android、HarmonyOS、iOS 或 Native Core 开发。

## 公共问题的处理

发现公共问题时：

```text
本仓记录真实案例与影响
→ 判断是否跨模块/跨平台
→ 形成 RFC candidate
→ Qingzhou-contracts 统一评审
→ 正式 Contract/Schema/Conformance 发布
→ EquipEffi 按需显式升级 platform lock
```

不得为了让当前项目快速通过而直接修改中央 Contract 含义。

## 当前锁定基线

- Qingzhou-contracts commit: `0cd74d783fa23add6dc881b408a8c8ba8503f8e8`
- Architecture: `V2.1 FROZEN`
- Contract release/tag: 无正式 release/tag
- Baseline kind: `pre-release / bootstrap baseline`
- Numeric / Unit / Module-Capability / Workspace-Record-Result / qzpack: `draft-v1 / DRAFT`

具体字段以 `PLATFORM_BASELINE.md` 和 `platform-lock.json` 为唯一当前锁定记录。
