from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from datetime import date

from equipeffi.application.services.motor_analysis_service import (
    MotorAnalysisRequest,
    MotorAnalysisService,
    get_motor_input_contract,
)
from equipeffi.application.services.motor_basis_formatter import format_motor_basis_lines
from equipeffi.domain.devices.motor.calculator import Gb18613MotorCalculator
from equipeffi.infrastructure.standards.motor_repository import load_motor_pack


class _Records:
    def __init__(self):
        self.records = []

    def append_record(self, record):
        self.records.append(record)


class MotorAnalysisServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack, cls.digest = load_motor_pack()

    def service(self, records=None, calculator=None):
        return MotorAnalysisService(
            self.pack,
            calculator or Gb18613MotorCalculator(),
            records=records,
            pack_sha256=self.digest,
            app_version="test",
        )

    @staticmethod
    def table1_values(**overrides):
        values = {
            "category_id": "three_phase_induction",
            "rated_output_power_kw": "0.14",
            "rated_voltage_kv": "0.38",
            "rated_frequency_hz": "50",
            "poles": "4",
            "measured_efficiency_pct": "71.43",
        }
        return values | overrides

    def test_real_pack_service_keeps_structured_exact_threshold_and_actual_trace(self):
        result = self.service().evaluate(MotorAnalysisRequest(self.table1_values()))
        self.assertEqual((result.evaluation_status, result.grade, result.ui_conclusion),
                         ("SUCCESS", "3", "3级"))
        grade2 = result.thresholds["grade_2"]
        self.assertEqual(grade2["state"], "AVAILABLE")
        self.assertEqual(grade2["exact"], {
            "numerator": "2143", "denominator": "30", "unit": "percent_point"})
        self.assertEqual(grade2["display_text"], "71.43")
        self.assertEqual(result.as_snapshot()["thresholds"]["grade_2"], grade2)
        self.assertEqual(result.thresholds_display["grade_2"], "71.43")
        self.assertEqual(result.raw_values["efficiency_basis_status"], "AS_DECLARED_BY_FIELD")
        self.assertEqual(result.raw_values["efficiency_basis_raw"], "")
        self.assertEqual(result.trace[0]["power_endpoints"], [
            {"power_w": "120", "source_power_text": "0.12", "source_unit": "kW",
             "source_row_id": "GB18613-T01-R006"},
            {"power_w": "180", "source_power_text": "0.18", "source_unit": "kW",
             "source_row_id": "GB18613-T01-R007"},
        ])
        lines = format_motor_basis_lines(result.trace)
        self.assertEqual(lines, (
            "查表依据：表1；4极；额定功率0.14 kW按0.12～0.18 kW线性插值；来源表1第6、7行。",
        ))

    def test_record_snapshot_keeps_basis_distinctions_required_test_basis_and_note(self):
        records = _Records()
        service = self.service(records)
        values = self.table1_values(
            efficiency_basis_status="USER_DECLARED",
            efficiency_basis_raw="用户选择：按上述试验口径填报",
            user_note="用户备注保留",
        )
        outcome = service.analyze_and_record(
            MotorAnalysisRequest(values, as_of=date(2026, 10, 25)))
        self.assertEqual(outcome.record_status, "SAVED")
        self.assertEqual(len(records.records), 1)
        record = records.records[0]
        self.assertEqual(record.input_snapshot["efficiency_basis_status"], "USER_DECLARED")
        self.assertEqual(record.input_snapshot["efficiency_basis_raw"], "用户选择：按上述试验口径填报")
        self.assertEqual(record.input_snapshot["user_note"], "用户备注保留")
        self.assertEqual(record.as_of, "2026-10-25")
        self.assertIn("request_fingerprint", record.input_snapshot)
        basis = record.reference_snapshot["required_test_basis"]
        self.assertEqual(basis["source_standard"], "GB 18613-2020")
        self.assertEqual(basis["source_clause"], "第6章")
        self.assertEqual(basis["method"], "GB/T 1032 B法（测量输入—输出功率的损耗分析法）")
        self.assertNotIn("report_verified", basis)
        self.assertEqual(record.result_snapshot["thresholds"]["grade_2"]["exact"]["numerator"], "2143")
        self.assertEqual(record.canonical_package_hash, self.digest)

    def test_direct_lookup_formatter_accepts_real_trace_mapping(self):
        result = self.service().evaluate(MotorAnalysisRequest(
            self.table1_values(rated_output_power_kw="0.12")))
        self.assertEqual(result.trace[0]["method"], "DIRECT")
        expected = ("查表依据：表1；4极；额定功率0.12 kW直接查表；来源表1第6行。",)
        self.assertEqual(format_motor_basis_lines(result.trace), expected)
        self.assertEqual(format_motor_basis_lines(result.trace[0]), expected)

    def test_300kw_six_pole_interpolation_formats_the_actual_source_interval(self):
        values = self.table1_values(
            rated_output_power_kw="300", poles="6", measured_efficiency_pct="96.58")
        result = self.service().evaluate(MotorAnalysisRequest(values))
        self.assertEqual(result.evaluation_status, "SUCCESS")
        self.assertEqual(result.trace[0]["power_endpoints"][1]["source_power_text"], "315~1000")
        self.assertIn("250～315 kW线性插值", format_motor_basis_lines(result.trace)[0])
        self.assertIs(get_motor_input_contract(), self.service().input_contract)

    def test_table6_basis_formatter_uses_speed_label_not_internal_branch_key(self):
        values = {
            "category_id": "ac_fan_brushless_dc",
            "rated_output_power_kw": "0.01",
            "max_nameplate_speed_rpm": "500",
            "measured_efficiency_pct": "60",
        }
        result = self.service().evaluate(MotorAnalysisRequest(values))
        self.assertEqual(result.trace[0]["speed_band"], "rpm_band_1")
        self.assertEqual(result.trace[0]["speed_band_label"], "0<r≤500 r/min")
        line = format_motor_basis_lines(result.trace)[0]
        self.assertIn("表6", line)
        self.assertIn("最高转速档0<r≤500 r/min", line)
        self.assertNotIn("rpm_band_1", line)
        self.assertIn("来源表6第6行", line)

    def test_invalid_input_never_creates_a_record_and_execution_errors_propagate(self):
        records = _Records()
        invalid = self.service(records).analyze_and_record(
            MotorAnalysisRequest(self.table1_values(measured_efficiency_pct="0.85")))
        self.assertEqual(invalid.result.evaluation_status, "INVALID_INPUT")
        self.assertNotEqual(invalid.record_status, "SAVED")
        self.assertEqual(records.records, [])

        class FailedCalculator:
            calculator_version = "test-failed"

            def evaluate(self, values, pack):
                raise RuntimeError("calculation failure")

        with self.assertRaisesRegex(RuntimeError, "calculation failure"):
            self.service(calculator=FailedCalculator()).evaluate(
                MotorAnalysisRequest(self.table1_values()))

    def test_repository_rejects_tampered_pack_integrity(self):
        altered = dict(self.pack)
        altered["standard_name"] = "tampered"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tampered.json"
            path.write_text(json.dumps(altered, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "完整性校验失败"):
                load_motor_pack(path)


if __name__ == "__main__":
    unittest.main()
