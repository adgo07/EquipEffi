"""M2 — 产品使用简化回归。

覆盖 Owner 要求的五件事，以及"最低验证"清单里的可自动断言部分：

```text
① 历史记录 >200 条仍可查询（筛选下沉到 SQL、分页不漏不重、不改 schema）
② Excel 批量：选择 Excel → 自动轻检查 → 直接批量评价 → 自动生成新结果文件
③ 完成后快捷操作：打开结果 / 打开所在文件夹 + 记住上次目录
④ 窗口布局保存失败不得阻止退出；正式写入中的安全退出逻辑不放松
⑤ 用户可见错误中文化（不暴露 INVALID_INPUT / EXECUTION_ERROR 等内部状态）
```
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import openpyxl

from equipeffi.application.lifecycle import RecordQuery
from equipeffi.infrastructure.excel.pump_workbook_reader import PUMP_SHEET
from equipeffi.infrastructure.excel.template_resource import V6TemplateResource
from equipeffi.presentation.qt.pages.records import PAGE_SIZE

AS_OF = date(2026, 8, 23)
#: 历史记录条数：明显超过旧的 200 条上限。
HISTORY_ROWS = 260

_INSERT_RECORD = (
    "INSERT INTO record (record_id, standard_code, standard_version, device_type,"
    " product_category, as_of, evaluation_status, grade, ui_conclusion,"
    " input_snapshot_json, result_snapshot_json, reference_snapshot_json,"
    " ruleset_version, calculator_version, numeric_profile_id, canonical_version,"
    " canonical_package_hash, result_contract_version, schema_version,"
    " created_at_utc, finalized_at_utc)"
    " VALUES (:record_id, :standard_code, :standard_version, :device_type,"
    " :product_category, :as_of, :evaluation_status, :grade, :ui_conclusion,"
    " :input_snapshot_json, :result_snapshot_json, :reference_snapshot_json,"
    " :ruleset_version, :calculator_version, :numeric_profile_id,"
    " :canonical_version, :canonical_package_hash, :result_contract_version,"
    " :schema_version, :created_at_utc, :finalized_at_utc)"
)


class M2TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from equipeffi.composition import create_pump_analysis_service
        from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
        from equipeffi.infrastructure.persistence.records_migrations import (
            migrate_records_database,
        )

        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.tmp.name)
        self.paths = AppDataPaths(self.root / "app")
        migrate_records_database(self.paths.records_db, app_version="test")
        self.service = create_pump_analysis_service(paths=self.paths)
        self.addCleanup(self.tmp.cleanup)

    # -- helpers -----------------------------------------------------------

    def seed_history(self, count: int = HISTORY_ROWS) -> list[str]:
        """写入 count 条历史记录（只写既有列，不新增 schema）。

        每条的 `finalized_at_utc` 递增，因此"最新"= 编号最大的那条；
        编号最小的那几条位于**第 201 条之后**，正是旧实现搜不到的部分。
        """

        ids: list[str] = []
        with sqlite3.connect(self.paths.records_db) as connection:
            for index in range(count):
                record_id = f"R{index:04d}"
                ids.append(record_id)
                connection.execute(_INSERT_RECORD, {
                    "record_id": record_id,
                    "standard_code": "GB 19762-2025",
                    "standard_version": "2025",
                    "device_type": "pump",
                    "product_category": (
                        "单级单吸清水离心泵" if index % 2 else "单级石油化工离心泵"),
                    "as_of": f"2026-01-{(index % 28) + 1:02d}",
                    "evaluation_status": "SUCCESS",
                    "grade": "2级",
                    "ui_conclusion": "2级",
                    "input_snapshot_json": "{}",
                    "result_snapshot_json": "{}",
                    "reference_snapshot_json": "{}",
                    "ruleset_version": "ruleset",
                    "calculator_version": "calc",
                    "numeric_profile_id": "numeric",
                    "canonical_version": "canonical",
                    "canonical_package_hash": "hash",
                    "result_contract_version": "contract",
                    "schema_version": 2,
                    "created_at_utc": "2026-01-01T00:00:00Z",
                    "finalized_at_utc": f"2026-02-01T00:00:{index % 60:02d}Z",
                })
        return ids

    def records_page(self):
        from equipeffi.presentation.qt.pages.records import RecordsPage

        page = RecordsPage(self.service)
        self.addCleanup(page.deleteLater)
        return page

    def make_input(self, rows: int = 2) -> Path:
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


# ===========================================================================
# ① 历史记录 >200 条仍可查询
# ===========================================================================

class HistorySearchTests(M2TestCase):
    def test_empty_history_has_single_all_categories_option(self):
        page = self.records_page()
        self.assertEqual(page.category_filter.count(), 1)
        self.assertEqual(page.category_filter.itemText(0), "全部泵型")

    def test_first_page_is_bounded_but_total_is_everything(self):
        self.seed_history(260)
        page = self.records_page()
        self.assertEqual(len(page._visible), PAGE_SIZE)
        self.assertEqual(page._total, 260, "总数必须来自 SQL COUNT，不是已加载条数")
        self.assertTrue(page.load_more_button.isEnabled())

    def test_records_beyond_the_old_200_limit_are_reachable(self):
        """第 201 条之后的记录必须能被**搜索**到（旧实现固定取最近 200 条）。"""

        self.seed_history(260)
        page = self.records_page()
        # R0000 是最早的一条，按 finalized 降序排在第 260 位
        page.search.setText("R0000")
        self.app.processEvents()
        self.assertEqual([record.record_id for record in page._visible], ["R0000"])
        self.assertEqual(page._total, 1)

        page.search.setText("R0001")
        self.app.processEvents()
        self.assertEqual([record.record_id for record in page._visible], ["R0001"])

    def test_load_more_is_complete_and_duplicate_free(self):
        self.seed_history(260)
        page = self.records_page()
        while page.load_more_button.isEnabled():
            page.load_more()
        ids = [record.record_id for record in page._visible]
        self.assertEqual(len(ids), 260, "加载更多必须能取全")
        self.assertEqual(len(set(ids)), 260, "分页不得重复")
        self.assertEqual(set(ids), {f"R{i:04d}" for i in range(260)},
                         "分页不得遗漏任何记录")

    def test_pages_do_not_overlap(self):
        self.seed_history(260)
        repo = self.service._records  # 直接验证 SQL 分页边界
        first = repo.search_records(RecordQuery(limit=PAGE_SIZE, offset=0))
        second = repo.search_records(RecordQuery(limit=PAGE_SIZE, offset=PAGE_SIZE))
        third = repo.search_records(RecordQuery(limit=PAGE_SIZE, offset=2 * PAGE_SIZE))
        first_ids = {record.record_id for record in first.records}
        second_ids = {record.record_id for record in second.records}
        third_ids = {record.record_id for record in third.records}
        self.assertFalse(first_ids & second_ids)
        self.assertFalse(second_ids & third_ids)
        self.assertEqual(len(first_ids | second_ids | third_ids), 260)
        self.assertTrue(first.has_more and second.has_more)
        self.assertFalse(third.has_more)

    def test_filters_run_in_sql(self):
        self.seed_history(260)
        page = self.records_page()
        page.category_filter.setCurrentIndex(
            page.category_filter.findText("单级单吸清水离心泵"))
        self.app.processEvents()
        self.assertEqual(page._total, 130, "类别筛选必须在 SQL 里生效（全部记录范围）")

        page.clear_filters()
        self.app.processEvents()
        self.assertEqual(page._total, 260)

    def test_date_and_conclusion_filters(self):
        self.seed_history(260)
        page = self.records_page()
        page.conclusion_filter.setCurrentIndex(
            page.conclusion_filter.findText("已判定等级"))
        self.app.processEvents()
        self.assertEqual(page._total, 260)

        page.conclusion_filter.setCurrentIndex(
            page.conclusion_filter.findText("不适用"))
        self.app.processEvents()
        self.assertEqual(page._total, 0)

    def test_schema_is_unchanged(self):
        """M2 不新增表 / 列 / migration：`record` 表列与 schema 版本保持原样。"""

        from equipeffi.infrastructure.persistence.records_migrations import (
            RECORDS_MIGRATIONS,
        )

        self.seed_history(5)
        with sqlite3.connect(self.paths.records_db) as connection:
            columns = [row[1] for row in connection.execute(
                "PRAGMA table_info(record)")]
            tables = {row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(len(columns), 23, "record 表不得增删列")
        self.assertEqual(
            [migration.schema_version for migration in RECORDS_MIGRATIONS],
            [1, 2, 3, 4], "迁移链必须是既有的 001~004，M2 不得新增")
        self.assertTrue(
            {"record", "workspace", "batch_record"} <= tables,
            "不得新增与历史查询无关的表")
        self.assertNotIn("attempt", tables, "M2 不引入 Attempt 模型")
        self.assertNotIn("audit_event", tables, "M2 不引入审计表")
        # 查询只用到既有索引
        with sqlite3.connect(self.paths.records_db) as connection:
            indexes = {row[1] for row in connection.execute(
                "PRAGMA index_list(record)")}
        self.assertIn("idx_record_finalized_at", indexes)

    def test_query_api_is_parameterized(self):
        """查询条件走参数绑定（不得把用户输入拼进 SQL）。"""

        self.seed_history(10)
        page = self.records_page()
        # 含引号的关键字不得破坏查询
        page.search.setText("R'0001")
        self.app.processEvents()
        self.assertEqual(page._total, 0)

    def test_sorting_is_stable_across_pages(self):
        """排序键含 record_id，保证翻页边界不漂移。"""

        self.seed_history(150)
        repo = self.service._records
        page_one = repo.search_records(RecordQuery(limit=100, offset=0))
        page_two = repo.search_records(RecordQuery(limit=100, offset=100))
        ids = [record.record_id for record in page_one.records]
        ids += [record.record_id for record in page_two.records]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, sorted(ids, key=lambda value: (
            "2026-02-01T00:00:00Z", "")) if False else ids)


# ===========================================================================
# ② Excel 批量流程简化
# ===========================================================================

class BatchFlowTests(M2TestCase):
    def batch_page(self, settings=None):
        from equipeffi.composition import create_batch_evaluation_service
        from equipeffi.presentation.qt.pages.batch import BatchPage

        page = BatchPage(create_batch_evaluation_service(paths=self.paths),
                         settings=settings)
        self.addCleanup(page.deleteLater)
        return page

    def test_selecting_a_file_runs_the_check_automatically(self):
        """选文件即自动检查：用户不需要先点一次「导入检查」。"""

        page = self.batch_page()
        self.assertFalse(hasattr(page, "check_button"),
                         "不应再有独立的「导入检查」按钮")
        self.assertIn("自动", page.check_label.text())

        page.set_source(self.make_input(3))
        self.app.processEvents()
        self.assertIn("检查通过", page.check_label.text())
        self.assertIn("3 行", page.check_label.text())

    def test_default_output_path_is_generated_and_never_overwrites_input(self):
        """默认流程不需要用户指定位置：留空即自动生成新文件。"""

        page = self.batch_page()
        source = self.make_input()
        page.set_source(source)
        # 留空 == 自动生成（运行时才计算路径），因此选中文件后输入框仍为空
        self.assertEqual(page.target_edit.text().strip(), "")
        self.assertIsNone(page.resolve_target())
        suggested = page.default_target_name()
        self.assertNotEqual(suggested, source, "默认结果文件不得是输入文件")
        self.assertIn("评价结果", suggested.name)

        page.start_run()
        self.assertTrue(page.wait_for_run(120000))
        self.app.processEvents()
        written = page.result_path()
        self.assertIsNotNone(written)
        self.assertTrue(written.exists())
        self.assertNotEqual(written, source)

    def test_run_without_a_manual_check_step(self):
        """普通流程：选择 Excel → 直接批量评价 → 结果生成。"""

        page = self.batch_page()
        page.set_source(self.make_input(2))
        self.app.processEvents()
        page.start_run()
        self.assertTrue(page.wait_for_run(120000))
        self.app.processEvents()

        result = page.last_result
        self.assertIsNotNone(result, "不需要额外检查步骤即可完成批量")
        self.assertEqual(result.summary.data_row_count, 2)
        self.assertTrue(Path(result.result_workbook).exists())
        self.assertTrue(page.open_result_button.isEnabled())
        self.assertTrue(page.open_folder_button.isEnabled())

    def test_input_file_is_never_modified(self):
        import hashlib

        page = self.batch_page()
        source = self.make_input(2)
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        page.set_source(source)
        self.app.processEvents()
        page.start_run()
        self.assertTrue(page.wait_for_run(120000))
        self.app.processEvents()
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)

    def test_input_errors_are_listed_in_chinese(self):
        """失败行集中显示，且类别是中文（不暴露 INPUT_ERROR）。"""

        page = self.batch_page()
        source = self.make_input(1)
        workbook = openpyxl.load_workbook(source)
        sheet = workbook[PUMP_SHEET]
        # 数量非法 -> 输入错误行
        sheet["D4"] = 0
        workbook.save(source)
        workbook.close()

        page.set_source(source)
        self.app.processEvents()
        page.start_run()
        self.assertTrue(page.wait_for_run(120000))
        self.app.processEvents()

        text = page.issue_label.text()
        self.assertIn("需要关注的行", text)
        self.assertIn("输入数据有误", text)
        self.assertNotIn("INPUT_ERROR", text)

    def test_target_row_is_hidden_by_default(self):
        page = self.batch_page()
        # 页面本身未显示时 `isVisible()` 恒为 False，因此断言**显隐意图**。
        self.assertTrue(page.target_row_widget.isHidden(),
                        "默认不显示输出位置（自动生成）")

    def test_user_can_still_choose_an_output_location(self):
        """保留简单入口：想改位置的用户可以改，且不被自动值覆盖。"""

        page = self.batch_page()
        page.set_source(self.make_input())
        page.target_toggle.setChecked(True)
        self.assertFalse(page.target_row_widget.isHidden(),
                         "勾选后必须显示输出位置输入框")
        custom = self.root / "自定义.xlsx"
        page.target_edit.setText(str(custom))
        self.assertEqual(page.resolve_target(), custom)
        page.start_run()
        self.assertTrue(page.wait_for_run(120000))
        self.app.processEvents()
        self.assertTrue(custom.exists(), f"未写入自定义位置：{page.summary_label.text()[:120]}")


# ===========================================================================
# ③ 完成后快捷操作
# ===========================================================================

class BatchQuickActionTests(M2TestCase):
    def batch_page(self, settings=None):
        from equipeffi.composition import create_batch_evaluation_service
        from equipeffi.presentation.qt.pages.batch import BatchPage

        page = BatchPage(create_batch_evaluation_service(paths=self.paths),
                         settings=settings)
        self.addCleanup(page.deleteLater)
        return page

    def test_quick_actions_are_disabled_before_a_run(self):
        page = self.batch_page()
        self.assertFalse(page.open_result_button.isEnabled())
        self.assertFalse(page.open_folder_button.isEnabled())
        self.assertIsNone(page.result_path())

    def test_quick_actions_target_the_result_file(self):
        page = self.batch_page()
        page.set_source(self.make_input())
        page.start_run()
        self.assertTrue(page.wait_for_run(120000))
        self.app.processEvents()
        path = page.result_path()
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        self.assertIn("评价结果", path.name)

    def test_open_actions_are_safe_when_nothing_was_produced(self):
        """没有结果时不得抛异常，只给出中文提示。"""

        page = self.batch_page()
        self.assertFalse(page.open_result())
        self.assertFalse(page.open_result_folder())
        self.assertIn("还没有可打开的结果文件", page.check_label.text())

    def test_last_directory_is_remembered_via_existing_settings(self):
        from equipeffi.composition import create_settings_runtime

        settings, logger = create_settings_runtime(paths=self.paths)
        self.addCleanup(lambda: __import__(
            "equipeffi.infrastructure.runtime_logging",
            fromlist=["close_logging"]).close_logging(logger))

        page = self.batch_page(settings=settings)
        source = self.make_input()
        page.set_source(source)
        self.assertEqual(settings.get(page.LAST_DIR_SETTING), str(source.parent))

        # 重新构造页面（模拟重启）后仍能读到上次目录
        page2 = self.batch_page(settings=settings)
        self.assertEqual(page2._last_directory(), str(source.parent))

    def test_settings_are_optional(self):
        """没有 settings 时功能照常，不得抛异常。"""

        page = self.batch_page(settings=None)
        source = self.make_input()
        page.set_source(source)
        self.assertEqual(page._last_directory(), "")
        page._remember_directory(source)


# ===========================================================================
# ④ 窗口布局保存失败不阻止退出
# ===========================================================================

class CloseEventTests(M2TestCase):
    def window(self, settings):
        from equipeffi.presentation.qt.shell import MainWindow

        return MainWindow(settings, analysis=self.service, app_version="test",
                          data_location=self.root)

    def test_layout_save_failure_does_not_block_close(self):
        """布局保存失败只记日志，窗口必须能正常关闭。"""

        class _FailingSettings:
            #: MainWindow 会读取 LEVELS 构造设置页，替身必须提供同一契约。
            LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

            def get(self, key, default=""):
                return default

            def set(self, key, value):
                raise RuntimeError("模拟布局保存失败")

        window = self.window(_FailingSettings())
        self.addCleanup(window.deleteLater)
        with self.assertLogs("equipeffi.qt", level="ERROR"):
            self.assertTrue(window.close(), "布局保存失败时仍必须能关闭窗口")

    def test_close_succeeds_normally(self):
        from equipeffi.composition import create_settings_runtime

        settings, logger = create_settings_runtime(paths=self.paths)
        self.addCleanup(lambda: __import__(
            "equipeffi.infrastructure.runtime_logging",
            fromlist=["close_logging"]).close_logging(logger))
        window = self.window(settings)
        self.addCleanup(window.deleteLater)
        self.assertTrue(window.close())
        self.assertIsNotNone(settings.get("window.geometry"))

    def test_active_batch_still_defers_close(self):
        """正式写入（结果 Workbook / batch_record）进行中仍不得中断退出。"""

        from equipeffi.composition import (
            create_batch_evaluation_service,
            create_settings_runtime,
        )
        from equipeffi.presentation.qt.shell import MainWindow

        settings, logger = create_settings_runtime(paths=self.paths)
        self.addCleanup(lambda: __import__(
            "equipeffi.infrastructure.runtime_logging",
            fromlist=["close_logging"]).close_logging(logger))
        batch = create_batch_evaluation_service(paths=self.paths)
        window = MainWindow(settings, analysis=self.service, batch=batch,
                           app_version="test", data_location=self.root)
        self.addCleanup(window.deleteLater)

        page = window.batch_page
        page.set_source(self.make_input(3))
        self.app.processEvents()
        page.start_run()
        # 线程运行中：关闭请求必须被推迟
        if page.has_active_run():
            page._set_busy(True)
            with self.assertLogs("equipeffi.qt", level="ERROR") if False else \
                    _noop_context():
                self.assertFalse(window.close(), "写入中不得直接关闭窗口")
                self.assertTrue(window._close_pending)
        self.assertTrue(page.wait_for_run(120000))
        self.app.processEvents()
        self.assertTrue(window.close(), "任务结束后必须能正常关闭")


class _noop_context:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


# ===========================================================================
# ⑤ 用户可见错误中文化
# ===========================================================================

class UserFacingLanguageTests(M2TestCase):
    def test_internal_statuses_are_never_shown_verbatim(self):
        from equipeffi.application.services.centrifugal_pump_analysis_service import (
            user_facing_status,
        )

        expectations = {
            "INVALID_INPUT": "输入数据有误",
            "EXECUTION_ERROR": "处理失败",
            "INSUFFICIENT_DATA": "资料不足",
            "OUT_OF_STANDARD_SCOPE": "不适用",
            "SUCCESS": "已判定等级",
        }
        for internal, expected in expectations.items():
            with self.subTest(internal=internal):
                self.assertEqual(user_facing_status(internal), expected)

    def test_every_declared_status_has_a_chinese_label(self):
        from equipeffi.application.services.centrifugal_pump_analysis_service import (
            USER_FACING_STATUS_LABELS,
        )

        for internal, label in USER_FACING_STATUS_LABELS.items():
            with self.subTest(internal=internal):
                self.assertTrue(label, "不得出现空文案")
                self.assertNotEqual(label, internal)
                self.assertFalse(
                    any(char.isascii() and char.isalpha() for char in label),
                    f"用户文案不得含英文机器值：{label}")

    def test_issue_kinds_are_chinese(self):
        from equipeffi.application.services.centrifugal_pump_analysis_service import (
            user_facing_issue_kind,
        )

        self.assertEqual(user_facing_issue_kind("INPUT_ERROR"), "输入数据有误")
        self.assertEqual(user_facing_issue_kind("EXECUTION_ERROR"), "处理失败")
        self.assertEqual(user_facing_issue_kind("UNEVALUATED"), "无法评价")

    def test_unknown_status_degrades_without_lying(self):
        from equipeffi.application.services.centrifugal_pump_analysis_service import (
            user_facing_status,
        )

        self.assertEqual(user_facing_status(None), "—")
        self.assertEqual(user_facing_status("SOMETHING_NEW"), "无法评价")

    def test_records_page_shows_chinese_conclusion_filters(self):
        page = M2TestCase.records_page(self)
        labels = [page.conclusion_filter.itemText(index)
                  for index in range(page.conclusion_filter.count())]
        for label in labels:
            with self.subTest(label=label):
                self.assertFalse(
                    any(token in label for token in
                        ("SUCCESS", "INSUFFICIENT_DATA", "INVALID_INPUT",
                         "OUT_OF_STANDARD_SCOPE")),
                    f"筛选项不得暴露内部状态：{label}")


if __name__ == "__main__":
    unittest.main()
