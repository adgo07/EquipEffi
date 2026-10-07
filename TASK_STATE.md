roadmap: EquipEffi V2.3
phase: Phase 8
goal: GB 19762 Excel 批量评价闭环
status: EXECUTION_COMPLETE
previous_acceptance: PHASE_7_PASS
next_status: READY_FOR_INDEPENDENT_ACCEPTANCE
qt_is_the_only_formal_windows_shell: true
analysis_auto_records: true
ordinary_user_draft_concept: REMOVED
pump_chemical_support_status: SUPPORTED
phase_8_pass_self_declared: false

# ---------------------------------------------------------------------------
# 本文件只承担“当前状态”：当前 master / head、当前任务、当前状态、blocker、
# next action。历史执行细节、run ID、历史测试数字与旧 SHA 一律不在本文件复制，
# 只保留链接（见文末 historical_evidence）。
#
# 分工（M1 治理文档收口，2026-10-07）：
#   AGENTS.md    = 长期硬规则、Owner 决策边界、权威入口
#   TASK_STATE.md = 本文件：当前状态
#   HANDOFF.md   = 很短的当前交接摘要 + 必要历史链接
#   QA_BACKLOG.md = 各 QA 项的唯一状态权威
#   V1_SCOPE.md / ROADMAP.md = 各 Profile scope / support / maturity 唯一权威
# ---------------------------------------------------------------------------

current_master:
  default_branch: master
  head_sha: 64b656ee4924fbf09f3fd87596ef1a1a779d1f09
  head_summary: "PR #16（phase8/gb19762-excel-batch → master）已合并"
  phase_8_acceptance_record: 未生成（docs/phase8_acceptance_record.md 尚不存在）

current_task:
  task_id: M1-SINGLE-OWNER-MAINTENANCE-SIMPLIFICATION
  task_kind: maintenance（单人维护简化；不是产品 Phase，不改变任何 Phase 状态或业务语义）
  branch: maintenance/m1-single-owner-feedback-loop
  base_sha: 64b656ee4924fbf09f3fd87596ef1a1a779d1f09
  goals:
    - CI 纯去重：windows-core job 内同一测试只执行一次（跨 workflow 的 pump 业务门禁刻意保留）；
      门禁不减少、按 ID 的 known-regression 比较保留
    - 治理文档收口：三份文件职责分离，消除重复 YAML key、过时 allowed_next 与互相矛盾状态
    - 统一 Python 3.12 开发入口：tools/setup_dev.ps1（不升级 3.13、不引入环境管理框架）
    - 修正明显过时的打包诊断/说明（Python 3.11、Tk 正式入口、Web fallback 正式入口）
  excluded:
    - 业务真值 / 标准计算 / Golden / Canonical / Numeric
    - Excel Reader / Writer 业务行为、records schema、Application business semantics
    - Qt 产品功能、标准资源、V6 模板、Phase 9 打包实现与发行包裁剪
  pr: "#17"
  pr_status: OPEN（等待 Owner 决定是否合并；Agent 不自行合并）
  next_action: 已推送并创建 PR #17；三个 gating job 全绿；等待 Owner 验收/合并决定
  review_fixes: "见 PR #17 评论——P1 比较器 expectedFailures 元组解包回归（已修 + 回归测试）、P2 workflow 去重口径注释收窄、P3 权威文件（ROADMAP / REFERENCE_STANDARD_ROADMAP / V1_SCOPE）Phase 8 与 pump_chemical 状态收口"

# ---------------------------------------------------------------------------
# Phase 状态：只记录结论与落档链接，不复制执行细节
# ---------------------------------------------------------------------------
phase_status:
  phase_0: 基线（不可变）
  phase_1: PHASE_1_PASS（历史多角色程序见 historical_evidence）
  phase_2: "PHASE_2_PASS（PR #10 合并 @ `7e16418a`）"
  phase_3: "PHASE_3_PASS（PR #11 合并 @ `87d9ef1b`；docs/phase3_acceptance_record.md）"
  phase_4: "PHASE_4_PASS（PR #12 合并 @ `d6112ea9`；docs/phase4_acceptance_record.md）"
  phase_5: "PHASE_5_PASS（PR #13 合并 @ `f3e32f84`；docs/phase5_acceptance_record.md）"
  phase_6: "PHASE_6_PASS（PR #14 合并 @ `6ead21f`；docs/phase6_acceptance_record.md）"
  phase_7: "PHASE_7_PASS（PR #15 合并 @ `79ea075`；docs/phase7_acceptance_record.md）"
  phase_8: "EXECUTION_COMPLETE / READY_FOR_INDEPENDENT_ACCEPTANCE（PR #16 合并 @ `64b656ee`；执行细节 PHASE8_EXECUTION_REPORT.md；**不得**自行宣布 PHASE_8_PASS）"
  phase_9: 未开始
  automatic_continuation: DISABLED

