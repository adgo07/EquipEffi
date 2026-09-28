# Pump V2 R01–R06 Commit Manifest

Date: 2026-09-27
New branch: phase1/pump-v2-r01-r06
Base commit: 9e413051177fbfa7f1b217de17d344f33176b152
Source worktree: G:/Python Project/EquipEffi
Target worktree: C:/Users/WANGWEI/.codex/worktrees/phase1-pump-v2-r01-r06/EquipEffi

## Commit shape

Use one combined commit for the V2 baseline and R01–R06 closure. The source worktree contains no committed or preserved snapshot of the exact V2-only intermediate state: core files such as pump.py and evaluation_service.py interleave the authorized contract implementation and R01/R02 corrections. Splitting them would require reconstructing an unaudited intermediate evaluator and risks changing frozen semantics. The single commit attributes every included file below.

No Golden Case is approved by this manifest. All candidate cases remain DRAFT/PENDING. Phase 1 remains BLOCKED pending fixed-SHA independent review and the existing named Golden/Solution-Product gates.

## Frozen boundaries checked

- Keep the current Decimal50 numeric implementation, ns_raw range and row selection, GB 19762-2025 formulas, total QBEP/HBEP and explicit suction/stages conversions byte-for-byte from the reviewed source state.
- Keep the previously authorized Canonical T3-08 C2=142.33 correction; do not change any other standard constant. Preserve T3-09 C3=144.33.
- Preserve the established OOS policy and the frozen V1 profile scope: pump_water remains the V1 candidate; pump_chemical remains UNDER_REVIEW and NOT_IN_RELEASE_SCOPE at the public application boundary.
- Do not modify non-pump release-audit behavior, existing motor failures, Phase 2 features, old official Golden hashes, or original-worktree files.

## Included file manifest

