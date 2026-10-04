"""Phase 3 R3：as_of / 标准生命周期规则收口。

Owner 正式决定（2026-10-02，**取代**此前"评价日期早于标准实施日期则不执行计算"的设计）：

- 评价日期 `as_of` 只用于：默认新建分析日期、用户手动修改、Record 历史追溯、
  Reopen 显示原评价日期；
- `as_of` **不再**决定所选标准能否执行；
- 用户可以主动使用未实施 / 现行 / 已废止的标准版本；只要明确选定版本，
  软件就按该版本的冻结规则正常计算；
- 标准生命周期状态只作**非阻断提示**，不得阻止计算、不得改成 `INSUFFICIENT_DATA`、
  不得改变 `evaluation_status`、不得改变 Finalize 权限、不得自动切换标准版本。
"""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from equipeffi.application.services.centrifugal_pump_analysis_service import (
    FINALIZABLE_STATUSES,
    AnalysisError,
    CentrifugalPumpAnalysisService,
    PumpAnalysisRequest,
)
from equipeffi.infrastructure.persistence.records_migrations import migrate_records_database
from equipeffi.infrastructure.persistence.sqlite_records_repository import (
    SqliteRecordRepository,
    SqliteWorkspaceRepository,
)
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository

ROOT = Path(__file__).resolve().parents[2]
WATER = "单级单吸清水离心泵"
CHEMICAL = "单级石油化工离心泵"

#: 标准实施日期为 2026-03-01：分别取实施前、实施当日、实施后。
BEFORE_EFFECTIVE = date(2026, 2, 28)
ON_EFFECTIVE = date(2026, 3, 1)
AFTER_EFFECTIVE = date(2026, 10, 3)
AS_OF_SAMPLES = (BEFORE_EFFECTIVE, ON_EFFECTIVE, AFTER_EFFECTIVE)

WATER_VALUES = {"QBEP": "100", "HBEP": "50", "speed": "2900",
                "efficiency": "90", "suction": "单吸", "stages": "1"}
CHEMICAL_VALUES = {"QBEP": "100", "HBEP": "14", "speed": "2900",
                   "efficiency": "73", "suction": "单吸", "stages": "1"}

BUSINESS_FIELDS = (
    "evaluation_status", "grade", "ui_conclusion", "category_status",
    "matched_rule_id", "thresholds", "issue_codes", "missing_fields",
    "extra_metrics", "calculation_trace", "support_status", "rule_profile",
)


def _service(workspaces=None, records=None) -> CentrifugalPumpAnalysisService:
    return CentrifugalPumpAnalysisService(
        JsonStandardRepository(ROOT / "src" / "equipeffi"), workspaces, records)


def _request(category: str, as_of: date, values: dict) -> PumpAnalysisRequest:
    return PumpAnalysisRequest(category, as_of, **values)


class _DbCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.tmp.name) / "records.sqlite"
        migrate_records_database(self.db, app_version="test")
        self.service = _service(SqliteWorkspaceRepository(self.db),
                                SqliteRecordRepository(self.db))

    def tearDown(self):
        self.tmp.cleanup()


