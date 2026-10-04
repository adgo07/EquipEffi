"""Phase 3 P3-G04：29 条 owner-approved Golden 回放与统一入口边界测试。

覆盖：
- 18 条 pump_water `golden-case-0.4`（经统一 AnalysisService 回放）
- 11 条 pump_chemical `golden-case-0.5`（经统一 AnalysisService 回放）
- 化学 Q 与 ns 端点的 inclusive/exclusive、唯一规则行与 Δη 分支

注意：`golden-case-0.5` 中石化案例的 `evaluation_layer` 为
`PROFILE_EVALUATOR_TECHNICAL`，`expected_result.support_status` 为 null；
统一 AnalysisService 额外给出**发布门禁**维度（Phase 5 起石化泵为
`SUPPORTED` 候选）。Golden 的 `evaluation_layer` 与历史 provenance
**未被改写**——它表示历史批准来源，当前正式产品链的证据另见
`specs/equipment_efficiency/evidence/phase5_chemical_stage_d_e2e.json`。
因此本测试只对业务真值字段断言，不对 `support_status` 做跨层级比较。
"""
from __future__ import annotations

import json
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from equipeffi.application.services.centrifugal_pump_analysis_service import (
    CentrifugalPumpAnalysisService,
    PumpAnalysisRequest,
)
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository

ROOT = Path(__file__).resolve().parents[2]
WATER_DIR = ROOT / "specs/equipment_efficiency/golden/pump_water"
CHEMICAL_DIR = ROOT / "specs/equipment_efficiency/golden/pump_chemical"

#: 测试 harness 固定日期；这只是测试条件，不是产品默认值。
TEST_AS_OF = date(2026, 8, 23)

#: 化学表2 ns 分档端点（标准原文：20≤ns<60、60≤ns<120、120≤ns≤210、210<ns≤300）。
NS_ENDPOINTS: tuple[tuple[str, bool], ...] = (
    ("20", True), ("60", False), ("120", True), ("210", True), ("300", True),
)

STEP = Decimal("0.000001")

#: 端点 → 期望唯一规则行（单级石化泵、5<Q≤300）。
CHEMICAL_SINGLE_NS_RULES: tuple[tuple[str, str], ...] = (
    ("30", "GB19762-R000011"),
    ("90", "GB19762-R000012"),
    ("150", "GB19762-R000013"),
    ("250", "GB19762-R000014"),
)


def _service() -> CentrifugalPumpAnalysisService:
    return CentrifugalPumpAnalysisService(JsonStandardRepository(ROOT / "src" / "equipeffi"))


def _request(case: dict, as_of: date = TEST_AS_OF) -> PumpAnalysisRequest:
    raw = case["raw_inputs"]
    return PumpAnalysisRequest(
        product_category=raw["product_type"],
        as_of=as_of,
        QBEP=raw.get("QBEP"),
        HBEP=raw.get("HBEP"),
        speed=raw.get("speed"),
        efficiency=raw.get("efficiency"),
        suction=raw.get("suction"),
        stages=raw.get("stages"),
        record_id=case["case_id"],
    )


