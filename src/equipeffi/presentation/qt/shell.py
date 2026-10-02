"""薄壳：占位导航与窗口状态；不接设备评价。"""
import base64
import binascii
import logging

from PySide6.QtCore import QByteArray
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QMainWindow, QStackedWidget, QWidget

from ...application.services.settings_service import SettingsService
from .navigation import PAGES
from .pages import placeholder_page
from .tokens import TOKENS


class MainWindow(QMainWindow):
    def __init__(self, settings: SettingsService):
        super().__init__()
        self.settings = settings
        self.setWindowTitle("设备能效分析工具 · Phase 2 工程薄壳")
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
        for title in PAGES:
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