class AsOfIsNotAnExecutionGateTests(_DbCase):
    """核心规则：同一输入在实施日前后必须得到**相同业务结果**。"""

    def _evaluate_all(self, category: str, values: dict) -> list:
        return [self.service.evaluate(_request(category, as_of, values))
                for as_of in AS_OF_SAMPLES]

    def test_before_effective_date_still_runs_the_evaluator(self):
        """提前日期必须正常进入 evaluator，而不是被短路成 INSUFFICIENT_DATA。"""

        result = self.service.evaluate(
            _request(WATER, BEFORE_EFFECTIVE, WATER_VALUES))
        self.assertNotEqual(result.evaluation_status, "INSUFFICIENT_DATA")
        self.assertEqual(result.evaluation_status, "SUCCESS")
        self.assertTrue(result.provenance["ruleset_executed"])
        self.assertEqual(result.rule_profile, "pump_water")
        self.assertTrue(result.references["standard"]["pack_hash"])
        self.assertNotIn("STANDARD_NOT_YET_EFFECTIVE", result.issue_codes)

    def test_water_business_result_identical_across_as_of(self):
        results = self._evaluate_all(WATER, WATER_VALUES)
        baseline = results[0]
        self.assertEqual(baseline.evaluation_status, "SUCCESS")
        self.assertEqual(baseline.grade, "1")
        for as_of, other in zip(AS_OF_SAMPLES, results):
            with self.subTest(as_of=as_of.isoformat()):
                for field in BUSINESS_FIELDS:
                    self.assertEqual(
                        getattr(other, field), getattr(baseline, field),
                        f"{field} 必须与 as_of 无关")

    def test_chemical_business_result_identical_across_as_of(self):
        results = self._evaluate_all(CHEMICAL, CHEMICAL_VALUES)
        baseline = results[0]
        self.assertEqual(baseline.evaluation_status, "SUCCESS")
        self.assertEqual(baseline.grade, "2")
        self.assertEqual(baseline.matched_rule_id, "GB19762-R000014")
        for as_of, other in zip(AS_OF_SAMPLES, results):
            with self.subTest(as_of=as_of.isoformat()):
                for field in BUSINESS_FIELDS:
                    self.assertEqual(
                        getattr(other, field), getattr(baseline, field),
                        f"{field} 必须与 as_of 无关")

    def test_date_does_not_participate_in_thresholds_or_range_decisions(self):
        """日期不得影响阈值、等级或范围判断（用范围外输入再验证一次）。"""

        out_of_range = dict(WATER_VALUES, QBEP="3")
        results = self._evaluate_all(WATER, out_of_range)
        for other in results[1:]:
            self.assertEqual(other.evaluation_status, results[0].evaluation_status)
            self.assertEqual(other.thresholds, results[0].thresholds)
            self.assertEqual(other.issue_codes, results[0].issue_codes)

    def test_finalizable_does_not_depend_on_as_of(self):
        for category, values in ((WATER, WATER_VALUES), (CHEMICAL, CHEMICAL_VALUES)):
            results = self._evaluate_all(category, values)
            expected = {r.finalizable for r in results}
            with self.subTest(category=category):
                self.assertEqual(len(expected), 1, "finalizable 不得随 as_of 变化")
                self.assertTrue(results[0].finalizable)

    def test_all_three_dates_are_finalizable_and_preserved(self):
        for category, values in ((WATER, WATER_VALUES), (CHEMICAL, CHEMICAL_VALUES)):
            for as_of in AS_OF_SAMPLES:
                with self.subTest(category=category, as_of=as_of.isoformat()):
                    request = _request(category, as_of, values)
                    result = self.service.evaluate(request)
                    self.assertIn(result.evaluation_status, FINALIZABLE_STATUSES)
                    record = self.service.finalize(
                        record_id=f"R-{category}-{as_of}", workspace_id=None,
                        request=request, result=result)
                    # Record 正确保存各自的 as_of
                    self.assertEqual(record.as_of, as_of.isoformat())
                    self.assertEqual(record.input_snapshot["as_of"], as_of.isoformat())
                    # Reopen 保留原 as_of
                    reopened = self.service.open_record(record.record_id)
                    self.assertEqual(reopened.as_of, as_of.isoformat())
                    self.assertEqual(
                        reopened.result_snapshot["as_of"], as_of.isoformat())


class LifecycleWarningTests(_DbCase):
    """标准生命周期只做非阻断提示，且与业务判定严格分离。"""

    def test_before_effective_date_emits_a_short_non_blocking_warning(self):
        """Phase 5 Owner 规则：提前日期只给**几个字**的非阻断提醒。"""

        result = self.service.evaluate(
            _request(WATER, BEFORE_EFFECTIVE, WATER_VALUES))
        self.assertTrue(result.warnings)
        self.assertEqual(result.warnings, ("该标准尚未实施",))
        # 不要求用户做任何确认；不改变业务结论
        self.assertEqual(result.evaluation_status, "SUCCESS")

    def test_no_warning_on_or_after_effective_date(self):
        for as_of in (ON_EFFECTIVE, AFTER_EFFECTIVE):
            with self.subTest(as_of=as_of.isoformat()):
                result = self.service.evaluate(_request(WATER, as_of, WATER_VALUES))
                self.assertEqual(result.warnings, ())

    def test_warning_is_not_a_business_status(self):
        """warning 不得进入 evaluation_status / issue_codes / missing_fields。"""

        result = self.service.evaluate(
            _request(WATER, BEFORE_EFFECTIVE, WATER_VALUES))
        self.assertTrue(result.warnings)
        self.assertEqual(result.evaluation_status, "SUCCESS")
        self.assertEqual(result.issue_codes, ())
        self.assertEqual(result.missing_fields, ())
        self.assertTrue(result.finalizable)
        self.assertFalse(result.not_finalizable_reason)

    def test_warning_does_not_change_the_result_payload(self):
        """有 warning 与无 warning 的结果，除 warnings 外完全一致。"""

        early = self.service.evaluate(_request(WATER, BEFORE_EFFECTIVE, WATER_VALUES))
        later = self.service.evaluate(_request(WATER, AFTER_EFFECTIVE, WATER_VALUES))
        self.assertNotEqual(early.warnings, later.warnings)
        for field in BUSINESS_FIELDS:
            with self.subTest(field=field):
                self.assertEqual(getattr(early, field), getattr(later, field))

    def test_warning_is_stored_in_the_record_for_traceability(self):
        request = _request(WATER, BEFORE_EFFECTIVE, WATER_VALUES)
        result = self.service.evaluate(request)
        record = self.service.finalize(record_id="R-warn", workspace_id=None,
                                       request=request, result=result)
        self.assertTrue(record.result_snapshot["warnings"])
        reopened = self.service.open_record("R-warn")
        self.assertTrue(reopened.result_snapshot["warnings"])

    def test_category_level_results_carry_no_lifecycle_warning(self):
        """类别级结论没有选定标准版本，因此不产生生命周期提示。"""

        result = self.service.evaluate(PumpAnalysisRequest("其他类别", AFTER_EFFECTIVE))
        self.assertEqual(result.warnings, ())


