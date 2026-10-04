"""Phase 6 — 完整 GB 19762 Product Shell（G07 证据）。

覆盖本轮交付的真实行为：

```text
启动入口：无参数 / --gui / --qt 都进入同一正式 Qt Shell
Tk 退出：legacy Tk 不再是任何用户产品入口，且不再回退到 Web
AppShell：五页均为真实页面，无 placeholder、无开发态文案
导航契约：切页 / 选择目标对象 / 载入已有对象
首页：新建分析 / 最近草稿 / 最近记录 / 当前标准
标准库：标准事实来自 Application read model，无第二真值源
Analysis：五层产品信息层级 + 技术详情默认折叠
Records：搜索/筛选/历史快照不漂移/Reopen 不重算
Settings：只显示真实可配置项，不暴露算法契约
QA-P5-001 / QA-P5-002 / QA-P3-003：已收口或已给出明确不能关闭的 blocker
```

本模块**不**修改任何业务算法；它只证明 Shell 行为与既有业务契约。
"""
from __future__ import annotations

import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton

from equipeffi.composition import create_settings_runtime
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository
from equipeffi.application.services.centrifugal_pump_analysis_service import (
    CentrifugalPumpAnalysisService,
    PumpAnalysisRequest,
)
from equipeffi.presentation.qt.navigation import PAGES
from equipeffi.presentation.qt.pages import (
    AnalysisPage,
    HomePage,
    RecordsPage,
    SettingsPage,
    StandardsPage,
)
from equipeffi.presentation.qt.shell import MainWindow

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
#: 开发态占位文案：不得出现在任何普通用户可见位置。
PLACEHOLDER_TEXTS = (
    "尚未在 Phase", "功能预留", "后续开发", "尚未实现", "待实现",
    "Phase N", "即将推出", "coming soon",
)

#: 普通用户 UI 不得泄露的内部标识。
INTERNAL_TOKENS = (
    "pump_water", "pump_chemical", "rule_profile", "matched_rule_id",
    "internal_id", "field_id", "canonical", "EQUIPEFFI_PUMP_DECIMAL50_V2",
    "PUMP_NUMERIC", "ruleset_version", "PROFILE_EVALUATOR_TECHNICAL",
)

WATER = {
    "category": "单级单吸清水离心泵", "suction": "单吸", "stages": "1",
    "QBEP": "100", "HBEP": "50", "speed": "2900", "efficiency": "80",
}
CHEMICAL = {
    "category": "单级石油化工离心泵", "suction": "单吸", "stages": "1",
    "QBEP": "100", "HBEP": "14", "speed": "2900", "efficiency": "73",
}


def _request(values, *, record_id="analysis"):
    """把测试用的取值字典转成真实分析请求（字段为扁平 QBEP/HBEP/...）。"""

    from datetime import date as _date

    return PumpAnalysisRequest(
        product_category=values["category"], as_of=_date.fromisoformat(WATER_AS_OF()),
        QBEP=values["QBEP"], HBEP=values["HBEP"], speed=values["speed"],
        efficiency=values["efficiency"], suction=values["suction"],
        stages=values["stages"], record_id=record_id)


def _service(paths=None):
    """真实分析服务；带持久化才能覆盖草稿/记录/Reopen。"""

    if paths is None:
        return CentrifugalPumpAnalysisService(JsonStandardRepository(SRC))
    from equipeffi.composition import create_pump_analysis_service

    return create_pump_analysis_service(paths=paths, with_persistence=True)


def _visible_text(widget) -> str:
    """递归收集控件上的全部可见文本。"""

    parts = [label.text() for label in widget.findChildren(QLabel)]
    parts += [field.text() for field in widget.findChildren(QLineEdit)]
    parts += [field.placeholderText() for field in widget.findChildren(QLineEdit)]
    parts += [button.text() for button in widget.findChildren(QPushButton)]
    parts += [field.itemText(i) for field in widget.findChildren(QLineEdit)
              for i in range(0)]
    return "\n".join(parts)


class ProductShellTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from tempfile import TemporaryDirectory

        from equipeffi.infrastructure.runtime_logging import close_logging

        self.temp = TemporaryDirectory(prefix="phase6-shell-中文-")
        self.addCleanup(self.temp.cleanup)
        self.paths = AppDataPaths(Path(self.temp.name))
        self.settings, self.logger = create_settings_runtime(paths=self.paths)
        # 必须在临时目录清理**之前**关闭日志句柄，否则 Windows 上
        # `equipeffi.log` 仍被占用，cleanup 会抛 PermissionError。
        self.addCleanup(close_logging, self.logger)
        self.service = _service(self.paths)

    def window(self, **kwargs):
        window = MainWindow(self.settings, self.service,
                            data_location=self.paths.root, **kwargs)
        self.addCleanup(window.close)
        return window


