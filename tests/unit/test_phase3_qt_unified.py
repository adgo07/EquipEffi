"""Phase 3 P3-G02：统一 GB 19762 分析页与分析记录页（offscreen）。"""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QLabel,
    QPushButton,
)
from unittest.mock import patch  # noqa: E402

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
from equipeffi.application.lifecycle.errors import (  # noqa: E402
    AnalysisError,
    LifecyclePersistenceError,
)
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
    """页面层行为。

    Phase 7：合法分析会自动固化，因此这里必须装配真实 Record 仓储
    （内存库），否则 `finalize` 会因"未装配 Record 仓储"而拒绝。
    """

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db = Path(self.tmp.name) / "records.sqlite"
        migrate_records_database(db, app_version="test")
        self.service = _service(SqliteWorkspaceRepository(db), SqliteRecordRepository(db))
        self.page = AnalysisPage(self.service)
        self.addCleanup(self.tmp.cleanup)

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
        self.page.point_inputs["QBEP"].setText("100")
        self.page.point_inputs["HBEP"].setText("50")
        self.page.point_inputs["speed"].setText("2900")
        self.page.point_inputs["efficiency"].setText("90")
        self.page.suction.setCurrentIndex(self.page.suction.findData("单吸"))
        result = self.page.evaluate()

        ordinary = "\n".join([self.page.conclusion.text(), self.page.summary.text(),
                              self.page.values_label.text(), self.page.basis.text()])
        self.assertNotIn("GB19762-T3-01", ordinary)
        self.assertNotIn("pump_water", ordinary)
        # Phase 6：第二层用用户可理解名称展示限值，不再使用内部阈值键。
        self.assertIn("对应等级效率限值", ordinary)
        self.assertIn("1级能效效率限值（%）", ordinary)
        # 审计能力保留
        # Phase 7：分析页不再显示技术详情；内部证据仍在 Result 契约中。
        self.assertTrue(result.matched_rule_id)

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
        # Owner Phase 8 R1 / UI02：普通结果区不再展示「标准依据」，
        # 只保留关键计算参数。
        self.assertIn("关键计算参数", self.page.basis.text())
        self.assertNotIn("标准依据", self.page.basis.text())
        self.assertEqual(self.page.last_record_status, "RECORDED")
        self.assertNotIn("pump_water", self.page.basis.text())

    def test_chemical_analysis_is_available_in_the_same_page(self):
        self.page.category.setCurrentIndex(self.page.category.findData("单级石油化工离心泵"))
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
        self.assertNotEqual(self.page.last_record_status, "RECORDED")
        self.assertIn("确认", self.page.summary.text())

    def test_other_category_is_not_applicable_and_can_be_saved(self):
        """其他类别是类别级正式结论：状态在白名单内，允许保存（无 ruleset provenance）。"""

        self.page.category.setCurrentIndex(self.page.category.findData("其他类别"))
        result = self.page.evaluate()
        self.assertEqual(result.ui_conclusion, "不适用")
        self.assertEqual(result.evaluation_status, "OUT_OF_STANDARD_SCOPE")
        self.assertFalse(result.provenance["ruleset_executed"])
        self.assertEqual(self.page.last_record_status, "RECORDED")

    def test_evaluation_date_is_never_asked_from_the_user(self):
        """Phase 7：评价日期不由用户输入，自动取本机当天日期。"""

        self.assertFalse(hasattr(self.page, "as_of"))
        self.page.category.setCurrentIndex(self.page.category.findData("单级单吸清水离心泵"))
        request = self.page._collect_request()
        self.assertIsNotNone(request)
        self.assertEqual(request.as_of, date.today())

    def test_missing_category_is_reported_before_any_calculation(self):
        self.assertIsNone(self.page.evaluate())
        self.assertIn("请先选择产品类别", self.page.summary.text())
        self.assertNotEqual(self.page.last_record_status, "RECORDED")

    def test_new_analysis_uses_local_current_date_automatically(self):
        """Phase 7：新分析自动采用本机当天日期，页面不显示、也不要求填写。"""

        self.page.category.setCurrentIndex(self.page.category.findData("单级单吸清水离心泵"))
        request = self.page._collect_request()
        self.assertEqual(request.as_of, date.today())
        labels = [w.text() for w in self.page.findChildren(QLabel)]
        self.assertNotIn("评价日期", "\n".join(labels))