def _load(directory: Path, schema_version: str) -> list[dict]:
    cases = []
    for path in sorted(directory.glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        if case.get("case_schema_version") == schema_version:
            cases.append(case)
    return cases


class ApprovedGoldenReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = _service()
        cls.water = _load(WATER_DIR, "golden-case-0.4")
        cls.chemical = _load(CHEMICAL_DIR, "golden-case-0.5")

    def test_owner_approved_case_count_is_29(self):
        self.assertEqual(len(self.water), 18, "pump_water 0.4 批准案例数必须为 18")
        self.assertEqual(len(self.chemical), 11, "pump_chemical 0.5 批准案例数必须为 11")
        self.assertEqual(len(self.water) + len(self.chemical), 29)

    def test_water_cases_replay_through_unified_service(self):
        for case in self.water:
            with self.subTest(case=case["case_id"]):
                self.assertEqual(case["approval_status"], "APPROVED")
                self.assertEqual(case["profile_id"], "pump_water")
                result = self.service.evaluate(_request(case))
                expected = case["expected_result"]
                self.assertEqual(result.ui_conclusion, expected["ui_conclusion"])
                self.assertEqual(result.grade, expected["grade"])
                self.assertEqual(result.evaluation_status, expected["evaluation_status"])
                self.assertEqual(result.category_status, expected["category_status"])
                self.assertEqual(list(result.issue_codes), expected["issue_codes"])
                self.assertEqual(result.matched_rule_id,
                                 case["expected_calculation_trace"]["matched_rule_id"])

    def test_chemical_cases_replay_through_unified_service(self):
        for case in self.chemical:
            with self.subTest(case=case["case_id"]):
                self.assertEqual(case["approval_status"], "APPROVED")
                self.assertEqual(case["profile_id"], "pump_chemical")
                result = self.service.evaluate(_request(case))
                expected = case["expected_result"]
                self.assertEqual(result.ui_conclusion, expected["ui_conclusion"],
                                 f"{case['case_id']} 结论必须与 owner 批准一致")
                self.assertEqual(result.grade, expected["grade"])
                self.assertEqual(result.evaluation_status, expected["evaluation_status"])
                self.assertEqual(result.category_status, expected["category_status"])
                self.assertEqual(list(result.issue_codes), expected["issue_codes"])
                self.assertEqual(result.matched_rule_id,
                                 case["expected_calculation_trace"]["matched_rule_id"])

    def test_chemical_release_gate_is_promoted_to_support_candidate(self):
        """Phase 5：统一入口对石化泵的发布门禁提升为 `SUPPORTED` 候选。

        Phase 3 时该断言为 `NOT_IN_RELEASE_SCOPE`（当时不得提升）；Phase 5 完成
        pump_chemical Stage D 后，统一正式产品路径的 `support_status` 变为
        `SUPPORTED`。这是**发布门禁维度**的变化，不改变任何业务真值——
        本文件的业务结论断言（等级 / 阈值 / 规则 / trace）全部保持原样。
        """

        for case in self.chemical:
            with self.subTest(case=case["case_id"]):
                result = self.service.evaluate(_request(case))
                self.assertEqual(result.support_status, "SUPPORTED")
                self.assertEqual(result.rule_profile, "pump_chemical")

    def test_chemical_golden_derived_values_match_owner_approved_trace(self):
        for case in self.chemical:
            trace = case["expected_calculation_trace"]
            if trace.get("matched_rule_id") is None:
                continue
            with self.subTest(case=case["case_id"]):
                result = self.service.evaluate(_request(case))
                self.assertEqual(result.calculation_trace["thresholds_internal"],
                                 trace["grade_thresholds_internal"])

    def test_owner_defined_cases_carry_owner_provenance_without_candidate_fabrication(self):
        owner_defined = [c for c in self.chemical
                         if c["provenance"]["provenance_kind"] == "OWNER_DEFINED"]
        self.assertEqual(len(owner_defined), 3)
        refs = sorted(c["provenance"]["owner_defined_case_ref"] for c in owner_defined)
        self.assertEqual(refs, ["C10", "C11", "C9"])
        for case in owner_defined:
            with self.subTest(case=case["case_id"]):
                self.assertNotIn("source_candidate_file", case["provenance"])
                self.assertNotIn("source_candidate_line", case["provenance"])
                self.assertTrue(case["provenance"]["standard_evidence"])
                self.assertTrue(case["provenance"]["canonical_evidence"])

    def test_candidate_derived_cases_keep_candidate_provenance(self):
        derived = [c for c in self.chemical
                   if c["provenance"]["provenance_kind"] == "CANDIDATE_DERIVED"]
        self.assertEqual(len(derived), 8)
        for case in derived:
            with self.subTest(case=case["case_id"]):
                provenance = case["provenance"]
                self.assertTrue(provenance["source_candidate_case_id"].startswith("GC-PUMP-V3-"))
                self.assertGreaterEqual(provenance["source_candidate_line"], 1)
                self.assertEqual(len(provenance["source_candidate_sha256"]), 64)


class UnifiedBoundaryTests(unittest.TestCase):
    """统一入口的化学 Q / ns 端点、唯一规则行与 Δη 分支。"""

    @classmethod
    def setUpClass(cls):
        cls.service = _service()

    def _evaluate(self, category: str, *, q: str, h: str, stages: str = "1",
                  suction: str = "单吸", efficiency: str = "80"):
        return self.service.evaluate(PumpAnalysisRequest(
            category, TEST_AS_OF, QBEP=q, HBEP=h, speed="2900",
            efficiency=efficiency, suction=suction, stages=stages))

    def test_chemical_flow_lower_endpoint_is_exclusive(self):
        """Q=5 为开区间下界：不适用；Q 略大于 5 才进入标准范围。"""

        at = self._evaluate("单级石油化工离心泵", q="5", h="50")
        self.assertEqual(at.evaluation_status, "OUT_OF_STANDARD_SCOPE")
        self.assertEqual(at.ui_conclusion, "不适用")

        above = self._evaluate("单级石油化工离心泵", q="5.000001", h="50")
        self.assertNotEqual(above.ui_conclusion, "不适用")

    def test_chemical_flow_just_above_300_switches_to_unbounded_interval(self):
        below = self._evaluate("单级石油化工离心泵", q="300", h="50")
        above = self._evaluate("单级石油化工离心泵", q="300.000001", h="50")
        self.assertEqual(below.evaluation_status, "SUCCESS")
        self.assertEqual(above.evaluation_status, "SUCCESS")
        # 两个区间有不同 offsets，等级阈值必须不同（证明走到了另一规则行）
        self.assertNotEqual(below.calculation_trace["thresholds_internal"],
                            above.calculation_trace["thresholds_internal"])

    def test_chemical_ns_endpoints_are_inclusive_or_exclusive_as_published(self):
        """20/60/120/210/300 端点按标准开闭语义，且各命中唯一规则行。"""

        # ns 由 Q/H/n 反推；用 Q=100、n=2900，改 H 得到不同 ns（单吸 S=1、stages=1）
        samples = {
            "20": "100", "60": "100", "120": "100", "210": "100", "300": "100",
        }
        observed_rules = set()
        for target in NS_ENDPOINTS:
            ns_value, _inclusive = target
            h = self._head_for_ns(float(ns_value))
            with self.subTest(ns=ns_value):
                result = self._evaluate("单级石油化工离心泵", q="100", h=h)
                self.assertIn(result.evaluation_status,
                              {"SUCCESS", "OUT_OF_STANDARD_SCOPE"})
                if result.matched_rule_id:
                    observed_rules.add(result.matched_rule_id)
        self.assertTrue(observed_rules.issubset(
            {f"GB19762-R0000{n}" for n in range(11, 19)}), observed_rules)

    def test_chemical_ns_outside_published_range_is_not_applicable(self):
        huge = self._evaluate("单级石油化工离心泵", q="100", h="1")
        tiny = self._evaluate("单级石油化工离心泵", q="100", h="100000")
        for label, result in (("ns too high", huge), ("ns too low", tiny)):
            with self.subTest(case=label):
                self.assertEqual(result.evaluation_status, "OUT_OF_STANDARD_SCOPE")
                self.assertEqual(result.ui_conclusion, "不适用")
                self.assertIsNone(result.grade)

    def test_each_ns_band_matches_exactly_one_rule_row(self):
        for ns_value, expected_rule in CHEMICAL_SINGLE_NS_RULES:
            h = self._head_for_ns(float(ns_value))
            with self.subTest(ns=ns_value):
                result = self._evaluate("单级石油化工离心泵", q="100", h=h)
                self.assertEqual(result.evaluation_status, "SUCCESS")
                self.assertEqual(result.matched_rule_id, expected_rule)

    def test_delta_eta_branch_is_used_above_210_and_not_in_120_210(self):
        """210<ns≤300 使用 Δη（公式(7)）；120≤ns≤210 的 Δ=0。"""

        above = self._evaluate("单级石油化工离心泵", q="100",
                               h=self._head_for_ns(250.0))
        middle = self._evaluate("单级石油化工离心泵", q="100",
                                h=self._head_for_ns(150.0))
        self.assertEqual(above.evaluation_status, "SUCCESS")
        self.assertEqual(middle.evaluation_status, "SUCCESS")
        self.assertIn("效率修正值 Δη（%）", above.calculation_trace["derived"])
        self.assertEqual(
            Decimal(above.calculation_trace["derived"]["效率修正值 Δη（%）"]),
            Decimal("0") if "效率修正值 Δη（%）" not in middle.calculation_trace["derived"]
            else Decimal(above.calculation_trace["derived"]["效率修正值 Δη（%）"]))
        self.assertNotEqual(
            above.calculation_trace["derived"]["效率修正值 Δη（%）"],
            middle.calculation_trace["derived"].get("效率修正值 Δη（%）"),
        )

    def test_water_boundaries_still_use_original_generated_rows(self):
        """water 原有生成边界行仍然被统一入口使用（未回归）。"""

        inside = self._evaluate("单级单吸清水离心泵", q="300", h="50")
        outside = self._evaluate("单级单吸清水离心泵", q="300.000001", h="50")
        self.assertEqual(inside.matched_rule_id, "GB19762-T3-01")
        self.assertEqual(outside.matched_rule_id, "GB19762-T3-02")

    @staticmethod
    def _head_for_ns(ns: float) -> str:
        """由目标 ns 反推 HBEP（单级、单吸、Q=100 m³/h、n=2900 r/min）。

        ns = 3.65 · n · sqrt(Q_s) / H^0.75，Q_s = QBEP / S / 3600。
        """

        q_s = 100.0 / 1.0 / 3600.0
        head = (3.65 * 2900.0 * (q_s ** 0.5) / ns) ** (4.0 / 3.0)
        return f"{head:.10f}"


if __name__ == "__main__":
    unittest.main()
