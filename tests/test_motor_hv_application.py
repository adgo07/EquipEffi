"""Product Application evidence derived from A.3 C01/C06/C08-C27."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import unittest
from equipeffi.composition import create_motor_analysis_service
from equipeffi.application.services.motor_analysis_service import MotorAnalysisRequest
from equipeffi.application.services.motor_product_service import HV_STANDARD
from equipeffi.domain.devices.motor_hv.calculator import HvPackError


def values(**overrides):
    return dict(category_id="gb30254_cage_induction", rated_voltage_v="3000",
        rated_frequency_hz="50", cooling_method="IC01", rated_output_power_kw="200",
        poles="2", rated_efficiency_pct="94.0") | overrides


class Records:
    def __init__(self):
        self.records = []
    def append_record(self, record):
        self.records.append(record)


class HvApplicationTests(unittest.TestCase):
    def setUp(self):
        self.service = create_motor_analysis_service(with_persistence=False)

    def test_six_explicit_table_routes_and_mapping_thresholds(self):
        for voltage, cooling, thresholds in (
            ("3000", "IC01", ("94.0", "93.1", "92.3")),
            ("10000", "IC01", ("93.7", "92.8", "92.0")),
            ("6000", "IC611", ("93.4", "92.6", "91.7")),
            ("10000", "IC611", ("93.1", "92.3", "91.5")),
            ("3300", "IC411", ("94.4", "93.5", "92.7")),
            ("10000", "IC411", ("94.1", "93.2", "92.4")),
        ):
            with self.subTest(voltage=voltage, cooling=cooling):
                result = self.service.evaluate(MotorAnalysisRequest(values(
                    rated_voltage_v=voltage, cooling_method=cooling)))
                self.assertEqual(result.standard_code, HV_STANDARD)
                self.assertEqual(result.support_status, "IMPLEMENTED")
                self.assertEqual(tuple(result.thresholds_display.values()), thresholds)

    def test_exact_boundary_display_and_record_identity(self):
        records = Records()
        self.service.high_voltage._records = records
        for efficiency, grade in (("94.054999", "2"), ("94.055", "1"), ("94.055001", "1")):
            result = self.service.analyze_and_record(MotorAnalysisRequest(values(
                rated_output_power_kw="211", rated_efficiency_pct=efficiency)))
            self.assertEqual(result.result.grade, grade)
            self.assertEqual(result.result.thresholds_display["grade_1"], "94.06")
            self.assertEqual(result.result.thresholds["grade_1"]["exact"]["numerator"], "18811")
            self.assertEqual(result.record.standard_code, HV_STANDARD)
            self.assertEqual(result.record.standard_version, "2024")
            self.assertEqual(result.record.rule_profile, "motor_hv")
            self.assertEqual(result.record.ruleset_version, "GB30254-A.3/motor-hv-rule.v1")
            self.assertEqual(result.record.numeric_profile_id, "EQUIPEFFI_MOTOR_HV_EXACT_LINEAR_V1")
            self.assertIn("source_cells", result.record.reference_snapshot)
            self.assertEqual(result.record.input_snapshot["input_units"]["rated_voltage_v"], "V")
        self.assertEqual(len({r.record_id for r in records.records}), 3)

    def test_bad_input_missing_scope_and_failures(self):
        records = Records()
        self.service.high_voltage._records = records
        for raw in (94.0, "NaN", "-1", "0.94"):
            result = self.service.analyze_and_record(MotorAnalysisRequest(values(rated_efficiency_pct=raw)))
            self.assertEqual(result.record_status, "NOT_ELIGIBLE")
        self.assertFalse(records.records)
        for changes, status in ((dict(cooling_method=""), "INSUFFICIENT_DATA"),
            (dict(rated_frequency_hz="5～120"), "OUT_OF_STANDARD_SCOPE"),
            (dict(cooling_method="IC411", poles="10"), "OUT_OF_STANDARD_SCOPE"),
            (dict(rated_voltage_v="3"), "OUT_OF_STANDARD_SCOPE")):
            result = self.service.evaluate(MotorAnalysisRequest(values(**changes)))
            self.assertEqual(result.evaluation_status, status)
        self.service.high_voltage._pack["numeric_profile_id"] = "WRONG"
        with self.assertRaises(HvPackError):
            self.service.analyze_and_record(MotorAnalysisRequest(values()))
        self.assertFalse(records.records)

    def test_storage_failure_does_not_report_saved(self):
        class Failed:
            def append_record(self, record):
                raise OSError("storage failure")
        self.service.high_voltage._records = Failed()
        result = self.service.analyze_and_record(MotorAnalysisRequest(values()))
        self.assertEqual(result.record_status, "SAVE_FAILED")
        self.assertIsNone(result.record)

    def test_explicit_high_voltage_special_categories_keep_actual_labels(self):
        for category, label in (("OTHER_CATEGORY", "其他类别"), ("UNCERTAIN_CATEGORY", "不确定类别")):
            result = self.service.evaluate(MotorAnalysisRequest(values(category_id=category), standard_code=HV_STANDARD))
            self.assertEqual(result.product_category, label)
            self.assertEqual(result.standard_code, HV_STANDARD)

    def test_low_voltage_stays_explicit_and_does_not_guess_from_voltage(self):
        result = self.service.evaluate(MotorAnalysisRequest(values(category_id="three_phase_induction")))
        self.assertEqual(result.standard_code, "GB 18613-2020")
        self.assertEqual(result.evaluation_status, "OUT_OF_STANDARD_SCOPE")

    def test_explicit_old_contract_standard_conflict_and_unknown_standard_rejected(self):
        for revision in ("motor-input.v2", "motor-input.v3", "motor-input.v99"):
            with self.assertRaisesRegex(ValueError, "契约"):
                self.service.evaluate(MotorAnalysisRequest(values(input_contract_revision=revision)))
        for code in ("GB 18613-2020", "UNKNOWN"):
            with self.assertRaises(ValueError):
                self.service.evaluate(MotorAnalysisRequest(values(), standard_code=code))


if __name__ == "__main__":
    unittest.main()
