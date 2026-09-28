# P1-G04 Golden 0.4 approval preparation manifest

Base/fixed technical acceptance SHA: `3101e05abd7f33262a9449c390d61ec00008fb75`
Branch: `phase1/pump-v2-r01-r06`
Scope: contract and review-package preparation only. This manifest does not approve Golden cases.

## Included files

| File/group | Change | Role | Why required | Source / history |
|---|---|---|---|---|
| `specs/equipment_efficiency/schemas/golden_case_0_4.schema.json` | Add | Formal approved V2 Golden schema | Requires three APPROVED states, named owner, timestamps, basis, limits and 0.3 provenance | Derived from existing 0.3 schema at fixed SHA; no earlier 0.4 history |
| `specs/equipment_efficiency/schemas/golden_case_0_4_review.schema.json` | Add | Pending review schema | Keeps preparation records structurally distinct from approved records | New versioned review-only layer |
| `specs/equipment_efficiency/golden/pump_water_approval_review/GC-PUMP-V4-WATER-*.json` (18 files) | Add | Independent per-case review records | Carries exact candidate payload, expected result, trace, evidence sidecar, pending approval fields, hash provenance and case-level review_flags | Each maps 1:1 to a 0.3 water Application E2E candidate; see review README |
| `specs/equipment_efficiency/golden/pump_water_approval_review/README.md` | Add | Human review dossier | Lists inputs, statuses, evidence, rule IDs and key calculation values; records boundary limitation and approval steps | Generated from the 18 records; no candidate values changed |
| `tools/validate_phase1_contracts.py` | Modify | Schema/source/provenance validator | Validates official 0.4 approvals, pending review records, exact candidate lineage/hash, and existing external evidence resolution | Existing validator with minimal G04 extension |
| `tests/unit/test_golden_case_0_4_approval.py` | Add | Contract/provenance tests | Tests approved-state requirements, pending set coverage, source hash, copied payload and approval semantics | New direct tests for this change |
| `.github/workflows/phase1-pump-windows.yml` | Modify | Windows CI | Runs review package validator and focused 0.4 approval tests | Existing Windows workflow |
| `ROADMAP.md`, `HANDOFF.md`, `TASK_STATE.md` | Modify | Current governance | Records G04 scope, historical/candidate/approved layers, remaining human blocker and Phase 1 restrictions | Existing files; current sections only |
| `specs/equipment_efficiency/golden/pump_water/README.md` | Modify | Pump Golden policy | Removes any suggestion to upgrade old 0.1 cases and explains all three layers | Existing README; replaced stale approval wording |
| `IMPLEMENTATION_REPORT.md` | Append | Verification record | Captures local P1-G04 checks and limits without claiming approval | Existing R01-R07 history retained |

## Review records and source candidates

| Proposed review ID | 0.3 source candidate ID | Status |
|---|---|---|
| `GC-PUMP-V4-WATER-BELOW-MINIMUM` | `GC-PUMP-V3-WATER-BELOW-MINIMUM` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-CATEGORY-MISSING` | `GC-PUMP-V3-WATER-CATEGORY-MISSING` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-CATEGORY-OTHER` | `GC-PUMP-V3-WATER-CATEGORY-OTHER` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-CATEGORY-UNKNOWN` | `GC-PUMP-V3-WATER-CATEGORY-UNKNOWN` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-DOUBLE-SUCTION-L1` | `GC-PUMP-V3-WATER-DOUBLE-SUCTION-L1` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-FLOW-OOS` | `GC-PUMP-V3-WATER-FLOW-OOS` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-LIGHT-HORIZONTAL-L3` | `GC-PUMP-V3-WATER-LIGHT-HORIZONTAL-L3` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-LIGHT-VERTICAL-L2` | `GC-PUMP-V3-WATER-LIGHT-VERTICAL-L2` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-MISSING-EFFICIENCY` | `GC-PUMP-V3-WATER-MISSING-EFFICIENCY` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-MISSING-STAGES` | `GC-PUMP-V3-WATER-MISSING-STAGES` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-MISSING-SUCTION` | `GC-PUMP-V3-WATER-MISSING-SUCTION` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-MULTISTAGE-C2-142-33` | `GC-PUMP-V3-WATER-MULTISTAGE-C2-142-33` | `PENDING_APPROVAL` |
| `GC-PUMP-V4-WATER-PIPELINE-L1` | `GC-PUMP-V3-WATER-PIPELINE-L1` | `PENDING_APPROVAL` |
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

## Known review limitation

The 18 frozen 0.3 water candidates cover efficiency grades 1/2/3, multiple pump types, below-minimum, out-of-scope, missing, invalid-conflict and unresolved/unknown categories. Three source-evidence flags remain open: the light vertical and horizontal candidate sidecars omit their trace rows T3-09/T3-10, and the pipeline case trace says T3-05 while its sidecar says T3-01. These cases must not be approved until resolved in a new candidate version. They include Q=4.9 just outside the lower standard limit but no exact Q=5 or Q=300 endpoint equality. The 0.1 endpoint examples remain historical only. The standard owner must decide whether this boundary coverage is sufficient; any required new exact-boundary Golden must be a separately versioned candidate, not an edit to 0.3 or promotion of 0.1.
