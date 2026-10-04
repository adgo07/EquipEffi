"""生成 Phase 5 pump_chemical Stage D 的正式 Application E2E 证据。

它证明**今天的正式产品链**已经成立：

    11 条 Approved Golden 的历史业务真值
      → 统一 Application 入口（CentrifugalPumpAnalysisService）
      → 实际 evaluator
      → 结果契约
      → 与历史真值一致

与历史 Golden 的分工（**不得混淆**）：

- `specs/equipment_efficiency/golden/pump_chemical/*.json` 表示**历史批准来源**，
  其 `evaluation_layer = PROFILE_EVALUATOR_TECHNICAL`、`support_status = null`，
  本脚本**不修改**它们（不改业务真值、不改历史 provenance、不批量改写 evaluation_layer）；
- 本脚本产出的证据表示**当前 Stage D 正式产品链**，二者并存、指向不同时点。

用法：

```powershell
$env:PYTHONPATH='src'
python tools/build_phase5_chemical_e2e_evidence.py
```

确定性：只读取 Golden 与实时计算结果，写入固定 JSON；重复运行结果一致。
"""
from __future__ import annotations

import json
import sys
from datetime import date
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from equipeffi.application.services.centrifugal_pump_analysis_service import (  # noqa: E402
    CentrifugalPumpAnalysisService,
    PumpAnalysisRequest,
)
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository  # noqa: E402

CHEMICAL_DIR = ROOT / "specs/equipment_efficiency/golden/pump_chemical"
OUTPUT = ROOT / "specs/equipment_efficiency/evidence/phase5_chemical_stage_d_e2e.json"

#: 测试 harness 固定日期；只是测试条件，不是产品默认值。
TEST_AS_OF = date(2026, 8, 23)

#: 逐条比对的历史业务真值字段（不得因本证据而改变）。
BUSINESS_FIELDS = ("evaluation_status", "grade", "ui_conclusion", "issue_codes",
                   "category_status")


def _stable_sha256(path: Path) -> str:
    """仓库文本哈希：UTF-8、CRLF→LF、SHA-256 大写十六进制。"""

    data = path.read_bytes().replace(b"\r\n", b"\n")
    return sha256(data).hexdigest().upper()


def _load_cases() -> list[dict]:
    cases = []
    for path in sorted(CHEMICAL_DIR.glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        if case.get("case_schema_version") == "golden-case-0.5":
            cases.append((path, case))
    return cases


def _request(case: dict) -> PumpAnalysisRequest:
    raw = case["raw_inputs"]
    return PumpAnalysisRequest(
        product_category=raw["product_type"],
        as_of=TEST_AS_OF,
        QBEP=raw.get("QBEP"),
        HBEP=raw.get("HBEP"),
        speed=raw.get("speed"),
        efficiency=raw.get("efficiency"),
        suction=raw.get("suction"),
        stages=raw.get("stages"),
        record_id=case["case_id"],
    )


def main() -> int:
    service = CentrifugalPumpAnalysisService(
        JsonStandardRepository(ROOT / "src" / "equipeffi"))
    cases = _load_cases()
    if len(cases) != 11:
        print(f"FAIL: 期望 11 条 chemical Golden，实际 {len(cases)}")
        return 1

    records = []
    mismatches = 0
    for path, case in cases:
        expected = case["expected_result"]
        result = service.evaluate(_request(case))
        actual = {
            "evaluation_status": result.evaluation_status,
            "grade": result.grade,
            "ui_conclusion": result.ui_conclusion,
            "issue_codes": list(result.issue_codes),
            "category_status": result.category_status,
        }
        expected_view = {
            "evaluation_status": expected.get("evaluation_status"),
            "grade": expected.get("grade"),
            "ui_conclusion": expected.get("ui_conclusion"),
            "issue_codes": list(expected.get("issue_codes") or []),
            "category_status": expected.get("category_status"),
        }
        consistent = all(actual[field] == expected_view[field]
                         for field in BUSINESS_FIELDS)
        if not consistent:
            mismatches += 1
            print(f"  MISMATCH {case['case_id']}: actual={actual} expected={expected_view}")
        records.append({
            "case_id": case["case_id"],
            "source_golden_file": path.relative_to(ROOT).as_posix(),
            "source_golden_text_sha256": _stable_sha256(path),
            "golden_evaluation_layer": case.get("evaluation_layer"),
            "golden_support_status": expected.get("support_status"),
            "historical_business_truth": expected_view,
            "formal_application_e2e": {
                **actual,
                "rule_profile": result.rule_profile,
                "matched_rule_id": result.matched_rule_id,
                "support_status": result.support_status,
                "finalizable": result.finalizable,
            },
            "business_truth_consistent": consistent,
        })

    payload = {
        "evidence_id": "PHASE5-CHEMICAL-STAGE-D-E2E",
        "phase": "Phase 5",
        "purpose": (
            "证明 11 条 pump_chemical Approved Golden 的历史业务真值可以通过当前"
            "正式 Application 链（统一入口 → 实际 evaluator → 结果契约）一致复现。"
        ),
        "product_surface": "PySide6 Qt Desktop (--qt) 所使用的统一 Application 入口",
        "entry_point": "CentrifugalPumpAnalysisService.evaluate",
        "as_of_basis": TEST_AS_OF.isoformat(),
        "as_of_note": "固定测试条件，不是产品默认值；评价日期不是业务门禁。",
        "golden_directory": CHEMICAL_DIR.relative_to(ROOT).as_posix(),
        "golden_case_count": len(cases),
        "business_fields_compared": list(BUSINESS_FIELDS),
        "support_status_expectation": "SUPPORTED",
        "support_promotion_status": "SUPPORT_PROMOTION_CANDIDATE",
        "historical_golden_untouched": (
            "本证据不修改任何 Golden 业务真值、历史 provenance 或 evaluation_layer；"
            "Golden 继续表示历史批准来源。"
        ),
        "cases": records,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"写入 {OUTPUT.relative_to(ROOT)}：{len(records)} 条，"
          f"不一致 {mismatches} 条")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
