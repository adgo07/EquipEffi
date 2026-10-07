"""正式 Windows Product Shell：五个真实一级页面。

一级导航（顺序即产品任务顺序）：首页 / 标准库 / 新建分析 / 分析记录 / 设置。
**每一个都是真实页面，没有 placeholder。**

跨页导航只实现"切页 + 选择目标对象 + 载入已有对象"，
不引入事件总线 / 通用 Router Framework / Page Base Class / DI 容器 / 导航状态机。

Excel 导入属 Phase 8，参数库当前无独立用户需求，因此**不**出现在一级导航。
"""
from __future__ import annotations

import base64
import binascii
import logging

from PySide6.QtCore import QByteArray, QTimer
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QMainWindow, QStackedWidget, QWidget

from ...application.services.settings_service import SettingsService
from .navigation import PAGES
from .pages.analysis import AnalysisPage
from .pages.batch import BatchPage
from .pages.home import HomePage
from .pages.records import RecordsPage
from .pages.settings import SettingsPage
from .pages.standards import StandardsPage
from .tokens import TOKENS


class MainWindow(QMainWindow):
    def __init__(self, settings: SettingsService, analysis=None, *,
                 batch=None, workspace_id: str | None = None, app_version: str = "",
                 data_location=None):
        super().__init__()
        self.settings = settings
        self.app_version = app_version or _app_version()
        # 用户在批量任务进行中请求关闭时，先拒绝销毁 QThread 所属页面；
        # 待线程真正 finished 后自动重试关闭。
        self._close_pending = False
        self.setWindowTitle("设备能效分析工具 · GB 19762—2025 离心泵能效分析")
        self.resize(1000, 700)
        # 允许用户把窗口缩小；页面内容由各自的滚动区域承载，
        # 不得让内容的最小宽度把窗口锁在大尺寸上。
        self.setMinimumSize(560, 420)
        font = self.font()
        font.setPixelSize(TOKENS.font_size)
        self.setFont(font)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setSpacing(TOKENS.spacing)
        self.navigation = QListWidget()
        self.navigation.setFixedWidth(TOKENS.navigation_width)
        self.navigation.addItems(PAGES)
        self.pages = QStackedWidget()

        # 所有页面都真实构建；analysis 为 None 时仍构建（用于仅设置/关于场景）。
        self.home_page = HomePage(analysis, self) if analysis is not None else None
        self.standards_page = StandardsPage(analysis, self) if analysis is not None else None
        # Phase 7：普通流程没有草稿概念，分析页不接收 workspace_id。
        self.analysis_page = AnalysisPage(analysis, navigator=self) if analysis is not None else None
        # Phase 8：批量评价页只在装配了批量服务时构建（Excel 仍是 adapter 表面）。
        self.batch_page = BatchPage(batch, navigator=self) if batch is not None else None
        if self.batch_page is not None:
            self.batch_page.background_idle.connect(self._finish_deferred_close)
        self.records_page = RecordsPage(analysis, navigator=self) if analysis is not None else None
        self.settings_page = SettingsPage(settings, analysis, app_version=self.app_version,
                                         data_location=data_location, navigator=self)

        self._page_widgets = {
            "首页": self.home_page,
            "标准库": self.standards_page,
            "新建分析": self.analysis_page,
            "Excel导入": self.batch_page,
            "分析记录": self.records_page,
            "设置": self.settings_page,
        }
        for title in PAGES:
            widget = self._page_widgets[title]
            self.pages.addWidget(widget if widget is not None else QWidget())

        layout.addWidget(self.navigation)
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(container)
        self.navigation.currentRowChanged.connect(self._on_navigation_changed)
        self.navigation.setCurrentRow(0)
        self._restore("window.geometry", self.restoreGeometry)
        self._restore("window.state", self.restoreState)

    # -- 最小导航契约 -------------------------------------------------------

    def _on_navigation_changed(self, row: int) -> None:
        self.pages.setCurrentIndex(row)
        widget = self.pages.currentWidget()
        refresh = getattr(widget, "refresh", None)
        if callable(refresh):
            refresh()

    def _show_page(self, title: str) -> None:
        index = PAGES.index(title)
        self.navigation.setCurrentRow(index)
        self.pages.setCurrentIndex(index)

    def open_batch(self) -> None:
        self._show_page("Excel导入")

    def open_home(self) -> None:
        self._show_page("首页")

    def open_standards(self, standard_code: str | None = None) -> None:
        self._show_page("标准库")

    def open_analysis(self, workspace_id: str | None = None) -> None:
        """切到「新建分析」页。

        Phase 7：普通产品流程已取消草稿概念，因此这里只切页，不再载入草稿。
        `workspace_id` 参数保留仅为兼容既有调用方，**不再**驱动任何草稿行为。
        """

        if self.analysis_page is None:
            return
        self._show_page("新建分析")

    def open_records(self, record_id: str | None = None) -> None:
        page = self.records_page
        if page is None:
            return
        self._show_page("分析记录")
        if record_id:
            page.show_record(record_id)

    def open_settings(self) -> None:
        self._show_page("设置")

    # -- 窗口状态 -----------------------------------------------------------

    def _restore(self, key, restore):
        value = self.settings.get(key)
        if not value:
            return
        try:
            data = base64.b64decode(value, validate=True)
        except (ValueError, binascii.Error):
            logging.getLogger("equipeffi.qt").warning("窗口设置无效，使用默认窗口布局")
            return
        if not restore(QByteArray(data)):
            logging.getLogger("equipeffi.qt").warning("窗口设置无法恢复，使用默认窗口布局")

    def _finish_deferred_close(self) -> None:
        """后台批量线程真正退出后，完成此前被拒绝的窗口关闭请求。"""

        if not self._close_pending:
            return
        self._close_pending = False
        # 不在 QThread.finished 信号栈内直接 close，避免对象销毁与信号派发重入。
        QTimer.singleShot(0, self.close)

    def closeEvent(self, event):
        batch_page = self.batch_page
        if batch_page is not None and batch_page.has_active_run():
            self._close_pending = True
            batch_page.notify_close_deferred()
            event.ignore()
            return

        self._close_pending = False
        try:
            self.settings.set("window.geometry", base64.b64encode(bytes(self.saveGeometry())).decode("ascii"))
            self.settings.set("window.state", base64.b64encode(bytes(self.saveState())).decode("ascii"))
        except Exception:
            # 保留完整根因并拒绝关闭，避免将保存失败伪装为成功。
            logging.getLogger("equipeffi.qt").exception("窗口设置保存失败")
            event.ignore()
            return
        super().closeEvent(event)


def _app_version() -> str:
    try:
        from ... import __version__

        return __version__
    except Exception:  # pragma: no cover - 版本信息缺失不应阻止启动
        return ""
