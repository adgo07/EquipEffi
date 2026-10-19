from datetime import date
from decimal import Decimal
from pathlib import Path
import unittest

from equipeffi.application.result_projection import (
    DERIVED_DISPLAY_NAMES,
    PUMP_METRIC_IDS,
    THRESHOLD_DISPLAY_NAMES,
    project_pump_metrics,
)
from equipeffi.application.services.centrifugal_pump_analysis_service import (
    CentrifugalPumpAnalysisService,
    PumpAnalysisRequest,
    PumpAnalysisResult,
)
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository

ROOT = Path(__file__).resolve().parents[2]


class PumpResultProjectionTests(unittest.TestCase):
    def test_stable_ids_keep_exact_values_and_explicit_units(self):
        projected = project_pump_metrics(
            {
                "ns_raw": Decimal("82.300100"),
                "C1": Decimal("161.33"),
                "C2": Decimal("163.33"),
                "C3": Decimal("168.33"),
                "输出功率_kW": Decimal("2.452500"),
                "规定点效率_%": Decimal("71.2300"),
            },
            {"1级效率_%": Decimal("71.23")},
        )

        self.assertEqual(projected[PUMP_METRIC_IDS["specific_speed"]].value,
                         "82.300100")
        self.assertEqual(projected[PUMP_METRIC_IDS["specific_speed"]].unit, "1")
        self.assertEqual(projected[PUMP_METRIC_IDS["c1"]].value, "161.33")
        self.assertEqual(projected[PUMP_METRIC_IDS["c1"]].unit, "%")
        self.assertEqual(projected[PUMP_METRIC_IDS["output_power"]].value,
                         "2.452500")
        self.assertEqual(projected[PUMP_METRIC_IDS["output_power"]].unit, "kW")
        self.assertEqual(
            projected[PUMP_METRIC_IDS["grade_1_efficiency_limit"]].value,
            "71.23",
        )
        self.assertNotIn("比转速 ns", projected)

    def test_real_evaluation_emits_stable_writer_ids_without_recalculation(self):
        service = CentrifugalPumpAnalysisService(
            JsonStandardRepository(ROOT / "src" / "equipeffi")
        )
        result = service.evaluate(PumpAnalysisRequest(
            "单级单吸清水离心泵",
            date(2026, 10, 19),
            QBEP="100",
            HBEP="50",
            speed="2900",
            efficiency="90",
            suction="单吸",
            stages="1",
        ))

        self.assertEqual(result.evaluation_status, "SUCCESS")
        metrics = result.metrics_by_id
        self.assertEqual(
            metrics[PUMP_METRIC_IDS["specific_speed"]].value,
            result.calculation_trace["derived"]["比转速 ns"],
        )
        self.assertEqual(
            metrics[PUMP_METRIC_IDS["grade_1_efficiency_limit"]].value,
            result.thresholds["1级能效效率限值（%）"],
        )
        self.assertTrue(all(PUMP_METRIC_IDS[key] in metrics for key in ("c1", "c2", "c3")))
        self.assertEqual(metrics[PUMP_METRIC_IDS["c1"]].unit, "%")
        self.assertIn(PUMP_METRIC_IDS["specific_speed"],
                      result.as_snapshot()["metrics_by_id"])

    def test_snapshot_adds_id_projection_and_keeps_legacy_fields(self):
        metrics = project_pump_metrics(
            {"ns_raw": Decimal("12.3400")},
            {"1级效率_%": Decimal("60.12")},
        )
        result = PumpAnalysisResult(
            rule_profile="pump_water",
            standard_code="GB 19762-2025",
            product_category="单级单吸清水离心泵",
            as_of=date(2026, 10, 19),
            evaluation_status="SUCCESS",
            category_status="SUPPORTED",
            support_status="SUPPORTED",
            ui_conclusion="1级",
            grade="1",
            thresholds={"1级能效效率限值（%）": "60.12"},
            metrics_by_id=metrics,
            calculation_trace={"derived": {"比转速 ns": "12.3400"}},
        )

        snapshot = result.as_snapshot()
        metric_id = PUMP_METRIC_IDS["specific_speed"]
        self.assertEqual(snapshot["metrics_by_id"][metric_id]["value"], "12.3400")
        self.assertEqual(snapshot["metrics_by_id"][metric_id]["unit"], "1")
        self.assertEqual(snapshot["metrics_by_id"][metric_id]["value_representation"],
                         "decimal_text")
        self.assertEqual(snapshot["thresholds"], {"1级能效效率限值（%）": "60.12"})
        self.assertEqual(snapshot["calculation_trace"]["derived"],
                         {"比转速 ns": "12.3400"})

    def test_compatibility_label_maps_are_derived_from_metric_definitions(self):
        self.assertEqual(DERIVED_DISPLAY_NAMES["ns_raw"], "比转速 ns")
        self.assertEqual(THRESHOLD_DISPLAY_NAMES["1级效率_%"],
                         "1级能效效率限值（%）")

    def test_missing_values_are_not_fabricated(self):
        self.assertEqual(project_pump_metrics({}, {}), {})


if __name__ == "__main__":
    unittest.main()
