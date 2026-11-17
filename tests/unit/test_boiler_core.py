"""GB24500批准映射边界、全源格及精确Profile。"""
from copy import deepcopy
from decimal import localcontext, ROUND_DOWN
from fractions import Fraction
from pathlib import Path
import json
import unittest
from equipeffi.domain.devices.boiler.calculator import Gb24500BoilerCalculator, BoilerPackError, PROFILE_ID, exact_decimal
from equipeffi.infrastructure.standards.boiler_repository import load_boiler_pack
from tools.build_gb24500_boiler_pack import build_pack

BASE = dict(category_id="steam_biomass", fuel="生物质", rated_capacity="10", rated_pressure_mpa="0.1", qnet_kj_kg="9000", efficiency_pct="88")


class BoilerCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack, _ = load_boiler_pack()
        cls.calc = Gb24500BoilerCalculator()

    def evaluate(self, **updates):
        return self.calc.evaluate(BASE | updates, self.pack)

    def test_fixed_source_all_79_values_and_derived_identity(self):
        self.assertEqual(build_pack(), self.pack)
        resource=Path(__file__).resolve().parents[2]/"src/equipeffi/resources/standards/gb24500_2020_candidate.json"
        self.assertNotIn(b"\r",resource.read_bytes())
        from openpyxl import load_workbook
        from tools.build_gb24500_boiler_pack import ROOT, WORKBOOK
        book = load_workbook(ROOT / WORKBOOK, data_only=True)
        for cell in self.pack["cells"]:
            sheet, ref = cell["source_cell"].split("!")
            self.assertEqual(Fraction(str(book[sheet][ref].value)), Fraction(cell["value"]))
        self.assertEqual(book["限定值与来源"]["B5"].value, 97)
        self.assertEqual(len(self.pack["cells"]), 78)

    def test_every_source_threshold_and_adjacent_exact_values(self):
        coal_q = {"烟煤Ⅰ类": "14400", "烟煤Ⅱ类": "17700", "烟煤Ⅲ类": "21001", "贫煤": "17700", "无烟煤Ⅱ类": "21000", "无烟煤Ⅲ类": "21000", "褐煤": "11500"}
        coal_v = {"烟煤Ⅰ类": "25", "烟煤Ⅱ类": "25", "烟煤Ⅲ类": "25", "贫煤": "15", "无烟煤Ⅱ类": "6.49", "无烟煤Ⅲ类": "6.5", "褐煤": "37.01"}
        heat_by_branch = {"T4-B1": "gas", "T4-B2": "gas_condensing_lower", "T4-B3": "gas_condensing_higher", "T4-B4": "oil", "T4-B5": "chamber_coal"}
        fuel_by_heat = {"gas": "天然气", "gas_condensing_lower": "天然气", "gas_condensing_higher": "天然气", "oil": "燃油", "chamber_coal": "煤"}
        for row in self.pack["cells"]:
            n = row["table_number"]
            values = dict(BASE)
            if n in {1, 2}:
                values.update(category_id="steam_layer_coal" if n == 1 else "steam_fluid_coal", fuel=row["fuel"],
                    qnet_kj_kg=coal_q[row["fuel"]], vdaf_pct=coal_v[row["fuel"]])
            elif n == 4:
                heat = heat_by_branch[row["branch"]]
                values.update(category_id="steam_"+heat, fuel=fuel_by_heat[heat], qnet_kj_kg="")
            if n in {1, 3}:
                values["rated_capacity"] = "1" if row["capacity_bucket"] == "SMALL" else "21"
            group = [r for r in self.pack["cells"] if r["table_number"] == n and r["branch"] == row["branch"] and r["capacity_bucket"] == row["capacity_bucket"]]
            for delta in ("-0.00000000000000000001", "0", "0.00000000000000000001"):
                value = Fraction(row["value"]) + Fraction(delta)
                # finite decimal exact lexical, independent of calculator formatting
                from decimal import Decimal
                with localcontext() as c:
                    c.prec = 50
                    lexical = str(Decimal(value.numerator) / Decimal(value.denominator))
                result = self.calc.evaluate(values | {"efficiency_pct": lexical}, self.pack)
                expected = next((str(r["grade"]) for r in sorted(group,key=lambda x:x["grade"]) if value >= Fraction(r["value"])), None)
                with self.subTest(cell=row["source_cell"], delta=delta):
                    self.assertEqual(result.evaluation_status, "SUCCESS")
                    self.assertEqual(result.grade, expected)
                    self.assertEqual(result.minimum_limit["met"], value >= Fraction(group[2]["value"]))

    def test_biomass_owner_order_and_8374_equality(self):
        for eta, design, grade, met in (("88","90","1",False),("79","75","3",True),("75","75","3",True),("90","90","1",True),("74.99","75",None,False)):
            r=self.evaluate(qnet_kj_kg="8373.99", efficiency_pct=eta, design_limit_pct=design)
            self.assertEqual((r.grade,r.minimum_limit["met"]),(grade,met))
            self.assertEqual(r.thresholds["grade_3"]["value"],design)
            self.assertEqual(r.thresholds["grade_3"]["original_table_value"],"80")
        self.assertEqual(self.evaluate(qnet_kj_kg="8374",efficiency_pct="79").grade,None)
        for design in ("", "0", "-1"):
            self.assertEqual(self.evaluate(qnet_kj_kg="8000",design_limit_pct=design).evaluation_status,"INVALID_INPUT")
        self.assertEqual(self.evaluate(qnet_kj_kg="8374",design_limit_pct="75").evaluation_status,"INVALID_INPUT")

    def test_pressure_scope_priority_and_capacity_boundaries(self):
        for p, status in (("0.099","OUT_OF_STANDARD_SCOPE"),("0.1","SUCCESS"),("3.799","SUCCESS"),("3.8","OUT_OF_STANDARD_SCOPE")):
            self.assertEqual(self.evaluate(rated_pressure_mpa=p).evaluation_status,status)
        self.assertEqual(self.evaluate(rated_pressure_mpa="3.8", qnet_kj_kg="", efficiency_pct="").evaluation_status,"OUT_OF_STANDARD_SCOPE")
        for cap, status in (("0.099","OUT_OF_STANDARD_SCOPE"),("0.1","SUCCESS")):
            self.assertEqual(self.evaluate(category_id="hot_water_biomass",rated_capacity=cap,rated_pressure_mpa="4").evaluation_status,status)
        for category, cap, expected in (("steam_biomass","10","88"),("steam_biomass","10.00001","91"),("hot_water_biomass","7","88"),("hot_water_biomass","7.00001","91")):
            self.assertEqual(self.evaluate(category_id=category,rated_capacity=cap).thresholds["grade_1"]["value"],expected)
        for form, boundary in (("steam", "20"),("hot_water","14")):
            for cap, first in ((boundary,"85"),(str(Fraction(boundary)+1),"86")):
                self.assertEqual(self.evaluate(category_id=form+"_layer_coal",rated_capacity=cap,fuel="烟煤Ⅱ类",qnet_kj_kg="17700",vdaf_pct="25").thresholds["grade_1"]["value"],first)

    def test_coal_quality_endpoints_and_no_borrowing(self):
        for fuel,q,v,ok in (("烟煤Ⅰ类","14400","25",True),("烟煤Ⅰ类","14399.99","25",False),
            ("烟煤Ⅱ类","21000","25",True),("烟煤Ⅱ类","21000.01","25",False),
            ("烟煤Ⅲ类","21000","25",False),("烟煤Ⅲ类","21000.01","25",True),
            ("贫煤","17700","10",False),("贫煤","17700","10.01",True),("贫煤","17700","20",True),("贫煤","17700","20.01",False),
            ("无烟煤Ⅱ类","21000","6.49",True),("无烟煤Ⅱ类","21000","6.5",False),
            ("无烟煤Ⅲ类","21000","6.5",True),("无烟煤Ⅲ类","21000","10",True),("无烟煤Ⅲ类","21000","10.01",False),
            ("褐煤","11500","37",False),("褐煤","11500","37.01",True)):
            r=self.evaluate(category_id="steam_fluid_coal",fuel=fuel,qnet_kj_kg=q,vdaf_pct=v,rated_capacity="")
            self.assertEqual(r.evaluation_status,"SUCCESS" if ok else "INSUFFICIENT_DATA",(fuel,q,v))
        self.assertEqual(self.evaluate(category_id="steam_layer_coal",fuel="烟煤Ⅰ类",qnet_kj_kg="14400",vdaf_pct="25").evaluation_status,"INSUFFICIENT_DATA")

    def test_condensing_electric_mixed_and_unopened(self):
        for heat, eta, grade in (("gas_condensing_lower","103","1"),("gas_condensing_higher","93","1"),("gas","96","1")):
            r=self.evaluate(category_id="steam_"+heat,fuel="天然气",qnet_kj_kg="",rated_capacity="",efficiency_pct=eta)
            self.assertEqual(r.grade,grade)
        for eta,met in (("96.999999999999999","未达到限定值"),("97","达到限定值"),("98","达到限定值")):
            r=self.evaluate(category_id="steam_electric",fuel="电",qnet_kj_kg="",rated_capacity="",efficiency_pct=eta)
            self.assertEqual((r.grade,r.ui_conclusion,r.thresholds),(None,met,{}))
            self.assertEqual(r.references["efficiency_basis"],"NOT_APPLICABLE")
        for category,status in (("steam_mixed","INSUFFICIENT_DATA"),("UNCERTAIN_CATEGORY","INSUFFICIENT_DATA"),("OTHER_CATEGORY","OUT_OF_STANDARD_SCOPE"),("ORGANIC_HEAT_CARRIER",None)):
            self.assertEqual(self.calc.evaluate(dict(category_id=category),self.pack).evaluation_status,status)
        self.assertEqual(self.evaluate(category_id="steam_mixed",rated_pressure_mpa="3.8").evaluation_status,"OUT_OF_STANDARD_SCOPE")

    def test_profile_rejection_ambient_and_resources(self):
        for value in (88.0,True,"NaN","Infinity","1e31","1/2"):
            self.assertEqual(self.evaluate(efficiency_pct=value).evaluation_status,"INVALID_INPUT")
        with localcontext() as context:
            context.prec=2;context.rounding=ROUND_DOWN
            self.assertEqual(self.evaluate(efficiency_pct="87.9999999999999999999999").grade,"2")
        with self.assertRaises(BoilerPackError):
            self.calc.evaluate(BASE,self.pack,numeric_profile_id="PUMP")
        pack=deepcopy(self.pack);pack["cells"][0]["value"]="0"
        with self.assertRaises(BoilerPackError):self.calc.evaluate(BASE,pack)

    def test_frozen_numeric_vectors_execute(self):
        path=Path(__file__).resolve().parents[2]/"specs/equipment_efficiency/numeric/equipeffi_boiler_conformance_v1.json"
        for vector in json.loads(path.read_text(encoding="utf-8")):
            with self.subTest(case=vector["case_id"]):
                self.assertEqual(vector["numeric_profile_id"],PROFILE_ID)
                result=self.calc.evaluate(vector["inputs"],self.pack,numeric_profile_id=vector["numeric_profile_id"])
                self.assertEqual(dict(evaluation_status=result.evaluation_status,grade=result.grade),vector["expected_business_result"])

    def test_fresh_checkout_file_identity_is_stable(self):
        from tempfile import TemporaryDirectory
        from hashlib import sha256
        from tests.test_motor_candidate_file_identity import fresh_checkouts
        path=Path("src/equipeffi/resources/standards/gb24500_2020_candidate.json")
        with TemporaryDirectory() as directory:
            for mode,checkout,expected in fresh_checkouts(Path(directory),(path,)):
                with self.subTest(autocrlf=mode):
                    self.assertEqual((checkout/path).read_bytes(),expected[path])
                    _pack,digest=load_boiler_pack(checkout/path)
                    self.assertEqual(digest,sha256(expected[path]).hexdigest().upper())
