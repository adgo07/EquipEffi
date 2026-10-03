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

    def test_no_category_is_preselected(self):
        """软件不得替用户猜泵型：初始必须无选中类别。"""

        self.assertIsNone(self.page.current_category())
        self.assertEqual(self.page.category.currentIndex(), 0)
        self.assertIn("请选择", self.page.category.itemText(0))
        self.assertEqual(self.page.stages.text(), "")
        self.assertIsNone(self.page.evaluate())

    def test_all_eight_formal_categories_are_present_in_one_selector(self):
        offered = [self.page.category.itemData(i)
                   for i in range(self.page.category.count())
                   if self.page.category.itemData(i)]
        for name in formal_category_names():
            with self.subTest(category=name):
                self.assertIn(name, offered)
        self.assertIn("其他类别", offered)
        self.assertIn("不确定类别", offered)

    def test_ordinary_result_area_hides_internal_rule_ids(self):
        """普通结果区不得出现内部 rule / data id；审计信息归技术详情。"""

        self.page.category.setCurrentIndex(self.page.category.findData("单级单吸清水离心泵"))
        self.page.as_of.setText(AS_OF)
        self.page.point_inputs["QBEP"].setText("100")
        self.page.point_inputs["HBEP"].setText("50")
        self.page.point_inputs["speed"].setText("2900")
        self.page.point_inputs["efficiency"].setText("90")
        self.page.suction.setCurrentIndex(self.page.suction.findData("单吸"))
        self.page.evaluate()

        ordinary = "\n".join([self.page.conclusion.text(), self.page.summary.text(),
                              self.page.basis.text()])
        self.assertNotIn("GB19762-T3-01", ordinary)
        self.assertNotIn("pump_water", ordinary)
        self.assertIn("等级阈值", ordinary)
        # 审计能力保留
        self.assertIn("GB19762-T3-01", self.page.technical.text())
        self.assertIn("命中规则", self.page.technical.text())

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

    def test_other_category_is_not_applicable_and_can_be_saved(self):
        """其他类别是类别级正式结论：状态在白名单内，允许保存（无 ruleset provenance）。"""

        self.page.category.setCurrentIndex(self.page.category.findData("其他类别"))
        result = self.page.evaluate()
        self.assertEqual(result.ui_conclusion, "不适用")
        self.assertEqual(result.evaluation_status, "OUT_OF_STANDARD_SCOPE")
        self.assertFalse(result.provenance["ruleset_executed"])
        self.assertTrue(self.page.finalize_button.isEnabled())

    def test_invalid_evaluation_date_is_reported_without_crashing(self):
        self.page.category.setCurrentIndex(self.page.category.findData("单级单吸清水离心泵"))
        self.page.as_of.setText("not-a-date")
        self.assertIsNone(self.page.evaluate())
        self.assertIn("YYYY-MM-DD", self.page.summary.text())

    def test_missing_category_is_reported_before_any_calculation(self):
        self.page.as_of.setText(AS_OF)
        self.assertIsNone(self.page.evaluate())
        self.assertIn("请先选择产品类别", self.page.summary.text())
        self.assertFalse(self.page.finalize_button.isEnabled())

    def test_new_analysis_defaults_to_local_current_date(self):
        """新建分析默认使用本机当前日期，且允许用户修改。"""

        self.assertEqual(self.page.as_of.text(), date.today().isoformat())
        self.assertTrue(self.page.as_of.isEnabled())

    def test_user_edited_date_is_used_instead_of_the_default(self):
        self.page.category.setCurrentIndex(self.page.category.findData("单级单吸清水离心泵"))
        self.page.as_of.setText(AS_OF)
        request = self.page._collect_request()
        self.assertIsNotNone(request)
        self.assertEqual(request.as_of, date.fromisoformat(AS_OF))


