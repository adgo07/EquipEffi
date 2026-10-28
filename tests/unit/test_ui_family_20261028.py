"""本轮 UI 的可观察行为；真实服务与隔离数据库，离屏验证。"""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from PySide6.QtCore import QSize, QRect, Qt
from PySide6.QtGui import QIcon
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton, QLineEdit, QComboBox, QGroupBox
from tests.unit import test_ui_family_stage2 as fixtures
from equipeffi.presentation.qt.style import icon


class UiFamily20261028Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.UiFamilyStage2Tests.setUpClass.__func__(cls)
        # Offscreen Windows does not enumerate system CJK fonts. Use the same
        # available font as the representative captures, rather than box glyphs.
        import os
        from pathlib import Path
        from PySide6.QtGui import QFontDatabase
        font = Path(os.environ.get("WINDIR", "")) / "Fonts/msyh.ttc"
        if font.is_file():
            QFontDatabase.addApplicationFont(str(font))

    setUp = fixtures.UiFamilyStage2Tests.setUp
    tearDown = fixtures.UiFamilyStage2Tests.tearDown
    _pump_record = fixtures.UiFamilyStage2Tests._pump_record
    def test_settings_keeps_origin_context_and_safe_home_exit(self):
        self.window.open_home()
        self.window.open_settings()
        self.assertTrue(self.window.sidebar.isHidden())
        self.assertTrue(self.window.settings_home_button.isVisible())
        self.window.settings_home_button.click()
        self.assertEqual(self.window.pages.currentWidget(), self.window.home_page)
        self.window.open_records()
        self.window.settings_button.click()
        self.assertFalse(self.window.sidebar.isHidden())
        self.assertTrue(self.window.settings_home_button.isHidden())

    def test_controls_have_final_40_dip_bounds_without_focus_jump(self):
        self.window.open_analysis(standard_code="GB 19762-2025")
        page = self.window.analysis_page
        page.category.setCurrentIndex(page.category.findData("单级单吸清水离心泵"))
        self.window.resize(1280, 800)
        QTest.qWait(30)
        self.assertEqual(self.window.navigation.visualItemRect(self.window.navigation.item(1)).height(), 46)
        self.assertEqual(self.window.settings_button.height(), 46)
        self.assertEqual(self.window.settings_button.iconSize(), QSize(18,18))
        self.assertEqual(self.window.records_page.detail_tabs.tabBar().tabRect(0).height(), 36)
        for widget in (page.project_name, page.point_inputs["QBEP"], page.category, page.evaluate_button):
            with self.subTest(widget=type(widget).__name__):
                self.assertEqual(widget.height(), 40)
                before = widget.size()
                widget.setFocus()
                QTest.qWait(10)
                self.assertEqual(widget.size(), before)
        edit = page.point_inputs["QBEP"]
        value = "100." + "1234567890" * 10
        edit.setText(value)
        edit.setFocus()
        self.assertEqual(edit.text(), value)
        self.window.open_records()
        self.window.records_page.clear_filters()
        self.window.records_page.refresh()
        self.window.open_analysis()
        self.assertEqual(edit.text(), value)

    def test_window_is_constrained_to_available_screen_and_restored_position(self):
        screen = SimpleNamespace(availableGeometry=lambda: QRect(200, 100, 1100, 720))
        self.window.resize(1280, 800)
        self.window._geometry_restored = False
        with patch("equipeffi.presentation.qt.shell.QGuiApplication.screens", return_value=[screen]), patch("equipeffi.presentation.qt.shell.QGuiApplication.screenAt", return_value=screen):
            self.window._ensure_on_screen()
            self.assertTrue(screen.availableGeometry().contains(self.window.frameGeometry()))
            self.assertFalse(self.window.isMaximized())
            self.window.move(10000, 10000)
            self.window._ensure_on_screen()
            self.assertTrue(screen.availableGeometry().contains(self.window.frameGeometry()))
            position = self.window.pos()
            self.window._ensure_on_screen()
            self.assertEqual(self.window.pos(), position)

    def test_long_chinese_table_rows_grow_and_keep_actions(self):
        # Use persisted records and the real first-entry/load-more path. Editing
        # an already visible item emits itemChanged and missed the insertion bug.
        self.window.resize(1280, 800)
        self.window.open_analysis(standard_code="GB 19762-2025")
        page = self.window.analysis_page
        page.category.setCurrentIndex(page.category.findData("单级单吸清水离心泵"))
        for key, value in dict(QBEP="100", HBEP="50", speed="2900", efficiency="90").items():
            page.point_inputs[key].setText(value)
        name = "长中文行高验收：设备能效分析项目名称完整保留，不截断正文。" * 5
        for index in range(2):
            page.project_name.setText(f"{name}{index}")
            self.assertIsNotNone(page.evaluate())
        record_id = page.last_saved_record_id
        records = self.window.records_page
        table = records.list
        with patch("equipeffi.presentation.qt.pages.records.PAGE_SIZE", 1):
            self.window.open_records()
            self.assertGreater(table.rowHeight(0), 48, "插入后不得依赖再次编辑或缩放修正行高")
            QTest.qWait(50)
            self.assertEqual(table.rowCount(), 1)
            self.assertGreater(table.rowHeight(0), 48, "首次载入不能截断长中文")
            records.load_more_button.click()
            QTest.qWait(50)
            self.assertEqual(table.rowCount(), 2)
            self.assertTrue(all(table.rowHeight(row) > 48 for row in range(2)))
        self.window.resize(960, 800)
        QTest.qWait(50)
        narrow = table.rowHeight(0)
        self.window.resize(1900, 800)
        QTest.qWait(50)
        self.assertGreater(narrow, table.rowHeight(0), "按实际列宽重新计算行高")
        records.refresh()
        QTest.qWait(50)
        self.assertTrue(all(table.rowHeight(row) > 48 for row in range(2)))
        self.assertTrue(table.wordWrap())
        self.assertEqual(table.textElideMode(), Qt.TextElideMode.ElideNone)
        self.assertTrue(table.cellWidget(0, table.columnCount()-1).isEnabled())
        records.show_record(record_id)
        self.assertEqual(records.detail_tabs.count(), 2)
        self.assertIn(name, records.detail.text())

    def test_brand_original_ratio_dpr_and_svg_scale(self):
        brand = self.window.home_page.brand
        self.assertEqual(brand.width(), 180)
        self.assertEqual((brand._image.width(), brand._image.height()), (3060, 759))
        self.assertEqual(brand.pixmap().devicePixelRatioF(), brand.devicePixelRatioF())
        self.assertAlmostEqual(brand.pixmap().deviceIndependentSize().width(), 180, delta=1)
        for scale in (1.0, 1.5, 2.0):
            image = icon("book").pixmap(QSize(18,18), scale, QIcon.Mode.Normal)
            self.assertEqual(image.width(), round(18*scale))
            self.assertAlmostEqual(image.deviceIndependentSize().width(), 18, delta=1)

    def test_batch_no_file_and_busy_failure_restore_prerequisites(self):
        page = self.window.batch_page
        self.assertFalse(page.run_button.isEnabled())
        page.source_edit.setText("隔离测试.xlsx")
        self.assertTrue(page.run_button.isEnabled())
        page._set_busy(True)
        self.assertFalse(page.run_button.isEnabled())
        self.assertIn("正在", page.run_button.text())
        page._on_failed("OSError")
        self.assertTrue(page.run_button.isEnabled())
        self.assertEqual(page.run_button.text(), "批量评价")
        page.source_edit.clear()
        self.assertFalse(page.run_button.isEnabled())

    def test_actual_content_width_is_capped_at_1440(self):
        from equipeffi.presentation.qt.widgets.page_layout import page_gutter
        from PySide6.QtWidgets import QWidget, QVBoxLayout
        surface = QWidget()
        layout = QVBoxLayout(surface)
        helper = page_gutter(layout)
        for width in (1280, 2000):
            surface.resize(width, 800)
            helper.apply()
            margins = layout.contentsMargins()
            expected = 1440 if width == 2000 else width - 2*round(width*0.034)
            self.assertEqual(width - margins.left() - margins.right(), expected)
        surface.deleteLater()

    def test_primary_disabled_color_and_home_card_contrast(self):
        from PySide6.QtGui import QPalette
        from PySide6.QtWidgets import QLabel
        self.window.open_home()
        QTest.qWait(20)
        title = self.window.home_page.task_buttons[0].findChild(QLabel, "taskTitle")
        self.assertEqual(title.palette().color(QPalette.ColorRole.WindowText).name(), "#ffffff")
        self.window.open_batch()
        button = self.window.batch_page.run_button
        button.setEnabled(True)
        QTest.qWait(20)
        self.assertEqual(button.grab().toImage().pixelColor(5, button.height()//2).name(), "#116fae")
        button.setEnabled(False)
        QTest.qWait(20)
        self.assertEqual(button.grab().toImage().pixelColor(5, button.height()//2).name(), "#f0f4f8")

    def test_maximized_window_restores_state_and_starts_on_home(self):
        from equipeffi.presentation.qt.shell import MainWindow
        self.window.showMaximized()
        QTest.qWait(20)
        self.window.close()
        second = MainWindow(self.settings)
        second.show()
        QTest.qWait(20)
        try:
            self.assertTrue(second.isMaximized())
            self.assertEqual(second.navigation.currentRow(), 0)
            self.assertTrue(second.sidebar.isHidden())
        finally:
            second.close()
            second.deleteLater()
