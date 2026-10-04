roadmap: EquipEffi V2.3
phase: Phase 7
goal: GB19762 分析流程与历史记录最终收口
status: EXECUTION_COMPLETE
previous_acceptance: PHASE_6_PASS
next_status: READY_FOR_INDEPENDENT_ACCEPTANCE
qt_is_the_only_formal_windows_shell: true
analysis_auto_records: true
ordinary_user_draft_concept: REMOVED
pump_chemical_support_status: SUPPORTED
phase_7_pass_self_declared: false

# ---------------------------------------------------------------------------
# 本文件只承担“当前状态”。历史执行细节、run ID、历史测试数字与旧 SHA 一律
# 不在本文件复制，只保留链接（见文末 historical_evidence）。
# ---------------------------------------------------------------------------

current_task:
  task_id: PHASE7-ANALYSIS-HISTORY-CLOSURE
  branch: phase7/gb19762-analysis-history-closure
  task_kind: authorised Phase 7 execution
  phase_7_execution: true
  base_sha: 6ead21fb6757d5d92ba81851f23e3c41d86598af
  execution_report: PHASE7_EXECUTION_REPORT.md
  ui_current_state_audit: UI_CURRENT_STATE_AUDIT.md（Phase 6 已按 Qt 实现重新盘点）
  formal_product_surface: PySide6 Qt Desktop（无参数 / --gui / --qt 同一入口）
  official_entrypoint_decision: TK_RETIRED_QT_IS_THE_ONLY_SHELL
  primary_navigation: 首页 / 标准库 / 新建分析 / 分析记录 / 设置（全部真实页面，无 placeholder）
  evidence_claim: 一个 GB19762 产品级 E2E 样板，其中有 water + chemical 两个真实内部 rule profile（不得表述为两个独立设备/标准 E2E 样板）
  phase_7_pass_self_declared: false
  phase_7_started: false
  merge_authorized: false
  goals:
    P7-G00: COMPLETE
    P7-G01: COMPLETE
    P7-G02: COMPLETE
    P7-G03: COMPLETE
    P7-G04: COMPLETE
    P7-G05: COMPLETE
  product_rules_owner: 9 条（见 AGENTS.md §2.8）
  records_schema_changed: false
  new_deviations:
    QA-P7-001: 版本字段实际存 profile 标识（不伪造，Presentation 改为标注「规则集标识」）；disposition 后续版本化任务
    QA-P7-002: 旧 Record 未冻结完整标准依据；降级显示，不追溯改写
  closed_deviations:
    QA-P6-003: 草稿概念退出产品表面而消解
  next_action: 等待独立验收；do not merge; do not start Phase 8

previous_task:
  task_id: PHASE4-MINIMAL-LIFECYCLE-GENERALIZATION
  branch: phase4/minimal-lifecycle-generalization
  task_kind: authorised Phase 4 execution
  phase_4_execution: true
  base_sha: 87d9ef1bf32fb3f765d4f8ef3f97aa222913152a
  execution_report: PHASE4_EXECUTION_REPORT.md
  evidence_claim: 一个 GB19762 产品级 E2E 样板，其中有 water + chemical 两个真实内部 rule profile（不得表述为两个独立设备/标准 E2E 样板）
  verdict: PHASE_4_PASS
  accepted_head: a4034ef3751590b52a821d6a3bdbebcbca6a8ec9
  pr: "#12"
  merge_sha: d6112ea9c7c1c16f95d798c2229cdc54aaf6240a
  acceptance_record: docs/phase4_acceptance_record.md
  phase_4_pass_self_declared: false
  phase_5_started: false
  merge_authorized: false
  pump_chemical_support_status_self_promoted: false
  goals:
    P4-G00: COMPLETE
    P4-G01: COMPLETE
    P4-G02: COMPLETE
    P4-G03: COMPLETE
    P4-G04: COMPLETE
  blocker_fixes:
    P4-B01:
      finding: PHASE_4_BLOCKED —— 生命周期指纹依赖泵 service 的导入副作用
      status: FIXED
      root_cause: 首版用进程内全局注册（register_business_keys）提供业务键集合；注册为空时旧 Workspace 无参指纹漂移，且不同业务输入碰撞
      fix: 移除全局注册；业务键集合作为 _business_keys 元数据随快照写入既有 payload_json 列；无元数据时不再猜测而是显式报错
      evidence: tests/unit/test_phase4_fingerprint_decoupling.py; tools/verify_phase4_fingerprint_compat.py
    P4-B02:
      finding: PHASE_4_BLOCKED —— 旧 Workspace 兼容性回归（缺字段草稿被拒 Finalize）
      status: FIXED
      root_cause: P4-B01 的回退规则只投影"载荷中实际存在的键"，无法补出缺失业务字段的 "None"（Phase 3 指纹把缺失字段计为 "None"），导致缺 efficiency 的旧草稿指纹漂移、Finalize 被拒，破坏既有 INSUFFICIENT_DATA 草稿的合法固化
      fix: 生命周期层不再猜测——缺元数据时 business_key_names() 返回 None 且 request_fingerprint() 显式抛 LifecycleError，删除 RESERVED_PAYLOAD_KEYS 与投影回退；finalize() 改为显式传 PUMP_FINGERPRINT_KEYS，由产品层提供业务键知识，恢复 Base 行为
      evidence: tests/unit/test_phase4_fingerprint_decoupling.py 的缺字段回归用例；tools/verify_phase4_fingerprint_compat.py 覆盖完整输入 + 缺字段共 4 种场景
      semantic_boundary: Phase 4 之前且无元数据的快照，无参 request_fingerprint() 会显式报错（拒绝给出无法确定的值）；不影响任何 Use Case，服务路径始终显式传键
  next_action: 等待独立验收；do not merge; do not start Phase 5

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

