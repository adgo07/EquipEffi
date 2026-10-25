"""GB 18613 calculator execution-consistency checks against the reviewed pack.

This test checks that the Application/Calculator path uses the limits and
no-indicator states present in the reviewed runtime pack. It does not establish
the pack as source truth; independent source-cell transcription review is a
separate audit.
"""

from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction
import unittest

from equipeffi.application.services.motor_analysis_service import (
    MotorAnalysisRequest,
    MotorAnalysisService,
)
from equipeffi.domain.devices.motor.calculator import Gb18613MotorCalculator
from equipeffi.domain.devices.motor.input_contract import MOTOR_CATEGORIES
from equipeffi.infrastructure.standards.motor_repository import load_motor_pack


_EDGE_DELTA = Fraction(1, 1_000_000)
_TABLE6_SPEEDS = {
    "rpm_band_1": "500",
    "rpm_band_2": "600",
    "rpm_band_3": "800",
    "rpm_band_4": "1100",
    "rpm_band_5": "1400",
}
_EXPECTED_AVAILABLE_CELLS = 1149
_EXPECTED_BOUNDARY_CASES = _EXPECTED_AVAILABLE_CELLS * 3
_EXPECTED_NO_INDICATOR_CASES = 11


def _as_fraction(value: object) -> Fraction:
    return Fraction(str(value))


def _as_decimal_text(value: Fraction) -> str:
    """Render the finite decimal inputs used here without a float conversion."""

    with localcontext() as context:
        context.prec = 50
        return format(Decimal(value.numerator) / Decimal(value.denominator), "f")


def _expected_grade(efficiency: Fraction,
                    thresholds: dict[str, Fraction]) -> str | None:
    """Classify using only the three source-row thresholds, independently."""

    for grade in ("grade_1", "grade_2", "grade_3"):
        if efficiency >= thresholds[grade]:
            return grade.removeprefix("grade_")
    return None


class MotorAllSourceBoundariesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pack, cls.pack_sha256 = load_motor_pack()
        cls.service = MotorAnalysisService(
            cls.pack,
            Gb18613MotorCalculator(),
            pack_sha256=cls.pack_sha256,
            app_version="execution-consistency-test",
        )
        cls.category_by_table = {
            category.table_no: category
            for category in MOTOR_CATEGORIES
            if category.table_no is not None
        }

    def _values(self, table_no: int, branch_id: str,
                row: dict, efficiency: Fraction) -> dict[str, str]:
        category = self.category_by_table[table_no]
        power_kw = _as_fraction(row["power"]["normalized_w_lower"]) / 1000
        values = {
            "category_id": category.category_id,
            "rated_output_power_kw": _as_decimal_text(power_kw),
            "measured_efficiency_pct": _as_decimal_text(efficiency),
        }
        facts = category.route_facts
        if table_no <= 4:
            values["rated_voltage_kv"] = "0.38"
            values["rated_frequency_hz"] = str(facts["rated_frequency_hz"])
        if table_no <= 5:
            branch_value = next(
                branch["value"]
                for branch in self.pack["tables"][table_no - 1]["branches"]
                if branch["branch_id"] == branch_id
            )
            values["poles"] = str(branch_value)
        else:
            values["max_nameplate_speed_rpm"] = _TABLE6_SPEEDS[branch_id]
        return values

    @staticmethod
    def _source_thresholds(branch_values: dict[str, dict]) -> dict[str, Fraction]:
        return {
            grade: _as_fraction(item["value"])
            for grade, item in branch_values.items()
            if item["state"] == "AVAILABLE"
        }

    def _assert_direct_trace(self, result, table_no: int, branch_id: str,
                             row: dict) -> None:
        self.assertEqual(len(result.trace), 1)
        trace = result.trace[0]
        self.assertEqual(trace["table_no"], table_no)
        self.assertEqual(trace["branch_id"], branch_id)
        self.assertEqual(trace["method"], "DIRECT")
        self.assertEqual(trace["source_rows"], [row["source_row_id"]])

    def _assert_thresholds_match_row(self, result,
                                     branch_values: dict[str, dict]) -> None:
        for grade in ("grade_1", "grade_2", "grade_3"):
            expected = branch_values[grade]
            actual = result.thresholds[grade]
            self.assertEqual(actual["state"], expected["state"])
            if expected["state"] == "AVAILABLE":
                fraction = _as_fraction(expected["value"])
                self.assertEqual(actual["exact"], {
                    "numerator": str(fraction.numerator),
                    "denominator": str(fraction.denominator),
                    "unit": "percent_point",
                })

    def test_every_available_source_limit_below_at_and_above(self) -> None:
        available_cells = 0
        boundary_cases = 0

        for table in self.pack["tables"]:
            table_no = table["table_no"]
            for row in table["rows"]:
                for branch_id, branch_values in row["branches"].items():
                    if any(branch_values[grade]["state"] != "AVAILABLE"
                           for grade in ("grade_1", "grade_2", "grade_3")):
                        continue

                    source_thresholds = self._source_thresholds(branch_values)
                    self.assertEqual(set(source_thresholds),
                                     {"grade_1", "grade_2", "grade_3"})
                    for boundary_grade, threshold in source_thresholds.items():
                        available_cells += 1
                        for relation, efficiency in (
                                ("below", threshold - _EDGE_DELTA),
                                ("equal", threshold),
                                ("above", threshold + _EDGE_DELTA)):
                            boundary_cases += 1
                            expected_grade = _expected_grade(
                                efficiency, source_thresholds)
                            request = MotorAnalysisRequest(self._values(
                                table_no, branch_id, row, efficiency))
                            result = self.service.evaluate(request)
                            with self.subTest(
                                    table=table_no,
                                    source_row=row["source_row_id"],
                                    branch=branch_id,
                                    boundary=boundary_grade,
                                    relation=relation):
                                self.assertEqual(result.evaluation_status, "SUCCESS")
                                self.assertEqual(result.grade, expected_grade)
                                self.assertEqual(
                                    result.ui_conclusion,
                                    f"{expected_grade}级" if expected_grade else "未达3级")
                                self._assert_direct_trace(
                                    result, table_no, branch_id, row)
                                self._assert_thresholds_match_row(
                                    result, branch_values)

        self.assertEqual(available_cells, _EXPECTED_AVAILABLE_CELLS)
        self.assertEqual(boundary_cases, _EXPECTED_BOUNDARY_CASES)

    def test_each_no_indicator_source_branch_blocks_classification(self) -> None:
        blocked_cases = 0
        source_blank_cells = []

        for table in self.pack["tables"]:
            table_no = table["table_no"]
            for row in table["rows"]:
                for branch_id, branch_values in row["branches"].items():
                    for grade, item in branch_values.items():
                        if item.get("source_state") == "SOURCE_BLANK":
                            source_blank_cells.append((table_no, row, branch_id, grade, item))
                    if not any(branch_values[grade]["state"] == "NO_INDICATOR"
                               for grade in ("grade_1", "grade_2", "grade_3")):
                        continue

                    blocked_cases += 1
                    result = self.service.evaluate(MotorAnalysisRequest(
                        self._values(table_no, branch_id, row, Fraction(100))))
                    with self.subTest(
                            table=table_no,
                            source_row=row["source_row_id"],
                            branch=branch_id):
                        self.assertEqual(result.evaluation_status, "INSUFFICIENT_DATA")
                        self.assertIsNone(result.grade)
                        self.assertEqual(result.ui_conclusion, "无法判定")
                        self.assertIn("NO_INDICATOR", result.reason_codes)
                        self._assert_direct_trace(result, table_no, branch_id, row)
                        self._assert_thresholds_match_row(result, branch_values)

        self.assertEqual(blocked_cases, _EXPECTED_NO_INDICATOR_CASES)
        self.assertEqual(len(source_blank_cells), 1)
        table_no, row, branch_id, grade, item = source_blank_cells[0]
        self.assertEqual(item["source_cell"], "C14")
        self.assertEqual(item["state"], "NO_INDICATOR")
        self.assertEqual((table_no, branch_id, grade), (3, "poles_4", "grade_1"))
        self.assertIn(
            "NO_INDICATOR",
            self.service.evaluate(MotorAnalysisRequest(
                self._values(table_no, branch_id, row, Fraction(100))
            )).reason_codes,
        )


if __name__ == "__main__":
    unittest.main()
