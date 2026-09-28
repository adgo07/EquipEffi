# P1-G04 Golden 0.4 approval preparation manifest

Base/fixed technical acceptance SHA: `3101e05abd7f33262a9449c390d61ec00008fb75`
P1-G04-R1 implementation base SHA: `6c672fe48ac3da09b173cb62fd4119daf1c0ab54`
Branch: `phase1/pump-v2-r01-r06`
Scope: P1-G04 schema/provenance preparation history plus the formal human-approved Golden 0.4 persistence recorded below.

## Included files

| File/group | Change | Role | Why required | Source / history |
|---|---|---|---|---|
| `specs/equipment_efficiency/schemas/golden_case_0_4.schema.json` | Add | Formal approved V2 Golden schema | Requires three APPROVED states, named owner, timestamps, basis, limits and 0.3 provenance | Derived from existing 0.3 schema at fixed SHA; no earlier 0.4 history |
| `specs/equipment_efficiency/schemas/golden_case_0_4_review.schema.json` | Add | Pending review schema | Keeps preparation records structurally distinct from approved records | New versioned review-only layer |
| `specs/equipment_efficiency/golden/pump_water_approval_review/GC-PUMP-V4-WATER-*.json` (18 files) | Add | Independent per-case review records | Carries exact candidate payload, expected result, trace, evidence sidecar, pending approval fields, hash provenance and empty case-level review_flags | 15 map to original 0.3 records; 3 map to registered replacement records; see review README |
| specs/equipment_efficiency/golden/pump_water/GC-PUMP-V4-WATER-*.json (18 files) | Add in approval persistence | Formal approved pump_water Golden 0.4 | Stores the explicit named approval, timestamps, basis, limits and exact review/candidate provenance while preserving approved business payload | 18 records approved by 王玮 at 2026-09-28T11:03:04+08:00; 0.1/0.3/replacements unchanged |
| `specs/equipment_efficiency/golden/pump_water_approval_review/README.md` | Add | Human review dossier | Lists inputs, statuses, evidence, rule IDs, key calculations, replacement provenance, generated-boundary responsibility and approval steps | Generated from the 18 records; business payloads retained |
| `specs/equipment_efficiency/golden/pump_water_replacement_candidates_v0_1.jsonl` | Add | Three provenance-only replacement candidates | Gives each inconsistent source a unique candidate ID and aligns only its Canonical stable_data_ids to its trace rule | Replacements are byte-pinned in source registry; raw_inputs, expected_result, expected_calculation_trace, thresholds and remaining fields match the predecessor |
| `specs/equipment_efficiency/golden/pump_candidate_source_registry_v0_1.json` | Add | Allowlisted versioned candidate source registry | Pins path, schema version, baseline SHA, file SHA, record count and old/new candidate ID pairs | Original 0.3 source file is pinned at normalized SHA-256 `E8096D18E4B62A6986222C6E5ADEC9519FA842AE44860A736D45AFA3AE712C8D`; replacement JSONL at `2600E577B25926263823AA7C42A59B8CD1433B5A6D49C2C0075D14543103CED9` |
| `specs/equipment_efficiency/schemas/pump_candidate_source_registry_v0_1.schema.json` | Add | Registry schema | Restricts registry shape and required lineage/hash fields | Versioned with source registry v0.1 |
| `tools/validate_phase1_contracts.py` | Modify | Schema/source/provenance validator | Validates official 0.4 approvals, pending review records, registry-allowlisted paths and hashes, unique candidate IDs, exact lineage/payload equality, and existing external evidence resolution | Existing validator extended for G04-R1 candidate registry |
| `tests/unit/test_golden_case_0_4_approval.py` | Add/modify | Contract/provenance tests | Tests approved-state requirements, pending set coverage, registered source hashes, copied payload, review_flags, mutation rejection and approval semantics | Direct G04 and R1 regression coverage |
| `.github/workflows/phase1-pump-windows.yml` | Modify | Windows CI | Runs review package validator and focused 0.4 approval tests | Existing Windows workflow |
| `ROADMAP.md`, `HANDOFF.md`, `TASK_STATE.md` | Modify | Current governance | Records G04-R1 source replacement, historical/candidate/review/approved layers, remaining human blocker, endpoint test ownership and Phase 1 restrictions | Existing files; current sections only |
| `specs/equipment_efficiency/golden/pump_water/README.md` | Modify | Pump Golden policy | Removes any suggestion to upgrade old 0.1 cases and explains all three layers | Existing README; replaced stale approval wording |
| `IMPLEMENTATION_REPORT.md` | Append | Verification record | Captures local P1-G04 and R1 checks and limits without claiming approval | Existing R01-R07/G04 history retained; R1 addendum supersedes the initial flag state |

## Review records and source candidates

