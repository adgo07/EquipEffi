"""X-line regression for stable Application metric IDs in the Excel Writer."""
from __future__ import annotations

import unittest

from equipeffi.application.ports.batch_workbook import BatchRowOutcome
from equipeffi.application.result_projection import PUMP_METRIC_IDS, PumpResultMetric
from equipeffi.infrastructure.excel.pump_result_writer import (
    ResultWorkbookWriteError,
    cell_payloads,
)


class StableMetricWriterTests(unittest.TestCase):
    def make_outcome(self, metric: PumpResultMetric) -> BatchRowOutcome:
        return BatchRowOutcome(
            row_number=4,
            evaluated=True,
            conclusion="1级",
            evaluation_status="SUCCESS",
            grade="1",
            metrics_by_id={metric.metric_id: metric},
        )

    def test_column_mapping_uses_stable_id_and_preserves_decimal_text(self):
        metric_id = PUMP_METRIC_IDS["specific_speed"]
        outcome = self.make_outcome(PumpResultMetric(
            metric_id=metric_id,
            value="123.456789012345678901",
            unit="1",
            display_name="本地化展示名不参与取值",
        ))

        self.assertEqual(cell_payloads(outcome)["N"],
                         ("n", "123.456789012345678901"))

    def test_localized_trace_label_does_not_drive_result_value(self):
        outcome = BatchRowOutcome(
            row_number=4,
            evaluated=True,
            conclusion="1级",
            evaluation_status="SUCCESS",
            grade="1",
            derived={"比转速 ns": "999.99"},
        )

        self.assertIsNone(cell_payloads(outcome)["N"])

    def test_metric_unit_mismatch_fails_closed(self):
        metric_id = PUMP_METRIC_IDS["specific_speed"]
        outcome = self.make_outcome(PumpResultMetric(
            metric_id=metric_id,
            value="123.45",
            unit="m³/s",
            display_name="比转速",
        ))

        with self.assertRaisesRegex(ResultWorkbookWriteError, "单位不匹配"):
            cell_payloads(outcome)

    def test_metric_id_mismatch_fails_closed(self):
        expected_id = PUMP_METRIC_IDS["specific_speed"]
        outcome = BatchRowOutcome(
            row_number=4,
            evaluated=True,
            conclusion="1级",
            evaluation_status="SUCCESS",
            grade="1",
            metrics_by_id={expected_id: PumpResultMetric(
                metric_id=PUMP_METRIC_IDS["c1"],
                value="123.45",
                unit="1",
                display_name="ns",
            )},
        )

        with self.assertRaisesRegex(ResultWorkbookWriteError, "身份不匹配"):
            cell_payloads(outcome)


if __name__ == "__main__":
    unittest.main()
