roadmap: EquipEffi V2.2
phase: Phase 1
goal: Submit the Phase 1 review package after P1-G01 through P1-G06
status: BLOCKED
next_status: PENDING_FIXED_SHA_INDEPENDENT_REVIEW
base_sha: 3e8ff4eb3f13593d2d223e7b98373311d2e85d7f
baseline_ref: pre-v2-rebaseline
working_tree_at_start: managed clean worktree from exact base SHA; original dirty worktree remains untouched
allowed_next: after the formal 18-case Golden 0.4 approval commit is pushed and its Windows CI is confirmed, stop for independent fixed-SHA re-review and Solution/Product Review; no Phase 1 PASS, PR merge, or Phase 2
automatic_continuation: DISABLED
phase_0b: NOT_EXECUTED
phase_1_hotfix: NOT_EXECUTED
blocked_by: FIXED_SHA_INDEPENDENT_REVIEW; SOLUTION_PRODUCT_REVIEW
evidence_needed: Validate all 7 immutable 0.1 records, 26 unchanged original 0.3 candidates, 3 unchanged replacements, 18 approved 0.4 records and negative probes with the real external evidence root; run the specified focused and full unittest checks, compileall and diff check; confirm Windows CI on the final SHA; then obtain independent fixed-SHA review and Solution/Product Review. Golden named-human approval is RESOLVED.
affected_scope: 18 formally approved pump_water Golden 0.4 records, P1-G04 governance/reporting, and required verification only; no evaluator, Decimal math, ns_raw, formula, Canonical, OOS, V1 scope, pump_chemical release, motor, or Phase 2 changes.
next_action: Push the approved Golden 0.4 and governance update to PR #1, confirm Windows CI on the resulting fixed SHA, then stop and hand that SHA to the independent reviewer and Solution/Product Review; do not merge.
last_verified: 2026-09-28: External-evidence validator passed with 25 official/historical cases, 26 original candidates, 3 replacements and 18 review records; errors=0, open_evidence_flags=0, 3 expected negative-probe rejections; external GB PDF SHA-256 matched 7F515D8B9D6B4D2AB97FFA7BECB78520BA0579CFBD6D5ECA10C7E7CC77895FEC. Focused pump/schema/application/boundary/golden tests: 164 pass; metadata/architecture/evaluator matrix: 394 pass; full unittest: 931 total, 924 pass, 3 known V4 motor failures, 1 known wheel audit error, 3 skips, 0 new regression; compileall and git diff --check pass; final-SHA Windows CI is to be verified after push.
acceptance_history: 2026-09-22 initially BLOCKED for uncommitted governance deliverables, incomplete evidence fields, non-uniform QA tables and missing demand/value evidence; corrected and revalidated without business-code changes; 2026-09-23 product decision recorded by 王玮（总经理） for transformer and centrifugal_pump public types, with pump_water as the evidence-backed IN_V1 profile; R01-R07 independent technical acceptance was completed at 3101e05; P1-G04-R1 provenance closure at the approved baseline left 0.1 historical, 26 original 0.3 candidates pending and 18 review records ready; on 2026-09-28 王玮（GB 19762—2025 离心泵标准负责人） explicitly approved all 18 Golden 0.4 records, resolving GOLDEN_CASE_NAMED_HUMAN_APPROVAL_PENDING; fixed-SHA independent review and Solution/Product Review remain.
authoritative_files: ROADMAP.md; HANDOFF.md; TASK_STATE.md; AGENTS.md; BASELINE.md; ASSET_AUDIT.md; QA_BACKLOG.md; V1_SCOPE.md; ADR/
historical_routes: v7-v15; T04.xx; HANDOFF_20260831.md; numbered execution checklists
