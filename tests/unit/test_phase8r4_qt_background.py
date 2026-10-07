"""Phase 8 R4 — Qt 批量评价后台执行（诊断 D05 回归）。

诊断事实：`presentation/qt/pages/batch.py` 的按钮处理直接调用整批
`evaluate_workbook()`，没有后台任务或事件循环让出；指定 head 的 CI 实测 10,000 行
耗时约 559 秒，因此在同等负载下主线程可能约 9 分钟无法处理界面事件。

本模块验证修复后的行为：整批评价在**工作线程**执行，主线程保持可响应，
界面有进行中状态与按钮守卫；**计算、统计与数据库语义完全不变**。
"""
from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import openpyxl

from equipeffi.infrastructure.excel.pump_workbook_reader import PUMP_SHEET
from equipeffi.infrastructure.excel.template_resource import V6TemplateResource

AS_OF = date(2026, 8, 23)


class QtBatchBackgroundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from equipeffi.composition import create_batch_evaluation_service
        from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
        from equipeffi.infrastructure.persistence.records_migrations import (
            migrate_records_database,
        )
        from equipeffi.presentation.qt.pages.batch import BatchPage

        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.tmp.name)
        self.paths = AppDataPaths(self.root / "app")
        migrate_records_database(self.paths.records_db, app_version="test")
        self.batch = create_batch_evaluation_service(paths=self.paths)
        self.page = BatchPage(self.batch)
        self.addCleanup(self.page.deleteLater)
        self.addCleanup(self.tmp.cleanup)
        self.source = self.make_input(rows=3)

    def make_input(self, *, rows: int) -> Path:
        path = self.root / "输入.xlsx"
        V6TemplateResource().download_to(path)
        workbook = openpyxl.load_workbook(path)
        sheet = workbook[PUMP_SHEET]
        for offset in range(rows):
            row = 4 + offset
            for column, value in dict(
                    B=f"泵{offset}", C=f"M-{offset}", D=1, E="1号车间",
                    F="单级单吸清水离心泵", G=100, H=50, I=2900, J=45,
                    K="单吸", L=1, M=78).items():
                sheet[f"{column}{row}"] = value
        workbook.save(path)
        workbook.close()
        return path

    def _pump_events(self, seconds: float) -> int:
        """在给定时间内让事件循环转起来，返回处理的定时器回调次数。"""

        ticks = {"count": 0}

        def tick():
            ticks["count"] += 1

        timer = QTimer()
        timer.timeout.connect(tick)
        timer.start(10)
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.005)
        timer.stop()
        return ticks["count"]

    def test_batch_run_does_not_block_the_event_loop(self):
        """整批评价期间，主线程必须能继续处理事件（D05 核心断言）。"""

        self.page.set_source(self.source)
        destination = self.root / "out.xlsx"
        self.page.target_edit.setText(str(destination))

        thread = self.page.start_run()
        self.assertIsNotNone(thread, "必须启动后台线程")
        self.assertTrue(self.page.busy, "进行中必须置 busy")
        self.assertFalse(self.page.run_button.isEnabled(),
                         "进行中必须禁用按钮，避免重复提交")

        ticks = self._pump_events(1.0)
        self.assertGreater(ticks, 10,
                           f"主线程被阻塞：1 秒内只处理了 {ticks} 次事件")

        self.assertTrue(self.page.wait_for_run(120000), "后台任务必须结束")
        self.app.processEvents()
        self.assertFalse(self.page.busy, "结束后必须解除 busy")
        self.assertTrue(self.page.run_button.isEnabled())
        self.assertIsNotNone(self.page.last_result)
        self.assertTrue(destination.exists(), "结果工作簿必须写出")

    def test_background_run_produces_the_same_result_as_the_synchronous_kernel(self):
        """后台路径与同步内核必须产出同一批统计（计算语义不变）。"""

        self.page.set_source(self.source)
        synchronous = self.page.run()
        self.assertIsNotNone(synchronous)

        second = self.root / "out2.xlsx"
        self.page.target_edit.setText(str(second))
        self.page.start_run()
        self.assertTrue(self.page.wait_for_run(120000))
        self.app.processEvents()
        asynchronous = self.page.last_result

        self.assertEqual(asynchronous.summary.data_row_count,
                         synchronous.summary.data_row_count)
        self.assertEqual(asynchronous.summary.total_quantity,
                         synchronous.summary.total_quantity)
        self.assertEqual(asynchronous.summary.evaluated_quantity,
                         synchronous.summary.evaluated_quantity)
        self.assertEqual(asynchronous.summary.conclusion_quantities,
                         synchronous.summary.conclusion_quantities)

    def test_failure_in_the_worker_is_reported_and_clears_busy(self):
        """工作线程内异常必须被提示并解除守卫，不得静默挂住界面。"""

        self.page.set_source(self.source)
        self.page.target_edit.setText(str(self.root / "out3.xlsx"))

        def boom(*_args, **_kwargs):
            raise RuntimeError("模拟批量失败")

        original = self.batch.evaluate_workbook
        self.batch.evaluate_workbook = boom
        try:
            self.page.start_run()
            self.assertTrue(self.page.wait_for_run(120000))
            self.app.processEvents()
        finally:
            self.batch.evaluate_workbook = original

        self.assertFalse(self.page.busy)
        self.assertTrue(self.page.run_button.isEnabled())
        self.assertIsNone(self.page.last_result)
        # 失败提示由 `_show_error` 写入 summary_label
        self.assertIn("未能完成", self.page.summary_label.text())
        self.assertIn("RuntimeError", self.page.summary_label.text())

    def test_no_background_thread_is_left_running(self):
        self.page.set_source(self.source)
        self.page.target_edit.setText(str(self.root / "out4.xlsx"))
        self.page.start_run()
        self.assertTrue(self.page.wait_for_run(120000))
        self.app.processEvents()
        self.assertIsNone(self.page._thread, "线程引用必须释放")

    def test_main_window_close_is_deferred_until_worker_thread_finishes(self):
        """正式 MainWindow 关闭链不得销毁仍在运行的 QThread。"""

        from equipeffi.application.services.settings_service import SettingsService
        from equipeffi.presentation.qt.shell import MainWindow

        class MemorySettingsRepository:
            def __init__(self):
                self.values = {}

            def get(self, key):
                return self.values.get(key)

            def set(self, key, value):
                self.values[key] = value

        settings = SettingsService(MemorySettingsRepository())
        window = MainWindow(settings, analysis=None, batch=self.batch)
        window.show()
        page = window.batch_page
        page.set_source(self.source)
        page.target_edit.setText(str(self.root / "close_during_run.xlsx"))

        started = threading.Event()
        release = threading.Event()
        original = self.batch.evaluate_workbook

        def slow_evaluate(*args, **kwargs):
            started.set()
            if not release.wait(10):
                raise RuntimeError("test worker release timeout")
            return original(*args, **kwargs)

        self.batch.evaluate_workbook = slow_evaluate
        try:
            page.start_run()
            self.assertTrue(started.wait(2), "后台任务必须真实进入 worker")
            self.assertTrue(page.has_active_run())

            # 模拟用户点击主窗口 X。旧实现会接受 close，随后父子对象销毁，
            # 最终触发 QThread: Destroyed while thread is still running。
            window.close()
            self.app.processEvents()
            self.assertTrue(window._close_pending,
                            "运行中关闭必须进入 deferred-close 状态")
            self.assertTrue(page.has_active_run(),
                            "关闭请求不得销毁仍运行的线程")
            self.assertTrue(window.isVisible(),
                            "任务未结束前 closeEvent 必须被 ignore")
            self.assertIn("任务结束后软件将自动退出", page.check_label.text())

            release.set()
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline and (
                    page.has_active_run() or window.isVisible()):
                self.app.processEvents()
                time.sleep(0.01)

            self.assertFalse(page.has_active_run(),
                             "任务结束后后台线程必须真正退出")
            self.assertIsNone(page._thread)
            self.assertFalse(window.isVisible(),
                             "线程退出后应自动完成用户原先的关闭请求")
        finally:
            release.set()
            self.batch.evaluate_workbook = original
            if page.has_active_run():
                page.wait_for_run(120000)
            window.close()
            self.app.processEvents()

    def test_missing_source_is_still_a_clear_error(self):
        self.page.source_edit.setText("")
        self.assertIsNone(self.page.start_run())
        self.assertFalse(self.page.busy)


if __name__ == "__main__":
    unittest.main()
