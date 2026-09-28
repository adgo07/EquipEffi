# pump_water Golden 与候选治理

本目录中的 7 个 `golden-case-0.1` 文件是**历史冻结记录**。它们的字节、历史状态和证据 hash 均保持原样；不会被改写为 `APPROVED`，也不会作为正式 V2 Golden。

## 三层关系

| 层 | 内容 | 当前状态 | 用途 |
|---|---|---|---|
| Golden 0.1 | 本目录既有 7 个案例 | 历史冻结；不升级、不批准 | 保存旧版历史证据 |
| Golden 0.3 | [`pump_e2e_v0_3_candidates.jsonl`](../pump_e2e_v0_3_candidates.jsonl) 共 26 条：18 条 `pump_water` Application E2E、8 条 `pump_chemical` technical-only | 全部 `DRAFT/PENDING` | 候选池；本轮不改写 |
| Golden 0.4 | 本目录以后新增的正式 V2 Golden | 只有标准负责人逐条批准后，才允许三个状态均为 `APPROVED` | 正式业务回归 Oracle |

待人工复核材料位于 [`pump_water_approval_review/README.md`](../pump_water_approval_review/README.md)，每条记录独立对应一条 0.3 清水候选并固定来源行 hash。复核材料使用 `golden-case-0.4-review`，状态为 `PENDING_APPROVAL/PENDING/PENDING`；其中 3 条 source-sidecar Canonical ID 与 trace rule 不一致，已标记且不得批准。它不是正式 Golden。石化 8 条候选仍是技术诊断材料，当前公共应用路由 `NOT_IN_RELEASE_SCOPE`，不得晋升为 Windows V1 Golden。

## 正式 0.4 批准条件

正式 schema 为 [`golden_case_0_4.schema.json`](../../schemas/golden_case_0_4.schema.json)，要求：

- `case_status = approval_status = review_status = APPROVED`；
- 真实具名 `review_owner`、带时区的 `reviewed_at` / `approved_at`；
- 非空 `approval_basis`、明确 `known_limits`；
- `provenance` 指向固定的 0.3 `pump_water` Application E2E `case_id`、文件/行和 canonical JSON SHA-256；候选原始输入、期望结果、计算 trace、source sidecar 和 notes 必须逐字段一致；`review_flags` 必须为空，所有 source-evidence 问题都已解决。

只有标准负责人完成逐条业务复核、作出批准决定并将正式 0.4 文件放入本目录后，validator 才会把该记录作为正式 Golden 接受。本轮没有代替标准负责人批准任何案例。

## 标准证据与复验

标准 PDF 不提交到 Git。证据注册表固定其 SHA-256 和相对定位符；本机复验需通过 `--external-evidence-root` 或 `EQUIPEFFI_EXTERNAL_EVIDENCE_ROOT` 提供标准目录。CI 使用 `--skip-external-evidence` 时只验证 schema、registry pins、仓库文件 hashes 和候选 provenance，并明确报告外部 PDF 字节检查已跳过。

```powershell
python tools/validate_phase1_contracts.py `
  --negative-probe `
  --candidate-jsonl specs/equipment_efficiency/golden/pump_e2e_v0_3_candidates.jsonl `
  --approval-review-dir specs/equipment_efficiency/golden/pump_water_approval_review `
  --external-evidence-root <包含注册标准相对路径的目录>
```

当前 18 条候选中有 3 条 Canonical 行 ID 问题（T3-09/T3-10 缺失、T3-05 对应到 T3-01），已在复核包标记，解决前不能批准；精确流量端点等值案例仍保存在冻结的 0.1 历史材料中；当前 18 条 0.3 清水候选含 Q=4.9 的下界外侧案例，但不含 Q=5、Q=300 等精确等值端点。若标准负责人要求这些精确边界成为正式 0.4 Golden，需另行形成并评审新版本候选，不能改写 0.3 或晋升 0.1。

当前 P1-G04 保持 `BLOCKED` 直至具名标准批准、固定 SHA 独立复验及 Solution/Product Review 完成；不得据此宣布 Phase 1 PASS 或进入 Phase 2。
