"""第二阶段状态、完整历史与正式保存边界回归。"""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace
from hashlib import sha256
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QCoreApplication, QEvent, Qt, QRect
from PySide6.QtWidgets import QApplication, QComboBox, QScrollArea
from PySide6.QtTest import QTest
from equipeffi.composition import (create_settings_runtime, create_pump_analysis_service,
    create_transformer_analysis_service, create_motor_analysis_service, create_batch_evaluation_service,
    create_records_runtime)
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.infrastructure.persistence.sqlite_batch_record_repository import SqliteBatchRecordRepository
from equipeffi.infrastructure.runtime_logging import close_logging
from equipeffi.presentation.qt.shell import MainWindow
from tests.unit.test_batch_records_history import _snapshot


class UiFamilyStage2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.paths = AppDataPaths(Path(self.temp.name))
        self.settings, self.logger = create_settings_runtime(paths=self.paths)
        self.pump = create_pump_analysis_service(paths=self.paths)
        self.transformer = create_transformer_analysis_service(paths=self.paths)
        self.motor = create_motor_analysis_service(paths=self.paths)
        self.batch = create_batch_evaluation_service(paths=self.paths, motor_candidate=True)
        self.window = MainWindow(self.settings, self.pump, transformer=self.transformer,
                                 motor=self.motor, batch=self.batch, data_location=self.paths.root)
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        close_logging(self.logger)
        self.temp.cleanup()

    def _fill(self, page, values):
        for key, value in values.items():
            control = page.field_inputs[key]
            if isinstance(control, QComboBox):
                control.setCurrentIndex(control.findData(value))
            else:
                control.setText(value)

    def _pump_record(self):
        page = self.window.analysis_page
        page.project_name.setText("历史测试项目")
        page.category.setCurrentIndex(page.category.findData("单级单吸清水离心泵"))
        for key, value in dict(QBEP="100", HBEP="50", speed="2900", efficiency="90").items():
            page.point_inputs[key].setText(value)
        page.evaluate()
        return self.pump.open_record(page.last_saved_record_id)

    def test_device_categories_preserve_local_values_and_stale_records(self):
        self.window.open_analysis(standard_code="GB 20052-2024")
        page = self.window.transformer_analysis_page
        page.category.setCurrentIndex(page.category.findData("GB20052-T01"))
        self._fill(page, {"capacity_kva": "500", "no_load_loss_w": "300", "load_loss_w": "2000"})
        page.field_inputs["standard_conditions"].setCurrentIndex(1)
        page.evaluate()
        self.assertEqual(page.last_record_status, "SAVED")
        record = self.pump.open_record(page.last_saved_record_id)
        page.field_inputs["no_load_loss_w"].setText("301")
        self.assertFalse(page.stale_label.isHidden())
        self.assertEqual(record, self.pump.open_record(record.record_id))
        page.category.setCurrentIndex(page.category.findData("GB20052-T02"))
        page.category.setCurrentIndex(page.category.findData("GB20052-T01"))
        self.assertEqual(page.field_inputs["no_load_loss_w"].text(), "301")
        self.window.open_analysis(standard_code="GB 18613-2020")
        motor = self.window.motor_analysis_page
        motor.category.setCurrentIndex(motor.category.findData("three_phase_induction"))
        self._fill(motor, dict(rated_voltage_v="380", rated_frequency_hz="50",
            rated_output_power_kw="0.14", poles="4", rated_efficiency_pct="71.43"))
        self.assertNotIn("efficiency_basis_status", motor.field_inputs)
        motor.evaluate()
        self.assertEqual(motor.last_record_status, "SAVED")
        self.window.records_page.show_record(motor.last_saved_record_id)
        self.assertNotIn("AS_DECLARED_BY_FIELD", self.window.records_page.inputs_detail.text())
        self.assertIn("额定效率（%）：71.43", self.window.records_page.inputs_detail.text())
        motor.field_inputs["rated_efficiency_pct"].setText("72")
        self.assertFalse(motor.stale_label.isHidden())
        self.assertTrue(motor.view_record_button.isHidden())
        self.window.open_analysis(standard_code="GB 20052-2024")
        self.assertEqual(page.field_inputs["no_load_loss_w"].text(), "301")

    def test_record_two_tabs_read_snapshots_and_back_keeps_context(self):
        record = self._pump_record()
        page = self.window.records_page
        page.search.setText("19762")
        self.window.open_records(record.record_id)
        before = sha256(self.paths.records_db.read_bytes()).hexdigest()
        with patch.object(self.pump, "evaluate", side_effect=AssertionError("must not recalculate")):
            page.show_record(record.record_id)
        self.assertEqual(page.detail_tabs.count(), 2)
        self.assertEqual([page.detail_tabs.tabText(i) for i in range(2)],
                         ["基本信息与结果", "输入数据与计算依据"])
        self.assertIn("历史测试项目", page.detail.text())
        self.assertIn("流量 Q（m³/h）：100", page.inputs_detail.text())
        self.assertEqual(before, sha256(self.paths.records_db.read_bytes()).hexdigest())
        page.back_button.click()
        self.assertEqual(page.stack.currentIndex(), 0)
        self.assertEqual(page.search.text(), "19762")
        self.assertEqual(page.list.currentRow(), 0)

    def test_single_older_than_100_and_batch_global_search_older_than_50(self):
        record = self._pump_record()
        repository = create_records_runtime(paths=self.paths)[1]
        for index in range(105):
            repository.append_record(replace(record, record_id=f"UI2-{index:03d}",
                finalized_at_utc=f"2026-10-26T01:{index // 60:02d}:{index % 60:02d}Z"))
        page = self.window.records_page
        self.window.open_records()
        self.assertEqual(page.list.rowCount(), 100)
        page.load_more_button.click()
        self.assertEqual(page.list.rowCount(), 106)
        page.list.setCurrentCell(105, 0)
        QTest.keyClick(page.list, Qt.Key.Key_Return)
        self.assertEqual(page.stack.currentIndex(), 1)
        page.back_button.click()
        self.assertEqual(page.list.currentRow(), 105)
        batch_repository = SqliteBatchRecordRepository(self.paths.records_db)
        for index in range(61):
            batch_repository.append_batch_record(_snapshot(index))
        batch_repository.append_batch_record(replace(_snapshot(1), batch_record_id="BATCH-MIX",
            created_at_utc="2026-10-20T00:00:00+00:00",
            source_file_name="UI_100%.xlsx", standard_code="MULTI", sheet_name="MULTI",
            summary={"sheets": [{"sheet_name": "变压器", "standard_code": "GB 20052-2024"}]}))
        page.refresh_batch_records()
        self.assertEqual(page.batch_list.rowCount(), 50)
        self.assertNotIn("BATCH-MIX", [r.batch_record_id for r in page._batch_visible])
        page.batch_button.click()
        for keyword in ("20052", "UI_", "%"):
            page.batch_search.setText(keyword)
            self.assertEqual(page.batch_list.rowCount(), 1)
            self.assertEqual(page.batch_list.item(0, 0).text(), "UI_100%.xlsx")
        page.batch_search.setText("<img src=x>")
        self.assertEqual(page.batch_list.rowCount(), 1)
        self.assertEqual(page.batch_list.item(0, 0).text(), "<img src=x>.xlsx")
        page.batch_list.cellActivated.emit(0, 0)
        self.assertEqual(page.detail.textFormat(), Qt.TextFormat.RichText)
        from PySide6.QtWidgets import QLabel
        self.assertIn("&lt;img src=x&gt;", QLabel.text(page.detail))
        self.assertIn("未保存逐行完整输入", page.inputs_detail.text())
        page.back_button.click()
        self.assertEqual(page.lists.currentIndex(), 1)
        self.assertEqual(page.batch_search.text(), "<img src=x>")

    def test_source_replacement_cancel_and_busy_protect_result_association(self):
        page = self.window.batch_page
        source = self.paths.root / "first.xlsx"
        self.batch.export_blank_template(source)
        import openpyxl
        workbook = openpyxl.load_workbook(source)
        sheet = workbook["离心泵"]
        for column, value in {"B": "测试泵", "D": 1, "F": "单级单吸清水离心泵",
                              "G": 100, "H": 50, "I": 2900, "K": "单吸", "L": 1, "M": 90}.items():
            sheet[f"{column}4"] = value
        workbook.save(source)
        workbook.close()
        page.set_source(source)
        result = page.run()
        self.assertIsNotNone(result)
        self.assertIsNotNone(page.result_path())
        with patch("equipeffi.presentation.qt.pages.batch.QFileDialog.getOpenFileName", return_value=("", "")):
            page._pick_source()
        self.assertIs(page.last_result, result)
        page.set_source(source)  # 同一路径也可能已被外部编辑，明确重新选择即失效。
        self.assertIsNone(page.last_result)
        self.assertIsNone(page.result_path())
        self.assertFalse(page.open_result_button.isEnabled())
        missing = self.paths.root / "missing.xlsx"
        page.set_source(missing)
        self.assertIsNone(page.last_check)
        self.assertIn("找不到", page.check_label.text())
        page._set_busy(True)
        page.set_source(source)
        self.assertEqual(page.source_edit.text(), str(missing))
        self.assertFalse(page.source_button.isEnabled())
        self.assertFalse(page.target_edit.isEnabled())
        page._set_busy(False)

    def test_settings_save_failure_and_long_paths_are_accessible(self):
        self.window.resize(560, 420)
        self.window.open_settings()
        page = self.window.settings_page
        self.settings.set("last.directory", "C:/" + "很长的测试目录/" * 30)
        page.refresh()
        page.runtime_section.set_expanded(True)
        self.app.processEvents()
        self.assertEqual(page.scroll_area.horizontalScrollBar().maximum(), 0)
        self.assertTrue(page.last_directory.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse)
        with patch.object(self.settings, "set", side_effect=OSError("read only")):
            page.log_level.setCurrentIndex((page.log_level.currentIndex() + 1) % page.log_level.count())
        self.assertIn("设置未保存", page.notice.text())

    def test_small_record_list_has_complete_row_and_mouse_keyboard_roundtrips(self):
        record = self._pump_record()
        self.window.resize(560, 420)
        self.window.open_records()
        page = self.window.records_page
        page.search.setText("19762")
        page.date_filter.setText(record.as_of)
        QTest.qWait(20)
        scroll = page.list_scroll_area
        table = page.list
        self.assertEqual(self.window.size().width(), 560)
        self.assertGreater(scroll.verticalScrollBar().maximum(), 0)
        scroll.ensureWidgetVisible(table, 0, 10)
        QTest.qWait(20)
        row = table.visualItemRect(table.item(0, 0))
        self.assertGreaterEqual(table.viewport().height(), table.rowHeight(0))

        self.assertTrue(table.viewport().rect().contains(row), (table.viewport().rect(), row))
        visible_row = QRect(table.viewport().mapTo(scroll.viewport(), row.topLeft()), row.size())
        self.assertTrue(scroll.viewport().rect().contains(visible_row), (scroll.viewport().rect(), visible_row))
        saved_scroll = scroll.verticalScrollBar().value()
        QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=row.center())
        QTest.mouseDClick(table.viewport(), Qt.MouseButton.LeftButton, pos=row.center())
        self.assertEqual(page.stack.currentIndex(), 1)
        self.assertIn("历史测试项目", page.detail.text())
        QTest.mouseClick(page.back_button, Qt.MouseButton.LeftButton)
        self.assertEqual(page.stack.currentIndex(), 0)
        self.assertEqual(page.search.text(), "19762")
        self.assertEqual(page.date_filter.text(), record.as_of)
        self.assertEqual(scroll.verticalScrollBar().value(), saved_scroll)
        table.setCurrentCell(0, 0)
        table.setFocus()
        QTest.keyClick(table, Qt.Key.Key_Return)
        self.assertEqual(page.stack.currentIndex(), 1)
        QTest.mouseClick(page.back_button, Qt.MouseButton.LeftButton)
        self.assertEqual(page.list.currentRow(), 0)
        self.assertEqual(scroll.verticalScrollBar().value(), saved_scroll)
        self.window.resize(1000, 700)
        QTest.qWait(20)
        self.assertEqual(scroll.verticalScrollBar().maximum(), 0)
        self.assertGreaterEqual(table.viewport().height(), table.rowHeight(0))

    def test_transformer_special_category_note_visible_and_regular_return(self):
        from PySide6.QtWidgets import QLabel
        self.window.open_analysis(standard_code="GB 20052-2024")
        page = self.window.transformer_analysis_page
        for label in ("其他类别", "不确定类别"):
            index = page.category.findText(label)
            self.assertGreaterEqual(index, 0)
            page.category.setCurrentIndex(index)
            self.app.processEvents()
            notes = [w for w in page.fields_group.findChildren(QLabel) if "没有可填写" in w.text()]
            self.assertEqual(len(notes), 1)
            self.assertTrue(notes[0].isVisibleTo(page))
            self.assertTrue(page.fields_group.isVisibleTo(page))
            self.assertFalse(page.field_inputs)
            result = page.evaluate()
            self.assertIsNotNone(result)
            if label == "其他类别":
                record = self.pump.open_record(page.last_saved_record_id)
                self.assertEqual(record.evaluation_status, "OUT_OF_STANDARD_SCOPE")
            else:
                self.assertEqual(result.ui_conclusion, "无法判定")
                self.assertEqual(page.last_record_status, "NOT_ELIGIBLE")
                self.assertIsNone(page.last_saved_record_id)
            page.category.setCurrentIndex(page.category.findData("GB20052-T03"))
            self.assertIn("capacity_kva", page.field_inputs)
            self.assertFalse(any("没有可填写" in w.text() for w in page.fields_group.findChildren(QLabel)))

    def test_names_search_entire_history_with_consistent_count(self):
        record = self._pump_record()
        repository = create_records_runtime(paths=self.paths)[1]
        for index in range(105):
            repository.append_record(replace(record, record_id=f"NAME-{index:03d}",
                input_snapshot=dict(record.input_snapshot, project_name="共同名称", equipment_no=f"设备-{index}"),
                finalized_at_utc=f"2026-10-26T01:{index // 60:02d}:{index % 60:02d}Z"))
        repository.append_record(replace(record, record_id="NAME-OLD",
            input_snapshot=dict(record.input_snapshot, project_name="旧项目唯一名称", equipment_no="旧设备"),
            finalized_at_utc="2020-01-01T00:00:00Z"))
        repository.append_record(replace(record, record_id="EQUIPMENT-OLD",
            input_snapshot=dict(record.input_snapshot, project_name=None, equipment_no="设备唯一名称"),
            finalized_at_utc="2020-01-01T00:00:01Z"))
        self.window.open_records()
        page = self.window.records_page
        self.assertNotIn("NAME-OLD", [r.record_id for r in page._visible])
        for keyword, expected in (("旧项目唯一名称", "NAME-OLD"), ("设备唯一名称", "EQUIPMENT-OLD")):
            page.search.setText(keyword)
            self.assertEqual(page._total, 1)
            self.assertEqual([r.record_id for r in page._visible], [expected])
        page.search.setText("共同名称")
        self.assertEqual(page._total, 105)
        self.assertEqual(page.list.rowCount(), 100)
        page.load_more_button.click()
        self.assertEqual(page.list.rowCount(), 105)

    def test_pump_tooltip_resets_on_change_clear_and_failure(self):
        self._pump_record()
        page = self.window.analysis_page
        self.assertTrue(page.evaluate_button.toolTip())
        self.assertIs(page.suction.parent(), page)
        page.point_inputs["efficiency"].setText("91")
        self.assertEqual(page.evaluate_button.toolTip(), "")
        page.evaluate()
        self.assertTrue(page.evaluate_button.toolTip())
        page.project_name.clear()
        self.assertEqual(page.evaluate_button.toolTip(), "")
        page.evaluate()
        with patch.object(page.service, "analyze_and_record", side_effect=OSError("test failure")):
            page.evaluate()
        self.assertEqual(page.evaluate_button.text(), "分析")
        self.assertEqual(page.evaluate_button.toolTip(), "")
