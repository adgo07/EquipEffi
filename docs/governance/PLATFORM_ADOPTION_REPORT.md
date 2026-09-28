# PLATFORM_ADOPTION_REPORT — QZC-A01

日期：2026-09-28  
业务仓：`adgo07/EquipEffi`  
模块：`qz.equipment_efficiency`  
任务：仅接入 `Qingzhou-contracts` 公共治理，不做业务重构。

## 1. 当前仓信息

- repository: `https://github.com/adgo07/EquipEffi.git`
- 默认分支：`master`
- QZC-A01 起始默认分支 head: `19b628f6349713f62d8f5127a52b4be521d163da`
- adoption branch: `chore/qingzhou-contracts-adoption`
- 默认分支 `HANDOFF.md` 当前描述阶段：评价内核可运行、标准数据已校对、继续按标准边界逐项补齐回归；Excel 正式导入/写回、完整发布和移动端仍未完成。
- 默认分支在本任务开始时没有 `AGENTS.md`、没有 `TASK_STATE.md`；QZC-A01 仅新增治理入口，不据此改写业务阶段。
- 仓库同时存在 open PR #1 `phase1/pump-v2-r01-r06`，其业务治理和 Phase 1 状态明显新于默认分支。该 PR 尚未合并，因此本任务仍按用户要求从最新默认分支创建。后续 merge/rebase 必须保留 PR #1 已形成的业务结论，不能由本 adoption 分支覆盖。

## 2. Qingzhou-contracts 锁定基线

中央仓：`https://github.com/adgo07/Qingzhou-contracts.git`

本次读取并锁定：

- `main` commit: `0cd74d783fa23add6dc881b408a8c8ba8503f8e8`
- Architecture: `V2.1 FROZEN`
- Numeric Contract: `draft-v1 / DRAFT / NOT YET RELEASED`
- Unit Contract: `draft-v1 / DRAFT / NOT YET RELEASED`
- Module / Capability Contract: `draft-v1 / DRAFT / NOT YET RELEASED`
- Workspace / Attempt / Record / Result Contract: `draft-v1 / DRAFT / NOT YET RELEASED`
- qzpack / Canonical Package Contract: `draft-v1 / DRAFT / NOT YET RELEASED`

检查时中央仓：

- releases: none
- tags: none

因此没有创建或假设 `contracts-v0.x.x` / `contracts-v1.0.0`。本仓采用 `pre-release / bootstrap baseline`，精确锁定上面的 commit SHA。未来不得实时跟随中央 `main`。

## 3. 已满足

### 3.1 Domain/Application 与 UI 分离 — 基本满足

仓库已经按 `application / domain / infrastructure / presentation` 分层；当前 `HANDOFF.md` 还明确规定核心评价器不得导入 Tk、Excel、Web 或文件扫描模块，Presentation 通过 Application Facade/API 调用核心。

这与 Architecture V2.1 的方向一致。当前不需要为了公共治理迁移 Tk/Web/Python UI 技术栈。

### 3.2 Canonical / 标准来源意识 — 已有较好基础

仓库存在：

- `src/equipeffi/standard_manifest.json`
- `src/equipeffi/resources/standards/`
- 标准来源页码、data_id、标准包状态、人工校对资产

当前业务治理已经强调标准 PDF / 人工复核证据优先、机器标准资源可追溯，并禁止按趋势猜标准值。

这为 Canonical-first 演进提供了基础。

### 3.3 Decimal 与可追溯计算 — 已有基础

仓库已有 `decimal_math.py`，使用 `Decimal` 进行插值、查表和数值处理；多个 evaluator 保存 `calculated_metrics / limits / comparisons / lookups / trace / standard_reference` 等结果证据。

这与 Numeric Contract 和 Result/Trace 的长期目标相容。

### 3.4 跨平台 UI/入口解耦方向 — 基本满足

当前已有 Desktop/Web/JSON/JSONL 等入口，并保留 Linux/Android 桥接方向；业务核心没有要求必须在线运行。Architecture V2.1 明确允许 EquipEffi 保持现有 Tk/Web 入口，因此不存在 UI 技术栈硬冲突。

## 4. 部分满足

### 4.1 Canonical-first — PARTIAL

当前标准数据已经数据化，但还没有完全达到中央 Canonical Envelope / Canonical Rule / qzpack 的公共格式。

真实差距：

