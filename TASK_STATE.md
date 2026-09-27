roadmap: EquipEffi V2.2
phase: Phase 1
goal: Submit the Phase 1 review package after P1-G01 through P1-G06
status: BLOCKED
next_status: PENDING_FIXED_SHA_INDEPENDENT_REVIEW
base_sha: 9e413051177fbfa7f1b217de17d344f33176b152
baseline_ref: pre-v2-rebaseline
working_tree_at_start: managed clean worktree from exact base SHA; original dirty worktree remains untouched
allowed_next: stop and wait for the original independent formal review of the fixed SHA; Golden approval and Solution/Product Review remain open; Phase 2 disabled
automatic_continuation: DISABLED
phase_0b: NOT_EXECUTED
phase_1_hotfix: NOT_EXECUTED
blocked_by: PENDING_FIXED_SHA_INDEPENDENT_REVIEW; GOLDEN_CASE_APPROVAL_PENDING; SOLUTION_PRODUCT_REVIEW
evidence_needed: Record the exact isolated-worktree verification; review only fixed commit SHA in the original independent session. All 26 current candidates remain DRAFT/PENDING; no Golden or Phase 1 approval.
affected_scope: Authorized pump V2/R01-R06 source, schemas, draft candidates, direct tests and minimal governance only; no V1 scope, OOS, motor or Phase 2 change.
next_action: Hand the exact fixed SHA from the execution message to the original independent formal acceptance session, then stop.
last_verified: 2026-09-27: final fixed-SHA detached clean worktree replay completed; validator/schema, numeric, boundaries, Golden, Application E2E, metadata, evaluator matrix, full unittest, compileall and diff-check are recorded in IMPLEMENTATION_REPORT.md; working tree was clean afterward.
acceptance_history: 2026-09-22 initially BLOCKED for uncommitted governance deliverables, incomplete evidence fields, non-uniform QA tables and missing demand/value evidence; corrected and revalidated without business-code changes; 2026-09-23 product decision recorded by 王玮（总经理） for transformer and centrifugal_pump public types, with pump_water as the evidence-backed IN_V1 profile; subsequent acceptance found the Golden approval gate unmet because all seven cases remain REVIEWED with placeholder review_owner
authoritative_files: ROADMAP.md; HANDOFF.md; TASK_STATE.md; AGENTS.md; BASELINE.md; ASSET_AUDIT.md; QA_BACKLOG.md; V1_SCOPE.md; ADR/
historical_routes: v7-v15; T04.xx; HANDOFF_20260831.md; numbered execution checklists
