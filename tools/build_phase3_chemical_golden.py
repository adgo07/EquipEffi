"""Generate the Phase 3 pump_chemical approved Golden records (golden-case-0.5).

Owner-approved business truth for C1-C11 is supplied by the product owner; this
script only formalizes it. It never invents or alters an expected conclusion:

* C1-C8 are derived from the existing technical candidates in
  ``pump_e2e_v0_3_candidates.jsonl`` (candidate provenance preserved).
* C9-C11 are owner-defined cases with no candidate artifact, so they carry
  ``OWNER_DEFINED`` provenance instead of a fabricated candidate file/line.

Every expected value is re-derived by replaying the current chemical evaluator
so that a mismatch stops generation instead of being written out.
"""
from __future__ import annotations

import hashlib
import json
from decimal import localcontext
from pathlib import Path

from equipeffi.domain.evaluation.evaluators.pump import (
    PUMP_DECIMAL_CONTEXT,
    ChemicalPumpEvaluator,
)
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_FILE = ROOT / "specs/equipment_efficiency/golden/pump_e2e_v0_3_candidates.jsonl"
OUT_DIR = ROOT / "specs/equipment_efficiency/golden/pump_chemical"

OWNER = "王玮"
APPROVED_AT = "2026-10-02T12:00:00+08:00"
REVIEWED_AT = "2026-10-02T12:00:00+08:00"
OWNER_EVIDENCE_ID = "USER_PROVIDED_OWNER_APPROVAL_2026-10-02_PUMP_CHEMICAL"
SOURCE_BASELINE_SHA = "3101e05abd7f33262a9449c390d61ec00008fb75"
CANONICAL_PUMP_JSON = ROOT / "src" / "equipeffi" / "resources" / "standards" / "pump.json"

DERIVED_KEY_BY_METRIC = {
    "suction_factor": "suction_factor",
    "stage_count": "stage_count",
    "q_for_ns_m3s": "q_for_ns_m3s",
    "h_for_ns_m": "h_for_ns_m",
    "ns_raw": "ns_raw",
    "eta_b": "基准效率_%",
    "delta_eta": "效率修正值_%",
    "eta_0": "规定点效率_%",
    "output_power_kw": "输出功率_kW",
}

# Owner-supplied expected business truth, transcribed verbatim from the Phase 3
# authorisation. These are the assertions the generator must reproduce.
OWNER_DEFINED_CASES = (
    {
        "owner_ref": "C9",
        "case_id": "GC-PUMP-V5-CHEMICAL-SINGLE-NS210-300-L2",
        "raw_inputs": {
            "product_type": "单级石油化工离心泵", "suction": "单吸", "stages": "1",
            "QBEP": "100", "HBEP": "14", "speed": "2900", "efficiency": "73",
        },
        "expect": {"evaluation_status": "SUCCESS", "grade": "2", "ui_conclusion": "2级",
                   "category_status": "APPLICABLE", "issue_codes": []},
        "ns_band": "210 < ns <= 300",
        "rule_id": "GB19762-R000014",
        "standard_evidence": "GB 19762-2025 表2、公式(1)、公式(4)~(7)：单级石化泵 5<Q<=300、210<ns<=300 行（η0 = η_b - Δη，公式(7)）",
        "canonical_evidence": "GB19762-R000014",
        "notes": ["产品负责人定义的石化单级泵 210<ns<=300 档位案例；预期结论由产品负责人批准。"],
    },
    {
        "owner_ref": "C10",
        "case_id": "GC-PUMP-V5-CHEMICAL-SINGLE-NS-ABOVE-300",
        "raw_inputs": {
            "product_type": "单级石油化工离心泵", "suction": "单吸", "stages": "1",
            "QBEP": "100", "HBEP": "10", "speed": "2900", "efficiency": "80",
        },
        "expect": {"evaluation_status": "OUT_OF_STANDARD_SCOPE", "grade": None,
                   "ui_conclusion": "不适用", "category_status": "APPLICABLE",
                   "issue_codes": ["OUT_OF_STANDARD_SCOPE"]},
        "ns_band": "ns > 300",
        "rule_id": None,
        "standard_evidence": "GB 19762-2025 表2：ns>300 超出标准适用范围，不生成等级",
        "canonical_evidence": "interval_boundaries.specific_speed_ns 上限 300",
        "notes": ["产品负责人定义的 ns>300 范围外案例；属于有效专业结论（不适用）。"],
    },
    {
        "owner_ref": "C11",
        "case_id": "GC-PUMP-V5-CHEMICAL-SINGLE-NS-BELOW-20",
        "raw_inputs": {
            "product_type": "单级石油化工离心泵", "suction": "单吸", "stages": "1",
            "QBEP": "100", "HBEP": "400", "speed": "2900", "efficiency": "80",
        },
        "expect": {"evaluation_status": "OUT_OF_STANDARD_SCOPE", "grade": None,
                   "ui_conclusion": "不适用", "category_status": "APPLICABLE",
                   "issue_codes": ["OUT_OF_STANDARD_SCOPE"]},
        "ns_band": "ns < 20",
        "rule_id": None,
        "standard_evidence": "GB 19762-2025 表2：ns<20 超出标准适用范围，不生成等级",
        "canonical_evidence": "interval_boundaries.specific_speed_ns 下限 20",
        "notes": ["产品负责人定义的 ns<20 范围外案例；属于有效专业结论（不适用）。"],
    },
)

