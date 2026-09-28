roadmap: EquipEffi V2.2
phase: Phase 1
goal: Submit the Phase 1 review package after P1-G01 through P1-G06
status: BLOCKED
next_status: PENDING_GOLDEN_OWNER_REVIEW
base_sha: 9e413051177fbfa7f1b217de17d344f33176b152
baseline_ref: pre-v2-rebaseline
working_tree_at_start: managed clean worktree from exact base SHA; original dirty worktree remains untouched
allowed_next: finish P1-G04 approval-contract preparation and Windows CI on the existing isolated branch; then stop for named human Golden review and fixed-SHA independent re-review; no Phase 1 PASS or Phase 2
automatic_continuation: DISABLED
phase_0b: NOT_EXECUTED
phase_1_hotfix: NOT_EXECUTED
blocked_by: GOLDEN_CASE_NAMED_HUMAN_APPROVAL_PENDING; THREE_CANDIDATE_EVIDENCE_FLAGS; FIXED_SHA_INDEPENDENT_REVIEW; SOLUTION_PRODUCT_REVIEW
evidence_needed: Obtain Windows CI for the new fixed commit SHA; standard owner must individually review all 18 water preparation cases. Resolve three CANONICAL_PACK stable_data_ids/matched_rule_id inconsistencies in a new candidate version before approving those cases. Keep 0.1 immutable/historical, all 26 0.3 records DRAFT/PENDING, and create no approved 0.4 case before human sign-off.
affected_scope: P1-G04 approval schemas, provenance validator, 18 water review packages, direct tests, Windows CI and named governance docs only; no numerical/evaluator/candidate-pool changes, no chemical approvals, motor changes or Phase 2.
next_action: Push only the P1-G04 allowlist to PR #1, record Windows CI for the new SHA, then stop for named standard-owner approval and original independent fixed-SHA review.
last_verified: 2026-09-28: G04 amendment local validator reports 7 historical official cases/0 errors, 26 candidates/0 errors, and 18 review cases/0 validation errors with 3 explicit open evidence flags; negative probes produced 3 expected rejections. Targeted pump/API/schema tests 164 passed, metadata/architecture 110 passed, evaluator matrix 284 passed, compileall and diff check passed. External PDF bytes were skipped by design. Initial G04 commit c54f7b6 Windows CI passed; the amended fixed-SHA Windows CI remains pending push.
acceptance_history: 2026-09-22 initially BLOCKED for uncommitted governance deliverables, incomplete evidence fields, non-uniform QA tables and missing demand/value evidence; corrected and revalidated without business-code changes; 2026-09-23 product decision recorded by 王玮（总经理） for transformer and centrifugal_pump public types, with pump_water as the evidence-backed IN_V1 profile; R01-R07 independent technical acceptance was completed at 3101e05; Golden 0.1 remains historical, Golden 0.3 remains DRAFT/PENDING, and P1-G04 approval still requires a named human owner
authoritative_files: ROADMAP.md; HANDOFF.md; TASK_STATE.md; AGENTS.md; BASELINE.md; ASSET_AUDIT.md; QA_BACKLOG.md; V1_SCOPE.md; ADR/
historical_routes: v7-v15; T04.xx; HANDOFF_20260831.md; numbered execution checklists
