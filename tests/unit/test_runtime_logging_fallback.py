"""文件日志不可用时仍应保留控制台日志。"""
from __future__ import annotations

from io import StringIO
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from equipeffi.config.logging import LoggingConfig
from equipeffi.infrastructure.runtime_logging import close_logging, configure_logging


class RuntimeLoggingFallbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stream = StringIO()

    def test_directory_creation_failure_keeps_console_and_warns(self):
        logs = self.root / "uncreatable-logs"
        with patch.object(Path, "mkdir", side_effect=PermissionError("directory denied")):
            logger = configure_logging(
                LoggingConfig(logs, "ERROR"), stream=self.stream
            )
        self.addCleanup(close_logging, logger)

        logger.error("console still works")
        output = self.stream.getvalue()
        self.assertIn("WARNING", output)
        self.assertIn("无法创建日志目录", output)
        self.assertIn(str(logs), output)
        self.assertIn("将仅写入控制台日志", output)
        self.assertIn("console still works", output)
        self.assertEqual(len(logger.handlers), 1)
        self.assertFalse(logs.exists())

    def test_file_handler_permission_failure_keeps_console_and_warns(self):
        logs = self.root / "logs"
        with patch(
            "equipeffi.infrastructure.runtime_logging.RotatingFileHandler",
            side_effect=PermissionError("file denied"),
        ):
            logger = configure_logging(
                LoggingConfig(logs, "ERROR"), stream=self.stream
            )
        self.addCleanup(close_logging, logger)

        logger.error("console after file failure")
        output = self.stream.getvalue()
        self.assertIn("WARNING", output)
        self.assertIn("无法打开日志文件", output)
        self.assertIn(str(logs / "equipeffi.log"), output)
        self.assertIn("将仅写入控制台日志", output)
        self.assertIn("console after file failure", output)
        self.assertEqual(len(logger.handlers), 1)
        self.assertIsInstance(logger.handlers[0], logging.StreamHandler)


if __name__ == "__main__":
    unittest.main()
