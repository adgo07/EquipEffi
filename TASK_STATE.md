roadmap: EquipEffi V2.3
phase: Phase 4
goal: GB19762 真实样板后的最小生命周期通用化
status: IN_PROGRESS
previous_acceptance: PHASE_3_PASS
next_status: READY_FOR_INDEPENDENT_ACCEPTANCE

# ---------------------------------------------------------------------------
# 本文件只承担“当前状态”。历史执行细节、run ID、历史测试数字与旧 SHA 一律
# 不在本文件复制，只保留链接（见文末 historical_evidence）。
# ---------------------------------------------------------------------------

current_task:
  task_id: PHASE4-MINIMAL-LIFECYCLE-GENERALIZATION
  branch: phase4/minimal-lifecycle-generalization
  task_kind: authorised Phase 4 execution
  phase_4_execution: true
  base_sha: 87d9ef1bf32fb3f765d4f8ef3f97aa222913152a
  execution_report: PHASE4_EXECUTION_REPORT.md
  evidence_claim: 一个 GB19762 产品级 E2E 样板，其中有 water + chemical 两个真实内部 rule profile（不得表述为两个独立设备/标准 E2E 样板）
  phase_4_pass_self_declared: false
  phase_5_started: false
  merge_authorized: false
  pump_chemical_support_status_self_promoted: false
  goals:
    P4-G00: IN_PROGRESS
    P4-G01: IN_PROGRESS
    P4-G02: IN_PROGRESS
    P4-G03: IN_PROGRESS
    P4-G04: IN_PROGRESS
  next_action: 完成 G00-G04 并通过 Required CI 后 push + 创建 PR 到 master；do not merge; do not start Phase 5

previous_task:
  task_id: PHASE3-GB19762-UNIFIED-VERTICAL-SLICE
  branch: phase3/gb19762-unified-vertical-slice
  task_kind: authorised Phase 3 execution
  design: docs/32_Phase 3 GB19762离心泵统一正式纵向闭环.md
  start_master_sha: 7e16418aa32ced5512e26bd70227f01a329fbdfc
  execution_report: PHASE3_EXECUTION_REPORT.md
  verdict: PHASE_3_PASS
  accepted_head: 728680dabf7b18e47ce9a5a23b296e405bc644a8
  pr: "#11"
  merge_sha: 87d9ef1bf32fb3f765d4f8ef3f97aa222913152a
  acceptance_record: docs/phase3_acceptance_record.md
  phase_3_pass_self_declared: false
  goals:
    P3-G01: COMPLETE
    P3-G02: COMPLETE
    P3-G03: COMPLETE
    P3-G04: COMPLETE
  r1_fixes:
    status: COMPLETE
    blockers: 5
    scope: Finalize 状态白名单 fail-closed / Qt stale result / Canonical pack_hash / 技术详情真折叠 / 治理状态一致性
    evidence: tests/unit/test_phase3_r1_blockers.py
  r2_fixes:
    status: COMPLETE
    root_causes: 3
    scope: Golden 历史 provenance 与当前源码解耦 / Finalize 完整状态矩阵（provenance + Canonical hash 归属）/ 治理状态全文收口
    evidence: tests/unit/test_phase3_r2_final_closure.py
  r3_fixes:
    status: COMPLETE
    root_causes: 1
    owner_decision: USER_PROVIDED_OWNER_DECISION_2026-10-02_R3
    scope: 删除 as_of < effective_date → INSUFFICIENT_DATA 门禁；评价日期改为仅用于记录与追溯；标准生命周期只做非阻断提示
    supersedes: 此前"评价日期早于标准实施日期则不执行计算"的产品规则
    evidence: tests/unit/test_phase3_r3_as_of_lifecycle.py
    scope_limit: 仅统一离心泵分析链（pump_water / pump_chemical）；遗留 EvaluationService 对 motor / transformer 的生效日期门禁未改动

