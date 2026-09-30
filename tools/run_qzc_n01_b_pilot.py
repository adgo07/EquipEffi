from __future__ import annotations

import json
from decimal import Decimal, localcontext
from pathlib import Path

from equipeffi.domain.common.enums import ComparisonDirection
from equipeffi.domain.evaluation.grading import grade_three
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository
from tools.qzc_n01_b_reference import (
    clean_thresholds,
    clean_thresholds_alt,
    make_context,
    polynomial_current,
    polynomial_horner,
    specific_speed,
    specific_speed_alt,
    tolerance_limit,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "artifacts" / "qzc_n01_b"
PRECISIONS = (28, 34, 40, 50, 60)


def s(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, list):
        return [s(v) for v in value]
    if isinstance(value, tuple):
        return [s(v) for v in value]
    if isinstance(value, dict):
        return {k: s(v) for k, v in value.items()}
    return value


def main() -> None:
    repo = JsonStandardRepository(ROOT)
    water = repo.get_pack("pump_water")
    chemical = repo.get_pack("pump_chemical")
    cases = [
        {"id": "EXACT-NS", "category": "多级", "QBEP": "7200", "HBEP": "32", "speed": "10", "suction": "双吸", "stages": "2", "efficiency": "80"},
        {"id": "WATER-TYPICAL", "category": "单级单吸", "QBEP": "100", "HBEP": "50", "speed": "2900", "suction": "单吸", "stages": "1", "efficiency": "80"},
        {"id": "WATER-MULTI", "category": "多级", "QBEP": "100", "HBEP": "150", "speed": "2900", "suction": "双吸", "stages": "3", "efficiency": "80"},
        {"id": "WATER-HIGH-FLOW", "category": "单级双吸", "QBEP": "5000", "HBEP": "90", "speed": "1480", "suction": "双吸", "stages": "1", "efficiency": "88"},
    ]
    evidence = {
        "pilot": "QZC-N01-B",
        "reference_procedure": "PUMP-RP-0.1",
        "precision_set": list(PRECISIONS),
        "tolerance_seed": {
            "T-NL-ATOM": "max(1E-13, 1E-13*abs(reference))",
            "T-NL-COMPOSITE": "max(1E-10, 1E-12*abs(reference))",
            "status": "EXPERIMENT_SEED_ONLY",
        },
        "cases": [],
        "vectors": [],
    }
    rows = water["water"]["ci"]
    for case in cases:
        entry = {"id": case["id"], "inputs": case, "precision": {}}
        for precision in PRECISIONS:
            current = specific_speed(case, precision)
            alternate = specific_speed_alt(case, precision)
            item = {
                "current_ns": current["ns_raw"],
                "alt_ns": alternate["ns_raw"],
                "ns_abs_diff": abs(current["ns_raw"] - alternate["ns_raw"]),
                "h_pow_current": current["h_pow_0_75"],
                "h_pow_alt": alternate["h_pow_0_75"],
                "h_pow_abs_diff": abs(current["h_pow_0_75"] - alternate["h_pow_0_75"]),
            }
            matching = [r for r in rows if r["type"] == case["category"] and Decimal(str(r["q_min"])) <= Decimal(case["QBEP"]) <= Decimal(str(r["q_max"]))]
            if matching:
                row = matching[0]
                kind = "多级" if "多级" in case["category"] else "单级"
                coeff = water["water"]["formulas"][kind]
                thresholds = clean_thresholds(current["ns_raw"], case["QBEP"], coeff, row["ci"], precision)
                thresholds_alt = clean_thresholds_alt(alternate["ns_raw"], case["QBEP"], coeff, row["ci"], precision)
                with localcontext(make_context(precision)):
                    grade = grade_three(Decimal(case["efficiency"]), thresholds, ComparisonDirection.GREATER_OR_EQUAL)[0].value
                    grade_alt = grade_three(Decimal(case["efficiency"]), thresholds_alt, ComparisonDirection.GREATER_OR_EQUAL)[0].value
                item.update({
                    "thresholds": thresholds,
                    "thresholds_alt": thresholds_alt,
                    "threshold_max_abs_diff": max(abs(a - b) for a, b in zip(thresholds, thresholds_alt)),
                    "grade": grade,
                    "grade_alt": grade_alt,
                    "rule_id": row.get("data_id"),
                })
            entry["precision"][str(precision)] = item
        p50 = entry["precision"]["50"]
        p60 = entry["precision"]["60"]
        entry["seed_tolerance_checks"] = {
            "ns_50_vs_60_limit": tolerance_limit(p60["current_ns"], "T-NL-COMPOSITE"),
            "ns_50_vs_60_diff": abs(p50["current_ns"] - p60["current_ns"]),
            "ns_seed_pass": abs(p50["current_ns"] - p60["current_ns"]) <= tolerance_limit(p60["current_ns"], "T-NL-COMPOSITE"),
        }
        evidence["cases"].append(entry)
        evidence["vectors"].append({
            "vector_id": f"N01B-{case['id']}",
            "category": "Exact" if case["id"] == "EXACT-NS" else "Composite",
            "inputs": case,
            "profile": "pump_water",
            "operation": "specific_speed + clean_thresholds" if p50.get("thresholds") else "specific_speed",
            "reference": {"precision50": p50, "precision60": p60},
            "acceptance_mode": "EXACT" if case["id"] == "EXACT-NS" else "NUMERICAL_TOLERANCE_WITH_BUSINESS_EXACT",
            "tolerance_purpose": None if case["id"] == "EXACT-NS" else "cross-implementation numerical conformance only",
            "business_output": {"grade": p50.get("grade"), "rule_id": p50.get("rule_id")},
        })

    eta_coeff = chemical["chemical"]["eta_b"]["单级"]
    evidence["chemical_polynomial"] = {}
    for precision in PRECISIONS:
        with localcontext(make_context(precision)):
            x = Decimal("100").ln()
        current = polynomial_current(x, eta_coeff, precision)
        horner = polynomial_horner(x, eta_coeff, precision)
        evidence["chemical_polynomial"][str(precision)] = {
            "current": current,
            "horner": horner,
            "abs_diff": abs(current - horner),
            "seed_limit": tolerance_limit(current, "T-NL-COMPOSITE"),
            "seed_pass": abs(current - horner) <= tolerance_limit(current, "T-NL-COMPOSITE"),
        }
    evidence["vectors"].append({
        "vector_id": "N01B-CHEM-ETA-B-ORDER",
        "category": "Operation-order sensitivity",
        "inputs": {"QBEP": "100", "pump_kind": "单级"},
        "profile": "pump_chemical",
        "operation": "ln(Q) + eta_b polynomial current tree vs Horner",
        "reference": evidence["chemical_polynomial"]["50"],
        "acceptance_mode": "NUMERICAL_TOLERANCE_WITH_BUSINESS_EXACT",
        "tolerance_purpose": "cross-implementation numerical conformance only",
        "business_output": {"must_not_change_rule_or_grade": True},
    })

    exact_threshold = Decimal("80.12345678901234567890123456789012345678901234567")
    delta = Decimal("1E-48")
    thresholds = [exact_threshold, Decimal("70"), Decimal("60")]
    with localcontext(make_context(50)):
        boundary = {
            "T-delta": grade_three(exact_threshold - delta, thresholds, ComparisonDirection.GREATER_OR_EQUAL)[0].value,
            "T": grade_three(exact_threshold, thresholds, ComparisonDirection.GREATER_OR_EQUAL)[0].value,
            "T+delta": grade_three(exact_threshold + delta, thresholds, ComparisonDirection.GREATER_OR_EQUAL)[0].value,
            "epsilon_used": False,
        }
    evidence["business_boundary_exact"] = boundary
    evidence["vectors"].append({
        "vector_id": "N01B-BOUNDARY-TDELTA",
        "category": "Business boundary",
        "inputs": {"threshold": str(exact_threshold), "delta": str(delta)},
        "profile": "pump_water",
        "operation": "grade comparison T-delta / T / T+delta",
        "reference": boundary,
        "acceptance_mode": "EXACT_BUSINESS_OUTPUT",
        "tolerance_purpose": "none; numerical tolerance is forbidden for business comparison",
        "business_output": boundary,
    })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "execution_evidence.json"
    out.write_text(json.dumps(s(evidence), ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)
    print(json.dumps(s(evidence["business_boundary_exact"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
