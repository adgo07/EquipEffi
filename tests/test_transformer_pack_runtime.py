"""安装资源可独立读取，损坏必须暴露为系统错误。"""
import json
import tempfile
import unittest
from pathlib import Path

from equipeffi.infrastructure.standards.transformer_repository import load_transformer_pack


class TransformerPackRuntimeTests(unittest.TestCase):
    def test_packaged_resource_contains_all_tables(self):
        pack, digest = load_transformer_pack()
        self.assertEqual(len(digest), 64)
        self.assertEqual(len(pack["tables"]), 35)
        self.assertEqual(sum(len(table["rows"]) for table in pack["tables"]), 589)

    def test_altered_threshold_is_rejected_before_calculation(self):
        pack, _ = load_transformer_pack()
        pack["tables"][0]["rows"][0]["thresholds_w"]["grade_1"]["no_load_loss"] = "999"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "damaged.json"
            path.write_text(json.dumps(pack), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "完整性"):
                load_transformer_pack(path)


if __name__ == "__main__":
    unittest.main()
