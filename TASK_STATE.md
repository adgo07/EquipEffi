roadmap: EquipEffi V2.3
phase: Phase 1 complete / Phase 2 ready
goal: V2.3 Product Scope & Governance Cleanup; no Phase 2 execution
status: PHASE_1_PASS
next_status: PHASE_2_READY

current_task:
  task_id: V2.3-PRODUCT-SCOPE-CLEANUP
  branch: governance/v2.3-product-scope-cleanup
  base_sha: f5c34277d35c9a7a1bcfbe4331297de2ad1fcf4f
  base_ref: origin/master
  task_kind: product scope closure + V2.3 sync + governance simplification + historical CI closure
  phase_2_execution: false
  new_features: NONE
  pump_business_algorithm_change: NONE
  central_contract_change: NONE
  deliverables: V1_SCOPE.md product scope closure (pump_water + pump_chemical; transformer deferred with assets preserved); REFERENCE_STANDARD_ROADMAP.md baseline and inventory sync; ROADMAP/TASK_STATE/HANDOFF and docs/28 V2.3 pointer sync; GitHub workflow trigger cleanup; PR_BODY_DRAFT.md removal; V2.3_PRODUCT_SCOPE_CLEANUP_REPORT.md
  next_action: stop for independent acceptance; do not merge automatically

allowed_next: independent acceptance of the V2.3 product scope and governance cleanup branch only; do not start Phase 2 automatically
automatic_continuation: DISABLED
phase_0b: NOT_EXECUTED
phase_1_hotfix: NOT_EXECUTED
fixed_sha_independent_review: RESOLVED
golden_case_named_human_approval: RESOLVED
solution_product_review: RESOLVED
blocked_by: []
evidence_needed: independent acceptance of the cleanup branch head, actual diff, central Frozen/Numeric v1 and ACTIVE guide reads, final CI, and docs/governance/V2.3_PRODUCT_SCOPE_CLEANUP_REPORT.md

