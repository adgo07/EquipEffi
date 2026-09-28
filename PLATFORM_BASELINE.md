# PLATFORM_BASELINE

本项目当前锁定的 Qingzhou-contracts 上位治理基线。

## 1. Baseline Identity

```text
module_id: qz.equipment_efficiency
repository: https://github.com/adgo07/Qingzhou-contracts.git
baseline_kind: pre-release / bootstrap baseline
contracts_release: none
contracts_tag: none
commit_sha: 0cd74d783fa23add6dc881b408a8c8ba8503f8e8
adopted_at: 2026-09-28
```

本仓按用户批准的精确 SHA 锁定中央基线，不虚构正式 release 或 tag。中央仓后续提交不会自动对本项目生效；本项目不得在运行时或开发治理中跟随 `Qingzhou-contracts/main`。

## 2. Architecture / Contract Versions

| 项目 | 锁定状态 |
|---|---|
| Architecture | `V2.1 FROZEN` |
| Numeric Contract | `draft-v1` — `DRAFT / NOT YET RELEASED` |
| Unit Contract | `draft-v1` — `DRAFT / NOT YET RELEASED` |
| Module / Capability Contract | `draft-v1` — `DRAFT / NOT YET RELEASED` |
| Workspace / Attempt / Record / Result Contract | `draft-v1` — `DRAFT / NOT YET RELEASED` |
| qzpack / Canonical Package Contract | `draft-v1` — `DRAFT / NOT YET RELEASED` |

`Architecture V2.1 FROZEN` 是冻结的长期架构约束。五组 Contract v1 仍为 DRAFT；本次锁定只建立可复核的 bootstrap 基线，不把 DRAFT 描述为 FROZEN，也不将未决项提前定型为本项目永久规则。

## 3. Upgrade Rule

- 本项目只受本文件与 `platform-lock.json` 中锁定的中央 commit 约束，不自动采用中央仓后续变化。
- 公共 Contract 升级必须显式更新本文件和 `platform-lock.json`。
- 正式 release/tag 出现后，按中央 `VERSIONING.md` 评估迁移；不得继续把 bootstrap SHA 称为正式 release。
- 升级前检查 breaking changes、RFC/ADR、release notes，并运行适用的公共 Conformance 与本项目回归。
- 普通业务 Bug、单标准专属逻辑和页面问题继续在 EquipEffi 处理；跨产品/跨平台公共语义缺口应记录 RFC candidate 并交由 Qingzhou-contracts 治理。

## 4. Known Local Deviations / Gaps

本次只接入治理，不迁移业务实现。当前已知差距包括：

1. EquipEffi 已有 `application / domain / infrastructure / presentation` 分层和机器可读标准资源，但尚未完整实现中央 Contract 定义的 Module/Capability Manifest、Workspace/Attempt/Record 生命周期和统一 Result Envelope。
2. 当前标准数据为本项目 JSON/manifest 体系，尚未全面转换为 qzpack；这是未实施能力，不是本次接入失败。
3. EquipEffi 已有 Decimal 计算与标准专用 Calculator/Evaluator；中央 Numeric Contract 仍为 DRAFT，不能将本项目计算约定宣传为已满足未来跨语言 Numeric Contract。
4. 单位语义主要由设备元数据和评价器表达，尚未接入统一 Unit Contract/UnitService。
5. 当前 pump_water 已有经批准的 Numeric & Decision Contract V2、Canonical 映射和 Golden 0.4；这些本地业务真值继续按 Phase 1 冻结边界管理，不因中央 DRAFT Contract 改写。
6. 平台无关 Workspace、正式 Record Envelope、qzpack lifecycle 和跨平台 Conformance Vector Schema 尚未完整实施。

这些是已知差距/集成风险；未发现与 `Architecture V2.1 FROZEN` 无法并存的硬冲突。

## 5. Local Authority Boundary

公共 Contract 不覆盖：

- 国家/行业标准原文及其 Canonical 标准数据；
- EquipEffi 合法的设备能效业务 Domain；
- 单标准专属适用范围、公式、表格、边界、比较方向和结果语义；
- 已批准的本项目业务治理结论，包括 Phase 1 冻结的 pump_water 契约与 Golden；
- 当前 V1 Scope 与 Profile 发布决策。

中央仓治理公共外围语义；EquipEffi 对设备能效专业业务保持自治。QZC-A01 不授权开始 Phase 2，Phase 2 仍须用户明确授权。
