# Phase 1 Pump V2 R01–R06 isolated implementation report

Date: 2026-09-27
Branch: `phase1/pump-v2-r01-r06`
Base: `9e413051177fbfa7f1b217de17d344f33176b152`
Implementation worktree: `C:\Users\WANGWEI\.codex\worktrees\phase1-pump-v2-r01-r06\EquipEffi`
Final verification worktree: `C:\Users\WANGWEI\.codex\worktrees\pump-v2-final-final\EquipEffi`
Original worktree: `G:\Python Project\EquipEffi` (read-only; not used for imports or test working directory)

## Scope and disposition

This is the authorized, limited implementation of R01–R06 from `docs/pump_v2_independent_formal_acceptance_20260927.md`. The reviewed file allowlist and exclusions are in `PUMP_V2_R01_R06_COMMIT_MANIFEST.md`. A single combined commit is used because the base worktree has no safe, auditable V2-only intermediate state and the contract/application changes interleave with R01/R02 fixes.

The Decimal50 numerical core, `ns_raw` formal bands, GB 19762—2025 formulas, total Q/H and explicit suction/stages conversion, OOS policy, V1 profile scope, Canonical constants other than the already authorized T3-08 C2 correction, old official Golden bytes/hashes, motor behavior, and Phase 2 boundary remain frozen. T3-08 C2 is `142.33`; no other `pump.json` JSON value differs from the base. `pump_chemical` remains `UNDER_REVIEW` and `NOT_IN_RELEASE_SCOPE` at the public application boundary. All 26 candidate cases remain `DRAFT/PENDING`.

## Environment and source isolation

Windows PowerShell 7.6.6; CPython 3.12.14 x64 from `G:\Python Project\EquipEffi\.venv\Scripts\python.exe`; `PYTHONPATH=src`; `PYTHONDONTWRITEBYTECODE=1`; `jsonschema 4.26.0`; `openpyxl 3.1.5`. Final-SHA commands ran with the detached clean verification worktree as current directory. `import equipeffi; print(equipeffi.__file__)` resolved to `C:\Users\WANGWEI\.codex\worktrees\pump-v2-final-final\EquipEffi\src\equipeffi\__init__.py`.

## Final fixed-SHA fresh-worktree verification results

PowerShell command prefix for Python rows below:

```powershell
$env:PYTHONPATH='src'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
$py='G:\Python Project\EquipEffi\.venv\Scripts\python.exe'
```

| Check | Command | Environment | Duration | Result |
|---|---|---|---:|---|
| Contract/schema CLI | `& $py tools/validate_phase1_contracts.py --negative-probe --candidate-jsonl specs/equipment_efficiency/golden/pump_e2e_v0_3_candidates.jsonl` | CPython 3.12.14 x64; jsonschema 4.26.0; final clean worktree | 0.467 s | Exit 0; 7 old cases, 0 errors; 10 exact historical provenance messages; negative probe=3 expected errors; 26 V0.3 candidates, 0 source/schema errors. |
| Historical/schema regressions | `& $py -m unittest tests.unit.test_golden_case_schema_0_2 -q` | Same | 0.556 s | 10 passed. Includes unchanged old case bytes, exact registered old Canonical hash accepted as historical, unknown hash rejected, CRLF/LF stable source pins, and all 26 draft candidate references. |
| Pump numeric + rule integrity | `& $py -m unittest tests.unit.test_pump_numeric_contract_v2 tests.unit.test_pump_rule_integrity_v2 -q` | Same | 0.394 s | 12 passed. |
| Pump generated boundaries | `& $py -m unittest tests.unit.test_pump_generated_boundaries_v2 -q` | Same | 0.376 s | 3 passed. |
| Pump Golden/schema | `& $py -m unittest tests.unit.test_pump_golden_case_0_3 tests.unit.test_golden_case_schema_0_2 -q` | Same | 0.743 s | 14 passed; candidates remain draft. |
| Application/API/E2E | `& $py -m unittest tests.unit.test_application_api tests.unit.test_evaluation_engine tests.unit.test_pump_source_pages tests.unit.test_pump_golden_case_0_3 -q` | Same | 1.752 s | 168 passed. |
| Metadata/architecture | `& $py -m unittest tests.contract.test_device_metadata tests.contract.test_architecture_boundaries -q` | Same | 7.938 s wall (7.581 s unittest) | 110 passed. |
| Evaluator matrix | `& $py -m unittest tests.unit.test_device_evaluator_matrix -q` | Same | 1.138 s wall | 284 passed. Non-pump baseline inputs and behavior retained. |
| Full unittest | `& $py -m unittest discover -s tests -p 'test_*.py' -q` | Same | 170.834 s wall (169.031 s unittest) | 916 total: 909 passed, 3 failed, 1 error, 3 skipped. See baseline failures below. |
| Compileall | `& $py -m compileall -q src tools tests` | Same | 1.105 s | Exit 0. |
| Diff whitespace check | `git diff --check` | Git in final clean worktree | 0.071 s | Exit 0; no whitespace errors. `git show --check --oneline --stat HEAD` also passed. Final `git status --short` was empty after compileall. |

