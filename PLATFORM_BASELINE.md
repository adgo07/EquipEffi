# PLATFORM_BASELINE

本项目当前锁定的 Qingzhou-contracts 上位治理基线。

## 1. Baseline Identity

```text
module_id: qz.equipment_efficiency
repository: https://github.com/adgo07/Qingzhou-contracts.git
baseline_kind: frozen Numeric v1 adoption / exact central SHA
contracts_release: none
contracts_tag: none
commit_sha: ee5feb0cc34dbd99790500fadd0c4c932e202a20
adopted_at: 2026-10-01
```

本仓按用户批准的精确 SHA 锁定中央基线，不实时跟随 `Qingzhou-contracts/main`。中央仓后续提交不会自动对本项目生效。

## 2. Architecture / Contract Versions

| 项目 | 锁定状态 |
|---|---|
| Architecture | `V2.1 FROZEN` |
| Numeric Contract | `v1` — `FROZEN` — `contracts/numeric/NUMERIC_CONTRACT_V1_FROZEN.md` |
| Unit Contract | `draft-v1` — `DRAFT / NOT YET RELEASED` |
| Module / Capability Contract | `draft-v1` — `DRAFT / NOT YET RELEASED` |
| Workspace / Attempt / Record / Result Contract | `draft-v1` — `DRAFT / NOT YET RELEASED` |
| qzpack / Canonical Package Contract | `draft-v1` — `DRAFT / NOT YET RELEASED` |

本次只正式采用冻结的 Numeric Contract v1。Unit、Module/Capability、Workspace/Attempt/Record/Result、qzpack 等 Contract 没有因为本次任务被升级或冻结。

Numeric Contract v1 明确禁止把单一 precision / rounding 配置解释为平台全局默认。EquipEffi 继续使用自己的 Pump Numeric Profile；其他设备 Calculator 后续分别声明自己的有效 Numeric Profile。

## 3. Pump Numeric Profile adoption

机器可读声明：`specs/equipment_efficiency/numeric/equipeffi_pump_numeric_profile_v1.json`。

本项目现有并经 QZC-N01-B 实证验证的 Pump Profile 继续作为正式本地 Profile：

```text
numeric_profile_id        = EQUIPEFFI_PUMP_DECIMAL50_V2
numeric_contract_version  = v1
representation            = strict Decimal text / Decimal / exact integer
working_precision         = 50
rounding_mode             = ROUND_HALF_EVEN working context
comparison_policy         = full-value exact rule/bucket/grade comparison
explicit_rounding_policy  = no hidden pre-grade rounding
transcendental_policy     = PUMP-RP-0.1
operation_order_policy    = explicit Pump reference procedure / current production expression tree
tolerance_policy          = numerical/test conformance only; never a business epsilon
display_policy            = presentation-only HALF_UP behavior; no feedback into authoritative comparison
binary_float_policy       = reject raw Python float/non-finite authoritative Pump input
```

`precision=50` 和 `ROUND_HALF_EVEN` 是 EquipEffi Pump Profile 的具体配置，不是 Numeric Contract v1 的平台默认，也不要求变压器、电机、风机或未来设备照搬。

本次采用使用等价不可变 trace/reference 结构满足 Numeric v1 的可追溯要求：机器可读 Profile 声明固定 `numeric_contract_version / numeric_profile_id / rule_version` 与中央 SHA；`platform-lock.json` 固定中央 Contract；Pump `EvaluationResult.standard_reference` 与 lookup/trace data IDs 继续固定实际标准/规则来源。中央 Frozen Contract 对最终统一 Result/Record 字段位置仍保持 OPEN，因此本任务不借 adoption 新增统一 Result Envelope 字段。

## 4. Upgrade Rule

- 本项目只受本文件与 `platform-lock.json` 中锁定的中央 commit 约束，不自动采用中央仓后续变化。
- 公共 Contract 升级必须显式更新本文件和 `platform-lock.json`。
- 正式 release/tag 出现后，按中央版本治理评估迁移；当前 adoption 仍以精确 SHA 作为可复核基线。
- 升级前检查 breaking changes、RFC/ADR、release notes，并运行适用的公共 Conformance 与本项目回归。
- 普通业务 Bug、单标准专属逻辑和页面问题继续在 EquipEffi 处理；跨产品/跨平台公共语义缺口交由 Qingzhou-contracts 治理。

## 5. Known Local Deviations / Gaps

1. EquipEffi 已有 `application / domain / infrastructure / presentation` 分层和机器可读标准资源，但尚未完整实现中央 DRAFT 的 Module/Capability Manifest、Workspace/Attempt/Record 生命周期和统一 Result Envelope。
2. 当前标准数据仍为本项目 JSON/manifest 体系，尚未全面转换为 qzpack；这是未实施能力，不是本次 adoption 失败。
3. Pump Numeric 已与 Frozen Numeric v1 的核心义务对齐并由 N01-B / 本次 adoption conformance 验证；其他设备尚未因此自动获得 Decimal50 Profile。
4. 单位语义主要由设备元数据和评价器表达，Unit Contract 仍为 DRAFT，本次不升级 Unit Contract。
5. 当前 `pump_water` 已有经批准的 Numeric & Decision Contract V2、Canonical 映射和 Golden 0.4；这些本地业务真值继续按 Phase 1 冻结边界管理，不因平台 Numeric v1 adoption 改写。
6. Kotlin/Swift/ArkTS 的非线性数值实证、通用 transcendental tolerance 和平台最小 precision 仍按中央 Numeric v1 保持 OPEN；本项目不自行冻结。

## 6. Local Authority Boundary

公共 Contract 不覆盖：

- 国家/行业标准原文及其 Canonical 标准数据；
- EquipEffi 合法的设备能效业务 Domain；
- 单标准专属适用范围、公式、表格、边界、比较方向和结果语义；
- 已批准的本项目业务治理结论，包括 Phase 1 冻结的 pump_water 契约与 Golden；
- 当前 V1 Scope 与 Profile 发布决策。

中央仓治理公共 Numeric 语义；EquipEffi 对设备能效专业业务保持自治。本次 Numeric Contract v1 adoption 不授权开始 Phase 2，Phase 2 仍须用户明确授权。
