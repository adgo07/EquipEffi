import json
import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.activate_gb30253_pack import activate


ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "src" / "equipeffi" / "resources" / "standards" / "gb30253_2024_pdf_verified_v1.json"


def _write_normalized_copy(destination: Path) -> None:
    """Create a pre-activation fixture even after the canonical pack is active."""
    payload = json.loads(PACK.read_text(encoding="utf-8"))
    payload["status"] = "normalized"
    payload["unavailable_reason"] = "测试夹具：等待人工复核"
    payload.pop("activation_review", None)
    destination.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _coverage():
    pack = json.loads(PACK.read_text(encoding="utf-8"))
    paths = {
        f"tables[{ti}].rows[{ri}].efficiency.{level}[{index}]"
        for ti, table in enumerate(pack["tables"])
        for ri, row in enumerate(table["rows"])
        for level, values in row["efficiency"].items()
        for index in range(len(values))
    }
    return {
        "all_cells_reviewed": True,
        "reviewed_tables": list(range(1, 30)),
        "reviewed_efficiency_cell_count": len(paths),
        "reviewed_paths_sha256": hashlib.sha256("\n".join(sorted(paths)).encode("utf-8")).hexdigest(),
        "pack_id": pack["pack_id"],
        "source_sha256": pack["source_sha256"],
    }


class PmsmActivationTests(unittest.TestCase):
    def test_active_provenance_uses_package_relative_source_refs(self):
        """激活元数据不能把当前开发机路径带进跨平台发布包。"""
        manifest = json.loads((ROOT / "src" / "equipeffi" / "standard_manifest.json").read_text(encoding="utf-8"))
        entry = next(item for item in manifest["packs"] if item["device_type"] == "motor_pmsm")
        pack = json.loads(PACK.read_text(encoding="utf-8"))
        source = entry["source"]
        self.assertEqual(entry.get("activation_source"), source)
        self.assertEqual(pack["activation_review"].get("source_pack"), source)
        for value in (entry.get("activation_source", ""), pack["activation_review"].get("source_pack", "")):
            self.assertNotRegex(str(value), r"^(?:[A-Za-z]:[\\/]|/)")
            self.assertNotIn(".codex", str(value))

    def test_activation_requires_explicit_pdf_confirmation_and_never_overwrites_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "normalized.json"
            _write_normalized_copy(source)
            review = root / "review.json"
            review.write_text(json.dumps({"reviewer": "张三", "review_date": "2026-08-27", **_coverage(), "items": [{
                "table_no": 1, "power_kw": 55, "level": 2, "dimension": 12,
                "replacement": 94.9, "pdf_page": 7, "pdf_checked": False,
            }]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "pdf_checked"):
                activate(source, review, root / "active.json")
            review_data = json.loads(review.read_text(encoding="utf-8"))
            review_data["items"][0]["pdf_checked"] = True
            review.write_text(json.dumps(review_data), encoding="utf-8")
            output = root / "active.json"
            result = activate(source, review, output)
            self.assertEqual(result["status"], "active")
            self.assertEqual(result["verified_table_count"], 29)
            self.assertIsNone(result["activation_review"]["items"][0]["previous_value"])
            self.assertEqual(json.loads(source.read_text(encoding="utf-8"))["status"], "normalized")

    def test_activation_accepts_confirmed_no_data_cell(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "normalized.json"
            _write_normalized_copy(source)
            review = root / "review.json"
            review.write_text(json.dumps({"reviewer": "张三", "review_date": "2026-08-27", **_coverage(), "items": [{
                "table_no": 1, "power_kw": 55, "level": 2, "dimension": 12,
                "replacement": None, "no_data": True, "pdf_page": 7, "pdf_checked": True,
                "comment": "已逐格对照PDF，原文无数据",
            }]}), encoding="utf-8")
            result = activate(source, review, root / "active.json")
            row = next(row for row in result["tables"][0]["rows"] if row.get("power_kw") == 55.0)
            self.assertIsNone(row["efficiency"]["2"][5])
            self.assertIn(12, row["no_data_cells"])
            item = result["activation_review"]["items"][0]
            self.assertTrue(item["no_data"])
            self.assertIsNone(item["replacement"])

    def test_activation_rejects_partial_review_without_coverage_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "normalized.json"
            _write_normalized_copy(source)
            review = root / "review.json"
            review.write_text(json.dumps({
                "reviewer": "张三", "review_date": "2026-08-27", "items": [],
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "all_cells_reviewed"):
                activate(source, review, root / "active.json")


if __name__ == "__main__":
    unittest.main()