R04 cross-checkout follow-up (2026-09-27): the first fresh checkout at interim commit `2cb84399c63b8ae5b2d62d6ef664132ae523a251` reproduced the targeted suites but an explicit V0.3 candidate-sidecar CLI check found 132 source-hash mismatches because `core.autocrlf=true` changed raw worktree bytes. That SHA is not the final acceptance SHA. The validator now hashes repository text after CRLF-to-LF normalization, keeps external and non-text artifacts on raw-byte hashes, and tests the normalization. The 26 new DRAFT/PENDING candidate records now pin the committed content digest for their nine repository source paths. The seven historical Golden 0.1 files and their hashes remain unchanged.

The pre-amend implementation-worktree logs are under its ignored `outputs/phase1_pump_v2_r01_r06_verify/` directory. The final-SHA fresh replay was streamed to the console and summarized here; no log artifacts were added to the final verification checkout or commit.

## R01–R06 closure evidence

| ID | Implemented correction | Direct evidence |
|---|---|---|
| R01 | Distinguishes absent required input from present-but-invalid values. Invalid suction, stages, Q/H and efficiency use `INVALID_INPUT` and invalid issue codes rather than being mislabeled missing; missing fields remain `INSUFFICIENT_DATA`; conflicts stop before formula evaluation. | `test_pump_numeric_contract_v2`, `test_pump_golden_case_0_3`, pump evaluator matrix. |
| R02 | Public pump Application route always supplies the release support dimension: `pump_water` is `SUPPORTED`; chemical and unresolved/unapproved routes are `NOT_IN_RELEASE_SCOPE`. Technical Profile evaluators retain `support_status=null`. | `test_application_api`, `test_pump_golden_case_0_3`, evaluator matrix. |
| R03 | Replaces invalid “light pump” examples that could not route with valid explicit profile inputs and includes pipe-pump coverage. Adds 26 versioned candidates: 18 water Application E2E, 8 chemical technical-only. | V0.3 schema validator; `test_pump_golden_case_0_3`; `pump_water.md` / `pump_chemical.md`. Cases are still DRAFT/PENDING, not approved. |
| R04 | Supports versioned 0.1/0.2/0.3 contract validation. Repository text source hashes are CRLF/LF stable; external and non-text references remain raw-byte hashes. The exact old 0.1 Canonical source path/catalog/hash is retained as historical provenance; no old Golden file or hash is rewritten, and an unknown mismatched hash remains an error. | Candidate-enabled contract CLI; 10-test `test_golden_case_schema_0_2`; seven base Golden files compare unchanged to base. |
| R05 | Restores the frozen V4 `EV_SUCTION` presentation values, including “不适用/其他（请备注说明）”, while the evaluator continues to accept only valid single/double suction for formulas. | Metadata contract (110-test group), architecture and evaluator matrix. |
| R06 | Synchronizes current scope, blockers and evidence in governance; keeps the status BLOCKED and keeps wheel/motor baseline defects visible. Only pump-specific `tools/audit_release.py` diagnostics are included; the release-audit test file and any non-pump behavior are excluded. | `HANDOFF.md`, `TASK_STATE.md`, `ROADMAP.md`, `BASELINE.md`, `QA_BACKLOG.md`, this report and reviewed manifest. |

## Existing full-suite failures retained

The final 916-test suite reproduces 3 V4 motor reader/writer assertion failures and one release-audit error because `wheel_pmsm_status` is absent from the generated audit result. These are outside the authorized pump boundary and were neither edited nor hidden:

- `unit.test_v4_reader.V4ReaderTests.test_copied_v4_row_is_read_and_evaluated`
- `unit.test_v4_writer.V4WriterTests.test_end_to_end_v4_1500_rows_read_evaluate_write_and_reopen`
- `unit.test_v4_writer.V4WriterTests.test_writer_creates_new_workbook_with_locked_results`
- `unit.test_release_audit.ReleaseAuditTests.test_source_and_bundled_wheel_pass_release_audit` (error: missing `wheel_pmsm_status`)

The existing three skipped tests remain skipped. The source worktree's `tests/unit/test_release_audit.py` had only a CRLF/LF status difference and is excluded; the branch does not claim a successful bundled-wheel audit.

## Not run / limitations

The one-time independent helper `docs/pump_v2_independent_acceptance_20260927.py --checks` was not included or treated as a required test. Its checks mode requires `outputs/phase1_pump_unified_20260927_01/evidence_v07/ns_boundary_70_application_rerun.jsonl`, an external historical artifact unavailable in this clean checkout. This is recorded as an exclusion in the manifest; current production-path numeric, boundary, candidate and Application tests are independently runnable here.

