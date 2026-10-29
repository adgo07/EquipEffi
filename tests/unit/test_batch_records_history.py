"""分析记录页对 batch_record 的只读接入与完整可访问性。"""
from __future__ import annotations

import os
from datetime import datetime
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QTextDocument

from equipeffi.application.lifecycle import (
    AnalysisError,
    BatchRecordSnapshot,
    RecordPage,
)
from equipeffi.application.services.pump_batch_evaluation_service import (
    PumpBatchEvaluationService,
)
from equipeffi.presentation.qt.pages.records import RecordsPage
from equipeffi.presentation.qt import shell as shell_module
from equipeffi.presentation.qt.shell import MainWindow


def _snapshot(index: int) -> BatchRecordSnapshot:
    return BatchRecordSnapshot(
        batch_record_id=f"BATCH-{index:03d}",
        standard_code="GB 19762-2025",
        device_type="离心泵",
        sheet_name="离心泵",
        evaluation_date="2026-10-21",
        source_workbook=f"input-{index:03d}.xlsx",
        source_workbook_sha256="source-hash",
        source_file_name="<img src=x>.xlsx" if index == 0 else f"输入-{index:03d}.xlsx",
        result_workbook=f"output-{index:03d}.xlsx",
        result_workbook_sha256="result-hash",
        output_file_name=f"结果-{index:03d}.xlsx",
        template_id="equipeffi.device-efficiency.V6",
        template_version="V6-20261005",
        template_sha256="template-hash",
        total_rows=1,
        evaluated_count=1,
        unevaluated_count=0,
        invalid_count=0,
        data_row_count=1,
        total_quantity=2,
        evaluated_quantity=2,
        summary={
            "concluded_rows": 1,
            "unevaluated_rows": 0,
            "input_error_rows": 0,
            "execution_error_rows": 0,
            "conclusion_quantities": {"1级": 2},
        },
        app_version="test",
        canonical_version="2026.09.26",
        numeric_profile_id="test-profile",
        schema_version=4,
        created_at_utc=(
            f"2026-10-21T00:{index // 60:02d}:{index % 60:02d}+00:00"),
    )


class _BarePage(QWidget):
    def __init__(self, *_args, **_kwargs):
        super().__init__()


class _SettingsPageStub(_BarePage):
    """设置页在新版Shell中提供标题/动作行，批次导航测试只替换其内容。"""
    def __init__(self, *_args, **_kwargs):
        super().__init__()
        layout = QVBoxLayout(self)
        self.header_row = QHBoxLayout()
        layout.addLayout(self.header_row)


class _SettingsStub:
    def get(self, _key):
        return ""


class _AnalysisServiceStub:
    def record_categories(self):
        return ()

    def search_records(self, query):
        return RecordPage((), 0, query.offset, query.limit)

    def evaluate(self, *_args, **_kwargs):
        raise AssertionError("打开历史批次不得重新评价")


class _BatchServiceStub:
    def __init__(self, records):
        self.records = sorted(
            records, key=lambda record: record.created_at_utc, reverse=True)
        self.requested_limits = []
        self.opened = []

    def list_batch_records(self, limit=50):
        self.requested_limits.append(limit)
        return self.records[:limit]

    def open_batch_record(self, batch_record_id):
        self.opened.append(batch_record_id)
        return next(record for record in self.records
                    if record.batch_record_id == batch_record_id)


class _BatchRepositoryStub:
    def __init__(self, record):
        self.record = record
        self.list_limits = []
        self.loaded = []

    def list_batch_records(self, limit=50):
        self.list_limits.append(limit)
        return [self.record][:limit]

    def load_batch_record(self, batch_record_id):
        self.loaded.append(batch_record_id)
        return self.record if batch_record_id == self.record.batch_record_id else None


class BatchRecordServiceReadTests(unittest.TestCase):
    def test_batch_service_exposes_read_only_list_and_open(self):
        record = _snapshot(1)
        repository = _BatchRepositoryStub(record)
        service = PumpBatchEvaluationService(
            _AnalysisServiceStub(), reader=None, writer=None,
            batch_repository=repository)

        self.assertEqual(service.list_batch_records(limit=7), [record])
        self.assertEqual(repository.list_limits, [7])
        self.assertIs(service.open_batch_record(record.batch_record_id), record)
        self.assertEqual(repository.loaded, [record.batch_record_id])

    def test_missing_batch_repository_is_explicit(self):
        service = PumpBatchEvaluationService(
            _AnalysisServiceStub(), reader=None, writer=None)

        self.assertEqual(service.list_batch_records(), [])
        with self.assertRaises(AnalysisError):
            service.open_batch_record("missing")


class BatchRecordHistoryShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_shell_injects_batch_history_and_refreshes_on_navigation(self):
        batch = _BatchServiceStub([_snapshot(1)])
        launch_context = object()
        patches = (
            "HomePage", "StandardsPage", "AnalysisPage")
        with patch.multiple(
                shell_module, SettingsPage=_SettingsPageStub,
                **{name: _BarePage for name in patches}):
            window = MainWindow(
                _SettingsStub(), _AnalysisServiceStub(), batch=batch,
                external_launch_context=launch_context)
        self.addCleanup(window.deleteLater)

        page = window.records_page
        self.assertIsNotNone(page.batch_list)
        self.assertIs(window.batch_page._external_launch_context, launch_context)
        # 页面构建先加载一次；导航到历史页会再读一次并展示批次。
        window.open_records()
        self.assertEqual(page.batch_list.rowCount(), 1)
        self.assertIn("输入-001.xlsx", page.batch_list.item(0, 0).text())
        page.show_batch_record("BATCH-001")
        self.assertIn("输入-001.xlsx", page.batch_detail.text())
        self.assertEqual(batch.requested_limits, [51, 51])

        # 同页再次打开也刷新，批次历史始终可从导航到达。
        window.open_records()
        self.assertEqual(batch.requested_limits, [51, 51, 51])


class BatchRecordHistoryPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_batch_tab_loads_older_records_and_keeps_plain_text_detail(self):
        batch = _BatchServiceStub([_snapshot(index) for index in range(61)])
        page = RecordsPage(_AnalysisServiceStub(), batch=batch)
        self.addCleanup(page.deleteLater)

        self.assertEqual(
            [page.single_button.text(), page.batch_button.text()],
            ["单台分析", "批量评价"])
        self.assertEqual(page.batch_list.rowCount(), 50)
        self.assertIn("输入-060.xlsx", page.batch_list.item(0, 0).text())
        expected_time = datetime.fromisoformat("2026-10-21T00:01:00+00:00").astimezone().strftime("%Y-%m-%d %H:%M:%S") + "（本地时间）"
        self.assertEqual(expected_time, page.batch_list.item(0, 5).text())
        self.assertEqual(batch.opened, [], "列表只查询，不自动打开详情")
        self.assertTrue(page.batch_load_more_button.isEnabled())
        self.assertEqual(batch.requested_limits, [51])

        page.search.setText("no matching record")
        self.assertEqual(page.filtered_records(), [])
        self.assertEqual(page.batch_list.rowCount(), 50)

        page.batch_load_more_button.click()
        self.assertEqual(page.batch_list.rowCount(), 61)
        self.assertFalse(page.batch_load_more_button.isEnabled())
        self.assertEqual(batch.requested_limits, [51, 101])
        self.assertEqual(batch.opened, [], "加载更多不自动打开详情")

        page.batch_list.setCurrentCell(60, 0)
        page.batch_list.cellActivated.emit(60, 0)
        detail = page.batch_detail.text()
        self.assertEqual(batch.opened[-1], "BATCH-000")
        self.assertIn("数据行数：1", detail)
        self.assertIn("设备数量总计：2 台", detail)
        self.assertIn("完成正式评价数量：2 台", detail)
        self.assertIn("正式结论分布：1级 2 台", detail)
        self.assertEqual(page.batch_detail.textFormat().name, "RichText")
        self.assertIn("<img src=x>.xlsx", detail)
        # ReadableDetail formats paragraphs, but the source filename must still
        # display literally. Parse the actual QLabel HTML, not its plain API.
        document = QTextDocument()
        document.setHtml(QLabel.text(page.batch_detail))
        self.assertIn("<img src=x>.xlsx", document.toPlainText())
        block = document.begin()
        while block.isValid():
            fragment = block.begin()
            while not fragment.atEnd():
                self.assertFalse(fragment.fragment().charFormat().isImageFormat(),
                                 "历史文件名不得被解释为HTML图片")
                fragment += 1
            block = block.next()

    def test_refresh_reloads_batch_records_without_changing_single_record_query(self):
        batch = _BatchServiceStub([_snapshot(index) for index in range(2)])
        analysis = _AnalysisServiceStub()
        page = RecordsPage(analysis, batch=batch)
        self.addCleanup(page.deleteLater)

        page.batch_list.setCurrentCell(1, 0)
        page.batch_list.cellActivated.emit(1, 0)
        batch.records.insert(0, _snapshot(99))
        page.refresh()

        self.assertEqual(page.batch_list.rowCount(), 3)
        self.assertIn("GB 19762-2025", page.batch_detail.text())
        self.assertEqual(batch.requested_limits[-1], 51)


if __name__ == "__main__":
    unittest.main()