COMMON_APPROVAL_BASIS = [
    "王玮作为产品负责人，于 2026-10-02 逐条批准本记录的业务真值（C1-C11 共 11 条全部通过）。",
    "预期结论与 GB 19762-2025 表2及公式(1)、(4)~(7) 的可追溯 Canonical 行一致。",
    "本记录不改动 pump_water 已批准的 18 条 golden-case-0.4，也不改变 pump_chemical 的 support_status。",
]

COMMON_KNOWN_LIMITS = [
    "pump_chemical 的 support_status 仍为 NOT_IN_RELEASE_SCOPE；本 Golden 不构成发布支持声明。",
    "正式支持提升仍需 Standard Development Guide Stage D 独立验收。",
    "表2精确边界由 generated boundary tests 负责，人工 Golden 不重复穷举全部端点。",
]


def canonical_candidate_sha256(record: dict) -> str:
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def _short(value) -> str:
    return "None" if value is None else str(value)[:24]


def canonical_file_sha256(path: Path) -> str:
    """Repository-text SHA-256 under the documented CRLF-to-LF normalization."""
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest().upper()


def build_source_sidecar(canonical_ids: list[str], clause: str) -> dict:
    return {
        "source_references": [
            {
                "source_id": "GB19762-2025-PDF",
                "artifact_kind": "EXTERNAL_FILE",
                "artifact_path": "6 7. GB 19762-2025 离心泵能效限定值及能效等级.pdf",
                "artifact_sha256": "7F515D8B9D6B4D2AB97FFA7BECB78520BA0579CFBD6D5ECA10C7E7CC77895FEC",
                "clause_or_table": clause,
                "pages": ["8-9"],
                "stable_data_ids": [],
                "evidence_role": "STANDARD",
                "note": "标准身份/哈希与相关印刷页；业务解释仍以 Canonical 与已批准真值为准。",
            },
            {
                "source_id": "pump-canonical-v1",
                "artifact_kind": "REPOSITORY_FILE",
                "artifact_path": "src/equipeffi/resources/standards/pump.json",
                "artifact_sha256": CANONICAL_PUMP_JSON_SHA256,
                "clause_or_table": "石油化工泵表2及公式(4)~(7)",
                "pages": ["8-9"],
                "stable_data_ids": canonical_ids,
                "evidence_role": "CANONICAL_PACK",
                "note": "Canonical 提供表2行与系数；不构成对本案例的业务批准。",
            },
        ]
    }


