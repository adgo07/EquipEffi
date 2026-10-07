import base64
from io import StringIO
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import qInstallMessageHandler, qWarning
from PySide6.QtWidgets import QApplication, QLabel

from equipeffi.composition import create_settings_runtime
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.infrastructure.runtime_logging import close_logging
from equipeffi.presentation.qt.app import install_qt_message_handler
from equipeffi.presentation.qt.navigation import PAGES
from equipeffi.presentation.qt.shell import MainWindow

ROOT = Path(__file__).resolve().parents[2]


def _analysis_service():
    """真实分析服务；首页/标准库/新建分析需要它才构建。"""

    from equipeffi.application.services.centrifugal_pump_analysis_service import (
        CentrifugalPumpAnalysisService,
    )
    from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository

    return CentrifugalPumpAnalysisService(
        JsonStandardRepository(ROOT / "src" / "equipeffi"))


class QtShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = TemporaryDirectory(prefix="phase2-qt-中文-")
        self.addCleanup(self.temp.cleanup)
        self.paths = AppDataPaths(Path(self.temp.name))
        self.service, self.logger = create_settings_runtime(paths=self.paths, stream=StringIO())
        self.addCleanup(close_logging, self.logger)

    def test_all_navigation_pages_are_real_pages(self):
        """所有一级页面都必须是真实页面，不得有 placeholder（Phase 8 起含批量评价）。"""

        analysis = _analysis_service()
        # Phase 8：「批量评价」是真实一级页面，必须一并注入批量服务，
        # 否则该页会退化为空控件而让「所有页面都真实」的断言失真。
        from equipeffi.composition import create_batch_evaluation_service

        batch = create_batch_evaluation_service(paths=self.paths)
        window = MainWindow(self.service, analysis, batch=batch,
                            data_location=self.paths.root)
        self.addCleanup(window.close)
        self.assertEqual(window.pages.count(), len(PAGES))
        for index, name in enumerate(PAGES):
            with self.subTest(page=name):
                window.navigation.setCurrentRow(index)
                self.assertEqual(window.pages.currentIndex(), index)
                widget = window.pages.currentWidget()
                labels = [label.text() for label in widget.findChildren(QLabel)]
                self.assertIn(name, labels)
                # 不得残留开发态占位文案
                blob = "\n".join(labels)
                self.assertNotIn("尚未在 Phase", blob)
                self.assertNotIn("功能预留", blob)
                self.assertNotIn("后续开发", blob)

    def test_shell_exposes_the_minimal_navigation_contract(self):
        analysis = _analysis_service()
        window = MainWindow(self.service, analysis, data_location=self.paths.root)
        self.addCleanup(window.close)
        for method in ("open_home", "open_standards", "open_analysis",
                       "open_records", "open_settings"):
            with self.subTest(method=method):
                self.assertTrue(callable(getattr(window, method)))
        window.open_records()
        self.assertEqual(window.pages.currentIndex(), PAGES.index("分析记录"))
        window.open_standards()
        self.assertEqual(window.pages.currentIndex(), PAGES.index("标准库"))

    def test_geometry_and_state_restore_on_new_window(self):
        first = MainWindow(self.service)
        first.resize(640, 480)
        first.show()
        self.app.processEvents()
        first.close()
        expected = self.service.get("window.state")
        second = MainWindow(self.service)
        self.addCleanup(second.close)
        self.assertEqual((second.width(), second.height()), (640, 480))
        self.assertEqual(base64.b64encode(bytes(second.saveState())).decode("ascii"), expected)

    def test_invalid_window_state_warns_and_falls_back(self):
        self.service.set("window.geometry", "invalid!")
        with self.assertLogs("equipeffi.qt", level="WARNING"):
            window = MainWindow(self.service)
        self.addCleanup(window.close)
        self.assertEqual(window.width(), 1000)

    def test_save_failure_is_logged_and_close_still_succeeds(self):
        """M2：窗口布局保存失败只记日志，**不再**阻止退出。

        这是普通偏好设置，不是正式数据；此前会因为它拒绝关闭窗口卡住用户。
        正式写入（结果 Workbook / Record / batch_record）进行中的安全退出逻辑
        由 `closeEvent` 的另一条分支保证，未放松。
        """

        window = MainWindow(self.service)
        window.show()
        with patch.object(self.service, "set", side_effect=OSError("disk full")):
            with self.assertLogs("equipeffi.qt", level="ERROR") as logs:
                self.assertTrue(window.close(),
                                "布局保存失败时仍必须能正常退出")
        self.assertIn("Traceback", logs.output[0])

    def test_qt_warning_reaches_file(self):
        previous = install_qt_message_handler(self.logger)
        try:
            qWarning("phase2 Qt diagnostic")
        finally:
            qInstallMessageHandler(previous)
        self.assertIn("phase2 Qt diagnostic", (self.paths.logs_dir / "equipeffi.log").read_text(encoding="utf-8"))

    def test_two_process_offscreen_write_and_restore_clean_exit(self):
        # 与单进程重建窗口不同，两个独立解释器检验真正的跨启动恢复。
        root = Path(__file__).resolve().parents[2]
        environment = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONPATH": str(root / "src"), "PYTHONIOENCODING": "utf-8"}
        for mode in ("write", "restore", "entry"):
            result = subprocess.run([sys.executable, str(root / "tools/qt_offscreen_smoke.py"),
                                     "--data-root", str(self.paths.root / "process"), "--mode", mode],
                                    cwd=root, env=environment, capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('"exit": 0', result.stdout)

    def test_qt_entrypoint_isolated_from_evaluation_factory(self):
        from equipeffi.entrypoint import main
        with patch("equipeffi.composition.launch_qt", return_value=0) as launch:
            with patch("equipeffi.entrypoint.create_application_api", side_effect=AssertionError):
                self.assertEqual(main(["--qt"]), 0)
        launch.assert_called_once()
        with self.assertRaises(SystemExit):
            main(["--qt", "--status"])
