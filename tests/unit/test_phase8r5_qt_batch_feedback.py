"""批量评价页面完成状态、重跑与快捷打开失败反馈回归。"""
from __future__ import annotations

import os
from contextlib import contextmanager
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

import openpyxl

from equipeffi.composition import create_batch_evaluation_service
from equipeffi.infrastructure.excel.pump_workbook_reader import PUMP_SHEET
from equipeffi.infrastructure.excel.template_resource import V6TemplateResource
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.infrastructure.persistence.records_migrations import (
    migrate_records_database,
)
from equipeffi.infrastructure.persistence.sqlite_batch_record_repository import (
    SqliteBatchRecordRepository,
)
from equipeffi.presentation.qt.pages.batch import BatchPage


class QtBatchFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths = AppDataPaths(self.root / "app")
        migrate_records_database(self.paths.records_db, app_version="test")
        self.batch = create_batch_evaluation_service(paths=self.paths)
        self.page = BatchPage(self.batch)
        self.addCleanup(self.page.deleteLater)
        self.source = self._make_input()

    def _make_input(self) -> Path:
        path = self.root / "输入.xlsx"
        V6TemplateResource().download_to(path)
        workbook = openpyxl.load_workbook(path)
        sheet = workbook[PUMP_SHEET]
        for column, value in dict(
            B="泵-A", C="M-A", D=1, E="1号车间",
            F="单级单吸清水离心泵", G=100, H=50, I=2900,
            J=45, K="单吸", L=1, M=78,
        ).items():
            sheet[f"{column}4"] = value
        workbook.save(path)
        workbook.close()
        return path

    def _finish_run(self) -> None:
        self.assertTrue(self.page.wait_for_run(120000), "后台批量任务应结束")
        self.app.processEvents()

    def test_async_completion_replaces_progress_and_persists_batch_record(self):
        destination = self.root / "异步结果.xlsx"
        self.page.set_source(self.source)
        self.page.target_edit.setText(str(destination))

        self.page.start_run()
        self.assertTrue(self.page.busy)
        self._finish_run()

        result = self.page.last_result
        self.assertIsNotNone(result)
        self.assertTrue(destination.exists())
        self.assertFalse(self.page.busy)
        self.assertTrue(self.page.run_button.isEnabled())
        self.assertTrue(self.page.open_result_button.isEnabled())
        self.assertTrue(self.page.open_folder_button.isEnabled())
        self.assertIn("批量评价已完成", self.page.check_label.text())
        self.assertNotIn("正在批量评价", self.page.check_label.text())
        self.assertTrue(result.batch_record_saved)

        records = SqliteBatchRecordRepository(self.paths.records_db).list_batch_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].batch_record_id, result.batch_record_id)

    def test_rerun_disables_previous_result_actions_until_new_output_is_ready(self):
        self.page.set_source(self.source)
        first = self.root / "第一次.xlsx"
        self.page.target_edit.setText(str(first))
        self.assertIsNotNone(self.page.run())
        self.assertTrue(self.page.open_result_button.isEnabled())
        self.assertTrue(self.page.open_folder_button.isEnabled())

        destination = self.root / "第二次.xlsx"
        self.page.target_edit.setText(str(destination))
        entered = threading.Event()
        release = threading.Event()
        original = self.batch.evaluate_workbook

        def blocked(*args, **kwargs):
            entered.set()
            if not release.wait(10):
                raise RuntimeError("test worker release timeout")
            return original(*args, **kwargs)

        with patch.object(self.batch, "evaluate_workbook", side_effect=blocked):
            try:
                self.page.start_run()
                self.assertTrue(entered.wait(2), "worker 应开始执行")
                self.assertTrue(self.page.busy)
                self.assertIsNone(self.page.last_result)
                self.assertFalse(self.page.open_result_button.isEnabled())
                self.assertFalse(self.page.open_folder_button.isEnabled())
            finally:
                release.set()
            self._finish_run()

        self.assertTrue(destination.exists())
        self.assertTrue(self.page.open_result_button.isEnabled())
        self.assertTrue(self.page.open_folder_button.isEnabled())
        self.assertIn("批量评价已完成", self.page.check_label.text())

    def test_async_failure_clears_progress_and_keeps_result_actions_disabled(self):
        self.page.set_source(self.source)
        self.page.target_edit.setText(str(self.root / "旧结果.xlsx"))
        self.assertIsNotNone(self.page.run())
        self.assertTrue(self.page.open_result_button.isEnabled())

        def boom(*_args, **_kwargs):
            raise RuntimeError("模拟批量失败")

        self.page.target_edit.setText(str(self.root / "失败结果.xlsx"))
        with patch.object(self.batch, "evaluate_workbook", side_effect=boom):
            self.page.start_run()
            self._finish_run()

        self.assertFalse(self.page.busy)
        self.assertTrue(self.page.run_button.isEnabled())
        self.assertIsNone(self.page.last_result)
        self.assertFalse(self.page.open_result_button.isEnabled())
        self.assertFalse(self.page.open_folder_button.isEnabled())
        self.assertIn("批量评价失败", self.page.check_label.text())
        self.assertNotIn("正在批量评价", self.page.check_label.text())
        self.assertIn("RuntimeError", self.page.summary_label.text())

    def test_open_uses_injected_launch_context_and_restores_after_failure(self):
        active = []

        @contextmanager
        def launch_context():
            active.append(True)
            try:
                yield
            finally:
                active.pop()

        page = BatchPage(self.batch, external_launch_context=launch_context)
        self.addCleanup(page.deleteLater)

        def open_path(path):
            self.assertEqual(active, [True])
            raise OSError("external launcher failed")

        with patch("equipeffi.presentation.qt.pages.batch._open_path", side_effect=open_path):
            self.assertFalse(page._try_open_path(self.source))
        self.assertEqual(active, [])

    def test_open_failures_explain_manual_recovery_paths(self):
        self.page.set_source(self.source)
        self.page.target_edit.setText(str(self.root / "打开失败.xlsx"))
        self.assertIsNotNone(self.page.run())
        result = self.page.result_path()
        self.assertIsNotNone(result)
        self.assertEqual(self.page.check_label.textFormat(), Qt.TextFormat.PlainText)
        self.assertTrue(
            self.page.check_label.textInteractionFlags()
            & Qt.TextInteractionFlag.TextSelectableByMouse
        )

        with patch(
            "equipeffi.presentation.qt.pages.batch._open_path",
            return_value=False,
        ) as open_path:
            self.assertFalse(self.page.open_result())
            self.assertIn("文件关联或访问权限", self.page.check_label.text())
            self.assertIn(str(result), self.page.check_label.text())

            self.assertFalse(self.page.open_result_folder())
            self.assertIn("文件资源管理器地址栏", self.page.check_label.text())
            self.assertIn(str(result.parent), self.page.check_label.text())

        self.assertEqual(open_path.call_count, 2)
        self.assertEqual(open_path.call_args_list[0].args[0], result)
        self.assertEqual(open_path.call_args_list[1].args[0], result.parent)


if __name__ == "__main__":
    unittest.main()