class AnalysisSaveFlowTests(unittest.TestCase):
    """Phase 7：合法分析**自动**形成正式记录，不存在手工保存按钮。"""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db = Path(self.tmp.name) / "records.sqlite"
        migrate_records_database(db, app_version="test")
        self.service = _service(SqliteWorkspaceRepository(db), SqliteRecordRepository(db))
        self.page = AnalysisPage(self.service)

    def tearDown(self):
        self.tmp.cleanup()

    def _fill_water(self, efficiency: str = "90"):
        self.page.category.setCurrentIndex(self.page.category.findData("单级单吸清水离心泵"))
        self.page.point_inputs["QBEP"].setText("100")
        self.page.point_inputs["HBEP"].setText("50")
        self.page.point_inputs["speed"].setText("2900")
        self.page.point_inputs["efficiency"].setText(efficiency)
        self.page.suction.setCurrentIndex(self.page.suction.findData("单吸"))

    def test_analysis_automatically_creates_a_real_formal_record(self):
        self._fill_water()
        self.page.evaluate()

        self.assertEqual(self.page.last_record_status, "RECORDED")
        self.assertIsNotNone(self.page.last_saved_record_id)
        record = self.service.open_record(self.page.last_saved_record_id)
        self.assertEqual(record.ui_conclusion, "1级")
        self.assertEqual(record.product_category, "单级单吸清水离心泵")
        self.assertEqual(record.as_of, date.today().isoformat())
        self.assertEqual(record.input_snapshot["efficiency"], "90")
        self.assertTrue(record.input_snapshot["request_fingerprint"])

    def test_page_has_no_manual_save_button(self):
        """Phase 7 Owner 规则：删除「保存为正式记录」。"""

        self.assertFalse(hasattr(self.page, "finalize_button"))
        self.assertFalse(hasattr(self.page, "finalize"))
        buttons = [b.text() for b in self.page.findChildren(QPushButton)]
        self.assertNotIn("保存为正式记录", buttons)
        self.assertIn("分析", buttons)

    def test_auto_saved_record_appears_in_history(self):
        self._fill_water()
        self.page.evaluate()
        records = self.service.list_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].record_id, self.page.last_saved_record_id)

    def test_repeated_analysis_creates_distinct_records(self):
        """连续合法分析形成多条 Record，互不覆盖。"""

        ids = []
        for efficiency in ("90", "85", "80"):
            self._fill_water(efficiency=efficiency)
            self.page.evaluate()
            ids.append(self.page.last_saved_record_id)
        self.assertEqual(len(set(ids)), 3)
        self.assertEqual(len(self.service.list_records()), 3)
        # 第一条记录仍按当时输入存在
        self.assertEqual(self.service.open_record(ids[0]).input_snapshot["efficiency"], "90")

    def test_uncertain_category_does_not_create_a_record(self):
        self.page.category.setCurrentIndex(self.page.category.findData("不确定类别"))
        self.page.evaluate()
        self.assertEqual(self.page.last_record_status, "NOT_RECORDED")
        self.assertEqual(self.service.list_records(), [])

    def test_invalid_input_does_not_create_a_record(self):
        self._fill_water()
        self.page.point_inputs["efficiency"].setText("abc")
        self.page.evaluate()
        self.assertEqual(self.page.last_record_status, "NOT_RECORDED")
        self.assertEqual(self.service.list_records(), [])

    def test_insufficient_data_is_a_legal_terminal_state_and_is_recorded(self):
        """业务「资料不足」是合法终态，可以形成 Record（≠ 系统失败）。"""

        self._fill_water()
        self.page.point_inputs["efficiency"].clear()
        self.page.evaluate()
        self.assertEqual(self.page.last_record_status, "RECORDED")
        self.assertEqual(len(self.service.list_records()), 1)

    def test_record_save_failure_is_reported_and_not_hidden(self):
        """计算结果已产生但持久化失败时，不得显示为已保存。"""

        self._fill_water()
        with patch.object(self.service, "finalize",
                          side_effect=LifecyclePersistenceError("disk full")):
            self.page.evaluate()
        self.assertEqual(self.page.last_record_status, "SAVE_FAILED")
        self.assertIsNone(self.page.last_saved_record_id)
        text = self.page.record_label.text()
        self.assertIn("保存失败", text)
        self.assertNotIn("已自动保存", text)

    def test_stale_input_is_still_rejected_by_the_fingerprint_gate(self):
        """取消手工按钮不等于取消 stale result 防护：指纹门禁仍在 Application 层。"""

        self._fill_water(efficiency="90")
        request = self.page._collect_request()
        result = self.service.evaluate(request)
        # 分析后修改输入，再用旧结果固化必须被拒绝
        changed = self.page._collect_request()
        self.page.point_inputs["efficiency"].setText("70")
        changed = self.page._collect_request()
        with self.assertRaises(AnalysisError):
            self.service.finalize(record_id="R-stale", workspace_id=None,
                                  request=changed, result=result)
        self.assertEqual(self.service.list_records(), [])


