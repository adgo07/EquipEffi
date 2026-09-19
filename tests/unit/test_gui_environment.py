from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.check_gui_environment import diagnose, main


class GuiEnvironmentTests(unittest.TestCase):
    def test_diagnose_is_json_serializable_and_non_destructive(self):
        payload = diagnose()
        self.assertIn("ready", payload)
        self.assertIn("candidate_tcl_paths", payload)
        json.dumps(payload, ensure_ascii=False)

    def test_report_output_is_optional_and_require_ready_has_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "gui.json"
            with patch("tools.check_gui_environment.diagnose", return_value={"ready": True}):
                self.assertEqual(main(("--output", str(target), "--require-ready")), 0)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["ready"], True)

        with patch("tools.check_gui_environment.diagnose", return_value={"ready": False}):
            self.assertEqual(main(("--require-ready",)), 2)


if __name__ == "__main__":
    unittest.main()
