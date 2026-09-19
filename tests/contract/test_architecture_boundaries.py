from __future__ import annotations

from pathlib import Path
import unittest

from equipeffi.application.services.v4_template_contract import V4_DEVICE_SHEETS
from equipeffi.domain.evaluation.device_types import (
    PUBLIC_DEVICE_NAMES,
    PUBLIC_DEVICE_TYPES,
    PUBLIC_INTERNAL_PROFILES,
    profiles_for_public_type,
)
from equipeffi.domain.evaluation.evaluator_registry import EVALUATOR_FACTORIES


class ArchitectureBoundaryTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[2]

    def test_core_layers_do_not_import_optional_ui_web_or_excel(self):
        forbidden = ("tkinter", "openpyxl", "http.server", "BaseHTTPRequestHandler")
        for directory in (self.ROOT / "src" / "equipeffi" / "domain", self.ROOT / "src" / "equipeffi" / "application"):
            for path in directory.rglob("*.py"):
                source = path.read_text(encoding="utf-8")
                for token in forbidden:
                    with self.subTest(path=path.relative_to(self.ROOT), token=token):
                        self.assertNotIn(token, source)

    def test_public_device_names_match_v4_sheet_order(self):
        self.assertEqual(tuple(PUBLIC_DEVICE_NAMES[code] for code in PUBLIC_DEVICE_TYPES), V4_DEVICE_SHEETS)

    def test_registry_contains_exact_internal_profiles(self):
        self.assertEqual(len(EVALUATOR_FACTORIES), 17)
        self.assertEqual(set(EVALUATOR_FACTORIES), {
            "transformer", "motor_lv", "motor_hv", "motor_pmsm", "compressor",
            "pump_water", "pump_chemical", "fan", "blower", "submersible",
            "boiler", "heat_treatment", "heat_pump_chiller",
            "heat_pump_water_heater", "duct_ac", "unitary_ac", "multi_split_ac",
        })

    def test_presentation_does_not_construct_json_standard_repository(self):
        """标准仓库只由应用装配层构造，避免GUI形成第二套装配路径。"""
        presentation = self.ROOT / "src" / "equipeffi" / "presentation"
        for path in presentation.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(self.ROOT)):
                self.assertNotIn("infrastructure.standards.json_repository", source)
                self.assertNotIn("JsonStandardRepository(", source)

    def test_desktop_launcher_uses_shared_application_factory(self):
        launcher = self.ROOT / "src" / "equipeffi" / "presentation" / "desktop" / "launcher.py"
        source = launcher.read_text(encoding="utf-8")
        self.assertIn("from ...application.bootstrap import create_application_api", source)
        self.assertIn("create_application_api(", source)
        self.assertNotIn("V4WorkbookReaderImpl", source)
        self.assertNotIn("EvaluationService(", source)

    def test_application_and_presentation_use_profile_query_not_mapping_constant(self):
        for directory in (
            self.ROOT / "src" / "equipeffi" / "application",
            self.ROOT / "src" / "equipeffi" / "presentation",
        ):
            for path in directory.rglob("*.py"):
                source = path.read_text(encoding="utf-8")
                with self.subTest(path=path.relative_to(self.ROOT)):
                    self.assertNotIn("PUBLIC_INTERNAL_PROFILES", source)

    def test_profile_query_preserves_the_single_routing_mapping(self):
        for public_type, expected in PUBLIC_INTERNAL_PROFILES.items():
            with self.subTest(public_type=public_type):
                self.assertEqual(profiles_for_public_type(public_type), expected)
        self.assertEqual(profiles_for_public_type("变压器"), ("transformer",))
        self.assertEqual(profiles_for_public_type("unknown"), ())

    def test_runtime_version_is_exposed_through_package_settings(self):
        from equipeffi import __version__
        from equipeffi.config.settings import Settings

        self.assertEqual(Settings().app_version, __version__)

    def test_root_entrypoint_only_forwards_to_package_entrypoint(self):
        """根入口不能形成第二套服务装配或参数解析路径。"""
        source = (self.ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("from equipeffi.entrypoint import main as package_main", source)
        self.assertNotIn("EvaluationService(", source)
        self.assertNotIn("JsonStandardRepository(", source)
        self.assertNotIn("EVALUATOR_FACTORIES", source)
        self.assertNotIn("V4WorkbookReaderImpl", source)


if __name__ == "__main__":
    unittest.main()
