"""电机Qt与真实Application的条件字段和快照验证。"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
import unittest
from pathlib import Path
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit
from equipeffi.composition import create_motor_analysis_service, create_pump_analysis_service
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.presentation.qt.pages.motor_analysis import MotorAnalysisPage
from equipeffi.presentation.qt.pages.records import RecordsPage


def _dispose_widget(widget) -> None:
    """Close the widget and flush deferred C++ destruction before the next test."""
    if widget is None:
        return
    try:
        widget.close()
    except RuntimeError:  # already destroyed
        return
    widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    QCoreApplication.processEvents()


class MotorQtTests(unittest.TestCase):
    def test_text_frequency_and_unlisted_even_poles_are_scope_results(self):
        with tempfile.TemporaryDirectory() as directory:
            service = create_motor_analysis_service(paths=AppDataPaths(Path(directory)))
            page = MotorAnalysisPage(service)
            try:
                page.category.setCurrentIndex(page.category.findData("three_phase_induction"))
                self.assertIsInstance(page.field_inputs["poles"], QLineEdit)
                for key, value in dict(rated_voltage_kv="0.38", rated_frequency_hz="5～120",
                                       rated_output_power_kw="0.14", poles="4",
                                       measured_efficiency_pct="71.43").items():
                    page.field_inputs[key].setText(value)
                self.assertEqual(page.evaluate().ui_conclusion, "不在范围")
                self.assertEqual(page.last_record_status, "SAVED")
                page.field_inputs["rated_frequency_hz"].setText("50")
                page.field_inputs["poles"].setText("10")
                self.assertEqual(page.evaluate().ui_conclusion, "不在范围")
                self.assertEqual(page.last_record_status, "SAVED")
                page.field_inputs["poles"].setText("3")
                self.assertEqual(page.evaluate().evaluation_status, "INVALID_INPUT")
                self.assertNotEqual(page.last_record_status, "SAVED")
            finally:
                _dispose_widget(page)

    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_category_fields_and_real_history(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = AppDataPaths(Path(directory))
            service = create_motor_analysis_service(paths=paths)
            page = MotorAnalysisPage(service)
            records = None
            default_history = None
            try:
                page.category.setCurrentIndex(page.category.findData("ac_fan_capacitor_run"))
                self.assertNotIn("max_nameplate_speed_rpm", page.field_inputs)
                page.category.setCurrentIndex(page.category.findData("ac_fan_brushless_dc"))
                self.assertIn("max_nameplate_speed_rpm", page.field_inputs)
                page.category.setCurrentIndex(page.category.findData("three_phase_induction"))
                for condition in ("单速", "封闭自扇冷", "N设计", "连续工作制"):
                    self.assertIn(condition, page.scope_hint.text())
                self.assertFalse(page.scope_hint.isHidden())
                for key, value in dict(rated_voltage_kv="0.38", rated_frequency_hz="50",
                                       rated_output_power_kw="0.14", poles="4",
                                       measured_efficiency_pct="71.43").items():
                    widget = page.field_inputs[key]
                    if isinstance(widget, QComboBox):
                        index = next(i for i in range(widget.count()) if str(widget.itemData(i)) == value)
                        widget.setCurrentIndex(index)
                    else:
                        widget.setText(value)
                result = page.evaluate()
                self.assertEqual(result.ui_conclusion, "3级")
                self.assertEqual(page.last_record_status, "SAVED")
                self.assertIn("71.43", page.thresholds_label.text())
                records = RecordsPage(create_pump_analysis_service(paths=paths), motor=service)
                text = records.show_record(page._last_outcome.record.record_id)
                self.assertIn("3级", text)
                self.assertIn("71.43", text)
                default_history = RecordsPage(create_pump_analysis_service(paths=paths))
                restored = default_history.show_record(page._last_outcome.record.record_id)
                self.assertIn("三相异步电动机", restored)
                self.assertNotIn("three_phase_induction", restored)
                self.assertNotIn("AS_DECLARED_BY_FIELD", restored)
                self.assertIn("按字段要求填报", restored)
                self.assertIn("软件状态：已接入，尚待正式支持验收。", restored)
                snapshot = default_history.service.open_record(page._last_outcome.record.record_id)
                default_history._render_technical(snapshot, snapshot.result_snapshot)
                self.assertIn("开发状态：已接入，尚待正式支持验收", default_history.technical.text())
                self.assertNotIn("支持状态：—", default_history.technical.text())
            finally:
                _dispose_widget(default_history)
                _dispose_widget(records)
                _dispose_widget(page)

    def test_candidate_shell_routes_motor_and_displays_standard(self):
        from equipeffi.composition import create_settings_runtime, create_transformer_analysis_service
        from equipeffi.presentation.qt.shell import MainWindow
        from equipeffi.infrastructure.runtime_logging import close_logging
        with tempfile.TemporaryDirectory() as directory:
            paths = AppDataPaths(Path(directory))
            settings, logger = create_settings_runtime(paths=paths)
            window = None
            try:
                window = MainWindow(settings, create_pump_analysis_service(paths=paths),
                                    transformer=create_transformer_analysis_service(paths=paths),
                                    motor=create_motor_analysis_service(paths=paths))
                self.assertIn("验收候选", window.windowTitle())
                self.assertEqual(window.standards_page.table.item(2, 0).text(), "GB 18613-2020")
                window.open_analysis(standard_code="GB 18613-2020")
                self.assertIs(window.device_analysis_page.pages.currentWidget(), window.motor_analysis_page)
                window.standards_page.open_detail(2)
                self.assertIn("电动机能效", window.standards_page.section_labels[0].text())
                self.assertEqual(window.standards_page.table.item(2, 4).text(), "验收候选")
            finally:
                _dispose_widget(window)
                close_logging(logger)
