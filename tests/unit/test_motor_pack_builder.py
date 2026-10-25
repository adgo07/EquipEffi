"""Regression coverage for the approved GB 18613 derived-pack builder."""

from __future__ import annotations

import json
from decimal import ROUND_CEILING, localcontext
from pathlib import Path
import runpy
import unittest


ROOT = Path(__file__).resolve().parents[2]
PACK_FILE = ROOT / "src/equipeffi/resources/standards/gb18613_2020.json"
BUILDER_FILE = ROOT / "tools/build_gb18613_motor_pack.py"


class MotorPackBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = runpy.run_path(str(BUILDER_FILE))

    def test_rebuild_is_ambient_context_independent_and_exactly_scales_kw(self):
        build_pack = self.builder["build_pack"]
        expected = build_pack()
        table1 = expected["tables"][0]
        row = next(item for item in table1["rows"] if item["power"]["source_cell"] == "A23")
        self.assertEqual(row["power"]["source_text"], "18.5")
        self.assertEqual(row["power"]["normalized_w_lower"], "18500")
        self.assertEqual(row["power"]["normalized_w_upper"], "18500")
        self.assertEqual(expected, json.loads(PACK_FILE.read_text(encoding="utf-8")))

        with localcontext() as context:
            context.prec = 2
            context.rounding = ROUND_CEILING
            altered = build_pack()

        self.assertEqual(altered, expected)


if __name__ == "__main__":
    unittest.main()