- 标准资源主要是当前项目自己的 JSON/manifest；
- 部分复杂公式和适用逻辑仍在 Python evaluator 中；
- 尚未形成统一 `module_id / standard_id / rule_version / source_hash / review_status / payload` 外围；
- 尚未通过 qzpack package lifecycle 管理标准包。

Architecture V2.1 允许复杂标准保留 Versioned Domain Calculator，所以“Python 中仍有复杂专业算法”不是违规；长期需要让规则数据、Calculator version、来源和 Conformance 共同组成 Business Truth。

### 4.2 Numeric — PARTIAL

已有 Decimal 工具，但尚未采用正式发布的 Qingzhou Numeric Contract。

当前默认分支可见：

- `decimal_math.py` 有通用 `rounded(..., digits=6)`；
- 泵等复杂评价器使用 `sqrt / ln / exp/pow` 类非线性计算；
- 中央 D-001 对 transcendental reference procedure、跨语言 tolerance/precision 尚未冻结。

因此不能把本项目当前 Decimal 实现直接宣传为已经完全满足未来跨语言 Numeric v1。本次只登记差距，不改算法。

### 4.3 Unit — PARTIAL

当前设备字段和标准元数据中已经表达单位，且部分换算是显式的；但还没有公共 Unit Contract/UnitService、稳定 conversion_id/version，也未系统区分所有“单位换算”与“标准公式固有系数”。

本次不迁移现有公式。

### 4.4 Capability — PARTIAL

本项目已经有：

- 15 类公共设备类型；
- 17 个内部 profile；
- 标准包 active 状态；
- 各 profile 的评价能力和部分边界测试。

但没有中央 DRAFT 所描述的机器可读 Capability Manifest，尚未统一表达：

```text
module_id + profile_id + standard_id + feature_id + platform + status
```

现有 `active` 也不能等价为中央 `SUPPORTED`。

### 4.5 Result — PARTIAL

`EvaluationResult` 已有丰富结果、trace、source 和 data-quality 字段，但尚未形成公共 Result Envelope 要求的 module/standard/rule/calculator/numeric/package/version 快照外围。

本次不改模型或数据库。

### 4.6 Conformance — PARTIAL

本项目已有大量 unit/contract/integration 测试、评价矩阵和标准边界测试，具备演进为 Conformance Vectors 的真实基础。

但当前测试资产还不是中央仓最终的 platform-independent Conformance Vector Schema，中央 D-004 也仍未冻结。

## 5. 尚未实施

以下在默认分支没有证据表明已经按中央 Contract 完整实施：

- 稳定的 `module_id = qz.equipment_efficiency` 贯穿所有 Record/Result/Package；
- 机器可读 Module/Capability Manifest；
- 平台无关 Workspace Contract；
- Attempt 生命周期；
- 正式不可变 Record 生命周期与 Lineage；
- 完整 Result Envelope；
- qzpack Manifest/Hash/Signature/Stage/Atomic Activate/Rollback；
- 平台无关 `.qzproj` Workspace transport；
- 公共 UnitService；
- 正式公共 Numeric Conformance；
- 跨语言同一标准 Conformance 验收。

这些是后续演进项，不应因为 Architecture V2.1 已存在就伪称已经实现。

## 6. 当前冲突 / 差异

### 6.1 与 Architecture V2.1 FROZEN 的硬冲突

**未发现无法并存的硬冲突。**

现有分层、离线核心、标准数据化、可替换 UI、追溯方向总体与 V2.1 一致。未实施能力属于差距，不等同于冲突。

### 6.2 默认分支与活动开发治理分叉

本任务开始时默认 `master` 停留在 `19b628f...`，同时 open PR #1 的治理、Phase 1 Golden 和任务状态已经前进很多。

这是**仓库集成风险，不是 Qingzhou Contract 冲突**。

处理原则：

- QZC-A01 按用户要求从默认分支创建；
- 不把 PR #1 的未合并业务结论复制进本分支；
- 如果 PR #1 先合并，本 adoption 分支应 rebase/reconcile；
- 如果 adoption 先合并，PR #1 合并时应保留其业务治理，只把 Qingzhou Contracts 上位治理章节合入；
- 不允许一次 merge 冲突解决把任一侧治理整文件覆盖掉。

### 6.3 DRAFT Contract 与现实现差异

