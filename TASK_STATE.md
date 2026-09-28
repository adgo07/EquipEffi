task_id: QZC-A01
scope: Qingzhou-contracts governance adoption only
status: ADOPTION_PREPARED
business_repo: adgo07/EquipEffi
default_branch_at_start: master
default_branch_head_at_start: 19b628f6349713f62d8f5127a52b4be521d163da
adoption_branch: chore/qingzhou-contracts-adoption
product_state_authority: HANDOFF.md
platform_governance_repo: https://github.com/adgo07/Qingzhou-contracts.git
platform_baseline_kind: pre-release / bootstrap baseline
platform_release: none
platform_tag: none
platform_commit_sha: 0cd74d783fa23add6dc881b408a8c8ba8503f8e8
architecture_version: V2.1 FROZEN
contracts_status: draft-v1 / DRAFT / NOT YET RELEASED
auto_follow_central_main: false
business_code_changed: false
database_schema_changed: false
ui_changed: false
central_contract_changed: false
submodule_or_vendor_added: false
adopted_at: 2026-09-28

notes:
  - This file records only QZC-A01 governance adoption and does not replace the product roadmap or business-phase conclusions in HANDOFF.md.
  - The default branch did not contain AGENTS.md or TASK_STATE.md before this adoption; they are added only as governance entry points.
  - An open Phase 1 PR (#1) exists from the same default-branch base and contains newer business governance. Before either branch is merged after the other, rebase/reconcile governance files; do not overwrite PR #1 business conclusions with this adoption-only state.
  - No formal Qingzhou-contracts release/tag existed at adoption time, so the merged central main SHA is pinned as a pre-release bootstrap baseline. DRAFT contracts remain DRAFT.

next_action:
  - Complete PLATFORM_ADOPTION_REPORT.md and minimal HANDOFF sync.
  - Verify the branch diff contains governance/documentation only.
  - If opening/merging a PR, reconcile against any newer business-governance branch first.
  - Do not start business refactoring, qzpack migration, Suite, mobile, Native Core, or public Contract changes under QZC-A01.
