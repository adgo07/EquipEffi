"""GB 30253 source-cell, range and exact numeric conformance."""
from dataclasses import replace
from decimal import ROUND_DOWN, ROUND_UP, Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import unittest

from equipeffi.domain.devices.motor_pmsm.calculator import Gb30253MotorCalculator, ISSUE_001, ISSUE_003, ISSUE_004
from equipeffi.domain.devices.motor_pmsm.numeric import PROFILE_ID
from equipeffi.domain.devices.motor_pmsm.pack import PmsmPack, PmsmPackError
from equipeffi.infrastructure.standards.motor_pmsm_repository import load_motor_pmsm_pack
from tools.build_gb30253_motor_pack import OUTPUT, WORKBOOK, build_pack

ROOT = Path(__file__).resolve().parents[2]
NUMERIC = ROOT / "specs/equipment_efficiency/numeric"
BASE = {"category_id": "gb30253_lv_async_start", "rated_voltage_v": "380", "rated_frequency_hz": "50",
        "rated_output_power_kw": "0.55", "poles": "2", "rated_efficiency_pct": "100"}
C = BASE | {"category_id": "gb30253_lv_vfd", "rated_speed_rpm": "550"}
D = BASE | {"category_id": "gb30253_hv_vfd", "rated_voltage_v": "3000", "cooling_method": "IC81W",
            "rated_output_power_kw": "200", "rated_speed_rpm": "3000"}
E = BASE | {"category_id": "gb30253_elevator", "rated_speed_rpm": "100"}


def exact(result, grade=1):
    value = result.thresholds[f"grade_{grade}"]["exact"]
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def route(number):
    if number == 1:
        return BASE
    if 2 <= number <= 7:
        index = number - 2
        return BASE | {"category_id": "gb30253_hv_async_start",
                       "rated_voltage_v": "10000" if index >= 3 else "3300",
                       "cooling_method": ("IC81W", "IC411", "IC666")[index % 3]}
    if 8 <= number <= 10:
        return C
    if 11 <= number <= 28:
        index = (number - 11) // 3
        return D | {"rated_voltage_v": "10000" if index >= 3 else "6000",
                    "cooling_method": ("IC71W(IC3W7)", "IC416", "IC616")[index % 3]}
    return E


def axis_input(source):
    if source.startswith(">") and "～" not in source:
        return str(int(source[1:]) + 1)
    return source.split("～")[-1].lstrip("≤≥")


class MotorPmsmCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = load_motor_pmsm_pack()
        cls.calculator = Gb30253MotorCalculator()

    def evaluate(self, base=BASE, **changes):
        return self.calculator.evaluate(base | changes, self.pack)

    def test_pinned_reproducible_pack_rejects_mutation_even_if_resigned(self):
        path = ROOT / OUTPUT
        original = path.read_bytes()
        payload = json.loads(original)
        self.assertEqual(payload, build_pack(ROOT))
        self.assertEqual(payload["counts"], {"tables": 29, "rows": 707, "numeric": 10651, "horizontal_dash": 152})
        self.assertEqual(payload["tables"][0]["rows"][16]["efficiencies_pct"][12], "0.0")
        self.assertEqual(dict(self.pack.excluded_cells), {"表01!N23": ISSUE_001})
        payload["tables"][0]["rows"][0]["efficiencies_pct"][0] = "85.8"
        with self.assertRaises(PmsmPackError):
            PmsmPack.from_bytes(json.dumps(payload).encode())
        payload.pop("integrity_sha256")
        digest = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        payload["integrity_sha256"] = digest
        with self.assertRaises(PmsmPackError):
            PmsmPack.from_bytes(json.dumps(payload).encode())

    def test_all_10803_efficiency_cells_and_29_routes_against_approved_workbook(self):
        from openpyxl import load_workbook

        workbook = load_workbook(ROOT / WORKBOOK, data_only=True)
        count = 0
        try:
            for table in self.pack.tables:
                sheet = workbook[table.sheet]
                base = route(table.number)
                dimensions = {}
                for column in table.columns:
                    header = sheet[f"{column.letter}6"].value
                    grade, heading = header.split("级\n")
                    field = "poles" if heading.endswith("极") else "rated_speed_rpm"
                    source_axis = heading.removesuffix("极").removesuffix(" r/min")
                    self.assertEqual((int(grade), source_axis), (column.grade, column.axis.text))
                    dimensions.setdefault((field, source_axis), {})[int(grade)] = column.letter

                for row in table.rows:
                    power = str(sheet[f"A{row.number}"].value)
                    self.assertEqual(axis_input(row.power.text), axis_input(power))
                    for (field, axis), columns in dimensions.items():
                        result = self.evaluate(base, rated_output_power_kw=axis_input(power),
                                               **{field: axis_input(axis)})
                        self.assertIn(table.number, result.references["table_numbers"])
                        for grade, letter in columns.items():
                            address = f"{letter}{row.number}"
                            source = sheet[address]
                            lookup = result.references["grade_lookups"][f"grade_{grade}"]
                            self.assertEqual(lookup["table_number"], table.number)
                            self.assertEqual(lookup["source_cells"][0]["source_cell"], address)
                            self.assertEqual(lookup["source_cells"][0]["source_sheet"], table.sheet)
                            if source.value == "—" or table.number == 1 and address == "N23":
                                self.assertNotIn(f"grade_{grade}", result.thresholds)
                                self.assertEqual(lookup["reason"], "NO_THRESHOLD")
                            else:
                                expected = f"{Decimal(str(source.value)):.1f}"
                                self.assertEqual(result.thresholds[f"grade_{grade}"]["display"], expected)
                                self.assertEqual(exact(result, grade), Fraction(expected))
                            count += 1
        finally:
            workbook.close()
        self.assertEqual(count, 10803)

    def test_full_value_t_minus_equal_plus_for_all_three_grades(self):
        for base, thresholds in ((BASE, ("85.9", "84.6", "81.5")), (C | {"rated_output_power_kw": "0.65"},
                                  ("82.125", "78.60", "74.60"))):
            for level, threshold in enumerate(thresholds, 1):
                for delta in (Decimal("-0.0000000000000000000001"), Decimal(0), Decimal("0.0000000000000000000001")):
                    result = self.evaluate(base, rated_efficiency_pct=str(Decimal(threshold) + delta))
                    expected = str(level) if delta >= 0 else str(level + 1) if level < 3 else None
                    self.assertEqual((result.evaluation_status, result.grade), ("SUCCESS", expected))

    def test_001_excluded_cell_and_non_extrapolation(self):
        within = self.evaluate(poles="12", rated_output_power_kw="45")
        self.assertEqual([exact(within, i) for i in (1, 2, 3)], list(map(Fraction, ("95.2", "94.1", "92.7"))))
        for power in ("45.001", "55", "75"):
            result = self.evaluate(poles="12", rated_output_power_kw=power)
            self.assertEqual((result.evaluation_status, result.reason_codes), ("INSUFFICIENT_DATA", ("NO_THRESHOLD",)))
            self.assertEqual(result.references["standard_issues"][ISSUE_001], "RESOLVED")
            self.assertEqual(result.references["effective_max_power_kw"], "45")
            self.assertFalse(result.thresholds)
        excluded = self.evaluate(poles="12", rated_output_power_kw="55").references["grade_lookups"]["grade_2"]["source_cells"][0]
        self.assertEqual((excluded["source_cell"], excluded["source_text"], excluded["value_pct"], excluded["excluded_by_issue"]),
                         ("N23", "0.0", None, ISSUE_001))
        self.assertEqual(self.evaluate(poles="10").reason_codes, ("NO_THRESHOLD",))
        self.assertEqual(self.evaluate(poles="5").reason_codes, ("NO_POLE_COLUMN",))
        self.assertEqual(self.evaluate(poles="17").evaluation_status, "OUT_OF_STANDARD_SCOPE")

    def test_003_speed_anchor_and_interval_discontinuities(self):
        for speed, expected, provisional in (
            ("500", "81.0", False), ("500.001", "81.000009", True), ("550", "81.45", True),
            ("599.999", "81.899991", True), ("600", "81.9", True), ("600.001", "81.9", False),
            ("900", "81.9", False), ("900.001", "84.5", False), ("1500", "86.3", False),
        ):
            result = self.evaluate(C, rated_speed_rpm=speed)
            self.assertEqual(exact(result), Fraction(expected))
            self.assertEqual(result.references["standard_issues"].get(ISSUE_003), "PROVISIONAL" if provisional else None)
        result = self.evaluate(C, rated_output_power_kw="0.65")
        lookup = result.references["grade_lookups"]["grade_1"]
        self.assertEqual(lookup["speed_anchor"]["rated_speed_rpm"], "600")
        self.assertEqual({cell["source_cell"] for cell in lookup["source_cells"]}, {"E7", "F7", "E8", "F8"})
        self.assertEqual(lookup["method"], "BILINEAR_INTERPOLATION")
        self.assertNotIn(ISSUE_004, result.references["standard_issues"])
        self.assertEqual([exact(result, i) for i in (1, 2, 3)], list(map(Fraction, ("82.125", "78.60", "74.60"))))
        self.assertEqual(exact(self.evaluate(E)), Fraction("74.6"))
        self.assertEqual(exact(self.evaluate(E, rated_speed_rpm="100.01")), Fraction("75.4"))

    def test_004_general_bilinear_both_orders_and_each_missing_corner(self):
        case = D | {"rated_output_power_kw": "207", "rated_speed_rpm": "2000"}
        result = self.evaluate(case)
        a, b, c, d = map(Fraction, ("93.7", "93.5", "93.9", "93.7"))
        u, v = Fraction(7, 20), Fraction(1, 3)
        power_first = (a + (c - a) * u) * (1 - v) + (b + (d - b) * u) * v
        speed_first = (a + (b - a) * v) * (1 - u) + (c + (d - c) * v) * u
        self.assertEqual(exact(result), Fraction(28111, 300))
        self.assertEqual(exact(result), power_first)
        self.assertEqual(exact(result), speed_first)
        self.assertEqual(result.references["standard_issues"][ISSUE_004], "RESOLVED")

        for table_index, columns, inputs in (
            (10, (0, 1), case), (7, (3, 4), C | {"rated_output_power_kw": "0.65"}),
        ):
            table = self.pack.tables[table_index]
            for index in (0, 1):
                for column in columns:
                    with self.subTest(table=table.number, row=index, column=column):
                        # Isolate the numeric kernel from pack identity validation.
                        rows = list(table.rows)
                        cells = list(rows[index].efficiencies)
                        cells[column] = "—"
                        rows[index] = replace(rows[index], efficiencies=tuple(cells))
                        tables = list(self.pack.tables)
                        tables[table_index] = replace(table, rows=tuple(rows))
                        missing = self.calculator.evaluate(inputs, replace(self.pack, tables=tuple(tables)))
                        self.assertEqual(missing.evaluation_status, "INSUFFICIENT_DATA")
                        self.assertNotIn("grade_1", missing.thresholds)

    def test_power_interval_direct_and_lower_bound_one_dimensional_only(self):
        cases = (
            (BASE | {"poles": "4"}, "380", "400", "1000", "1000.01"),
            (C | {"rated_speed_rpm": "300"}, "300", "315", "1250", "1250.01"),
            (D, "3000", "3150", "8000", None),
        )
        for case, between, lower, inside, above in cases:
            interpolation = self.evaluate(case, rated_output_power_kw=between)
            lookup = interpolation.references["grade_lookups"]["grade_1"]
            self.assertEqual(lookup["power_interval_lower_endpoint_kw"], lower)
            self.assertEqual(lookup["method"], "LINEAR_INTERPOLATION")
            self.assertEqual(self.evaluate(case, rated_output_power_kw=lower).thresholds,
                             self.evaluate(case, rated_output_power_kw=inside).thresholds)
            if above:
                self.assertEqual(self.evaluate(case, rated_output_power_kw=above).evaluation_status, "OUT_OF_STANDARD_SCOPE")
        for case, power, speed in ((C, "300", "550"), (C, "300", "275"), (D, "3000", "2250")):
            missing = self.evaluate(case, rated_output_power_kw=power, rated_speed_rpm=speed)
            self.assertEqual(missing.reason_codes, ("NO_POWER_ENDPOINT",))
            self.assertFalse(missing.thresholds)
        self.assertEqual(self.evaluate(D, rated_output_power_kw="3150", rated_speed_rpm="2250").evaluation_status, "SUCCESS")

    def test_scope_and_input_do_not_guess_voltage_cooling_or_frequency(self):
        for changes, reason in (
            ({"rated_voltage_v": "1140.01"}, "VOLTAGE_OUT_OF_SCOPE"),
            ({"rated_frequency_hz": "5～120"}, "FREQUENCY_OUT_OF_SCOPE"),
            ({"rated_frequency_hz": "60"}, "FREQUENCY_OUT_OF_SCOPE"),
        ):
            self.assertEqual(self.evaluate(**changes).reason_codes, (reason,))
        self.assertEqual(self.evaluate(rated_voltage_v="1140").evaluation_status, "SUCCESS")
        self.assertEqual(self.evaluate(D, rated_voltage_v="3").reason_codes, ("VOLTAGE_OUT_OF_SCOPE",))
        self.assertEqual(self.evaluate(D, rated_speed_rpm="3000.01").reason_codes, ("SPEED_OUT_OF_SCOPE",))
        self.assertEqual(self.evaluate(D, cooling_method="W").reason_codes, ("COOLING_OUT_OF_SCOPE",))
        self.assertEqual(self.evaluate(D, cooling_method=None).missing_fields, ("cooling_method",))
        self.assertEqual(self.evaluate(C, rated_speed_rpm=None).missing_fields, ("rated_speed_rpm",))
        for bad in (True, 85.9, "0.859", "NaN", "Infinity", "100.01", "85.9%", "1e99"):
            self.assertEqual(self.evaluate(rated_efficiency_pct=bad).invalid_fields, ("rated_efficiency_pct",))
        for invalid in ("1e+", "sNaN5", "#VALUE!", "=50", 50.0):
            self.assertEqual(self.evaluate(rated_frequency_hz=invalid).invalid_fields, ("rated_frequency_hz",))
        self.assertEqual(self.evaluate(C, rated_frequency_hz="5～120", poles="16").thresholds, self.evaluate(C).thresholds)

    def test_independent_numeric_profile_and_frozen_conformance_vectors(self):
        import jsonschema

        profile = json.loads((NUMERIC / "equipeffi_motor_pmsm_numeric_profile_v1.json").read_text(encoding="utf-8"))
        lock = json.loads((ROOT / "platform-lock.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["numeric_contract_source"]["commit_sha"], lock["commit_sha"])
        self.assertEqual(profile["numeric_contract_source"]["path"], lock["numeric_contract"]["path"])
        self.assertEqual(profile["authoritative_scopes"], ["motor_pmsm"])
        self.assertFalse(profile["platform_default"])
        self.assertEqual(profile["numeric_profile_id"], PROFILE_ID)
        schema_path = ROOT / "tests/fixtures/numeric/conformance_vector_v1.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        vectors = json.loads((NUMERIC / "equipeffi_motor_pmsm_conformance_v1.json").read_text(encoding="utf-8"))
        for vector in vectors:
            with self.subTest(case_id=vector["case_id"]):
                jsonschema.validate(vector, schema)
                self.assertEqual(vector["numeric_profile_id"], PROFILE_ID)
                self.assertEqual(vector["authority_scope"], "motor_pmsm")
                if vector["category"] == "profile_mismatch_rejection":
                    with self.assertRaises(PmsmPackError):
                        self.calculator.evaluate(vector["inputs"], self.pack, numeric_profile_id=vector["requested_profile"])
                    continue
                for rounding in (ROUND_DOWN, ROUND_UP):
                    with localcontext() as context:
                        context.prec, context.rounding = 2, rounding
                        actual = self.calculator.evaluate(vector["inputs"], self.pack, numeric_profile_id=PROFILE_ID)
                    expected = vector["expected_business_result"]
                    self.assertEqual((actual.evaluation_status, actual.grade), (expected["evaluation_status"], expected["grade"]))
                    self.assertEqual(actual.references["numeric_profile_id"], PROFILE_ID)
                    if "expected_reference_value" in vector:
                        self.assertEqual(actual.thresholds["grade_1"]["exact"], vector["expected_reference_value"])
                    if "display_value" in vector:
                        self.assertEqual(actual.thresholds["grade_1"]["display"], vector["display_value"])
                    if "normalized_value" in vector:
                        self.assertEqual(actual.normalized_numbers["rated_voltage_v"], vector["normalized_value"]["rated_voltage_v"])
                    if "expected_error" in vector:
                        self.assertIn(vector["expected_error"]["code"], actual.reason_codes)
