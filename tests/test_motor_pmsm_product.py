"""GB 30253 Application, shared Qt page and immutable single-unit records."""
from contextlib import closing
from datetime import date
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QComboBox, QWidget

from equipeffi.application.services.motor_analysis_service import MotorAnalysisRequest
from equipeffi.composition import create_motor_analysis_service, create_pump_analysis_service, create_transformer_analysis_service
from equipeffi.domain.devices.motor_pmsm.calculator import ISSUE_003
from equipeffi.domain.devices.motor_pmsm.input_contract import BRANCHES, STANDARD_CODE
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.presentation.qt.pages.motor_analysis import MotorAnalysisPage
from equipeffi.presentation.qt.pages.records import RecordsPage
from equipeffi.presentation.qt.pages.standards import StandardsPage
from equipeffi.presentation.qt.pages.transformer_analysis import DeviceAnalysisPage, TransformerAnalysisPage
from tests.unit.test_motor_qt import _dispose_widget


BASE = dict(category_id="gb30253_lv_vfd", rated_voltage_v=" 3.8e2 ", rated_output_power_kw="0.65",
            rated_speed_rpm="550.0", rated_efficiency_pct="82.125", input_contract_revision="motor-input.v5")


class PmsmApplicationTests(unittest.TestCase):
    def test_one_legal_terminal_per_analysis_with_immutable_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = AppDataPaths(Path(directory))
            motor = create_motor_analysis_service(paths=paths)
            request = MotorAnalysisRequest(BASE | {"poles": "12", "rated_frequency_hz": "60"}, date(2026, 11, 11))
            outcome = motor.analyze_and_record(request)
            self.assertEqual(outcome.record_status, "SAVED")
            record = outcome.record
            self.assertEqual((record.standard_code, record.device_type, record.grade), (STANDARD_CODE, "motor_pmsm", "1"))
            self.assertEqual(record.input_snapshot["raw_input"]["rated_voltage_v"], " 3.8e2 ")
            self.assertEqual(record.input_snapshot["input_units"]["rated_speed_rpm"], "r/min")
            self.assertNotIn("poles", record.input_snapshot["raw_input"])
            self.assertNotIn("rated_frequency_hz", record.input_snapshot["raw_input"])
            self.assertEqual(record.result_snapshot["thresholds"]["grade_1"]["exact"]["numerator"], "657")
            self.assertEqual(record.reference_snapshot["standard_issues"][ISSUE_003], "PROVISIONAL")
            self.assertEqual(len(record.reference_snapshot["grade_lookups"]["grade_1"]["source_cells"]), 4)
            self.assertEqual(record.reference_snapshot["numeric_profile_version"], "1.0.0")

            missing = motor.analyze_and_record(MotorAnalysisRequest(BASE | {"rated_speed_rpm": None}))
            self.assertEqual((missing.record_status, missing.record.evaluation_status), ("SAVED", "INSUFFICIENT_DATA"))
            invalid = motor.analyze_and_record(MotorAnalysisRequest(BASE | {"rated_efficiency_pct": "0.82125"}))
            self.assertEqual((invalid.record_status, invalid.record), ("NOT_ELIGIBLE", None))
            with patch.object(motor.permanent_magnet._calculator, "evaluate", side_effect=RuntimeError("pack error")):
                with self.assertRaisesRegex(RuntimeError, "pack error"):
                    motor.analyze_and_record(request)
                reopened = create_pump_analysis_service(paths=paths).open_record(record.record_id)
                self.assertEqual(reopened.result_snapshot, record.result_snapshot)
                self.assertEqual(reopened.reference_snapshot, record.reference_snapshot)
            with closing(sqlite3.connect(paths.records_db)) as connection:
                self.assertEqual(connection.execute("SELECT count(*) FROM record").fetchone()[0], 2)

    def test_persistence_and_explicit_contract_errors(self):
        motor = create_motor_analysis_service(with_persistence=False)
        result = motor.analyze_and_record(MotorAnalysisRequest(BASE))
        self.assertEqual(result.record_status, "SAVE_FAILED")
        self.assertIsNone(result.record)
        with self.assertRaisesRegex(ValueError, "v5"):
            motor.evaluate(MotorAnalysisRequest(BASE | {"input_contract_revision": "motor-input.v4"}))
        with self.assertRaisesRegex(ValueError, "不一致"):
            motor.evaluate(MotorAnalysisRequest(BASE, standard_code="GB 30254-2024"))


class PmsmQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_library_explicit_branch_fields_and_reopening(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = AppDataPaths(Path(directory))
            motor = create_motor_analysis_service(paths=paths)
            pump = create_pump_analysis_service(paths=paths)
            transformer = create_transformer_analysis_service(paths=paths)
            catalog = StandardsPage(pump, transformer=transformer, motor=motor)
            page = MotorAnalysisPage(motor)
            selector = DeviceAnalysisPage(QWidget(), TransformerAnalysisPage(transformer), motor_page=page)
            history = RecordsPage(pump)
            try:
                row = next(item for item in catalog._catalog if item["standard_code"] == STANDARD_CODE)
                self.assertEqual(row["support"], "已实现，待验收")
                self.assertTrue(selector.select_standard(STANDARD_CODE))
                self.assertIn(STANDARD_CODE, page.standard_title.text())
                self.assertIsNone(page.category.currentData())
                self.assertEqual(page.category.count(), len(BRANCHES) + 1)
                self.assertIsNone(page.evaluate())
                self.assertIsNone(page.last_saved_record_id)

                for category, extras in (
                    ("gb30253_hv_async_start", {"rated_frequency_hz", "poles", "cooling_method"}),
                    ("gb30253_lv_async_start", {"rated_frequency_hz", "poles"}),
                    ("gb30253_hv_vfd", {"rated_speed_rpm", "cooling_method"}),
                    ("gb30253_elevator", {"rated_speed_rpm"}),
                    ("gb30253_lv_vfd", {"rated_speed_rpm"}),
                ):
                    page.category.setCurrentIndex(page.category.findData(category))
                    self.assertEqual(set(page.field_inputs), extras | {
                        "rated_voltage_v", "rated_output_power_kw", "rated_efficiency_pct", "user_note"})
                    if "cooling_method" in extras:
                        field = page.field_inputs["cooling_method"]
                        self.assertIsInstance(field, QComboBox)
                        self.assertNotEqual(field.findData("IC71W(IC3W7)"), -1)
                        self.assertEqual(field.findData("IC01"), -1)
                        field.setCurrentIndex(field.findData("IC81W"))
                for key in ("rated_voltage_v", "rated_output_power_kw", "rated_speed_rpm", "rated_efficiency_pct"):
                    page.field_inputs[key].setText(BASE[key])
                result = page.evaluate()
                self.assertEqual((result.grade, page.last_record_status), ("1", "SAVED"))
                self.assertIn("临时解释", page.explanation.text())
                self.assertIn("双线性插值", page.explanation.text())
                self.assertIn("82.13", page.thresholds_label.text())
                self.assertNotIn("cooling_method", result.raw_values["raw_input"])
                with patch.object(motor.permanent_magnet._calculator, "evaluate", side_effect=AssertionError("recalculated")):
                    reopened = history.show_record(page.last_saved_record_id)
                for text in (STANDARD_CODE, "额定转速", "82.13", "临时解释", "表8、表9、表10"):
                    self.assertIn(text, reopened)
                self.assertEqual(history.detail_tabs.count(), 2)
                selector.select_standard(None)
                self.assertGreater(page.category.count(), len(BRANCHES) + 1)
                selector.select_standard("GB 30254-2024")
                self.assertEqual(page.category.currentData(), "gb30254_cage_induction")
            finally:
                _dispose_widget(history)
                _dispose_widget(selector)
                _dispose_widget(catalog)
