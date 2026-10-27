from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from equipeffi.entrypoint import main


class EntrypointTests(unittest.TestCase):
    def test_no_arguments_launch_qt(self):
        with patch("equipeffi.composition.launch_qt", return_value=0) as launch:
            self.assertEqual(main([]), 0)
        launch.assert_called_once_with()

    def test_gui_and_qt_are_aliases_for_the_same_shell(self):
        with patch("equipeffi.composition.launch_qt", return_value=0) as launch:
            self.assertEqual(main(["--gui"]), 0)
            self.assertEqual(main(["--qt"]), 0)
        self.assertEqual(launch.call_count, 2)

    def test_none_argv_uses_console_arguments(self):
        output = StringIO()
        with patch("sys.argv", ["equipeffi", "--status"]), \
                patch("equipeffi.entrypoint._runtime_status", return_value={"ready": True}) as status, \
                redirect_stdout(output):
            self.assertEqual(main(), 0)
        status.assert_called_once_with()
        self.assertTrue(json.loads(output.getvalue())["ready"])

    def test_status_reports_real_formal_capabilities_without_a_window(self):
        output = StringIO()
        with redirect_stdout(output):
            result = main(["--status"])
        status = json.loads(output.getvalue())
        self.assertEqual(result, 0 if status["ready"] else 1)
        self.assertEqual(status["desktop"]["surface"], "PySide6 Qt")
        self.assertIn("available", status["desktop"])
        self.assertTrue(status["template"]["template_id"])
        self.assertTrue(status["template"]["template_version"])
        self.assertTrue(status["template"]["available"], status["template"]["issues"])
        self.assertEqual(status["template"]["template_version"], "V6.2")
        self.assertTrue(status["transformer"]["available"])
        self.assertEqual(status["transformer"]["support_status"], "SUPPORTED")
        self.assertTrue(status["motor"]["enabled"])
        self.assertTrue(status["motor"]["available"])
        self.assertEqual(status["motor"]["support_status"], "SUPPORTED")
        for name in ("pump_water", "pump_chemical"):
            with self.subTest(profile=name):
                profile = status["pump_profiles"][name]
                self.assertTrue(profile["available"])
                self.assertEqual(profile["support_status"], "SUPPORTED")
                self.assertTrue(profile["pack_id"])

    def test_status_file_works_without_stdout(self):
        payload = {"ready": True, "desktop": {"surface": "PySide6 Qt"}}
        with tempfile.TemporaryDirectory() as tmp:
            status_file = Path(tmp) / "nested" / "status.json"
            with patch("equipeffi.entrypoint._runtime_status", return_value=payload), \
                    patch("sys.stdout", None):
                self.assertEqual(
                    main(["--status", "--status-file", str(status_file)]), 0
                )
            self.assertEqual(
                json.loads(status_file.read_text(encoding="utf-8")), payload
            )

    def test_status_file_requires_status_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                main(["--status-file", str(Path(tmp) / "status.json")])

    def test_qt_and_status_cannot_be_combined(self):
        for argv in (["--qt", "--status"], ["--gui", "--status"]):
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                main(argv)

    def test_legacy_compatibility_switches_are_rejected(self):
        for option in (
            "--json", "--list-device-types", "--jsonl", "--web",
            "--schema", "--v4-sheet", "--batch-json", "--audit-template",
        ):
            with self.subTest(option=option), self.assertRaises(SystemExit):
                main([option])

    def test_help_only_exposes_formal_desktop_and_diagnostic_options(self):
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as result:
            main(["--help"])
        self.assertEqual(result.exception.code, 0)
        help_text = output.getvalue()
        for option in ("--qt", "--gui", "--status"):
            self.assertIn(option, help_text)
        for option in ("--json", "--jsonl", "--web", "--v4-sheet"):
            self.assertNotIn(option, help_text)


if __name__ == "__main__":
    unittest.main()
