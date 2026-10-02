from io import StringIO
import logging
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from equipeffi.config.logging import LoggingConfig
from equipeffi.infrastructure.runtime_logging import close_logging, configure_logging, install_exception_hook


class LoggingTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.stream = StringIO()
        self.logs = Path(self.temp.name) / "logs"
        self.logger = configure_logging(LoggingConfig(self.logs, "WARNING", 250, 2), stream=self.stream)
        self.addCleanup(close_logging, self.logger)

    def test_console_file_level_and_rotation(self):
        self.logger.info("hidden")
        self.logger.warning("visible")
        self.assertNotIn("hidden", self.stream.getvalue())
        self.assertIn("visible", self.stream.getvalue())
        self.assertIn("visible", (self.logs / "equipeffi.log").read_text(encoding="utf-8"))
        for _ in range(20):
            self.logger.warning("rotation " * 10)
        self.assertTrue((self.logs / "equipeffi.log.1").exists())
        self.assertLessEqual(len(list(self.logs.iterdir())), 3)

    def test_unhandled_exception_hook_records_traceback(self):
        previous = install_exception_hook(self.logger)
        self.addCleanup(setattr, sys, "excepthook", previous)
        try:
            raise RuntimeError("test traceback")
        except RuntimeError:
            sys.excepthook(*sys.exc_info())
        text = (self.logs / "equipeffi.log").read_text(encoding="utf-8")
        self.assertIn("Traceback", text)
        self.assertIn("RuntimeError: test traceback", text)

    def test_reinitialisation_closes_old_handlers(self):
        old = self.logger.handlers[-1]
        configure_logging(LoggingConfig(self.logs), stream=self.stream)
        self.assertIsNone(old.stream)
        self.assertEqual(len(self.logger.handlers), 2)
