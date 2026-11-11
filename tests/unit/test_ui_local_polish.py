"""局部收口的用户操作回归；仅使用隔离数据目录。"""
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from tests.unit import test_ui_family_stage2 as fixtures


class LocalPolishTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.UiFamilyStage2Tests.setUpClass.__func__)
    setUp = fixtures.UiFamilyStage2Tests.setUp
    tearDown = fixtures.UiFamilyStage2Tests.tearDown
    _pump_record = fixtures.UiFamilyStage2Tests._pump_record

    def test_record_empty_filtered_failure_and_retry_are_in_list(self):
        self.window.open_records()
        page = self.window.records_page
        self.assertTrue(page.empty_status.isVisible())
        self.assertEqual(page.empty_status.text(), "暂无分析记录")
        self.assertEqual(page.empty_action.text(), "新建分析")
        page.conclusion_filter.setCurrentIndex(1)
        self.assertIn("筛选", page.empty_status.text())
        self.assertEqual(page.empty_action.text(), "清除筛选")
        page.empty_action.click()
        self.assertEqual(page.conclusion_filter.currentIndex(), 0)
        with patch.object(self.pump, "search_records", side_effect=OSError("read failure")):
            page.refresh()
        self.assertEqual(page.empty_action.text(), "重试")
        page.empty_action.click()
        self.assertEqual(page.empty_status.text(), "暂无分析记录")
        self._pump_record()
        page.refresh()
        page._offset = 100
        with patch.object(self.pump, "search_records", side_effect=OSError("older page failed")):
            page._load_page(reset=False)
        self.assertEqual(page.list.rowCount(), 1)
        self.assertIn("仍可查看", page.empty_status.text())
        with patch.object(self.pump, "search_records", wraps=self.pump.search_records) as read:
            page.empty_action.click()
        self.assertEqual(read.call_args.args[0].offset, 100)
        self.assertEqual(page.list.rowCount(), 1)

    def test_batch_empty_search_and_retry_are_visible(self):
        self.window.open_records()
        page = self.window.records_page
        page.batch_button.click()
        self.assertTrue(page.batch_empty_status.isVisible())
        self.assertEqual(page.batch_empty_action.text(), "表格导入")
        page.batch_search.setText("no match")
        self.assertEqual(page.batch_empty_action.text(), "清除筛选")
        page.batch_empty_action.click()
        with patch.object(self.batch, "list_batch_records", side_effect=OSError("read failure")):
            page.refresh_batch_records()
        self.assertEqual(page.batch_empty_action.text(), "重试")
        page.batch_empty_action.click()
        self.assertIn("暂无", page.batch_empty_status.text())

    def test_batch_load_more_failure_retries_same_limit_and_keeps_rows(self):
        from tests.unit.test_batch_records_history import _snapshot
        page = self.window.records_page
        records = [_snapshot(i) for i in range(51)]
        with patch.object(self.batch, "list_batch_records", return_value=records):
            page.refresh_batch_records()
        self.assertEqual(page.batch_list.rowCount(), 50)
        with patch.object(self.batch, "list_batch_records", side_effect=OSError("older batch failure")):
            page.load_more_batch_records()
        self.assertEqual(page.batch_list.rowCount(), 50)
        self.assertIn("仍可查看", page.batch_empty_status.text())
        with patch.object(self.batch, "list_batch_records", return_value=records) as read:
            page.batch_empty_action.click()
        self.assertEqual(read.call_args.kwargs["limit"], 101)
        self.assertEqual(page.batch_list.rowCount(), 51)
        self.assertTrue(page.batch_empty_status.isHidden())

    def test_home_empty_action_and_failure_retry_are_distinct(self):
        self.window.open_home()
        page = self.window.home_page
        self.assertEqual(page.record_status.text(), "暂无分析记录")
        self.assertTrue(page.new_analysis_button.isVisible())
        with patch.object(self.pump, "list_records", side_effect=OSError("read failure")):
            page.refresh()
        self.assertTrue(page.new_analysis_button.isHidden())
        self.assertTrue(page.retry_button.isVisible())
        page.retry_button.click()
        self.assertTrue(page.retry_button.isHidden())
        self.assertTrue(page.new_analysis_button.isVisible())

    def test_standard_no_match_clear_retry_and_rated_summary(self):
        self.window.open_standards()
        page = self.window.standards_page
        expected_codes = (
            "GB 19762-2025", "GB 20052-2024", "GB 18613-2020",
            "GB 30254-2024", "GB 30253-2024",
        )
        page.search.setText("no match")
        self.assertTrue(page.clear_filters_button.isVisible())
        page.clear_filters_button.click()
        codes = [page.table.item(row, 0).text() for row in range(page.table.rowCount())]
        self.assertCountEqual(codes, expected_codes)
        self.assertEqual(len(codes), len(set(codes)))
        page.search.setText("30253")
        self.assertEqual(page.table.rowCount(), 1)
        self.assertEqual(page.table.item(0, 0).text(), "GB 30253-2024")
        page.search.clear()
        self.assertCountEqual(
            [page.table.item(row, 0).text() for row in range(page.table.rowCount())],
            expected_codes,
        )
        with patch.object(self.pump, "standard_overview", side_effect=OSError("read failure")):
            page.refresh()
        self.assertTrue(page.retry_button.isVisible())
        self.assertTrue(page.clear_filters_button.isHidden())
        page.retry_button.click()
        self.assertCountEqual(
            [page.table.item(row, 0).text() for row in range(page.table.rowCount())],
            expected_codes,
        )
        page.search.setText("18613")
        page.open_detail(0)
        text = page.section_labels[2].text()
        self.assertIn("额定效率", text)
        self.assertIn("1～100", text)
        self.assertNotIn("实测效率", text)

    def test_all_forms_explain_record_effect_before_analysis(self):
        for code, page in (("GB 19762-2025", self.window.analysis_page),
                           ("GB 20052-2024", self.window.transformer_analysis_page),
                           ("GB 18613-2020", self.window.motor_analysis_page)):
            self.window.open_analysis(standard_code=code)
            self.assertFalse(page.record_notice.isHidden())
            self.assertIn("再次分析会新增记录", page.record_notice.text())
            self.assertIn("失败不生成记录", page.record_notice.text())
            self.assertFalse(page.view_record_button.property("primary"))

    def test_supplementary_info_keyboard_and_empty_content(self):
        from equipeffi.presentation.qt.widgets.supplementary_info import SupplementaryInfo
        widget = SupplementaryInfo("背景说明", "这是一段背景")
        widget.show()
        self.app.processEvents()
        self.assertFalse(widget.toggle_button.icon().isNull())
        self.assertEqual(widget.toggle_button.accessibleName(), "背景说明")
        self.assertTrue(widget.popup.isHidden())
        widget.toggle_button.setFocus()
        QTest.keyClick(widget.toggle_button, Qt.Key.Key_Space)
        self.assertTrue(widget.popup.isVisible())
        QTest.keyClick(widget.close_button, Qt.Key.Key_Escape)
        self.assertTrue(widget.popup.isHidden())
        self.assertTrue(widget.toggle_button.hasFocus())
        self.assertFalse(widget.toggle_button.isChecked())
        widget.toggle_button.click()
        self.assertTrue(widget.popup.isVisible())
        self.assertTrue(widget.popup.screen().availableGeometry().contains(widget.popup.geometry()))
        widget.close_button.click()
        self.assertTrue(widget.popup.isHidden())
        widget.set_content("")
        self.assertTrue(widget.isHidden())
        widget.close()
        widget.deleteLater()
