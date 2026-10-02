"""真实 Qt 生命周期与跨进程设置恢复证据；所有路径必须显式注入。"""
import argparse
import json
from pathlib import Path
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from equipeffi.composition import create_settings_runtime
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.infrastructure.runtime_logging import close_logging
from equipeffi.presentation.qt.app import install_qt_message_handler
from equipeffi.presentation.qt.navigation import PAGES
from equipeffi.presentation.qt.shell import MainWindow
from PySide6.QtCore import qInstallMessageHandler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--mode", choices=("write", "restore"), required=True)
    args = parser.parse_args()
    assert sys.version_info[:2] == (3, 12), sys.version
    settings, logger = create_settings_runtime(paths=AppDataPaths(args.data_root))
    application = QApplication([])
    previous = install_qt_message_handler(logger)
    try:
        window = MainWindow(settings)
        for index in range(len(PAGES)):
            window.navigation.setCurrentRow(index)
            assert window.pages.currentIndex() == index
        if args.mode == "write":
            window.resize(640, 480)
            settings.set("last.directory", "中文测试目录")
            settings.set("log.level", "WARNING")
        else:
            assert window.size().width() == 640, window.size()
            assert window.size().height() == 480, window.size()
            assert settings.get("last.directory") == "中文测试目录"
            assert settings.get("log.level") == "WARNING"
            assert settings.get("window.state")
            assert window.restoreState(window.saveState())
        window.show()
        QTimer.singleShot(0, window.close)
        code = application.exec()
        assert code == 0
        assert settings.get("window.geometry")
        assert settings.get("window.state")
        print(json.dumps({"mode": args.mode, "width": window.width(), "height": window.height(),
                          "exit": code, "python": sys.version, "executable": sys.executable}, ensure_ascii=False))
        return code
    finally:
        qInstallMessageHandler(previous)
        close_logging(logger)


if __name__ == "__main__":
    raise SystemExit(main())
