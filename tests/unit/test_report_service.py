from __future__ import annotations

import unittest

from equipeffi.application.services.report_service import ReportService
from equipeffi.domain.common.enums import Conclusion
from equipeffi.domain.common.models import EvaluationResult


class ReportServiceTests(unittest.TestCase):
    def test_build_creates_stable_conclusion_and_device_summaries(self):
        results = [
            EvaluationResult(
                record_id="1",
                conclusion=Conclusion.LEVEL_1,
                public_device_type="motor",
                internal_device_type="motor_lv",
            ),
            EvaluationResult(
                record_id="2",
                conclusion=Conclusion.UNABLE_TO_JUDGE,
                public_device_type="motor",
                internal_device_type="motor_hv",
                data_quality_issues=[{"code": "required"}],
            ),
            EvaluationResult(record_id="3", conclusion=Conclusion.ELIMINATED),
        ]

        report = ReportService().build("PROJECT-1", results)

        self.assertEqual(report.project_id, "PROJECT-1")
        self.assertEqual(report.summary["total_records"], 3)
        self.assertEqual(report.summary["by_conclusion"]["1级"], 1)
        self.assertEqual(report.summary["by_conclusion"]["无法判定"], 1)
        self.assertEqual(report.summary["by_conclusion"]["淘汰"], 1)
        self.assertEqual(report.summary["eliminated_records"], 1)
        self.assertEqual(report.summary["unable_records"], 1)
        self.assertEqual(report.summary["data_quality_issue_records"], 1)
        self.assertEqual(report.summary["by_public_device_type"]["未标注"], 1)
        self.assertEqual(report.summary["by_internal_device_type"]["motor_hv"], 1)


if __name__ == "__main__":
    unittest.main()