| Proposed review ID | Registered source candidate ID | Status |
|---|---|---|
| `GC-PUMP-V4-WATER-BELOW-MINIMUM` | `GC-PUMP-V3-WATER-BELOW-MINIMUM` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-CATEGORY-MISSING` | `GC-PUMP-V3-WATER-CATEGORY-MISSING` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-CATEGORY-OTHER` | `GC-PUMP-V3-WATER-CATEGORY-OTHER` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-CATEGORY-UNKNOWN` | `GC-PUMP-V3-WATER-CATEGORY-UNKNOWN` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-DOUBLE-SUCTION-L1` | `GC-PUMP-V3-WATER-DOUBLE-SUCTION-L1` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-FLOW-OOS` | `GC-PUMP-V3-WATER-FLOW-OOS` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-LIGHT-HORIZONTAL-L3` | `GC-PUMP-V3-R1-WATER-LIGHT-HORIZONTAL-L3` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-LIGHT-VERTICAL-L2` | `GC-PUMP-V3-R1-WATER-LIGHT-VERTICAL-L2` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-MISSING-EFFICIENCY` | `GC-PUMP-V3-WATER-MISSING-EFFICIENCY` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-MISSING-STAGES` | `GC-PUMP-V3-WATER-MISSING-STAGES` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-MISSING-SUCTION` | `GC-PUMP-V3-WATER-MISSING-SUCTION` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-MULTISTAGE-C2-142-33` | `GC-PUMP-V3-WATER-MULTISTAGE-C2-142-33` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-PIPELINE-L1` | `GC-PUMP-V3-R1-WATER-PIPELINE-L1` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-SINGLE-L2` | `GC-PUMP-V3-WATER-SINGLE-L2` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-SINGLE-L3` | `GC-PUMP-V3-WATER-SINGLE-L3` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-SINGLE-SUCTION-L1` | `GC-PUMP-V3-WATER-SINGLE-SUCTION-L1` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-STAGE-CONFLICT` | `GC-PUMP-V3-WATER-STAGE-CONFLICT` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-SUCTION-CONFLICT` | `GC-PUMP-V3-WATER-SUCTION-CONFLICT` | `PENDING_APPROVAL` |

## Explicit exclusions

- Golden 0.1 seven JSON files and their recorded hashes: not modified, not upgraded to APPROVED.
- Golden 0.3 candidate JSONL: not modified; all 26 entries remain DRAFT/PENDING.
- Eight pump_chemical technical-only candidates: not approved and not included in the review package.
- Decimal50, ns_raw, standards formulas, total Q/H and suction/stages conversion, Canonical values including C2=142.33, OOS policy and pump evaluator: unchanged.
- Standard PDF: not committed; validator still accepts `--external-evidence-root` and `EQUIPEFFI_EXTERNAL_EVIDENCE_ROOT`.
- No unrelated historical or user-worktree files included. The original dirty worktree was not modified.

## Initial G04 finding (superseded by R1)

The initial G04 review run found three source mismatches and three flags. P1-G04-R1 supersedes that state with separate replacement candidates; the original 0.3 file remains unchanged. The replacement pair comparison is enforced by validator and tested.

## P1-G04-R1 closure state

- The 18 review IDs and all business payloads are retained. Fifteen still cite their original 0.3 candidate; the light vertical, light horizontal and pipeline records now cite the registered replacement IDs listed above.
- Replacement IDs are `GC-PUMP-V3-R1-WATER-LIGHT-VERTICAL-L2`, `GC-PUMP-V3-R1-WATER-LIGHT-HORIZONTAL-L3`, and `GC-PUMP-V3-R1-WATER-PIPELINE-L1`. Their matched Canonical IDs are T3-09, T3-10 and T3-05 respectively. Only candidate `case_id` and Canonical `stable_data_ids` differ from each predecessor.
- At the R1 preparation point, all 18 review_flags arrays were empty and no formal 0.4 record had yet been generated. The approval persistence below supersedes that point-in-time state.
- 精确表3边界由generated boundary test负责，首批人工Golden不要求重复穷举端点。 `tests/unit/test_pump_generated_boundaries_v2.py` exercises q_min/q_max equality and both sides at ±1e-6 for every water Canonical row. No Q=5/Q=300 review Golden is required.
- The external GB 19762-2025 PDF remains outside Git. Its raw SHA-256 `7F515D8B9D6B4D2AB97FFA7BECB78520BA0579CFBD6D5ECA10C7E7CC77895FEC` was checked with `--external-evidence-root`.
- The named human Golden approval gate is now RESOLVED. Phase 1 remains BLOCKED pending independent review of the final fixed SHA and Solution/Product Review. This manifest does not declare Phase 1 PASS or authorize Phase 2.

## P1-G04 formal Golden 0.4 approval persistence (2026-09-28)

王玮明确表示其作为 GB 19762—2025 离心泵标准负责人已逐案审阅并正式批准全部 18 条 pump_water review records。批准元数据使用 reviewed_at=approved_at=2026-09-28T11:03:04+08:00。18 条正式文件已写入 specs/equipment_efficiency/golden/pump_water/；每条 case_schema_version=golden-case-0.4、case_status=approval_status=review_status=APPROVED、review_owner=王玮、review_flags=[]。每条均包含适合标准计算类或缺失/未知/冲突类的 approval_basis 和限制说明。

批准文件与其已审 review/candidate provenance 一致；raw_inputs、expected_result、expected_calculation_trace、source_sidecar、matched_rule_id、grade thresholds、issue_codes、ui_conclusion 与 provenance 不改写。原 Golden 0.1 七例、原始 0.3 二十六候选、三条 replacement candidates 及八条 pump_chemical 技术候选均未改。GB PDF 不进入仓库，外部原始 SHA-256 为 7F515D8B9D6B4D2AB97FFA7BECB78520BA0579CFBD6D5ECA10C7E7CC77895FEC。

精确表3边界由generated boundary test负责，首批人工Golden不要求重复穷举端点。Golden named-human approval gate 现为 RESOLVED；最终批准落库 SHA 仍须独立正式复验，随后还须 Solution/Product Review。Phase 1 保持 BLOCKED；不批准 pump_chemical Golden，不宣布 Phase 1 PASS，不进入 Phase 2，不合并 PR。
