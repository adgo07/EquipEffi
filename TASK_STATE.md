roadmap: EquipEffi V2.2
phase: Phase 1
goal: Submit the Phase 1 review package after P1-G01 through P1-G06
status: BLOCKED
next_status: PENDING_FIXED_SHA_INDEPENDENT_REVIEW
base_sha: 9e413051177fbfa7f1b217de17d344f33176b152
baseline_ref: pre-v2-rebaseline
working_tree_at_start: managed clean worktree from exact base SHA; original dirty worktree remains untouched
allowed_next: finish the authorized R07 PR update and fixed-SHA checks in the independent worktree; then stop and wait for the original independent formal review; Golden approval and Solution/Product Review remain open; Phase 2 disabled
automatic_continuation: DISABLED
phase_0b: NOT_EXECUTED
phase_1_hotfix: NOT_EXECUTED
blocked_by: PENDING_FIXED_SHA_INDEPENDENT_REVIEW; GOLDEN_CASE_APPROVAL_PENDING; SOLUTION_PRODUCT_REVIEW
evidence_needed: Record the exact isolated-worktree verification and GitHub Windows CI result; review only the pushed fixed commit SHA in the original independent session. All 26 current candidates remain DRAFT/PENDING; no Golden or Phase 1 approval.
affected_scope: Authorized pump V2/R01-R07 source, schemas, draft candidates, direct tests, Windows CI and minimal governance only; no Decimal50/ns_raw/formula/C2/OOS/V1 scope, motor or Phase 2 change.
next_action: After pushing the reviewed R07 allowlist and checking Windows CI, hand the exact fixed SHA to the original independent formal acceptance session, then stop.
last_verified: 2026-09-28: R07 implementation replay in the isolated branch worktree passed 157 pump/routing tests, 394 metadata/architecture/matrix tests, both external-evidence validator modes, and compile/diff checks; full unittest is 921 total with the same 3 V4 motor failures, 1 wheel audit error and 3 skips. Exact final SHA and GitHub CI result are reported in the execution handoff.
acceptance_history: 2026-09-22 initially BLOCKED for uncommitted governance deliverables, incomplete evidence fields, non-uniform QA tables and missing demand/value evidence; corrected and revalidated without business-code changes; 2026-09-23 product decision recorded by 王玮（总经理） for transformer and centrifugal_pump public types, with pump_water as the evidence-backed IN_V1 profile; subsequent acceptance found the Golden approval gate unmet because all seven cases remain REVIEWED with placeholder review_owner
authoritative_files: ROADMAP.md; HANDOFF.md; TASK_STATE.md; AGENTS.md; BASELINE.md; ASSET_AUDIT.md; QA_BACKLOG.md; V1_SCOPE.md; ADR/
historical_routes: v7-v15; T04.xx; HANDOFF_20260831.md; numbered execution checklists
