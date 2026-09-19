from __future__ import annotations

import unittest
from decimal import Decimal

from equipeffi.application.services.v4_validation import (
    V4ValidationService,
    _metadata_numeric_constraints,
    _metadata_non_negative_constraints,
    _metadata_range_constraints,
    _metadata_percentage_limits,
)


class V4ValidationTests(unittest.TestCase):
    def test_common_required_and_quantity_are_checked_without_rewriting(self):
        values = {"device_name": " A ", "model": "M1", "quantity": 0, "category": "变压器"}
        issues = V4ValidationService.validate("变压器", values)
        codes = {issue.code for issue in issues}
        self.assertIn("required", codes)  # 缺少铭牌照片
        self.assertIn("positive_integer", codes)
        self.assertIn("whitespace", {issue.code for issue in issues})
        self.assertEqual(values["device_name"], " A ")

    def test_transformer_numeric_validation_pilot_uses_metadata_v4_ids(self):
        constraints = _metadata_numeric_constraints("变压器")
        self.assertEqual(constraints, {
            "positive": ("rated_capacity", "no_load_loss", "load_loss"),
            "integer": ("quantity",),
            "percentage": (),
        })
        issues = V4ValidationService.validate("变压器", {
            "device_name": "T", "model": "T1", "quantity": 1,
            "category": "110kV油浸式三相双绕组无励磁调压电力变压器",
            "rated_capacity": 0, "no_load_loss": "待复核", "load_loss": -1,
            "photo": "photo",
        })
        by_field = {(issue.field, issue.code) for issue in issues}
        self.assertIn(("rated_capacity", "positive"), by_field)
        self.assertIn(("no_load_loss", "number"), by_field)
        self.assertIn(("load_loss", "positive"), by_field)

    def test_boiler_efficiency_limits_use_metadata_union_and_standard_condition(self):
        self.assertEqual(
            _metadata_percentage_limits("工业锅炉", "design_efficiency", {"condensing": "冷凝"}),
            (1, 110),
        )
        self.assertEqual(
            _metadata_percentage_limits("工业锅炉", "design_efficiency", {"condensing": "非冷凝"}),
            (1, 100),
        )

    def test_boiler_volatile_matter_uses_metadata_range_without_rewriting(self):
        self.assertEqual(
            _metadata_range_constraints("工业锅炉")["vdaf"],
            (Decimal("0"), Decimal("100")),
        )
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "链条炉排锅炉", "photo": "photo",
        }
        valid = {**base, "vdaf": 50}
        self.assertFalse(any(issue.field == "vdaf" for issue in V4ValidationService.validate("工业锅炉", valid)))
        for value in (-1, 101):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("工业锅炉", {**base, "vdaf": value})
                self.assertTrue(any(issue.field == "vdaf" and issue.code == "range" for issue in issues))
        text_value = {**base, "vdaf": "待复核"}
        issues = V4ValidationService.validate("工业锅炉", text_value)
        self.assertTrue(any(issue.field == "vdaf" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "vdaf": " 50 "}
        issues = V4ValidationService.validate("工业锅炉", whitespace_value)
        self.assertTrue(any(issue.field == "vdaf" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["vdaf"], "待复核")
        self.assertEqual(whitespace_value["vdaf"], " 50 ")

    def test_boiler_evaporation_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("工业锅炉"),
            {"positive": ("evaporation", "thermal_power", "lhv"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "电锅炉", "photo": "photo",
        }
        valid = {**base, "evaporation": 0.1}
        self.assertFalse(any(issue.field == "evaporation" for issue in V4ValidationService.validate("工业锅炉", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("工业锅炉", {**base, "evaporation": value})
                self.assertTrue(any(issue.field == "evaporation" and issue.code == "positive" for issue in issues))
        text_value = {**base, "evaporation": "待复核"}
        issues = V4ValidationService.validate("工业锅炉", text_value)
        self.assertTrue(any(issue.field == "evaporation" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "evaporation": " 0.1 "}
        issues = V4ValidationService.validate("工业锅炉", whitespace_value)
        self.assertTrue(any(issue.field == "evaporation" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["evaporation"], "待复核")
        self.assertEqual(whitespace_value["evaporation"], " 0.1 ")

    def test_boiler_thermal_power_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("工业锅炉"),
            {"positive": ("evaporation", "thermal_power", "lhv"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "电锅炉", "photo": "photo",
        }
        valid = {**base, "thermal_power": 0.1}
        self.assertFalse(any(issue.field == "thermal_power" for issue in V4ValidationService.validate("工业锅炉", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("工业锅炉", {**base, "thermal_power": value})
                self.assertTrue(any(issue.field == "thermal_power" and issue.code == "positive" for issue in issues))
        text_value = {**base, "thermal_power": "待复核"}
        issues = V4ValidationService.validate("工业锅炉", text_value)
        self.assertTrue(any(issue.field == "thermal_power" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "thermal_power": " 0.1 "}
        issues = V4ValidationService.validate("工业锅炉", whitespace_value)
        self.assertTrue(any(issue.field == "thermal_power" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["thermal_power"], "待复核")
        self.assertEqual(whitespace_value["thermal_power"], " 0.1 ")

    def test_boiler_lhv_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("工业锅炉"),
            {"positive": ("evaporation", "thermal_power", "lhv"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "燃气锅炉", "photo": "photo",
        }
        valid = {**base, "lhv": 35000}
        self.assertFalse(any(issue.field == "lhv" for issue in V4ValidationService.validate("工业锅炉", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("工业锅炉", {**base, "lhv": value})
                self.assertTrue(any(issue.field == "lhv" and issue.code == "positive" for issue in issues))
        text_value = {**base, "lhv": "待复核"}
        issues = V4ValidationService.validate("工业锅炉", text_value)
        self.assertTrue(any(issue.field == "lhv" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "lhv": " 35000 "}
        issues = V4ValidationService.validate("工业锅炉", whitespace_value)
        self.assertTrue(any(issue.field == "lhv" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["lhv"], "待复核")
        self.assertEqual(whitespace_value["lhv"], " 35000 ")

    def test_hpwh_heating_capacity_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("热泵热水机"),
            {"positive": ("heating_capacity", "rated_power", "cop"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "H", "model": "H1", "quantity": 1,
            "category": "普通型", "photo": "photo",
        }
        valid = {**base, "heating_capacity": 12.5}
        self.assertFalse(any(issue.field == "heating_capacity" for issue in V4ValidationService.validate("热泵热水机", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热泵热水机", {**base, "heating_capacity": value})
                self.assertTrue(any(issue.field == "heating_capacity" and issue.code == "positive" for issue in issues))
        text_value = {**base, "heating_capacity": "待复核"}
        issues = V4ValidationService.validate("热泵热水机", text_value)
        self.assertTrue(any(issue.field == "heating_capacity" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "heating_capacity": " 12.5 "}
        issues = V4ValidationService.validate("热泵热水机", whitespace_value)
        self.assertTrue(any(issue.field == "heating_capacity" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["heating_capacity"], "待复核")
        self.assertEqual(whitespace_value["heating_capacity"], " 12.5 ")

    def test_hpwh_rated_power_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("热泵热水机"),
            {"positive": ("heating_capacity", "rated_power", "cop"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "H", "model": "H1", "quantity": 1,
            "category": "普通型", "photo": "photo",
        }
        valid = {**base, "rated_power": 4.2}
        self.assertFalse(any(issue.field == "rated_power" for issue in V4ValidationService.validate("热泵热水机", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热泵热水机", {**base, "rated_power": value})
                self.assertTrue(any(issue.field == "rated_power" and issue.code == "positive" for issue in issues))
        text_value = {**base, "rated_power": "待复核"}
        issues = V4ValidationService.validate("热泵热水机", text_value)
        self.assertTrue(any(issue.field == "rated_power" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "rated_power": " 4.2 "}
        issues = V4ValidationService.validate("热泵热水机", whitespace_value)
        self.assertTrue(any(issue.field == "rated_power" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["rated_power"], "待复核")
        self.assertEqual(whitespace_value["rated_power"], " 4.2 ")

    def test_hpwh_cop_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("热泵热水机"),
            {"positive": ("heating_capacity", "rated_power", "cop"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "H", "model": "H1", "quantity": 1,
            "category": "普通型", "photo": "photo",
        }
        valid = {**base, "cop": 3.2}
        self.assertFalse(any(issue.field == "cop" for issue in V4ValidationService.validate("热泵热水机", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热泵热水机", {**base, "cop": value})
                self.assertTrue(any(issue.field == "cop" and issue.code == "positive" for issue in issues))
        text_value = {**base, "cop": "待复核"}
        issues = V4ValidationService.validate("热泵热水机", text_value)
        self.assertTrue(any(issue.field == "cop" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "cop": " 3.2 "}
        issues = V4ValidationService.validate("热泵热水机", whitespace_value)
        self.assertTrue(any(issue.field == "cop" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["cop"], "待复核")
        self.assertEqual(whitespace_value["cop"], " 3.2 ")

    def test_chiller_rated_power_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("热泵和冷水机组"),
            {"positive": ("cooling_capacity", "heating_capacity", "rated_power", "primary_metric_value", "aux_metric1_value", "aux_metric2_value"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "C", "model": "C1", "quantity": 1,
            "category": "蒸气压缩循环冷水（热泵）机组-舒适型", "photo": "photo",
        }
        valid = {**base, "rated_power": 4.2}
        self.assertFalse(any(issue.field == "rated_power" for issue in V4ValidationService.validate("热泵和冷水机组", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热泵和冷水机组", {**base, "rated_power": value})
                self.assertTrue(any(issue.field == "rated_power" and issue.code == "positive" for issue in issues))
        text_value = {**base, "rated_power": "待复核"}
        issues = V4ValidationService.validate("热泵和冷水机组", text_value)
        self.assertTrue(any(issue.field == "rated_power" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "rated_power": " 4.2 "}
        issues = V4ValidationService.validate("热泵和冷水机组", whitespace_value)
        self.assertTrue(any(issue.field == "rated_power" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["rated_power"], "待复核")
        self.assertEqual(whitespace_value["rated_power"], " 4.2 ")

    def test_chiller_cooling_capacity_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("热泵和冷水机组"),
            {"positive": ("cooling_capacity", "heating_capacity", "rated_power", "primary_metric_value", "aux_metric1_value", "aux_metric2_value"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "C", "model": "C1", "quantity": 1,
            "category": "蒸气压缩循环冷水（热泵）机组-舒适型", "photo": "photo",
        }
        valid = {**base, "cooling_capacity": 100.0}
        self.assertFalse(any(issue.field == "cooling_capacity" for issue in V4ValidationService.validate("热泵和冷水机组", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热泵和冷水机组", {**base, "cooling_capacity": value})
                self.assertTrue(any(issue.field == "cooling_capacity" and issue.code == "positive" for issue in issues))
        text_value = {**base, "cooling_capacity": "待复核"}
        issues = V4ValidationService.validate("热泵和冷水机组", text_value)
        self.assertTrue(any(issue.field == "cooling_capacity" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "cooling_capacity": " 100 "}
        issues = V4ValidationService.validate("热泵和冷水机组", whitespace_value)
        self.assertTrue(any(issue.field == "cooling_capacity" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["cooling_capacity"], "待复核")
        self.assertEqual(whitespace_value["cooling_capacity"], " 100 ")

    def test_chiller_heating_capacity_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("热泵和冷水机组"),
            {"positive": ("cooling_capacity", "heating_capacity", "rated_power", "primary_metric_value", "aux_metric1_value", "aux_metric2_value"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "C", "model": "C1", "quantity": 1,
            "category": "低环境温度空气源热泵（冷水）机组", "photo": "photo",
        }
        valid = {**base, "heating_capacity": 100.0}
        self.assertFalse(any(issue.field == "heating_capacity" for issue in V4ValidationService.validate("热泵和冷水机组", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热泵和冷水机组", {**base, "heating_capacity": value})
                self.assertTrue(any(issue.field == "heating_capacity" and issue.code == "positive" for issue in issues))
        text_value = {**base, "heating_capacity": "待复核"}
        issues = V4ValidationService.validate("热泵和冷水机组", text_value)
        self.assertTrue(any(issue.field == "heating_capacity" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "heating_capacity": " 100 "}
        issues = V4ValidationService.validate("热泵和冷水机组", whitespace_value)
        self.assertTrue(any(issue.field == "heating_capacity" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["heating_capacity"], "待复核")
        self.assertEqual(whitespace_value["heating_capacity"], " 100 ")

    def test_chiller_primary_metric_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("热泵和冷水机组"),
            {"positive": ("cooling_capacity", "heating_capacity", "rated_power", "primary_metric_value", "aux_metric1_value", "aux_metric2_value"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "C", "model": "C1", "quantity": 1,
            "category": "蒸气压缩循环冷水（热泵）机组-舒适型", "photo": "photo",
        }
        valid = {**base, "primary_metric_value": 3.4}
        self.assertFalse(any(issue.field == "primary_metric_value" for issue in V4ValidationService.validate("热泵和冷水机组", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热泵和冷水机组", {**base, "primary_metric_value": value})
                self.assertTrue(any(issue.field == "primary_metric_value" and issue.code == "positive" for issue in issues))
        text_value = {**base, "primary_metric_value": "待复核"}
        issues = V4ValidationService.validate("热泵和冷水机组", text_value)
        self.assertTrue(any(issue.field == "primary_metric_value" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "primary_metric_value": " 3.4 "}
        issues = V4ValidationService.validate("热泵和冷水机组", whitespace_value)
        self.assertTrue(any(issue.field == "primary_metric_value" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["primary_metric_value"], "待复核")
        self.assertEqual(whitespace_value["primary_metric_value"], " 3.4 ")

    def test_chiller_aux_metric1_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("热泵和冷水机组"),
            {"positive": ("cooling_capacity", "heating_capacity", "rated_power", "primary_metric_value", "aux_metric1_value", "aux_metric2_value"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "C", "model": "C1", "quantity": 1,
            "category": "蒸气压缩循环冷水（热泵）机组-舒适型", "photo": "photo",
        }
        valid = {**base, "aux_metric1_value": 2.1}
        self.assertFalse(any(issue.field == "aux_metric1_value" for issue in V4ValidationService.validate("热泵和冷水机组", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热泵和冷水机组", {**base, "aux_metric1_value": value})
                self.assertTrue(any(issue.field == "aux_metric1_value" and issue.code == "positive" for issue in issues))
        text_value = {**base, "aux_metric1_value": "待复核"}
        issues = V4ValidationService.validate("热泵和冷水机组", text_value)
        self.assertTrue(any(issue.field == "aux_metric1_value" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "aux_metric1_value": " 2.1 "}
        issues = V4ValidationService.validate("热泵和冷水机组", whitespace_value)
        self.assertTrue(any(issue.field == "aux_metric1_value" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["aux_metric1_value"], "待复核")
        self.assertEqual(whitespace_value["aux_metric1_value"], " 2.1 ")

    def test_chiller_aux_metric2_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("热泵和冷水机组"),
            {"positive": ("cooling_capacity", "heating_capacity", "rated_power", "primary_metric_value", "aux_metric1_value", "aux_metric2_value"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "C", "model": "C1", "quantity": 1,
            "category": "蒸气压缩循环冷水（热泵）机组-舒适型", "photo": "photo",
        }
        valid = {**base, "aux_metric2_value": 2.4}
        self.assertFalse(any(issue.field == "aux_metric2_value" for issue in V4ValidationService.validate("热泵和冷水机组", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热泵和冷水机组", {**base, "aux_metric2_value": value})
                self.assertTrue(any(issue.field == "aux_metric2_value" and issue.code == "positive" for issue in issues))
        text_value = {**base, "aux_metric2_value": "待复核"}
        issues = V4ValidationService.validate("热泵和冷水机组", text_value)
        self.assertTrue(any(issue.field == "aux_metric2_value" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "aux_metric2_value": " 2.4 "}
        issues = V4ValidationService.validate("热泵和冷水机组", whitespace_value)
        self.assertTrue(any(issue.field == "aux_metric2_value" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["aux_metric2_value"], "待复核")
        self.assertEqual(whitespace_value["aux_metric2_value"], " 2.4 ")

    def test_duct_cooling_capacity_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("风管送风式空调"),
            {"positive": ("cooling_capacity", "rated_power", "indicator_value"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "D", "model": "D1", "quantity": 1,
            "category": "风管送风式空调（热泵）机组", "photo": "photo",
        }
        valid = {**base, "cooling_capacity": 100.0}
        self.assertFalse(any(issue.field == "cooling_capacity" for issue in V4ValidationService.validate("风管送风式空调", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("风管送风式空调", {**base, "cooling_capacity": value})
                self.assertTrue(any(issue.field == "cooling_capacity" and issue.code == "positive" for issue in issues))
        text_value = {**base, "cooling_capacity": "待复核"}
        issues = V4ValidationService.validate("风管送风式空调", text_value)
        self.assertTrue(any(issue.field == "cooling_capacity" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "cooling_capacity": " 100 "}
        issues = V4ValidationService.validate("风管送风式空调", whitespace_value)
        self.assertTrue(any(issue.field == "cooling_capacity" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["cooling_capacity"], "待复核")
        self.assertEqual(whitespace_value["cooling_capacity"], " 100 ")

    def test_duct_rated_power_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("风管送风式空调"),
            {"positive": ("cooling_capacity", "rated_power", "indicator_value"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "D", "model": "D1", "quantity": 1,
            "category": "风管送风式空调（热泵）机组", "photo": "photo",
        }
        valid = {**base, "rated_power": 20.0}
        self.assertFalse(any(issue.field == "rated_power" for issue in V4ValidationService.validate("风管送风式空调", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("风管送风式空调", {**base, "rated_power": value})
                self.assertTrue(any(issue.field == "rated_power" and issue.code == "positive" for issue in issues))
        text_value = {**base, "rated_power": "待复核"}
        issues = V4ValidationService.validate("风管送风式空调", text_value)
        self.assertTrue(any(issue.field == "rated_power" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "rated_power": " 20 "}
        issues = V4ValidationService.validate("风管送风式空调", whitespace_value)
        self.assertTrue(any(issue.field == "rated_power" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["rated_power"], "待复核")
        self.assertEqual(whitespace_value["rated_power"], " 20 ")

    def test_duct_indicator_value_uses_field_scoped_metadata_rule_without_rewriting(self):
        """风管送风式空调动态设计指标接入统一元数据正数规则。"""
        self.assertEqual(
            _metadata_numeric_constraints("风管送风式空调"),
            {"positive": ("cooling_capacity", "rated_power", "indicator_value"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "D", "model": "D1", "quantity": 1,
            "category": "风管送风式空调（热泵）机组", "photo": "photo",
        }
        valid = {**base, "indicator_value": 4.2}
        self.assertFalse(any(issue.field == "indicator_value" for issue in V4ValidationService.validate("风管送风式空调", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("风管送风式空调", {**base, "indicator_value": value})
                self.assertTrue(any(issue.field == "indicator_value" and issue.code == "positive" for issue in issues))
        text_value = {**base, "indicator_value": "待复核"}
        issues = V4ValidationService.validate("风管送风式空调", text_value)
        self.assertTrue(any(issue.field == "indicator_value" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "indicator_value": " 4.2 "}
        issues = V4ValidationService.validate("风管送风式空调", whitespace_value)
        self.assertTrue(any(issue.field == "indicator_value" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["indicator_value"], "待复核")
        self.assertEqual(whitespace_value["indicator_value"], " 4.2 ")

    def test_unitary_cooling_capacity_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("单元式空调"),
            {"positive": ("cooling_capacity", "rated_power", "indicator_value"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "U", "model": "U1", "quantity": 1,
            "category": "普通单元式空调机", "photo": "photo",
        }
        valid = {**base, "cooling_capacity": 100.0}
        self.assertFalse(any(issue.field == "cooling_capacity" for issue in V4ValidationService.validate("单元式空调", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("单元式空调", {**base, "cooling_capacity": value})
                self.assertTrue(any(issue.field == "cooling_capacity" and issue.code == "positive" for issue in issues))
        text_value = {**base, "cooling_capacity": "待复核"}
        issues = V4ValidationService.validate("单元式空调", text_value)
        self.assertTrue(any(issue.field == "cooling_capacity" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "cooling_capacity": " 100 "}
        issues = V4ValidationService.validate("单元式空调", whitespace_value)
        self.assertTrue(any(issue.field == "cooling_capacity" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["cooling_capacity"], "待复核")
        self.assertEqual(whitespace_value["cooling_capacity"], " 100 ")

    def test_unitary_rated_power_uses_field_scoped_metadata_rule_without_rewriting(self):
        base = {
            "device_name": "U", "model": "U1", "quantity": 1,
            "category": "普通单元式空调机", "photo": "photo",
        }
        valid = {**base, "rated_power": 20.0}
        self.assertFalse(any(issue.field == "rated_power" for issue in V4ValidationService.validate("单元式空调", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("单元式空调", {**base, "rated_power": value})
                self.assertTrue(any(issue.field == "rated_power" and issue.code == "positive" for issue in issues))
        text_value = {**base, "rated_power": "待复核"}
        issues = V4ValidationService.validate("单元式空调", text_value)
        self.assertTrue(any(issue.field == "rated_power" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "rated_power": " 20 "}
        issues = V4ValidationService.validate("单元式空调", whitespace_value)
        self.assertTrue(any(issue.field == "rated_power" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["rated_power"], "待复核")
        self.assertEqual(whitespace_value["rated_power"], " 20 ")

    def test_unitary_indicator_value_uses_field_scoped_metadata_rule_without_rewriting(self):
        """单元式空调动态设计指标的正数规则接入统一元数据。"""
        self.assertEqual(
            _metadata_numeric_constraints("单元式空调"),
            {"positive": ("cooling_capacity", "rated_power", "indicator_value"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "U", "model": "U1", "quantity": 1,
            "category": "普通单元式空调机", "photo": "photo",
        }
        valid = {**base, "indicator_value": 4.5}
        self.assertFalse(any(issue.field == "indicator_value" for issue in V4ValidationService.validate("单元式空调", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("单元式空调", {**base, "indicator_value": value})
                self.assertTrue(any(issue.field == "indicator_value" and issue.code == "positive" for issue in issues))
        text_value = {**base, "indicator_value": "待复核"}
        issues = V4ValidationService.validate("单元式空调", text_value)
        self.assertTrue(any(issue.field == "indicator_value" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "indicator_value": " 4.5 "}
        issues = V4ValidationService.validate("单元式空调", whitespace_value)
        self.assertTrue(any(issue.field == "indicator_value" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["indicator_value"], "待复核")
        self.assertEqual(whitespace_value["indicator_value"], " 4.5 ")

    def test_multi_split_cooling_capacity_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("多联式空调"),
            {"positive": ("cooling_capacity", "heating_capacity", "rated_power", "primary_metric_value", "eer_min_value", "cop_minus12_value", "cop_minus20_value"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "M", "model": "M1", "quantity": 1,
            "category": "风冷式单冷型多联机", "photo": "photo",
        }
        valid = {**base, "cooling_capacity": 100.0}
        self.assertFalse(any(issue.field == "cooling_capacity" for issue in V4ValidationService.validate("多联式空调", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("多联式空调", {**base, "cooling_capacity": value})
                self.assertTrue(any(issue.field == "cooling_capacity" and issue.code == "positive" for issue in issues))
        text_value = {**base, "cooling_capacity": "待复核"}
        issues = V4ValidationService.validate("多联式空调", text_value)
        self.assertTrue(any(issue.field == "cooling_capacity" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "cooling_capacity": " 100 "}
        issues = V4ValidationService.validate("多联式空调", whitespace_value)
        self.assertTrue(any(issue.field == "cooling_capacity" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["cooling_capacity"], "待复核")
        self.assertEqual(whitespace_value["cooling_capacity"], " 100 ")

    def test_multi_split_heating_capacity_uses_field_scoped_metadata_rule_without_rewriting(self):
        """多联式空调名义制热量接入统一元数据正数规则。"""
        self.assertEqual(
            _metadata_numeric_constraints("多联式空调"),
            {"positive": ("cooling_capacity", "heating_capacity", "rated_power", "primary_metric_value", "eer_min_value", "cop_minus12_value", "cop_minus20_value"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "M", "model": "M1", "quantity": 1,
            "category": "低温多联机", "rated_power": 20,
            "external_static": 0, "primary_metric_value": 3.4,
            "cop_minus12_value": 2.2, "cop_minus20_value": 1.8,
            "photo": "photo",
        }
        valid = {**base, "heating_capacity": 18.0}
        self.assertFalse(any(issue.field == "heating_capacity" for issue in V4ValidationService.validate("多联式空调", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("多联式空调", {**base, "heating_capacity": value})
                self.assertTrue(any(issue.field == "heating_capacity" and issue.code == "positive" for issue in issues))
        text_value = {**base, "heating_capacity": "待复核"}
        issues = V4ValidationService.validate("多联式空调", text_value)
        self.assertTrue(any(issue.field == "heating_capacity" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "heating_capacity": " 18 "}
        issues = V4ValidationService.validate("多联式空调", whitespace_value)
        self.assertTrue(any(issue.field == "heating_capacity" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["heating_capacity"], "待复核")
        self.assertEqual(whitespace_value["heating_capacity"], " 18 ")

    def test_multi_split_rated_power_uses_field_scoped_metadata_rule_without_rewriting(self):
        base = {
            "device_name": "M", "model": "M1", "quantity": 1,
            "category": "风冷式单冷型多联机", "photo": "photo",
        }
        valid = {**base, "rated_power": 20.0}
        self.assertFalse(any(issue.field == "rated_power" for issue in V4ValidationService.validate("多联式空调", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("多联式空调", {**base, "rated_power": value})
                self.assertTrue(any(issue.field == "rated_power" and issue.code == "positive" for issue in issues))
        text_value = {**base, "rated_power": "待复核"}
        issues = V4ValidationService.validate("多联式空调", text_value)
        self.assertTrue(any(issue.field == "rated_power" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "rated_power": " 20 "}
        issues = V4ValidationService.validate("多联式空调", whitespace_value)
        self.assertTrue(any(issue.field == "rated_power" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["rated_power"], "待复核")
        self.assertEqual(whitespace_value["rated_power"], " 20 ")

    def test_multi_split_primary_metric_uses_field_scoped_metadata_rule_without_rewriting(self):
        """多联式空调分级指标设计值接入统一元数据正数规则。"""
        self.assertEqual(
            _metadata_numeric_constraints("多联式空调"),
            {"positive": ("cooling_capacity", "heating_capacity", "rated_power", "primary_metric_value", "eer_min_value", "cop_minus12_value", "cop_minus20_value"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "M", "model": "M1", "quantity": 1,
            "category": "风冷式单冷型多联机", "photo": "photo",
        }
        valid = {**base, "primary_metric_value": 4.2}
        self.assertFalse(any(issue.field == "primary_metric_value" for issue in V4ValidationService.validate("多联式空调", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("多联式空调", {**base, "primary_metric_value": value})
                self.assertTrue(any(issue.field == "primary_metric_value" and issue.code == "positive" for issue in issues))
        text_value = {**base, "primary_metric_value": "待复核"}
        issues = V4ValidationService.validate("多联式空调", text_value)
        self.assertTrue(any(issue.field == "primary_metric_value" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "primary_metric_value": " 4.2 "}
        issues = V4ValidationService.validate("多联式空调", whitespace_value)
        self.assertTrue(any(issue.field == "primary_metric_value" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["primary_metric_value"], "待复核")
        self.assertEqual(whitespace_value["primary_metric_value"], " 4.2 ")

    def test_multi_split_eer_min_uses_field_scoped_metadata_rule_without_rewriting(self):
        """多联式空调EER设计值接入统一元数据正数规则。"""
        self.assertEqual(
            _metadata_numeric_constraints("多联式空调"),
            {"positive": ("cooling_capacity", "heating_capacity", "rated_power", "primary_metric_value", "eer_min_value", "cop_minus12_value", "cop_minus20_value"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "M", "model": "M1", "quantity": 1,
            "category": "风冷式单冷型多联机", "cooling_capacity": 10,
            "rated_power": 20, "external_static": 0, "primary_metric_value": 4.2,
            "photo": "photo",
        }
        valid = {**base, "eer_min_value": 2.1}
        self.assertFalse(any(issue.field == "eer_min_value" for issue in V4ValidationService.validate("多联式空调", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("多联式空调", {**base, "eer_min_value": value})
                self.assertTrue(any(issue.field == "eer_min_value" and issue.code == "positive" for issue in issues))
        text_value = {**base, "eer_min_value": "待复核"}
        issues = V4ValidationService.validate("多联式空调", text_value)
        self.assertTrue(any(issue.field == "eer_min_value" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "eer_min_value": " 2.1 "}
        issues = V4ValidationService.validate("多联式空调", whitespace_value)
        self.assertTrue(any(issue.field == "eer_min_value" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["eer_min_value"], "待复核")
        self.assertEqual(whitespace_value["eer_min_value"], " 2.1 ")

    def test_multi_split_cop_minus12_uses_field_scoped_metadata_rule_without_rewriting(self):
        """多联式空调COP(-12℃)设计值接入统一元数据正数规则。"""
        self.assertEqual(
            _metadata_numeric_constraints("多联式空调"),
            {"positive": ("cooling_capacity", "heating_capacity", "rated_power", "primary_metric_value", "eer_min_value", "cop_minus12_value", "cop_minus20_value"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "M", "model": "M1", "quantity": 1,
            "category": "低温多联机", "heating_capacity": 18,
            "rated_power": 20, "external_static": 0,
            "primary_metric_value": 3.4, "cop_minus20_value": 1.8,
            "photo": "photo",
        }
        valid = {**base, "cop_minus12_value": 2.2}
        self.assertFalse(any(issue.field == "cop_minus12_value" for issue in V4ValidationService.validate("多联式空调", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("多联式空调", {**base, "cop_minus12_value": value})
                self.assertTrue(any(issue.field == "cop_minus12_value" and issue.code == "positive" for issue in issues))
        text_value = {**base, "cop_minus12_value": "待复核"}
        issues = V4ValidationService.validate("多联式空调", text_value)
        self.assertTrue(any(issue.field == "cop_minus12_value" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "cop_minus12_value": " 2.2 "}
        issues = V4ValidationService.validate("多联式空调", whitespace_value)
        self.assertTrue(any(issue.field == "cop_minus12_value" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["cop_minus12_value"], "待复核")
        self.assertEqual(whitespace_value["cop_minus12_value"], " 2.2 ")

    def test_multi_split_cop_minus20_uses_field_scoped_metadata_rule_without_rewriting(self):
        """多联式空调COP(-20℃)设计值接入统一元数据正数规则。"""
        self.assertEqual(
            _metadata_numeric_constraints("多联式空调"),
            {"positive": ("cooling_capacity", "heating_capacity", "rated_power", "primary_metric_value", "eer_min_value", "cop_minus12_value", "cop_minus20_value"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "M", "model": "M1", "quantity": 1,
            "category": "低温多联机", "heating_capacity": 18,
            "rated_power": 20, "external_static": 0,
            "primary_metric_value": 3.4, "cop_minus12_value": 2.2,
            "photo": "photo",
        }
        valid = {**base, "cop_minus20_value": 1.8}
        self.assertFalse(any(issue.field == "cop_minus20_value" for issue in V4ValidationService.validate("多联式空调", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("多联式空调", {**base, "cop_minus20_value": value})
                self.assertTrue(any(issue.field == "cop_minus20_value" and issue.code == "positive" for issue in issues))
        text_value = {**base, "cop_minus20_value": "待复核"}
        issues = V4ValidationService.validate("多联式空调", text_value)
        self.assertTrue(any(issue.field == "cop_minus20_value" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "cop_minus20_value": " 1.8 "}
        issues = V4ValidationService.validate("多联式空调", whitespace_value)
        self.assertTrue(any(issue.field == "cop_minus20_value" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["cop_minus20_value"], "待复核")
        self.assertEqual(whitespace_value["cop_minus20_value"], " 1.8 ")

    def test_known_motor_category_alias_is_not_reported_as_invalid_enum(self):
        # 兼容入口示例和历史填报中的说明性后缀，仍对应V4标准枚举值。
        issues = V4ValidationService.validate(
            "电动机",
            {
                "device_name": "M", "model": "M1", "quantity": 1,
                "category": "三相异步电动机（一般用途）", "photo": "photo",
            },
            enum_values={"category": {"三相异步电动机", "高压三相笼型异步电动机"}},
        )
        self.assertFalse(any(issue.field == "category" and issue.code == "enum" for issue in issues))

    def test_motor_category_uses_metadata_enum_and_rejects_unknown_value(self):
        base = {
            "device_name": "M", "model": "M1", "quantity": 1, "photo": "photo",
        }
        for value in ("三相异步电动机", "高压三相笼型异步电动机", "三相异步电动机（一般用途）"):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("电动机", {**base, "category": value})
                self.assertFalse(any(issue.field == "category" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("电动机", {**base, "category": "未知电动机"})
        self.assertTrue(any(issue.field == "category" and issue.code == "enum" for issue in invalid))

    def test_motor_rated_voltage_uses_metadata_enum_and_rejects_unit_suffix(self):
        base = {
            "device_name": "M", "model": "M1", "quantity": 1,
            "category": "三相异步电动机", "photo": "photo",
        }
        for value in ("0.2", "0.4", "3（3.3）", "6", "其他（请备注说明）", "10"):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("电动机", {**base, "rated_voltage": value})
                self.assertFalse(any(issue.field == "rated_voltage" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("电动机", {**base, "rated_voltage": "0.4kV"})
        self.assertTrue(any(issue.field == "rated_voltage" and issue.code == "enum" for issue in invalid))

    def test_motor_poles_uses_metadata_enum_and_rejects_fractional_value(self):
        base = {
            "device_name": "M", "model": "M1", "quantity": 1,
            "category": "三相异步电动机", "photo": "photo",
        }
        for value in (2, 4, 12, "其他（请备注说明）"):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("电动机", {**base, "poles": value})
                self.assertFalse(any(issue.field == "poles" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("电动机", {**base, "poles": 4.5})
        self.assertTrue(any(issue.field == "poles" and issue.code in {"enum", "integer"} for issue in invalid))

    def test_motor_rated_speed_uses_metadata_numeric_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("电动机"),
            {
                "positive": ("rated_power", "rated_speed"),
                "integer": ("quantity", "poles"),
                "percentage": ("efficiency",),
            },
        )
        base = {
            "device_name": "M", "model": "M1", "quantity": 1,
            "category": "三相异步电动机", "rated_power": 7.5, "photo": "photo",
        }
        valid_values = {**base, "rated_speed": 1480}
        self.assertFalse(any(issue.field == "rated_speed" for issue in V4ValidationService.validate("电动机", valid_values)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("电动机", {**base, "rated_speed": value})
                self.assertTrue(any(issue.field == "rated_speed" and issue.code == "positive" for issue in issues))
        text_value = {**base, "rated_speed": "待复核"}
        issues = V4ValidationService.validate("电动机", text_value)
        self.assertTrue(any(issue.field == "rated_speed" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "rated_speed": " 1480 "}
        issues = V4ValidationService.validate("电动机", whitespace_value)
        self.assertTrue(any(issue.field == "rated_speed" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["rated_speed"], "待复核")
        self.assertEqual(whitespace_value["rated_speed"], " 1480 ")

    def test_unknown_category_is_still_reported_as_invalid_enum(self):
        issues = V4ValidationService.validate(
            "电动机",
            {
                "device_name": "M", "model": "M1", "quantity": 1,
                "category": "未知电动机", "photo": "photo",
            },
            enum_values={"category": {"三相异步电动机"}},
        )
        self.assertTrue(any(issue.field == "category" and issue.code == "enum" for issue in issues))

    def test_motor_cooling_enum_falls_back_to_metadata_without_template_contract(self):
        base = {
            "device_name": "M", "model": "M1", "quantity": 1,
            "category": "高压三相笼型异步电动机", "photo": "photo",
        }
        self.assertFalse(any(issue.field == "cooling" and issue.code == "enum" for issue in V4ValidationService.validate(
            "电动机", {**base, "cooling": "IC86W"},
        )))
        issues = V4ValidationService.validate("电动机", {**base, "cooling": "不属于标准的冷却方式"})
        self.assertTrue(any(issue.field == "cooling" and issue.code == "enum" for issue in issues))

    def test_explicit_template_enum_remains_authoritative_over_metadata_fallback(self):
        # 传入V4契约时不把领域回退列表与契约合并，避免两个版本的
        # 标准枚举静默叠加；这里用一个仅含IC01的契约模拟该边界。
        issues = V4ValidationService.validate(
            "电动机",
            {
                "device_name": "M", "model": "M1", "quantity": 1,
                "category": "高压三相笼型异步电动机", "cooling": "IC86W", "photo": "photo",
            },
            enum_values={"cooling": {"IC01"}},
        )
        self.assertTrue(any(issue.field == "cooling" and issue.code == "enum" for issue in issues))

    def test_transformer_enum_falls_back_to_metadata_without_template_contract(self):
        base = {
            "device_name": "T", "model": "T1", "quantity": 1,
            "photo": "photo",
        }
        valid = {
            **base,
            "category": "10kV油浸式三相双绕组无励磁调压配电变压器",
            "core_material": "电工钢带",
            "insulation": "不适用",
            "connection": "Dyn11/Yzn11",
        }
        valid_issues = V4ValidationService.validate("变压器", valid)
        self.assertFalse(any(issue.code == "enum" for issue in valid_issues))

        invalid = {
            **valid,
            "category": "10kV油浸式三相双绕组无励磁调压配电变压器-手工改写",
            "core_material": "未知铁芯",
            "insulation": "未知绝缘",
            "connection": "未知连接组",
        }
        invalid_issues = V4ValidationService.validate("变压器", invalid)
        enum_fields = {
            issue.field for issue in invalid_issues if issue.code == "enum"
        }
        self.assertEqual(enum_fields, {"category", "core_material", "insulation", "connection"})

    def test_transformer_explicit_template_enum_remains_authoritative(self):
        issues = V4ValidationService.validate(
            "变压器",
            {
                "device_name": "T", "model": "T1", "quantity": 1,
                "category": "10kV油浸式三相双绕组无励磁调压配电变压器",
                "photo": "photo",
            },
            enum_values={"category": {"其他（请备注说明）"}},
        )
        self.assertTrue(any(issue.field == "category" and issue.code == "enum" for issue in issues))

    def test_compressor_category_uses_metadata_fallback_without_template_contract(self):
        base = {
            "device_name": "C", "model": "C1", "quantity": 1,
            "photo": "photo",
        }
        valid = V4ValidationService.validate(
            "空压机", {**base, "category": "一般用喷油回转（工频）"}
        )
        self.assertFalse(any(issue.field == "category" and issue.code == "enum" for issue in valid))
        invalid = V4ValidationService.validate(
            "空压机", {**base, "category": "一般用喷油回转（未知工频）"}
        )
        self.assertTrue(any(issue.field == "category" and issue.code == "enum" for issue in invalid))

    def test_compressor_cooling_uses_metadata_fallback_without_template_contract(self):
        base = {
            "device_name": "C", "model": "C1", "quantity": 1,
            "category": "一般用喷油回转（工频）", "photo": "photo",
        }
        valid = V4ValidationService.validate("空压机", {**base, "cooling": "风冷"})
        self.assertFalse(any(issue.field == "cooling" and issue.code == "enum" for issue in valid))
        invalid = V4ValidationService.validate("空压机", {**base, "cooling": "气冷"})
        self.assertTrue(any(issue.field == "cooling" and issue.code == "enum" for issue in invalid))

    def test_compressor_input_power_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("空压机"),
            {"positive": ("input_power", "volume_flow", "discharge_pressure", "specific_power"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "C", "model": "C1", "quantity": 1,
            "category": "一般用喷油回转（工频）", "photo": "photo",
        }
        valid = {**base, "input_power": 7.5}
        self.assertFalse(any(issue.field == "input_power" for issue in V4ValidationService.validate("空压机", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("空压机", {**base, "input_power": value})
                self.assertTrue(any(issue.field == "input_power" and issue.code == "positive" for issue in issues))
        text_value = {**base, "input_power": "待复核"}
        issues = V4ValidationService.validate("空压机", text_value)
        self.assertTrue(any(issue.field == "input_power" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "input_power": " 7.5 "}
        issues = V4ValidationService.validate("空压机", whitespace_value)
        self.assertTrue(any(issue.field == "input_power" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["input_power"], "待复核")
        self.assertEqual(whitespace_value["input_power"], " 7.5 ")

    def test_compressor_volume_flow_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("空压机"),
            {"positive": ("input_power", "volume_flow", "discharge_pressure", "specific_power"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "C", "model": "C1", "quantity": 1,
            "category": "一般用喷油回转（工频）", "photo": "photo",
        }
        valid = {**base, "volume_flow": 8.0}
        self.assertFalse(any(issue.field == "volume_flow" for issue in V4ValidationService.validate("空压机", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("空压机", {**base, "volume_flow": value})
                self.assertTrue(any(issue.field == "volume_flow" and issue.code == "positive" for issue in issues))
        text_value = {**base, "volume_flow": "待复核"}
        issues = V4ValidationService.validate("空压机", text_value)
        self.assertTrue(any(issue.field == "volume_flow" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "volume_flow": " 8.0 "}
        issues = V4ValidationService.validate("空压机", whitespace_value)
        self.assertTrue(any(issue.field == "volume_flow" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["volume_flow"], "待复核")
        self.assertEqual(whitespace_value["volume_flow"], " 8.0 ")

    def test_compressor_discharge_pressure_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("空压机"),
            {"positive": ("input_power", "volume_flow", "discharge_pressure", "specific_power"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "C", "model": "C1", "quantity": 1,
            "category": "一般用喷油回转（工频）", "photo": "photo",
        }
        valid = {**base, "discharge_pressure": 0.7}
        self.assertFalse(any(issue.field == "discharge_pressure" for issue in V4ValidationService.validate("空压机", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("空压机", {**base, "discharge_pressure": value})
                self.assertTrue(any(issue.field == "discharge_pressure" and issue.code == "positive" for issue in issues))
        text_value = {**base, "discharge_pressure": "待复核"}
        issues = V4ValidationService.validate("空压机", text_value)
        self.assertTrue(any(issue.field == "discharge_pressure" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "discharge_pressure": " 0.7 "}
        issues = V4ValidationService.validate("空压机", whitespace_value)
        self.assertTrue(any(issue.field == "discharge_pressure" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["discharge_pressure"], "待复核")
        self.assertEqual(whitespace_value["discharge_pressure"], " 0.7 ")

    def test_compressor_specific_power_uses_field_scoped_metadata_rule_without_rewriting(self):
        self.assertEqual(
            _metadata_numeric_constraints("空压机"),
            {"positive": ("input_power", "volume_flow", "discharge_pressure", "specific_power"), "integer": ("quantity",), "percentage": ()},
        )
        base = {
            "device_name": "C", "model": "C1", "quantity": 1,
            "category": "一般用喷油回转（工频）", "photo": "photo",
        }
        valid = {**base, "specific_power": 0.55}
        self.assertFalse(any(issue.field == "specific_power" for issue in V4ValidationService.validate("空压机", valid)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("空压机", {**base, "specific_power": value})
                self.assertTrue(any(issue.field == "specific_power" and issue.code == "positive" for issue in issues))
        text_value = {**base, "specific_power": "待复核"}
        issues = V4ValidationService.validate("空压机", text_value)
        self.assertTrue(any(issue.field == "specific_power" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "specific_power": " 0.55 "}
        issues = V4ValidationService.validate("空压机", whitespace_value)
        self.assertTrue(any(issue.field == "specific_power" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["specific_power"], "待复核")
        self.assertEqual(whitespace_value["specific_power"], " 0.55 ")

    def test_pump_category_accepts_internal_alias_and_rejects_unknown_value(self):
        base = {
            "device_name": "P", "model": "P1", "quantity": 1,
            "photo": "photo",
        }
        # 评价器内部使用“单级单吸”，V4标准下拉使用完整名称；
        # 元数据校验应允许已登记的确定别名，但不放宽到模糊文本。
        valid = V4ValidationService.validate("离心泵", {**base, "category": "单级单吸"})
        self.assertFalse(any(issue.field == "category" and issue.code == "enum" for issue in valid))
        invalid = V4ValidationService.validate("离心泵", {**base, "category": "单级单吸泵"})
        self.assertTrue(any(issue.field == "category" and issue.code == "enum" for issue in invalid))

    def test_pump_suction_uses_metadata_enum_and_is_not_applied_to_chemical_only_fields(self):
        base = {
            "device_name": "P", "model": "P1", "quantity": 1,
            "category": "单级单吸清水离心泵", "photo": "photo",
        }
        valid = V4ValidationService.validate("离心泵", {**base, "suction": "双吸"})
        self.assertFalse(any(issue.field == "suction" and issue.code == "enum" for issue in valid))
        invalid = V4ValidationService.validate("离心泵", {**base, "suction": "单双吸均可"})
        self.assertTrue(any(issue.field == "suction" and issue.code == "enum" for issue in invalid))

    def test_submersible_device_form_accepts_registered_aliases_and_rejects_unknown(self):
        base = {
            "device_name": "S", "model": "S1", "quantity": 1,
            "category": "小型潜水电泵", "photo": "photo",
        }
        for value in ("QDX", "QD", "混流式(蜗壳)"):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("潜水电泵", {**base, "device_form": value})
                self.assertFalse(any(issue.field == "device_form" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("潜水电泵", {**base, "device_form": "未知泵型"})
        self.assertTrue(any(issue.field == "device_form" and issue.code == "enum" for issue in invalid))

    def test_submersible_category_uses_metadata_enum(self):
        base = {
            "device_name": "S", "model": "S1", "quantity": 1,
            "photo": "photo", "device_form": "QDX和QD",
        }
        values = (
            "小型潜水电泵", "大中型潜水电泵", "污水污物潜水电泵",
            "井用潜水电泵", "其他（请备注说明）", "混流潜水电泵",
        )
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("潜水电泵", {**base, "category": value})
                self.assertFalse(any(issue.field == "category" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("潜水电泵", {**base, "category": "潜水泵"})
        self.assertTrue(any(issue.field == "category" and issue.code == "enum" for issue in invalid))

    def test_boiler_category_uses_metadata_fallback_without_template_contract(self):
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "photo": "photo",
        }
        valid = V4ValidationService.validate("工业锅炉", {**base, "category": "电锅炉"})
        self.assertFalse(any(issue.field == "category" and issue.code == "enum" for issue in valid))
        invalid = V4ValidationService.validate("工业锅炉", {**base, "category": "燃气锅炉（冷凝）"})
        self.assertTrue(any(issue.field == "category" and issue.code == "enum" for issue in invalid))

    def test_boiler_fuel_uses_metadata_enum(self):
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "电锅炉", "photo": "photo",
        }
        values = (
            "烟煤", "贫煤", "无烟煤", "褐煤", "天然气",
            "生物质", "燃油", "煤（室燃）", "电力", "其他（请备注说明）",
        )
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("工业锅炉", {**base, "fuel": value})
                self.assertFalse(any(issue.field == "fuel" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("工业锅炉", {**base, "fuel": "燃气"})
        self.assertTrue(any(issue.field == "fuel" and issue.code == "enum" for issue in invalid))

    def test_heat_treatment_category_uses_metadata_enum(self):
        base = {
            "device_name": "H", "model": "H1", "quantity": 1,
            "energy_type": "电力", "photo": "photo",
        }
        values = (
            "传送式连续炉", "震底式连续炉", "推送式连续炉", "滚筒式连续炉",
            "井式炉-中温炉", "箱式多用炉", "井式炉-回火炉", "井式炉-气体渗碳(氮)炉",
            "箱式炉", "台车炉", "热处理电热浴炉", "辊底炉", "罩式炉", "其他（请备注说明）",
        )
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热处理设备", {**base, "category": value})
                self.assertFalse(any(issue.field == "category" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("热处理设备", {**base, "category": "热处理炉"})
        self.assertTrue(any(issue.field == "category" and issue.code == "enum" for issue in invalid))

    def test_heat_treatment_energy_type_uses_metadata_enum(self):
        base = {
            "device_name": "H", "model": "H1", "quantity": 1,
            "category": "传送式连续炉", "photo": "photo",
        }
        values = (
            "燃料油", "发生炉煤气（1250kcal/m³～1350kcal/m³）",
            "发生炉煤气（1400kcal/m³～2200kcal/m³）", "城市煤气/焦炉煤气",
            "电力", "天然气", "其他（请备注说明）",
        )
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热处理设备", {**base, "energy_type": value})
                self.assertFalse(any(issue.field == "energy_type" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("热处理设备", {**base, "energy_type": "煤气"})
        self.assertTrue(any(issue.field == "energy_type" and issue.code == "enum" for issue in invalid))

    def test_hpwh_heating_method_accepts_registered_internal_aliases(self):
        base = {
            "device_name": "H", "model": "H1", "quantity": 1,
            "category": "普通型", "photo": "photo",
        }
        for value in ("一次加热式", "一次加热", "循环加热式", "循环加热", "静态加热式"):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热泵热水机", {**base, "heating_method": value})
                self.assertFalse(any(issue.field == "heating_method" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("热泵热水机", {**base, "heating_method": "瞬时加热"})
        self.assertTrue(any(issue.field == "heating_method" and issue.code == "enum" for issue in invalid))

    def test_hpwh_category_uses_metadata_enum(self):
        base = {
            "device_name": "H", "model": "H1", "quantity": 1,
            "photo": "photo", "heating_method": "一次加热式",
        }
        for value in ("普通型", "低温型", "其他（请备注说明）"):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热泵热水机", {**base, "category": value})
                self.assertFalse(any(issue.field == "category" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("热泵热水机", {**base, "category": "热泵热水器"})
        self.assertTrue(any(issue.field == "category" and issue.code == "enum" for issue in invalid))

    def test_hpwh_with_pump_uses_standard_yes_no_enum(self):
        base = {
            "device_name": "H", "model": "H1", "quantity": 1,
            "category": "普通型", "photo": "photo",
        }
        for value in ("是", "否", "不适用", "其他（请备注说明）"):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热泵热水机", {**base, "with_pump": value})
                self.assertFalse(any(issue.field == "with_pump" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("热泵热水机", {**base, "with_pump": "有水泵"})
        self.assertTrue(any(issue.field == "with_pump" and issue.code == "enum" for issue in invalid))

    def test_centrifugal_fan_transmission_uses_standard_enum(self):
        base = {
            "device_name": "F", "model": "F1", "quantity": 1,
            "category": "离心通风机", "photo": "photo",
        }
        values = (
            "A式传动（普通电动机直联）", "外转子电机直联", "其他传动", "不适用", "其他（请备注说明）",
        )
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("离心通风机", {**base, "transmission": value})
                self.assertFalse(any(issue.field == "transmission" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("离心通风机", {**base, "transmission": "直联"})
        self.assertTrue(any(issue.field == "transmission" and issue.code == "enum" for issue in invalid))

    def test_axial_fan_transmission_uses_standard_enum(self):
        base = {
            "device_name": "F", "model": "F1", "quantity": 1,
            "category": "轴流通风机", "photo": "photo",
        }
        values = (
            "A式传动（普通电动机直联）", "外转子电机直联", "其他传动", "不适用", "其他（请备注说明）",
        )
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("轴流通风机", {**base, "transmission": value})
                self.assertFalse(any(issue.field == "transmission" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("轴流通风机", {**base, "transmission": "直联"})
        self.assertTrue(any(issue.field == "transmission" and issue.code == "enum" for issue in invalid))

    def test_centrifugal_fan_suction_uses_standard_enum(self):
        base = {
            "device_name": "F", "model": "F1", "quantity": 1,
            "category": "离心通风机", "transmission": "其他传动", "photo": "photo",
        }
        values = ("单吸", "双吸", "不适用", "其他（请备注说明）")
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("离心通风机", {**base, "suction": value})
                self.assertFalse(any(issue.field == "suction" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("离心通风机", {**base, "suction": "吸入式"})
        self.assertTrue(any(issue.field == "suction" and issue.code == "enum" for issue in invalid))

    def test_centrifugal_fan_hvac_use_uses_standard_yes_no_enum(self):
        base = {
            "device_name": "F", "model": "F1", "quantity": 1,
            "category": "离心通风机", "transmission": "其他传动", "photo": "photo",
        }
        values = ("是", "否", "不适用", "其他（请备注说明）")
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("离心通风机", {**base, "hvac_use": value})
                self.assertFalse(any(issue.field == "hvac_use" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("离心通风机", {**base, "hvac_use": "暖通"})
        self.assertTrue(any(issue.field == "hvac_use" and issue.code == "enum" for issue in invalid))

    def test_centrifugal_fan_inlet_box_uses_standard_yes_no_enum(self):
        base = {
            "device_name": "F", "model": "F1", "quantity": 1,
            "category": "离心通风机", "transmission": "其他传动", "photo": "photo",
        }
        values = ("是", "否", "不适用", "其他（请备注说明）")
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("离心通风机", {**base, "inlet_box": value})
                self.assertFalse(any(issue.field == "inlet_box" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("离心通风机", {**base, "inlet_box": "带进气箱"})
        self.assertTrue(any(issue.field == "inlet_box" and issue.code == "enum" for issue in invalid))

    def test_axial_fan_inlet_box_uses_standard_yes_no_enum(self):
        base = {
            "device_name": "F", "model": "F1", "quantity": 1,
            "category": "轴流通风机", "transmission": "其他传动", "photo": "photo",
        }
        values = ("是", "否", "不适用", "其他（请备注说明）")
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("轴流通风机", {**base, "inlet_box": value})
                self.assertFalse(any(issue.field == "inlet_box" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("轴流通风机", {**base, "inlet_box": "带进气箱"})
        self.assertTrue(any(issue.field == "inlet_box" and issue.code == "enum" for issue in invalid))

    def test_axial_fan_diffuser_uses_standard_yes_no_enum(self):
        base = {
            "device_name": "F", "model": "F1", "quantity": 1,
            "category": "轴流通风机", "transmission": "其他传动", "photo": "photo",
        }
        values = ("是", "否", "不适用", "其他（请备注说明）")
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("轴流通风机", {**base, "diffuser": value})
                self.assertFalse(any(issue.field == "diffuser" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("轴流通风机", {**base, "diffuser": "扩散筒"})
        self.assertTrue(any(issue.field == "diffuser" and issue.code == "enum" for issue in invalid))

    def test_axial_fan_variable_blade_uses_standard_yes_no_enum(self):
        base = {
            "device_name": "F", "model": "F1", "quantity": 1,
            "category": "轴流通风机", "transmission": "其他传动", "photo": "photo",
        }
        values = ("是", "否", "不适用", "其他（请备注说明）")
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("轴流通风机", {**base, "variable_blade": value})
                self.assertFalse(any(issue.field == "variable_blade" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("轴流通风机", {**base, "variable_blade": "动叶可调"})
        self.assertTrue(any(issue.field == "variable_blade" and issue.code == "enum" for issue in invalid))

    def test_axial_fan_reversible_uses_standard_yes_no_enum(self):
        base = {
            "device_name": "F", "model": "F1", "quantity": 1,
            "category": "轴流通风机", "transmission": "其他传动", "photo": "photo",
        }
        values = ("是", "否", "不适用", "其他（请备注说明）")
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("轴流通风机", {**base, "reversible": value})
                self.assertFalse(any(issue.field == "reversible" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("轴流通风机", {**base, "reversible": "可逆转"})
        self.assertTrue(any(issue.field == "reversible" and issue.code == "enum" for issue in invalid))

    def test_heat_pump_chiller_category_uses_metadata_enum(self):
        base = {
            "device_name": "C", "model": "C1", "quantity": 1,
            "photo": "photo", "cooling_capacity": 1, "rated_power": 1,
            "indicator_value": 1,
        }
        values = (
            "蒸气压缩循环冷水（热泵）机组-舒适型",
            "蒸气压缩循环冷水（热泵）机组-数据中心专用型",
            "低环境温度空气源热泵（冷水）机组",
            "水（地）源热泵机组",
            "蒸气压缩循环高温热泵机组",
            "溴化锂吸收式冷（温）水机组",
            "间接蒸发冷却冷水机组",
            "一体式冷水（热泵）机组",
            "其他（请备注说明）",
        )
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热泵和冷水机组", {**base, "category": value})
                self.assertFalse(any(issue.field == "category" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("热泵和冷水机组", {**base, "category": "冷水机组"})
        self.assertTrue(any(issue.field == "category" and issue.code == "enum" for issue in invalid))

    def test_heat_pump_chiller_product_standard_uses_metadata_enum(self):
        base = {
            "device_name": "C", "model": "C1", "quantity": 1,
            "category": "蒸气压缩循环冷水（热泵）机组-舒适型", "photo": "photo",
            "cooling_capacity": 1, "rated_power": 1, "indicator_value": 1,
        }
        values = (
            "GB/T 18430.1", "GB/T 18430.2", "GB/T 25127.1", "GB/T 25127.2",
            "GB/T 18431", "GB/T 19409", "GB/T 18362", "GB/T 25861",
            "JB/T 12840", "JB/T 14642", "JB/T 14640", "JB/T 12839",
            "其他（请备注说明）",
        )
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热泵和冷水机组", {**base, "product_standard": value})
                self.assertFalse(any(issue.field == "product_standard" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("热泵和冷水机组", {**base, "product_standard": "GB/T 18430"})
        self.assertTrue(any(issue.field == "product_standard" and issue.code == "enum" for issue in invalid))

    def test_heat_pump_chiller_unit_type_uses_metadata_enum(self):
        base = {
            "device_name": "C", "model": "C1", "quantity": 1,
            "category": "蒸气压缩循环冷水（热泵）机组-舒适型", "photo": "photo",
            "cooling_capacity": 1, "rated_power": 1, "indicator_value": 1,
        }
        values = (
            "舒适型", "数据中心专用型", "地板采暖型", "风机盘管型", "冷热风型-热泵型",
            "散热器型", "冷热水型-单热型", "冷热水型-热泵型", "饱和蒸汽压力0.4MPa",
            "饱和蒸汽压力0.6MPa", "饱和蒸汽压力0.8MPa", "直燃型机组", "H1a", "H2a",
            "H3a", "H4a", "H5a", "H1b", "H2b", "H3b", "H4b", "H5b",
            "循环供水式热泵高温热水机组", "外冷式", "内冷式", "内外冷串联式", "风冷式",
            "蒸发冷却式冷却塔式", "其他（请备注说明）",
        )
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热泵和冷水机组", {**base, "unit_type": value})
                self.assertFalse(any(issue.field == "unit_type" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("热泵和冷水机组", {**base, "unit_type": "热泵型"})
        self.assertTrue(any(issue.field == "unit_type" and issue.code == "enum" for issue in invalid))

    def test_heat_pump_chiller_source_uses_metadata_enum(self):
        base = {
            "device_name": "C", "model": "C1", "quantity": 1,
            "category": "蒸气压缩循环冷水（热泵）机组-舒适型", "photo": "photo",
            "cooling_capacity": 1, "rated_power": 1, "indicator_value": 1,
        }
        values = (
            "水冷式", "风冷式", "蒸发冷却式", "空气源", "地下水式", "水环式",
            "地埋管式", "地表水式", "饱和蒸汽", "直燃", "不适用", "其他（请备注说明）",
        )
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热泵和冷水机组", {**base, "source": value})
                self.assertFalse(any(issue.field == "source" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("热泵和冷水机组", {**base, "source": "冷却水"})
        self.assertTrue(any(issue.field == "source" and issue.code == "enum" for issue in invalid))

    def test_heat_pump_chiller_evaluation_system_uses_metadata_enum(self):
        base = {
            "device_name": "C", "model": "C1", "quantity": 1,
            "category": "蒸气压缩循环冷水（热泵）机组-舒适型", "photo": "photo",
            "cooling_capacity": 1, "rated_power": 1, "indicator_value": 1,
        }
        values = (
            "综合部分负荷/季节性能指标体系（表1）",
            "制冷性能系数COPc指标体系（表2）",
            "对应产品类别指标体系（表3～表8）",
            "其他（请备注说明）",
        )
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("热泵和冷水机组", {**base, "evaluation_system": value})
                self.assertFalse(any(issue.field == "evaluation_system" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("热泵和冷水机组", {**base, "evaluation_system": "表1"})
        self.assertTrue(any(issue.field == "evaluation_system" and issue.code == "enum" for issue in invalid))

    def test_centrifugal_fan_category_uses_metadata_enum(self):
        base = {
            "device_name": "F", "model": "F1", "quantity": 1,
            "photo": "photo", "flow": 1, "fan_pressure": 1,
            "rated_power": 1, "impeller_power": 1, "speed": 1,
            "machine_no": 1, "density": 1, "isentropic_k": 1.4,
            "indicator_value": 1,
        }
        values = ("离心通风机", "外转子电机直联前向多翼离心风机", "其他（请备注说明）")
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("离心通风机", {**base, "category": value})
                self.assertFalse(any(issue.field == "category" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("离心通风机", {**base, "category": "离心风机"})
        self.assertTrue(any(issue.field == "category" and issue.code == "enum" for issue in invalid))

    def test_axial_fan_category_uses_metadata_enum(self):
        base = {
            "device_name": "A", "model": "A1", "quantity": 1,
            "photo": "photo", "flow": 1, "fan_pressure": 1,
            "rated_power": 1, "impeller_power": 1, "speed": 1,
            "machine_no": 1, "density": 1, "isentropic_k": 1.4,
            "indicator_value": 1,
        }
        for value in ("轴流通风机", "其他（请备注说明）"):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("轴流通风机", {**base, "category": value})
                self.assertFalse(any(issue.field == "category" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("轴流通风机", {**base, "category": "轴流风机"})
        self.assertTrue(any(issue.field == "category" and issue.code == "enum" for issue in invalid))

    def test_blower_category_uses_metadata_enum(self):
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "photo": "photo", "flow": 1, "pressure_in": 1,
            "pressure_out": 1, "temperature_in": 20, "temperature_out": 30,
            "isentropic_k": 1.4, "impeller_outlet_width": 1,
            "impeller_outlet_diameter": 1, "polytropic_efficiency": 80,
            "indicator_value": 1,
        }
        values = (
            "单级双支撑低速离心鼓风机", "多级低速离心鼓风机",
            "单级双支撑高速离心鼓风机", "多级高速离心鼓风机",
            "其他（请备注说明）",
        )
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("鼓风机", {**base, "category": value})
                self.assertFalse(any(issue.field == "category" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("鼓风机", {**base, "category": "离心鼓风机"})
        self.assertTrue(any(issue.field == "category" and issue.code == "enum" for issue in invalid))

    def test_blower_multi_impeller_uses_metadata_enum(self):
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "多级低速离心鼓风机", "photo": "photo",
        }
        for value in ("是", "否", "不适用", "其他（请备注说明）"):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("鼓风机", {**base, "multi_impeller": value})
                self.assertFalse(any(issue.field == "multi_impeller" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("鼓风机", {**base, "multi_impeller": "多级"})
        self.assertTrue(any(issue.field == "multi_impeller" and issue.code == "enum" for issue in invalid))

    def test_blower_cantilever_uses_metadata_enum(self):
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "单级双支撑低速离心鼓风机", "photo": "photo",
        }
        for value in ("是", "否", "不适用", "其他（请备注说明）"):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("鼓风机", {**base, "cantilever": value})
                self.assertFalse(any(issue.field == "cantilever" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("鼓风机", {**base, "cantilever": "悬臂"})
        self.assertTrue(any(issue.field == "cantilever" and issue.code == "enum" for issue in invalid))

    def test_blower_three_dimensional_uses_metadata_enum(self):
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "单级双支撑高速离心鼓风机", "photo": "photo",
        }
        for value in ("是", "否", "不适用", "其他（请备注说明）"):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("鼓风机", {**base, "three_dimensional": value})
                self.assertFalse(any(issue.field == "three_dimensional" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("鼓风机", {**base, "three_dimensional": "三元"})
        self.assertTrue(any(issue.field == "three_dimensional" and issue.code == "enum" for issue in invalid))

    def test_blower_inlet_pressure_uses_metadata_numeric_rule_without_rewriting(self):
        constraints = _metadata_numeric_constraints("鼓风机")
        self.assertIsNotNone(constraints)
        self.assertIn("p1", constraints["positive"])
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "单级双支撑高速离心鼓风机", "photo": "photo",
        }
        valid_values = {**base, "p1": 101.3}
        self.assertFalse(any(issue.field == "p1" for issue in V4ValidationService.validate("鼓风机", valid_values)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("鼓风机", {**base, "p1": value})
                self.assertTrue(any(issue.field == "p1" and issue.code == "positive" for issue in issues))
        text_value = {**base, "p1": "待复核"}
        issues = V4ValidationService.validate("鼓风机", text_value)
        self.assertTrue(any(issue.field == "p1" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "p1": " 101.3 "}
        issues = V4ValidationService.validate("鼓风机", whitespace_value)
        self.assertTrue(any(issue.field == "p1" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["p1"], "待复核")
        self.assertEqual(whitespace_value["p1"], " 101.3 ")

    def test_blower_outlet_pressure_uses_metadata_numeric_rule_without_rewriting(self):
        constraints = _metadata_numeric_constraints("鼓风机")
        self.assertIsNotNone(constraints)
        self.assertIn("p2", constraints["positive"])
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "单级双支撑高速离心鼓风机", "photo": "photo",
        }
        valid_values = {**base, "p2": 180.0}
        self.assertFalse(any(issue.field == "p2" for issue in V4ValidationService.validate("鼓风机", valid_values)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("鼓风机", {**base, "p2": value})
                self.assertTrue(any(issue.field == "p2" and issue.code == "positive" for issue in issues))
        text_value = {**base, "p2": "待复核"}
        issues = V4ValidationService.validate("鼓风机", text_value)
        self.assertTrue(any(issue.field == "p2" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "p2": " 180.0 "}
        issues = V4ValidationService.validate("鼓风机", whitespace_value)
        self.assertTrue(any(issue.field == "p2" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["p2"], "待复核")
        self.assertEqual(whitespace_value["p2"], " 180.0 ")

    def test_blower_inlet_temperature_uses_metadata_numeric_rule_without_rewriting(self):
        constraints = _metadata_numeric_constraints("鼓风机")
        self.assertIsNotNone(constraints)
        self.assertIn("t1", constraints["positive"])
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "单级双支撑高速离心鼓风机", "photo": "photo",
        }
        valid_values = {**base, "t1": 293.15}
        self.assertFalse(any(issue.field == "t1" for issue in V4ValidationService.validate("鼓风机", valid_values)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("鼓风机", {**base, "t1": value})
                self.assertTrue(any(issue.field == "t1" and issue.code == "positive" for issue in issues))
        text_value = {**base, "t1": "待复核"}
        issues = V4ValidationService.validate("鼓风机", text_value)
        self.assertTrue(any(issue.field == "t1" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "t1": " 293.15 "}
        issues = V4ValidationService.validate("鼓风机", whitespace_value)
        self.assertTrue(any(issue.field == "t1" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["t1"], "待复核")
        self.assertEqual(whitespace_value["t1"], " 293.15 ")

    def test_blower_outlet_temperature_uses_metadata_numeric_rule_without_rewriting(self):
        constraints = _metadata_numeric_constraints("鼓风机")
        self.assertIsNotNone(constraints)
        self.assertIn("t2", constraints["positive"])
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "单级双支撑高速离心鼓风机", "photo": "photo",
        }
        valid_values = {**base, "t2": 423.15}
        self.assertFalse(any(issue.field == "t2" for issue in V4ValidationService.validate("鼓风机", valid_values)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("鼓风机", {**base, "t2": value})
                self.assertTrue(any(issue.field == "t2" and issue.code == "positive" for issue in issues))
        text_value = {**base, "t2": "待复核"}
        issues = V4ValidationService.validate("鼓风机", text_value)
        self.assertTrue(any(issue.field == "t2" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "t2": " 423.15 "}
        issues = V4ValidationService.validate("鼓风机", whitespace_value)
        self.assertTrue(any(issue.field == "t2" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["t2"], "待复核")
        self.assertEqual(whitespace_value["t2"], " 423.15 ")

    def test_blower_impeller_width_uses_metadata_numeric_rule_without_rewriting(self):
        constraints = _metadata_numeric_constraints("鼓风机")
        self.assertIsNotNone(constraints)
        self.assertIn("b2", constraints["positive"])
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "单级双支撑高速离心鼓风机", "photo": "photo",
        }
        valid_values = {**base, "b2": 12.5}
        self.assertFalse(any(issue.field == "b2" for issue in V4ValidationService.validate("鼓风机", valid_values)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("鼓风机", {**base, "b2": value})
                self.assertTrue(any(issue.field == "b2" and issue.code == "positive" for issue in issues))
        text_value = {**base, "b2": "待复核"}
        issues = V4ValidationService.validate("鼓风机", text_value)
        self.assertTrue(any(issue.field == "b2" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "b2": " 12.5 "}
        issues = V4ValidationService.validate("鼓风机", whitespace_value)
        self.assertTrue(any(issue.field == "b2" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["b2"], "待复核")
        self.assertEqual(whitespace_value["b2"], " 12.5 ")

    def test_blower_impeller_diameter_uses_metadata_numeric_rule_without_rewriting(self):
        constraints = _metadata_numeric_constraints("鼓风机")
        self.assertIsNotNone(constraints)
        self.assertIn("d2", constraints["positive"])
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "单级双支撑高速离心鼓风机", "photo": "photo",
        }
        valid_values = {**base, "d2": 250.0}
        self.assertFalse(any(issue.field == "d2" for issue in V4ValidationService.validate("鼓风机", valid_values)))
        for value in (0, -1):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("鼓风机", {**base, "d2": value})
                self.assertTrue(any(issue.field == "d2" and issue.code == "positive" for issue in issues))
        text_value = {**base, "d2": "待复核"}
        issues = V4ValidationService.validate("鼓风机", text_value)
        self.assertTrue(any(issue.field == "d2" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "d2": " 250.0 "}
        issues = V4ValidationService.validate("鼓风机", whitespace_value)
        self.assertTrue(any(issue.field == "d2" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["d2"], "待复核")
        self.assertEqual(whitespace_value["d2"], " 250.0 ")

    def test_blower_polytropic_efficiency_uses_metadata_percentage_rule_without_rewriting(self):
        constraints = _metadata_numeric_constraints("鼓风机")
        self.assertIsNotNone(constraints)
        self.assertIn("polytropic_efficiency", constraints["percentage"])
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "单级双支撑高速离心鼓风机", "photo": "photo",
        }
        for value in (1, 75, 100):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("鼓风机", {**base, "polytropic_efficiency": value})
                self.assertFalse(any(issue.field == "polytropic_efficiency" for issue in issues))
        for value in (0, 100.1, "待复核"):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("鼓风机", {**base, "polytropic_efficiency": value})
                self.assertTrue(any(issue.field == "polytropic_efficiency" and issue.code == "percent_range" for issue in issues))
        whitespace_value = {**base, "polytropic_efficiency": " 75 "}
        issues = V4ValidationService.validate("鼓风机", whitespace_value)
        self.assertTrue(any(issue.field == "polytropic_efficiency" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(whitespace_value["polytropic_efficiency"], " 75 ")

    def test_fan_and_blower_isentropic_k_use_metadata_range_without_rewriting(self):
        for sheet_name in ("离心通风机", "轴流通风机", "鼓风机"):
            with self.subTest(sheet_name=sheet_name):
                ranges = _metadata_range_constraints(sheet_name)
                self.assertEqual(ranges["isentropic_k"], (Decimal("1"), Decimal("2")))
                base = {
                    "device_name": "F", "model": "F1", "quantity": 1,
                    "category": "离心通风机" if sheet_name == "离心通风机" else "轴流通风机" if sheet_name == "轴流通风机" else "单级双支撑高速离心鼓风机",
                    "photo": "photo",
                }
                for value in (1, 1.4, 2):
                    issues = V4ValidationService.validate(sheet_name, {**base, "isentropic_k": value})
                    self.assertFalse(any(issue.field == "isentropic_k" for issue in issues))
                for value in (0, 2.1):
                    issues = V4ValidationService.validate(sheet_name, {**base, "isentropic_k": value})
                    self.assertTrue(any(issue.field == "isentropic_k" and issue.code == "range" for issue in issues))
                text_value = {**base, "isentropic_k": "待复核"}
                issues = V4ValidationService.validate(sheet_name, text_value)
                self.assertTrue(any(issue.field == "isentropic_k" and issue.code == "number" for issue in issues))
                whitespace_value = {**base, "isentropic_k": " 1.4 "}
                issues = V4ValidationService.validate(sheet_name, whitespace_value)
                self.assertTrue(any(issue.field == "isentropic_k" and issue.code == "whitespace" for issue in issues))
                self.assertEqual(text_value["isentropic_k"], "待复核")
                self.assertEqual(whitespace_value["isentropic_k"], " 1.4 ")

    def test_axial_fan_hub_ratio_uses_metadata_range_without_rewriting(self):
        self.assertEqual(
            _metadata_range_constraints("轴流通风机"),
            {"isentropic_k": (Decimal("1"), Decimal("2")), "hub_ratio": (Decimal("0"), Decimal("1"))},
        )
        base = {
            "device_name": "F", "model": "F1", "quantity": 1,
            "category": "轴流通风机", "photo": "photo",
        }
        for value in (0, 0.5, 1):
            issues = V4ValidationService.validate("轴流通风机", {**base, "hub_ratio": value})
            self.assertFalse(any(issue.field == "hub_ratio" for issue in issues))
        for value in (-0.1, 1.1):
            issues = V4ValidationService.validate("轴流通风机", {**base, "hub_ratio": value})
            self.assertTrue(any(issue.field == "hub_ratio" and issue.code == "range" for issue in issues))
        text_value = {**base, "hub_ratio": "待复核"}
        issues = V4ValidationService.validate("轴流通风机", text_value)
        self.assertTrue(any(issue.field == "hub_ratio" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "hub_ratio": " 0.5 "}
        issues = V4ValidationService.validate("轴流通风机", whitespace_value)
        self.assertTrue(any(issue.field == "hub_ratio" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["hub_ratio"], "待复核")
        self.assertEqual(whitespace_value["hub_ratio"], " 0.5 ")

    def test_submersible_temperature_uses_metadata_range_without_rewriting(self):
        ranges = _metadata_range_constraints("潜水电泵")
        self.assertEqual(ranges["temperature"], (Decimal("0"), Decimal("100")))
        base = {
            "device_name": "P", "model": "P1", "quantity": 1,
            "category": "小型潜水电泵", "photo": "photo",
        }
        for value in (0, 50, 100):
            issues = V4ValidationService.validate("潜水电泵", {**base, "temperature": value})
            self.assertFalse(any(issue.field == "temperature" for issue in issues))
        for value in (-0.1, 100.1):
            issues = V4ValidationService.validate("潜水电泵", {**base, "temperature": value})
            self.assertTrue(any(issue.field == "temperature" and issue.code == "range" for issue in issues))
        text_value = {**base, "temperature": "待复核"}
        issues = V4ValidationService.validate("潜水电泵", text_value)
        self.assertTrue(any(issue.field == "temperature" and issue.code == "number" for issue in issues))
        whitespace_value = {**base, "temperature": " 50 "}
        issues = V4ValidationService.validate("潜水电泵", whitespace_value)
        self.assertTrue(any(issue.field == "temperature" and issue.code == "whitespace" for issue in issues))
        self.assertEqual(text_value["temperature"], "待复核")
        self.assertEqual(whitespace_value["temperature"], " 50 ")

    def test_duct_category_uses_metadata_enum_and_registered_internal_aliases(self):
        base = {
            "device_name": "D", "model": "D1", "quantity": 1,
            "photo": "photo", "cooling": "风冷式", "mode": "单冷型",
            "enthalpy": "小焓差", "rated_power": 1, "indicator_value": 1,
        }
        for value in (
            "风管送风式空调（热泵）机组",
            "风管送风式机组",
            "直接蒸发式全新风空气处理机组",
            "直接蒸发式全新风机组",
            "其他（请备注说明）",
        ):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("风管送风式空调", {**base, "category": value})
                self.assertFalse(any(issue.field == "category" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("风管送风式空调", {**base, "category": "风管空调机组"})
        self.assertTrue(any(issue.field == "category" and issue.code == "enum" for issue in invalid))

    def test_duct_cooling_uses_metadata_enum_and_internal_alias(self):
        base = {
            "device_name": "D", "model": "D1", "quantity": 1,
            "category": "风管送风式空调（热泵）机组", "mode": "单冷型",
            "enthalpy": "小焓差", "rated_power": 1, "indicator_value": 1,
        }
        for value in ("风冷式", "水冷式（水环式）", "水冷式(水环式)", "不适用", "其他（请备注说明）"):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("风管送风式空调", {**base, "cooling": value})
                self.assertFalse(any(issue.field == "cooling" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("风管送风式空调", {**base, "cooling": "气冷式"})
        self.assertTrue(any(issue.field == "cooling" and issue.code == "enum" for issue in invalid))

    def test_duct_mode_uses_metadata_enum(self):
        base = {
            "device_name": "D", "model": "D1", "quantity": 1,
            "category": "风管送风式空调（热泵）机组", "cooling": "风冷式",
            "enthalpy": "小焓差", "rated_power": 1, "indicator_value": 1,
        }
        for value in ("单冷型", "热泵型", "不适用", "其他（请备注说明）"):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("风管送风式空调", {**base, "mode": value})
                self.assertFalse(any(issue.field == "mode" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("风管送风式空调", {**base, "mode": "制冷制热"})
        self.assertTrue(any(issue.field == "mode" and issue.code == "enum" for issue in invalid))

    def test_duct_enthalpy_uses_metadata_enum(self):
        base = {
            "device_name": "D", "model": "D1", "quantity": 1,
            "category": "风管送风式空调（热泵）机组", "cooling": "风冷式",
            "mode": "单冷型", "rated_power": 1, "indicator_value": 1,
        }
        for value in ("小焓差", "大焓差", "不适用", "其他（请备注说明）"):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("风管送风式空调", {**base, "enthalpy": value})
                self.assertFalse(any(issue.field == "enthalpy" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("风管送风式空调", {**base, "enthalpy": "中焓差"})
        self.assertTrue(any(issue.field == "enthalpy" and issue.code == "enum" for issue in invalid))

    def test_unitary_category_uses_metadata_enum(self):
        base = {
            "device_name": "U", "model": "U1", "quantity": 1,
            "photo": "photo", "cooling": "风冷式", "mode": "单冷型",
            "rated_power": 1, "indicator_value": 1,
        }
        for value in (
            "普通单元式空调机",
            "计算机和数据处理机房用单元式空调机",
            "通讯基站用单元式空气调节机",
            "恒温恒湿型单元式空调机",
            "其他（请备注说明）",
        ):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("单元式空调", {**base, "category": value})
                self.assertFalse(any(issue.field == "category" and issue.code == "enum" for issue in issues))
        # Existing internal evaluator labels are deterministic aliases for the
        # V4 "普通单元式空调机" category and must remain accepted.  A value
        # outside both the canonical list and those aliases is still invalid.
        for alias in ("风冷式单元式空调机", "水冷式单元式空调机"):
            with self.subTest(alias=alias):
                issues = V4ValidationService.validate("单元式空调", {**base, "category": alias})
                self.assertFalse(any(issue.field == "category" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("单元式空调", {**base, "category": "未知单元式空调机"})
        self.assertTrue(any(issue.field == "category" and issue.code == "enum" for issue in invalid))

    def test_unitary_cooling_uses_metadata_enum(self):
        base = {
            "device_name": "U", "model": "U1", "quantity": 1,
            "category": "普通单元式空调机", "mode": "单冷型",
            "rated_power": 1, "indicator_value": 1, "photo": "photo",
        }
        values = (
            "风冷式", "水冷式", "乙二醇经济冷却式", "风冷双冷源式",
            "不适用", "水冷双冷源式", "其他（请备注说明）",
        )
        for value in values:
            with self.subTest(value=value):
                issues = V4ValidationService.validate("单元式空调", {**base, "cooling": value})
                self.assertFalse(any(issue.field == "cooling" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("单元式空调", {**base, "cooling": "水冷双冷源"})
        self.assertTrue(any(issue.field == "cooling" and issue.code == "enum" for issue in invalid))

    def test_unitary_mode_uses_metadata_enum(self):
        base = {
            "device_name": "U", "model": "U1", "quantity": 1,
            "category": "普通单元式空调机", "cooling": "风冷式",
            "rated_power": 1, "indicator_value": 1, "photo": "photo",
        }
        for value in ("单冷型", "热泵型", "不适用", "其他（请备注说明）"):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("单元式空调", {**base, "mode": value})
                self.assertFalse(any(issue.field == "mode" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("单元式空调", {**base, "mode": "单冷/热泵"})
        self.assertTrue(any(issue.field == "mode" and issue.code == "enum" for issue in invalid))

    def test_multi_split_water_source_uses_metadata_enum(self):
        base = {
            "device_name": "M", "model": "M1", "quantity": 1,
            "category": "水冷式多联机", "rated_power": 1,
            "primary_metric_value": 1, "photo": "photo",
        }
        for value in ("水环式", "地埋管式", "地下水式", "不适用", "其他（请备注说明）"):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("多联式空调", {**base, "water_source": value})
                self.assertFalse(any(issue.field == "water_source" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("多联式空调", {**base, "water_source": "水冷式"})
        self.assertTrue(any(issue.field == "water_source" and issue.code == "enum" for issue in invalid))

    def test_multi_split_category_uses_metadata_enum_and_internal_aliases(self):
        base = {
            "device_name": "M", "model": "M1", "quantity": 1,
            "water_source": "不适用", "rated_power": 1,
            "primary_metric_value": 1, "photo": "photo",
        }
        canonical = (
            "风冷式单冷型多联机", "风冷式热泵型多联机", "水冷式多联机",
            "低温多联机", "其他（请备注说明）",
        )
        aliases = ("风冷单冷", "风冷热泵", "水冷", "低温机组")
        for value in (*canonical, *aliases):
            with self.subTest(value=value):
                issues = V4ValidationService.validate("多联式空调", {**base, "category": value})
                self.assertFalse(any(issue.field == "category" and issue.code == "enum" for issue in issues))
        invalid = V4ValidationService.validate("多联式空调", {**base, "category": "多联机"})
        self.assertTrue(any(issue.field == "category" and issue.code == "enum" for issue in invalid))

    def test_multistage_efficiency_sequence_is_checked_as_percent_values(self):
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "多级低速离心鼓风机", "photo": "photo",
        }
        self.assertFalse(any(issue.field == "stage_efficiencies" for issue in V4ValidationService.validate(
            "鼓风机", {**base, "stage_efficiencies": [70, 80, 90]},
        )))
        issues = V4ValidationService.validate(
            "鼓风机", {**base, "stage_efficiencies": [70, 0.8, 101]},
        )
        self.assertTrue(any(issue.field == "stage_efficiencies" and issue.code == "percent_range" for issue in issues))

    def test_percent_uses_v4_1_to_100_rule(self):
        issues = V4ValidationService.validate("电动机", {
            "device_name": "M", "model": "M1", "quantity": 1, "category": "低压",
            "rated_power": 7.5, "rated_speed": 1480, "efficiency": 0.98, "photo": "photo",
        })
        self.assertTrue(any(issue.field == "efficiency" and issue.code == "percent_range" for issue in issues))

    def test_canonical_rated_efficiency_uses_percent_value_rule(self):
        base = {
            "device_name": "M", "model": "M1", "quantity": 1,
            "category": "低压", "rated_power": 7.5, "rated_speed": 1480,
            "photo": "photo",
        }
        self.assertFalse(any(issue.field == "rated_efficiency" for issue in V4ValidationService.validate(
            "电动机", {**base, "rated_efficiency": 98},
        )))
        for value in (0.98, 101):
            issues = V4ValidationService.validate("电动机", {**base, "rated_efficiency": value})
            self.assertTrue(any(issue.field == "rated_efficiency" and issue.code == "percent_range" for issue in issues))

    def test_efficiency_tolerance_is_not_confused_with_efficiency_percent(self):
        values = {
            "device_name": "P", "model": "P1", "quantity": 1,
            "category": "小型潜水电泵", "pump_efficiency": 60,
            "efficiency_tolerance": 0.5, "photo": "photo",
        }
        issues = V4ValidationService.validate("潜水电泵", values)
        self.assertFalse(any(issue.field == "efficiency_tolerance" and issue.code == "percent_range" for issue in issues))

    def test_standard_range_and_integer_rules_cover_non_efficiency_fields(self):
        boiler = V4ValidationService.validate("工业锅炉", {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "层状燃烧燃煤锅炉", "thermal_power": 1,
            "vdaf": 101, "design_efficiency": 90, "photo": "photo",
        })
        self.assertTrue(any(issue.field == "vdaf" and issue.code == "range" for issue in boiler))

        fan = V4ValidationService.validate("轴流通风机", {
            "device_name": "F", "model": "F1", "quantity": 1,
            "category": "轴流通风机", "hub_ratio": 1.2, "isentropic_k": 2.1,
            "photo": "photo",
        })
        self.assertTrue(any(issue.field == "hub_ratio" and issue.code == "range" for issue in fan))
        self.assertTrue(any(issue.field == "isentropic_k" and issue.code == "range" for issue in fan))

        motor = V4ValidationService.validate("电动机", {
            "device_name": "M", "model": "M1", "quantity": 1,
            "category": "低压", "rated_power": 7.5, "poles": 4.5,
            "rated_speed": 1480, "efficiency": 98, "photo": "photo",
        })
        self.assertTrue(any(issue.field == "poles" and issue.code == "integer" for issue in motor))

    def test_standard_range_text_is_reported_as_numeric_error(self):
        boiler = V4ValidationService.validate("工业锅炉", {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "层状燃烧燃煤锅炉", "thermal_power": 1,
            "vdaf": "待复核", "design_efficiency": 90, "photo": "photo",
        })
        self.assertTrue(any(issue.field == "vdaf" and issue.code == "number" for issue in boiler))

        fan = V4ValidationService.validate("轴流通风机", {
            "device_name": "F", "model": "F1", "quantity": 1,
            "category": "轴流通风机", "hub_ratio": "待复核", "photo": "photo",
        })
        self.assertTrue(any(issue.field == "hub_ratio" and issue.code == "number" for issue in fan))

    def test_submersible_efficiency_tolerance_rejects_negative(self):
        issues = V4ValidationService.validate("潜水电泵", {
            "device_name": "P", "model": "P1", "quantity": 1,
            "category": "小型潜水电泵", "efficiency_tolerance": -0.1,
            "photo": "photo",
        })
        self.assertTrue(any(issue.field == "efficiency_tolerance" and issue.code == "non_negative" for issue in issues))

    def test_boiler_requires_evaporation_or_thermal_power(self):
        issues = V4ValidationService.validate("工业锅炉", {
            "device_name": "B", "model": "B1", "quantity": 1, "category": "蒸汽锅炉", "fuel": "天然气", "design_efficiency": 90, "photo": "photo",
        })
        self.assertTrue(any(issue.code == "one_of_required" for issue in issues))

    def test_boiler_efficiency_limit_uses_condensing_field(self):
        base = {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "室燃锅炉", "thermal_power": 1, "photo": "photo",
        }
        condensing = V4ValidationService.validate(
            "工业锅炉", {**base, "condensing": "冷凝", "design_efficiency": 103},
        )
        self.assertFalse(any(issue.field == "design_efficiency" and issue.code == "percent_range" for issue in condensing))
        non_condensing = V4ValidationService.validate(
            "工业锅炉", {**base, "condensing": "非冷凝", "design_efficiency": 103},
        )
        self.assertTrue(any(issue.field == "design_efficiency" and issue.code == "percent_range" for issue in non_condensing))

    def test_axial_fan_requires_hub_ratio_for_standard_binning(self):
        issues = V4ValidationService.validate("轴流通风机", {
            "device_name": "F", "model": "F1", "quantity": 1,
            "category": "轴流通风机", "machine_no": 10,
            "fan_efficiency": 80, "photo": "photo",
        })
        self.assertTrue(any(issue.field == "hub_ratio" and issue.code == "conditional_required" for issue in issues))

    def test_multistage_pump_requires_stage_count_for_single_stage_head(self):
        issues = V4ValidationService.validate("离心泵", {
            "device_name": "P", "model": "P1", "quantity": 1,
            "category": "多级清水离心泵", "flow": 100, "head": 80,
            "speed": 2900, "pump_efficiency": 80, "photo": "photo",
        })
        self.assertTrue(any(issue.field == "stages" and issue.code == "conditional_required" for issue in issues))

    def test_stage_count_uses_metadata_integer_bridge_without_changing_raw_input(self):
        samples = {
            "离心泵": {"category": "多级清水离心泵", "stages": 2},
            "鼓风机": {"category": "多级低速离心鼓风机", "stages": 2},
            "潜水电泵": {"category": "小型潜水电泵", "stages": 2},
        }
        for sheet_name, extra in samples.items():
            with self.subTest(sheet_name=sheet_name):
                values = {
                    "device_name": "D", "model": "D1", "quantity": 1,
                    "photo": "photo", **extra,
                }
                original = dict(values)
                self.assertFalse(any(issue.field == "stages" for issue in V4ValidationService.validate(sheet_name, values)))
                self.assertEqual(values, original)
                invalid = {**values, "stages": 0}
                invalid_issues = V4ValidationService.validate(sheet_name, invalid)
                self.assertTrue(any(issue.field == "stages" for issue in invalid_issues))
                non_integer = {**values, "stages": 1.5}
                non_integer_issues = V4ValidationService.validate(sheet_name, non_integer)
                self.assertTrue(any(issue.field == "stages" and issue.code == "integer" for issue in non_integer_issues))

    def test_heat_treatment_temperature_uses_metadata_positive_bridge_without_rewriting(self):
        constraints = _metadata_numeric_constraints("热处理设备")
        self.assertIsNotNone(constraints)
        self.assertIn("rated_temperature", constraints["positive"])
        values = {
            "device_name": "H", "model": "H1", "quantity": 1,
            "photo": "photo", "category": "传送式连续炉", "rated_temperature": 800,
        }
        original = dict(values)
        self.assertFalse(any(issue.field == "rated_temperature" for issue in V4ValidationService.validate("热处理设备", values)))
        self.assertEqual(values, original)
        zero = V4ValidationService.validate("热处理设备", {**values, "rated_temperature": 0})
        self.assertTrue(any(issue.field == "rated_temperature" and issue.code == "positive" for issue in zero))
        text = V4ValidationService.validate("热处理设备", {**values, "rated_temperature": "待复核"})
        self.assertTrue(any(issue.field == "rated_temperature" and issue.code == "number" for issue in text))

    def test_fan_machine_no_uses_metadata_positive_bridge_and_accepts_decimal(self):
        for sheet_name in ("离心通风机", "轴流通风机"):
            with self.subTest(sheet_name=sheet_name):
                constraints = _metadata_numeric_constraints(sheet_name)
                self.assertIsNotNone(constraints)
                self.assertIn("machine_no", constraints["positive"])
                values = {
                    "device_name": "F", "model": "F1", "quantity": 1,
                    "photo": "photo", "category": "离心通风机" if sheet_name == "离心通风机" else "轴流通风机",
                    "machine_no": 2.5,
                }
                original = dict(values)
                issues = V4ValidationService.validate(sheet_name, values)
                self.assertFalse(any(issue.field == "machine_no" for issue in issues))
                self.assertEqual(values, original)
                zero = V4ValidationService.validate(sheet_name, {**values, "machine_no": 0})
                self.assertTrue(any(issue.field == "machine_no" and issue.code == "positive" for issue in zero))
                text = V4ValidationService.validate(sheet_name, {**values, "machine_no": "待复核"})
                self.assertTrue(any(issue.field == "machine_no" and issue.code == "number" for issue in text))

    def test_transformer_conditionally_requires_standard_classification_fields(self):
        issues = V4ValidationService.validate("变压器", {
            "device_name": "T", "model": "T1", "quantity": 1,
            "category": "10kV干式三相双绕组无励磁调压配电变压器",
            "rated_capacity": 100, "no_load_loss": 100, "load_loss": 1000,
            "photo": "photo",
        })
        fields = {issue.field for issue in issues if issue.code == "conditional_required"}
        self.assertEqual(fields, {"core_material", "insulation"})

    def test_higher_voltage_transformer_does_not_require_10kv_only_fields(self):
        issues = V4ValidationService.validate("变压器", {
            "device_name": "T", "model": "T1", "quantity": 1,
            "category": "110kV油浸式三相双绕组无励磁调压电力变压器",
            "rated_capacity": 10000, "no_load_loss": 100, "load_loss": 1000,
            "photo": "photo",
        })
        self.assertFalse(any(issue.code == "conditional_required" for issue in issues))

    def test_heat_treatment_energy_mutual_exclusion(self):
        issues = V4ValidationService.validate("热处理设备", {
            "device_name": "H", "model": "H1", "quantity": 1, "category": "传送式连续炉", "energy_type": "电力",
            "equivalent_weight": 1, "electricity": 300, "fuel_consumption": 10, "fuel_heat": 40000, "photo": "photo",
        })
        self.assertTrue(any(issue.code == "mutually_exclusive" for issue in issues))

    def test_heat_treatment_fuel_energy_rejects_electricity_field(self):
        """燃料能源填写电炉总耗电量时，应明确保留能源字段互斥问题。"""
        issues = V4ValidationService.validate("热处理设备", {
            "device_name": "H", "model": "H1", "quantity": 1, "category": "传送式连续炉", "energy_type": "天然气",
            "equivalent_weight": 1, "electricity": 300, "fuel_consumption": 10, "fuel_heat": 40000, "photo": "photo",
        })
        self.assertTrue(any(issue.field == "electricity" and issue.code == "mutually_exclusive" for issue in issues))

    def test_multi_split_conditional_gates(self):
        issues = V4ValidationService.validate("多联式空调", {
            "device_name": "A", "model": "A1", "quantity": 1, "category": "低温多联机",
            "rated_power": 2, "external_static": 0, "primary_metric_value": 3, "photo": "photo",
        })
        fields = {issue.field for issue in issues}
        self.assertIn("heating_capacity", fields)
        self.assertIn("cop_minus12_value", fields)
        self.assertIn("cop_minus20_value", fields)

    def test_optional_numeric_fields_are_checked_by_sign(self):
        issues = V4ValidationService.validate("工业锅炉", {
            "device_name": "B", "model": "B1", "quantity": 1,
            "category": "蒸汽锅炉", "fuel": "天然气", "evaporation": -1,
            "thermal_power": "待复核", "photo": "photo",
        })
        by_field = {issue.field: issue.code for issue in issues}
        self.assertEqual(by_field["evaporation"], "positive")
        self.assertEqual(by_field["thermal_power"], "number")

    def test_multisplit_external_static_pressure_allows_zero_but_rejects_negative(self):
        base = {
            "device_name": "A", "model": "A1", "quantity": 1,
            "category": "风冷单冷型多联机", "rated_power": 2,
            "primary_metric_value": 5, "photo": "photo",
        }
        self.assertFalse(any(issue.field == "external_static" for issue in V4ValidationService.validate(
            "多联式空调", {**base, "external_static": 0},
        )))
        issues = V4ValidationService.validate("多联式空调", {**base, "external_static": -1})
        self.assertTrue(any(issue.field == "external_static" and issue.code == "non_negative" for issue in issues))

    def test_multisplit_external_static_pressure_uses_metadata_non_negative_bridge(self):
        self.assertEqual(_metadata_non_negative_constraints("多联式空调"), ("external_static",))
        self.assertEqual(_metadata_non_negative_constraints("单元式空调"), ())

    def test_multisplit_static_dropdown_requires_not_applicable_for_non_water_cooling(self):
        base = {
            "device_name": "A", "model": "A1", "quantity": 1,
            "category": "风冷单冷型多联机", "rated_power": 2,
            "primary_metric_value": 5, "photo": "photo",
        }
        issues = V4ValidationService.validate("多联式空调", {**base, "water_source": "水环式"})
        self.assertTrue(any(issue.field == "water_source" and issue.code == "conditional_enum" for issue in issues))
        self.assertFalse(any(issue.field == "water_source" for issue in V4ValidationService.validate(
            "多联式空调", {**base, "water_source": "不适用"},
        )))

    def test_multisplit_water_cooling_rejects_not_applicable_source(self):
        base = {
            "device_name": "A", "model": "A1", "quantity": 1,
            "category": "水冷式多联机", "rated_power": 2,
            "primary_metric_value": 5, "photo": "photo",
        }
        issues = V4ValidationService.validate("多联式空调", {**base, "water_source": "不适用"})
        self.assertTrue(any(issue.field == "water_source" and issue.code == "conditional_enum" for issue in issues))

    def test_multisplit_static_correction_values_must_be_positive(self):
        base = {
            "device_name": "A", "model": "A1", "quantity": 1,
            "category": "风冷单冷型多联机", "rated_power": 2,
            "primary_metric_value": 5, "photo": "photo",
        }
        issues = V4ValidationService.validate("多联式空调", {
            **base, "static_pressure_correction_factor": 0,
            "static_pressure_corrected_metric": -1,
        })
        by_field = {issue.field: issue.code for issue in issues}
        self.assertEqual(by_field["static_pressure_correction_factor"], "positive")
        self.assertEqual(by_field["static_pressure_corrected_metric"], "positive")

    def test_multisplit_static_correction_alternatives_are_exclusive(self):
        base = {
            "device_name": "A", "model": "A1", "quantity": 1,
            "category": "风冷单冷型多联机", "rated_power": 2,
            "primary_metric_value": 5, "photo": "photo",
            "external_static": 120,
        }
        issues = V4ValidationService.validate("多联式空调", {
            **base, "static_pressure_correction_factor": 0.95,
            "static_pressure_corrected_metric": 5.2,
        })
        self.assertTrue(any(issue.code == "mutually_exclusive" for issue in issues))
        no_static = V4ValidationService.validate("多联式空调", {
            **{key: value for key, value in base.items() if key != "external_static"},
            "static_pressure_correction_factor": 0.95,
        })
        self.assertTrue(any(issue.field == "external_static" and issue.code == "conditional_required" for issue in no_static))

    def test_heat_pump_chiller_table2_uses_copc_then_alternate_metric(self):
        # GB 19577-2024表2不是把COPc和CSPF/IPLV都作为同一主指标；
        # V4把COPc放在主指标、替代指标放在辅助约束指标1。
        values = {
            "device_name": "H", "model": "H1", "quantity": 1,
            "category": "蒸气压缩循环冷水（热泵）机组-舒适型",
            "product_standard": "GB/T 18430.1", "unit_type": "舒适型",
            "source": "水冷式", "evaluation_system": "制冷性能系数COPc指标体系（表2）",
            "cooling_capacity": 100, "rated_power": 20,
            "primary_metric_value": 4.5, "aux_metric1_value": 5.5, "photo": "photo",
        }
        issues = V4ValidationService.validate("热泵和冷水机组", values)
        self.assertFalse(any(issue.code in {"indicator_mismatch", "conditional_required"} for issue in issues))

    def test_hvac_required_classification_fields_are_reported(self):
        issues = V4ValidationService.validate("热泵和冷水机组", {
            "device_name": "H", "model": "H1", "quantity": 1,
            "category": "蒸气压缩循环冷水（热泵）机组-舒适型", "photo": "photo",
        })
        fields = {issue.field for issue in issues if issue.code == "required"}
        self.assertTrue({"product_standard", "unit_type", "source", "evaluation_system", "rated_power"}.issubset(fields))

    def test_dynamic_indicator_name_is_checked_against_v4_formula(self):
        values = {
            "device_name": "A", "model": "A1", "quantity": 1,
            "category": "风冷单冷型多联机", "cooling_capacity": 10,
            "indicator1_name": "SEER", "indicator1_value": 5,
            "indicator2_name": "COP(-12℃)", "indicator2_value": 2,
            "photo": "photo",
        }
        issues = V4ValidationService.validate("多联式空调", values)
        self.assertTrue(any(issue.field == "indicator2_name" and issue.code == "indicator_mismatch" for issue in issues))

    def test_sparse_numbered_indicator_does_not_shift_positions(self):
        values = {
            "device_name": "A", "model": "A1", "quantity": 1,
            "category": "风冷式单冷型多联机", "cooling_capacity": 10,
            "indicator2_name": "EERmin", "indicator2_value": 2.1,
            "photo": "photo",
        }
        issues = V4ValidationService.validate("多联式空调", values)
        self.assertTrue(any(issue.field == "primary_metric_value" and issue.code == "conditional_required" for issue in issues))
        self.assertFalse(any(issue.field == "indicator2_name" and issue.code == "indicator_mismatch" for issue in issues))

    def test_dynamic_metric_aliases_cover_low_temperature_multisplit_values(self):
        values = {
            "device_name": "A", "model": "A1", "quantity": 1,
            "category": "低温多联机", "heating_capacity": 18,
            "primary_metric_value": 3.4, "cop_minus12_value": 2.2,
            "cop_minus20_value": 1.8, "photo": "photo",
        }
        issues = V4ValidationService.validate("多联式空调", values)
        self.assertFalse(any(issue.code == "indicator_mismatch" for issue in issues))
        self.assertFalse(any(issue.code == "conditional_required" and "设计指标" in issue.message for issue in issues))


if __name__ == "__main__":
    unittest.main()