class AnalysisSaveFlowTests(unittest.TestCase):
    """Qt 保存按钮必须走真实 Finalize（不是占位）。"""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db = Path(self.tmp.name) / "records.sqlite"
        migrate_records_database(db, app_version="test")
        self.service = _service(SqliteWorkspaceRepository(db), SqliteRecordRepository(db))
        self.page = AnalysisPage(self.service, workspace_id="W-qt")

    def tearDown(self):
        self.tmp.cleanup()

    def _fill_water(self, efficiency: str = "90"):
        self.page.category.setCurrentIndex(self.page.category.findData("单级单吸清水离心泵"))
        self.page.as_of.setText(AS_OF)
        self.page.point_inputs["QBEP"].setText("100")
        self.page.point_inputs["HBEP"].setText("50")
        self.page.point_inputs["speed"].setText("2900")
        self.page.point_inputs["efficiency"].setText(efficiency)
        self.page.suction.setCurrentIndex(self.page.suction.findData("单吸"))

    def test_save_button_creates_a_real_formal_record(self):
        self._fill_water()
        self.page.evaluate()
        status = self.page.finalize()
        self.assertEqual(status, "SAVED")
        self.assertIsNotNone(self.page.last_saved_record_id)

        record = self.service.open_record(self.page.last_saved_record_id)
        self.assertEqual(record.ui_conclusion, "1级")
        self.assertEqual(record.product_category, "单级单吸清水离心泵")
        self.assertEqual(record.as_of, AS_OF)
        self.assertEqual(record.input_snapshot["efficiency"], "90")
        self.assertTrue(record.input_snapshot["request_fingerprint"])

    def test_saved_record_appears_in_history(self):
        self._fill_water()
        self.page.evaluate()
        self.page.finalize()
        records = self.service.list_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].record_id, self.page.last_saved_record_id)

    def test_save_without_analysis_is_refused(self):
        self._fill_water()
        self.assertEqual(self.page.finalize(), "NO_RESULT")
        self.assertEqual(self.service.list_records(), [])

    def test_save_refused_when_input_changed_after_analysis(self):
        """改了输入但未重新分析时，保存必须被拒绝，不能把旧结果当新输入保存。"""

        self._fill_water(efficiency="90")
        self.page.evaluate()
        self.page.point_inputs["efficiency"].setText("70")  # 未重新分析
        self.assertEqual(self.page.finalize(), "STALE_RESULT")
        self.assertEqual(self.service.list_records(), [])
        self.assertIn("重新分析", self.page.summary.text())

    def test_uncertain_category_cannot_be_saved(self):
        self.page.category.setCurrentIndex(self.page.category.findData("不确定类别"))
        self.page.evaluate()
        self.assertEqual(self.page.finalize(), "NOT_FINALIZABLE")
        self.assertEqual(self.service.list_records(), [])

    def test_workspace_round_trip_through_the_page(self):
        """保存草稿 → 新页面 load_workspace → 全部输入恢复。"""

        self._fill_water(efficiency="82.5")
        self.page.project_name.setText("页面往返项目")
        self.page.equipment_no.setText("P-QT-9")
        self.page.evaluate()
        self.assertEqual(self.page.finalize(), "SAVED")

        fresh = AnalysisPage(self.service, workspace_id="W-qt")
        self.assertTrue(fresh.load_workspace("W-qt"))
        self.assertEqual(fresh.current_category(), "单级单吸清水离心泵")
        self.assertEqual(fresh.as_of.text(), AS_OF)
        self.assertEqual(fresh.point_inputs["QBEP"].text(), "100")
        self.assertEqual(fresh.point_inputs["HBEP"].text(), "50")
        self.assertEqual(fresh.point_inputs["efficiency"].text(), "82.5")
        self.assertEqual(fresh.suction.currentData(), "单吸")
        self.assertEqual(fresh.project_name.text(), "页面往返项目")
        self.assertEqual(fresh.equipment_no.text(), "P-QT-9")

    def test_load_missing_workspace_returns_false(self):
        self.assertFalse(self.page.load_workspace("does-not-exist"))


