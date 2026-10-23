from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile

from tools.check_distribution_assets import audit_artifact, runtime_asset_members, runtime_asset_paths
from tools.build_zipapp import build_zipapp


ROOT = Path(__file__).resolve().parents[2]


class DistributionAssetAuditTests(unittest.TestCase):
    def _wheel(self, path: Path, extra: dict[str, bytes] | None = None) -> Path:
        members = {name: b"declared runtime asset" for name in runtime_asset_members(ROOT)}
        members["equipeffi/__init__.py"] = b""
        members.update(extra or {})
        with zipfile.ZipFile(path, "w") as archive:
            for name, content in members.items():
                archive.writestr(name, content)
        return path

    def _sdist(self, path: Path, extra: dict[str, bytes] | None = None) -> Path:
        with tarfile.open(path, "w:gz") as archive:
            members = {
                f"equipeffi-0.2.1/src/{name}": b"declared runtime asset"
                for name in runtime_asset_members(ROOT)
            }
            members.update(extra or {})
            for name, content in members.items():
                info = tarfile.TarInfo(name)
                info.size = len(content)
                archive.addfile(info, BytesIO(content))
        return path

    def test_declared_assets_keep_canonical_pump_metadata_and_formal_v6_template(self):
        names = {path.relative_to(ROOT / "src" / "equipeffi").as_posix() for path in runtime_asset_paths(ROOT)}
        self.assertIn("standard_manifest.json", names)
        self.assertIn("resources/TEMPLATE_MANIFEST.json", names)
        self.assertIn("resources/standards/pump.json", names)
        self.assertIn("resources/templates/设备能效分析空白模板_重构版V6_20261005.xlsx", names)
        self.assertNotIn("resources/templates/设备能效分析空白模板_重构版V4_20260825.xlsx", names)

    def test_sdist_excludes_source_directories_without_globally_banning_pdf_reports(self):
        manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
        self.assertIn("prune 标准原文", manifest)
        self.assertIn("prune docs/standards", manifest)
        self.assertNotIn("global-exclude *.pdf", manifest)
        self.assertIn("include src/equipeffi/resources/TEMPLATE_MANIFEST.json", manifest)
        self.assertIn("include src/equipeffi/resources/templates/设备能效分析空白模板_重构版V6_20261005.xlsx", manifest)

    def test_runtime_report_pdf_is_not_an_installation_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            wheel = self._wheel(
                Path(tmp) / "equipeffi.whl",
                {"reports/evaluation-result.pdf": b"%PDF-1.7\nEquipEffi evaluation result\n%%EOF"},
            )
            result = audit_artifact(wheel, root=ROOT)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.checks["allowed_report_pdfs"], [])
        self.assertTrue(any("reports/evaluation-result.pdf" in item
                            for item in result.checks["standard_source_findings"]))

    def test_same_pdf_is_rejected_when_path_looks_like_report(self):
        pdf = b"%PDF-1.7\nEquipEffi evaluation result\n%%EOF"
        findings = {}
        with tempfile.TemporaryDirectory() as tmp:
            for relative in ("docs/GB19762-2025.pdf", "reports/evaluation-result.pdf"):
                wheel = self._wheel(Path(tmp) / (relative.split("/")[-1] + ".whl"), {relative: pdf})
                result = audit_artifact(wheel, root=ROOT)
                findings[relative] = result
        for relative, result in findings.items():
            with self.subTest(path=relative):
                self.assertFalse(result.is_valid)
                self.assertTrue(any(relative in item
                                    for item in result.checks["standard_source_findings"]))

    def test_source_pdf_is_detected_when_renamed_as_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            wheel = self._wheel(
                Path(tmp) / "equipeffi.whl",
                {"assets/GB19762_2025_scan.png": b"%PDF-1.7\nscanned standard\n%%EOF"},
            )
            result = audit_artifact(wheel, root=ROOT)
        self.assertFalse(result.is_valid)
        self.assertTrue(result.checks["standard_source_findings"])

    def test_high_resolution_scan_page_is_detected_by_image_signature(self):
        png = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + (2480).to_bytes(4, "big") + (3508).to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"
        with tempfile.TemporaryDirectory() as tmp:
            wheel = self._wheel(Path(tmp) / "equipeffi.whl", {"assets/page-01.dat": png})
            result = audit_artifact(wheel, root=ROOT)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("高分辨率" in item for item in result.checks["standard_source_findings"]))

    def test_complete_standard_text_copy_is_detected(self):
        text = (
            "GB 19762—2025\n中华人民共和国国家标准\n"
            "1 范围\n本标准规定离心泵能效要求。\n"
            "2 规范性引用文件\n本标准适用时引用相关文件。\n"
            "3 术语和定义\n"
            + ("本标准的技术要求与评价方法应按本文件执行。\n" * 80)
        ).encode("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            sdist = self._sdist(
                Path(tmp) / "equipeffi-0.2.1.tar.gz",
                {"equipeffi-0.2.1/docs/backup.txt": text},
            )
            result = audit_artifact(sdist, root=ROOT)
        self.assertFalse(result.is_valid)
        self.assertTrue(result.checks["standard_source_findings"])

    def test_unlisted_resource_is_rejected_even_if_it_uses_json_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            wheel = self._wheel(
                Path(tmp) / "equipeffi.whl",
                {"equipeffi/resources/standards/unlisted_source.json": b'{"full_text": "not a declared resource"}'},
            )
            result = audit_artifact(wheel, root=ROOT)
        self.assertFalse(result.is_valid)
        self.assertTrue(result.checks["unexpected_runtime_resources"])

    def test_nested_portable_package_is_recursively_inspected(self):
        with tempfile.TemporaryDirectory() as tmp:
            inner = self._wheel(
                Path(tmp) / "equipeffi-0.2.1-py3-none-any.whl",
                {"originals/GB19762-2025.pdf": b"%PDF-1.7\nsource\n%%EOF"},
            )
            outer = Path(tmp) / "portable.zip"
            with zipfile.ZipFile(outer, "w") as archive:
                archive.write(inner, inner.name)
            result = audit_artifact(outer, root=ROOT)
        self.assertFalse(result.is_valid)
        self.assertTrue(result.checks["standard_source_findings"])

    def test_zipapp_builder_excludes_unlisted_development_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_bytes((ROOT / "pyproject.toml").read_bytes())
            package = root / "src" / "equipeffi"
            (package / "resources" / "standards").mkdir(parents=True)
            (package / "resources" / "templates").mkdir(parents=True)
            (package / "resources" / "knowledge").mkdir(parents=True)
            (package / "entrypoint.py").write_text("def main(): return 0\n", encoding="utf-8")
            (package / "standard_manifest.json").write_text('{"packs": []}', encoding="utf-8")
            (package / "resources" / "standards" / "pump.json").write_text("{}", encoding="utf-8")
            (package / "resources" / "standards" / "gb20052_2024_v21.json").write_text("{}", encoding="utf-8")
            (package / "resources" / "TEMPLATE_MANIFEST.json").write_text("{}", encoding="utf-8")
            (package / "resources" / "standards" / "developer-notes.md").write_text("source notes", encoding="utf-8")
            (package / "resources" / "standards" / "scan.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (package / "resources" / "templates" / "设备能效分析空白模板_重构版V6_20261005.xlsx").write_bytes(b"v6")
            (package / "resources" / "templates" / "设备能效分析空白模板_重构版V6_1.xlsx").write_bytes(b"v61")
            (package / "resources" / "knowledge" / "README.md").write_text("draft", encoding="utf-8")
            output = build_zipapp(root, root / "dist" / "test.pyz")
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
        self.assertIn("equipeffi/resources/standards/pump.json", names)
        self.assertIn("equipeffi/resources/standards/gb20052_2024_v21.json", names)
        self.assertIn("equipeffi/resources/templates/设备能效分析空白模板_重构版V6_1.xlsx", names)
        self.assertIn("equipeffi/resources/templates/设备能效分析空白模板_重构版V6_20261005.xlsx", names)
        self.assertNotIn("equipeffi/resources/templates/设备能效分析空白模板_重构版V4_20260825.xlsx", names)
        self.assertNotIn("equipeffi/resources/standards/developer-notes.md", names)
        self.assertNotIn("equipeffi/resources/standards/scan.png", names)
        self.assertNotIn("equipeffi/resources/knowledge/README.md", names)


if __name__ == "__main__":
    unittest.main()
