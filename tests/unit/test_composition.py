import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import call, patch

import equipeffi.composition as composition
from equipeffi.composition import create_core_api, load_v4_contract
from equipeffi.infrastructure.excel.ooxml_reader import OOXMLReadError


class CompositionTests(unittest.TestCase):
    @staticmethod
    def _write_standard_manifest(root: Path) -> Path:
        manifest = root / "src" / "equipeffi" / "standard_manifest.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"packs": []}), encoding="utf-8")
        return manifest

    def test_core_factory_never_loads_template(self):
        with patch("equipeffi.composition.load_v4_contract", side_effect=AssertionError):
            self.assertEqual(len(create_core_api().device_types()), 15)

    def test_analysis_factories_prefer_the_package_manifest_and_create_fresh_repositories(self):
        package_manifest = Path(composition.__file__).resolve().parent / "standard_manifest.json"
        self.assertTrue(package_manifest.is_file())
        with tempfile.TemporaryDirectory() as temp:
            project_root = Path(temp)
            self._write_standard_manifest(project_root)
            original_factory = composition._create_standard_repository
            repositories = []

            def record_repository(project_root=None):
                repository = original_factory(project_root)
                repositories.append(repository)
                return repository

            with patch.object(
                composition, "_create_standard_repository", side_effect=record_repository
            ) as factory, patch.object(
                composition, "load_v4_contract", side_effect=AssertionError
            ):
                core_api = composition.create_core_api(project_root=project_root)
                application_api, contract, resource_manager = composition.create_application_api(
                    project_root=project_root, load_template=False)
                pump_service = composition.create_pump_analysis_service(with_persistence=False)

            self.assertEqual(factory.call_args_list, [call(project_root), call(project_root), call()])
            self.assertEqual(len({id(repository) for repository in repositories}), 3)
            self.assertTrue(all(repository.root == package_manifest.parent.resolve()
                                for repository in repositories))
            self.assertTrue(all(repository.manifest_path == package_manifest.resolve()
                                for repository in repositories))
            self.assertIsNot(core_api, application_api)
            self.assertIsNone(contract)
            self.assertIsNone(resource_manager)
            self.assertIsNotNone(pump_service)

    def test_analysis_factories_fall_back_to_custom_root_when_package_manifest_is_missing(self):
        package_manifest = Path(composition.__file__).resolve().parent / "standard_manifest.json"
        real_is_file = Path.is_file
        with tempfile.TemporaryDirectory() as temp:
            project_root = Path(temp)
            fallback_manifest = self._write_standard_manifest(project_root)
            repositories = []
            original_factory = composition._create_standard_repository

            def is_file(path):
                if path.resolve() == package_manifest.resolve():
                    return False
                return real_is_file(path)

            def record_repository(root=None):
                repository = original_factory(root)
                repositories.append(repository)
                return repository

            with patch.object(Path, "is_file", new=is_file), patch.object(
                composition, "_default_project_root", return_value=project_root
            ), patch.object(
                composition, "_create_standard_repository", side_effect=record_repository
            ) as factory, patch.object(
                composition, "load_v4_contract", side_effect=AssertionError
            ):
                core_api = composition.create_core_api(project_root=project_root)
                application_api, contract, resource_manager = composition.create_application_api(
                    project_root=project_root, load_template=False)
                pump_service = composition.create_pump_analysis_service(with_persistence=False)

            self.assertEqual(factory.call_args_list, [call(project_root), call(project_root), call()])
            self.assertEqual(len({id(repository) for repository in repositories}), 3)
            self.assertTrue(all(repository.root == project_root.resolve()
                                for repository in repositories))
            self.assertTrue(all(repository.manifest_path == fallback_manifest.resolve()
                                for repository in repositories))
            self.assertIsNot(core_api, application_api)
            self.assertIsNone(contract)
            self.assertIsNone(resource_manager)
            self.assertIsNotNone(pump_service)

    def test_expected_template_damage_warns_and_falls_back(self):
        with patch("equipeffi.infrastructure.excel.v4_reader.V4WorkbookReaderImpl.read_contract",
                   side_effect=OOXMLReadError("damaged")):
            with self.assertLogs("equipeffi.composition", level="WARNING") as logs:
                self.assertEqual(load_v4_contract(), (None, None))
            self.assertIn("damaged", logs.output[0])

    def test_unknown_template_error_propagates(self):
        with patch("equipeffi.infrastructure.excel.v4_reader.V4WorkbookReaderImpl.read_contract",
                   side_effect=RuntimeError("unexpected bug")):
            with self.assertRaisesRegex(RuntimeError, "unexpected bug"):
                load_v4_contract()