| File | Change | Owner | Why required | Source worktree path | Prior history |
|---|---|---|---|---|---|
| src/equipeffi/domain/evaluation/evaluators/pump.py | Modify | V2 baseline / R01 | Implements the already authorized V2 pump contract and distinguishes present-invalid values from missing values; preserve the reviewed numeric core unchanged. | G:/Python Project/EquipEffi/src/equipeffi/domain/evaluation/evaluators/pump.py | Existing uncommitted V2 implementation; R01 fix is in the same file and has no safe intermediate snapshot. |
| src/equipeffi/application/services/evaluation_service.py | Modify | R02 / R06 | Supplies release support status at the public application boundary, keeps unsupported/unresolved routing explicit, and repairs the as-of helper placement. | G:/Python Project/EquipEffi/src/equipeffi/application/services/evaluation_service.py | Existing uncommitted V2 implementation plus R02 correction; no safe intermediate snapshot. |
| src/equipeffi/application/services/input_normalization.py | Modify | V2 baseline | Maps the canonical raw pump names and legacy aliases without changing numeric meaning. | G:/Python Project/EquipEffi/src/equipeffi/application/services/input_normalization.py | Existing uncommitted V2 input-contract change. |
| src/equipeffi/domain/common/enums.py | Modify | V2 baseline / R02 | Adds explicit pump applicability and release-gate conclusions used by the result contract. | G:/Python Project/EquipEffi/src/equipeffi/domain/common/enums.py | Existing uncommitted V2 result-contract change. |
| src/equipeffi/domain/common/models.py | Modify | V2 baseline / R02 | Adds support, category, evaluation, grade and issue-code result fields required by the V2 contract. | G:/Python Project/EquipEffi/src/equipeffi/domain/common/models.py | Existing uncommitted V2 result-contract change. |
| src/equipeffi/domain/evaluation/device_specs.py | Modify | V2 baseline / R05 | Projects the explicit pump input contract and frozen suction enum into the form schema. | G:/Python Project/EquipEffi/src/equipeffi/domain/evaluation/device_specs.py | Existing uncommitted pump metadata change. |
| src/equipeffi/domain/evaluation/device_types.py | Modify | V2 baseline / R02 | Routes from canonical product_type while retaining category as a compatibility alias. | G:/Python Project/EquipEffi/src/equipeffi/domain/evaluation/device_types.py | Existing uncommitted pump routing change. |
| src/equipeffi/domain/evaluation/metadata.py | Modify | R05 | Makes the pump V4 field and EV_SUCTION projections agree with the frozen metadata contract. | G:/Python Project/EquipEffi/src/equipeffi/domain/evaluation/metadata.py | Existing uncommitted pump metadata projection change. |
| src/equipeffi/entrypoint.py | Modify | V2 baseline | Keeps the public pump example explicit and sends decimal inputs as text. | G:/Python Project/EquipEffi/src/equipeffi/entrypoint.py | Existing uncommitted pump example change. |
| src/equipeffi/infrastructure/standards/json_repository.py | Modify | V2 baseline | Parses pump JSON decimal literals as Decimal without changing other package loaders. | G:/Python Project/EquipEffi/src/equipeffi/infrastructure/standards/json_repository.py | Existing uncommitted pump precision-preservation change. |
| src/equipeffi/presentation/api/application_api.py | Modify | R02 | Allows the public centrifugal-pump API to represent supported, not-applicable and not-in-release-scope outcomes. | G:/Python Project/EquipEffi/src/equipeffi/presentation/api/application_api.py | Existing uncommitted pump API contract change. |
| src/equipeffi/presentation/web/server.py | Modify | V2 baseline | Preserves pump decimal text through the web request instead of converting it to binary float in JavaScript. | G:/Python Project/EquipEffi/src/equipeffi/presentation/web/server.py | Existing one-line pump input precision change; no broader UI feature. |
| src/equipeffi/resources/standards/pump.json | Modify | V2 baseline | Carries only the previously authorized T3-08 C2=142.33 correction needed by this V2 baseline. | G:/Python Project/EquipEffi/src/equipeffi/resources/standards/pump.json | Prior authorized change existed before R01–R06; HEAD value was 144.33. No other canonical row may change. |
| src/equipeffi/standard_manifest.json | Modify | V2 baseline | Records the version of the shared pump resource containing the authorized C2 correction. | G:/Python Project/EquipEffi/src/equipeffi/standard_manifest.json | Existing uncommitted manifest version update. |
| specs/equipment_efficiency/profiles/pump_water.md | Modify | V2 baseline / R01 / R05 | Records the active water-pump contract, explicit input/status semantics, and C2 source fingerprint; remains a draft for review. | G:/Python Project/EquipEffi/specs/equipment_efficiency/profiles/pump_water.md | Existing uncommitted V2 mapping. Historical appendix remains explicitly historical. |
| specs/equipment_efficiency/profiles/pump_chemical.md | Add and scope-correct | R02 / R03 | Documents technical-only diagnostics and the public NOT_IN_RELEASE_SCOPE gate without promoting chemical pumps into frozen V1 scope. | G:/Python Project/EquipEffi/specs/equipment_efficiency/profiles/pump_chemical.md | New untracked draft in source; corrected in the clean worktree to preserve V1_SCOPE and remove a reference to an absent crosswalk artifact. |
| specs/equipment_efficiency/schemas/golden_case_0_2.schema.json | Add | R04 | Supports explicit versioned reading of prior 0.2 evidence without refreshing historical hashes. | G:/Python Project/EquipEffi/specs/equipment_efficiency/schemas/golden_case_0_2.schema.json | New untracked schema from the V2 work. |
| specs/equipment_efficiency/schemas/golden_case_0_3.schema.json | Add | R03 / R04 | Defines the current draft candidate shape and versioned source-reference fields, including the cross-checkout text SHA-256 normalization contract. | G:/Python Project/EquipEffi/specs/equipment_efficiency/schemas/golden_case_0_3.schema.json | New untracked schema from the V2 work. |
| specs/equipment_efficiency/golden/pump_e2e_v0_3_candidates.jsonl | Add and pin | R03 / R04 | Provides 26 DRAFT/PENDING cases: 18 water Application E2E candidates and 8 chemical technical diagnostics only. Repository-text sidecar hashes pin committed LF-canonical content so Windows checkout EOL settings do not stale the evidence. | G:/Python Project/EquipEffi/specs/equipment_efficiency/golden/pump_e2e_v0_3_candidates.jsonl | New untracked candidate stream; source pins were corrected to the committed content digest after fresh-checkout replay exposed raw CRLF sensitivity. Replaces neither the original seven cases nor their approvals. |
| tools/validate_phase1_contracts.py | Modify | R04 | Validates schema versions 0.1/0.2/0.3; normalizes CRLF to LF only for repository text SHA-256, leaves external/non-text hashes on raw bytes, and recognizes only the exact registered 0.1 Canonical path/catalog/hash as historical; unknown mismatches remain errors. | G:/Python Project/EquipEffi/tools/validate_phase1_contracts.py | Existing uncommitted validator update; new 0.3 sidecars pin committed content; no old case hash refresh is included. |
| tools/audit_release.py | Modify | R01 | Updates only pump example, invalid-stage and pump range-miss diagnostics; no non-pump release-audit behavior is included. | G:/Python Project/EquipEffi/tools/audit_release.py | Existing uncommitted pump-only audit change. |
| tests/unit/test_application_api.py | Modify | R02 | Asserts the public pump release-status outcomes in the API contract. | G:/Python Project/EquipEffi/tests/unit/test_application_api.py | Existing uncommitted pump-only expectation. |
| tests/unit/test_device_evaluator_matrix.py | Modify, pump hunks only | V2 baseline / R01 | Adds pump explicit inputs and assertions for invalid-versus-missing states, decimal values and profile behavior. Only pump inputs use decimal text in the targeted test; the generic all-device value-type hunk is restored to HEAD, preserving non-pump baseline inputs. | G:/Python Project/EquipEffi/tests/unit/test_device_evaluator_matrix.py | Existing uncommitted mixed pump test changes; non-pump hunk deliberately omitted. |
| tests/unit/test_pump_numeric_contract_v2.py | Add | Test | Rechecks the frozen Decimal50 and comparator contract against independent fixed expected values. | G:/Python Project/EquipEffi/tests/unit/test_pump_numeric_contract_v2.py | New untracked focused test. |
| tests/unit/test_pump_generated_boundaries_v2.py | Add | Test | Rechecks generated raw-flow and ns_raw boundary behavior without changing the production boundaries. | G:/Python Project/EquipEffi/tests/unit/test_pump_generated_boundaries_v2.py | New untracked focused test. |
| tests/unit/test_pump_rule_integrity_v2.py | Add | Test | Rechecks canonical rows, coefficients, identities and unchanged C2/C3 values. | G:/Python Project/EquipEffi/tests/unit/test_pump_rule_integrity_v2.py | New untracked focused test. |
| tests/unit/test_pump_golden_case_0_3.py | Add | R03 / Test | Replays the 26 versioned draft candidates and checks the water Application E2E versus chemical technical-only split. | G:/Python Project/EquipEffi/tests/unit/test_pump_golden_case_0_3.py | New untracked focused test; cases remain unapproved. |
| tests/unit/test_golden_case_schema_0_2.py | Add / extend | R04 / Test | Verifies the seven frozen 0.1 case files are not rewritten, accepts only the registered historical Canonical hash, rejects an unknown historical hash, validates all 26 candidate source pins, checks CRLF/LF-stable repository text hashes, and covers the explicit 0.2 schema. | G:/Python Project/EquipEffi/tests/unit/test_golden_case_schema_0_2.py | New untracked focused test with R04 regressions for historical identity, unknown hashes, cross-checkout normalization, and candidate source references. |
| docs/PUMP_NUMERIC_AND_DECISION_CONTRACT_V2.md | Add | V2 baseline / Governance | Records the frozen pump input, calculation, status, candidate and release-gate contract used by this implementation. | G:/Python Project/EquipEffi/docs/PUMP_NUMERIC_AND_DECISION_CONTRACT_V2.md | New untracked user-authorized V2 contract; wording is aligned to the unchanged V1_SCOPE. |
| docs/pump_v2_independent_formal_acceptance_20260927.md | Add unchanged | Governance | Preserves the independent source report that defines R01–R06 and the exact repair scope; remains a historical BLOCKED report, not an approval. | G:/Python Project/EquipEffi/docs/pump_v2_independent_formal_acceptance_20260927.md | New untracked independent report; immutable source artifact. |
| ROADMAP.md | Modify minimally | R06 / Governance | Updates only the current next step and scope statement to show R01–R06 work followed by fixed-SHA re-review; Phase 1 remains blocked. | G:/Python Project/EquipEffi/ROADMAP.md | Start from the specified base, not the source worktree diff; prior Phase 1/Phase 0 history retained. |
| HANDOFF.md | Modify minimally | R06 / Governance | Replaces stale current-state claims with the authorized pump revision, test evidence and the original independent-review next step. | G:/Python Project/EquipEffi/HANDOFF.md | Start from the specified base; historical sections retained and dated. |
| TASK_STATE.md | Modify minimally | R06 / Governance | Records the exact worktree base, current BLOCKED state, R01–R06 scope and remaining independent-review/approval gates. | G:/Python Project/EquipEffi/TASK_STATE.md | Start from the specified base; historical acceptance history retained. |
| QA_BACKLOG.md | Modify minimally | R06 / Governance | Records remediation evidence without reclassifying any P0, declaring business approval or closing legacy motor/wheel issues. | G:/Python Project/EquipEffi/QA_BACKLOG.md | Start from the specified base; original issue classifications retained. |
| BASELINE.md | Modify minimally | Governance | Appends the before/after canonical resource hash and exact C2 correction; preserves the immutable Phase 0 baseline. | G:/Python Project/EquipEffi/BASELINE.md | Start from the specified base; Phase 0 entries remain unchanged. |
| IMPLEMENTATION_REPORT.md | Add fresh | R06 / Test / Governance | Records exact clean-worktree commands, environment, runtimes and pass/fail/error/skip/not-run results from this run. | G:/Python Project/EquipEffi/IMPLEMENTATION_REPORT.md | The source-worktree draft is not copied; this report is generated from the isolated worktree results. |
| PUMP_V2_R01_R06_COMMIT_MANIFEST.md | Add | Governance | Provides this reviewed file-level allowlist and exclusion record. | C:/Users/WANGWEI/.codex/worktrees/phase1-pump-v2-r01-r06/EquipEffi/PUMP_V2_R01_R06_COMMIT_MANIFEST.md | New file in the isolated worktree. |

