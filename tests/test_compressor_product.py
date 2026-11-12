"""候选产品验证：真实SQLite、同核Excel和Qt薄表单。"""
from equipeffi.infrastructure.excel.template_resource import V65MotorTemplateResource, V66CompressorTemplateResource, validate_v6_template
from equipeffi.composition import create_compressor_analysis_service, create_pump_analysis_service, create_batch_evaluation_service
from PySide6.QtWidgets import QApplication, QComboBox, QWidget
from equipeffi.infrastructure.excel.unified_workbook_reader import CompressorWorkbookReader, UnifiedWorkbookReader
from tests.unit.test_motor_qt import _dispose_widget
from equipeffi.presentation.qt.pages.transformer_analysis import DeviceAnalysisPage
from equipeffi.presentation.qt.pages.records import RecordsPage
from equipeffi.presentation.qt.pages.compressor_analysis import CompressorAnalysisPage
from equipeffi.infrastructure.excel.ooxml_reader import OOXMLWorkbook
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.application.services.compressor_analysis_service import CompressorAnalysisRequest
from openpyxl import load_workbook
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from unittest.mock import patch
import unittest
import tempfile
import sqlite3
from pathlib import Path
import json
from hashlib import sha256
from datetime import date
from copy import deepcopy
from contextlib import closing
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
BASE = dict(category_id="oil_injected_rotary", rated_motor_output_power_kw="1.5",
            rated_discharge_pressure_mpa="0.3", cooling_method="AIR", specific_power_kw_per_m3_min="5.8")


class CompressorProductTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def test_record_identity_immutable_and_errors(self):
        with tempfile.TemporaryDirectory() as d:
            paths = AppDataPaths(Path(d))
            service = create_compressor_analysis_service(paths=paths)
            a = service.analyze_and_record(CompressorAnalysisRequest(BASE, date(2026, 11, 12)))
            b = service.analyze_and_record(CompressorAnalysisRequest(BASE))
            self.assertNotEqual(a.record.record_id, b.record.record_id)
            self.assertEqual(a.record.result_contract_version, "compressor-result.v1")
            self.assertEqual(a.record.reference_snapshot["assessment_scope"], "SPECIFIC_POWER_GRADE_ONLY")
            self.assertEqual(a.result.explanation, "")
            original = json.dumps(a.record.result_snapshot, sort_keys=True)
            for updates in ({"cooling_method": ""}, {"specific_power_kw_per_m3_min": 5.8}):
                outcome = service.analyze_and_record(CompressorAnalysisRequest(BASE | updates))
                self.assertEqual(outcome.record_status, "NOT_ELIGIBLE")
            with patch.object(service._calculator, "evaluate", side_effect=RuntimeError("system")):
                with self.assertRaises(RuntimeError):
                    service.analyze_and_record(CompressorAnalysisRequest(BASE))
            reopened = create_pump_analysis_service(paths=paths).open_record(a.record.record_id)
            self.assertEqual(json.dumps(reopened.result_snapshot, sort_keys=True), original)
            with closing(sqlite3.connect(paths.records_db)) as c:
                self.assertEqual(c.execute("select count(*) from record").fetchone()[0], 2)

    def test_template_preservation_and_gate(self):
        old, new = V65MotorTemplateResource(), V66CompressorTemplateResource()
        self.assertTrue(new.validate().is_valid)
        with OOXMLWorkbook(old.template_path) as a, OOXMLWorkbook(new.template_path) as b:
            self.assertEqual(a.sheet_names, b.sheet_names)
            self.assertEqual(len(b.sheet_names), 18)
            allowed = {a._sheets["空压机"], a._sheets["配置"], "xl/workbook.xml"}
            changed = {name for name in a.archive.namelist() if a.archive.read(name) != b.archive.read(name)}
            self.assertTrue(changed <= allowed | {
                            name for name in a.archive.namelist() if name == "xl/tables/table3.xml"})
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)/"坏配置.xlsx"
            book = load_workbook(new.template_path)
            book["配置"]["FG2"] = "改错类别"
            book.save(source)
            self.assertFalse(validate_v6_template(source).is_valid)
            with self.assertRaises(ValueError):
                CompressorWorkbookReader().read(old.template_path)

    def test_old_compressor_upgrade_message_without_blocking_existing_devices(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)/"旧模板.xlsx"
            book = load_workbook(V65MotorTemplateResource().template_path)
            book["空压机"]["B4"] = "旧空压机"
            book["空压机"]["D4"] = 1
            book.save(source)
            paths = AppDataPaths(Path(d)/"数据")
            batch = create_batch_evaluation_service(paths=paths)
            with self.assertRaisesRegex(ValueError, "V6.6"):
                batch.evaluate_workbook(source)
            book["离心泵"]["F4"] = "其他类别"
            book["离心泵"]["D4"] = 1
            book.save(source)
            result = batch.evaluate_workbook(source, destination=Path(d)/"结果.xlsx")
            self.assertIn("V6.6", result.summary.compatibility_messages[0])
            self.assertEqual(result.summary.data_row_count, 1)
            self.assertEqual(result.summary.conclusion_rows, {"不在范围": 1})

    def test_batch_same_kernel_evidence_and_input_protection(self):
        with tempfile.TemporaryDirectory() as d:
            paths = AppDataPaths(Path(d)/"数据")
            batch = create_batch_evaluation_service(paths=paths)
            source = Path(d)/"中文输入.xlsx"
            out = Path(d)/"中文结果.xlsx"
            book = load_workbook(V66CompressorTemplateResource().template_path)
            for n, changes in enumerate(({}, {"J": "液冷"}, {"F": "不确定类别", "G": "", "I": "", "J": "", "K": ""}, {"D": "0"}, {"K": "5.800000000000000000000001"}), 4):
                vals = {"D": 2, "F": "一般用喷油回转空气压缩机", "G": "1.5", "I": "0.3", "J": "风冷", "K": "5.8"} | changes
                for col, value in vals.items():
                    book["空压机"][f"{col}{n}"] = value
            book.save(source)
            before = sha256(source.read_bytes()).hexdigest()
            result = batch.evaluate_workbook(source, destination=out)
            self.assertEqual(before, sha256(source.read_bytes()).hexdigest())
            self.assertFalse(result.batch_record_error)
            summary = next(s for s in result.summary.sheets if s["sheet_id"] == "compressor")
            self.assertEqual(summary["data_row_count"], 5)
            rows = load_workbook(out, data_only=False)["空压机"]
            self.assertEqual([rows[f"O{n}"].value for n in range(4, 9)], ["1级", "无法判定", "无法判定", "输入错误", "2级"])
            self.assertIn("横杠", rows["R5"].value)
            self.assertFalse(rows["R4"].value)
            self.assertEqual(rows["L4"].value, "5.8")
            with closing(sqlite3.connect(paths.records_db)) as c:
                self.assertEqual(c.execute("select count(*) from record").fetchone()[0], 0)
                payload = json.loads(c.execute("select summary_json from batch_record").fetchone()[0])
                evidence = payload["compressor_row_evidence"]
                self.assertEqual(len(evidence), 5)
                self.assertEqual(evidence[0]["raw_input"]["specific_power_kw_per_m3_min"], "5.8")
                self.assertEqual(evidence[-1]["grade"], "2")
                self.assertNotIn("lookup", evidence[3])
            original_db = sha256(paths.records_db.read_bytes()).hexdigest()
            listed = batch.batch_repository.list_batch_records()
            self.assertNotIn("compressor_row_evidence", listed[0].summary)
            self.assertEqual(len(batch.batch_repository.load_batch_record(
                result.batch_record_id).summary["compressor_row_evidence"]), 5)
            self.assertEqual(original_db, sha256(paths.records_db.read_bytes()).hexdigest())

    def test_qt_fields_record_history_and_no_motor_routing(self):
        with tempfile.TemporaryDirectory() as d:
            paths = AppDataPaths(Path(d))
            service = create_compressor_analysis_service(paths=paths)
            page = CompressorAnalysisPage(service)
            history = None
            device = None
            try:
                page.category.setCurrentIndex(page.category.findData(BASE["category_id"]))
                self.assertIsNone(page.field_inputs["cooling_method"].currentData())
                for key, value in BASE.items():
                    if key == "category_id":
                        continue
                    control = page.field_inputs[key]
                    if isinstance(control, QComboBox):
                        control.setCurrentIndex(control.findData(value))
                    else:
                        control.setText(value)
                result = page.evaluate()
                self.assertEqual(result.ui_conclusion, "1级")
                self.assertFalse(page.explanation.text())
                history = RecordsPage(create_pump_analysis_service(paths=paths))
                text = history.show_record(page.last_saved_record_id)
                self.assertIn("1级", text)
                self.assertIn("有效机组比功率", history.inputs_detail.text())
                page.field_inputs["specific_power_kw_per_m3_min"].setText("0")
                self.assertIsNone(page.evaluate())
                self.assertNotEqual(page.conclusion.text(), "1级")
                device = DeviceAnalysisPage(QWidget(), QWidget(), motor_page=None, compressor_page=page)
                self.assertTrue(device.select_standard("GB 19153-2019"))
                self.assertIs(device.pages.currentWidget(), page)
                page.category.setCurrentIndex(page.category.findData("portable_lubricated"))
                self.assertIn("rated_input_power_kw", page.field_inputs)
                self.assertNotIn("cooling_method", page.field_inputs)
                self.assertNotIn("rated_motor_output_power_kw", page.field_inputs)
            finally:
                _dispose_widget(history)
                _dispose_widget(device if device else page)


if __name__ == "__main__":
    unittest.main()