def replay(raw_inputs: dict, pack: dict) -> dict:
    evaluator = ChemicalPumpEvaluator()
    with localcontext(PUMP_DECIMAL_CONTEXT):
        result = evaluator.evaluate(dict(raw_inputs), pack)
    derived = {}
    for key, metric in DERIVED_KEY_BY_METRIC.items():
        value = result.calculated_metrics.get(metric)
        derived[key] = None if value is None else str(value)
    lookup = result.lookups[0] if result.lookups else {}
    return {
        "support_status": result.support_status,
        "category_status": result.category_status,
        "evaluation_status": result.evaluation_status,
        "ui_conclusion": result.conclusion.value,
        "grade": result.grade,
        "issue_codes": list(result.issue_codes),
        "trace": {
            "execution_basis": "BUSINESS_DRAFT",
            "derived": derived,
            "matched_rule_id": lookup.get("data_id"),
            "grade_thresholds_internal": [
                str(v) for v in result.calculated_metrics.get("grade_thresholds_internal", [])
            ],
        },
    }


def main() -> int:
    global CANONICAL_PUMP_JSON_SHA256
    CANONICAL_PUMP_JSON_SHA256 = canonical_file_sha256(CANONICAL_PUMP_JSON)
    documented = "5D91F01B1C5F26DC4F364A3156C4E974B159FA1005BD840489C0BC3465C18C0F"
    if CANONICAL_PUMP_JSON_SHA256 != documented:
        raise SystemExit(
            f"Canonical pump.json SHA-256 drifted: computed {CANONICAL_PUMP_JSON_SHA256}, "
            f"documented {documented}; refusing to pin a stale hash"
        )
    repository = JsonStandardRepository(ROOT / "src" / "equipeffi")
    pack = repository.get_pack("pump_chemical")
    raw_lines = CANDIDATE_FILE.read_text(encoding="utf-8").splitlines()
    candidates = [json.loads(line) for line in raw_lines if line.strip()]
    chemical = [(index + 1, record) for index, record in enumerate(candidates)
                if record.get("profile_id") == "pump_chemical"]
    if len(chemical) != 8:
        raise SystemExit(f"expected 8 chemical candidates, found {len(chemical)}")

    records = []
    # C1-C8: candidate-derived, provenance preserved verbatim.
    #
    # evaluation_layer is PROFILE_EVALUATOR_TECHNICAL, not APPLICATION_E2E. The
    # public Application release gate still returns NOT_IN_RELEASE_SCOPE for
    # pump_chemical without computing a result (frozen by
    # tests/unit/test_pump_golden_case_0_3.py), so claiming an Application E2E
    # layer here would misstate where these approved values can currently be
    # reproduced. The business truth below is unchanged from the owner approval.
    for owner_index, (line_no, candidate) in enumerate(chemical, start=1):
        replay_result = replay(candidate["raw_inputs"], pack)
        expected = {
            "support_status": None,
            "category_status": replay_result["category_status"],
            "evaluation_status": replay_result["evaluation_status"],
            "ui_conclusion": replay_result["ui_conclusion"],
            "grade": replay_result["grade"],
            "issue_codes": replay_result["issue_codes"],
        }
        record = {
            "case_schema_version": "golden-case-0.5",
            "case_id": candidate["case_id"].replace("GC-PUMP-V3-", "GC-PUMP-V5-"),
            "case_status": "APPROVED",
            "approval_status": "APPROVED",
            "review_status": "APPROVED",
            "device_type": "centrifugal_pump",
            "profile_id": "pump_chemical",
            "numeric_contract_id": "PUMP_NUMERIC_AND_DECISION_CONTRACT_V2",
            "evaluation_layer": "PROFILE_EVALUATOR_TECHNICAL",
            "raw_inputs": {**candidate["raw_inputs"]},
            "expected_result": expected,
            "expected_calculation_trace": replay_result["trace"],
            "source_sidecar": build_source_sidecar(
                [replay_result["trace"]["matched_rule_id"]] if replay_result["trace"]["matched_rule_id"] else [],
                "表2、公式(1)、公式(4)~(7)",
            ),
            "historical_origin_id": candidate["case_id"],
            "notes": [
                f"由 0.3 技术候选 {candidate['case_id']} 形式化为产品负责人批准的正式 Golden。",
                "候选 provenance 原样保留；预期结论未改写。",
            ],
            "review_owner": OWNER,
            "reviewed_at": REVIEWED_AT,
            "approved_at": APPROVED_AT,
            "approval_basis": list(COMMON_APPROVAL_BASIS),
            "known_limits": list(COMMON_KNOWN_LIMITS),
            "provenance": {
                "provenance_kind": "CANDIDATE_DERIVED",
                "source_candidate_case_id": candidate["case_id"],
                "source_candidate_schema_version": candidate["case_schema_version"],
                "source_candidate_file": "specs/equipment_efficiency/golden/pump_e2e_v0_3_candidates.jsonl",
                "source_candidate_line": line_no,
                "source_candidate_sha256": canonical_candidate_sha256(candidate),
                "source_baseline_sha": SOURCE_BASELINE_SHA,
            },
            "review_flags": [],
        }
        records.append(record)
        print(f"C{owner_index}: {record['case_id']} -> grade={expected['grade']} "
              f"status={expected['evaluation_status']} ns={_short(replay_result['trace']['derived']['ns_raw'])}")

    # C9-C11: owner-defined, no candidate artifact.
    for spec in OWNER_DEFINED_CASES:
        raw_inputs = {**spec["raw_inputs"], "input_basis": "STANDARD_BEP", "measurement_point": "BEP"}
        replay_result = replay(raw_inputs, pack)
        for key, want in spec["expect"].items():
            got = replay_result[key]
            if got != want:
                raise SystemExit(
                    f"{spec['owner_ref']}: owner-approved {key}={want!r} but current evaluator "
                    f"produces {got!r}; refusing to write a Golden that contradicts approved truth"
                )
        if spec["rule_id"] and replay_result["trace"]["matched_rule_id"] != spec["rule_id"]:
            raise SystemExit(
                f"{spec['owner_ref']}: expected rule {spec['rule_id']} but got "
                f"{replay_result['trace']['matched_rule_id']!r}"
            )
        record = {
            "case_schema_version": "golden-case-0.5",
            "case_id": spec["case_id"],
            "case_status": "APPROVED",
            "approval_status": "APPROVED",
            "review_status": "APPROVED",
            "device_type": "centrifugal_pump",
            "profile_id": "pump_chemical",
            "numeric_contract_id": "PUMP_NUMERIC_AND_DECISION_CONTRACT_V2",
            "evaluation_layer": "PROFILE_EVALUATOR_TECHNICAL",
            "raw_inputs": raw_inputs,
            "expected_result": {
                "support_status": None,
                "category_status": replay_result["category_status"],
                "evaluation_status": replay_result["evaluation_status"],
                "ui_conclusion": replay_result["ui_conclusion"],
                "grade": replay_result["grade"],
                "issue_codes": replay_result["issue_codes"],
            },
            "expected_calculation_trace": replay_result["trace"],
            "source_sidecar": build_source_sidecar(
                [spec["rule_id"]] if spec["rule_id"] else [], "表2、公式(1)、公式(4)~(7)"),
            "notes": list(spec["notes"]) + [f"owner_defined_case_ref={spec['owner_ref']}（ns 区间 {spec['ns_band']}）"],
            "review_owner": OWNER,
            "reviewed_at": REVIEWED_AT,
            "approved_at": APPROVED_AT,
            "approval_basis": list(COMMON_APPROVAL_BASIS),
            "known_limits": list(COMMON_KNOWN_LIMITS),
            "provenance": {
                "provenance_kind": "OWNER_DEFINED",
                "owner_approval_evidence_id": OWNER_EVIDENCE_ID,
                "owner_defined_case_ref": spec["owner_ref"],
                "standard_evidence": spec["standard_evidence"],
                "canonical_evidence": spec["canonical_evidence"],
            },
            "review_flags": [],
        }
        records.append(record)
        print(f"{spec['owner_ref']}: {record['case_id']} -> grade={replay_result['grade']} "
              f"status={replay_result['evaluation_status']} ns={_short(replay_result['trace']['derived']['ns_raw'])}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for record in records:
        path = OUT_DIR / f"{record['case_id']}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8", newline="\n")
    print(f"wrote {len(records)} records to {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
