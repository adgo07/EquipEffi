"""电机Qt与真实Application的条件字段和快照验证。"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication, QComboBox
from equipeffi.composition import create_motor_analysis_service, create_pump_analysis_service
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.presentation.qt.pages.motor_analysis import MotorAnalysisPage
from equipeffi.presentation.qt.pages.records import RecordsPage


class MotorQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_category_fields_and_real_history(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = AppDataPaths(Path(directory))
            service = create_motor_analysis_service(paths=paths)
            page = MotorAnalysisPage(service)
            page.category.setCurrentIndex(page.category.findData("ac_fan_capacitor_run"))
            self.assertNotIn("max_nameplate_speed_rpm", page.field_inputs)
            page.category.setCurrentIndex(page.category.findData("ac_fan_brushless_dc"))
            self.assertIn("max_nameplate_speed_rpm", page.field_inputs)
            page.category.setCurrentIndex(page.category.findData("three_phase_induction"))
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
            default_history.close()
            records.close()
            page.close()

    def test_candidate_shell_routes_motor_and_displays_standard(self):
        from equipeffi.composition import create_settings_runtime, create_transformer_analysis_service
        from equipeffi.presentation.qt.shell import MainWindow
        from equipeffi.infrastructure.runtime_logging import close_logging
        with tempfile.TemporaryDirectory() as directory:
            paths = AppDataPaths(Path(directory))
            settings, logger = create_settings_runtime(paths=paths)
            window = MainWindow(settings, create_pump_analysis_service(paths=paths),
                                transformer=create_transformer_analysis_service(paths=paths),
                                motor=create_motor_analysis_service(paths=paths))
            try:
                self.assertIn("验收候选", window.windowTitle())
                self.assertIn("GB 18613-2020", window.home_page.standard_label.text())
                window.open_analysis(standard_code="GB 18613-2020")
                self.assertIs(window.device_analysis_page.pages.currentWidget(), window.motor_analysis_page)
                selector = window.standards_page.standard_selector
                selector.setCurrentIndex(selector.findData("GB 18613-2020"))
                self.assertIn("电动机能效", window.standards_page.facts.text())
            finally:
                window.close()
                close_logging(logger)
