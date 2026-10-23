"""变压器应用边界：精确快照、独立留档、异常与业务终态分离。"""
import unittest
from decimal import Decimal
from types import SimpleNamespace

from equipeffi.application.services.transformer_analysis_service import (
    TransformerAnalysisRequest, TransformerAnalysisService,
)


class Calculator:
    def __init__(self, status="SUCCESS"):
        self.status = status

    def evaluate(self, values, pack):
        return SimpleNamespace(
            evaluation_status=self.status, grade="1", ui_conclusion="1级",
            thresholds={"no_load_loss_1": Decimal("422.50000000001")},
            explanation="测试夹具，仅验证应用生命周期，不作为业务Golden",
            missing_fields=(), trace=({"source": "fixture"},))


class Records:
    def __init__(self):
        self.items = []

    def append_record(self, record):
        self.items.append(record)


class TransformerApplicationTests(unittest.TestCase):
    def test_real_frozen_table03_result_can_be_saved_as_json(self):
        import json
        import tempfile
        from pathlib import Path
        from equipeffi.composition import create_transformer_analysis_service
        from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
        # 冻结表03，3150kVA：一级P0=1.7kW、Pk=20.7kW，输入契约为W。
        with tempfile.TemporaryDirectory() as directory:
            service = create_transformer_analysis_service(paths=AppDataPaths(Path(directory)))
            outcome = service.analyze_and_record(TransformerAnalysisRequest({
                "category_id": "GB20052-T03", "category": "", "capacity_kva": "3150",
                "no_load_loss_w": "1700", "load_loss_w": "20700"}))
            self.assertEqual(outcome.result.ui_conclusion, "1级")
            self.assertEqual(outcome.record_status, "SAVED", outcome.record_error)
            self.assertEqual(outcome.result.thresholds["no_load_loss_1"], Decimal("1700"))
            self.assertTrue(outcome.record.result_snapshot["trace"])
            self.assertIn("35kV", outcome.record.product_category)
            json.dumps(outcome.record.result_snapshot)

    def test_each_analysis_saves_new_immutable_exact_snapshot(self):
        records = Records()
        service = TransformerAnalysisService(
            {"mapping_revision": "V2.1"}, Calculator(), records=records,
            pack_sha256="source-hash")
        values = {"category": "示例", "no_load_loss_w": Decimal("422.50000000001")}
        request = TransformerAnalysisRequest(values)
        first = service.analyze_and_record(request)
        second = service.analyze_and_record(request)
        values["no_load_loss_w"] = Decimal("999")
        self.assertEqual(first.record_status, "SAVED")
        self.assertNotEqual(first.record.record_id, second.record.record_id)
        self.assertEqual(len(records.items), 2)
        self.assertEqual(first.record.input_snapshot["no_load_loss_w"], "422.50000000001")
        self.assertEqual(first.record.result_snapshot["thresholds"]["no_load_loss_1"],
                         "422.50000000001")
        self.assertEqual(first.record.canonical_package_hash, "source-hash")

    def test_invalid_or_unconfirmed_category_does_not_save(self):
        for status in ("INVALID_INPUT", None):
            with self.subTest(status=status):
                records = Records()
                service = TransformerAnalysisService({}, Calculator(status), records=records)
                outcome = service.analyze_and_record(TransformerAnalysisRequest({}))
                self.assertEqual(outcome.record_status, "NOT_ELIGIBLE")
                self.assertEqual(records.items, [])

    def test_execution_error_is_not_business_outcome(self):
        class Broken:
            def evaluate(self, values, pack):
                raise RuntimeError("损坏的标准包")
        records = Records()
        service = TransformerAnalysisService({}, Broken(), records=records)
        with self.assertRaisesRegex(RuntimeError, "损坏"):
            service.analyze_and_record(TransformerAnalysisRequest({}))
        self.assertEqual(records.items, [])

    def test_persistence_failure_does_not_hide_computed_result(self):
        class BrokenRecords:
            def append_record(self, record):
                raise OSError("readonly")
        service = TransformerAnalysisService({}, Calculator(), records=BrokenRecords())
        outcome = service.analyze_and_record(TransformerAnalysisRequest({}))
        self.assertEqual(outcome.record_status, "SAVE_FAILED")
        self.assertIsNone(outcome.record)
        self.assertIn("readonly", outcome.record_error)
        self.assertEqual(outcome.result.grade, "1")


if __name__ == "__main__":
    unittest.main()
