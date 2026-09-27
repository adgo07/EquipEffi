from __future__ import annotations

import unittest
from decimal import Decimal
from pathlib import Path

from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository


ROOT = Path(__file__).resolve().parents[2]


class PumpRuleIntegrityV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = JsonStandardRepository(ROOT).get_pack("pump_water")

    def test_water_table_has_unique_stable_ids_and_c2_142_33(self):
        rows = self.pack["water"]["ci"]
        ids = [row["data_id"] for row in rows]
        self.assertEqual(len(rows), 10)
        self.assertEqual(len(ids), len(set(ids)))
        t3_08 = [row for row in rows if row["data_id"] == "GB19762-T3-08"]
        self.assertEqual(len(t3_08), 1)
        upper_band = t3_08[0]
        self.assertEqual(upper_band["ci"][1], Decimal("142.33"))
        self.assertEqual(Decimal(str(upper_band["q_min"])), Decimal("100"))
        self.assertFalse(upper_band["min_inclusive"])
        self.assertEqual(Decimal(str(upper_band["q_max"])), Decimal("3000"))
        self.assertTrue(upper_band["max_inclusive"])

    def test_chemical_table_has_sixteen_unique_stable_ids_and_decimal_coefficients(self):
        rules = self.pack["chemical"]["level_offsets"]
        ids = [row["data_id"] for row in rules]
        self.assertEqual(len(rules), 16)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids[0], "GB19762-R000011")
        self.assertEqual(ids[-1], "GB19762-R000026")
        for coefficient in self.pack["chemical"]["eta_b"]["多级"]:
            self.assertIsInstance(coefficient, Decimal)
        self.assertEqual(self.pack["chemical"]["eta_b"]["多级"][-1], Decimal("41.467097"))

    def test_standard_json_fractional_literals_are_loaded_as_decimal_text(self):
        self.assertEqual(self.pack["water"]["formulas"]["多级"]["a"], Decimal("-6.93"))
        self.assertEqual(self.pack["chemical"]["delta_eta"]["ns_20_120"][0], Decimal("3.7873403E-10"))


if __name__ == "__main__":
    unittest.main()
