"""多Sheet编排和记录兼容；不将测试夹具当作变压器业务真值。"""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from equipeffi.application.ports.batch_workbook import BatchSourceRow, BatchSourceWorkbook
from equipeffi.application.ports.unified_workbook import UnifiedSourceWorkbook
from equipeffi.application.services.workbook_evaluation_service import WorkbookEvaluationService
from equipeffi.composition import create_pump_analysis_service


class Transformer:
    def evaluate(self, request):
        if request.values.get("category") == "crash":
            raise RuntimeError("fixture")
        return SimpleNamespace(evaluation_status="SUCCESS", grade="1", ui_conclusion="1级",
                               thresholds={"no_load_loss_1": "10"},
                               explanation="fixture", trace=("fixture",),
                               references={"numeric_profile_id": "fixture"})


class Writer:
    def __init__(self):
        self.calls = []

    def default_destination(self, source):
        return source.with_name("result.xlsx")

    def write(self, source, outcomes, destination):
        self.calls.append(outcomes)
        destination.write_bytes(b"result fixture")
        return destination


class Records:
    def __init__(self):
        self.items = []

    def append_batch_record(self, record):
        self.items.append(record)


class UnifiedWorkbookApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "source.xlsx"
        self.source.write_bytes(b"source fixture")
        self.writer = Writer()
        self.records = Records()

    def service(self, transformer_values, *, unprocessed=()):
        source = UnifiedSourceWorkbook(str(self.source), {
            "离心泵": BatchSourceWorkbook(str(self.source), (
                BatchSourceRow(6, {"category": "其他类别", "quantity": "2"}),)),
            "变压器": BatchSourceWorkbook(str(self.source), (
                BatchSourceRow(6, transformer_values),)),
        }, template_identity={"template_version": "V6.1"},
            unprocessed_sheets=unprocessed)
        reader = SimpleNamespace(read=lambda path: source)
        return WorkbookEvaluationService(
            create_pump_analysis_service(with_persistence=False), Transformer(),
            reader=reader, writer=self.writer, batch_repository=self.records)

    def test_same_row_on_two_sheets_is_not_overwritten_and_one_record(self):
        result = self.service({"quantity": "3"}).evaluate_workbook(self.source)
        self.assertEqual(len(self.writer.calls), 1)
        written = self.writer.calls[0]
        self.assertEqual(written["离心泵"][6].conclusion, "不在范围")
        self.assertEqual(written["变压器"][6].conclusion, "1级")
        self.assertEqual(result.summary.total_quantity, 5)
        self.assertEqual(result.summary.data_row_count, 2)
        self.assertEqual(result.records_created, 0)
        self.assertEqual(len(self.records.items), 1)
        record = self.records.items[0]
        self.assertEqual(record.standard_code, "MULTI")
        self.assertEqual(record.schema_version, 4)
        self.assertEqual(record.summary["schema_version"], 2)
        self.assertEqual(len(record.summary["sheets"]), 2)
        self.assertEqual(self.source.read_bytes(), b"source fixture")

    def test_execution_error_has_sheet_identity_and_does_not_abort_pump(self):
        result = self.service({"quantity": "3", "category": "crash"}).evaluate_workbook(self.source)
        self.assertEqual(result.summary.execution_error_rows, 1)
        self.assertEqual(result.summary.evaluated_quantity, 2)
        issue = result.summary.issues[0]
        self.assertEqual(issue.sheet_name, "变压器")
        self.assertEqual(issue.row_number, 6)
        self.assertTrue(self.writer.calls[0]["变压器"][6].is_execution_error)

    def test_invalid_quantity_is_not_defaulted(self):
        result = self.service({"quantity": ""}).evaluate_workbook(self.source)
        self.assertEqual(result.summary.total_quantity, 2)
        self.assertEqual(result.summary.input_error_rows, 1)
        self.assertEqual(result.summary.evaluated_quantity, 2)

    def test_preserved_unprocessed_sheet_is_recorded(self):
        result = self.service({"quantity": "1"}, unprocessed=("电动机",)).evaluate_workbook(self.source)
        self.assertEqual(result.summary.unprocessed_sheets, ("电动机",))
        self.assertEqual(self.records.items[0].summary["unprocessed_sheets"], ["电动机"])

    def test_writer_failure_never_persists_completed_batch(self):
        service = self.service({"quantity": "1"})
        def fail(*args):
            raise OSError("disk full")
        self.writer.write = fail
        with self.assertRaisesRegex(OSError, "disk full"):
            service.evaluate_workbook(self.source)
        self.assertEqual(self.records.items, [])

    def test_existing_sqlite_schema_round_trips_mixed_batch_without_row_records(self):
        import sqlite3
        from contextlib import closing
        from equipeffi.composition import create_records_runtime
        from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
        from equipeffi.infrastructure.persistence.sqlite_batch_record_repository import SqliteBatchRecordRepository
        paths = AppDataPaths(Path(self.temp.name) / "data")
        create_records_runtime(paths=paths)
        repository = SqliteBatchRecordRepository(paths.records_db)
        service = self.service({"quantity": "3"})
        service.batch_repository = repository
        result = service.evaluate_workbook(self.source)
        self.assertEqual(result.batch_record_error, "")
        stored = repository.load_batch_record(result.batch_record_id)
        self.assertEqual(stored.standard_code, "MULTI")
        self.assertEqual(stored.summary["sheets"][0]["device_type"], "离心泵")
        with closing(sqlite3.connect(paths.records_db)) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM batch_record").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT count(*) FROM record").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
