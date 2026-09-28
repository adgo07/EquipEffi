# pump_water Golden 与候选治理

本目录中的 7 个 `golden-case-0.1` 文件是**历史冻结记录**。它们的字节、历史状态和证据 hash 均保持原样；不会被改写为 `APPROVED`，也不会作为正式 V2 Golden。

## 三层关系

| 层 | 内容 | 当前状态 | 用途 |
|---|---|---|---|
| Golden 0.1 | 本目录既有 7 个案例 | 历史冻结；不升级、不批准 | 保存旧版历史证据 |
| Golden 0.3 | [`pump_e2e_v0_3_candidates.jsonl`](../pump_e2e_v0_3_candidates.jsonl) 共 26 条：18 条 `pump_water` Application E2E、8 条 `pump_chemical` technical-only | 全部 `DRAFT/PENDING` | 候选池；本轮不改写 |
| Golden 0.4 | 本目录新增的 18 条正式 V2 Golden | 王玮已逐案批准；三个状态均为 APPROVED | 正式业务回归 Oracle |

审批依据材料保存在 pump_water_approval_review/README.md，18 条原始 review records 仍作为候选来源与审核档案保留；每条正式记录通过版本化来源注册表引用原始 0.3 清水候选或对应 replacement candidate，并验证 case_id、schema 版本、来源文件、文件/记录 SHA、baseline SHA 与逐字段业务 payload。正式目录中的 18 条 golden-case-0.4 均为 APPROVED/APPROVED/APPROVED，review_owner=王玮，review_flags=[]。原始 0.3 26 条记录未改。石化 8 条候选仍是技术诊断材料，当前公共应用路由 NOT_IN_RELEASE_SCOPE，不得晋升为 Windows V1 Golden。

## 正式 0.4 审批记录

正式 schema 为 [`golden_case_0_4.schema.json`](../../schemas/golden_case_0_4.schema.json)，要求：

- `case_status = approval_status = review_status = APPROVED`；
- 真实具名 `review_owner`、带时区的 `reviewed_at` / `approved_at`；
- 非空 `approval_basis`、明确 `known_limits`；
- `provenance` 指向固定的 0.3 `pump_water` Application E2E `case_id`、文件/行和 canonical JSON SHA-256；候选原始输入、期望结果、计算 trace、source sidecar 和 notes 必须逐字段一致；`review_flags` 必须为空，所有 source-evidence 问题都已解决。

王玮作为 GB 19762—2025 离心泵标准负责人，已于 2026-09-28T11:03:04+08:00 完成 18 条记录的具名批准。正式文件保留 review/candidate 的已审业务 payload 与来源 provenance；approval basis 和适用限制随每条正式记录保存。Golden named-human approval gate 为 RESOLVED。

## 标准证据与复验

标准 PDF 不提交到 Git。证据注册表固定其 SHA-256 和相对定位符；本机复验需通过 `--external-evidence-root` 或 `EQUIPEFFI_EXTERNAL_EVIDENCE_ROOT` 提供标准目录。CI 使用 `--skip-external-evidence` 时只验证 schema、registry pins、仓库文件 hashes 和候选 provenance，并明确报告外部 PDF 字节检查已跳过。

```powershell
python tools/validate_phase1_contracts.py `
  --negative-probe `
  --candidate-jsonl specs/equipment_efficiency/golden/pump_e2e_v0_3_candidates.jsonl `
  --candidate-jsonl specs/equipment_efficiency/golden/pump_water_replacement_candidates_v0_1.jsonl `
  --approval-review-dir specs/equipment_efficiency/golden/pump_water_approval_review `
  --external-evidence-root <包含注册标准相对路径的目录>
```

3 条 replacement candidate 已分别将 Canonical `stable_data_ids` 对齐到 trace T3-09、T3-10、T3-05；原始 0.3 记录没有改写，替代来源由注册表/hash validator 验证。精确表3边界由 generated boundary test 负责，首批人工 Golden 不要求重复穷举端点。该测试覆盖全部 water Canonical 行的 q_min/q_max 等值及两侧 ±1e-6；人工 review package 只保留必要代表场景，不要求新增 Q=5/Q=300 Golden。

当前 P1-G04 的具名 Golden 批准门禁为 RESOLVED。Phase 1 仍 BLOCKED，待正式批准落库 SHA 的独立复验及 Solution/Product Review；不得据此宣布 Phase 1 PASS 或进入 Phase 2。
