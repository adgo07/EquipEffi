"""Contract tests for transformer F categories and H condition choices."""

from __future__ import annotations

import unittest

from equipeffi.domain.devices.transformer.input_contract import (
    TRANSFORMER_CATEGORIES,
    TransformerInputError,
    category_fields,
    condition_options,
    normalize_transformer_input,
    visible_fields,
)


class TransformerInputContractTests(unittest.TestCase):
    def test_exactly_35_physical_types_plus_other_and_uncertain(self) -> None:
        self.assertEqual(len(TRANSFORMER_CATEGORIES), 37)
        self.assertEqual(
            [item.category_id for item in TRANSFORMER_CATEGORIES[:35]],
            [f"GB20052-T{number:02d}" for number in range(1, 36)],
        )
        self.assertEqual(TRANSFORMER_CATEGORIES[6].category_id, "GB20052-T07")
        self.assertIn("低压非35kV", TRANSFORMER_CATEGORIES[6].label)
        self.assertEqual(TRANSFORMER_CATEGORIES[11].category_id, "GB20052-T12")
        self.assertIn("低压非66kV", TRANSFORMER_CATEGORIES[11].label)
        self.assertEqual(
            [item.category_id for item in TRANSFORMER_CATEGORIES[-2:]],
            ["OTHER_CATEGORY", "UNCERTAIN_CATEGORY"],
        )
        self.assertEqual(
            [item.label for item in TRANSFORMER_CATEGORIES[-2:]],
            ["其他类别", "不确定类别"],
        )

    def test_h_options_encode_only_physical_conditions(self) -> None:
        self.assertEqual(len(condition_options("GB20052-T01")), 4)
        self.assertEqual(len(condition_options("GB20052-T02")), 6)
        self.assertEqual(len(condition_options("GB20052-T29")), 3)
        self.assertEqual(len(condition_options("GB20052-T30")), 9)
        self.assertEqual(condition_options("GB20052-T03"), ())
        self.assertFalse(any("uk_group" in option.values for option in condition_options("GB20052-T02")))

    def test_h_selection_normalizes_to_stable_fields_without_numeric_coercion(self) -> None:
        option = condition_options("GB20052-T01")[0]
        source = {
            "category": TRANSFORMER_CATEGORIES[0].label,
            "rated_capacity_kva": "30.000",
            "standard_conditions": option.condition_id,
            "no_load_loss_w": "65.00000000001",
        }
        normalized = normalize_transformer_input(source)
        self.assertEqual(normalized["category_id"], "GB20052-T01")
        self.assertEqual(normalized["capacity_kva"], "30.000")
        self.assertEqual(normalized["no_load_loss_w"], "65.00000000001")
        self.assertEqual(normalized["core_material"], "electrical_steel")
        self.assertEqual(normalized["vector_group"], "dyn11_yzn11")
        self.assertEqual(
            normalized["standard_conditions"],
            {"core_material": "electrical_steel", "vector_group": "dyn11_yzn11"},
        )

    def test_usage_and_thermal_selection_shares_same_h_directory(self) -> None:
        option = next(
            item for item in condition_options("GB20052-T32")
            if item.values == {"renewable_type": "wind", "thermal_class": "F"}
        )
        normalized = normalize_transformer_input({
            "category_id": "GB20052-T32", "standard_conditions": option.condition_id,
        })
        self.assertEqual(normalized["renewable_type"], "wind")
        self.assertEqual(normalized["thermal_class"], "F")

    def test_h_thermal_reference_is_145c_and_old_180c_alias_is_rejected(self) -> None:
        for category_id in ("GB20052-T02", "GB20052-T30", "GB20052-T32", "GB20052-T34"):
            with self.subTest(category_id=category_id):
                option = next(
                    item for item in condition_options(category_id)
                    if item.values.get("thermal_class") == "H"
                )
                self.assertIn("H级（145℃）", option.label)
                normalized = normalize_transformer_input({
                    "category_id": category_id,
                    "thermal_class": "H级（145℃）",
                })
                self.assertEqual(normalized["thermal_class"], "H")
                with self.assertRaises(TransformerInputError):
                    normalize_transformer_input({
                        "category_id": category_id,
                        "thermal_class": "H级（180℃）",
                    })

    def test_field_catalog_drives_common_and_conditional_visibility(self) -> None:
        self.assertEqual(
            [item.field_id for item in visible_fields("GB20052-T15")],
            ["capacity_kva", "no_load_loss_w", "load_loss_w", "lv_rated_voltage_kv"],
        )
        t2_uk = next(item for item in category_fields("GB20052-T02") if item.field_id == "uk_rated_percent")
        self.assertFalse(t2_uk.required)
        self.assertEqual(t2_uk.required_when, "capacity_kva == 630")
        t23_hm = next(item for item in category_fields("GB20052-T23") if item.field_id == "uk_hm_rated_percent")
        self.assertFalse(t23_hm.required)
        self.assertNotIn("uk_hl_rated_percent", {item.field_id for item in category_fields("GB20052-T23")})

    def test_conflicting_and_unknown_contract_values_are_rejected(self) -> None:
        with self.assertRaises(TransformerInputError):
            normalize_transformer_input({"category_id": "GB20052-T01", "category": "GB20052-T02"})
        with self.assertRaises(TransformerInputError):
            normalize_transformer_input({"category_id": "GB20052-T03", "standard_conditions": "B"})
        with self.assertRaises(TransformerInputError):
            normalize_transformer_input({"category_id": "GB20052-T01", "standard_conditions": "core=steel"})


if __name__ == "__main__":
    unittest.main()