phase_8_state:
  pr: "#16"
  merge_sha: 64b656ee4924fbf09f3fd87596ef1a1a779d1f09
  branch: phase8/gb19762-excel-batch（已合并）
  formal_template: equipeffi.device-efficiency.V6（V6-20261005）
  records_schema_changed: YES (additive only)
  records_schema_detail: 迁移 003 create_batch_record（独立表）+ 004 extend_batch_record（补列）；schema_version 2 -> 4；单台 record/workspace 语义与列契约不变
  golden_excel_replay: 29/29 零漂移
  qa_blockers: QA-P8-001 ～ QA-P8-014 全部 CLOSED（状态见 QA_BACKLOG.md）
  detail: PHASE8_EXECUTION_REPORT.md（本文件不复制执行细节）
  next_action: 等待独立验收；不得进入 Phase 9

# ---------------------------------------------------------------------------
# 当前产品目标与范围（2026-10-02 产品决定；状态以 V1_SCOPE.md / ROADMAP.md 为准）
# ---------------------------------------------------------------------------
product_scope:
  decision_id: USER_PROVIDED_PRODUCT_DECISION_2026-10-02
  decision_owner: 王玮（总经理）
  windows_v1_product_goal: 完整支持 GB 19762-2025《离心泵能效限定值及能效等级》
  complete_scope: pump_water + pump_chemical
  supersedes: USER_PROVIDED_PRODUCT_DECISION_2026-09-23
  authority: V1_SCOPE.md; REFERENCE_STANDARD_ROADMAP.md
  # 三个维度分离，不得互相冒充：scope_status / support_status / standard_maturity
  pump_water:
    scope_status: IN_V1
    support_status: SUPPORTED
    standard_maturity: SUPPORTED
    owner_reconfirmation: 18 / 18 PASS (2026-10-02)
  pump_chemical:
    scope_status: IN_V1
    support_status: SUPPORTED
    standard_maturity: SUPPORTED
    effective_since: "Phase 5 Stage D 独立验收通过（PHASE_5_PASS，PR #13 @ f3e32f84）"
    owner_business_truth_approval: 11 / 11 PASS (2026-10-02)
    golden: specs/equipment_efficiency/golden/pump_chemical/（11 条 golden-case-0.5，APPROVED；evaluation_layer 未改写）
    note: Phase 5 之前的 SUPPORT_PROMOTION_CANDIDATE 措辞已随独立验收结束而失效，不得再写回。
  transformer:
    scope_status: POST_V1
    support_status: NOT_IN_RELEASE_SCOPE
    decision: 本轮暂缓；代码、标准数据、测试与历史资产保留，不删除、不重构

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

# ---------------------------------------------------------------------------
# 当前已知 blocker / 待办（QA 项状态一律以 QA_BACKLOG.md 为准）
# ---------------------------------------------------------------------------
known_blockers:
  phase_8_independent_acceptance:
    status: PENDING
    note: "Phase 8 已 EXECUTION_COMPLETE 并合并 PR #16；尚无独立验收结论，也无 docs/phase8_acceptance_record.md。**不得**自行宣布 PHASE_8_PASS。"
  numeric_contract_v1_adoption_acceptance:
    status: INDEPENDENT_ACCEPTANCE_RECORD_PENDING
    merge_sha: 66835d2ae2e0a8eaee50260f43ee0c52b4858d85
    merge_pr: "PR #5"
    acceptance_record_found_in_repo: false
    note: 合并事实不等同于独立验收证据；不得报告为验收 PASS
  non_formal_surface_support_deviations:
    status: 部分关闭 / 其余已登记
    authority: QA_BACKLOG.md
    closed:
      - QA-P5-001 CLOSED（Phase 6 R1）
      - QA-P5-002 CLOSED（Phase 6 R1）
      - QA-P5-003 CLOSED（Phase 8 / 8B）
    still_registered:
      - QA-P5-004（Android bridge）disposition = Phase 9
      - QA-P5-005（安装包 / 签名 / 发布产物）disposition = Phase 9
      - QA-P6-001 / QA-P6-004 / QA-P4-001 / QA-P7-001 / QA-P7-002 仍为 REGISTERED_DEVIATION
    note: 正式发布用户表面 = PySide6 Qt Desktop；其余 compatibility / development surface 与其 support 语义差异必须保持登记，不得含糊带过，也不得假装已全部关闭。
  as_of_implicit_default_legacy_entries:
    standard_issue: EQP-STD-GB19762-001
    status: RESOLVED（软件产品决定 2026-10-02；R3 补充：as_of 不是标准执行门禁）
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
  - docs/phase3_acceptance_record.md
  - docs/phase4_acceptance_record.md
  - docs/phase5_acceptance_record.md
  - docs/phase6_acceptance_record.md
  - docs/phase7_acceptance_record.md
  - PHASE8_EXECUTION_REPORT.md
  - QA_BACKLOG.md（QA-P8-001 ～ QA-P8-014 关闭记录；Phase 3/4/5/6/7 关闭记录）
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
