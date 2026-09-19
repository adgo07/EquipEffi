from __future__ import annotations

import unittest

from equipeffi.domain.evaluation.device_specs import DEVICE_SPECS
from equipeffi.domain.evaluation.device_types import (
    PUBLIC_DEVICE_NAMES,
    PUBLIC_DEVICE_TYPES,
    PUBLIC_INTERNAL_PROFILES,
)
from equipeffi.application.services.v4_template_contract import V4_DEVICE_SHEETS
from equipeffi.infrastructure.excel.template_resource import V4TemplateResource
from equipeffi.infrastructure.excel.v4_reader import V4WorkbookReaderImpl
from equipeffi.domain.evaluation.metadata import (
    DEVICE_PROFILES,
    DeviceMetadataError,
    get_device_profile,
    get_field_spec,
    list_device_profiles,
    metadata_summary,
)


class DeviceMetadataContractTests(unittest.TestCase):
    def test_registry_follows_the_public_v4_order(self):
        profiles = list_device_profiles()
        self.assertEqual(tuple(profile.public_type for profile in profiles), PUBLIC_DEVICE_TYPES)
        self.assertEqual(tuple(profile.sheet_name for profile in profiles), tuple(PUBLIC_DEVICE_NAMES.values()))
        self.assertEqual(tuple(profile.display_name for profile in profiles), tuple(PUBLIC_DEVICE_NAMES.values()))
        self.assertEqual(tuple(profile.sheet_name for profile in profiles), V4_DEVICE_SHEETS)

    def test_editable_v4_fields_have_a_metadata_mapping(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        for profile in list_device_profiles():
            metadata_by_v4_id = {
                field.v4_field_id: field
                for field in profile.fields
                if field.v4_field_id
            }
            for v4_field in contract.fields_for_public_type(profile.public_type, editable_only=True):
                with self.subTest(device=profile.public_type, field=v4_field.field_id):
                    self.assertIn(v4_field.field_id, metadata_by_v4_id)
                    field = metadata_by_v4_id[v4_field.field_id]
                    self.assertEqual(field.v4_display_name, v4_field.display_name)
                    self.assertEqual(field.v4_unit, v4_field.unit)
                    self.assertTrue(field.editable)

    def test_metadata_preserves_the_editable_v4_column_order(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        for profile in list_device_profiles():
            expected = [
                field.field_id
                for field in contract.fields_for_public_type(profile.public_type, editable_only=True)
            ]
            actual = [
                field.v4_field_id
                for field in profile.input_fields
                if field.v4_field_id
            ]
            self.assertEqual(actual, expected, profile.public_type)

    def test_all_internal_specs_are_reachable_without_inventing_profiles(self):
        reachable: set[str] = set()
        for profile in list_device_profiles():
            self.assertEqual(profile.internal_profiles, PUBLIC_INTERNAL_PROFILES[profile.public_type])
            reachable.update(profile.internal_profiles)
        self.assertEqual(reachable, set(DEVICE_SPECS))
        self.assertEqual(len(reachable), 17)

    def test_each_profile_has_unique_fields_and_common_contract(self):
        common = {"device_name", "model", "quantity", "category", "location", "photo"}
        forbidden = {"设备位号", "是否在标准适用范围", "device_position", "in_scope"}
        for profile in list_device_profiles():
            fields = profile.fields
            field_ids = [field.field_id for field in fields]
            self.assertEqual(len(field_ids), len(set(field_ids)), profile.public_type)
            self.assertTrue(common.issubset(field_ids), profile.public_type)
            self.assertTrue(forbidden.isdisjoint(field_ids), profile.public_type)
            self.assertTrue(profile.input_fields)
            self.assertTrue(profile.result_fields)
            self.assertEqual(field_ids[:6], [
                "seq", "device_name", "model", "quantity", "category", "location",
            ])
            self.assertEqual(field_ids[-4:], [
                "technical_record_id", "photo", "form_note", "auto_note",
            ])
            for field in fields:
                self.assertIn(field.field_id, field.aliases)
                self.assertIn(field.display_name, field.aliases)
                self.assertTrue(field.role in {"input", "calculated", "result"})
                if field.role == "result":
                    self.assertFalse(field.editable)

    def test_spec_fields_preserve_name_label_unit_and_required_flag(self):
        for public_type in PUBLIC_DEVICE_TYPES:
            profile = get_device_profile(public_type)
            for internal_type in profile.internal_profiles:
                for item in DEVICE_SPECS[internal_type]["fields"]:
                    field_id = str(item["name"])
                    field = profile.field(field_id)
                    self.assertIn(str(item.get("label", field_id)), field.aliases)
                    self.assertEqual(field.unit, str(item.get("unit", "-") or "-"))
                    self.assertEqual(
                        field.required_for(internal_type),
                        bool(item.get("required", True)),
                    )
                    self.assertIn(internal_type, field.source_profiles or (internal_type,))

    def test_model_alias_and_special_bounds_are_explicit(self):
        self.assertIn("设备型号", get_field_spec("motor", "model").aliases)
        efficiency = get_field_spec("motor", "rated_efficiency")
        self.assertEqual(efficiency.data_type, "percentage")
        self.assertEqual(str(efficiency.minimum), "1")
        self.assertEqual(str(efficiency.maximum), "100")
        condensing = get_field_spec("industrial_boiler", "design_efficiency")
        self.assertEqual(str(condensing.minimum), "1")
        self.assertEqual(str(condensing.maximum), "110")
        self.assertIsNone(get_field_spec("motor", "production_year").v4_field_id)

    def test_boiler_volatile_matter_metadata_matches_v4_range(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("industrial_boiler").field("volatile_matter_percent")
        v4 = next(item for item in contract.fields_for_public_type("industrial_boiler", editable_only=True)
                   if item.field_id == "vdaf")
        self.assertEqual(field.v4_field_id, "vdaf")
        self.assertEqual(field.data_type, "percentage")
        self.assertEqual(field.unit, "%")
        self.assertEqual((field.minimum, field.maximum), (0, 100))
        self.assertEqual((v4.minimum, v4.maximum), (0, 100))
        self.assertIn("燃煤", v4.required)

    def test_boiler_evaporation_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("industrial_boiler").field("evaporation_tph")
        v4 = next(item for item in contract.fields_for_public_type("industrial_boiler", editable_only=True)
                   if item.field_id == "evaporation")
        self.assertEqual(field.v4_field_id, "evaporation")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "t/h")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("热功率", v4.required)

    def test_boiler_thermal_power_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("industrial_boiler").field("thermal_power_mw")
        v4 = next(item for item in contract.fields_for_public_type("industrial_boiler", editable_only=True)
                   if item.field_id == "thermal_power")
        self.assertEqual(field.v4_field_id, "thermal_power")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "MW")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("蒸发量", v4.required)

    def test_boiler_lhv_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("industrial_boiler").field("lower_heating_value_kjkg")
        v4 = next(item for item in contract.fields_for_public_type("industrial_boiler", editable_only=True)
                   if item.field_id == "lhv")
        self.assertEqual(field.v4_field_id, "lhv")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.v4_unit, "kJ/kg或kJ/m³")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("燃料锅炉", v4.required)

    def test_hpwh_heating_capacity_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_pump_water_heater").field("heating_capacity_kw")
        v4 = next(item for item in contract.fields_for_public_type("heat_pump_water_heater", editable_only=True)
                   if item.field_id == "heating_capacity")
        self.assertEqual(field.v4_field_id, "heating_capacity")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "kW")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)

    def test_hpwh_rated_power_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_pump_water_heater").field("rated_power_kw")
        v4 = next(item for item in contract.fields_for_public_type("heat_pump_water_heater", editable_only=True)
                   if item.field_id == "rated_power")
        self.assertEqual(field.v4_field_id, "rated_power")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "kW")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)

    def test_hpwh_cop_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_pump_water_heater").field("cop")
        v4 = next(item for item in contract.fields_for_public_type("heat_pump_water_heater", editable_only=True)
                   if item.field_id == "cop")
        self.assertEqual(field.v4_field_id, "cop")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "W/W")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)

    def test_chiller_rated_power_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_pump_chiller").field("rated_power_kw")
        v4 = next(item for item in contract.fields_for_public_type("heat_pump_chiller", editable_only=True)
                   if item.field_id == "rated_power")
        self.assertEqual(field.v4_field_id, "rated_power")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "kW")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)

    def test_chiller_cooling_capacity_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_pump_chiller").field("cooling_capacity_kw")
        v4 = next(item for item in contract.fields_for_public_type("heat_pump_chiller", editable_only=True)
                   if item.field_id == "cooling_capacity")
        self.assertEqual(field.v4_field_id, "cooling_capacity")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "kW")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)

    def test_chiller_heating_capacity_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_pump_chiller").field("heating_capacity_kw")
        v4 = next(item for item in contract.fields_for_public_type("heat_pump_chiller", editable_only=True)
                   if item.field_id == "heating_capacity")
        self.assertEqual(field.v4_field_id, "heating_capacity")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "kW")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)

    def test_duct_cooling_capacity_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("duct_ac").field("cooling_capacity_w")
        v4 = next(item for item in contract.fields_for_public_type("duct_ac", editable_only=True)
                   if item.field_id == "cooling_capacity")
        self.assertEqual(field.v4_field_id, "cooling_capacity")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "W")
        self.assertEqual(field.v4_unit, "kW")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)

    def test_unitary_cooling_capacity_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("unitary_ac").field("cooling_capacity_w")
        v4 = next(item for item in contract.fields_for_public_type("unitary_ac", editable_only=True)
                   if item.field_id == "cooling_capacity")
        self.assertEqual(field.v4_field_id, "cooling_capacity")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "W")
        self.assertEqual(field.v4_unit, "kW")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)

    def test_multi_split_cooling_capacity_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("multi_split_ac").field("cooling_capacity_w")
        v4 = next(item for item in contract.fields_for_public_type("multi_split_ac", editable_only=True)
                   if item.field_id == "cooling_capacity")
        self.assertEqual(field.v4_field_id, "cooling_capacity")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "W")
        self.assertEqual(field.v4_unit, "kW")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)

    def test_multi_split_heating_capacity_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("multi_split_ac").field("heating_capacity_w")
        v4 = next(item for item in contract.fields_for_public_type("multi_split_ac", editable_only=True)
                   if item.field_id == "heating_capacity")
        self.assertEqual(field.v4_field_id, "heating_capacity")
        self.assertEqual(field.display_name, "名义制热量")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "W")
        self.assertEqual(field.v4_unit, "kW")
        self.assertEqual(field.required_condition, "低温类别条件必填")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("低温类别条件必填", v4.required)
        self.assertIn("数值>0", v4.validation)

    def test_multi_split_rated_power_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("multi_split_ac").field("rated_power_kw")
        v4 = next(item for item in contract.fields_for_public_type("multi_split_ac", editable_only=True)
                   if item.field_id == "rated_power")
        self.assertEqual(field.v4_field_id, "rated_power")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "kW")
        self.assertEqual(field.v4_unit, "kW")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)

    def test_multi_split_primary_metric_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("multi_split_ac").field("primary_metric_value")
        v4 = next(item for item in contract.fields_for_public_type("multi_split_ac", editable_only=True)
                   if item.field_id == "primary_metric_value")
        self.assertEqual(field.v4_field_id, "primary_metric_value")
        self.assertEqual(field.display_name, "分级指标设计值")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "无量纲")
        self.assertEqual(field.v4_unit, "无量纲")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)
        self.assertIn("数值>0", v4.validation)

    def test_multi_split_eer_min_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("multi_split_ac").field("eer_min_value")
        v4 = next(item for item in contract.fields_for_public_type("multi_split_ac", editable_only=True)
                   if item.field_id == "eer_min_value")
        self.assertEqual(field.v4_field_id, "eer_min_value")
        self.assertEqual(field.display_name, "EER设计值（用于EERmin校核）")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "W/W")
        self.assertEqual(field.v4_unit, "W/W")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)
        self.assertIn("数值>0", v4.validation)

    def test_multi_split_cop_minus12_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("multi_split_ac").field("cop_minus12_value")
        v4 = next(item for item in contract.fields_for_public_type("multi_split_ac", editable_only=True)
                   if item.field_id == "cop_minus12_value")
        self.assertEqual(field.v4_field_id, "cop_minus12_value")
        self.assertEqual(field.display_name, "COP(-12℃)设计值")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "W/W")
        self.assertEqual(field.v4_unit, "W/W")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("低温多联机条件必填", v4.required)
        self.assertIn("数值>0", v4.validation)

    def test_multi_split_cop_minus20_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("multi_split_ac").field("cop_minus20_value")
        v4 = next(item for item in contract.fields_for_public_type("multi_split_ac", editable_only=True)
                   if item.field_id == "cop_minus20_value")
        self.assertEqual(field.v4_field_id, "cop_minus20_value")
        self.assertEqual(field.display_name, "COP(-20℃)设计值")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "W/W")
        self.assertEqual(field.v4_unit, "W/W")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("低温多联机条件必填", v4.required)
        self.assertIn("数值>0", v4.validation)

    def test_duct_rated_power_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("duct_ac").field("rated_power_kw")
        v4 = next(item for item in contract.fields_for_public_type("duct_ac", editable_only=True)
                   if item.field_id == "rated_power")
        self.assertEqual(field.v4_field_id, "rated_power")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "kW")
        self.assertEqual(field.v4_unit, "kW")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)

    def test_duct_indicator_value_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("duct_ac").field("indicator_value")
        v4 = next(item for item in contract.fields_for_public_type("duct_ac", editable_only=True)
                   if item.field_id == "indicator_value")
        self.assertEqual(field.v4_field_id, "indicator_value")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "按指标")
        self.assertEqual(field.v4_unit, "按指标")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)
        self.assertIn("数值>0", v4.validation)

    def test_unitary_rated_power_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("unitary_ac").field("rated_power_kw")
        v4 = next(item for item in contract.fields_for_public_type("unitary_ac", editable_only=True)
                   if item.field_id == "rated_power")
        self.assertEqual(field.v4_field_id, "rated_power")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "kW")
        self.assertEqual(field.v4_unit, "kW")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)

    def test_unitary_indicator_value_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("unitary_ac").field("indicator_value")
        v4 = next(item for item in contract.fields_for_public_type("unitary_ac", editable_only=True)
                   if item.field_id == "indicator_value")
        self.assertEqual(field.v4_field_id, "indicator_value")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "按指标")
        self.assertEqual(field.v4_unit, "按指标")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)
        self.assertIn("数值>0", v4.validation)

    def test_multi_split_external_static_metadata_matches_v4_non_negative_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("multi_split_ac").field("external_static_pressure_pa")
        v4 = next(item for item in contract.fields_for_public_type("multi_split_ac", editable_only=True)
                   if item.field_id == "external_static")
        self.assertEqual(field.v4_field_id, "external_static")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "Pa")
        self.assertEqual(field.v4_unit, "Pa")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("数值≥0", v4.validation)

    def test_chiller_primary_metric_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_pump_chiller").field("primary_metric_value")
        v4 = next(item for item in contract.fields_for_public_type("heat_pump_chiller", editable_only=True)
                   if item.field_id == "primary_metric_value")
        self.assertEqual(field.v4_field_id, "primary_metric_value")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "-")
        self.assertEqual(field.v4_unit, "无量纲")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)

    def test_chiller_aux_metric1_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_pump_chiller").field("aux_metric1_value")
        v4 = next(item for item in contract.fields_for_public_type("heat_pump_chiller", editable_only=True)
                   if item.field_id == "aux_metric1_value")
        self.assertEqual(field.v4_field_id, "aux_metric1_value")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "-")
        self.assertEqual(field.v4_unit, "无量纲")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("条件必填", v4.required)

    def test_chiller_aux_metric2_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_pump_chiller").field("aux_metric2_value")
        v4 = next(item for item in contract.fields_for_public_type("heat_pump_chiller", editable_only=True)
                   if item.field_id == "aux_metric2_value")
        self.assertEqual(field.v4_field_id, "aux_metric2_value")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "-")
        self.assertEqual(field.v4_unit, "无量纲")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("条件必填", v4.required)

    def test_compressor_input_power_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("compressor").field("input_power_kw")
        v4 = next(item for item in contract.fields_for_public_type("compressor", editable_only=True)
                   if item.field_id == "input_power")
        self.assertEqual(field.v4_field_id, "input_power")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "kW")
        self.assertIsNone(field.maximum)
        self.assertEqual(field.minimum, 0)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))
        self.assertIn("必填", v4.required)

    def test_compressor_volume_flow_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("compressor").field("volume_flow_m3min")
        v4 = next(item for item in contract.fields_for_public_type("compressor", editable_only=True)
                   if item.field_id == "volume_flow")
        self.assertEqual(field.v4_field_id, "volume_flow")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "m³/min")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))

    def test_compressor_discharge_pressure_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("compressor").field("discharge_pressure_mpa")
        v4 = next(item for item in contract.fields_for_public_type("compressor", editable_only=True)
                   if item.field_id == "discharge_pressure")
        self.assertEqual(field.v4_field_id, "discharge_pressure")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "MPa")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))

    def test_compressor_specific_power_metadata_matches_v4_positive_field(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("compressor").field("specific_power")
        v4 = next(item for item in contract.fields_for_public_type("compressor", editable_only=True)
                   if item.field_id == "specific_power")
        self.assertEqual(field.v4_field_id, "specific_power")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.unit, "kW/(m³/min)")
        self.assertEqual(field.minimum, 0)
        self.assertIsNone(field.maximum)
        self.assertEqual(v4.minimum, 0)
        self.assertIn(v4.maximum, (None, ""))

    def test_transformer_enum_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        profile = get_device_profile("transformer")
        for field_id in ("category", "core_material", "insulation", "connection"):
            with self.subTest(field=field_id):
                field = profile.field(field_id)
                self.assertTrue(field.enum_name)
                self.assertEqual(
                    tuple(field.enum_values),
                    tuple(contract.enums[field.enum_name]),
                )
                self.assertEqual(field.ui_control, "select")

    def test_motor_category_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("motor").field("category")
        self.assertEqual(field.v4_field_id, "category")
        self.assertEqual(field.enum_name, "EV_MOTOR_CATEGORY")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_motor_rated_voltage_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("motor").field("rated_voltage_v")
        self.assertEqual(field.v4_field_id, "rated_voltage")
        self.assertEqual(field.enum_name, "EV_MOTOR_VOLTAGE")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_motor_poles_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("motor").field("poles")
        self.assertEqual(field.v4_field_id, "poles")
        self.assertEqual(field.enum_name, "EV_POLES_PMSM")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_motor_rated_speed_metadata_matches_v4_numeric_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        v4_field = next(
            field for field in contract.fields_for_public_type("motor", editable_only=True)
            if field.field_id == "rated_speed"
        )
        field = get_device_profile("motor").field("rated_speed_rpm")
        self.assertEqual(field.v4_field_id, v4_field.field_id)
        self.assertEqual(field.v4_display_name, v4_field.display_name)
        self.assertEqual(field.v4_unit, v4_field.unit)
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.ui_control, "number")
        self.assertEqual(str(field.minimum), "0")
        self.assertIsNone(field.maximum)
        self.assertEqual(v4_field.data_type, "数值")
        self.assertEqual(v4_field.minimum, 0)
        self.assertEqual(v4_field.maximum, "")
        self.assertEqual(v4_field.required, "整行启用时必填")
        self.assertEqual(v4_field.validation, "数值>0")
        mapped_ids = [item.v4_field_id for item in get_device_profile("motor").input_fields if item.v4_field_id]
        self.assertLess(mapped_ids.index("rated_speed"), mapped_ids.index("efficiency"))

    def test_fan_and_blower_isentropic_k_metadata_matches_v4_numeric_range(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        for public_type in ("centrifugal_fan", "axial_fan", "blower"):
            with self.subTest(public_type=public_type):
                v4_field = next(
                    field
                    for field in contract.fields_for_public_type(public_type, editable_only=True)
                    if field.field_id == "isentropic_k"
                )
                field = get_device_profile(public_type).field("isentropic_k")
                self.assertEqual(field.v4_field_id, "isentropic_k")
                self.assertEqual(field.v4_display_name, v4_field.display_name)
                self.assertEqual(field.v4_unit, "-")
                self.assertEqual(field.data_type, "number")
                self.assertEqual(field.ui_control, "number")
                self.assertEqual(str(field.minimum), "1")
                self.assertEqual(str(field.maximum), "2")
                self.assertEqual(v4_field.data_type, "数值")
                self.assertEqual(v4_field.minimum, 1)
                self.assertEqual(v4_field.maximum, 2)
                self.assertEqual(v4_field.required, "整行启用时必填")
                self.assertEqual(v4_field.validation, "1～2")

    def test_axial_fan_hub_ratio_metadata_matches_v4_numeric_range(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        v4_field = next(
            field
            for field in contract.fields_for_public_type("axial_fan", editable_only=True)
            if field.field_id == "hub_ratio"
        )
        field = get_device_profile("axial_fan").field("hub_ratio")
        self.assertEqual(field.v4_field_id, "hub_ratio")
        self.assertEqual(field.v4_display_name, v4_field.display_name)
        self.assertEqual(field.v4_unit, "-")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.ui_control, "number")
        self.assertEqual(str(field.minimum), "0")
        self.assertEqual(str(field.maximum), "1")
        self.assertEqual(v4_field.data_type, "数值")
        self.assertEqual(v4_field.minimum, 0)
        self.assertEqual(v4_field.maximum, 1)
        self.assertEqual(v4_field.required, "轴流通风机必填")
        self.assertEqual(v4_field.validation, "0～1")

    def test_centrifugal_fan_hub_ratio_remains_hidden_internal_field(self):
        field = get_device_profile("centrifugal_fan").field("hub_ratio")
        self.assertIsNone(field.v4_field_id)
        self.assertEqual(field.data_type, "text")
        self.assertEqual(field.ui_control, "hidden")

    def test_submersible_temperature_metadata_matches_v4_numeric_range(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        v4_field = next(
            field
            for field in contract.fields_for_public_type("submersible_pump", editable_only=True)
            if field.field_id == "temperature"
        )
        field = get_device_profile("submersible_pump").field("working_temperature_c")
        self.assertEqual(field.v4_field_id, "temperature")
        self.assertEqual(field.v4_display_name, v4_field.display_name)
        self.assertEqual(field.v4_unit, "℃")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.ui_control, "number")
        self.assertEqual(str(field.minimum), "0")
        self.assertEqual(str(field.maximum), "100")
        self.assertEqual(v4_field.data_type, "数值")
        self.assertEqual(v4_field.minimum, 0)
        self.assertEqual(v4_field.maximum, 100)
        self.assertEqual(v4_field.required, "整行启用时必填")
        self.assertEqual(v4_field.validation, "0～100")

    def test_stage_count_metadata_matches_positive_integer_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        for public_type in ("centrifugal_pump", "blower", "submersible_pump"):
            with self.subTest(public_type=public_type):
                v4_field = next(
                    field
                    for field in contract.fields_for_public_type(public_type, editable_only=True)
                    if field.field_id == "stages"
                )
                field = get_device_profile(public_type).field("stages")
                self.assertEqual(field.v4_field_id, "stages")
                self.assertEqual(field.v4_display_name, v4_field.display_name)
                self.assertEqual(field.v4_unit, "级")
                self.assertEqual(field.data_type, "integer")
                self.assertEqual(field.ui_control, "number")
                self.assertEqual(str(field.minimum), "1")
                self.assertIsNone(field.maximum)
                self.assertEqual(v4_field.data_type, "整数")
                self.assertEqual(v4_field.minimum, 1)
                self.assertIn(v4_field.validation, {"正整数", "整数≥1"})

    def test_heat_treatment_rated_temperature_metadata_matches_v4_positive_number(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        v4_field = next(
            field
            for field in contract.fields_for_public_type("heat_treatment", editable_only=True)
            if field.field_id == "rated_temperature"
        )
        field = get_device_profile("heat_treatment").field("rated_temperature_c")
        self.assertEqual(field.v4_field_id, "rated_temperature")
        self.assertEqual(field.v4_display_name, v4_field.display_name)
        self.assertEqual(field.v4_unit, "℃")
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.ui_control, "number")
        self.assertEqual(str(field.minimum), "0")
        self.assertIsNone(field.maximum)
        self.assertEqual(v4_field.data_type, "数值")
        self.assertEqual(v4_field.minimum, 0)
        self.assertEqual(v4_field.maximum, "")
        self.assertEqual(v4_field.validation, "数值>0")

    def test_fan_machine_no_metadata_matches_v4_positive_number(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        for public_type in ("centrifugal_fan", "axial_fan"):
            with self.subTest(public_type=public_type):
                v4_field = next(
                    field
                    for field in contract.fields_for_public_type(public_type, editable_only=True)
                    if field.field_id == "machine_no"
                )
                field = get_device_profile(public_type).field("machine_no")
                self.assertEqual(field.v4_field_id, "machine_no")
                self.assertEqual(field.v4_display_name, "机号")
                self.assertEqual(field.v4_unit, "No.")
                self.assertEqual(field.data_type, "number")
                self.assertEqual(field.ui_control, "number")
                self.assertEqual(str(field.minimum), "0")
                self.assertIsNone(field.maximum)
                self.assertEqual(v4_field.data_type, "数值")
                self.assertEqual(v4_field.minimum, 0)
                self.assertEqual(v4_field.maximum, "")
                self.assertEqual(v4_field.validation, "数值>0")

    def test_compressor_category_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("compressor").field("category")
        self.assertEqual(field.enum_name, "EV_COMPRESSOR_CATEGORY")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_compressor_cooling_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("compressor").field("cooling_method")
        self.assertEqual(field.v4_field_id, "cooling")
        self.assertEqual(field.enum_name, "EV_COMPRESSOR_COOLING")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_centrifugal_pump_category_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("centrifugal_pump").field("category")
        self.assertEqual(field.enum_name, "EV_PUMP_CATEGORY")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_centrifugal_pump_suction_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("centrifugal_pump").field("suction")
        self.assertEqual(field.v4_field_id, "suction")
        self.assertEqual(field.enum_name, "EV_SUCTION")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_submersible_device_form_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("submersible_pump").field("subtype")
        self.assertEqual(field.v4_field_id, "device_form")
        self.assertEqual(field.enum_name, "EV_SUB_FORM_ALL")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_submersible_category_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("submersible_pump").field("category")
        self.assertEqual(field.v4_field_id, "category")
        self.assertEqual(field.enum_name, "EV_SUBMERSIBLE_CATEGORY")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_boiler_category_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("industrial_boiler").field("category")
        self.assertEqual(field.enum_name, "EV_BOILER_CATEGORY")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_boiler_fuel_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("industrial_boiler").field("fuel")
        self.assertEqual(field.v4_field_id, "fuel")
        self.assertEqual(field.enum_name, "EV_FUEL")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_heat_treatment_category_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_treatment").field("category")
        self.assertEqual(field.v4_field_id, "category")
        self.assertEqual(field.enum_name, "EV_HEAT_TREAT_CATEGORY")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_heat_treatment_energy_type_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_treatment").field("energy_type")
        self.assertEqual(field.v4_field_id, "energy_type")
        self.assertEqual(field.enum_name, "EV_ENERGY_TYPE")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_hpwh_heating_method_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_pump_water_heater").field("heating_method")
        self.assertEqual(field.enum_name, "EV_HEATING_METHOD")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_hpwh_category_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_pump_water_heater").field("category")
        self.assertEqual(field.v4_field_id, "category")
        self.assertEqual(field.enum_name, "EV_HPWH_CATEGORY")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_hpwh_with_pump_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_pump_water_heater").field("with_pump")
        self.assertEqual(field.enum_name, "EV_YES_NO")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_heat_pump_chiller_category_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_pump_chiller").field("category")
        self.assertEqual(field.v4_field_id, "category")
        self.assertEqual(field.enum_name, "EV_HP_CHILLER_CATEGORY")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_heat_pump_chiller_product_standard_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_pump_chiller").field("product_standard")
        self.assertEqual(field.v4_field_id, "product_standard")
        self.assertEqual(field.enum_name, "EV_HP_STD_ALL")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_heat_pump_chiller_unit_type_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_pump_chiller").field("unit_type")
        self.assertEqual(field.v4_field_id, "unit_type")
        self.assertEqual(field.enum_name, "EV_HP_UNIT_ALL")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_heat_pump_chiller_source_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_pump_chiller").field("source")
        self.assertEqual(field.v4_field_id, "source")
        self.assertEqual(field.enum_name, "EV_HP_SOURCE_ALL")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_heat_pump_chiller_evaluation_system_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("heat_pump_chiller").field("evaluation_system")
        self.assertEqual(field.v4_field_id, "evaluation_system")
        self.assertEqual(field.enum_name, "EV_HP_EVAL_SYSTEM")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_centrifugal_fan_category_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("centrifugal_fan").field("category")
        self.assertEqual(field.v4_field_id, "category")
        self.assertEqual(field.enum_name, "EV_CENTRIFUGAL_FAN_CATEGORY")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_centrifugal_fan_transmission_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("centrifugal_fan").field("transmission")
        self.assertEqual(field.v4_field_id, "transmission")
        self.assertEqual(field.enum_name, "EV_TRANSMISSION")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_axial_fan_category_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("axial_fan").field("category")
        self.assertEqual(field.v4_field_id, "category")
        self.assertEqual(field.enum_name, "EV_AXIAL_FAN_CATEGORY")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_axial_fan_transmission_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("axial_fan").field("transmission")
        self.assertEqual(field.v4_field_id, "transmission")
        self.assertEqual(field.enum_name, "EV_TRANSMISSION")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_centrifugal_fan_suction_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("centrifugal_fan").field("suction")
        self.assertEqual(field.v4_field_id, "suction")
        self.assertEqual(field.enum_name, "EV_SUCTION")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_centrifugal_fan_hvac_use_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("centrifugal_fan").field("hvac_use")
        self.assertEqual(field.v4_field_id, "hvac_use")
        self.assertEqual(field.enum_name, "EV_YES_NO")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_centrifugal_fan_inlet_box_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("centrifugal_fan").field("inlet_box")
        self.assertEqual(field.v4_field_id, "inlet_box")
        self.assertEqual(field.enum_name, "EV_YES_NO")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_axial_fan_inlet_box_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("axial_fan").field("inlet_box")
        self.assertEqual(field.v4_field_id, "inlet_box")
        self.assertEqual(field.enum_name, "EV_YES_NO")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_axial_fan_diffuser_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("axial_fan").field("diffuser")
        self.assertEqual(field.v4_field_id, "diffuser")
        self.assertEqual(field.enum_name, "EV_YES_NO")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_axial_fan_variable_blade_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("axial_fan").field("variable_blade")
        self.assertEqual(field.v4_field_id, "variable_blade")
        self.assertEqual(field.enum_name, "EV_YES_NO")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_axial_fan_reversible_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("axial_fan").field("reversible")
        self.assertEqual(field.v4_field_id, "reversible")
        self.assertEqual(field.enum_name, "EV_YES_NO")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_blower_category_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("blower").field("category")
        self.assertEqual(field.v4_field_id, "category")
        self.assertEqual(field.enum_name, "EV_BLOWER_CATEGORY")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_blower_inlet_pressure_metadata_matches_v4_numeric_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        v4_field = next(
            field for field in contract.fields_for_public_type("blower", editable_only=True)
            if field.field_id == "p1"
        )
        field = get_device_profile("blower").field("inlet_absolute_pressure_kpa")
        self.assertEqual(field.v4_field_id, "p1")
        self.assertEqual(field.v4_display_name, v4_field.display_name)
        self.assertEqual(field.v4_unit, v4_field.unit)
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.ui_control, "number")
        self.assertEqual(str(field.minimum), "0")
        self.assertIsNone(field.maximum)
        self.assertEqual(v4_field.data_type, "数值")
        self.assertEqual(v4_field.minimum, 0)
        self.assertEqual(v4_field.maximum, "")
        self.assertEqual(v4_field.required, "整行启用时必填")
        self.assertEqual(v4_field.validation, "数值>0")

    def test_blower_outlet_pressure_metadata_matches_v4_numeric_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        v4_field = next(
            field for field in contract.fields_for_public_type("blower", editable_only=True)
            if field.field_id == "p2"
        )
        field = get_device_profile("blower").field("outlet_absolute_pressure_kpa")
        self.assertEqual(field.v4_field_id, "p2")
        self.assertEqual(field.v4_display_name, v4_field.display_name)
        self.assertEqual(field.v4_unit, v4_field.unit)
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.ui_control, "number")
        self.assertEqual(str(field.minimum), "0")
        self.assertIsNone(field.maximum)
        self.assertEqual(v4_field.data_type, "数值")
        self.assertEqual(v4_field.minimum, 0)
        self.assertEqual(v4_field.maximum, "")
        self.assertEqual(v4_field.required, "整行启用时必填")
        self.assertEqual(v4_field.validation, "数值>0")

    def test_blower_inlet_temperature_metadata_matches_v4_numeric_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        v4_field = next(
            field for field in contract.fields_for_public_type("blower", editable_only=True)
            if field.field_id == "t1"
        )
        field = get_device_profile("blower").field("inlet_temperature_k")
        self.assertEqual(field.v4_field_id, "t1")
        self.assertEqual(field.v4_display_name, v4_field.display_name)
        self.assertEqual(field.v4_unit, v4_field.unit)
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.ui_control, "number")
        self.assertEqual(str(field.minimum), "0")
        self.assertIsNone(field.maximum)
        self.assertEqual(v4_field.data_type, "数值")
        self.assertEqual(v4_field.minimum, 0)
        self.assertEqual(v4_field.maximum, "")
        self.assertEqual(v4_field.required, "整行启用时必填")
        self.assertEqual(v4_field.validation, "数值>0")

    def test_blower_outlet_temperature_metadata_matches_v4_numeric_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        v4_field = next(
            field for field in contract.fields_for_public_type("blower", editable_only=True)
            if field.field_id == "t2"
        )
        field = get_device_profile("blower").field("outlet_temperature_k")
        self.assertEqual(field.v4_field_id, "t2")
        self.assertEqual(field.v4_display_name, v4_field.display_name)
        self.assertEqual(field.v4_unit, v4_field.unit)
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.ui_control, "number")
        self.assertEqual(str(field.minimum), "0")
        self.assertIsNone(field.maximum)
        self.assertEqual(v4_field.data_type, "数值")
        self.assertEqual(v4_field.minimum, 0)
        self.assertEqual(v4_field.maximum, "")
        self.assertEqual(v4_field.required, "整行启用时必填")
        self.assertEqual(v4_field.validation, "数值>0")

    def test_blower_impeller_width_metadata_matches_v4_numeric_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        v4_field = next(
            field for field in contract.fields_for_public_type("blower", editable_only=True)
            if field.field_id == "b2"
        )
        field = get_device_profile("blower").field("impeller_width_mm")
        self.assertEqual(field.v4_field_id, "b2")
        self.assertEqual(field.v4_display_name, v4_field.display_name)
        self.assertEqual(field.v4_unit, v4_field.unit)
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.ui_control, "number")
        self.assertEqual(str(field.minimum), "0")
        self.assertIsNone(field.maximum)
        self.assertEqual(v4_field.data_type, "数值")
        self.assertEqual(v4_field.minimum, 0)
        self.assertEqual(v4_field.maximum, "")
        self.assertEqual(v4_field.required, "整行启用时必填")
        self.assertEqual(v4_field.validation, "数值>0")

    def test_blower_impeller_diameter_metadata_matches_v4_numeric_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        v4_field = next(
            field for field in contract.fields_for_public_type("blower", editable_only=True)
            if field.field_id == "d2"
        )
        field = get_device_profile("blower").field("impeller_diameter_mm")
        self.assertEqual(field.v4_field_id, "d2")
        self.assertEqual(field.v4_display_name, v4_field.display_name)
        self.assertEqual(field.v4_unit, v4_field.unit)
        self.assertEqual(field.data_type, "number")
        self.assertEqual(field.ui_control, "number")
        self.assertEqual(str(field.minimum), "0")
        self.assertIsNone(field.maximum)
        self.assertEqual(v4_field.data_type, "数值")
        self.assertEqual(v4_field.minimum, 0)
        self.assertEqual(v4_field.maximum, "")
        self.assertEqual(v4_field.required, "整行启用时必填")
        self.assertEqual(v4_field.validation, "数值>0")

    def test_blower_polytropic_efficiency_metadata_matches_v4_percentage_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        v4_field = next(
            field for field in contract.fields_for_public_type("blower", editable_only=True)
            if field.field_id == "polytropic_efficiency"
        )
        field = get_device_profile("blower").field("polytropic_efficiency")
        self.assertEqual(field.v4_field_id, "polytropic_efficiency")
        self.assertEqual(field.v4_display_name, v4_field.display_name)
        self.assertEqual(field.v4_unit, v4_field.unit)
        self.assertEqual(field.data_type, "percentage")
        self.assertEqual(field.ui_control, "number")
        self.assertEqual(str(field.minimum), "1")
        self.assertEqual(str(field.maximum), "100")
        self.assertEqual(v4_field.data_type, "数值")
        self.assertEqual(v4_field.minimum, 1)
        self.assertEqual(v4_field.maximum, 100)
        self.assertEqual(v4_field.required, "整行启用时必填")
        self.assertEqual(v4_field.validation, "百分数本值1～100")

    def test_blower_multi_impeller_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("blower").field("multi_impeller")
        self.assertEqual(field.v4_field_id, "multi_impeller")
        self.assertEqual(field.enum_name, "EV_YES_NO")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_blower_cantilever_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("blower").field("cantilever")
        self.assertEqual(field.v4_field_id, "cantilever")
        self.assertEqual(field.enum_name, "EV_YES_NO")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_blower_three_dimensional_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("blower").field("three_dimensional")
        self.assertEqual(field.v4_field_id, "three_dimensional")
        self.assertEqual(field.enum_name, "EV_YES_NO")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_duct_category_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("duct_ac").field("category")
        self.assertEqual(field.enum_name, "EV_DUCT_CATEGORY")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_duct_cooling_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("duct_ac").field("cooling_source")
        self.assertEqual(field.v4_field_id, "cooling")
        self.assertEqual(field.enum_name, "EV_AC_COOLING_DUCT")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_duct_mode_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("duct_ac").field("mode")
        self.assertEqual(field.enum_name, "EV_AC_MODE")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_duct_enthalpy_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("duct_ac").field("enthalpy_difference")
        self.assertEqual(field.v4_field_id, "enthalpy")
        self.assertEqual(field.enum_name, "EV_ENTHALPY")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_unitary_category_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("unitary_ac").field("category")
        self.assertEqual(field.enum_name, "EV_UNITARY_CATEGORY")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_unitary_cooling_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("unitary_ac").field("cooling_source")
        self.assertEqual(field.v4_field_id, "cooling")
        self.assertEqual(field.enum_name, "EV_AC_COOLING_UNITARY")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_unitary_mode_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("unitary_ac").field("mode")
        self.assertEqual(field.v4_field_id, "mode")
        self.assertEqual(field.enum_name, "EV_AC_MODE")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_multi_split_water_source_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("multi_split_ac").field("cooling_source")
        self.assertEqual(field.v4_field_id, "water_source")
        self.assertEqual(field.enum_name, "EV_WATER_SOURCE")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

    def test_multi_split_category_metadata_matches_v4_contract(self):
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        field = get_device_profile("multi_split_ac").field("category")
        self.assertEqual(field.v4_field_id, "category")
        self.assertEqual(field.enum_name, "EV_MULTI_CATEGORY")
        self.assertEqual(tuple(field.enum_values), tuple(contract.enums[field.enum_name]))
        self.assertEqual(field.ui_control, "select")

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
