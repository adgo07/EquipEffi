"""Phase 6 — 完整 GB 19762 Product Shell（G07 证据）。

覆盖本轮交付的真实行为：

```text
启动入口：无参数 / --gui / --qt 都进入同一正式 Qt Shell
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
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QRect
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton
from PySide6.QtTest import QTest

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
    BatchPage,
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


def _dispose_widget(widget) -> None:
    """最小 Qt 生命周期清理：close -> deleteLater -> flush DeferredDelete -> processEvents。

    为什么必须显式 flush：`close()` 只是隐藏窗口，`deleteLater()` 只把删除排进
    事件队列。两者都不保证 C++ 侧对象在**本测试结束前**真的销毁，于是对象会
    推迟到不确定的时刻（下一个测试，甚至解释器收尾阶段）才析构，表现为
    "没有 FAIL/ERROR、没有 Ran...、进程直接终止"的 Qt 生命周期问题。

    这里只做**测试清理**，不改正式 Presentation 实现。
    """

    if widget is None:
        return
    try:
        widget.close()
    except RuntimeError:  # 已经销毁
        return
    widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    QCoreApplication.processEvents()


def _dispose_temp_dir(temp, close_logging, logger) -> None:
    """先关闭日志句柄再清理临时目录；句柄释放有延迟时重试。

    Windows CI（长短名路径、杀毒/索引扫描）会在句柄刚释放时短暂占用文件，
    导致 `TemporaryDirectory.cleanup` 抛 `PermissionError`。这里显式重试，
    避免把环境抖动误报成测试失败。
    """

    import gc
    import time

    close_logging(logger)
    gc.collect()
    for attempt in range(5):
        try:
            temp.cleanup()
            return
        except (PermissionError, OSError):
            if attempt == 4:
                raise
            time.sleep(0.3)


def _launch_window(settings, analysis, paths, **kwargs):
    """按 composition.launch_qt 的真实装配构造 MainWindow（不跑事件循环）。

    与 `launch_qt` 的差异只有在这一点：不调用 `app.run` 的 `exec()`。
    数据目录必须由 **composition** 解析并传入，测试不得自行注入。
    """

    from equipeffi.composition import create_batch_evaluation_service
    from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths

    resolved = paths if paths is not None else AppDataPaths.default()
    # Phase 8：「批量评价」是真实一级页面，因此按 launch_qt 的真实装配一并注入
    # 批量服务；不注入时该页退化为空控件，会让"所有页面都真实"的断言失真。
    batch = kwargs.pop("batch", None)
    if batch is None and analysis is not None:
        batch = create_batch_evaluation_service(paths=resolved)
    return MainWindow(settings, analysis, batch=batch,
                      data_location=resolved.root, **kwargs)


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
        self.paths = AppDataPaths(Path(self.temp.name))
        self.settings, self.logger = create_settings_runtime(paths=self.paths)
        # Windows 上日志句柄会占用临时目录内的 equipeffi.log；清理顺序与重试
        # 都必须显式处理，否则 long-path / 短名（8.3）环境会抛出 PermissionError。
        self.addCleanup(_dispose_temp_dir, self.temp, close_logging, self.logger)
        self.service = _service(self.paths)

    def window(self, **kwargs):
        """按**正式 composition 启动路径**构造窗口。

        刻意不手工注入 ``data_location``：那会掩盖 composition 未接线的问题。
        这里走 ``launch_qt`` 真正使用的同一组构造，只把 Qt 事件循环换成直接建窗。
        """

        window = _launch_window(self.settings, self.service, self.paths, **kwargs)
        # 只 `close()` 不足以保证 C++ 对象在下一个测试前析构；
        # 显式 flush DeferredDelete，避免跨测试 Qt 生命周期污染。
        self.addCleanup(_dispose_widget, window)
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

    def test_none_argv_uses_console_status_option(self):
        from equipeffi.entrypoint import main

        with patch("equipeffi.composition.launch_qt", return_value=0) as launch:
            with patch("equipeffi.entrypoint._runtime_status", return_value={"ready": True}):
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

        for argv in (["--gui", "--status"], ["--qt", "--status"]):
            with self.subTest(argv=argv):
                with self.assertRaises(SystemExit):
                    main(argv)

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
                expected = "设备能效分析工具" if title == "首页" else title
                self.assertIn(expected, _visible_text(widget))

    def test_registry_pages_are_the_real_page_classes(self):
        window = self.window()
        self.assertIsInstance(window._page_widgets["首页"], HomePage)
        self.assertIsInstance(window._page_widgets["标准库"], StandardsPage)
        self.assertIsInstance(window._page_widgets["新建分析"], AnalysisPage)
        self.assertIsInstance(window._page_widgets["表格导入"], BatchPage)
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

    def test_primary_navigation_has_no_parameter_library(self):
        """GB 19762 无独立用户参数库需求（标准参数/限值/依据归标准详情）。

        Phase 8 变更：Owner 已授权 Excel 批量评价成为正式产品表面，因此
        「批量评价」是允许的一级页面；参数库仍然不允许。
        Phase 6 当时的"导航不得含 Excel"断言已由该 Owner 决定取代。
        """

        self.assertNotIn("参数库", " ".join(PAGES))
        self.assertIn("表格导入", PAGES)
        self.assertEqual(PAGES, ("首页", "标准库", "新建分析", "表格导入",
                                 "分析记录", "设置"))

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
    def test_home_offers_standard_first_task_cards(self):
        window = self.window()
        home = window.home_page
        self.assertEqual([b.text().splitlines()[0] for b in home.task_buttons],
                         ["标准库", "新建分析", "表格导入", "分析记录"])
        self.assertTrue(window.sidebar.isHidden())
        home.task_buttons[0].click()
        self.assertEqual(window.pages.currentIndex(), PAGES.index("标准库"))
        self.assertFalse(window.sidebar.isHidden())

    def test_home_routes_devices_through_new_analysis_and_standards(self):
        from equipeffi.composition import create_transformer_analysis_service
        transformer = create_transformer_analysis_service(paths=self.paths)
        window = self.window(transformer=transformer)
        home = window.home_page
        home.task_buttons[0].click()
        page = window.standards_page
        codes = [page.table.item(row, 0).text() for row in range(page.table.rowCount())]
        self.assertEqual(codes, [self.service.standard_overview()["standard_code"],
                                 transformer.standard_overview()["standard_code"]])
        self.assertEqual(page.table.item(1, 4).text(), "已接入，待正式支持验收")
        page.open_detail(1)
        page.start_button.click()
        self.assertEqual(window.device_analysis_page.device_selector.currentData(), "transformer")
        window.open_home()
        home.task_buttons[1].click()
        self.assertEqual(window.device_analysis_page.device_selector.currentData(), "transformer")
        window.open_analysis(standard_code="GB 19762-2025")
        self.assertEqual(window.device_analysis_page.device_selector.currentData(), "centrifugal_pump")

    def test_home_lists_recent_records_from_existing_capabilities(self):
        home = self.window().home_page
        self.assertEqual(home.records.count(), 0)
        self.assertIn("尚无分析记录", home.record_status.text())

    def test_home_has_no_draft_surface(self):
        """Phase 7：普通界面没有「分析草稿」概念，首页也不提供草稿入口。"""

        home = self.window().home_page
        for name in ("drafts", "resume_button", "_draft_ids"):
            with self.subTest(attribute=name):
                self.assertFalse(hasattr(home, name))
        text = _visible_text(home)
        for word in ("草稿", "继续选中的草稿"):
            with self.subTest(word=word):
                self.assertNotIn(word, text)

    def test_home_reuses_list_records_without_new_persistence(self):
        """首页不得为列表新增 persistence：必须复用现有 Use Case。"""

        home = self.window().home_page
        self.assertEqual(len(home._record_ids), len(self.service.list_records(limit=5)))

    def test_home_navigates_to_analysis_and_standards(self):
        window = self.window()
        window.home_page._start_new_analysis()
        self.assertEqual(window.pages.currentIndex(), PAGES.index("新建分析"))
        window.home_page._open_standard()
        self.assertEqual(window.pages.currentIndex(), PAGES.index("标准库"))

    def test_home_opens_a_recent_record(self):
        window = self.window()
        home = window.home_page
        request = _request(WATER)
        result = self.service.evaluate(request)
        self.service.finalize(record_id="P6-HOME-R1", workspace_id=None,
                              request=request, result=result)
        home.refresh()
        home._open_record(0)
        self.assertEqual(window.pages.currentIndex(), PAGES.index("分析记录"))

    def test_home_does_not_render_kpi_dashboard_widgets(self):
        text = _visible_text(self.window().home_page)
        for word in ("KPI", "Dashboard", "仪表盘", "统计图"):
            self.assertNotIn(word, text)


class StandardsPageTests(ProductShellTestCase):
    def test_standard_facts_come_from_the_application_read_model(self):
        page = self.window().standards_page
        overview = self.service.standard_overview()
        page.open_detail(0)
        text = "\n".join(label.text() for label in page.section_labels)
        for key in ("standard_code", "standard_name", "effective_date"):
            self.assertIn(str(overview[key]), text)
        self.assertEqual(page.table.columnCount(), 5)

    def test_standard_page_shows_supported_categories_and_support_status(self):
        page = self.window().standards_page
        page.open_detail(0)
        for category in self.service.standard_overview()["supported_categories"]:
            self.assertIn(category, page.section_labels[1].text())
        self.assertEqual(page.table.item(0, 4).text(), "正式支持")
        self.assertNotIn("软件支持", page.section_labels[1].text())

    def test_standard_page_starts_an_analysis(self):
        window = self.window()
        window.standards_page.open_detail(0)
        window.standards_page.start_button.click()
        self.assertEqual(window.pages.currentIndex(), PAGES.index("新建分析"))

    def test_standard_page_does_not_keep_a_second_standard_table(self):
        source = (SRC / "equipeffi" / "presentation" / "qt" / "pages" / "standards.py").read_text(encoding="utf-8")
        for forbidden in ("read_text", "sqlite"):
            self.assertNotIn(forbidden, source)

    def test_special_options_are_searchable_and_separate_from_supported_categories(self):
        page = self.window().standards_page
        original = page.service.standard_overview()
        overview = dict(original, special_categories=["仅供分类的特殊选项"])
        with patch.object(page.service, "standard_overview", return_value=overview):
            page.refresh()
        page.search.setText("仅供分类的特殊选项")
        self.assertEqual(page.table.rowCount(), 1)
        page.open_detail(0)
        self.assertIn("其他可选项（不表示正式支持类别）：仅供分类的特殊选项", page.section_labels[1].text())

    def test_unknown_and_similar_number_codes_do_not_inherit_known_requirements(self):
        page = self.window().standards_page
        original = page.service.standard_overview()
        for code in ("UNKNOWN", "OTHER 19762-2025", "OTHER 20052-2024", "GB 18613-2099"):
            with self.subTest(code=code), patch.object(page.service, "standard_overview", return_value=dict(original, standard_code=code)):
                page.refresh()
                page.open_detail(0)
                text = page.section_labels[2].text()
                self.assertIn("未提供标准要求摘要", text)
                self.assertNotIn("表1至表6", text)
                self.assertNotIn("泵效率", text)
                self.assertNotIn("空载损耗", text)
        with patch.object(page.service, "standard_overview", return_value=dict(original, standard_code="UNKNOWN", requirements_text="来自现有展示投影的摘要")):
            page.refresh()
            page.open_detail(0)
            self.assertEqual(page.section_labels[2].text(), "来自现有展示投影的摘要")

    def test_standard_page_reports_missing_original_truthfully(self):
        page = self.window().standards_page
        page.open_detail(0)
        page.source_button.click()
        self.assertIn("当前没有可打开的标准原文", page.feedback.text())
        self.assertEqual(len(page.section_labels), 3)



# --------------------------------------------------------------------------
# G03 Analysis 产品层级
# --------------------------------------------------------------------------

def WATER_AS_OF() -> str:
    return "2026-08-23"


class AnalysisLayeringTests(ProductShellTestCase):
    def page(self, *, as_of=None):
        """分析页。

        Phase 7：页面没有评价日期输入，日期自动取本机当天；需要固定日期时
        用 `as_of` 覆盖（测试专用 hook，不产生用户可见控件）。
        """

        page = AnalysisPage(self.service, as_of=as_of)
        self.addCleanup(lambda: page.deleteLater())
        return page

    def fill(self, page, values):
        page.category.setCurrentIndex(page.category.findData(values["category"]))
        for key in ("QBEP", "HBEP", "speed", "efficiency"):
            page.point_inputs[key].setText(values[key])
        page.suction.setCurrentIndex(page.suction.findData(values["suction"]))
        if page.stages.isEnabled():
            page.stages.setText(values["stages"])

    def test_water_result_has_five_layers(self):
        page = self.page()
        self.fill(page, WATER)
        result = page.evaluate()
        self.assertIsNotNone(result)
        # Owner Phase 8 R1 / UI02：普通结果区只保留
        # 最终结论+等级 / 关键计算参数 / 对应等级效率限值。
        # 已删除：判定说明、为什么、所选标准、标准依据。
        self.assertEqual(page.conclusion.text(), result.ui_conclusion)
        self.assertIn("实际泵效率", page.values_label.text())
        self.assertIn("对应等级效率限值", page.values_label.text())
        self.assertIn("关键计算参数", page.basis.text())
        self.assertEqual(page.reason_label.text().strip(), "")
        self.assertNotIn("所选标准", page.basis.text())
        self.assertNotIn("标准依据", page.basis.text())

    def test_chemical_result_has_the_same_layers(self):
        page = self.page()
        self.fill(page, CHEMICAL)
        result = page.evaluate()
        self.assertIsNotNone(result)
        self.assertIn("实际泵效率", page.values_label.text())
        # UI02：不再展示"所选标准 / 标准依据"，只保留关键计算参数。
        self.assertIn("关键计算参数", page.basis.text())
        self.assertNotIn("所选标准", page.basis.text())

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

    def test_analysis_page_has_no_technical_detail_but_result_keeps_evidence(self):
        """Phase 7：分析页不展示技术详情，但内部证据仍完整保存在 Result 中。"""

        page = self.page()
        self.fill(page, CHEMICAL)
        result = page.evaluate()
        self.assertFalse(hasattr(page, "technical_box"))
        self.assertTrue(result.matched_rule_id)
        self.assertTrue(result.references["standard"]["pack_hash"])
        self.assertEqual(result.references["numeric_profile_id"],
                         "EQUIPEFFI_PUMP_DECIMAL50_V2")

    def test_values_and_limits_use_user_facing_threshold_names(self):
        page = self.page()
        self.fill(page, WATER)
        page.evaluate()
        self.assertIn("1级能效效率限值（%）", page.values_label.text())
        self.assertNotIn("1级效率_%", page.values_label.text())

    def test_evaluation_date_remains_a_non_blocking_notice(self):
        """早于实施日只给非阻断提示，不改变结论、等级或自动记录。"""

        from datetime import date as _date

        page = self.page(as_of=_date(2026, 2, 28))
        self.fill(page, WATER)
        result = page.evaluate()
        self.assertIsNotNone(result)
        self.assertEqual(result.evaluation_status, "SUCCESS")
        self.assertIsNotNone(result.grade)
        self.assertIn("该标准尚未实施", page.warning_label.text())
        self.assertTrue(page.warning_label.isVisibleTo(page))
        # 非阻断：仍然自动形成历史记录
        self.assertEqual(page.last_record_status, "RECORDED")

    def test_matching_evaluation_date_shows_no_warning(self):
        from datetime import date as _date

        page = self.page(as_of=_date(2026, 3, 1))
        self.fill(page, WATER)
        page.evaluate()
        self.assertEqual(page.warning_label.text(), "")


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
        # `findText` 找不到会静默返回 -1，因此这里显式断言选项真实存在
        # （结论筛选项使用面向用户的中文文案）。
        graded = page.conclusion_filter.findText("已判定等级")
        self.assertGreaterEqual(graded, 0, "必须存在「已判定等级」筛选项")
        page.conclusion_filter.setCurrentIndex(graded)
        self.assertEqual(len(page.filtered_records()), 1)

        out_of_scope = page.conclusion_filter.findText("不在范围")
        self.assertGreaterEqual(out_of_scope, 0, "必须存在「不在范围」筛选项")
        page.conclusion_filter.setCurrentIndex(out_of_scope)
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

    def test_settings_shows_both_standards_and_transformer_status_from_real_services(self):
        from equipeffi.composition import create_transformer_analysis_service

        transformer = create_transformer_analysis_service(
            paths=self.paths, with_persistence=True)
        page = self.window(transformer=transformer).settings_page
        pump = self.service.standard_overview()
        transformer_overview = transformer.standard_overview()
        about = page.about.text()

        self.assertIn(pump["standard_code"], about)
        self.assertIn(pump["standard_name"], about)
        self.assertIn(transformer_overview["standard_code"], about)
        self.assertIn(transformer_overview["name"], about)
        self.assertEqual(transformer_overview["support_status"], "IMPLEMENTED")
        self.assertIn("已接入，尚待正式支持验收", about)
        self.assertNotIn("IMPLEMENTED", about)
        self.assertNotIn("本版本已正式支持", about)
        self.assertNotIn("草稿", page.runtime.text())

    def test_settings_content_is_reachable_in_a_small_window(self):
        from equipeffi.composition import create_transformer_analysis_service

        transformer = create_transformer_analysis_service(
            paths=self.paths, with_persistence=True)
        window = self.window(transformer=transformer)
        window.resize(640, 480)
        window.show()
        window.open_settings()
        self.app.processEvents()

        page = window.settings_page
        scroll = page.scroll_area
        bar = scroll.verticalScrollBar()
        viewport = scroll.viewport()
        content = scroll.widget()
        self.assertGreater(bar.maximum(), 0, "小窗口必须提供可滚动范围")
        self.assertEqual(
            scroll.horizontalScrollBar().maximum(), 0,
            "小窗口应换行显示内容，不应依赖水平滚动来读完整文本",
        )
        self.assertIn("尚待正式支持验收", page.about.text())
        self.assertIn("运行日志存放于 logs 子目录", page.runtime.text())
        self.assertFalse(page.runtime_section.is_expanded())
        page.runtime_section.set_expanded(True)
        QTest.qWait(10)  # 折叠区展开后的换行高度由页面定时器更新。

        long_directory = self.paths.root.joinpath(*(["nested"] * 8))
        self.settings.set("last.directory", str(long_directory))
        page.refresh()
        QTest.qWait(10)
        last_directory_height = page.last_directory.heightForWidth(
            page.last_directory.width())
        self.assertGreaterEqual(
            page.last_directory.height(), last_directory_height,
            "刷新长目录后，标签高度应覆盖自动换行所需高度",
        )

        for label in (page.about, page.runtime):
            with self.subTest(label=label.objectName() or label.text()[:12]):
                required_height = label.heightForWidth(label.width())
                if required_height >= 0:
                    self.assertGreaterEqual(label.height(), required_height)
                content_y = label.mapTo(content, QPoint(0, 0)).y()
                value = max(0, content_y + label.height() - viewport.height())
                bar.setValue(min(value, bar.maximum()))
                self.app.processEvents()
                visible = QRect(label.mapTo(viewport, QPoint(0, 0)), label.size())
                self.assertTrue(
                    viewport.rect().contains(visible),
                    "滚动后每个信息标签应能完整进入可视区域",
                )

    def test_log_level_is_a_real_persisted_preference(self):
        page = self.window().settings_page
        # Owner Phase 8 R1 / UI04：界面显示中文，内部仍保存正式枚举值。
        index = page.log_level.findData("WARNING")
        self.assertGreaterEqual(index, 0, "内部值必须作为 item data 保留")
        page.log_level.setCurrentIndex(index)
        self.assertEqual(self.settings.get("log.level"), "WARNING")
        self.assertEqual(page.log_level.currentText(), "警告")

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

class QaClosureTests(ProductShellTestCase):
    """R1：QA-P5-001 / QA-P5-002(b) / QA-P3-003 已在本 Phase 内**真正关闭**。"""

    def test_qa_p5_001_and_002b_are_closed(self):
        """正式泵分析服务将石化泵报告为受支持 Profile。"""

        result = self.service.evaluate(_request(CHEMICAL, record_id="QA-CLOSED"))
        self.assertEqual(result.support_status, "SUPPORTED")
        self.assertNotIn("PROFILE_NOT_IN_RELEASE_SCOPE", result.issue_codes)



class FormalPumpServiceTests(ProductShellTestCase):
    """验证正式离心泵分析服务的支持状态和日期语义。"""

    CHEMICAL_VALUES = {
        "category": "单级石油化工离心泵", "suction": "单吸", "stages": "1",
        "flow_m3h": 100, "head_m": 14, "rated_speed_rpm": 2900,
        "pump_efficiency": 73,
    }

    def test_formal_service_supports_chemical_profile_and_returns_grade(self):
        result = self.service.evaluate(_request(CHEMICAL, record_id="R1-PARITY"))
        self.assertEqual(result.rule_profile, "pump_chemical")
        self.assertEqual(result.support_status, "SUPPORTED")
        self.assertIsNotNone(result.grade)

    def test_evaluation_date_is_a_non_blocking_formal_service_notice(self):
        """生命周期日期只生成提示，不改变正式业务状态或计算能力。"""

        from dataclasses import replace
        from datetime import date

        for as_of in ("2026-02-28", "2026-03-01", "2026-03-02"):
            with self.subTest(as_of=as_of):
                request = replace(
                    _request(CHEMICAL, record_id="R1-DATE"),
                    as_of=date.fromisoformat(as_of),
                )
                result = self.service.evaluate(request)
                self.assertEqual(result.support_status, "SUPPORTED")
                self.assertEqual(result.evaluation_status, "SUCCESS")
                self.assertTrue(result.metrics_by_id)
                self.assertEqual(result.issue_codes, ())
                if as_of < "2026-03-01":
                    self.assertEqual(result.warnings, ("该标准尚未实施",))
                else:
                    self.assertEqual(result.warnings, ())

    def test_pump_release_gate_is_the_single_source_of_truth(self):
        from equipeffi.application.services import pump_release_gate

        self.assertEqual(pump_release_gate.PUMP_RELEASE_SUPPORT["pump_chemical"],
                         "SUPPORTED")
        self.assertEqual(pump_release_gate.PUMP_RELEASE_SUPPORT["pump_water"],
                         "SUPPORTED")
        service = (SRC / "equipeffi" / "application" / "services"
                   / "centrifugal_pump_analysis_service.py").read_text(encoding="utf-8")
        self.assertNotIn('"pump_chemical": "NOT_IN_RELEASE_SCOPE"', service)


class StandardLifecycleNoticeTests(ProductShellTestCase):
    """B2：生命周期提示必须基于真实日期，不得硬编码结论。"""

    BEFORE = "2026-02-28"
    ON = "2026-03-01"
    AFTER = "2026-03-02"

    def test_state_covers_before_on_and_after_effective_date(self):
        from datetime import date

        cases = ((self.BEFORE, "NOT_YET_EFFECTIVE"), (self.ON, "EFFECTIVE"),
                 (self.AFTER, "EFFECTIVE"))
        for raw, expected in cases:
            with self.subTest(as_of=raw):
                overview = self.service.standard_overview(
                    as_of=date.fromisoformat(raw), show_lifecycle_warning=True)
                self.assertEqual(overview["lifecycle_state"], expected)

    def test_warning_only_before_effective_date(self):
        from datetime import date

        before = self.service.standard_overview(
            as_of=date.fromisoformat(self.BEFORE), show_lifecycle_warning=True)
        self.assertEqual(before["lifecycle_warning"], "该标准尚未实施")
        for raw in (self.ON, self.AFTER):
            with self.subTest(as_of=raw):
                overview = self.service.standard_overview(
                    as_of=date.fromisoformat(raw), show_lifecycle_warning=True)
                self.assertEqual(overview["lifecycle_warning"], "")

    def test_current_date_does_not_claim_not_yet_effective(self):
        """当前日期已达到实施日期时，不得显示"该标准尚未实施"。"""

        overview = self.service.standard_overview()
        self.assertEqual(overview["lifecycle_state"], "EFFECTIVE")
        self.assertEqual(self.window().standards_page.table.item(0, 2).text(), "已实施")

    def test_standards_page_derives_lifecycle_instead_of_hardcoding(self):
        source = (SRC / "equipeffi" / "presentation" / "qt" / "pages"
                  / "standards.py").read_text(encoding="utf-8")
        self.assertNotIn('"该标准尚未实施"', source)
        self.assertNotIn("'该标准尚未实施'", source)

    def test_no_supersession_is_invented(self):
        overview = self.service.standard_overview()
        self.assertEqual(overview["supersession_note"],
                         "当前标准数据未提供废止或被替代关系信息。")
        page = self.window().standards_page
        page.open_detail(0)
        page_text = "\n".join(label.text() for label in page.section_labels)
        self.assertNotIn("已废止", page_text)
        self.assertNotIn("已被替代", page_text)

    def test_lifecycle_notice_never_blocks_evaluation(self):
        from datetime import date

        page = AnalysisPage(self.service)
        self.addCleanup(lambda: page.deleteLater())
        page.category.setCurrentIndex(page.category.findData(WATER["category"]))
        for key in ("QBEP", "HBEP", "speed", "efficiency"):
            page.point_inputs[key].setText(WATER[key])
        page.suction.setCurrentIndex(page.suction.findData(WATER["suction"]))
        page.stages.setText(WATER["stages"])
        result = page.evaluate()
        self.assertEqual(result.evaluation_status, "SUCCESS")
        self.assertIsNotNone(result.grade)
        # Phase 7：非阻断 —— 早于实施日仍自动形成历史记录
        self.assertEqual(page.last_record_status, "RECORDED")


class SettingsCompositionWiringTests(ProductShellTestCase):
    """B3：数据目录必须由正式 composition 解析，不能靠测试注入。"""

    def test_launch_qt_passes_a_real_data_root(self):
        from unittest.mock import patch

        from equipeffi import composition

        captured: dict = {}

        def fake_run(settings, logger, analysis, **kwargs):
            captured.update(kwargs)
            return 0

        with patch("equipeffi.presentation.qt.app.run", side_effect=fake_run):
            composition.launch_qt(paths=self.paths)
        self.assertIn("data_location", captured)
        self.assertIsNotNone(captured["data_location"])
        self.assertEqual(Path(captured["data_location"]).resolve(),
                         self.paths.root.resolve())

    def test_settings_page_shows_the_real_path_from_composition(self):
        page = self.window().settings_page
        self.assertIn(str(self.paths.root), page.runtime.text())
        self.assertNotIn("未能确定", page.runtime.text())

    def test_settings_page_hides_internal_machine_keys(self):
        page = self.window().settings_page
        blob = _visible_text(page) + page.about.text() + page.runtime.text()
        for key in ("last.directory", "window.geometry", "window.state",
                    "log.level", "KEYS"):
            with self.subTest(key=key):
                self.assertNotIn(key, blob)

    def test_settings_page_does_not_join_internal_keys(self):
        source = (SRC / "equipeffi" / "presentation" / "qt" / "pages"
                  / "settings.py").read_text(encoding="utf-8")
        self.assertNotIn("type(self.settings).KEYS", source)
        self.assertNotIn("settings.KEYS", source)

    def test_window_geometry_is_not_offered_as_a_user_setting(self):
        page = self.window().settings_page
        self.assertNotIn("窗口位置", _visible_text(page))
        self.assertNotIn("窗口大小", _visible_text(page))

class R1SecondRoundBlockerTests(ProductShellTestCase):
    """复验 blocker 回归：内部标识泄露 / 共享门禁真实性 / 治理同步。"""

    def test_ordinary_result_never_shows_raw_issue_code(self):
        """普通结果区不得出现 `CATEGORY_UNCERTAIN` 等内部提示码。"""

        page = AnalysisPage(self.service)
        self.addCleanup(lambda: page.deleteLater())
        page.category.setCurrentIndex(page.category.findData("不确定类别"))
        result = page.evaluate()
        self.assertIn("CATEGORY_UNCERTAIN", result.issue_codes)

        ordinary = "\n".join([
            page.conclusion.text(), page.summary.text(), page.values_label.text(),
            page.reason_label.text(), page.basis.text(),
        ])
        self.assertNotIn("CATEGORY_UNCERTAIN", ordinary)
        self.assertNotIn("CATEGORY_", ordinary)
        # 应显示中文说明
        self.assertIn("尚未确认产品类别", ordinary)

    def test_raw_issue_code_remains_available_in_technical_detail(self):
        """审计能力不删：原始提示码保留在折叠技术详情区。"""

        page = AnalysisPage(self.service)
        self.addCleanup(lambda: page.deleteLater())
        page.category.setCurrentIndex(page.category.findData("不确定类别"))
        page.evaluate()

    def test_all_mapped_issue_codes_are_chinese(self):
        """所有已知内部码都必须有中文映射，且映射值不得是内部英文码。"""

        from equipeffi.presentation.qt.labels import ISSUE_CODE_LABELS

        known = (
            "CATEGORY_UNCERTAIN", "CATEGORY_UNRESOLVED", "CATEGORY_MISSING",
            "CATEGORY_NOT_APPLICABLE", "SUCTION_CATEGORY_CONFLICT",
            "STAGE_CATEGORY_CONFLICT", "FLOW_INVALID", "HEAD_INVALID",
            "SPEED_INVALID", "STAGES_INVALID", "EFFICIENCY_INVALID",
            "SUCTION_INVALID", "STAGES_MISSING", "SUCTION_MISSING", "INVALID_INPUT",
        )
        for code in known:
            with self.subTest(code=code):
                self.assertIn(code, ISSUE_CODE_LABELS)
                label = ISSUE_CODE_LABELS[code]
                self.assertNotIn("_", label)
                self.assertTrue(any("\u4e00" <= ch <= "\u9fff" for ch in label))

    def test_unmapped_issue_code_is_suppressed_not_shown_raw(self):
        from equipeffi.presentation.qt.labels import issue_code_texts

        self.assertEqual(issue_code_texts(["TOTALLY_UNKNOWN_CODE"]), [])
        self.assertEqual(issue_code_texts(["CATEGORY_UNCERTAIN"]), ["尚未确认产品类别"])

    def test_release_gate_controls_formal_support_status(self):
        """替换唯一发布门禁时，正式服务的 Profile 状态同步改变。"""

        from equipeffi.application.services import pump_release_gate as gate

        original = gate.PUMP_RELEASE_SUPPORT["pump_chemical"]
        request = _request(CHEMICAL, record_id="GATE")
        try:
            gate.PUMP_RELEASE_SUPPORT["pump_chemical"] = "SUPPORTED"
            supported = self.service.evaluate(request)
            self.assertEqual(supported.support_status, "SUPPORTED")
            gate.PUMP_RELEASE_SUPPORT["pump_chemical"] = "NOT_IN_RELEASE_SCOPE"
            unsupported = self.service.evaluate(request)
            self.assertEqual(unsupported.support_status, "NOT_IN_RELEASE_SCOPE")
            self.assertEqual(unsupported.evaluation_status, supported.evaluation_status)
            self.assertEqual(unsupported.grade, supported.grade)
        finally:
            gate.PUMP_RELEASE_SUPPORT["pump_chemical"] = original

    def test_unified_service_does_not_hardcode_release_support(self):
        source = (SRC / "equipeffi" / "application" / "services"
                  / "centrifugal_pump_analysis_service.py").read_text(encoding="utf-8")
        self.assertIn("return pump_release_support(rule_profile)", source)
        self.assertNotIn('if rule_profile == "pump_chemical":', source)