allowed_next: Phase 7 G00..G06 execution and evidence only; no merge; no Phase 8
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
    # Phase 5 Stage D 候选：统一正式产品路径（Qt --qt）已返回 SUPPORTED。
    # **独立验收通过前不得写成"正式支持已经生效"。**
    support_status: SUPPORT_PROMOTION_CANDIDATE
    support_status_effective_value: SUPPORTED
    support_status_pending: independent acceptance (Stage D)
    standard_maturity: IMPLEMENTED
    standard_maturity_candidate: SUPPORTED
    target_support_status: SUPPORTED
    owner_business_truth_approval: 11 / 11 PASS
    owner_business_truth_approval_date: 2026-10-02
    owner_business_truth_evidence: specs/equipment_efficiency/golden/owner_approvals/pump_chemical_owner_approval_2026-10-02.json
    golden: specs/equipment_efficiency/golden/pump_chemical/ (11 条 golden-case-0.5，APPROVED；evaluation_layer 未改写)
    stage_d_evidence_matrix: docs/phase5_stage_d_evidence_matrix.md
    formal_application_e2e_evidence: specs/equipment_efficiency/evidence/phase5_chemical_stage_d_e2e.json
    release_gate: CentrifugalPumpAnalysisService._release_support('pump_chemical') = SUPPORTED（候选）
    upgrade_blocked_by:
      - Standard Development Guide Stage D independent acceptance（唯一剩余 blocker）
    note: Owner business truth 已批准（11/11）；Stage D 证据闭环已完成并交独立验收。治理状态只写 SUPPORT_PROMOTION_CANDIDATE / READY_FOR_INDEPENDENT_ACCEPTANCE；执行阶段不得自行宣布 Stage D PASS 或 pump_chemical officially SUPPORTED。历史 Record 的 NOT_IN_RELEASE_SCOPE 快照不追溯改写。
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
  pump_chemical_golden_0_5: APPROVED (11 条 formal records；evaluation_layer 未改写)
  pump_chemical_standard_maturity: IMPLEMENTED (Phase 5；SUPPORTED 为候选，待独立验收)
  pump_chemical_support_status: SUPPORT_PROMOTION_CANDIDATE (统一 Qt 正式路径取值 SUPPORTED)
  pump_chemical_stage_d: READY_FOR_INDEPENDENT_ACCEPTANCE

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
    status: SUPPORT_PROMOTION_CANDIDATE
    formal_surface_value: SUPPORTED (PySide6 Qt Desktop --qt)
    remaining_blocker: Standard Development Guide Stage D independent acceptance
    business_truth_approval: RESOLVED (11/11, 2026-10-02)
    stage_d_evidence: COMPLETE (docs/phase5_stage_d_evidence_matrix.md; specs/equipment_efficiency/evidence/phase5_chemical_stage_d_e2e.json)
    note: 业务真值与 Stage D 证据均已就绪；仅剩独立验收结论。见 product_scope.pump_chemical.upgrade_blocked_by
  non_formal_surface_support_deviations:
    status: REGISTERED_DEVIATION
    qa_ids: [QA-P5-001, QA-P5-002, QA-P5-003, QA-P5-004, QA-P5-005]
    note: --json / ApplicationApi / JSONL / CLI / --web / legacy Tk --gui 仍返回 NOT_IN_RELEASE_SCOPE（Phase 6 收口）；V4·Excel 为 Phase 8；Android bridge 与安装/签名/发布产物为 Phase 9。不得误报为 Phase 5 已修复。
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
    phase5_update: 正式 Qt 路径的提醒缩短为四字短语（如"该标准尚未实施"）；tooltip 改为"评价日期用于记录与追溯；不影响所选标准的计算"
    remaining: 既有 CLI/API/JSONL 入口的兼容默认值与旧 as_of 门禁登记保留（QA-P3-003），全局取消须另立任务做兼容影响评估
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
