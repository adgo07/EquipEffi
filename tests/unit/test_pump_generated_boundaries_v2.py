from __future__ import annotations

import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from equipeffi.domain.evaluation.device_evaluators import _explicit_boundary_hit
from equipeffi.domain.evaluation.evaluators.pump import ChemicalPumpEvaluator
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository


ROOT = Path(__file__).resolve().parents[2]
STEP = Decimal("0.000001")


class PumpGeneratedBoundariesV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = JsonStandardRepository(ROOT).get_pack("pump_water")

    @staticmethod
    def _row_hit(value, row, minimum_key, maximum_key, boundaries=None):
        boundaries = boundaries or [{
            "min": row[minimum_key], "max": row[maximum_key],
            "min_inclusive": row.get("min_inclusive", True),
            "max_inclusive": row.get("max_inclusive", True),
        }]
        return _explicit_boundary_hit(value, row[minimum_key], row[maximum_key], boundaries)

    def test_generated_water_flow_boundaries_cover_exact_inside_and_outside(self):
        for row in self.pack["water"]["ci"]:
            low, high = Decimal(str(row["q_min"])), Decimal(str(row["q_max"]))
            low_inclusive = row.get("min_inclusive", True)
            high_inclusive = row.get("max_inclusive", True)
            with self.subTest(data_id=row["data_id"], edge="min"):
                self.assertEqual(self._row_hit(low, row, "q_min", "q_max"), low_inclusive)
                self.assertTrue(self._row_hit(low + STEP, row, "q_min", "q_max"))
                self.assertFalse(self._row_hit(low - STEP, row, "q_min", "q_max"))
            with self.subTest(data_id=row["data_id"], edge="max"):
                self.assertEqual(self._row_hit(high, row, "q_min", "q_max"), high_inclusive)
                self.assertTrue(self._row_hit(high - STEP, row, "q_min", "q_max"))
                self.assertFalse(self._row_hit(high + STEP, row, "q_min", "q_max"))

    def test_generated_chemical_flow_and_specific_speed_intervals(self):
        chemical = self.pack["chemical"]
        for dim, key in (("flow_q", "q"), ("specific_speed_ns", "ns")):
            for index, interval in enumerate(chemical["interval_boundaries"][dim]):
                lower = Decimal(str(interval["min"]))
                upper = Decimal(str(interval["max"])) if interval.get("max") is not None else None
                with self.subTest(dimension=dim, interval=index, edge="min"):
                    hit = _explicit_boundary_hit(lower, interval["min"], interval.get("max"), [interval])
                    self.assertEqual(hit, interval["min_inclusive"])
                    if interval["min_inclusive"]:
                        self.assertTrue(_explicit_boundary_hit(lower + STEP, interval["min"], interval.get("max"), [interval]))
                    self.assertFalse(_explicit_boundary_hit(lower - STEP, interval["min"], interval.get("max"), [interval]))
                if upper is not None:
                    with self.subTest(dimension=dim, interval=index, edge="max"):
                        hit = _explicit_boundary_hit(upper, interval["min"], interval["max"], [interval])
                        self.assertEqual(hit, interval["max_inclusive"])
                        self.assertTrue(_explicit_boundary_hit(upper - STEP, interval["min"], interval["max"], [interval]))
                        self.assertFalse(_explicit_boundary_hit(upper + STEP, interval["min"], interval["max"], [interval]))

    def test_chemical_evaluator_selects_rule_from_ns_raw_not_six_digit_rounding(self):
        base = {
            "category": "单级石油化工离心泵", "suction": "单吸", "stages": "1",
            "flow_m3h": "100", "head_m": "50", "rated_speed_rpm": "2900", "pump_efficiency": "80",
        }
        for ns, expected_rule in ((Decimal("59.9999999"), "GB19762-R000011"), (Decimal("60.0000004"), "GB19762-R000012")):
            with self.subTest(ns=str(ns)):
                derived = {"suction_factor": Decimal("1"), "stage_count": 1, "q_for_ns_m3s": Decimal("0.027777777777777777777777777777777777777777777777778"), "h_for_ns_m": Decimal("50"), "ns_raw": ns, "比转速": ns}
                with patch("equipeffi.domain.evaluation.device_evaluators._specific_speed", return_value=(ns, derived)):
                    result = ChemicalPumpEvaluator().evaluate(dict(base), self.pack)
                self.assertEqual(result.evaluation_status, "SUCCESS")
                self.assertEqual(result.lookups[0]["data_id"], expected_rule)
                self.assertEqual(result.calculated_metrics["ns_raw"], ns)


if __name__ == "__main__":
    unittest.main()