affected_scope: V1_SCOPE.md; REFERENCE_STANDARD_ROADMAP.md; ROADMAP.md; TASK_STATE.md; HANDOFF.md; docs/28_EquipEffi 后续开发总体路线 V2.3.md; .github/workflows/*; PR_BODY_DRAFT.md; docs/governance/V2.3_PRODUCT_SCOPE_CLEANUP_REPORT.md. No Pump production evaluator, decimal_math, Canonical, Approved Golden, standard pack, database, Excel or UI implementation changes. No platform-lock.json or PLATFORM_BASELINE.md change.

product_scope_2026_10_02:
  decision_id: USER_PROVIDED_PRODUCT_DECISION_2026-10-02
  decision_owner: 王玮（总经理）
  windows_v1_product_goal: complete support for GB 19762-2025 (centrifugal pump energy efficiency)
  complete_scope: pump_water + pump_chemical
  supersedes: USER_PROVIDED_PRODUCT_DECISION_2026-09-23
  pump_water:
    scope_status: IN_V1
    support_status: SUPPORTED
    standard_maturity: SUPPORTED
  pump_chemical:
    scope_status: IN_V1
    support_status: NOT_IN_RELEASE_SCOPE
    standard_maturity: READY_FOR_IMPLEMENTATION
    support_status_upgrade_blocked_by: pump_chemical Golden named approval and Standard Development Guide Stage D independent acceptance
    target_support_status: SUPPORTED
  transformer:
    scope_status: POST_V1
    decision: deferred this round; code, standard data, tests and historical assets preserved and not to be deleted or refactored
  dimension_separation: scope_status / support_status / standard maturity are three separate dimensions and must not impersonate each other

authoritative_files: ROADMAP.md; HANDOFF.md; TASK_STATE.md; AGENTS.md; BASELINE.md; ASSET_AUDIT.md; QA_BACKLOG.md; V1_SCOPE.md; REFERENCE_STANDARD_ROADMAP.md; STANDARD_ISSUES_REGISTER.md; UI_CURRENT_STATE_AUDIT.md; PLATFORM_BASELINE.md; platform-lock.json; ADR/; docs/governance/
historical_routes: EquipEffi V2.2 (inherited baseline); v7-v15; T04.xx; HANDOFF_20260831.md; numbered execution checklists

roadmap_v2_3:
  status: ALIGNMENT_COMPLETE
  phase_0: PASS
  phase_1: PASS
  phase_2: PHASE_2_READY; NOT_STARTED
  automatic_continuation: DISABLED

central_baseline:
  locked_sha: ee5feb0cc34dbd99790500fadd0c4c932e202a20
  architecture: V2.1 FROZEN
  numeric_contract: v1 FROZEN
  other_contracts: DRAFT / NOT YET RELEASED
  auto_follow_central_main: false
  platform_lock_changed: false
  active_guides_read_from: central merged version (GUIDE_INDEX.md section 2.1 class B); governance snapshot origin/main@4516e204ab20ca61c5931a46c0b28d1c06459727
  active_guides_note: GUIDE_INDEX / PRODUCT_DELIVERY_POLICY_V1 / STANDARD_DEVELOPMENT_GUIDE_V0.1 / UI_DESIGN_GUIDELINES_V0.1 do not exist at the locked SHA and must be read from the central merged version

phase_1_authority:
  phase_1_pr_1_merge_sha: 1a74ff4cc07e9068783a370ec4269e89245cef38
  fixed_sha_independent_review: RESOLVED
  golden_case_named_human_approval: RESOLVED
  solution_product_review: RESOLVED
  pump_water_golden_0_4: APPROVED
  pump_chemical_v1_golden: NOT_APPROVED

qzc_a01:
  status: COMPLETE
  original_platform_commit_sha: 0cd74d783fa23add6dc881b408a8c8ba8503f8e8
  architecture: V2.1 FROZEN
  phase_1_state_preserved: PHASE_1_PASS
  phase_2_state: PHASE_2_READY; NOT_STARTED

# ---------------------------------------------------------------------------
# HISTORICAL RECORD — Numeric Contract v1 Adoption
# PR #5 was MERGED at 66835d2ae2e0a8eaee50260f43ee0c52b4858d85.
# No independent acceptance report exists in the repository; the acceptance
# record is therefore PENDING and must not be reported as an acceptance PASS.
# This block no longer controls the next action.
# ---------------------------------------------------------------------------
numeric_contract_v1_adoption:
  status: MERGED / INDEPENDENT_ACCEPTANCE_RECORD_PENDING
  merge_sha: 66835d2ae2e0a8eaee50260f43ee0c52b4858d85
  merge_pr: PR #5
  acceptance_record_found_in_repo: false
  acceptance_note: merge fact does not by itself constitute independent acceptance evidence; no acceptance report located this round
  task_kind: compatibility/adoption; not a new Numeric Pilot
  equip_efffi_start_master_sha: 9efc6260b03d9e0a895abdb294a70cda39aa7598
  technical_tested_sha: b1683e89ee72fa6ae5e5be7f073c123590fc2a23
  adoption_report_commit_sha: 44be0234d401174d3487b32eeaddc4ca1caad7cb
  platform_repository: https://github.com/adgo07/Qingzhou-contracts.git
  platform_commit_sha: ee5feb0cc34dbd99790500fadd0c4c932e202a20
  numeric_contract_version: v1
  numeric_contract_status: FROZEN
  numeric_contract_path: contracts/numeric/NUMERIC_CONTRACT_V1_FROZEN.md
  unit_contract: draft-v1 / DRAFT
  module_capability_contract: draft-v1 / DRAFT
  record_contract: draft-v1 / DRAFT
  package_contract: draft-v1 / DRAFT
  pump_numeric_profile_id: EQUIPEFFI_PUMP_DECIMAL50_V2
  pump_profile_declaration: specs/equipment_efficiency/numeric/equipeffi_pump_numeric_profile_v1.json
  pump_reference_procedure: PUMP-RP-0.1
  pump_working_precision: 50
  pump_working_rounding: ROUND_HALF_EVEN
  pump_business_comparison: full-value exact
  pump_display_rounding: independent presentation only
  pump_tolerance: numerical/test conformance only; never grade/rule/bucket epsilon
  decimal50_platform_default: false
  traceability: machine-readable profile + exact platform lock + EvaluationResult.standard_reference + lookup/trace rule data IDs
  production_pump_evaluator_change: NONE
  production_decimal_math_change: NONE
  canonical_or_approved_golden_change: NONE
  other_device_decimal50_migration: NONE
  auto_follow_central_main: false
  phase_2_started: false

  technical_ci:
    adoption_push_run: 36811317025 / PASS targeted gates
    adoption_pr_run: 36811320886 / PASS
    phase1_pump_windows_run: 36811320889 / PASS
    qzc_n01_b_run: 36811320954 / PASS
    adoption_tests: 6/6 PASS
    n01_b_tests: 8/8 PASS
    pump_numeric_tests: 15/15 PASS
    pump_evaluator_api_tests: 408/408 PASS
    golden_phase_tests: 138/138 PASS
    compile_and_diff_check: PASS
    full_suite: 945 run / 9 failures / 6 errors / 3 skipped
    prior_n01_b_full_suite_baseline: 939 run / 9 failures / 6 errors / 3 skipped
    regression_delta: +6 tests / +0 failures / +0 errors / +0 skips
    full_suite_workflow_note: full suite command remains failure; continue-on-error is used only to preserve/upload evidence and must not be interpreted as a green full suite

  execution_test_notes:
    initial_boundary_test_issue: T-delta was initially constructed under ambient Decimal context; fixed in adoption test only by using Pump context; production unaffected
    profile_wording_test_issue: numerical tolerance declaration clarified from purpose-specific only to purpose-specific conformance only; governance wording only; production unaffected

acceptance_history: Phase 0 PASS; Phase 1 PASS; 王玮 approved all 18 pump_water Golden 0.4 on 2026-09-28; P1-SR01 PASS; PR #1 merged; QZC-A01 PR #2 merged; QZC-N01-B execution PR #4 merged at master@9efc6260b03d9e0a895abdb294a70cda39aa7598; Numeric Contract v1 adoption PR #5 merged at master@66835d2ae2e0a8eaee50260f43ee0c52b4858d85 (independent acceptance record still pending); PR #6 roadmap, PR #7 UI audit and PR #8 governance guidance merged. On 2026-10-02 the product owner closed the Windows V1 product scope to complete support of GB 19762-2025 covering pump_water and pump_chemical, with transformer deferred and its assets preserved.
