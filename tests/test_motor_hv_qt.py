"""Shared motor Qt fields, switching and immutable high-voltage history."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
from pathlib import Path
import unittest
from PySide6.QtWidgets import QApplication, QComboBox, QWidget
from equipeffi.composition import create_motor_analysis_service, create_pump_analysis_service, create_transformer_analysis_service
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.presentation.qt.pages.motor_analysis import MotorAnalysisPage
from equipeffi.presentation.qt.pages.transformer_analysis import DeviceAnalysisPage, TransformerAnalysisPage
from equipeffi.presentation.qt.pages.records import RecordsPage
from equipeffi.presentation.qt.pages.standards import StandardsPage
from tests.unit.test_motor_qt import _dispose_widget


class HvQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_real_high_voltage_fields_record_and_low_voltage_switch(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = AppDataPaths(Path(directory))
            service = create_motor_analysis_service(paths=paths)
            page = MotorAnalysisPage(service)
            history = None
            try:
                page.category.setCurrentIndex(page.category.findData("gb30254_cage_induction"))
                self.assertIn("GB 30254", page.standard_title.text())
                self.assertNotIn("max_nameplate_speed_rpm", page.field_inputs)
                self.assertIsNone(page.field_inputs["cooling_method"].currentData())
                for key, value in dict(rated_voltage_v="3000", rated_frequency_hz="50", cooling_method="IC01",
                    rated_output_power_kw="211", poles="2", rated_efficiency_pct="94.055").items():
                    widget = page.field_inputs[key]
                    if isinstance(widget, QComboBox): widget.setCurrentIndex(widget.findData(value))
                    else: widget.setText(value)
                result = page.evaluate()
                self.assertEqual(result.ui_conclusion, "1级")
                self.assertEqual(result.support_status, "IMPLEMENTED")
                self.assertEqual(page.last_record_status, "SAVED")
                self.assertIn("94.06", page.thresholds_label.text())
                self.assertIn("200～220 kW", page.explanation.text())
                history = RecordsPage(create_pump_analysis_service(paths=paths))
                text = history.show_record(page.last_saved_record_id)
                self.assertIn("GB 30254-2024", text)
                self.assertIn("冷却方式：IC01", text)
                self.assertIn("94.06", text)
                page.category.setCurrentIndex(0)
                self.assertIn("GB 18613", page.standard_title.text())
                self.assertTrue(page.stale_label.isHidden() is False)
                self.assertEqual(page.field_inputs, {})
            finally:
                _dispose_widget(history); _dispose_widget(page)

    def test_catalog_and_selected_standard_route(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = AppDataPaths(Path(directory))
            pump = create_pump_analysis_service(paths=paths)
            transformer = create_transformer_analysis_service(paths=paths)
            motor = create_motor_analysis_service(paths=paths)
            catalog = StandardsPage(pump, transformer=transformer, motor=motor)
            motor_page = MotorAnalysisPage(motor)
            selector = DeviceAnalysisPage(QWidget(), TransformerAnalysisPage(transformer), motor_page=motor_page)
            try:
                row = next(r for r in catalog._catalog if r["standard_code"] == "GB 30254-2024")
                self.assertEqual(row["support"], "已实现，待验收")
                self.assertTrue(selector.select_standard("GB 30254-2024"))
                self.assertEqual(motor_page.category.currentData(), "gb30254_cage_induction")
                self.assertTrue(selector.select_standard("GB 18613-2020"))
                self.assertIsNone(motor_page.category.currentData())
                self.assertIn("GB 18613", motor_page.standard_title.text())
            finally:
                _dispose_widget(selector); _dispose_widget(catalog)


if __name__ == "__main__": unittest.main()
