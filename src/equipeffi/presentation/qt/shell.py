"""薄壳：统一 GB 19762 分析页与分析记录页；窗口状态经 SettingsService 持久化。"""
import base64
import binascii
import logging

from PySide6.QtCore import QByteArray
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QMainWindow, QStackedWidget, QWidget

from ...application.services.settings_service import SettingsService
from .navigation import PAGES
from .pages import placeholder_page
from .pages.analysis import AnalysisPage
from .pages.records import RecordsPage
from .tokens import TOKENS


class MainWindow(QMainWindow):
    def __init__(self, settings: SettingsService, analysis=None):
        super().__init__()
        self.settings = settings
        self.setWindowTitle("设备能效分析工具 · GB 19762—2025 离心泵能效分析")
        self.resize(1000, 700)
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
        self.analysis_page = AnalysisPage(analysis) if analysis is not None else None
        self.records_page = RecordsPage(analysis) if analysis is not None else None
        for title in PAGES:
            if title == "新建分析" and self.analysis_page is not None:
                self.pages.addWidget(self.analysis_page)
            elif title == "分析记录" and self.records_page is not None:
                self.pages.addWidget(self.records_page)
            else:
                self.pages.addWidget(placeholder_page(title))
        layout.addWidget(self.navigation)
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(container)
        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.navigation.setCurrentRow(0)
        self._restore("window.geometry", self.restoreGeometry)
        self._restore("window.state", self.restoreState)

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

    def closeEvent(self, event):
        try:
            self.settings.set("window.geometry", base64.b64encode(bytes(self.saveGeometry())).decode("ascii"))
            self.settings.set("window.state", base64.b64encode(bytes(self.saveState())).decode("ascii"))
        except Exception:
            # 保留完整根因并拒绝关闭，避免将保存失败伪装为成功。
            logging.getLogger("equipeffi.qt").exception("窗口设置保存失败")
            event.ignore()
            return
        super().closeEvent(event)
