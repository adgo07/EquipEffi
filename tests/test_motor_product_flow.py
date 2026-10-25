"""真实三设备编排、精确阈值与候选边界；不替代WPS交互验收。"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from openpyxl import load_workbook
from equipeffi.composition import (create_batch_evaluation_service,
    create_motor_analysis_service, motor_candidate_enabled)
from equipeffi.application.services.motor_analysis_service import MotorAnalysisRequest
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.infrastructure.persistence.sqlite_batch_record_repository import SqliteBatchRecordRepository


class MotorProductFlowTests(unittest.TestCase):
    def test_candidate_switch_alone_launches_desktop(self):
        from equipeffi.entrypoint import main
        with patch.dict(os.environ, {}, clear=True), patch(
                "equipeffi.composition.launch_qt", return_value=0) as launch:
            self.assertEqual(main(["--motor-candidate"]), 0)
            launch.assert_called_once_with()
            self.assertTrue(motor_candidate_enabled())

    def test_candidate_is_opt_in(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(motor_candidate_enabled())
        with patch.dict(os.environ, {"EQUIPEFFI_ENABLE_MOTOR_CANDIDATE": "1"}):
            self.assertTrue(motor_candidate_enabled())

    def test_only_unconnected_sheet_does_not_create_successful_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = AppDataPaths(Path(directory) / "data")
            batch = create_batch_evaluation_service(paths=paths, motor_candidate=True)
            source = Path(directory) / "unsupported.xlsx"
            destination = Path(directory) / "result.xlsx"
            batch.template_resource.download_to(source)
            workbook = load_workbook(source)
            workbook["空压机"]["B4"] = "保留未接通设备"
            workbook["空压机"]["D4"] = 1
            workbook.save(source)
            workbook.close()
            with self.assertRaisesRegex(ValueError, "没有可评价数据"):
                batch.evaluate_workbook(source, destination=destination)
            self.assertFalse(destination.exists())
            self.assertEqual(batch.batch_repository.list_batch_records(), [])

    def test_three_device_batch_and_reimport_preserve_exact_result(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = AppDataPaths(Path(directory) / "data")
            batch = create_batch_evaluation_service(paths=paths, motor_candidate=True)
            source = Path(directory) / "input.xlsx"
            batch.template_resource.download_to(source)
            workbook = load_workbook(source)
            motor = create_motor_analysis_service(with_persistence=False)
            category = next(c for c in motor.input_contract.categories
                            if c.category_id == "three_phase_induction")
            for cell, value in {"D4": 2, "F4": category.label, "G4": 0.38,
                                "H4": 50, "J4": 0.14, "K4": 4, "M4": 71.43}.items():
                workbook["电动机"][cell] = value
            workbook["离心泵"]["D4"] = 3
            workbook["离心泵"]["F4"] = "其他类别"
            workbook["变压器"]["D4"] = 4
            workbook["变压器"]["F4"] = "其他类别"
            workbook.save(source)
            workbook.close()
            before = source.read_bytes()
            result = batch.evaluate_workbook(source)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(result.batch_record_error, "")
            self.assertEqual(result.summary.total_quantity, 9)
            self.assertEqual(result.summary.conclusion_quantities, {"3级": 2, "不在范围": 7})
            output = load_workbook(result.result_workbook, data_only=True)
            self.assertEqual(output["电动机"]["Q4"].value, "3级")
            self.assertEqual(float(output["电动机"]["O4"].value), 71.43)
            self.assertIn("电动机", output["模板说明"]["B30"].value)
            output.close()
            record = SqliteBatchRecordRepository(paths.records_db).load_batch_record(result.batch_record_id)
            self.assertEqual(record.standard_code, "MULTI")
            self.assertEqual(len(record.summary["sheets"]), 3)
            repeated = batch.evaluate_workbook(Path(result.result_workbook))
            self.assertEqual(repeated.summary.conclusion_quantities, result.summary.conclusion_quantities)
            with self.assertRaisesRegex(ValueError, "未启用"):
                create_batch_evaluation_service(paths=paths, motor_candidate=False).evaluate_workbook(source)

    def test_efficiency_fraction_is_input_error_not_record(self):
        with tempfile.TemporaryDirectory() as directory:
            motor = create_motor_analysis_service(paths=AppDataPaths(Path(directory)))
            values = dict(category_id="three_phase_induction", rated_voltage_kv="0.38",
                          rated_frequency_hz="50", rated_output_power_kw="0.14", poles="4",
                          measured_efficiency_pct="0.85")
            outcome = motor.analyze_and_record(MotorAnalysisRequest(values))
            self.assertEqual(outcome.result.evaluation_status, "INVALID_INPUT")
            self.assertNotEqual(outcome.record_status, "SAVED")
            values["measured_efficiency_pct"] = "71.43"
            accepted = motor.analyze_and_record(MotorAnalysisRequest(values))
            self.assertEqual(accepted.result.ui_conclusion, "3级")
            self.assertEqual(accepted.record_status, "SAVED")
            threshold = accepted.result.thresholds["grade_2"]
            self.assertEqual(threshold["exact"]["numerator"], "2143")
            self.assertEqual(threshold["exact"]["denominator"], "30")
