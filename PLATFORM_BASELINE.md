# PLATFORM_BASELINE

本项目当前锁定的 Qingzhou Contracts 上位治理基线。

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

截至本次接入，`Qingzhou-contracts` 没有正式 release，也没有 `contracts-v0.x.x` / `contracts-v1.x.x` tag。因此本仓**没有虚构正式版本**，而是按治理要求锁定已经合并到中央仓 `main` 的精确 commit SHA，作为 pre-release / bootstrap baseline。

本项目不得在运行时或开发治理中自动跟随 `Qingzhou-contracts/main`。以后中央仓有任何新提交，只有在本仓显式升级本文件和 `platform-lock.json` 后才对本项目生效。

## 2. Architecture / Contract Versions

| 项目 | 锁定状态 |
|---|---|
| Architecture | `V2.1 FROZEN` |
| Numeric Contract | `draft-v1` — `DRAFT / NOT YET RELEASED` |
| Unit Contract | `draft-v1` — `DRAFT / NOT YET RELEASED` |
| Module / Capability Contract | `draft-v1` — `DRAFT / NOT YET RELEASED` |
| Workspace / Attempt / Record / Result Contract | `draft-v1` — `DRAFT / NOT YET RELEASED` |
| qzpack / Canonical Package Contract | `draft-v1` — `DRAFT / NOT YET RELEASED` |

`Architecture V2.1 FROZEN` 是已冻结的长期架构约束。上述 Contract v1 文档仍为 DRAFT；本次锁定仅用于建立稳定、可复核的 bootstrap 基线，不把 DRAFT 描述成 FROZEN，也不把其中未决项提前定型为本项目永久规则。

## 3. Upgrade Rule

- 本项目只受本文件与 `platform-lock.json` 中**已锁定的中央仓 commit**约束，不自动采用中央仓后续变化；
- 公共 Contract 升级必须显式修改 `PLATFORM_BASELINE.md` 与 `platform-lock.json`；
- 正式 release/tag 出现后，应按中央 `VERSIONING.md` 评估迁移，不得继续假装 bootstrap SHA 是正式 release；
- 升级前检查 breaking changes、RFC/ADR、release notes，并运行适用的公共 Conformance + 本项目回归；
- 普通业务 Bug、单标准专属逻辑、页面问题继续在 EquipEffi 仓库处理；
- 发现跨三个产品/跨平台公共语义缺口时，记录 RFC candidate 并提交 `Qingzhou-contracts` 统一治理，不在本仓永久私有化公共规则。

## 4. Known Local Deviations / Gaps

本次接入只记录差距，不做业务重构：

1. EquipEffi 已有 `application / domain / infrastructure / presentation` 分层与机器可读标准资源，但尚未实现中央 Contract 定义的完整 Module/Capability Manifest、Workspace/Attempt/Record 生命周期和统一 Result Envelope。
2. 当前标准数据为仓库内 JSON/manifest 体系，尚未全面转换为 qzpack；这属于未实施能力，不是本次任务的失败条件。
3. 本仓已有 Decimal 工具和标准专用 Calculator/Evaluator，但尚未采用正式发布的 Qingzhou Numeric Contract；中央 Numeric Contract 仍是 DRAFT，且 D-001 非线性函数 reference procedure 尚未冻结。
4. Unit 语义目前主要由设备元数据/评价器自行表达，尚未接入统一 Unit Contract/UnitService。
5. 平台无关 Workspace、正式 Record Envelope、qzpack lifecycle、跨平台 Conformance Vector Schema 尚未完整实施。
6. 本次 adoption 分支按用户要求从默认分支 `master@19b628f6349713f62d8f5127a52b4be521d163da` 创建；仓库同时存在尚未合并的 Phase 1 PR #1，其治理文件比默认分支更新。合并顺序变化时必须 rebase/reconcile，不能用本次治理接入覆盖该 PR 已形成的业务阶段结论。

以上均为已知差距/集成风险；未发现与 `Architecture V2.1 FROZEN` 无法并存的硬冲突。

## 5. Local Authority Boundary

公共 Contract 不覆盖：

- 国家/行业标准原文；
- EquipEffi 合法的设备能效业务 Domain；
- 单标准专属适用范围、公式、表格、边界和结果语义；
- 已批准的本项目业务治理结论。

中央仓定义公共外围语义；EquipEffi 对设备能效专业业务保持自治。
