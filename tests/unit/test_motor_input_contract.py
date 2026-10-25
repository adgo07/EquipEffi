"""Tests for the controlled GB 18613 motor input contract."""

from __future__ import annotations

import unittest

from equipeffi.domain.devices.motor.input_contract import (
    BASIS_OPTIONS, MOTOR_CATEGORIES, MotorInputError, normalize_motor_input,
    efficiency_basis_hint, options, scope_hint, visible_fields,
)


class MotorInputContractTests(unittest.TestCase):
    def test_exactly_six_standard_types_plus_other_and_uncertain(self) -> None:
        self.assertEqual([x.category_id for x in MOTOR_CATEGORIES], [
            "three_phase_induction", "capacitor_start", "capacitor_run", "two_value_capacitor",
            "ac_fan_capacitor_run", "ac_fan_brushless_dc", "OTHER_CATEGORY", "UNCERTAIN_CATEGORY",
        ])
        self.assertEqual([x.table_no for x in MOTOR_CATEGORIES[:6]], [1, 2, 3, 4, 5, 6])
        self.assertEqual([x.label for x in MOTOR_CATEGORIES[-2:]], ["其他类别", "不确定类别"])

    def test_conditional_fields_follow_table_routes(self) -> None:
        expected = {
            "three_phase_induction": {"rated_voltage_kv", "rated_frequency_hz", "poles"},
            "capacitor_start": {"rated_voltage_kv", "rated_frequency_hz", "poles"},
            "capacitor_run": {"rated_voltage_kv", "rated_frequency_hz", "poles"},
            "two_value_capacitor": {"rated_voltage_kv", "rated_frequency_hz", "poles"},
            "ac_fan_capacitor_run": {"poles"},
            "ac_fan_brushless_dc": {"max_nameplate_speed_rpm"},
        }
        for category_id, route_fields in expected.items():
            with self.subTest(category=category_id):
                fields = {field.field_id for field in visible_fields(category_id)}
                self.assertTrue({"rated_output_power_kw", "measured_efficiency_pct", "efficiency_basis_status", "user_note"} <= fields)
                self.assertEqual(fields & {"rated_voltage_kv", "rated_frequency_hz", "poles", "max_nameplate_speed_rpm"}, route_fields)
        self.assertEqual(visible_fields("OTHER_CATEGORY"), ())
        self.assertEqual(visible_fields("UNCERTAIN_CATEGORY"), ())

    def test_scope_and_efficiency_basis_hints_are_available_from_contract(self) -> None:
        for term in ("单速", "封闭自扇冷", "N设计", "连续工作制", "一般用途防爆"):
            self.assertIn(term, scope_hint("three_phase_induction"))
        self.assertIn("一般用途", scope_hint("capacitor_start"))
        self.assertIn("空调器风扇", scope_hint("ac_fan_brushless_dc"))
        self.assertIn("GB/T 1032 B法", efficiency_basis_hint("three_phase_induction"))
        self.assertIn("不得以普通输入/输出功率比替代", efficiency_basis_hint("three_phase_induction"))
        self.assertIn("GB/T 5171.21直接法", efficiency_basis_hint("capacitor_run"))
        self.assertIn("铭牌标称最高转速", efficiency_basis_hint("ac_fan_capacitor_run"))
        self.assertIn("整体效率", efficiency_basis_hint("ac_fan_brushless_dc"))

    def test_category_specific_enum_options(self) -> None:
        self.assertEqual(options("three_phase_induction", "poles"), (("2", "2极"), ("4", "4极"), ("6", "6极"), ("8", "8极")))
        self.assertEqual(options("two_value_capacitor", "poles"), (("2", "2极"), ("4", "4极")))
        self.assertEqual(options("ac_fan_brushless_dc", "poles"), ())
        self.assertEqual(tuple(code for code, _ in BASIS_OPTIONS), ("USER_DECLARED", "NAMEPLATE_ONLY", "KNOWN_NONCONFORMING", "INSEPARABLE_MOTOR_ONLY", "UNKNOWN"))

    def test_normalization_preserves_numeric_lexemes_and_basis_evidence(self) -> None:
        normalized = normalize_motor_input({
            "category": "三相异步电动机（一般用途或一般用途防爆）",
            "rated_output_power_kw": "0.1400", "measured_efficiency_pct": "71.4300",
        })
        self.assertEqual(normalized["category_id"], "three_phase_induction")
        self.assertEqual(normalized["rated_output_power_kw"], "0.1400")
        self.assertEqual(normalized["measured_efficiency_pct"], "71.4300")
        self.assertEqual(normalized["efficiency_basis_status"], "AS_DECLARED_BY_FIELD")
        self.assertEqual(normalized["efficiency_basis_raw"], "")
        explicit = normalize_motor_input({"category_id": "ac_fan_brushless_dc", "efficiency_basis_status": "驱动不可分离但仅有电机本体效率（仅表6）"})
        self.assertEqual(explicit["efficiency_basis_status"], "INSEPARABLE_MOTOR_ONLY")

    def test_contradictory_or_unknown_options_are_rejected(self) -> None:
        with self.assertRaises(MotorInputError):
            normalize_motor_input({"category_id": "three_phase_induction", "category": "capacitor_run"})
        with self.assertRaises(MotorInputError):
            normalize_motor_input({"category_id": "not-a-motor-category"})
        with self.assertRaises(MotorInputError):
            normalize_motor_input({"category_id": "capacitor_run", "efficiency_basis_status": "INSEPARABLE_MOTOR_ONLY"})


if __name__ == "__main__":
    unittest.main()
