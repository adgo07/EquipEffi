"""V6.5 derivation, compatibility, same-kernel batch and row evidence."""
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import tempfile
from time import monotonic
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

from openpyxl import load_workbook

from equipeffi.application.services.motor_analysis_service import MotorAnalysisRequest
from equipeffi.composition import create_batch_evaluation_service, create_records_runtime
from equipeffi.domain.devices.motor_pmsm.calculator import ISSUE_003
from equipeffi.domain.devices.motor_pmsm.input_contract import BRANCHES, STANDARD_CODE
from equipeffi.infrastructure.excel.ooxml_reader import OOXMLWorkbook
from equipeffi.infrastructure.excel.template_resource import (
    V62MotorTemplateResource, V63MotorTemplateResource, V64MotorTemplateResource, V65MotorTemplateResource,
    V64_TEMPLATE_ENTRY, V65_TEMPLATE_ENTRY, validate_v6_template,
)
from equipeffi.infrastructure.excel.unified_workbook_reader import MotorWorkbookReader
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from tools.build_v61_transformer_template import _sheet_table_target

BASE = {"D": 1, "F": "gb30253_lv_vfd", "G": "0380.00", "J": "0.65", "L": "550.0", "M": "82.125"}


def fill(sheet, row=4, **changes):
    for column, value in (BASE | changes).items():
        sheet[f"{column}{row}"] = value


def motor_summary(summary):
    return next(sheet for sheet in summary["sheets"] if sheet["sheet_id"] == "motor")