No Golden case was approved, no Phase 1 PASS was declared, no Phase 2 feature was started, and no push was authorized. The final-SHA fresh replay completed with a clean status; the exact SHA is reported in the execution handoff because a report inside a commit cannot embed its own hash. Stop for the original independent formal review.

## R07 follow-up implementation and verification (2026-09-28)

The user authorized a focused R07 follow-up after the independent report found an unknown-keyword pump route and machine-specific external evidence paths. Work continued in the existing isolated branch worktree, based on merge commit `9e4e29aa431323791f6399778ee29a11315a29b7`. The original `G:\Python Project\EquipEffi` worktree was not modified, cleaned, copied from, or used as a test directory.

R07 changes are limited to exact `product_type`/explicit-profile pump routing, an external evidence registry and injectable evidence root, exact registered historical hash acceptance, direct regression tests, Windows CI, and governance/reporting. The public route now rejects unknown strings even when they contain “多级”, “管道”, or “单级单吸”; three Application API negative cases require `NOT_IN_RELEASE_SCOPE`, `UNRESOLVED`, `INVALID_INPUT`, and route-only trace. The validator resolves portable v0.3 evidence under `--external-evidence-root` or `EQUIPEFFI_EXTERNAL_EVIDENCE_ROOT`, verifies registered raw-byte SHA-256, and prevents paths escaping that root. GitHub CI uses `--skip-external-evidence` and reports the skipped byte checks explicitly; this is structural/source-pin CI evidence, not a claim that CI has the external PDF. The standard PDF is not committed.

Only the exact registered schema-version/catalog/path/hash tuples are treated as historical repository evidence. The immutable 0.1 cases and their hashes were not rewritten; arbitrary mismatched implementation hashes and the old hash under an unregistered schema version fail validation. Candidate cases remain `DRAFT/PENDING`.

| Check | Command / configuration | Environment | Result |
|---|---|---|---|
| Pump route, numeric, boundary, candidate and schema tests | `python -m unittest tests.unit.test_application_api tests.unit.test_pump_numeric_contract_v2 tests.unit.test_pump_rule_integrity_v2 tests.unit.test_pump_generated_boundaries_v2 tests.unit.test_pump_golden_case_0_3 tests.unit.test_golden_case_schema_0_2 -q` | CPython 3.12.14 x64; isolated branch worktree; `PYTHONPATH=src`; `PYTHONDONTWRITEBYTECODE=1` | 157 passed; 0.604 s |
| Metadata, architecture and evaluator matrix | `python -m unittest tests.contract.test_device_metadata tests.contract.test_architecture_boundaries tests.unit.test_device_evaluator_matrix -q` | Same | 394 passed; 7.530 s |
| Contract/schema with external bytes mounted | `python tools/validate_phase1_contracts.py --external-evidence-root <standard-library-root> --negative-probe --candidate-jsonl specs/equipment_efficiency/golden/pump_e2e_v0_3_candidates.jsonl` | Local standard library root; actual standard PDF bytes checked | 7 official cases and 26 candidates; 0 errors; 3 expected negative-probe errors |
| Contract/schema without external bytes | Same CLI with `--skip-external-evidence` instead of evidence root | Isolated worktree; no PDF mount required | 7 official and 26 candidate external checks explicitly skipped; schemas, registry pins and repository hashes pass; 0 errors; 3 expected negative-probe errors |
| Full unittest | `python -m unittest discover -q` | Same Python/worktree | 921 total: 914 passed, 3 failed, 1 error, 3 skipped; 151.137 s. The same 3 V4 motor failures and wheel release-audit error remain; no new pump failure. |

The exact commands `python -m compileall -q src tools tests` and `git diff --check` are run again against the final clean candidate before push. The Windows workflow whitespace step checks `72e8e490d2da56ec8064ad799750fb7b83425a57...HEAD` (the previously accepted R01–R06 head through the R07/master-integration delta); it does not reclassify existing whitespace in the earlier accepted baseline as an R07 defect. The PR workflow is configured to run on the existing `phase1/pump-v2-r01-r06` branch and on PR #1. Its `--skip-external-evidence` output must not be interpreted as external-PDF verification.

Initial GitHub Windows runs for `90af7f882aad542bd4f5d992acdb62a91da341de` failed one new evidence-root test because Windows Actions returned the temporary directory using its 8.3 short path while the resolver correctly returned the canonical long path. The test now compares against `evidence_root.resolve()`; no production route or numeric code changed. The follow-up commit and rerun status are reported in the execution handoff.

The R07 file-by-file allowlist and provenance notes are in `PUMP_V2_R07_COMMIT_MANIFEST.md`. Phase 1 remains `BLOCKED` pending fixed-SHA independent review, named Golden approval, and Solution/Product Review. No Golden approval, Phase 1 PASS, or Phase 2 work is authorized. The current pushed SHA is supplied outside this report because a commit cannot include its own final hash.