class DraftUserFlowTests(unittest.TestCase):
    """草稿必须在**用户流程**里独立保存、列出、跨重启恢复。"""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.tmp.name) / "records.sqlite"
        migrate_records_database(self.db, app_version="test")
        self.page = self._new_page()

    def tearDown(self):
        self.tmp.cleanup()

    def _new_page(self) -> AnalysisPage:
        """模拟一次程序启动：全新 Service + 全新页面（不传任何 session id）。"""

        return AnalysisPage(_service(SqliteWorkspaceRepository(self.db),
                                    SqliteRecordRepository(self.db)))

    def _fill(self, category: str = "单级石油化工离心泵", **overrides) -> None:
        values = {"QBEP": "123.5", "HBEP": "14.25", "speed": "2950",
                  "efficiency": "73.5", "suction": "单吸", "stages": "1"}
        values.update(overrides)
        self.page.category.setCurrentIndex(self.page.category.findData(category))
        if self.page.stages.isEnabled():
            self.page.stages.setText(values["stages"])
        self.page.as_of.setText(AS_OF)
        for key in ("QBEP", "HBEP", "speed", "efficiency"):
            self.page.point_inputs[key].setText(values[key])
        self.page.suction.setCurrentIndex(self.page.suction.findData(values["suction"]))

    def test_draft_can_be_saved_without_analysing_or_finalizing(self):
        self.page.draft_name.setText("草稿A")
        self._fill()
        self.assertEqual(self.page.save_draft(), "SAVED")
        # 草稿不产生正式记录
        self.assertEqual(_service(SqliteWorkspaceRepository(self.db),
                                  SqliteRecordRepository(self.db)).list_records(), [])

    def test_draft_requires_a_name(self):
        self._fill()
        self.assertEqual(self.page.save_draft(), "NO_NAME")
        self.assertEqual(self.page.draft_list.count(), 0)

    def test_draft_is_listed_and_fully_restored_after_restart(self):
        """核心用户链：保存草稿 → 关程序 → 重开 → 列表可见 → 载入恢复全部输入。"""

        self.page.draft_name.setText("3号循环水泵-2026Q4")
        self.page.project_name.setText("示例项目")
        self.page.equipment_no.setText("P-777")
        self._fill()
        self.assertEqual(self.page.save_draft(), "SAVED")

        restarted = self._new_page()          # 等价于重新启动程序
        self.assertEqual(restarted.draft_list.count(), 1)
        self.assertIn("3号循环水泵-2026Q4", restarted.draft_list.itemText(0))
        self.assertTrue(restarted.load_selected_draft())

        self.assertEqual(restarted.current_category(), "单级石油化工离心泵")
        self.assertEqual(restarted.as_of.text(), AS_OF)
        self.assertEqual(restarted.point_inputs["QBEP"].text(), "123.5")
        self.assertEqual(restarted.point_inputs["HBEP"].text(), "14.25")
        self.assertEqual(restarted.point_inputs["speed"].text(), "2950")
        self.assertEqual(restarted.point_inputs["efficiency"].text(), "73.5")
        self.assertEqual(restarted.suction.currentData(), "单吸")
        self.assertEqual(restarted.stages.text(), "1")
        self.assertEqual(restarted.project_name.text(), "示例项目")
        self.assertEqual(restarted.equipment_no.text(), "P-777")
        self.assertEqual(restarted.draft_name.text(), "3号循环水泵-2026Q4")

    def test_restored_draft_can_be_evaluated_and_finalized(self):
        self.page.draft_name.setText("草稿B")
        self._fill()
        self.page.save_draft()

        restarted = self._new_page()
        restarted.load_selected_draft()
        result = restarted.evaluate()
        self.assertEqual(result.evaluation_status, "SUCCESS")
        self.assertEqual(restarted.finalize(), "SAVED")
        record = restarted.service.open_record(restarted.last_saved_record_id)
        self.assertEqual(record.input_snapshot["QBEP"], "123.5")
        self.assertEqual(record.input_snapshot["equipment_no"], None)

    def test_new_draft_clears_the_form(self):
        self.page.draft_name.setText("草稿C")
        self._fill()
        self.page.save_draft()
        self.page.new_draft()
        self.assertIsNone(self.page.current_category())
        self.assertEqual(self.page.draft_name.text(), "")
        self.assertEqual(self.page.point_inputs["QBEP"].text(), "")
        self.assertEqual(self.page.project_name.text(), "")
        # 已有草稿不受影响
        self.assertEqual(self.page.draft_list.count(), 1)

    def test_delete_draft_keeps_formal_records(self):
        self.page.draft_name.setText("草稿D")
        self._fill()
        self.page.save_draft()
        self.page.evaluate()
        self.assertEqual(self.page.finalize(), "SAVED")
        record_id = self.page.last_saved_record_id

        self.page.refresh_drafts()
        self.page.draft_list.setCurrentIndex(0)
        self.assertEqual(self.page.delete_selected_draft(), "DELETED")
        self.assertEqual(self.page.draft_list.count(), 0)
        # 正式记录不可被草稿删除影响
        self.assertIsNotNone(self.page.service.open_record(record_id))

    def test_multiple_drafts_are_all_listed_after_restart(self):
        for name in ("草稿-1", "草稿-2"):
            self.page.draft_name.setText(name)
            self._fill()
            self.page.save_draft()
        restarted = self._new_page()
        self.assertEqual(restarted.draft_list.count(), 2)


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
        self.assertIn("规定点流量 Q_BEP（m³/h）：100", text)
        self.assertNotIn("QBEP：", text)          # 内部字段名不得原样出现在普通详情
        self.assertNotIn("pump_water", text)

    def test_ordinary_record_detail_hides_internal_rule_ids(self):
        """普通记录详情不得出现内部 rule / data id；它们归技术详情。"""

        record = self._finalize("单级单吸清水离心泵", QBEP="100", HBEP="50",
                                speed="2900", efficiency="90", suction="单吸", stages="1")
        text = self.page.show_record(record.record_id)
        self.assertNotIn("GB19762-T3-01", text)
        self.assertNotIn("pump_water", text)
        self.assertNotIn("EQUIPEFFI_PUMP_DECIMAL50_V2", text)
        # 审计能力保留在技术详情
        self.assertIn("GB19762-T3-01", self.page.technical.text())
        self.assertIn("命中规则", self.page.technical.text())
        self.assertIn("数值配置", self.page.technical.text())

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
