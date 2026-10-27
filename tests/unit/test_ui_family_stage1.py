"""批准的第一阶段 UI 行为；正式服务配隔离测试库。"""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt, QCoreApplication, QEvent
from PySide6.QtGui import QInputMethodEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QGroupBox, QScrollArea
from equipeffi.composition import (create_settings_runtime, create_pump_analysis_service,
    create_transformer_analysis_service, create_batch_evaluation_service)
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.infrastructure.runtime_logging import close_logging
from equipeffi.presentation.qt.shell import MainWindow
from equipeffi.presentation.qt.navigation import PAGES


class UiFamilyStage1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.paths = AppDataPaths(Path(self.temp.name))
        self.settings, self.logger = create_settings_runtime(paths=self.paths)
        self.service = create_pump_analysis_service(paths=self.paths)
        self.window = MainWindow(self.settings, self.service,
            transformer=create_transformer_analysis_service(paths=self.paths),
            batch=create_batch_evaluation_service(paths=self.paths))
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        close_logging(self.logger)
        self.temp.cleanup()

    def test_home_business_and_detail_keep_expected_shell(self):
        self.assertTrue(self.window.sidebar.isHidden())
        home = self.window.home_page
        self.assertEqual(len(home.task_buttons), 4)
        home.task_buttons[0].click()
        self.assertFalse(self.window.sidebar.isHidden())
        page = self.window.standards_page
        for column in (0, 1):
            page.stack.setCurrentIndex(0)
            cell = page.table.visualItemRect(page.table.item(0, column))
            QTest.mouseClick(page.table.viewport(), Qt.MouseButton.LeftButton, pos=cell.center())
            self.assertEqual(page.stack.currentIndex(), 1)
            self.assertEqual(page.standard_code, "GB 19762-2025")
            self.assertFalse(self.window.sidebar.isHidden())
        self.window.open_home()
        self.assertTrue(self.window.sidebar.isHidden())
        self.window.open_settings()
        self.assertFalse(self.window.sidebar.isHidden())
        self.assertTrue(self.window.navigation.item(5).isHidden())

    def test_search_ime_filter_keyboard_and_back_preserve_context(self):
        self.window.open_standards()
        page = self.window.standards_page
        self.assertEqual([page.table.horizontalHeaderItem(i).text() for i in range(5)],
            ["标准编号", "标准名称", "标准状态", "实施日期", "软件支持"])
        for keyword in ("19762", "能效限定值", "清水"):
            page.search.setText(keyword)
            self.assertGreater(page.table.rowCount(), 0)
        page.search.clear()
        page.search.setFocus()
        self.app.processEvents()
        preedit = QInputMethodEvent("变压", [])
        QApplication.sendEvent(page.search, preedit)
        self.assertTrue(page.search.hasFocus())
        self.assertEqual(page.search.text(), "")
        commit = QInputMethodEvent()
        commit.setCommitString("变压器")
        QApplication.sendEvent(page.search, commit)
        self.assertEqual(page.table.rowCount(), 1)
        self.assertTrue(page.search.hasFocus())
        self.assertEqual(page.search.cursorPosition(), 3)
        page.table.setCurrentCell(0, 0)
        QTest.keyClick(page.table, Qt.Key.Key_Return)
        self.assertEqual(page.stack.currentIndex(), 1)
        self.assertEqual([box.title() for box in page.stack.currentWidget().findChildren(QGroupBox)],
            ["基本信息", "适用范围", "标准要求"])
        page.back_button.click()
        self.assertEqual(page.search.text(), "变压器")
        self.assertEqual(page.table.currentRow(), 0)
        page.status_filter.setCurrentIndex(page.status_filter.findData("NOT_YET_EFFECTIVE"))
        self.assertEqual(page.table.rowCount(), 0)
        self.assertIn("没有匹配", page.list_status.text())

    def test_unknown_and_disabled_motor_do_not_reuse_last_device(self):
        self.window.open_analysis(standard_code="GB 20052-2024")
        selector = self.window.device_analysis_page.device_selector
        self.assertEqual(selector.currentData(), "transformer")
        for code in ("UNKNOWN", "GB 18613-2020"):
            self.window.open_analysis(standard_code=code)
            self.assertEqual(self.window.pages.currentIndex(), PAGES.index("标准库"))
            self.assertEqual(selector.currentData(), "transformer")
            self.assertIn("尚未开放", self.window.standards_page.list_status.text())
        self.assertFalse(selector.model().item(2).isEnabled())

    def test_changed_input_marks_result_stale_without_changing_history(self):
        self.window.open_analysis(standard_code="GB 19762-2025")
        page = self.window.analysis_page
        page.project_name.setText("测试项目")
        page.category.setCurrentIndex(page.category.findData("单级单吸清水离心泵"))
        for field, value in dict(QBEP="100", HBEP="50", speed="2900", efficiency="90").items():
            page.point_inputs[field].setText(value)
        self.assertIsNotNone(page.evaluate())
        record_id = page.last_saved_record_id
        snapshot = self.service.open_record(record_id)
        self.assertEqual(len(self.service.list_records()), 1)
        self.assertFalse(page.view_record_button.isHidden())
        page.point_inputs["efficiency"].setText("80")
        self.assertFalse(page.stale_label.isHidden())
        self.assertTrue(page.view_record_button.isHidden())
        self.assertEqual(snapshot, self.service.open_record(record_id))
        page.evaluate()
        self.assertTrue(page.stale_label.isHidden())
        self.assertEqual(len(self.service.list_records()), 2)
        self.window.open_home()
        self.assertEqual(self.window.home_page.records.rowCount(), 2)
        self.assertIn("测试项目", self.window.home_page.records.item(0, 0).text())

    def test_category_search_is_not_a_new_business_value(self):
        page = self.window.analysis_page
        page.category.setCurrentIndex(page.category.findData("单级单吸清水离心泵"))
        page.category.setEditText("不存在的泵型")
        self.assertIsNone(page.current_category())
        self.assertIsNone(page.evaluate())
        self.assertEqual(len(self.service.list_records()), 0)

    def test_recent_read_failure_is_distinct_from_empty(self):
        home = self.window.home_page
        self.assertIn("尚无分析记录", home.record_status.text())
        with patch.object(self.service, "list_records", side_effect=OSError("unavailable")), self.assertLogs("equipeffi.qt.home", level="ERROR") as logs:
            home.refresh()
        self.assertIn("unavailable", "\n".join(logs.output))
        self.assertEqual(home.record_status.text(), "暂时无法读取记录")
        self.assertFalse(home.retry_button.isHidden())
        home.retry_button.click()
        self.assertTrue(home.retry_button.isHidden())
        self.assertIn("尚无分析记录", home.record_status.text())

    def test_original_unavailable_does_not_claim_opened(self):
        page = self.window.standards_page
        page.open_detail(0)
        with patch("equipeffi.presentation.qt.pages.standards.QDesktopServices.openUrl") as opener:
            page.source_button.click()
        opener.assert_not_called()
        self.assertIn("没有可打开", page.feedback.text())

    def test_small_window_retains_navigation_and_scrollable_form(self):
        self.window.resize(560, 420)
        self.window.open_analysis(standard_code="GB 19762-2025")
        self.app.processEvents()
        self.assertEqual(self.window.width(), 560)
        self.assertEqual(self.window.sidebar.width(), 144)
        self.assertTrue(self.window.navigation.isVisible())
        scroll = self.window.analysis_page.findChild(QScrollArea)
        self.assertGreater(scroll.verticalScrollBar().maximum(), 0)
        scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
        self.app.processEvents()
        self.assertTrue(self.window.analysis_page.result_group.isVisible())

    def test_new_detail_starts_at_top_and_back_preserves_list_context(self):
        self.window.resize(560, 420)
        self.window.open_standards()
        page = self.window.standards_page
        page.search.setText("能效")
        page.status_filter.setCurrentIndex(page.status_filter.findData("EFFECTIVE"))
        self.app.processEvents()
        page.table.selectRow(0)
        page.table.horizontalScrollBar().setValue(80)
        list_scroll = page.table.horizontalScrollBar().value()
        page.open_detail(0)
        self.app.processEvents()
        scroll = page.stack.currentWidget().findChild(QScrollArea).verticalScrollBar()
        self.assertGreater(scroll.maximum(), 0)
        scroll.setValue(scroll.maximum())
        page.back_button.click()
        self.app.processEvents()
        self.assertEqual(page.search.text(), "能效")
        self.assertEqual(page.status_filter.currentData(), "EFFECTIVE")
        self.assertEqual(page.table.currentRow(), 0)
        self.assertEqual(page.table.horizontalScrollBar().value(), list_scroll)
        page.open_detail(1)
        self.app.processEvents()
        self.assertEqual(scroll.value(), 0)
        self.assertIn("GB 20052-2024", page.section_labels[0].text())

    def test_unknown_standard_after_detail_returns_visible_rejection(self):
        page = self.window.standards_page
        for code in ("UNKNOWN", "GB 18613-2020"):
            self.window.open_standards()
            page.open_detail(1)
            page.start_button.click()
            self.window.open_analysis(standard_code=code)
            self.app.processEvents()
            self.assertEqual(self.window.pages.currentWidget(), page)
            self.assertEqual(page.stack.currentIndex(), 0)
            self.assertTrue(page.list_status.isVisible())
            self.assertIn("尚未开放", page.list_status.text())
            self.assertIsNone(page.standard_code)
            self.assertEqual(self.window.device_analysis_page.device_selector.currentData(), "transformer")

    def test_catalog_read_failure_is_atomic_and_retry_restores_current_filter(self):
        self.window.open_standards()
        page = self.window.standards_page
        page.search.setText("变压器")
        page.open_detail(0)
        # 同时覆盖首项失败和第二项失败；后者不能留下已读到的泵目录。
        for service in page.services:
            with self.subTest(service=type(service).__name__):
                with patch.object(service, "standard_overview", side_effect=OSError("read unavailable")):
                    page.refresh()
                    self.app.processEvents()
                    self.assertEqual(page.table.rowCount(), 0)
                    self.assertEqual(page._catalog, [])
                    self.assertEqual(page.stack.currentIndex(), 0)
                    self.assertIsNone(page.standard_code)
                    self.assertTrue(page.list_status.isVisible())
                    self.assertIn("暂时无法读取标准", page.list_status.text())
                    self.assertTrue(page.retry_button.isVisible())
                    page.search.setText("19762")
                    self.assertIn("暂时无法读取标准", page.list_status.text())
                page.search.setText("变压器")
                page.retry_button.click()
                self.assertEqual(page.table.rowCount(), 1)
                self.assertEqual(page.table.item(0, 0).text(), "GB 20052-2024")
                self.assertTrue(page.retry_button.isHidden())
                self.assertEqual(page.search.text(), "变压器")

    def test_standard_columns_fill_on_first_show_and_viewport_resize(self):
        self.window.resize(1440, 1000)
        self.app.processEvents()
        self.window.open_standards()
        QTest.qWait(10)
        page = self.window.standards_page
        table = page.table
        self.assertEqual(sum(table.columnWidth(i) for i in range(5)), table.viewport().width())
        self.assertGreater(table.columnWidth(1), 300)
        table.setFixedWidth(table.width() - 90)
        QTest.qWait(10)
        self.assertEqual(sum(table.columnWidth(i) for i in range(5)), table.viewport().width())
        table.setMinimumWidth(0)
        table.setMaximumWidth(16777215)
        self.window.resize(560, 420)
        QTest.qWait(10)
        self.assertGreaterEqual(table.columnWidth(1), 300)
        self.assertGreater(sum(table.columnWidth(i) for i in range(5)), table.viewport().width())
        self.assertGreater(table.horizontalScrollBar().maximum(), 0)