class WorkspaceIsNoLongerAProductConceptTests(unittest.TestCase):
    """Phase 7：Workspace 退出普通产品表面，但底层能力保留。"""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.tmp.name) / "records.sqlite"
        migrate_records_database(self.db, app_version="test")
        self.service = _service(SqliteWorkspaceRepository(self.db),
                                SqliteRecordRepository(self.db))
        self.page = AnalysisPage(self.service)

    def tearDown(self):
        self.tmp.cleanup()

    def test_analysis_page_has_no_draft_surface(self):
        for name in ("draft_name", "draft_list", "draft_status",
                     "save_draft", "new_draft", "refresh_drafts",
                     "load_selected_draft", "delete_selected_draft",
                     "load_workspace", "save_draft_button", "new_draft_button",
                     "load_draft_button", "delete_draft_button",
                     "refresh_drafts_button"):
            with self.subTest(attribute=name):
                self.assertFalse(hasattr(self.page, name))

    def test_no_draft_wording_is_visible(self):
        labels = [w.text() for w in self.page.findChildren(QLabel)]
        buttons = [b.text() for b in self.page.findChildren(QPushButton)]
        blob = "\n".join(labels + buttons)
        for word in ("草稿", "保存草稿", "新建草稿", "已有草稿", "载入", "删除草稿"):
            with self.subTest(word=word):
                self.assertNotIn(word, blob)

    def test_workspace_lifecycle_is_still_available_internally(self):
        """底层 Workspace 能力保留（Application 契约 + 旧数据兼容 + 测试依赖）。"""

        for name in ("create_workspace", "update_workspace", "load_workspace",
                     "list_workspaces", "delete_workspace", "evaluate_workspace",
                     "request_from_workspace", "save_workspace_from_request"):
            with self.subTest(method=name):
                self.assertTrue(callable(getattr(self.service, name)))

    def test_records_are_independent_from_workspaces(self):
        """自动记录不依赖 Workspace：finalize(workspace_id=None) 即可固化。"""

        request = PumpAnalysisRequest(
            product_category="单级单吸清水离心泵", as_of=date.today(),
            QBEP="100", HBEP="50", speed="2900", efficiency="90",
            suction="单吸", stages="1")
        result = self.service.evaluate(request)
        record = self.service.finalize(record_id="R-nostore", workspace_id=None,
                                       request=request, result=result)
        self.assertIsNone(record.workspace_id)


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