class PmsmExcelTests(unittest.TestCase):
    def test_pinned_v64_and_unrelated_parts_are_preserved(self):
        old, current = V64MotorTemplateResource(), V65MotorTemplateResource()
        self.assertEqual(sha256(old.template_path.read_bytes()).hexdigest().upper(), V64_TEMPLATE_ENTRY["asset_sha256"])
        self.assertEqual(sha256(current.template_path.read_bytes()).hexdigest().upper(), V65_TEMPLATE_ENTRY["asset_sha256"])
        self.assertTrue(old.validate().is_valid)
        self.assertTrue(current.validate().is_valid)
        with OOXMLWorkbook(old.template_path) as before, OOXMLWorkbook(current.template_path) as after:
            self.assertEqual(before.sheet_names, after.sheet_names)
            self.assertEqual(before.archive.namelist(), after.archive.namelist())
            allowed = {before._sheets[name] for name in ("电动机", "配置", "注意事项", "模板说明")}
            allowed |= {"xl/workbook.xml", _sheet_table_target(before.archive, before._sheets["电动机"], "TblMotor")}
            self.assertEqual({name for name in before.archive.namelist()
                              if before.archive.read(name) != after.archive.read(name)}, allowed)
            before_cells, after_cells = [
                {cell.get("r"): ET.tostring(cell) for cell in ET.fromstring(
                    book.archive.read(book._sheets["配置"])).iter()
                 if cell.tag.endswith("}c")}
                for book in (before, after)
            ]
            owned = {f"{column}{row}" for column in ("EW", "EX", "FA", "FB", "FC", "FD") for row in range(2, 16)}
            owned |= {"FB1", "FC1", "FD1"}
            for address in before_cells.keys() | after_cells.keys():
                if address not in owned:
                    self.assertEqual(before_cells.get(address), after_cells.get(address), address)

    def test_old_connected_contracts_reject_pmsm_id_and_label(self):
        with tempfile.TemporaryDirectory() as directory:
            for resource in (V62MotorTemplateResource(), V63MotorTemplateResource(), V64MotorTemplateResource()):
                with self.subTest(version=resource.identity["template_version"]):
                    path = Path(directory) / resource.identity["filename"]
                    resource.download_to(path)
                    workbook = load_workbook(path)
                    fill(workbook["电动机"])
                    fill(workbook["电动机"], 5, F=BRANCHES[BASE["F"]].category.label)
                    workbook.save(path)
                    workbook.close()
                    rows = MotorWorkbookReader().read(path).rows
                    self.assertEqual(len(rows), 2)
                    self.assertTrue(all("永磁电动机类别需要V6.5模板" in row.input_errors[0] for row in rows))

    def test_reject_changed_config_header_and_formula_result_region(self):
        with tempfile.TemporaryDirectory() as directory:
            for index, (sheet, address, change) in enumerate((
                ("配置", "FC12", "max_nameplate_speed_rpm"),
                ("电动机", "L3", "铭牌标称最高转速\n(r/min)"),
                ("电动机", "N104", "=98"),
            )):
                source = Path(directory) / f"bad-{index}.xlsx"
                V65MotorTemplateResource().download_to(source)
                workbook = load_workbook(source)
                workbook[sheet][address] = change
                workbook.save(source)
                workbook.close()
                self.assertFalse(validate_v6_template(source).is_valid, (sheet, address, change))

    def test_mixed_three_standards_and_row_evidence_are_immutable(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = AppDataPaths(Path(directory) / "data")
            service = create_batch_evaluation_service(paths=paths)
            source = Path(directory) / "mixed.xlsx"
            service.template_resource.download_to(source)
            workbook = load_workbook(source)
            motor = workbook["电动机"]
            fill(motor, H="60", K="12", I="IC01")
            fill(motor, 5, M="82.12499999")
            fill(motor, 6, F="gb30254_cage_induction", G="3000", H="50", I="IC01", J="200", K="2", L=None, M="94")
            fill(motor, 7, F="three_phase_induction", G="380", H="50", I=None, J="0.14", K="4", L=None, M="71.43")
            fill(motor, 8, M="0.82125")
            fill(motor, 9, L=None)
            fill(motor, 10, F="unknown")
            fill(motor, 11, M="=82.125")
            workbook.save(source)
            workbook.close()

            digest = sha256(source.read_bytes()).hexdigest()
            result = service.evaluate_workbook(source)
            self.assertEqual(sha256(source.read_bytes()).hexdigest(), digest)
            self.assertEqual(result.batch_record_error, "")
            self.assertEqual(result.summary.conclusion_rows, {"1级": 2, "2级": 1, "3级": 1, "无法判定": 1})
            self.assertEqual(result.summary.input_error_rows, 3)
            self.assertEqual(result.summary.execution_error_rows, 0)
            saved = service.batch_repository.load_batch_record(result.batch_record_id)
            self.assertEqual((saved.standard_code, saved.device_type), ("MULTI", "MULTI"))
            self.assertEqual(len(service.batch_repository.list_batch_records()), 1)
            self.assertEqual(create_records_runtime(paths=paths)[1].list_records(), [])
            report = motor_summary(saved.summary)
            references = {item["standard_code"]: item for item in report["evaluation_provenance"]}
            self.assertEqual(set(references), {STANDARD_CODE, "GB 30254-2024", "GB 18613-2020"})
            evidence = {row["row"]: row for row in saved.summary["motor_pmsm_row_evidence"]}
            self.assertEqual(set(evidence), {4, 5, 8, 9, 11})
            first = evidence[4]
            self.assertEqual(first["pack_sha256"], references[STANDARD_CODE]["pack_sha256"])
            self.assertEqual(first["raw_input"]["rated_voltage_v"], "0380.00")
            self.assertEqual(first["raw_input"]["rated_speed_rpm"], "550.0")
            self.assertEqual(first["input_units"]["rated_speed_rpm"], "r/min")
            self.assertNotIn("poles", first["raw_input"])
            self.assertNotIn("cooling_method", first["raw_input"])
            self.assertEqual(first["thresholds"]["grade_1"]["exact"], {
                "numerator": "657", "denominator": "8", "unit": "percent_point"})
            self.assertEqual(first["standard_issues"][ISSUE_003], "PROVISIONAL")
            self.assertEqual({cell["source_cell"] for cell in first["grade_lookups"]["grade_1"]["source_cells"]},
                             {"E7", "F7", "E8", "F8"})
            self.assertEqual(evidence[9]["evaluation_status"], "INSUFFICIENT_DATA")
            for row in (8, 11):
                self.assertEqual(evidence[row]["evaluation_status"], "INVALID_INPUT")
                self.assertNotIn("grade_lookups", evidence[row])
            with patch.object(service.motor, "evaluate", side_effect=AssertionError("history recalculated")):
                self.assertEqual(service.batch_repository.load_batch_record(result.batch_record_id).summary, saved.summary)
            with closing(sqlite3.connect(paths.records_db)) as connection:
                stored_before = connection.execute("SELECT summary_json FROM batch_record WHERE batch_record_id=?",
                                                   (saved.batch_record_id,)).fetchone()[0]
            listed = service.batch_repository.list_batch_records(keyword="mixed")
            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0].summary, {key: value for key, value in saved.summary.items()
                                               if key != "motor_pmsm_row_evidence"})
            with closing(sqlite3.connect(paths.records_db)) as connection:
                stored_after = connection.execute("SELECT summary_json FROM batch_record WHERE batch_record_id=?",
                                                  (saved.batch_record_id,)).fetchone()[0]
            self.assertEqual(stored_after, stored_before)
            self.assertEqual(service.batch_repository.load_batch_record(saved.batch_record_id).summary, saved.summary)
            single = service.motor.evaluate(MotorAnalysisRequest(first["raw_input"]))
            self.assertEqual(single.thresholds["grade_1"]["exact"], first["thresholds"]["grade_1"]["exact"])

            output = load_workbook(result.result_workbook, data_only=True)
            try:
                self.assertEqual(output["电动机"]["N4"].value, 82.13)
                self.assertEqual(output["电动机"]["M4"].value, "82.125")
                self.assertEqual(output["电动机"]["Q5"].value, "2级")
                self.assertIn(output["电动机"]["Q11"].value, (None, ""))
                self.assertIn("输入错误", output["电动机"]["T11"].value)
                self.assertIn("临时解释", output["电动机"]["T4"].value)
            finally:
                output.close()

    def test_capacity_1_100_1000_10000_and_persisted_bytes(self):
        measurements = []
        with tempfile.TemporaryDirectory() as directory:
            paths = AppDataPaths(Path(directory) / "data")
            service = create_batch_evaluation_service(paths=paths)
            for count in (1, 100, 1000, 10000):
                source = Path(directory) / f"pmsm-{count}.xlsx"
                service.template_resource.download_to(source)
                workbook = load_workbook(source)
                for number in range(4, count + 4):
                    # Unique lexical inputs prevent a repeated-row provenance shortcut.
                    fill(workbook["电动机"], number, J=f"0.6{number:05d}", L=f"550.{number:05d}", M="100")
                workbook.save(source)
                workbook.close()
                started = monotonic()
                result = service.evaluate_workbook(source)
                elapsed = monotonic() - started
                self.assertEqual(result.summary.conclusion_rows, {"1级": count})
                self.assertEqual(result.batch_record_error, "")
                saved = service.batch_repository.load_batch_record(result.batch_record_id)
                self.assertEqual((saved.standard_code, saved.device_type), (STANDARD_CODE, "motor_pmsm"))
                motor = motor_summary(saved.summary)
                self.assertEqual(len(motor["evaluation_provenance"]), 1)
                evidence = saved.summary["motor_pmsm_row_evidence"]
                self.assertEqual(len(evidence), count)
                self.assertEqual(evidence[-1]["row"], count + 3)
                with closing(sqlite3.connect(paths.records_db)) as connection:
                    size = connection.execute("SELECT length(CAST(summary_json AS BLOB)) FROM batch_record WHERE batch_record_id=?",
                                              (saved.batch_record_id,)).fetchone()[0]
                measurements.append({"rows": count, "seconds": round(elapsed, 3), "record_json_bytes": size})
            recent = service.batch_repository.list_batch_records()
            self.assertEqual(len(recent), 4)
            self.assertTrue(all("motor_pmsm_row_evidence" not in row.summary for row in recent))
            self.assertEqual(create_records_runtime(paths=paths)[1].list_records(), [])
        print("PMSM_V65_CAPACITY " + json.dumps(measurements))
