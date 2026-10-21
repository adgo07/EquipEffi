from __future__ import annotations

import unittest

from equipeffi.domain.evaluation.device_specs import DEVICE_SPECS
from equipeffi.domain.evaluation.device_types import (
    PUBLIC_DEVICE_NAMES, PUBLIC_DEVICE_TYPES, PUBLIC_INTERNAL_PROFILES,
)
from equipeffi.domain.evaluation.metadata import (
    DEVICE_PROFILES, DeviceMetadataError, get_device_profile, get_field_spec,
    list_device_profiles, metadata_summary,
)


class DeviceMetadataContractTests(unittest.TestCase):
    def test_registry_matches_public_device_types(self):
        profiles = list_device_profiles()
        self.assertEqual(tuple(profile.public_type for profile in profiles), PUBLIC_DEVICE_TYPES)
        self.assertEqual(tuple(profile.sheet_name for profile in profiles), tuple(PUBLIC_DEVICE_NAMES.values()))
        self.assertEqual(tuple(profile.display_name for profile in profiles), tuple(PUBLIC_DEVICE_NAMES.values()))

    def test_all_internal_specs_are_reachable_without_inventing_profiles(self):
        reachable: set[str] = set()
        for profile in list_device_profiles():
            self.assertEqual(profile.internal_profiles, PUBLIC_INTERNAL_PROFILES[profile.public_type])
            reachable.update(profile.internal_profiles)
        self.assertEqual(reachable, set(DEVICE_SPECS))
        self.assertEqual(len(reachable), 17)

    def test_each_profile_preserves_complete_field_metadata(self):
        common = {"device_name", "model", "quantity", "category", "location", "photo"}
        for profile in list_device_profiles():
            with self.subTest(device=profile.public_type):
                fields = profile.fields
                field_ids = [field.field_id for field in fields]
                self.assertEqual(len(field_ids), len(set(field_ids)))
                self.assertTrue(common.issubset(field_ids))
                self.assertTrue(profile.input_fields)
                self.assertTrue(profile.result_fields)
                for field in fields:
                    self.assertIn(field.field_id, field.aliases)
                    self.assertIn(field.display_name, field.aliases)
                    self.assertIn(field.role, {"input", "calculated", "result"})
                    self.assertTrue(field.data_type)
                    if field.enum_name:
                        self.assertTrue(field.enum_values)
                        self.assertEqual(field.ui_control, "select")
                    if field.role == "result":
                        self.assertFalse(field.editable)
                    if field.v4_field_id:
                        # Preserve established external field IDs as mapping values;
                        # this metadata does not retain V4 runtime support.
                        self.assertIn(field.v4_field_id, field.aliases)
                        self.assertTrue(field.v4_display_name)
                        self.assertTrue(field.v4_unit)

    def test_spec_fields_preserve_name_label_unit_and_required_flag(self):
        for public_type in PUBLIC_DEVICE_TYPES:
            profile = get_device_profile(public_type)
            for internal_type in profile.internal_profiles:
                for item in DEVICE_SPECS[internal_type]["fields"]:
                    field_id = str(item["name"])
                    field = profile.field(field_id)
                    self.assertIn(str(item.get("label", field_id)), field.aliases)
                    self.assertEqual(field.unit, str(item.get("unit", "-") or "-"))
                    self.assertEqual(field.required_for(internal_type), bool(item.get("required", True)))
                    self.assertIn(internal_type, field.source_profiles or (internal_type,))

    def test_special_bounds_and_v6_pump_field_ids_remain_stable(self):
        self.assertIn("设备型号", get_field_spec("motor", "model").aliases)
        efficiency = get_field_spec("motor", "rated_efficiency")
        self.assertEqual(efficiency.data_type, "percentage")
        self.assertEqual((str(efficiency.minimum), str(efficiency.maximum)), ("1", "100"))
        condensing = get_field_spec("industrial_boiler", "design_efficiency")
        self.assertEqual((str(condensing.minimum), str(condensing.maximum)), ("1", "110"))
        self.assertIsNone(get_field_spec("motor", "production_year").v4_field_id)

        pump = get_device_profile("centrifugal_pump")
        expected = {
            "flow_m3h": ("flow", "m³/h"), "head_m": ("head", "m"),
            "rated_speed_rpm": ("speed", "r/min"),
            "rated_power_kw": ("power", "kW"), "stages": ("stages", "级"),
            "pump_efficiency": ("efficiency", "%"),
        }
        for field_id, (external_id, unit) in expected.items():
            with self.subTest(field=field_id):
                field = pump.field(field_id)
                self.assertEqual(field.v4_field_id, external_id)
                self.assertEqual(field.unit, unit)

    def test_registry_is_read_only_but_serialization_returns_copies(self):
        with self.assertRaises(TypeError):
            DEVICE_PROFILES["motor"] = DEVICE_PROFILES["transformer"]  # type: ignore[index]
        with self.assertRaises(Exception):
            get_device_profile("motor").fields += ()  # type: ignore[misc]
        payload = get_device_profile("电动机").as_dict()
        payload["fields"].clear()
        self.assertTrue(get_device_profile("motor").fields)
        self.assertEqual(metadata_summary()["public_device_count"], 15)

    def test_unknown_public_type_has_a_domain_error(self):
        with self.assertRaises(DeviceMetadataError):
            get_device_profile("不存在的设备")


if __name__ == "__main__":
    unittest.main()
