roadmap: EquipEffi V2.3
phase: Phase 1 complete / Phase 2 ready
goal: Numeric Contract v1 Adoption; no Phase 2 execution
status: PHASE_1_PASS
next_status: PHASE_2_READY
base_sha: 9efc6260b03d9e0a895abdb294a70cda39aa7598
baseline_ref: pre-v2-rebaseline
working_tree_at_start: branch chore/numeric-contract-v1-adoption from exact master@9efc6260b03d9e0a895abdb294a70cda39aa7598
allowed_next: Numeric Contract v1 Adoption independent acceptance only; do not start Phase 2 automatically
automatic_continuation: DISABLED
phase_0b: NOT_EXECUTED
phase_1_hotfix: NOT_EXECUTED
fixed_sha_independent_review: RESOLVED
golden_case_named_human_approval: RESOLVED
solution_product_review: RESOLVED
blocked_by: []
evidence_needed: independent review of PR latest head, actual diff, central Frozen Numeric v1, final CI and docs/governance/NUMERIC_CONTRACT_V1_ADOPTION_REPORT.md

affected_scope: platform-lock.json; PLATFORM_BASELINE.md; ROADMAP.md; AGENTS.md; TASK_STATE.md; Numeric v1 Pump profile declaration; adoption conformance/tests/workflow/report. No Pump production evaluator, decimal_math, Canonical, Approved Golden, database, Excel, UI or Phase 2 implementation changes.
next_action: stop for Numeric Contract v1 Adoption independent acceptance; do not merge automatically

authoritative_files: ROADMAP.md; HANDOFF.md; TASK_STATE.md; AGENTS.md; BASELINE.md; ASSET_AUDIT.md; QA_BACKLOG.md; V1_SCOPE.md; PLATFORM_BASELINE.md; platform-lock.json; ADR/; docs/governance/NUMERIC_CONTRACT_V1_ADOPTION_REPORT.md
historical_routes: EquipEffi V2.2 (inherited baseline); v7-v15; T04.xx; HANDOFF_20260831.md; numbered execution checklists

roadmap_v2_3:
  status: ALIGNMENT_COMPLETE
  phase_0: PASS
  phase_1: PASS
  phase_2: PHASE_2_READY; NOT_STARTED
  automatic_continuation: DISABLED

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

numeric_contract_v1_adoption:
  status: EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE
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
  merge_authorized: false

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

acceptance_history: Phase 0 PASS; Phase 1 PASS; 王玮 approved all 18 pump_water Golden 0.4 on 2026-09-28; P1-SR01 PASS; PR #1 merged; QZC-A01 PR #2 merged; QZC-N01-B execution PR #4 merged at master@9efc6260b03d9e0a895abdb294a70cda39aa7598. Numeric Contract v1 adoption starts from that exact master, adopts central Frozen Numeric v1 only, preserves the N01-B Pump Profile, does not reopen Pump design, does not migrate other devices to Decimal50, does not start Phase 2, and is now stopped for independent acceptance.