Numeric、Unit、Capability、Record、qzpack 仍是 DRAFT。本项目当前行为与其候选语义存在未完成映射，但 DRAFT 不能被当作 FROZEN 规则强制反向修改成熟业务代码。

## 7. RFC Candidates

本次未发现必须新建、且中央仓尚未记录的公共 Contract 缺口。

EquipEffi 的真实案例已经直接对应中央 `DECISIONS_NEEDED.md` 中的开放事项：

### D-001 — Transcendental Numeric reference procedure

- 公共问题：`sqrt / ln / fractional pow` 跨 Python/Kotlin/Swift/ArkTS 的末位一致性；
- 当前产品案例：GB 19762—2025 离心泵比转数和效率公式；
- 影响：Numeric Contract / numerical conformance；
- 建议：后续用正式泵 Golden/数值向量向 D-001 提供试点证据；**不新建重复 RFC**。

### D-005 — Recordable business outcomes by module

- 公共问题：Attempt 与 Record 的公共外围需要统一，但每个模块哪些业务状态允许正式保存必须自治；
- 当前产品案例：不在范围、无法判定、未达标、淘汰、等级结果等；
- 影响：Workspace/Attempt/Record/Result Contract；
- 建议：由 EquipEffi 业务规范后续明确 recordable outcome，再反馈中央；**不在本次 adoption 中决定**。

### D-006 — qzpack granularity

- 当前产品案例：一个标准可能对应多个设备 Profile/数据表；
- 建议：离心泵 prototype 可作为 qzpack 粒度试点之一；当前不全量迁移。

因此本报告记录：`new_rfc_candidates = 0`，`existing_central_open_decisions_relevant = D-001, D-005, D-006`。

## 8. 当前最小预留

为避免未来继续制造不兼容技术债，近期新工作只需要遵守这些低成本预留：

1. 新增公共外围数据时优先预留稳定 `module_id = qz.equipment_efficiency`；
2. 新增正式规则/阈值时继续使用可追溯十进制数据，避免新增 binary-float 权威链和无依据隐式修约；
3. 新增标准数据继续保存稳定 ID、版本、来源、页码/条款、hash/review 状态；
4. 新增正式结果外围时预留 rule/calculator/numeric/package/result contract version 字段，而不是把版本混成一个 app version；
5. 新增跨平台 Workspace/交换数据不得写入 Tk/Qt 控件对象、Windows 绝对路径或 Python pickle；
6. 新增发布能力声明应逐步细化到 profile/standard/feature/platform，并由对应 Conformance 保护；
7. 新增单位换算避免散落不可追溯的 `/1000`、`*10000`；如果数字是标准公式系数，则继续留在业务规则并记录来源；
8. 新增标准包相关设计优先考虑 Canonical 可重建、hash/provenance、版本不可静默替换和历史可追溯。

这些是设计预留，不授权本任务修改现有业务实现。

## 9. 当前不做

QZC-A01 明确不做：

- 不合并三个业务仓库；
- 不开发 Suite；
- 不开发 Android/HarmonyOS/iOS；
- 不重写 Native Core；
- 不创建公共 Python package；
- 不把所有复杂算法 DSL 化；
- 不把现有标准全量 qzpack 化；
- 不迁移数据库；
- 不重写成熟 Tk/Web UI；
- 不修改业务 evaluator/calculator；
- 不修改标准 Canonical 数值；
- 不修改中央 Qingzhou Contract；
- 不把 DRAFT Contract 标成 FROZEN；
- 不发布虚构的 `contracts-v1.0.0`。

## 10. Adoption 结论

**PASS（治理接入层）**，但带有明确 integration caution：

- 已存在可锁定的 `Architecture V2.1 FROZEN`；
- 没有正式 Contract release/tag，因此本仓锁定 `Qingzhou-contracts@0cd74d783fa23add6dc881b408a8c8ba8503f8e8` 作为 `pre-release / bootstrap baseline`；
- 五组 Contract 仍全部保持 DRAFT；
- 未发现 Architecture V2.1 与当前 EquipEffi 无法并存的硬冲突；
- 本任务不声称当前业务代码已经实现全部公共 Contract；
- 本 adoption 分支与 open PR #1 存在治理文件合并风险，最终 merge 前必须 reconcile，禁止整文件覆盖另一侧治理。

本报告不是 Phase 1、产品功能或标准业务正确性的验收结论。
