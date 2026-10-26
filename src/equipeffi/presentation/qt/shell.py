"""无侧栏首页与正式 Windows 业务壳；沿用最小跨页导航契约。"""
from __future__ import annotations

import base64
import binascii
import logging

from PySide6.QtCore import QByteArray, QTimer, QSize, Qt
from PySide6.QtWidgets import (QHBoxLayout, QVBoxLayout, QListWidget, QMainWindow,
                              QStackedWidget, QWidget, QFrame, QLabel, QPushButton)

from ...application.services.settings_service import SettingsService
from .navigation import PAGES
from .pages.analysis import AnalysisPage
from .pages.batch import BatchPage
from .pages.home import HomePage
from .pages.records import RecordsPage
from .pages.settings import SettingsPage
from .pages.standards import StandardsPage
from .pages.transformer_analysis import DeviceAnalysisPage, TransformerAnalysisPage
from .tokens import TOKENS
from .style import STYLE, brand, icon


class MainWindow(QMainWindow):
    def __init__(self, settings: SettingsService, analysis=None, *,
                 batch=None, transformer=None, motor=None, workspace_id: str | None = None, app_version: str = "",
                 data_location=None, external_launch_context=None):
        super().__init__()
        self.settings = settings
        self.app_version = app_version or _app_version()
        # 用户在批量任务进行中请求关闭时，先拒绝销毁 QThread 所属页面；
        # 待线程真正 finished 后自动重试关闭。
        self._close_pending = False
        self.setWindowTitle(
            "设备能效分析工具 · 离心泵与电力变压器能效分析"
            if transformer is not None
            else "设备能效分析工具 · GB 19762—2025 离心泵能效分析")
        if motor is not None:
            self.setWindowTitle("设备能效分析工具 · 电动机接入验收候选")
        self.resize(1000, 700)
        # 允许用户把窗口缩小；页面内容由各自的滚动区域承载，
        # 不得让内容的最小宽度把窗口锁在大尺寸上。
        self.setMinimumSize(560, 420)
        font = self.font()
        font.setPixelSize(TOKENS.font_size)
        self.setFont(font)
        self.setStyleSheet(STYLE)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(TOKENS.navigation_width)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(14, 24, 14, 20)
        sidebar_layout.addWidget(brand(46))
        self.brand_title = QLabel("设备能效分析工具")
        self.brand_title.setWordWrap(True)
        sidebar_layout.addWidget(self.brand_title)
        sidebar_layout.addSpacing(24)
        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setWordWrap(True)
        self.navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.navigation.setIconSize(QSize(18, 18))
        self.navigation.addItems(PAGES)
        for index, name in enumerate(("home", "book", "plus", "excel", "records", "settings")):
            self.navigation.item(index).setIcon(icon(name))
        # 设置保持原导航索引契约，由独立底部按钮承载。
        self.navigation.item(5).setHidden(True)
        sidebar_layout.addWidget(self.navigation, 1)
        self.settings_button = QPushButton("设置")
        self.settings_button.setCheckable(True)
        self.settings_button.setIcon(icon("settings"))
        self.settings_button.clicked.connect(self.open_settings)
        sidebar_layout.addWidget(self.settings_button)
        self.pages = QStackedWidget()

        # 所有页面都真实构建；analysis 为 None 时仍构建（用于仅设置/关于场景）。
        self.home_page = (HomePage(analysis, self, transformer=transformer, motor=motor)
                          if analysis is not None else None)
        if self.home_page is not None and batch is None:
            self.home_page.task_buttons[2].setEnabled(False)
            self.home_page.task_buttons[2].setToolTip("当前构建未装配表格导入服务。")
        self.standards_page = (StandardsPage(analysis, self, transformer=transformer, motor=motor)
                               if analysis is not None else None)
        # Phase 7：普通流程没有草稿概念，分析页不接收 workspace_id。
        self.analysis_page = AnalysisPage(analysis, navigator=self) if analysis is not None else None
        self.transformer_analysis_page = (
            TransformerAnalysisPage(transformer) if transformer is not None else None)
        from .pages.motor_analysis import MotorAnalysisPage
        self.motor_analysis_page = MotorAnalysisPage(motor) if motor is not None else None
        self.device_analysis_page = (
            DeviceAnalysisPage(self.analysis_page, self.transformer_analysis_page,
                               motor_page=self.motor_analysis_page)
            if self.analysis_page is not None and self.transformer_analysis_page is not None
            else None)
        # Phase 8：批量评价页只在装配了批量服务时构建（Excel 仍是 adapter 表面）。
        self.batch_page = (
            BatchPage(
                batch, navigator=self, settings=settings,
                external_launch_context=external_launch_context,
            )
            if batch is not None else None)
        if self.batch_page is not None:
            self.batch_page.background_idle.connect(self._finish_deferred_close)
        self.records_page = (
            RecordsPage(analysis, navigator=self, batch=batch,
                        transformer=transformer, motor=motor)
            if analysis is not None else None)
        self.settings_page = SettingsPage(settings, analysis, app_version=self.app_version,
                                         data_location=data_location, navigator=self,
                                         transformer=transformer, motor=motor)

        self._page_widgets = {
            "首页": self.home_page,
            "标准库": self.standards_page,
            "新建分析": self.device_analysis_page or self.analysis_page,
            "表格导入": self.batch_page,
            "分析记录": self.records_page,
            "设置": self.settings_page,
        }
        for title in PAGES:
            widget = self._page_widgets[title]
            self.pages.addWidget(widget if widget is not None else QWidget())
            if widget is None and title != "首页":
                self.navigation.item(PAGES.index(title)).setFlags(
                    self.navigation.item(PAGES.index(title)).flags() & ~Qt.ItemFlag.ItemIsEnabled)

        layout.addWidget(self.sidebar)
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(container)
        self.navigation.currentRowChanged.connect(self._on_navigation_changed)
        self.navigation.setCurrentRow(0)
        self._restore("window.geometry", self.restoreGeometry)
        self._restore("window.state", self.restoreState)

    # -- 最小导航契约 -------------------------------------------------------

    def _on_navigation_changed(self, row: int) -> None:
        self.sidebar.setVisible(row != 0)
        self.settings_button.setChecked(row == 5)
        self.pages.setCurrentIndex(row)
        widget = self.pages.currentWidget()
        refresh = getattr(widget, "refresh", None)
        if callable(refresh):
            refresh()

    def _show_page(self, title: str) -> None:
        index = PAGES.index(title)
        same_page = self.navigation.currentRow() == index
        self.navigation.setCurrentRow(index)
        self.pages.setCurrentIndex(index)
        if same_page:
            refresh = getattr(self.pages.currentWidget(), "refresh", None)
            if callable(refresh):
                refresh()

    def open_batch(self) -> None:
        if self.batch_page is not None:
            self._show_page("表格导入")

    def open_home(self) -> None:
        self._show_page("首页")

    def open_standards(self, standard_code: str | None = None) -> None:
        self._show_page("标准库")

    def open_analysis(self, workspace_id: str | None = None, *,
                      standard_code: str | None = None) -> None:
        """切到「新建分析」页。

        Phase 7：普通产品流程已取消草稿概念，因此这里只切页，不再载入草稿。
        `workspace_id` 参数保留仅为兼容既有调用方，**不再**驱动任何草稿行为。
        """

        if self.analysis_page is None:
            return
        if standard_code is not None:
            available = {self.analysis_page.service.standard_overview()["standard_code"]}
            if self.transformer_analysis_page is not None:
                available.add(self.transformer_analysis_page.service.standard_overview()["standard_code"])
            if self.motor_analysis_page is not None:
                available.add(self.motor_analysis_page.service.standard_overview()["standard_code"])
            if standard_code not in available:
                # 未知或未装配的标准不允许沿用上次设备。
                self._show_page("标准库")
                if self.standards_page is not None:
                    self.standards_page.list_status.setText("该标准尚未开放分析，请从标准库选择已接入的标准。")
                return
        if self.device_analysis_page is not None:
            self.device_analysis_page.select_standard(standard_code)
        self._show_page("新建分析")

    def resizeEvent(self, event):
        if hasattr(self, "sidebar"):
            self.sidebar.setFixedWidth(144 if self.width() < 760 else TOKENS.navigation_width)
        super().resizeEvent(event)

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
        """关闭窗口。

        两类情形必须分开（M2）：

        ```text
        后台批量评价仍在运行（正在写结果 Workbook / 提交 batch_record）
            -> event.ignore()：正式写入不能安全中断，等线程真正结束后自动关闭。

        普通窗口布局保存失败
            -> 记 warning/error 日志后**正常退出**：这是偏好设置，不是正式数据，
               不得因为它拒绝关闭窗口（此前会卡住用户）。
        ```

        正式的 Record / batch_record 写入失败**不会**走到这里：它们的失败在批量
        流程内部就已显式报错，绝不伪装成成功。
        """

        batch_page = self.batch_page
        if batch_page is not None and batch_page.has_active_run():
            self._close_pending = True
            batch_page.notify_close_deferred()
            event.ignore()
            return

        self._close_pending = False
        try:
            self.settings.set(
                "window.geometry",
                base64.b64encode(bytes(self.saveGeometry())).decode("ascii"))
            self.settings.set(
                "window.state",
                base64.b64encode(bytes(self.saveState())).decode("ascii"))
        except Exception:  # noqa: BLE001 - 偏好设置失败不得阻止正常退出
            logging.getLogger("equipeffi.qt").exception(
                "窗口布局保存失败（不影响退出，本次不保存布局偏好）")
        super().closeEvent(event)

def _app_version() -> str:
    try:
        from ... import __version__

        return __version__
    except Exception:  # pragma: no cover - 版本信息缺失不应阻止启动
        return ""