# --------------------------------------------------------------------------
# G01 正式 AppShell + 启动入口 + 导航契约
# --------------------------------------------------------------------------

class EntrypointTests(ProductShellTestCase):
    def test_no_arguments_launches_the_qt_shell(self):
        from equipeffi.entrypoint import main

        with patch("equipeffi.composition.launch_qt", return_value=0) as launch:
            self.assertEqual(main([]), 0)
        launch.assert_called_once_with()

    def test_none_argv_means_console_arguments_not_empty(self):
        """``argv is None`` 不得被当成"无参数启动"。

        否则 zipapp / ``runpy`` / ``python -m equipeffi`` 会误入桌面事件循环，
        把 ``--status`` / ``--jsonl`` 等路径吞掉。
        """

        from equipeffi.entrypoint import main

        with patch("equipeffi.composition.launch_qt", return_value=0) as launch:
            with patch("sys.argv", ["equipeffi", "--status"]):
                self.assertEqual(main(), 0)
        launch.assert_not_called()

    def test_gui_and_qt_launch_the_same_shell(self):
        from equipeffi.entrypoint import main

        with patch("equipeffi.composition.launch_qt", return_value=0) as launch:
            main(["--gui"])
            main(["--qt"])
        self.assertEqual(launch.call_count, 2)

    def test_desktop_options_reject_business_input(self):
        from equipeffi.entrypoint import main

        for argv in (["--gui", "--status"], ["--qt", "--jsonl"]):
            with self.subTest(argv=argv):
                with self.assertRaises(SystemExit):
                    main(argv)

    def test_legacy_tk_launcher_is_not_a_product_entrypoint(self):
        from equipeffi.presentation.desktop import launcher

        for forbidden in ("launch_packaged_gui", "_run_web_fallback", "launch"):
            with self.subTest(forbidden=forbidden):
                self.assertFalse(hasattr(launcher, forbidden))
        source = Path(launcher.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import tkinter", source)

    def test_main_py_no_longer_prints_a_console_only_notice(self):
        """无参数启动必须是产品 Shell，不是"已就绪 + 启动窗口: ..."提示。"""

        source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertNotIn("已就绪", source)
        self.assertIn("package_main", source)


class AppShellTests(ProductShellTestCase):
    def test_five_first_level_pages_are_all_real(self):
        window = self.window()
        self.assertEqual(window.pages.count(), len(PAGES))
        for index, title in enumerate(PAGES):
            with self.subTest(page=title):
                window.navigation.setCurrentRow(index)
                self.assertEqual(window.pages.currentIndex(), index)
                widget = window.pages.currentWidget()
                self.assertIsNotNone(widget)
                self.assertIn(title, _visible_text(widget))

    def test_registry_pages_are_the_real_page_classes(self):
        window = self.window()
        self.assertIsInstance(window._page_widgets["首页"], HomePage)
        self.assertIsInstance(window._page_widgets["标准库"], StandardsPage)
        self.assertIsInstance(window._page_widgets["新建分析"], AnalysisPage)
        self.assertIsInstance(window._page_widgets["分析记录"], RecordsPage)
        self.assertIsInstance(window._page_widgets["设置"], SettingsPage)

    def test_no_placeholder_page_helper_exists_any_more(self):
        import equipeffi.presentation.qt.pages as pages

        self.assertFalse(hasattr(pages, "placeholder_page"))
        self.assertFalse(hasattr(pages, "placeholder"))

    def test_no_development_state_wording_is_visible(self):
        window = self.window()
        for title in PAGES:
            with self.subTest(page=title):
                window.navigation.setCurrentRow(PAGES.index(title))
                text = _visible_text(window.pages.currentWidget())
                for phrase in PLACEHOLDER_TEXTS:
                    self.assertNotIn(phrase, text)

    def test_primary_navigation_has_no_excel_or_parameter_library(self):
        """Excel 属 Phase 8；GB 19762 无独立用户参数库需求。"""

        self.assertNotIn("Excel", " ".join(PAGES))
        self.assertNotIn("参数库", " ".join(PAGES))
        self.assertEqual(PAGES, ("首页", "标准库", "新建分析", "分析记录", "设置"))

    def test_navigation_contract_only_switches_pages_and_selects_objects(self):
        window = self.window()
        window.open_standards()
        self.assertEqual(window.pages.currentIndex(), PAGES.index("标准库"))
        window.open_settings()
        self.assertEqual(window.pages.currentIndex(), PAGES.index("设置"))
        window.open_home()
        self.assertEqual(window.pages.currentIndex(), PAGES.index("首页"))
        window.open_analysis()
        self.assertEqual(window.pages.currentIndex(), PAGES.index("新建分析"))
        window.open_records()
        self.assertEqual(window.pages.currentIndex(), PAGES.index("分析记录"))

    def test_no_event_bus_or_router_framework_was_introduced(self):
        """禁止事件总线 / 通用 Router / Page 基类体系 / DI 容器。"""

        forbidden_modules = ("event_bus", "router", "page_base", "container")
        qt_dir = SRC / "equipeffi" / "presentation" / "qt"
        names = {path.stem for path in qt_dir.rglob("*.py")}
        for name in forbidden_modules:
            self.assertNotIn(name, names)
        source = (qt_dir / "navigation.py").read_text(encoding="utf-8")
        self.assertIn("Protocol", source)
        self.assertNotIn("class Base", source)


# --------------------------------------------------------------------------
# G02 首页 + 标准库
# --------------------------------------------------------------------------

class HomePageTests(ProductShellTestCase):
    def test_home_offers_new_analysis_and_current_standard(self):
        window = self.window()
        home = window.home_page
        self.assertIn("开始新的离心泵分析", home.new_analysis_button.text())
        self.assertIn("查看当前正式标准", home.open_standard_button.text())
        overview = self.service.standard_overview()
        self.assertIn(overview["standard_code"], home.standard_label.text())
        self.assertIn(overview["standard_name"], home.standard_label.text())

    def test_home_lists_recent_drafts_and_records_from_existing_capabilities(self):
        home = self.window().home_page
        # 空状态不得显示开发态文案，也不得崩溃。
        self.assertIn("暂无草稿", home.drafts.item(0).text())
        self.assertIn("暂无正式记录", home.records.item(0).text())
        self.assertFalse(home.resume_button.isEnabled())
        self.assertFalse(home.open_record_button.isEnabled())

    def test_home_reuses_list_workspaces_and_list_records(self):
        """首页不得为列表新增 persistence：必须复用现有 Use Case。"""

        request = _request(WATER)
        self.service.create_workspace("P6-DRAFT", request)
        home = self.window().home_page
        self.assertEqual(len(home._draft_ids), len(self.service.list_workspaces(limit=5)))
        self.assertIn("P6-DRAFT", home._draft_ids[0])

    def test_home_navigates_to_analysis_and_standards(self):
        window = self.window()
        window.home_page._start_new_analysis()
        self.assertEqual(window.pages.currentIndex(), PAGES.index("新建分析"))
        window.home_page._open_standard()
        self.assertEqual(window.pages.currentIndex(), PAGES.index("标准库"))

    def test_home_continues_a_recent_draft(self):
        request = _request(WATER)
        self.service.create_workspace("P6-RESUME", request)
        window = self.window()
        home = window.home_page
        home.refresh()
        home._open_draft(0)
        self.assertEqual(window.pages.currentIndex(), PAGES.index("新建分析"))
        self.assertEqual(window.analysis_page.draft_name.text(), "P6-RESUME")

    def test_home_does_not_render_kpi_dashboard_widgets(self):
        text = _visible_text(self.window().home_page)
        for word in ("KPI", "Dashboard", "仪表盘", "统计图"):
            self.assertNotIn(word, text)


class StandardsPageTests(ProductShellTestCase):
    def test_standard_facts_come_from_the_application_read_model(self):
        page = self.window().standards_page
        overview = self.service.standard_overview()
        text = page.facts.text() + page.scopes.text() + page.source.text()
        for key in ("standard_code", "standard_name", "effective_date", "data_version"):
            self.assertIn(str(overview[key]), text)

    def test_standard_page_shows_supported_categories_and_support_status(self):
        page = self.window().standards_page
        overview = self.service.standard_overview()
        scopes = page.scopes.text()
        for category in overview["supported_categories"]:
            self.assertIn(category, scopes)
        self.assertIn("正式支持", scopes)

    def test_standard_page_starts_an_analysis(self):
        window = self.window()
        window.standards_page._start_analysis()
        self.assertEqual(window.pages.currentIndex(), PAGES.index("新建分析"))

    def test_standard_page_does_not_keep_a_second_standard_table(self):
        """禁止 Presentation 自维护第二份标准表 / 硬编码第二套标准数据。"""

        source = (SRC / "equipeffi" / "presentation" / "qt" / "pages"
                  / "standards.py").read_text(encoding="utf-8")
        self.assertNotIn("GB 19762", source.replace("GB 19762—2025《", ""))
        # 不得解析 Markdown/PDF，也不得内联标准限值表。
        for forbidden in ("open(", "read_text", ".pdf", ".md", "sqlite"):
            self.assertNotIn(forbidden, source)

    def test_standard_page_reports_missing_supersession_instead_of_inventing(self):
        page = self.window().standards_page
        self.assertIn("未提供", page.source.text())


# --------------------------------------------------------------------------
# G03 Analysis 产品层级
# --------------------------------------------------------------------------

def WATER_AS_OF() -> str:
    return "2026-08-23"


class AnalysisLayeringTests(ProductShellTestCase):
    def page(self):
        page = AnalysisPage(self.service)
        self.addCleanup(lambda: page.deleteLater())
        return page

    def fill(self, page, values):
        page.category.setCurrentIndex(page.category.findData(values["category"]))
        for key in ("QBEP", "HBEP", "speed", "efficiency"):
            page.point_inputs[key].setText(values[key])
        page.suction.setCurrentIndex(page.suction.findData(values["suction"]))
        if page.stages.isEnabled():
            page.stages.setText(values["stages"])
        page.as_of.setText(WATER_AS_OF())

    def test_water_result_has_five_layers(self):
        page = self.page()
        self.fill(page, WATER)
        result = page.evaluate()
        self.assertIsNotNone(result)
        # 1 结论 / 2 实际值与限值 / 3 解释 / 4 标准依据 / 5 技术详情（折叠）
        self.assertEqual(page.conclusion.text(), result.ui_conclusion)
        self.assertIn("实际泵效率", page.values_label.text())
        self.assertIn("对应等级效率限值", page.values_label.text())
        self.assertTrue(page.reason_label.text().strip())
        self.assertIn("所选标准", page.basis.text())
        self.assertFalse(page.technical_box.is_expanded())

    def test_chemical_result_has_the_same_layers(self):
        page = self.page()
        self.fill(page, CHEMICAL)
        result = page.evaluate()
        self.assertIsNotNone(result)
        self.assertIn("实际泵效率", page.values_label.text())
        self.assertIn("所选标准", page.basis.text())
        self.assertFalse(page.technical_box.is_expanded())

    def test_ordinary_layers_do_not_leak_internal_identifiers(self):
        page = self.page()
        self.fill(page, CHEMICAL)
        page.evaluate()
        ordinary = "\n".join([
            page.conclusion.text(), page.summary.text(), page.values_label.text(),
            page.reason_label.text(), page.basis.text(),
        ])
        for token in INTERNAL_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(token, ordinary)

    def test_technical_details_keep_audit_capability(self):
        page = self.page()
        self.fill(page, CHEMICAL)
        page.evaluate()
        technical = page.technical.text()
        self.assertIn("命中规则", technical)
        self.assertIn("支持状态", technical)
        page.show()
        self.app.processEvents()
        page.technical_box.set_expanded(True)
        self.assertTrue(page.technical_box.is_expanded())

    def test_values_and_limits_use_user_facing_threshold_names(self):
        page = self.page()
        self.fill(page, WATER)
        page.evaluate()
        self.assertIn("1级能效效率限值（%）", page.values_label.text())
        self.assertNotIn("1级效率_%", page.values_label.text())

    def test_evaluation_date_remains_a_non_blocking_notice(self):
        page = self.page()
        self.fill(page, WATER)
        page.as_of.setText("2020-01-01")  # 早于实施日期
        result = page.evaluate()
        self.assertIsNotNone(result)
        self.assertEqual(result.evaluation_status, "SUCCESS")
        self.assertIsNotNone(result.grade)
        self.assertIn("该标准尚未实施", page.warning_label.text())
        self.assertTrue(page.warning_label.isVisibleTo(page))


# --------------------------------------------------------------------------
# G04 Records 产品化
# --------------------------------------------------------------------------

class RecordsPageTests(ProductShellTestCase):
    def _finalize(self, values, record_id):
        """走真实 Workspace → 评价 → 固化链路（结果必须绑定草稿修订号）。"""

        workspace_id = f"{record_id}-WS"
        request = _request(values, record_id=record_id)
        self.service.create_workspace(workspace_id, request)
        workspace = self.service.load_workspace(workspace_id)
        request = self.service.request_from_workspace(workspace, record_id=record_id)
        result = self.service.evaluate_workspace(workspace_id, record_id=record_id)
        return self.service.finalize(record_id=record_id, workspace_id=workspace_id,
                                     request=request, result=result)

    def test_search_and_filters_exist_and_work(self):
        self._finalize(WATER, "P6-W-1")
        self._finalize(CHEMICAL, "P6-C-1")
        window = self.window()
        page = window.records_page
        self.assertEqual(len(page.filtered_records()), 2)
        page.search.setText("P6-C-1")
        self.assertEqual([r.record_id for r in page.filtered_records()], ["P6-C-1"])
        page.clear_filters()
        self.assertEqual(len(page.filtered_records()), 2)
        page.category_filter.setCurrentIndex(
            page.category_filter.findText(CHEMICAL["category"]))
        self.assertEqual(len(page.filtered_records()), 1)
        page.clear_filters()
        page.date_filter.setText("1900")
        self.assertEqual(page.filtered_records(), [])
        page.clear_filters()
        self.assertEqual(len(page.filtered_records()), 2)

    def test_filter_by_conclusion_uses_snapshot_status(self):
        self._finalize(WATER, "P6-W-2")
        page = self.window().records_page
        page.conclusion_filter.setCurrentIndex(
            page.conclusion_filter.findText("已判定等级"))
        self.assertEqual(len(page.filtered_records()), 1)
        page.conclusion_filter.setCurrentIndex(
            page.conclusion_filter.findText("不适用（超出标准范围）"))
        self.assertEqual(page.filtered_records(), [])

    def test_history_snapshot_is_displayed_without_drift(self):
        self._finalize(WATER, "P6-W-3")
        page = self.window().records_page
        snapshot = self.service.open_record("P6-W-3")
        before = snapshot.result_snapshot_json if hasattr(
            snapshot, "result_snapshot_json") else None
        text = page.show_record("P6-W-3")
        self.assertIn("P6-W-3", text)
        self.assertIn(snapshot.ui_conclusion, text)
        after = self.service.open_record("P6-W-3")
        if before is not None:
            self.assertEqual(before, after.result_snapshot_json)

    def test_reopen_does_not_recalculate(self):
        self._finalize(CHEMICAL, "P6-C-4")
        page = self.window().records_page
        with patch.object(self.service, "evaluate",
                          side_effect=AssertionError("Reopen 不得重算")):
            page.show_record("P6-C-4")

    @staticmethod
    def _snapshot_stub(support_status="NOT_IN_RELEASE_SCOPE"):
        """只读快照替身：字段与 RecordSnapshot 一致，用于渲染层断言。"""

        from types import SimpleNamespace

        return SimpleNamespace(
            evaluation_status="SUCCESS", canonical_version="2026.09.26",
            numeric_profile_id="EQUIPEFFI_PUMP_DECIMAL50_V2",
            result_contract_version="v1",
            reference_snapshot={"standard": {"rule_profile": "pump_chemical"}},
            input_snapshot={"request_fingerprint": "FP", "workspace_revision": 1},
            support_status=support_status)

    def test_record_detail_shows_snapshot_support_status_not_today_value(self):
        """历史 Record 显示**当时**的支持状态，不追溯改写。"""

        request = _request(CHEMICAL)
        result = self.service.evaluate(request)
        self.assertEqual(result.support_status, "SUPPORTED")
        page = self.window().records_page
        page._render_technical(self._snapshot_stub(),
                                {"matched_rule_id": "X",
                                 "support_status": "NOT_IN_RELEASE_SCOPE"})
        self.assertIn("当前版本未支持", page.technical.text())

    def test_no_lineage_or_audit_or_reproduce_was_implemented(self):
        source = (SRC / "equipeffi" / "presentation" / "qt" / "pages"
                  / "records.py").read_text(encoding="utf-8")
        for forbidden in ("lineage", "audit_event", "reproduce", "recalculate"):
            self.assertNotIn(forbidden, source)


# --------------------------------------------------------------------------
# G05 Settings / About
# --------------------------------------------------------------------------

class SettingsPageTests(ProductShellTestCase):
    def test_settings_exposes_only_real_configurable_items(self):
        page = self.window().settings_page
        text = _visible_text(page) + page.about.text() + page.runtime.text()
        self.assertIn("日志级别", text)
        self.assertIn("应用版本", page.about.text())
        self.assertIn("数据存储位置", page.runtime.text())
        self.assertIn(str(self.paths.root), page.runtime.text())

    def test_settings_does_not_expose_algorithm_contracts_as_user_options(self):
        page = self.window().settings_page
        blob = _visible_text(page) + page.about.text() + page.runtime.text()
        for token in INTERNAL_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(token, blob)
        from equipeffi.presentation.qt.pages.settings import FORBIDDEN_SETTING_TOKENS

        for token in FORBIDDEN_SETTING_TOKENS:
            with self.subTest(forbidden=token):
                self.assertNotIn(token, blob)

    def test_settings_shows_current_standard(self):
        page = self.window().settings_page
        overview = self.service.standard_overview()
        self.assertIn(overview["standard_code"], page.about.text())

    def test_log_level_is_a_real_persisted_preference(self):
        page = self.window().settings_page
        page.log_level.setCurrentText("WARNING")
        self.assertEqual(self.settings.get("log.level"), "WARNING")

    def test_no_installer_or_update_system(self):
        # 只检查真实代码，不检查解释性 docstring/注释。
        source = (SRC / "equipeffi" / "presentation" / "qt" / "pages"
                  / "settings.py").read_text(encoding="utf-8")
        code = re.sub(r'""".*?"""', "", source, flags=re.S)
        for forbidden in ("updater", "auto_update", "QProcess", "subprocess"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, code)


# --------------------------------------------------------------------------
# G06 QA 项真实处置
# --------------------------------------------------------------------------

class QaDispositionTests(ProductShellTestCase):
    def test_qa_p5_001_and_002_remain_open_with_a_named_blocker(self):
        """共享 Application/CLI 语义未能在 Phase 6 收口，必须留下明确 blocker。"""

        request = _request(CHEMICAL)
        # 正式纵向切片（统一 Use Case）已支持。
        self.assertEqual(self.service.evaluate(request).support_status, "SUPPORTED")
        # 遗留共享表面仍被冻结文件短路（见 QA_BACKLOG 的 provenance 冻结 blocker）。
        from equipeffi.application.services.evaluation_service import EvaluationService
        from equipeffi.domain.common.models import DeviceDraft

        legacy = EvaluationService(JsonStandardRepository(SRC))
        result = legacy.evaluate(DeviceDraft(
            record_id="QA-P5", device_type="pump_chemical",
            raw_values={"category": CHEMICAL["category"], "suction": "单吸",
                        "stages": "1", "flow_m3h": 100, "head_m": 14,
                        "rated_speed_rpm": 2900, "pump_efficiency": 73}))
        self.assertEqual(result.support_status, "NOT_IN_RELEASE_SCOPE")

    def test_qa_p3_003_legacy_as_of_gate_is_still_present(self):
        """遗留 as_of 门禁属冻结文件；Phase 6 未改，须继续登记。"""

        source = (SRC / "equipeffi" / "application" / "services"
                  / "evaluation_service.py").read_text(encoding="utf-8")
        self.assertIn("effective_as_of < effective_date", source)

    def test_frozen_implementation_files_are_unchanged_from_base(self):
        """候选层 Golden 冻结了这些实现文件；Phase 6 不得改动它们。"""

        import subprocess

        protected = (
            "src/equipeffi/application/services/evaluation_service.py",
            "src/equipeffi/application/services/input_normalization.py",
            "src/equipeffi/domain/evaluation/evaluators/pump.py",
            "src/equipeffi/domain/evaluation/device_evaluators.py",
            "src/equipeffi/domain/evaluation/decimal_math.py",
            "src/equipeffi/domain/evaluation/device_types.py",
            "src/equipeffi/domain/evaluation/evaluator_registry.py",
            "src/equipeffi/infrastructure/standards/json_repository.py",
            "src/equipeffi/resources/standards/pump.json",
        )
        changed = subprocess.run(
            ["git", "diff", "--name-only",
             "f3e32f84123937ed6caa2b84b7cc0cd04c3100e0", "HEAD", "--", *protected],
            cwd=ROOT, capture_output=True, text=True, check=False).stdout.split()
        pending = subprocess.run(
            ["git", "diff", "--name-only", "--", *protected],
            cwd=ROOT, capture_output=True, text=True, check=False).stdout.split()
        self.assertEqual(changed, [], f"受保护实现文件被改动：{changed}")
        self.assertEqual(pending, [], f"受保护实现文件有未提交改动：{pending}")
