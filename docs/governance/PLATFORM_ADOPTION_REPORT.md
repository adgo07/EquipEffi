# PLATFORM_ADOPTION_REPORT — QZC-A01 reapplication

日期：2026-09-28
业务仓：`adgo07/EquipEffi`
公共治理仓：`adgo07/Qingzhou-contracts`
模块：`qz.equipment_efficiency`
任务：在 Phase 1 已合并的最新 master 上重新落地公共治理接入；仅更新治理，不做业务重构。

## 1. Master 基线与阶段事实

- 本次分支基于最新 `master` SHA：`1a74ff4cc07e9068783a370ec4269e89245cef38`。
- 该 SHA 是 Phase 1 PR #1 的 merge SHA；旧 adoption 分支 `chore/qingzhou-contracts-adoption` 来自旧 master，只作为 Qingzhou-contracts 接入内容参考，不 rebase，也不整份复制其 `AGENTS.md`、`HANDOFF.md` 或 `TASK_STATE.md`。
- 当前 Phase 1 状态按 master 权威记录为 `PHASE_1_PASS`；Phase 2 为 `PHASE_2_READY`，尚未开始，仍需用户明确授权；自动继续为 `DISABLED`。
- 本次不修改 `ROADMAP.md`，并保留其中 Phase 1 出口、Phase 2 授权和现行路线约束。

## 2. Qingzhou-contracts 锁定基线

本仓锁定中央仓精确 commit：`0cd74d783fa23add6dc881b408a8c8ba8503f8e8`。该对象已从公共仓读取并核验；锁定内容为：

| 项目 | 状态 |
|---|---|
| Architecture | `V2.1 FROZEN` |
| Numeric Contract | `draft-v1 / DRAFT / NOT YET RELEASED` |
| Unit Contract | `draft-v1 / DRAFT / NOT YET RELEASED` |
| Module / Capability Contract | `draft-v1 / DRAFT / NOT YET RELEASED` |
| Workspace / Attempt / Record / Result Contract | `draft-v1 / DRAFT / NOT YET RELEASED` |
| qzpack / Canonical Package Contract | `draft-v1 / DRAFT / NOT YET RELEASED` |

本次采用 pre-release / bootstrap baseline，不虚构 release/tag，也不跟随中央 `main`。后续中央变化只有在本仓显式升级 `PLATFORM_BASELINE.md` 与 `platform-lock.json` 后才生效。

## 3. 与 Phase 1 的治理边界

最新 master 中已经通过的 Phase 1 治理保持权威。本次只把 Qingzhou-contracts 公共治理关系追加到现有治理入口，并更新中央锁定/差距报告；不覆盖或弱化：

- P1-G01～G06 的顺序、Phase 1 Exit Gate 与 Solution/Product Review 门禁；
- 已审阅的业务规范、多维状态模型、Numeric & Decision Contract V2 和 V1 Scope 映射；
- Canonical 标准事实、Approved pump_water Golden 0.4、Golden 历史/候选分层和 QA/P0 证据要求；
- Phase 2 必须取得用户明确授权、自动继续保持 `DISABLED` 的条件。

公共 Contract 约束跨产品的公共外围语义，不覆盖国家/行业标准原文、Canonical、单标准业务算法、已批准本地业务结论或 V1 发布决策。pump_water 的 Decimal50、`ns_raw`、公式、状态和 Golden 仍按本仓 Phase 1 冻结文件管理；本次没有改动这些内容。

## 4. 当前差距记录

当前分层和标准资源体系为未来公共 Contract 演进提供基础，但本次没有把“架构方向相容”写成“合同已经实现”：

- 本仓仍未完整实现机器可读 Module/Capability Manifest、公共 Workspace/Attempt/Record 生命周期和统一 Result Envelope；
- 现有标准 JSON/manifest 未全面转换为 qzpack；
- 已有 Decimal 计算与 trace，但中央 Numeric v1 仍为 DRAFT，尚不能据此声称跨语言数值 Conformance 已完成；
- 单位语义尚未统一接入 Unit Contract/UnitService；
- 已批准的 pump_water Golden 0.4 是本地业务回归 Oracle，并非中央平台无关 Conformance Vector Schema；
- 尚未完整实现公共 qzpack lifecycle、平台无关 Workspace transport 和跨平台公共 Conformance Schema。

这些是后续治理/演进差距，不是本次 QZC-A01 的业务失败，也不授权本次进入 Phase 2。未发现与 Architecture V2.1 FROZEN 无法并存的硬冲突。

## 5. RFC Candidate 结论

`new_rfc_candidates = 0`。本轮没有发现必须新增且中央仓尚未登记的公共 Contract 缺口。以下中央开放决策仍与本项目有关，应沿中央流程处理，不在 EquipEffi 重复定义：

- **D-001**：跨语言 `sqrt`、`ln`、fractional `pow` 等非线性数值函数的 reference procedure；已批准 pump_water 数值案例可作为未来讨论证据，但不代表中央 Numeric Contract 已冻结。
- **D-005**：Record / Attempt 公共外围与各业务模块可正式记录的 outcome 范围；Pump 多维业务状态仍由本地业务契约定义。
- **D-006**：qzpack 粒度；本地标准/profile 关系可作为未来试点输入，本次不决定迁移粒度。

## 6. 文件范围与结果

本次变更范围限定为：

- `AGENTS.md`：在当前 master 治理上追加公共治理章节，明确 Phase 1 已批准状态优先、Phase 2 授权要求和中央锁规则；
- `HANDOFF.md`：最小追加本次接入事实，不覆盖 Phase 1 交接内容；
- `TASK_STATE.md`：最小追加 QZC-A01 状态和中央基线，不改变 Phase 1 状态；
- `PLATFORM_BASELINE.md`、`platform-lock.json`：记录并锁定批准的中央 SHA；
- `docs/governance/PLATFORM_ADOPTION_REPORT.md`：记录本次实际 master 基线、差距及 RFC 结论。

没有修改 `src/`、evaluator、pump calculator、Canonical、Golden、Schema、数据库、Excel、UI、测试业务预期或 Phase 1 冻结业务结论。本报告记录治理接入事实，不是 Phase 2 授权，也不重新评定 Phase 1。
