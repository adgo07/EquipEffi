"""Shared capture lifecycle: isolated paths, bounded Qt waits and failure evidence."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import threading
import traceback

from PySide6.QtCore import QObject, QEvent, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from equipeffi.infrastructure.runtime_logging import close_logging


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-ms", type=int, default=180000)
    args = parser.parse_args()
    # Validate BOTH paths before mkdir/settings/database or any other writes.
    data, output = args.data_root.resolve(), args.output.resolve()
    if data == output or data in output.parents or output in data.parents:
        parser.error("数据与截图目录必须独立，不得相同或互相嵌套")
    for path in (data, output):
        if path.exists() and (not path.is_dir() or any(path.iterdir())):
            parser.error(f"必须使用全新或空目录：{path}")
        for ancestor in path.parents:
            if ancestor.exists() and not ancestor.is_dir():
                parser.error(f"父路径不是目录：{ancestor}")
    if args.timeout_ms <= 0:
        parser.error("timeout-ms必须为正整数")
    args.data_root, args.output = data, output
    return args


class CaptureSession(QObject):
    def __init__(self, args, filename):
        super().__init__()
        self.args, self.filename = args, filename
        self.app = self.window = self.logger = None
        self.closing = False
        self.deadline = time.monotonic() + args.timeout_ms / 1000
        self.evidence = {"data_root": str(args.data_root), "captures": [], "failures": [],
                         "status": "running", "scale_factor_override": os.environ.get("QT_SCALE_FACTOR")}

    def eventFilter(self, watched, event):
        if watched is self.window and event.type() == QEvent.Type.Close and not self.closing:
            self.evidence["failures"].append("窗口在任务完成前关闭")
        return False

    def attach(self, window):
        self.window = window
        window.installEventFilter(self)

    def check(self):
        require(time.monotonic() < self.deadline, "截图任务总超时")
        require(not self.evidence["failures"], "; ".join(self.evidence["failures"]))

    def settle(self, milliseconds=30):
        self.check()
        QTest.qWait(milliseconds)
        self.check()

    def save(self, filename):
        self.check()
        saved = self.window.grab().save(str(self.args.output / filename))
        require(saved, f"截图保存失败：{filename}")
        return saved

    def write_evidence(self):
        try:
            (self.args.output / self.filename).write_text(
                json.dumps(self.evidence, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except BaseException as error:
            print(f"失败证据JSON无法写入 {self.args.output / self.filename}: {error}", file=sys.stderr)
            return False

    def emergency_timeout(self):
        # Last resort for a blocked startup/native call: no Qt calls from this thread.
        self.evidence["status"] = "failed"
        self.evidence["failures"].append("截图任务总超时（进程守卫）")
        self.write_evidence()
        print("截图任务总超时，终止捕获进程", file=sys.stderr, flush=True)
        os._exit(124)

    def run(self, action):
        code = 1
        watchdog = threading.Timer(self.args.timeout_ms / 1000 + 2, self.emergency_timeout)
        watchdog.daemon = True
        watchdog.start()
        try:
            self.args.output.mkdir(parents=True, exist_ok=True)
            self.app = QApplication([])
            self.app.setQuitOnLastWindowClosed(False)
            self.evidence.update({"platform": self.app.platformName(), "python": sys.version,
                "native_windows": self.app.platformName() == "windows",
                "screens": [{"name": s.name(), "logical_dpi": s.logicalDotsPerInch(),
                             "device_pixel_ratio": s.devicePixelRatio()} for s in self.app.screens()]})
            self.timer = QTimer(self)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(lambda: self.evidence["failures"].append("截图任务总超时"))
            self.timer.start(self.args.timeout_ms)
            self.check()
            action(self)
            self.check()
            self.evidence["status"] = "completed"
            code = 0
        except BaseException as error:
            traceback.print_exc()
            self.evidence["failures"].append(f"{type(error).__name__}: {error}")
            self.evidence["status"] = "failed"
        finally:
            self.closing = True
            try:
                if self.window is not None:
                    self.window.close()
                if self.app is not None:
                    self.app.processEvents()
                if self.logger is not None:
                    close_logging(self.logger)
            except BaseException as error:
                self.evidence["failures"].append(f"收尾失败：{error}")
                code = 1
            if self.evidence["failures"]:
                self.evidence["status"] = "failed"
                code = 1
            if not self.write_evidence():
                code = 1
            if self.app is not None:
                self.app.quit()
            watchdog.cancel()
        return code
