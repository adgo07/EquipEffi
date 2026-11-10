"""V6.4 lossless adapter, protected parts and batch-record boundaries."""
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import time
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED
from openpyxl import load_workbook
from equipeffi.composition import create_batch_evaluation_service, create_records_runtime
from equipeffi.infrastructure.excel.template_resource import (
    V64MotorTemplateResource, V63MotorTemplateResource, V64_TEMPLATE_ENTRY, V63_TEMPLATE_ENTRY,
    validate_v6_template, _workbook_defined_names)
from equipeffi.infrastructure.excel.ooxml_reader import OOXMLWorkbook
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.domain.devices.motor_hv.input_contract import HV_CATEGORY


def fill(sheet, row=4, **overrides):
    for col, value in (dict(D=1, F=HV_CATEGORY.label, G="3000", H="50", I="IC01", J="211", K="2", M="94.055") | overrides).items():
        sheet[f"{col}{row}"] = value


class HvExcelTests(unittest.TestCase):
    def test_pinned_old_assets_and_unrelated_zip_parts_unchanged(self):
        current, old = V64MotorTemplateResource(), V63MotorTemplateResource()
        self.assertTrue(current.validate().is_valid)
        self.assertEqual(sha256(old.template_path.read_bytes()).hexdigest().upper(), V63_TEMPLATE_ENTRY["asset_sha256"])
        with OOXMLWorkbook(old.template_path) as before, OOXMLWorkbook(current.template_path) as after:
            self.assertEqual(before.sheet_names, after.sheet_names)
            allowed = {before._sheets[s] for s in ("电动机", "配置", "注意事项", "模板说明")} | {"xl/workbook.xml", "xl/tables/table2.xml"}
            changed = {name for name in before.archive.namelist() if before.archive.read(name) != after.archive.read(name)}
            # The motor table target is discovered rather than assumed.
            self.assertEqual(len(changed - {n for n in changed if n.startswith("xl/tables/")}), 5)
            for name in changed:
                self.assertTrue(name in allowed or name.startswith("xl/tables/"), name)
            for sheet in ("离心泵", "变压器"):
                self.assertEqual(before.archive.read(before._sheets[sheet]), after.archive.read(after._sheets[sheet]))

    def test_hidden_contract_and_output_formula_negative_cases(self):
        ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"bad.xlsx"
            V64MotorTemplateResource().download_to(path)
            workbook = load_workbook(path)
            workbook["电动机"]["N10"] = "=94"
            workbook.save(path); workbook.close()
            self.assertFalse(validate_v6_template(path).is_valid)
            V64MotorTemplateResource().download_to(path)
            workbook = load_workbook(path)
            workbook.defined_names["EQUIPEFFI_SHEET_CONTRACT_motor"].attr_text = '"motor-input.v99"' if "EQUIPEFFI_SHEET_CONTRACT_motor" in workbook.defined_names else '"motor-input.v99"'
            workbook.save(path); workbook.close()
            self.assertFalse(validate_v6_template(path).is_valid)

    def test_same_kernel_batch_identity_and_input_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = AppDataPaths(Path(directory)/"data")
            batch = create_batch_evaluation_service(paths=paths)
            path = Path(directory)/"input.xlsx"
            batch.template_resource.download_to(path)
            workbook = load_workbook(path)
            fill(workbook["电动机"])
            fill(workbook["电动机"], 5, M="94.054999")
            workbook.save(path); workbook.close()
            before = sha256(path.read_bytes()).hexdigest()
            result = batch.evaluate_workbook(path)
            self.assertEqual(sha256(path.read_bytes()).hexdigest(), before)
            self.assertEqual(result.summary.conclusion_rows, {"1级": 1, "2级": 1})
            saved = batch.batch_repository.load_batch_record(result.batch_record_id)
            self.assertEqual((saved.standard_code, saved.device_type), ("GB 30254-2024", "motor_hv"))
            self.assertEqual(len(batch.batch_repository.list_batch_records()), 1)
            self.assertEqual(create_records_runtime(paths=paths)[1].list_records(), [])
            refs = next(s for s in saved.summary["sheets"] if s["sheet_name"] == "电动机")["evaluation_provenance"]
            self.assertEqual(refs[0]["numeric_profile_id"], "EQUIPEFFI_MOTOR_HV_EXACT_LINEAR_V1")
            output = load_workbook(result.result_workbook, data_only=True)
            self.assertEqual(output["电动机"]["N4"].value, 94.06)
            self.assertEqual(output["电动机"]["Q5"].value, "2级")
            self.assertEqual(output["电动机"]["M4"].value, "94.055")
            output.close()

    def test_mixed_devices_and_standards_and_bad_category_are_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = AppDataPaths(Path(directory)/"data")
            batch = create_batch_evaluation_service(paths=paths)
            path = Path(directory)/"mixed.xlsx"
            batch.template_resource.download_to(path)
            workbook = load_workbook(path)
            fill(workbook["电动机"])
            fill(workbook["电动机"], 5, F="三相异步电动机（一般用途或一般用途防爆）", G="380", I="", J="0.14", K="4", M="71.43")
            fill(workbook["电动机"], 6, F="未知电动机类别")
            for name in ("离心泵", "变压器"):
                workbook[name]["D4"] = 1; workbook[name]["F4"] = "其他类别"
            workbook.save(path); workbook.close()
            result = batch.evaluate_workbook(path)
            self.assertEqual(result.summary.input_error_rows, 1)
            motor = next(s for s in result.summary.sheets if s["sheet_name"] == "电动机")
            self.assertEqual(motor["standard_code"], "MULTI")
            self.assertEqual({r["standard_code"] for r in motor["evaluation_provenance"]}, {"GB 30254-2024", "GB 18613-2020"})
            self.assertEqual(batch.batch_repository.load_batch_record(result.batch_record_id).standard_code, "MULTI")

    def test_capacity_1_100_1000_10000(self):
        measurements = []
        with tempfile.TemporaryDirectory() as directory:
            paths = AppDataPaths(Path(directory)/"data")
            batch = create_batch_evaluation_service(paths=paths)
            for count in (1, 100, 1000, 10000):
                path = Path(directory)/f"capacity-{count}.xlsx"
                batch.template_resource.download_to(path)
                workbook = load_workbook(path)
                for number in range(4, count+4): fill(workbook["电动机"], number)
                workbook.save(path); workbook.close()
                started = time.monotonic()
                result = batch.evaluate_workbook(path)
                self.assertEqual(result.summary.concluded_rows, count)
                self.assertEqual(result.summary.conclusion_rows, {"1级": count})
                self.assertEqual(result.summary.execution_error_rows, 0)
                self.assertEqual(result.batch_record_error, "")
                measurements.append(dict(rows=count, seconds=round(time.monotonic()-started, 3)))
            self.assertEqual(len(batch.batch_repository.list_batch_records()), 4)
            self.assertEqual(create_records_runtime(paths=paths)[1].list_records(), [])
        print("HV_V64_CAPACITY " + json.dumps(measurements))

    def test_old_contract_rejects_new_high_voltage_id_and_label(self):
        from equipeffi.infrastructure.excel.template_resource import V62MotorTemplateResource
        from equipeffi.infrastructure.excel.unified_workbook_reader import MotorWorkbookReader
        with tempfile.TemporaryDirectory() as directory:
            for resource in (V62MotorTemplateResource(), V63MotorTemplateResource()):
                path = Path(directory)/"old.xlsx"
                resource.download_to(path)
                workbook = load_workbook(path)
                fill(workbook["电动机"], I="", F=HV_CATEGORY.category_id)
                fill(workbook["电动机"], 5, I="", F=HV_CATEGORY.label)
                workbook.save(path); workbook.close()
                rows = MotorWorkbookReader().read(path).rows
                self.assertEqual(len(rows), 2)
                self.assertTrue(all(row.input_errors for row in rows))

    def test_requested_standard_identity_survives_all_or_partial_input_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = AppDataPaths(Path(directory)/"data")
            batch = create_batch_evaluation_service(paths=paths)
            for mixed in (False, True):
                path = Path(directory)/f"failed-{mixed}.xlsx"
                batch.template_resource.download_to(path)
                workbook = load_workbook(path)
                fill(workbook["电动机"], M="NaN")
                if mixed:
                    fill(workbook["电动机"], 5, F="三相异步电动机（一般用途或一般用途防爆）", G="380", I="", J="0.14", K="4", M="71.43")
                workbook.save(path); workbook.close()
                result = batch.evaluate_workbook(path)
                saved = batch.batch_repository.load_batch_record(result.batch_record_id)
                self.assertEqual(saved.standard_code, "MULTI" if mixed else "GB 30254-2024")
                self.assertEqual(saved.device_type, "MULTI" if mixed else "motor_hv")
                self.assertEqual(result.summary.input_error_rows, 1)


if __name__ == "__main__": unittest.main()
