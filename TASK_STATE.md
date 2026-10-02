roadmap: EquipEffi V2.3
phase: Phase 1 complete / Phase 2 ready
goal: V2.3 Product Scope & Governance Cleanup (R1 final closure); no Phase 2 execution
status: PHASE_1_PASS
next_status: PHASE_2_READY

# ---------------------------------------------------------------------------
# 本文件只承担“当前状态”。历史执行细节、run ID、历史测试数字与旧 SHA 一律
# 不在本文件复制，只保留链接（见文末 historical_evidence）。
# ---------------------------------------------------------------------------

current_task:
  task_id: V2.3-PRODUCT-SCOPE-CLEANUP-R1
  branch: governance/v2.3-product-scope-cleanup
  task_kind: independent pre-acceptance fix round (R1 final closure)
  phase_2_execution: false
  new_features: NONE
  pump_business_algorithm_change: NONE
  central_contract_change: NONE
  deliverables:
    - TASK_STATE deliverables wording corrected
    - docs/28 V2.3 Phase 3-9 semantics synchronised to complete GB 19762-2025 coverage
    - TASK_STATE / ROADMAP / HANDOFF reduced to current-state-only, history via links
    - long-term CI established: windows-core.yml + pump-conformance.yml
    - three historical task workflows removed
    - historical fixed diff baselines removed; dynamic whitespace check adopted
    - full suite explicitly marked NON-GATING BASELINE / KNOWN BASELINE
    - QA_BACKLOG stale Excel Decimal risk registered with a stable QA ID
  next_action: stop for independent acceptance; do not merge automatically

allowed_next: independent acceptance of this branch only; do not start Phase 2 automatically
automatic_continuation: DISABLED
phase_0b: NOT_EXECUTED
phase_1_hotfix: NOT_EXECUTED
blocked_by: []

# ---------------------------------------------------------------------------
# 当前产品目标与范围（2026-10-02 产品决定，取代 2026-09-23 映射）
# ---------------------------------------------------------------------------
product_scope:
  decision_id: USER_PROVIDED_PRODUCT_DECISION_2026-10-02
  decision_owner: 王玮（总经理）
  windows_v1_product_goal: 完整支持 GB 19762-2025《离心泵能效限定值及能效等级》
  complete_scope: pump_water + pump_chemical
  supersedes: USER_PROVIDED_PRODUCT_DECISION_2026-09-23
  authority: V1_SCOPE.md; REFERENCE_STANDARD_ROADMAP.md

  # 三个维度分离，不得互相冒充
  #   scope_status           = 产品范围决策（本仓）
  #   support_status         = 当前发布能力（本仓发布门禁）
  #   standard_maturity      = 中央 STANDARD_DEVELOPMENT_GUIDE_V0.1 §19 阶段成熟度
  pump_water:
    scope_status: IN_V1
    support_status: SUPPORTED
    standard_maturity: SUPPORTED
  pump_chemical:
    scope_status: IN_V1
    support_status: NOT_IN_RELEASE_SCOPE
    standard_maturity: READY_FOR_IMPLEMENTATION
    target_support_status: SUPPORTED
    upgrade_blocked_by:
      - pump_chemical Golden named business approval (8 candidates currently technical-only, NOT_APPROVED)
      - Standard Development Guide Stage D independent acceptance
    note: 进入产品范围不等于已经正式支持；Stage D 通过前不得写为 SUPPORTED
  transformer:
    scope_status: POST_V1
    support_status: NOT_IN_RELEASE_SCOPE
    decision: 本轮暂缓；代码、标准数据、测试与历史资产保留，不删除、不重构
    phase_5_included: false

# ---------------------------------------------------------------------------
# 当前 central lock
# ---------------------------------------------------------------------------
central_baseline:
  locked_sha: ee5feb0cc34dbd99790500fadd0c4c932e202a20
  architecture: V2.1 FROZEN
  numeric_contract: v1 FROZEN
  other_contracts: DRAFT / NOT YET RELEASED
  auto_follow_central_main: false
  platform_lock_changed: false
  frozen_read_from: locked SHA
  active_guides_read_from: 中央当前已合并版本（GUIDE_INDEX.md §2.1 B 类）
  active_guides_note: GUIDE_INDEX / PRODUCT_DELIVERY_POLICY_V1 / STANDARD_DEVELOPMENT_GUIDE_V0.1 / UI_DESIGN_GUIDELINES_V0.1 在 locked SHA 上不存在，不得按 locked SHA 读取

phase_1_authority:
  phase_1_pr_1_merge_sha: 1a74ff4cc07e9068783a370ec4269e89245cef38
  fixed_sha_independent_review: RESOLVED
  golden_case_named_human_approval: RESOLVED
  solution_product_review: RESOLVED
  pump_water_golden_0_4: APPROVED
  pump_chemical_v1_golden: NOT_APPROVED

qzc_a01:
  status: COMPLETE
  architecture: V2.1 FROZEN

# ---------------------------------------------------------------------------
# 当前已知 blocker / 待办
# ---------------------------------------------------------------------------
known_blockers:
  numeric_contract_v1_adoption_acceptance:
    status: INDEPENDENT_ACCEPTANCE_RECORD_PENDING
    merge_sha: 66835d2ae2e0a8eaee50260f43ee0c52b4858d85
    merge_pr: PR #5
    acceptance_record_found_in_repo: false
    note: 合并事实不等同于独立验收证据；不得报告为验收 PASS
  pump_chemical_support_status:
    status: NOT_IN_RELEASE_SCOPE
    note: 见 product_scope.pump_chemical.upgrade_blocked_by
  excel_decimal_ingress:
    qa_id: QA-EXCEL-001
    surface: NOT_SHIPPED
    authoritative_path_impact: 尚待验证
    must_close_before: Phase 8
    python_change_this_round: NONE

# ---------------------------------------------------------------------------
# 历史证据（只保留链接，不复制正文）
# ---------------------------------------------------------------------------
historical_evidence:
  - docs/governance/NUMERIC_CONTRACT_V1_ADOPTION_REPORT.md
  - docs/governance/PLATFORM_ADOPTION_REPORT.md
  - QZC_N01_B_EXECUTION_REPORT.md
  - PUMP_V2_G04_APPROVAL_MANIFEST.md
  - PUMP_V2_R01_R06_COMMIT_MANIFEST.md
  - PUMP_V2_R07_COMMIT_MANIFEST.md
  - IMPLEMENTATION_REPORT.md
  - HANDOFF_20260831.md
  - docs/governance/V2.3_PRODUCT_SCOPE_CLEANUP_REPORT.md
  - docs/28_EquipEffi 后续开发总体路线 V2.3.md
