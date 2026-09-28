roadmap: EquipEffi V2.2
phase: Phase 1
goal: Submit the Phase 1 review package after P1-G01 through P1-G06
status: BLOCKED
next_status: PENDING_GOLDEN_OWNER_REVIEW
base_sha: 9e413051177fbfa7f1b217de17d344f33176b152
baseline_ref: pre-v2-rebaseline
working_tree_at_start: managed clean worktree from exact base SHA; original dirty worktree remains untouched
allowed_next: after pushing the P1-G04-R1 commit and confirming its Windows CI, stop for named human Golden review and fixed-SHA independent re-review; no Phase 1 PASS or Phase 2
automatic_continuation: DISABLED
phase_0b: NOT_EXECUTED
phase_1_hotfix: NOT_EXECUTED
blocked_by: GOLDEN_CASE_NAMED_HUMAN_APPROVAL_PENDING; FIXED_SHA_INDEPENDENT_REVIEW; SOLUTION_PRODUCT_REVIEW
evidence_needed: Obtain Windows CI for the new fixed commit SHA; standard owner must individually review all 18 water preparation cases using the registered 0.3 or replacement candidate provenance. Keep 0.1 immutable/historical, all 26 original 0.3 records DRAFT/PENDING, and create no approved 0.4 case before human sign-off. Three replacements have matching Canonical IDs and trace rules; review_flags must remain zero.
affected_scope: P1-G04 approval schemas, provenance validator, 18 water review packages, direct tests, Windows CI and named governance docs only; no numerical/evaluator/candidate-pool changes, no chemical approvals, motor changes or Phase 2.
next_action: Push only the P1-G04-R1 allowlist to PR #1 and verify Windows CI on the resulting SHA. Then stop for named standard-owner review and original independent fixed-SHA re-review; do not merge PR #1.
last_verified: 2026-09-28: CPython 3.13.3 local checks passed: contract validator reported 7 historical cases, 26 original candidates, 3 registered replacements and 18 review records with zero errors/flags; 3 negative probes rejected as expected; pump/API/Golden/provenance/boundary/numeric suites 164 passed; metadata/architecture/evaluator matrix 394 passed; compileall and git diff --check passed. The external GB PDF raw SHA-256 was verified using --external-evidence-root as 7F515D8B9D6B4D2AB97FFA7BECB78520BA0579CFBD6D5ECA10C7E7CC77895FEC. Windows CI for the final pushed SHA remains to be checked. Generated boundary test covers exact q_min/q_max and both sides for all water Canonical rows; no Q=5/Q=300 review Golden is required.
acceptance_history: 2026-09-22 initially BLOCKED for uncommitted governance deliverables, incomplete evidence fields, non-uniform QA tables and missing demand/value evidence; corrected and revalidated without business-code changes; 2026-09-23 product decision recorded by 王玮（总经理） for transformer and centrifugal_pump public types, with pump_water as the evidence-backed IN_V1 profile; R01-R07 independent technical acceptance was completed at 3101e05; Golden 0.1 remains historical, Golden 0.3 remains DRAFT/PENDING, and P1-G04 approval still requires a named human owner
authoritative_files: ROADMAP.md; HANDOFF.md; TASK_STATE.md; AGENTS.md; BASELINE.md; ASSET_AUDIT.md; QA_BACKLOG.md; V1_SCOPE.md; ADR/
historical_routes: v7-v15; T04.xx; HANDOFF_20260831.md; numbered execution checklists
