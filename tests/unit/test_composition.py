import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import equipeffi.composition as composition
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository


class CompositionTests(unittest.TestCase):
    @staticmethod
    def _write_standard_manifest(root: Path) -> Path:
        manifest = root / "src" / "equipeffi" / "standard_manifest.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"packs": []}), encoding="utf-8")
        return manifest

    def test_pump_factory_uses_packaged_standard_manifest(self):
        package_manifest = Path(composition.__file__).resolve().parent / "standard_manifest.json"
        self.assertTrue(package_manifest.is_file())
        service = composition.create_pump_analysis_service(with_persistence=False)
        self.assertIsInstance(service._standards, JsonStandardRepository)
        self.assertEqual(service._standards.root, package_manifest.parent.resolve())
        self.assertEqual(service._standards.manifest_path, package_manifest.resolve())

    def test_pump_factory_falls_back_to_project_root_without_packaged_manifest(self):
        package_manifest = Path(composition.__file__).resolve().parent / "standard_manifest.json"
        real_is_file = Path.is_file
        with tempfile.TemporaryDirectory() as temp:
            project_root = Path(temp)
            fallback_manifest = self._write_standard_manifest(project_root)

            def is_file(path):
                if path.resolve() == package_manifest.resolve():
                    return False
                return real_is_file(path)

            with patch.object(Path, "is_file", new=is_file), patch.object(
                composition, "_default_project_root", return_value=project_root
            ):
                service = composition.create_pump_analysis_service(with_persistence=False)

            self.assertEqual(service._standards.root, project_root.resolve())
            self.assertEqual(service._standards.manifest_path, fallback_manifest.resolve())

    def test_formal_factory_can_create_a_non_persistent_pump_service(self):
        service = composition.create_pump_analysis_service(with_persistence=False)
        self.assertEqual(
            {item["rule_profile"] for item in service.standard_overview()["scopes"]},
            {"pump_water", "pump_chemical"},
        )


if __name__ == "__main__":
    unittest.main()