phase_2:
  status: PHASE_2_PASS
  independent_acceptance: COMPLETE_BY_PRODUCT_OWNER_AUTHORISATION
  merge_pr: PR #10
  merge_sha: 7e16418aa32ced5512e26bd70227f01a329fbdfc
  note: 任务授权书明确“PR #10 已完成独立验收、已合并”；仓库内未另存独立验收报告，故以产品负责人授权 + 合并事实为记录来源
  design: docs/31_Phase 2 最小正式工程底座.md
  execution_report: PHASE2_EXECUTION_REPORT.md

allowed_next: Phase 3 P3-G01..G04 execution and evidence only; no merge; no Phase 4
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
  #   scope_status           = 产品范围决策（本仓维度，保留 IN_V1 / UNDER_REVIEW / POST_V1 三值）
  #   support_status         = 当前发布能力（本仓发布门禁）
  #   standard_maturity      = 中央 STANDARD_DEVELOPMENT_GUIDE_V0.1 §19 阶段成熟度
  pump_water:
    scope_status: IN_V1
    support_status: SUPPORTED
    standard_maturity: SUPPORTED
    owner_reconfirmation: 18 / 18 PASS
    owner_reconfirmation_date: 2026-10-02
    owner_reconfirmation_evidence: specs/equipment_efficiency/golden/owner_approvals/pump_water_owner_reconfirmation_2026-10-02.json
  pump_chemical:
    scope_status: IN_V1
    support_status: NOT_IN_RELEASE_SCOPE
    standard_maturity: READY_FOR_IMPLEMENTATION
    target_support_status: SUPPORTED
    owner_business_truth_approval: 11 / 11 PASS
    owner_business_truth_approval_date: 2026-10-02
    owner_business_truth_evidence: specs/equipment_efficiency/golden/owner_approvals/pump_chemical_owner_approval_2026-10-02.json
    golden: specs/equipment_efficiency/golden/pump_chemical/ (11 条 golden-case-0.5，APPROVED)
    upgrade_blocked_by:
      - Standard Development Guide Stage D independent acceptance
    note: Owner business truth 已批准（11/11 RESOLVED）；剩余正式 blocker 仅为 Stage D 独立验收。执行阶段不得自行把 support_status 写成 SUPPORTED。
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
  pump_water_owner_reconfirmation: 18 / 18 PASS (2026-10-02)
  pump_chemical_business_truth: 11 / 11 PASS (2026-10-02)
  pump_chemical_golden_0_5: APPROVED (11 条 formal records)
  pump_chemical_standard_maturity: READY_FOR_IMPLEMENTATION
  pump_chemical_support_status: NOT_IN_RELEASE_SCOPE

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
    remaining_blocker: Standard Development Guide Stage D independent acceptance
    business_truth_approval: RESOLVED (11/11, 2026-10-02)
    note: 业务真值 blocker 已关闭；仅剩 Stage D。见 product_scope.pump_chemical.upgrade_blocked_by
  excel_decimal_ingress:
    qa_id: QA-EXCEL-001
    surface: NOT_SHIPPED
    authoritative_path_impact: 尚待验证
    must_close_before: Phase 8
    python_change_this_round: NONE
  as_of_implicit_default_legacy_entries:
    standard_issue: EQP-STD-GB19762-001
    status: RESOLVED (软件产品决定 2026-10-02；R3 补充决定：as_of 不是标准执行门禁)
    r3_supplement: 评价日期仅用于记录与追溯；标准生命周期只做非阻断提示；已删除提前日期不执行计算的门禁与对应的 Finalize 白名单例外
    remaining: 既有 CLI/API/JSONL 入口的兼容默认值登记保留，全局取消须另立任务做兼容影响评估
    locations:
      - src/equipeffi/application/services/evaluation_service.py:13
      - src/equipeffi/application/services/evaluation_facade.py:27
      - src/equipeffi/application/services/evaluation_facade.py:68
      - src/equipeffi/application/services/v4_workbook_service.py:34
      - src/equipeffi/application/services/v4_workbook_service.py:67
      - src/equipeffi/presentation/api/application_api.py:539

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
