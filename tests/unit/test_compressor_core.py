import unittest
from decimal import localcontext, ROUND_DOWN
from copy import deepcopy
from fractions import Fraction
from equipeffi.domain.devices.compressor.calculator import Gb19153CompressorCalculator, CompressorPackError, PROFILE_ID
from equipeffi.domain.devices.compressor.input_contract import CATEGORIES
from equipeffi.infrastructure.standards.compressor_repository import load_compressor_pack
from tools.build_gb19153_compressor_pack import build_pack


class CompressorCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.pack, _ = load_compressor_pack(
    ); cls.calc = Gb19153CompressorCalculator()

    def values(self, n=1, p="1.5", q="0.3", e="5.8", cool="AIR"):
        d = dict(category_id=CATEGORIES[n - 1].category_id,
                 rated_discharge_pressure_mpa=q,
                 specific_power_kw_per_m3_min=e)
        d["rated_motor_output_power_kw" if n <= 4 else "rated_input_power_kw"] = p
        if n <= 4:
            d["cooling_method"] = cool
        return d

    def test_approved_candidates(self):
        for n, p, q, e, expected in ((1, "1.5", "0.3", "5.8", "1级"), (1, "1.5", "0.3", "6.5", "2级"), (1, "1.5", "0.3", "7.4", "3级"), (1, "1.5", "0.3", "7.401", "未达3级"), (
                2, "2.2", "0.3", "6.1", "1级"), (3, "2.2", "0.25", "6.9", "3级"), (4, "18.5", "0.7", "6.7", "1级"), (5, "0.25", "0.2", "5.2", "1级"), (6, "0.25", "0.2", "5.5", "1级")):
            with self.subTest(n=n, e=e):
                self.assertEqual(
                    self.calc.evaluate(
                        self.values(
                            n,
                            p,
                            q,
                            e,
                            "LIQUID" if n == 4 else "AIR"),
                        self.pack).ui_conclusion,
                    expected)

    def test_independent_source_rebuild(
        self): self.assertEqual(build_pack(), self.pack)

    def test_all_source_branches_and_boundaries(self):
        for table in self.pack["tables"]:
            groups = {}
            for row in table["rows"]:
                groups.setdefault(
                    (row["power_kw"],
                     row["pressure_mpa"],
                        row["cooling"]),
                    []).append(row)
            for (p, q, c), rows in groups.items():
                n = table["table_number"]
                values = self.values(n, p, q, "1", c)
                result = self.calc.evaluate(values, self.pack)
                if any(row["value"] is None for row in rows):
                    self.assertEqual(result.reason_codes, ("SOURCE_DASH",))
                    continue
                for row in rows:
                    values["specific_power_kw_per_m3_min"] = row["value"]
                    expected = next(str(x["grade"]) for x in sorted(
                        rows, key=lambda x: x["grade"]) if Fraction(row["value"]) <= Fraction(x["value"]))
                    self.assertEqual(
                        self.calc.evaluate(
                            values, self.pack).grade, expected)

    def test_lookup_and_absent_branches(self):
        v = self.values(p="3.5", q="0.75")
        r = self.calc.evaluate(v, self.pack)
        self.assertEqual(
            (r.references["selected_power_kw"],
             r.references["selected_pressure_mpa"]),
            ("4",
             "7/10"))
        for v, reason in ((self.values(cool="LIQUID"), "SOURCE_DASH"), (self.values(3, "2.2", "0.25", cool="LIQUID"), "COOLING_UNRESOLVED"), (self.values(
                4, "2.2", "0.7", cool="LIQUID"), "COOLING_UNRESOLVED"), (self.values(q="0.25"), "NO_LOOKUP_BRANCH"), (self.values(q="1.3"), "NO_LOOKUP_BRANCH")):
            self.assertEqual(
                self.calc.evaluate(
                    v, self.pack).reason_codes, (reason,))

    def test_invalid_missing_and_scope(self):
        for raw in (True, 5.8, "NaN", "Infinity", "5 kW", "1e9999", "0", "-1"):
            v = self.values()
            v["specific_power_kw_per_m3_min"] = raw
            self.assertEqual(
                self.calc.evaluate(
                    v,
                    self.pack).evaluation_status,
                "INVALID_INPUT")
        v = self.values()
        del v["cooling_method"]
        self.assertEqual(
            self.calc.evaluate(
                v,
                self.pack).evaluation_status,
            "INVALID_INPUT")
        for p, q in (("1.49", "0.3"), ("631", "0.3"),
                     ("1.5", "0.249"), ("1.5", "1.401")):
            self.assertEqual(
                self.calc.evaluate(
                    self.values(
                        p=p,
                        q=q),
                    self.pack).evaluation_status,
                "OUT_OF_STANDARD_SCOPE")

    def test_ambient_display_and_profile(self):
        v = self.values(e="5.800000000000000000000001")
        for prec in (2, 7, 50):
            with localcontext() as c:
                c.prec = prec
                c.rounding = ROUND_DOWN
                r = self.calc.evaluate(v, self.pack)
                self.assertEqual(r.grade, "2")
                self.assertEqual(r.thresholds["grade_1"]["value"], "5.8")
        with self.assertRaises(CompressorPackError):
            self.calc.evaluate(v, self.pack, numeric_profile_id="bad")
        p = deepcopy(self.pack)
        p["tables"][0]["rows"][0]["value"] = "99"
        with self.assertRaises(CompressorPackError):
            self.calc.evaluate(v, p)


    def test_frozen_schema_vectors(self):
        from pathlib import Path
        import json
        import jsonschema
        root = Path(__file__).resolve().parents[2]
        schema = json.loads((root / "tests/fixtures/numeric/conformance_vector_v1.schema.json").read_text())
        vectors = json.loads((root / "specs/equipment_efficiency/numeric/equipeffi_compressor_conformance_v1.json").read_text(encoding="utf-8"))
        for vector in vectors:
            jsonschema.validate(vector, schema)
            with localcontext() as context:
                context.prec = 2 if vector["category"] == "ambient_independence" else 28
                result = self.calc.evaluate(vector["inputs"], self.pack)
                expected = vector["expected_business_result"]
                self.assertEqual((result.evaluation_status, result.grade), (expected["evaluation_status"], expected["grade"]))
                self.assertEqual(result.references["numeric_profile_id"], vector["numeric_profile_id"])

    def test_builder_failure_paths_on_isolated_copies(self):
        from pathlib import Path
        import tempfile
        from zipfile import ZipFile
        from xml.etree import ElementTree as ET
        from hashlib import sha256
        from unittest.mock import patch
        import tools.build_gb19153_compressor_pack as builder
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / builder.WORKBOOK
            target.parent.mkdir(parents=True)
            data = (builder.ROOT / builder.WORKBOOK).read_bytes()
            target.write_bytes(data + b"tamper")
            with self.assertRaisesRegex(ValueError, "哈希"):
                builder.build_pack(root)
            target.write_bytes(data)
            with ZipFile(target) as archive:
                entries = [(info, archive.read(info.filename)) for info in archive.infolist()]
                names = builder._sheet_names(archive)
                strings = builder._shared_strings(archive)
                xml = ET.fromstring(archive.read(names["表1"]))
            for address in ("G6", "N6"):
                changed = ET.fromstring(ET.tostring(xml))
                cell = next(node for node in changed.iter(builder._q(builder.NS_MAIN, "c")) if node.get("r") == address)
                for child in list(cell):
                    cell.remove(child)
                if address == "N6":
                    cell.set("t", "inlineStr")
                    inline = ET.SubElement(cell, builder._q(builder.NS_MAIN, "is"))
                    ET.SubElement(inline, builder._q(builder.NS_MAIN, "t")).text = "99.9"
                with ZipFile(target, "w") as archive:
                    for info, raw in entries:
                        archive.writestr(info, ET.tostring(changed) if info.filename == names["表1"] else raw)
                with patch.object(builder, "SOURCE_SHA", sha256(target.read_bytes()).hexdigest()):
                    with self.assertRaisesRegex(ValueError, "源格缺失|显示值改变"):
                        builder.build_pack(root)

if __name__ == "__main__":
    unittest.main()
