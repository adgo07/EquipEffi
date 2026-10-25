"""Core GB 18613 calculator and derived-pack regression coverage."""
from __future__ import annotations

import copy
import json
from decimal import ROUND_CEILING, localcontext
from pathlib import Path
import unittest

from equipeffi.domain.devices.motor.calculator import DECIMAL_PROFILE_ID, Gb18613MotorCalculator, MotorPackError

ROOT = Path(__file__).resolve().parents[2]
PACK_FILE = ROOT / "src/equipeffi/resources/standards/gb18613_2020.json"


class MotorCalculatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK_FILE.read_text(encoding="utf-8"))

    def setUp(self):
        self.calc = Gb18613MotorCalculator()

    def ev(self, table, power, efficiency=None, *, poles=None, speed=None, voltage="0.38", frequency="50", basis=None, category_id=None, pack=None, **extra):
        category_id = category_id or {1: "three_phase_induction", 2: "capacitor_start", 3: "capacitor_run", 4: "two_value_capacitor", 5: "ac_fan_capacitor_run", 6: "ac_fan_brushless_dc"}[table]
        values = {"category_id": category_id, "rated_output_power_kw": power, **extra}
        if efficiency is not None:
            values["measured_efficiency_pct"] = efficiency
        if poles is not None:
            values["poles"] = str(poles)
        if speed is not None:
            values["max_nameplate_speed_rpm"] = speed
        if table <= 4:
            values.update(rated_voltage_kv=voltage, rated_frequency_hz=frequency)
        if basis is not None:
            values["efficiency_basis_status"] = basis
        return self.calc.evaluate(values, self.pack if pack is None else pack)

    def test_pack_source_inventory_and_blank_dash_provenance(self):
        self.assertEqual(self.pack["numeric_profile_id"], DECIMAL_PROFILE_ID)
        self.assertEqual((self.pack["source_files"]["mapping"]["revision"], self.pack["source_files"]["source_workbook"]["revision"]), ("A.2", "A.1"))
        self.assertEqual(self.pack["counts"], {"power_rows": 108, "threshold_cells": 1182, "threshold_values": 1149, "horizontal_dashes": 32, "source_blanks": 1})
        row = next(x for x in self.pack["tables"][2]["rows"] if x["source_row"] == 14)
        item = row["branches"]["poles_4"]["grade_1"]
        self.assertEqual((item["state"], item["source_state"], item["source_cell"], item["source_text"]), ("NO_INDICATOR", "SOURCE_BLANK", "C14", ""))
        dash = self.pack["tables"][1]["rows"][0]["branches"]["poles_2"]["grade_1"]
        self.assertEqual((dash["state"], dash["source_state"], dash["source_text"]), ("NO_INDICATOR", "HORIZONTAL_DASH", "—"))

    def test_all_six_tables_have_a_unique_calculation_route(self):
        cases = ((1,"0.12",2,None),(2,"0.25",6,None),(3,"0.75",4,None),(4,"0.25",4,None),(5,"0.75",4,None),(6,"0.15",None,"1300"))
        for table,power,poles,speed in cases:
            with self.subTest(table=table):
                result = self.ev(table,power,"90",poles=poles,speed=speed)
                self.assertEqual(result.evaluation_status,"SUCCESS")
                self.assertEqual(result.trace[0]["table_id"],f"GB18613-T{table:02d}")
                self.assertEqual(result.trace[0]["numeric_profile_id"],DECIMAL_PROFILE_ID)
                self.assertIn("required_test_basis",result.references)

    def test_bc01_04_direct_and_interpolated_grade_boundaries(self):
        for eta,grade in (("71.3","2"),("71.4","1"),("71.5","1"),("66.4","3"),("66.5","2"),("66.6","2"),("60.7",None),("60.8","3"),("60.9","3")):
            self.assertEqual(self.ev(1,"0.12",eta,poles=2).grade,grade)
        for eta,grade in (("72.24","3"),("72.25","2"),("72.26","2")):
            result=self.ev(1,"0.15",eta,poles=4)
            self.assertEqual(result.grade,grade)
            self.assertEqual(result.thresholds["grade_2"]["exact"],{"numerator":"289","denominator":"4","unit":"percent_point"})
            self.assertEqual(result.thresholds["grade_2"]["display_text"],"72.25")
            self.assertEqual(result.trace[0]["method"],"LINEAR_INTERPOLATION")
        below=self.ev(1,"0.12","71.3999",poles=2)
        self.assertEqual(below.grade,"2")

    def test_bc05_table1_terminal_range_is_direct_but_starts_interpolation(self):
        expected=(("250","193","2"),("275","1255","13"),("282.5","1931","20"),("300","2511","26"),("315","483","5"),("500","483","5"),("1000","483","5"))
        for power,numerator,denominator in expected:
            result=self.ev(1,power,"96.58",poles=6)
            self.assertEqual((result.thresholds["grade_2"]["exact"]["numerator"],result.thresholds["grade_2"]["exact"]["denominator"]),(numerator,denominator))
        self.assertEqual(self.ev(1,"275","96.54",poles=6).grade,"2")
        self.assertEqual(self.ev(1,"300","96.54",poles=6).grade,"3")
        self.assertEqual(self.ev(1,"300","96.58",poles=6).trace[0]["power_endpoints"][1]["source_power_text"],"315~1000")

    def test_bc06_08_bc13_and_bc23_respect_table_branch_and_holes(self):
        for eta,grade in (("61.9","1"),("58.0","2"),("54.0","3")):
            result=self.ev(2,"0.25",eta,poles=6)
            self.assertEqual((result.grade,result.trace[0]["table_id"]),(grade,"GB18613-T02"))
        self.assertEqual(self.ev(3,"2.2",None,poles=4).reason_codes,("NO_INDICATOR",))
        self.assertEqual(self.ev(3,"1.8","80",poles=4).reason_codes,("NO_INDICATOR",))
        self.assertEqual(self.ev(2,"0.15","80",poles=2).reason_codes,("NO_INDICATOR",))
        self.assertEqual(self.ev(4,"0.25","75",poles=2).reason_codes,("NO_INDICATOR",))
        t4=self.ev(4,"0.25","73.5",poles=4)
        self.assertEqual([t4.thresholds[f"grade_{n}"]["display_text"] for n in (1,2,3)],["73.5","68.5","62"])
        self.assertEqual(self.ev(5,"1.1","80",poles=8).reason_codes,("NO_INDICATOR",))
        t5=self.ev(5,"1.1","77",poles=6)
        self.assertEqual([t5.thresholds[f"grade_{n}"]["display_text"] for n in (1,2,3)],["77","73","69"])
        self.assertEqual((self.ev(3,"0.75","80",poles=4).grade,self.ev(5,"0.75","80",poles=4).grade),("2","1"))

    def test_bc09_12_speed_groups_use_right_inclusive_edges_and_keep_source_value(self):
        for speed,branch,n,d in (("500","rpm_band_1","613","10"),("700","rpm_band_2","318","5"),("1000","rpm_band_3","703","10")):
            result=self.ev(6,"0.01","90",speed=speed)
            self.assertEqual(result.trace[0]["branch_id"],branch)
            self.assertEqual(result.thresholds["grade_1"]["exact"],{"numerator":n,"denominator":d,"unit":"percent_point"})
        at,above=self.ev(6,"0.15","85",speed="1300"),self.ev(6,"0.15","85",speed="1300.0001")
        self.assertEqual((at.trace[0]["branch_id"],at.trace[0]["speed_band_label"]),("rpm_band_4","1000<r≤1300 r/min"))
        self.assertEqual((above.trace[0]["branch_id"],above.trace[0]["speed_band_label"]),("rpm_band_5","r>1300 r/min"))
        self.assertEqual(at.thresholds["grade_1"]["exact"],{"numerator":"406","denominator":"5","unit":"percent_point"})
        self.assertEqual(above.thresholds["grade_1"]["exact"],{"numerator":"163","denominator":"2","unit":"percent_point"})
        self.assertEqual(self.ev(6,"0.075","72.4",speed="1400").thresholds["grade_3"]["display_text"],"72")
        self.assertEqual(self.ev(6,"0.0675","80",speed="1400").thresholds["grade_3"]["exact"],{"numerator":"72","denominator":"1","unit":"percent_point"})

    def test_bc15_16_25_26_basis_and_table5_speed_requirement(self):
        for basis in ("NAMEPLATE_ONLY","KNOWN_NONCONFORMING","UNKNOWN"):
            self.assertEqual(self.ev(5,"0.75","80",poles=4,basis=basis).evaluation_status,"INSUFFICIENT_DATA")
        self.assertEqual(self.ev(6,"0.15","90",speed="1300",basis="INSEPARABLE_MOTOR_ONLY").reason_codes,("INSEPARABLE_MOTOR_ONLY",))
        self.assertEqual(self.ev(5,"0.75","80",poles=4).grade,"1")
        self.assertEqual(self.ev(6,"0.15","85",speed="1300",rated_frequency_hz="0",rated_voltage_kv="0").evaluation_status,"SUCCESS")

    def test_bc17_20_scope_checks_precede_missing_and_keep_unknown_category_explicit(self):
        self.assertEqual(self.ev(1,"0.119",None,poles=2).evaluation_status,"OUT_OF_STANDARD_SCOPE")
        self.assertEqual(self.ev(1,"0.12","80",poles=2,voltage="0.9999").evaluation_status,"SUCCESS")
        for power in ("1000.001",):
            self.assertEqual(self.ev(1,power,None,poles=2).evaluation_status,"OUT_OF_STANDARD_SCOPE")
        for voltage in ("1","1.0001"):
            self.assertEqual(self.ev(1,"0.12",None,poles=2,voltage=voltage).evaluation_status,"OUT_OF_STANDARD_SCOPE")
        self.assertEqual(self.ev(1,"0.12","80",poles=2,frequency="60").evaluation_status,"OUT_OF_STANDARD_SCOPE")
        self.assertEqual(self.ev(2,"0.25","80",poles=4,voltage="0.69").evaluation_status,"SUCCESS")
        self.assertEqual(self.ev(2,"0.25",None,poles=4,voltage="0.6901").evaluation_status,"OUT_OF_STANDARD_SCOPE")
        unknown=self.calc.evaluate({"category_id":"UNCERTAIN_CATEGORY"},self.pack)
        self.assertEqual(unknown.reason_codes,("CATEGORY_UNCERTAIN",))

    def test_frequency_text_is_out_of_scope_only_for_tables_one_to_four(self):
        cases = ((1, "0.12", 2), (2, "0.25", 6), (3, "0.75", 4), (4, "0.25", 4))
        for table, power, poles in cases:
            with self.subTest(table=table):
                result = self.ev(table, power, "80", poles=poles, frequency="5~120")
                self.assertEqual(result.evaluation_status, "OUT_OF_STANDARD_SCOPE")
                self.assertEqual(result.reason_codes, ("RATED_FREQUENCY_OUT_OF_SCOPE",))
                self.assertIsNone(result.grade)

        table5 = self.ev(5, "0.75", "80", poles=6, rated_frequency_hz="5~120")
        self.assertEqual(table5.evaluation_status, "SUCCESS")
        self.assertEqual(table5.trace[0]["rated_frequency_hz_raw"], "5~120")
        self.assertEqual(self.ev(5, "0.75", "80", poles=6, rated_frequency_hz="5-120").evaluation_status, "SUCCESS")
        table6 = self.ev(6, "0.15", "85", poles=10, speed="1300", rated_frequency_hz="5~120")
        self.assertEqual(table6.evaluation_status, "SUCCESS")
        self.assertEqual(table6.trace[0]["rated_frequency_hz_raw"], "5~120")
        self.assertIsNone(table6.trace[0]["poles"])
        self.assertEqual(table6.trace[0]["poles_input_raw"], "10")

    def test_poles_require_positive_even_integer_and_respect_table_coverage(self):
        cases = ((1, "0.12"), (2, "0.25"), (3, "0.75"), (4, "0.25"), (5, "0.75"))
        for table, power in cases:
            with self.subTest(table=table):
                result = self.ev(table, power, "80", poles=10)
                self.assertEqual(result.evaluation_status, "OUT_OF_STANDARD_SCOPE")
                self.assertEqual(result.reason_codes, ("POLE_COUNT_OUT_OF_SCOPE",))

        for invalid in ("1", "0", "-2", "2.5", "NaN", "Infinity", "=SUM(A1)"):
            with self.subTest(poles=invalid):
                result = self.ev(6, "0.15", "85", speed="1300", poles=invalid)
                self.assertEqual(result.evaluation_status, "INVALID_INPUT")
                self.assertIn("poles", result.invalid_fields)
        for invalid in (True, 2.0, []):
            result = self.calc.evaluate({"category_id": "ac_fan_brushless_dc", "rated_output_power_kw": "0.15", "measured_efficiency_pct": "85", "max_nameplate_speed_rpm": "1300", "poles": invalid}, self.pack)
            self.assertEqual(result.evaluation_status, "INVALID_INPUT")
            self.assertIn("poles", result.invalid_fields)

        omitted = self.ev(6, "0.15", "85", speed="1300")
        self.assertEqual(omitted.evaluation_status, "SUCCESS")
        self.assertIsNone(omitted.trace[0]["poles"])
        self.assertIsNone(omitted.trace[0]["poles_input_raw"])

    def test_frequency_formulas_errors_and_malformed_numbers_remain_invalid(self):
        for invalid in ("=50", "#DIV/0!", "Infinity", "1e31", "1e+", "50.2.3", "1,000", "0", "-1", "x" * 129, " " * 129):
            with self.subTest(frequency=invalid):
                result = self.ev(1, "0.12", "80", poles=2, frequency=invalid)
                self.assertEqual(result.evaluation_status, "INVALID_INPUT")
                self.assertIn("rated_frequency_hz", result.invalid_fields)
        for invalid in ("=50", "#DIV/0!", "1e31", "1e+"):
            result = self.ev(6, "0.15", "85", speed="1300", rated_frequency_hz=invalid)
            self.assertEqual(result.evaluation_status, "INVALID_INPUT")
            self.assertIn("rated_frequency_hz", result.invalid_fields)
        for invalid in (True, [], 50.0):
            result = self.calc.evaluate({"category_id": "three_phase_induction", "rated_output_power_kw": "0.12", "measured_efficiency_pct": "80", "rated_voltage_kv": "0.38", "rated_frequency_hz": invalid, "poles": "2"}, self.pack)
            self.assertEqual(result.evaluation_status, "INVALID_INPUT")
            self.assertIn("rated_frequency_hz", result.invalid_fields)

    def test_bc21_24_efficiency_speed_and_lexical_bounds(self):
        self.assertEqual(self.ev(1,"0.12","85.9",poles=2).evaluation_status,"SUCCESS")
        for efficiency in ("0","0.859","0.999","100.001","-1","NaN","Infinity"):
            self.assertEqual(self.ev(1,"0.12",efficiency,poles=2).evaluation_status,"INVALID_INPUT")
        for efficiency in ("1","100"):
            self.assertEqual(self.ev(1,"0.12",efficiency,poles=2).evaluation_status,"SUCCESS")
        for speed in ("0","-1","NaN","Infinity"):
            self.assertEqual(self.ev(6,"0.15","80",speed=speed).evaluation_status,"INVALID_INPUT")
        self.assertEqual(self.ev(6,"0.15","80").missing_fields,("max_nameplate_speed_rpm",))
        values={"category_id":"three_phase_induction","rated_output_power_kw":0.12,"rated_voltage_kv":"0.38","rated_frequency_hz":"50","poles":"2","measured_efficiency_pct":"80"}
        self.assertEqual(self.calc.evaluate(values,self.pack).evaluation_status,"INVALID_INPUT")
        for value in ("1e31","1e-31","1"+"0"*30,"1e+"+"0"*126):
            result=self.calc.evaluate({**values,"rated_output_power_kw":value},self.pack)
            self.assertEqual(result.evaluation_status,"INVALID_INPUT")
        self.assertEqual(self.calc.evaluate({**values,"rated_output_power_kw":"1e+"+"0"*125},self.pack).evaluation_status,"SUCCESS")

    def test_bc22_execution_fault_missing_input_and_no_indicator_are_distinct(self):
        broken=copy.deepcopy(self.pack); broken["tables"]=broken["tables"][:-1]
        with self.assertRaises(MotorPackError):
            self.calc.evaluate({"category_id":"three_phase_induction"},broken)
        missing=self.ev(1,"0.12",None,poles=2)
        self.assertEqual((missing.missing_fields,missing.thresholds["grade_1"]["state"]),(("measured_efficiency_pct",),"AVAILABLE"))
        no_indicator=self.ev(3,"2.2",None,poles=4)
        self.assertEqual((no_indicator.reason_codes,no_indicator.missing_fields),(("NO_INDICATOR",),()))

    def test_nonapplicable_fields_only_get_type_and_nonnegative_validation(self):
        result=self.calc.evaluate({"category_id":"ac_fan_brushless_dc","rated_output_power_kw":"0.15","measured_efficiency_pct":"85","max_nameplate_speed_rpm":"1300","rated_voltage_kv":"0","rated_frequency_hz":"60","poles":"10"},self.pack)
        self.assertEqual(result.evaluation_status,"SUCCESS")
        for field in ("rated_voltage_kv","rated_frequency_hz"):
            bad=self.calc.evaluate({"category_id":"ac_fan_brushless_dc","rated_output_power_kw":"0.15","measured_efficiency_pct":"85","max_nameplate_speed_rpm":"1300",field:"-1"},self.pack)
            self.assertEqual(bad.evaluation_status,"INVALID_INPUT")

    def test_results_do_not_depend_on_ambient_decimal_context(self):
        values={"category_id":"three_phase_induction","rated_output_power_kw":"0.14","rated_voltage_kv":"0.38","rated_frequency_hz":"50","poles":"4","measured_efficiency_pct":"71.43"}
        baseline=self.calc.evaluate(values,self.pack)
        with localcontext() as context:
            context.prec=2; context.rounding=ROUND_CEILING
            altered=self.calc.evaluate(values,self.pack)
        self.assertEqual((altered.grade,altered.thresholds,altered.trace),(baseline.grade,baseline.thresholds,baseline.trace))


if __name__ == "__main__":
    unittest.main()