class AsOfFinalizePolicyTests(_DbCase):
    """Finalize 政策不得再有任何 as_of 特例。"""

    def test_no_as_of_specific_finalize_exception_exists(self):
        """提前日期与实施后日期必须有完全相同的 Finalize 政策。"""

        outcomes = []
        for as_of in (BEFORE_EFFECTIVE, AFTER_EFFECTIVE):
            request = _request(WATER, as_of, WATER_VALUES)
            result = self.service.evaluate(request)
            record = self.service.finalize(
                record_id=f"R-{as_of}", workspace_id=None,
                request=request, result=result)
            outcomes.append((record.evaluation_status, record.grade))
        self.assertEqual(outcomes[0], outcomes[1])

    def test_invalid_input_is_rejected_regardless_of_as_of(self):
        for as_of in AS_OF_SAMPLES:
            with self.subTest(as_of=as_of.isoformat()):
                request = _request(WATER, as_of, dict(WATER_VALUES, stages="2"))
                result = self.service.evaluate(request)
                self.assertEqual(result.evaluation_status, "INVALID_INPUT")
                self.assertFalse(result.finalizable)
                with self.assertRaises(AnalysisError):
                    self.service.finalize(record_id="R-x", workspace_id=None,
                                          request=request, result=result)

    def test_uncertain_category_is_rejected_regardless_of_as_of(self):
        for as_of in AS_OF_SAMPLES:
            with self.subTest(as_of=as_of.isoformat()):
                request = PumpAnalysisRequest("不确定类别", as_of)
                result = self.service.evaluate(request)
                self.assertFalse(result.finalizable)
                with self.assertRaises(AnalysisError):
                    self.service.finalize(record_id="R-u", workspace_id=None,
                                          request=request, result=result)
                self.assertEqual(self.service.list_records(), [])


class LifecycleWarningUiTests(_DbCase):
    """UI 必须把生命周期提示作为非阻断 warning 展示。"""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def _page(self, as_of: date | None = None):
        """构造分析页。

        Phase 7：普通页面不再有评价日期输入（自动取本机当天）。因此这里不再
        通过 UI 设置日期；需要特定日期的用例直接在 Result 契约层验证
        （见 `_service_request`）。
        """

        from equipeffi.presentation.qt.pages.analysis import AnalysisPage

        page = AnalysisPage(self.service, as_of=as_of)
        page.category.setCurrentIndex(page.category.findData(WATER))
        page.point_inputs["QBEP"].setText("100")
        page.point_inputs["HBEP"].setText("50")
        page.point_inputs["speed"].setText("2900")
        page.point_inputs["efficiency"].setText("90")
        page.suction.setCurrentIndex(page.suction.findData("单吸"))
        return page

    def test_early_as_of_shows_non_blocking_warning_and_still_calculates(self):
        """评价日期早于实施日时仍正常计算、仍自动形成 Record（非阻断）。"""

        page = self._page(BEFORE_EFFECTIVE)
        result = page.evaluate()
        self.assertEqual(result.evaluation_status, "SUCCESS")
        self.assertEqual(result.grade, "1")
        self.assertIn("该标准尚未实施", page.warning_label.text())
        # 非阻断：合法终态已自动记录
        self.assertEqual(page.last_record_status, "RECORDED")
        self.assertIsNotNone(page.last_saved_record_id)

    def test_lifecycle_warning_is_non_blocking_at_the_contract_level(self):
        """直接以早于实施日的 as_of 调用 Application：计算与固化都不被阻断。"""

        request = self._request(BEFORE_EFFECTIVE)
        outcome = self.service.analyze_and_record(request)
        self.assertEqual(outcome.result.evaluation_status, "SUCCESS")
        self.assertEqual(outcome.result.grade, "1")
        self.assertIn("该标准尚未实施", outcome.result.warnings)
        self.assertEqual(outcome.record_status, "RECORDED")

    def _request(self, as_of: date):
        from equipeffi.application.services.centrifugal_pump_analysis_service import (
            PumpAnalysisRequest,
        )

        return PumpAnalysisRequest(
            product_category=WATER, as_of=as_of, QBEP="100", HBEP="50",
            speed="2900", efficiency="90", suction="单吸", stages="1")

    def test_warning_label_hidden_when_no_warning(self):
        page = self._page(AFTER_EFFECTIVE)
        page.show()
        self.app.processEvents()
        page.evaluate()
        self.assertEqual(page.warning_label.text(), "")
        self.assertFalse(page.warning_label.isVisible())

    def test_warning_text_is_not_mixed_into_the_business_summary(self):
        page = self._page(BEFORE_EFFECTIVE)
        page.evaluate()
        ordinary = "\n".join([page.conclusion.text(), page.summary.text(),
                              page.basis.text()])
        self.assertNotIn("该标准尚未实施", ordinary)
        self.assertIn("该标准尚未实施", page.warning_label.text())


if __name__ == "__main__":
    unittest.main()
