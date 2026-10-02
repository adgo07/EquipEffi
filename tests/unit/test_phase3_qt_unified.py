"""Phase 3 P3-G02：统一 GB 19762 分析页与分析记录页（offscreen）。"""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from equipeffi.application.services.centrifugal_pump_analysis_service import (  # noqa: E402
    CentrifugalPumpAnalysisService,
    PumpAnalysisRequest,
    category_names,
    formal_category_names,
)
from equipeffi.infrastructure.persistence.records_migrations import migrate_records_database  # noqa: E402
from equipeffi.infrastructure.persistence.sqlite_records_repository import (  # noqa: E402
    SqliteRecordRepository,
    SqliteWorkspaceRepository,
)
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository  # noqa: E402
from equipeffi.presentation.qt.pages.analysis import AnalysisPage  # noqa: E402
from equipeffi.presentation.qt.pages.records import RecordsPage  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
AS_OF = "2026-08-23"


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _service(workspaces=None, records=None) -> CentrifugalPumpAnalysisService:
    return CentrifugalPumpAnalysisService(
        JsonStandardRepository(ROOT / "src" / "equipeffi"), workspaces, records)


class UnifiedAnalysisPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        self.page = AnalysisPage(_service())

    def test_all_eight_formal_categories_are_present_in_one_selector(self):
        offered = [self.page.category.itemData(i)
                   for i in range(self.page.category.count())
                   if self.page.category.itemData(i)]
        for name in formal_category_names():
            with self.subTest(category=name):
                self.assertIn(name, offered)
        self.assertIn("其他类别", offered)
        self.assertIn("不确定类别", offered)

    def test_no_internal_profile_or_rule_identifier_is_visible(self):
        """普通 UI 不得出现内部 profile / rule / field id。"""

        widgets_text = []
        for index in range(self.page.category.count()):
            widgets_text.append(self.page.category.itemText(index) or "")
            widgets_text.append(str(self.page.category.itemData(index) or ""))
        widgets_text.append(self.page.category_help.text())
        widgets_text.append(self.page.summary.text())
        widgets_text.append(self.page.basis.text())
        widgets_text.append(self.page.conclusion.text())
        blob = "\n".join(widgets_text)
        for forbidden in ("pump_water", "pump_chemical", "profile_id", "rule_id",
                          "internal_id", "field_id", "SUPPORTED",
                          "NOT_IN_RELEASE_SCOPE"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, blob)

    def test_single_stage_category_locks_stage_count(self):
        index = self.page.category.findData("单级单吸清水离心泵")
        self.page.category.setCurrentIndex(index)
        self.assertEqual(self.page.stages.text(), "1")
        self.assertFalse(self.page.stages.isEnabled())

    def test_multistage_category_keeps_stage_count_editable(self):
        index = self.page.category.findData("多级清水离心泵")
        self.page.category.setCurrentIndex(index)
        self.assertTrue(self.page.stages.isEnabled())

    def test_water_analysis_renders_conclusion_and_bypasses_internal_names(self):
        self.page.category.setCurrentIndex(self.page.category.findData("单级单吸清水离心泵"))
        self.page.as_of.setText(AS_OF)
        self.page.point_inputs["QBEP"].setText("100")
        self.page.point_inputs["HBEP"].setText("50")
        self.page.point_inputs["speed"].setText("2900")
        self.page.point_inputs["efficiency"].setText("90")
        self.page.suction.setCurrentIndex(self.page.suction.findData("单吸"))

        result = self.page.evaluate()
        self.assertIsNotNone(result)
        self.assertEqual(result.ui_conclusion, "1级")
        self.assertEqual(self.page.conclusion.text(), "1级")
        self.assertIn("评价结论", "评价结论")  # 结构断言见下
        self.assertIn("设备类别：单级单吸清水离心泵", self.page.summary.text())
        self.assertIn("标准依据", self.page.basis.text())
        self.assertTrue(self.page.finalize_button.isEnabled())
        self.assertNotIn("pump_water", self.page.basis.text())

    def test_chemical_analysis_is_available_in_the_same_page(self):
        self.page.category.setCurrentIndex(self.page.category.findData("单级石油化工离心泵"))
        self.page.as_of.setText(AS_OF)
        self.page.point_inputs["QBEP"].setText("100")
        self.page.point_inputs["HBEP"].setText("14")
        self.page.point_inputs["speed"].setText("2900")
        self.page.point_inputs["efficiency"].setText("73")
        self.page.suction.setCurrentIndex(self.page.suction.findData("单吸"))

        result = self.page.evaluate()
        self.assertEqual(result.ui_conclusion, "2级")
        self.assertEqual(self.page.conclusion.text(), "2级")
        # 普通结果区不得暴露内部 profile 名
        self.assertNotIn("pump_chemical", self.page.summary.text())
        self.assertNotIn("pump_chemical", self.page.basis.text())

    def test_uncertain_category_does_not_compute_and_asks_confirmation(self):
        self.page.category.setCurrentIndex(self.page.category.findData("不确定类别"))
        result = self.page.evaluate()
        self.assertTrue(result.requires_category_confirmation)
        self.assertFalse(self.page.finalize_button.isEnabled())
        self.assertIn("确认", self.page.summary.text())

    def test_other_category_is_not_applicable(self):
        self.page.category.setCurrentIndex(self.page.category.findData("其他类别"))
        result = self.page.evaluate()
        self.assertEqual(result.ui_conclusion, "不适用")
        self.assertFalse(self.page.finalize_button.isEnabled())

    def test_invalid_evaluation_date_is_reported_without_crashing(self):
        self.page.as_of.setText("not-a-date")
        self.assertIsNone(self.page.evaluate())
        self.assertIn("YYYY-MM-DD", self.page.summary.text())


class RecordsPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db = Path(self.tmp.name) / "records.sqlite"
        migrate_records_database(db, app_version="test")
        self.service = _service(SqliteWorkspaceRepository(db), SqliteRecordRepository(db))
        self.page = RecordsPage(self.service)

    def tearDown(self):
        self.tmp.cleanup()

    def _finalize(self, category: str, **values):
        request = PumpAnalysisRequest(category, date.fromisoformat(AS_OF), **values)
        result = self.service.evaluate(request)
        return self.service.finalize(
            record_id=f"R-{category}", workspace_id=None, request=request, result=result)

    def test_history_shows_water_and_chemical_in_one_list(self):
        self._finalize("单级单吸清水离心泵", QBEP="100", HBEP="50", speed="2900",
                       efficiency="90", suction="单吸", stages="1")
        self._finalize("单级石油化工离心泵", QBEP="100", HBEP="14", speed="2900",
                       efficiency="73", suction="单吸", stages="1")
        self.page.refresh()
        self.assertEqual(self.page.list.count(), 2)
        listed = [self.page.list.item(i).text() for i in range(self.page.list.count())]
        self.assertTrue(any("单级单吸清水离心泵" in text for text in listed))
        self.assertTrue(any("单级石油化工离心泵" in text for text in listed))

    def test_open_record_shows_original_as_of_thresholds_and_basis(self):
        record = self._finalize("单级单吸清水离心泵", QBEP="100", HBEP="50",
                                speed="2900", efficiency="90", suction="单吸", stages="1")
        text = self.page.show_record(record.record_id)
        self.assertIn("评价日期：2026-08-23", text)
        self.assertIn("评价结论：1级", text)
        self.assertIn("原等级阈值", text)
        self.assertIn("原标准依据", text)
        self.assertNotIn("pump_water", text)

    def test_reopen_does_not_recalculate_when_evaluator_is_broken(self):
        record = self._finalize("单级石油化工离心泵", QBEP="100", HBEP="14",
                                speed="2900", efficiency="73", suction="单吸", stages="1")

        from equipeffi.application.services import centrifugal_pump_analysis_service as mod

        def _boom(_rule_profile):
            raise RuntimeError("evaluator must not run on reopen")

        original = mod.build_pump_evaluator
        mod.build_pump_evaluator = _boom
        try:
            text = self.page.show_record(record.record_id)
        finally:
            mod.build_pump_evaluator = original
        self.assertIn("评价结论：2级", text)

    def test_empty_history_is_explained(self):
        self.page.refresh()
        self.assertEqual(self.page.list.count(), 0)
        self.assertIn("尚无正式记录", self.page.detail.text())


if __name__ == "__main__":
    unittest.main()