## Source-worktree changes deliberately not carried

At the source-worktree inventory checkpoint, Git reported 91 changed/untracked paths outside `.tmp_sheet_edit/` (34 tracked changes and 57 untracked files). Of these, 36 source paths are represented in the allowlist above; the remaining 55 are covered by the path-specific decisions below and the historical-artifact review table. Git also reported 3,330 paths under `.tmp_sheet_edit/`; that directory and all of its contents were excluded without copying or editing.

| File or path | Decision and reason |
|---|---|
| HANDOFF_20260831.md | Excluded by user; unrelated historical tracked change. |
| .tmp_sheet_edit/** | Excluded in full by user; not inspected, copied, staged or changed. |
| tests/unit/test_release_audit.py | Excluded; source status is only CRLF/LF, with no textual Git diff. |
| Seven official Golden 0.1 files under specs/equipment_efficiency/golden/pump_water/ | Excluded; source diff refreshes old catalog/hash fields. The clean worktree retains base bytes and R04 validates them as historical. |
| The generic all-device values[field] test hunk in tests/unit/test_device_evaluator_matrix.py | Excluded; unrelated to pump scope and restored to the base value. |
| V1_SCOPE.md source-worktree diff | Excluded; frozen profile scope is unchanged. Clean-worktree V1_SCOPE remains authoritative. |
| Any non-pump portions of a release-audit change | Excluded; the only carried audit diff is pump-specific. |
| Original-worktree IMPLEMENTATION_REPORT.md | Not copied; replaced with a fresh report from this isolated test run. |
| docs/phase1_v2_r01_r06_worktree_inventory_20260927.md | Excluded; describes the original dirty worktree, not project runtime evidence. |
| .tmp_sheet_edit/node_modules/** | Excluded in full by user; no action taken. |

## Historical reports and one-time scripts reviewed but excluded

Each item below remains untouched in the source worktree. It is excluded because it is either a superseded Phase 1 case-closure/V0.2/V07 artifact, a one-time audit bound to historical external outputs, or an Excel/V5 workbook investigation outside this commit. The current V2 contract, 0.3 candidate stream, focused tests and formal R01–R06 source report are the durable evidence kept here.

| File | Long-term evidence decision |
|---|---|
| docs/pump_v2_independent_acceptance_20260927.py | Exclude: its checks mode requires the external historical ns_boundary_70_application_rerun.jsonl file absent from the clean checkout; targeted numeric/boundary tests are independently runnable and included. |
| docs/build_pump_human_review_20260927.py | Exclude: one-time generator of human decision aids; generated workbooks/reports are not implementation tests. |
| docs/extract_gb19762_pages_for_review.py | Exclude: one-time extraction of externally stored PDF pages; source path and hash remain in active profile documentation. |
| docs/phase1_case_closure_approval_package_20260926.md | Exclude: historical R2 draft approval package superseded by the current 0.3 candidate stream; it never approved cases. |
| docs/phase1_case_closure_execution_plan_20260926.md | Exclude: completed historical execution plan; not an active route or acceptance command. |
| docs/phase1_case_closure_execution_status_20260926.md | Exclude: historical run status tied to external R2 outputs. |
| docs/phase1_case_closure_independent_acceptance_20260926.md | Exclude: first-cycle case-closure decision; superseded by R2 and the current V2 formal report. |
| docs/phase1_case_closure_independent_acceptance_20260926_r2.md | Exclude: prior case-closure review and precision caveat; not the current R01–R06 review. |
| docs/phase1_case_closure_r2_package_smoke_20260926.py | Exclude: one-time smoke script for the historical R2 package. |
| docs/phase1_case_closure_r2_runner_20260926.py | Exclude: one-time candidate runner writing historical R2 outputs. |
| docs/phase1_case_source_decision_20260926.md | Exclude: historical source decision for the prior R2 case package; current candidate source contracts are versioned separately. |
| docs/phase1_independent_acceptance_20260926.py | Exclude: one-time first-cycle independent audit of historical case inputs. |
| docs/phase1_independent_acceptance_r2_20260926.py | Exclude: one-time R2 independent replay bound to old output artifacts. |
| docs/phase1_pump_numeric_contract_checks_20260927.py | Exclude: DEV_ONLY primitive checks that do not invoke the production evaluator; current production numeric tests are included. |
| docs/phase1_pump_numeric_contract_test_log_20260927.md | Exclude: log for the excluded DEV_ONLY helper checks; not production evaluator evidence. |
| docs/phase1_pump_unified_approval_package_20260927.md | Exclude: historical 73-row V07 draft package; superseded by the 26 versioned V0.3 candidates. |
| docs/phase1_pump_unified_contract_20260927.md | Exclude: explicitly historical V0.2 contract superseded by the included V2 contract. |
| docs/phase1_pump_unified_execution_plan_20260927.md | Exclude: historical execution plan with old task/goal routing; no current scheduling authority. |
| docs/phase1_pump_unified_execution_status_20260927.md | Exclude: historical V07 execution status and candidate counts. |
| docs/phase1_pump_unified_final_checks_20260927.py | Exclude: one-time checks over historical output paths and V07 approval state. |
| docs/phase1_pump_unified_independent_audit_20260927.py | Exclude: one-time API replay audit for the superseded V07 evidence package. |
| docs/phase1_pump_unified_independent_final_20260927.md | Exclude: historical acceptance of V07 with open business decisions; not the current R01–R06 acceptance source. |
| docs/phase1_pump_unified_independent_review_20260927.md | Exclude: first-cycle V07 review, superseded by the later final disposition and current formal report. |
| docs/phase1_pump_unified_independent_review_v07_20260927.md | Exclude: intermediate review progress record, not current acceptance authority. |
| docs/phase1_pump_unified_package_smoke_20260927.py | Exclude: one-time resource/Application smoke for the old V07 package; covered by current contract and integration tests. |
| docs/phase1_pump_unified_runner_20260927.py | Exclude: one-time V07 runner that emits a superseded candidate package. |
| docs/phase1_pump_unified_source_audit_20260927.py | Exclude: one-time source audit importing the historical first-cycle acceptance script. |
| docs/pump_acceptance_20260926.mjs | Exclude: one-time workbook performance/structure audit tied to external outputs and artifact-tool. |
| docs/pump_acceptance_structure_20260926.py | Exclude: one-time Excel workbook structure audit tied to external task output paths. |
| docs/pump_c2_excel_followup_20260926.md | Exclude: historical Excel follow-up outside current runtime scope; the authorized C2 value and source fingerprint are recorded in the current Canonical/profile evidence. |
| docs/pump_independent_acceptance_20260926.md | Exclude: V5 workbook R1 acceptance report; not the current evaluator contract. |
| docs/pump_independent_acceptance_20260926_r2.md | Exclude: V5 workbook R2 report and performance/Excel gate, outside this commit. |
| docs/pump_v5_candidate_r2_builder.py | Exclude: one-time builder for a separate V5 workbook artifact. |
| docs/pump_v5_execution_status_20260926.md | Exclude: historical V5 R1 workbook status, superseded by its R2 record and unrelated to evaluator changes. |
| docs/pump_v5_execution_status_20260926_r2.md | Exclude: V5 workbook status; no runtime source, test or frozen contract change. |
| docs/pump_v5_optimization_plan_20260926.md | Exclude: revoked performance target/workbook plan; no longer an authorized product change. |
| docs/pump_v5_r2_audit.py | Exclude: one-time audit of an external workbook candidate. |
| docs/pump_v5_r2_bench_recalc.mjs | Exclude: one-time spreadsheet recalculation benchmark; user no longer requires a speed target. |
| docs/pump_v5_r2_bench_total.mjs | Exclude: one-time workbook total-runtime benchmark; not part of Python evaluator acceptance. |
| docs/pump_v5_r2_evaluate.mjs | Exclude: one-time artifact-tool workbook evaluator, not production Python logic. |
| docs/pump_v5_r2_extras.mjs | Exclude: one-time supplemental workbook output checks. |
| docs/pump_v5_r2_oracle.py | Exclude: workbook-specific oracle bound to V5 artifacts; the included reviewer harness independently checks the production V2 contract. |
| docs/离心泵_人工复核明细_20260927.md | Exclude: human decision aid for historical V07 candidates; not an approval record and superseded by current V0.3 candidate identities. |
| docs/离心泵_需要决定的事项_20260927.md | Exclude: business decision aid for historical V07; no decisions are made by this commit. |

## Post-commit record

The commit SHA and fresh-worktree verification SHA are reported in the execution handoff after commit. They are not embedded here because a commit cannot contain its own final SHA without changing that SHA.
