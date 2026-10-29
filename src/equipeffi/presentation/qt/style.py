"""本地家族视觉与高 DPI 资产；不依赖中央仓运行环境。"""
from functools import lru_cache
from pathlib import Path
import math
import xml.etree.ElementTree as ET

from PySide6.QtCore import QEvent, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QIconEngine, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QLabel

ASSETS = Path(__file__).with_name("assets")


class SvgIconEngine(QIconEngine):
    """直接在目标 painter 绘制既有 SVG，不先固定为低分辨率位图。"""
    def __init__(self, svg):
        super().__init__()
        self.svg = svg

    def clone(self):
        return SvgIconEngine(self.svg)

    def paint(self, painter, rect, mode, state):
        painter.save()
        if mode == QIcon.Mode.Disabled:
            painter.setOpacity(0.4)
        QSvgRenderer(self.svg).render(painter, QRectF(rect))
        painter.restore()

    def pixmap(self, size, mode, state):
        return self.scaledPixmap(size, mode, state, 1.0)

    def scaledPixmap(self, size, mode, state, scale):
        pixmap = QPixmap(QSize(math.ceil(size.width() * scale), math.ceil(size.height() * scale)))
        pixmap.setDevicePixelRatio(scale)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        self.paint(painter, QRectF(0, 0, size.width(), size.height()).toRect(), mode, state)
        painter.end()
        return pixmap


@lru_cache(maxsize=64)
def icon(name: str, color: str = "#197CC2") -> QIcon:
    root = ET.parse(ASSETS / "icons.svg").getroot()
    symbol = next(s for s in root if s.get("id") == f"qz-icon-{name}")
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
           + ''.join(ET.tostring(c, encoding="unicode") for c in symbol) + '</svg>')
    return QIcon(SvgIconEngine(svg.replace("currentColor", color).encode()))


class BrandLabel(QLabel):
    def __init__(self, height=56):
        super().__init__()
        self._image = QPixmap(str(ASSETS / "qingzhou-logo.png"))
        self._height = max(height, 48)
        self.setFixedSize(180, self._height)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setAccessibleName("青舟")
        self._render()

    def _render(self):
        if self._image.isNull():
            return
        ratio = self.devicePixelRatioF()
        width = min(180, self.width())
        pixmap = self._image.scaled(math.ceil(width * ratio), math.ceil(self._height * ratio),
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        pixmap.setDevicePixelRatio(ratio)
        self.setPixmap(pixmap)

    def resizeEvent(self, event):
        self._render()
        super().resizeEvent(event)

    def event(self, event):
        if event.type() in (QEvent.Type.DevicePixelRatioChange, QEvent.Type.Show):
            self._render()
        return super().event(event)


def brand(height: int = 56) -> QLabel:
    return BrandLabel(height)


def heading(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("pageHeading")
    label.setWordWrap(True)
    return label


STYLE = """
QWidget { font-family:'Microsoft YaHei UI','Microsoft YaHei'; font-size:14px; color:#213A4F; }
QMainWindow, QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget { background:#F5F8FC; }
QLabel { background:transparent; }
QLabel#pageHeading { font-size:24px; font-weight:600; color:#18364F; }
QLabel#homeHeading { font-size:30px; font-weight:800; color:#18364F; }
QLabel#coreResult, QLabel[coreResult="true"] { font-size:26px; font-weight:600; color:#18364F; }
QLabel#muted { color:#526A7D; font-size:13px; }
QLabel[warning="true"] { color:#956420; }
QFrame#sidebar { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #E6F2FC,stop:0.5 #EDF6FD,stop:1 #E6F2FB); border-right:1px solid #DAE7F1; }
QListWidget#navigation { background:transparent; border:0; outline:0; font-size:13px; font-weight:600; }
QListWidget#navigation::item { height:36px; padding:0 10px; margin:3px 0; border:2px solid transparent; border-left-width:3px; border-radius:9px; }
QListWidget#navigation::item:hover { background:#EDF6FD; }
QListWidget#navigation::item:selected { background:#D6EBF9; color:#116FAE; border-left-color:#298CCB; }
QListWidget#navigation::item:focus { border-color:#298CCB; }
QPushButton { background:white; border:2px solid #DAE7F1; border-radius:6px; padding:0 14px; min-height:36px; max-height:36px; }
QPushButton:hover { background:#EDF6FD; border-color:#197CC2; }
QPushButton:pressed { background:#D6EBF9; border-color:#116FAE; }
QPushButton:checked { background:#D6EBF9; color:#116FAE; border-color:#298CCB; }
QPushButton[primary="true"] { background:#116FAE; color:white; border-color:#116FAE; }
QPushButton[primary="true"]:hover { background:#0D6097; border-color:#0D6097; }
QPushButton[primary="true"]:pressed { background:#094E7C; border-color:#094E7C; }
QPushButton[role="light"] { background:transparent; color:#116FAE; border-color:transparent; }
QPushButton[role="light"]:hover { background:#EDF6FD; }
QPushButton[role="light"]:pressed { background:#D6EBF9; }
QPushButton[role="danger"] { color:#B9484A; border-color:#B9484A; }
QPushButton[role="danger"]:hover { background:#FDF0F0; }
QPushButton[role="danger"]:pressed { background:#F7DCDC; }
QPushButton:focus, QPushButton[primary="true"]:focus, QPushButton[role="light"]:focus, QPushButton[role="danger"]:focus { border:2px solid #298CCB; }
QPushButton:disabled, QPushButton[primary="true"]:disabled, QPushButton[role="light"]:disabled, QPushButton[role="danger"]:disabled { color:#698198; background:#F0F4F8; border-color:#DAE7F1; }
QPushButton#sidebarSettings { min-height:42px; max-height:42px; text-align:left; font-size:13px; font-weight:600; border-radius:9px; }
/* Override the ordinary button cap; leave room for borders below Qt's size limit. */
QPushButton#taskCard { text-align:left; background:white; border-radius:14px; padding:0; min-height:150px; max-height:100000px; }
QPushButton#taskCard:hover { background:#EDF6FD; }
QPushButton#taskCard:pressed { background:#D6EBF9; }
QPushButton#taskCard[primary="true"] { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #174E7C,stop:1 #116FAE); color:white; }
QPushButton#taskCard[primary="true"]:hover { background:#0D6097; }
QPushButton#taskCard[primary="true"]:pressed { background:#094E7C; }
QPushButton#taskCard:focus { border:2px solid #298CCB; }
QPushButton#taskCard:disabled, QPushButton#taskCard[primary="true"]:disabled { background:#F0F4F8; border-color:#DAE7F1; }
QLabel#taskTitle { font-size:20px; font-weight:600; color:#18364F; }
QLabel#taskDescription { font-size:13px; color:#526A7D; }
QLabel#taskTitle[onPrimary="true"] { color:white; }
QLabel#taskDescription[onPrimary="true"] { color:#DCEFFC; }
QLabel#taskTitle:disabled, QLabel#taskDescription:disabled { color:#698198; }
QLineEdit, QComboBox { background:white; border:2px solid #DAE7F1; border-radius:6px; min-height:36px; max-height:36px; padding:0 10px; selection-background-color:#D6EBF9; }
QLineEdit:read-only { background:#F7FAFD; color:#526A7D; }
QLineEdit:hover, QComboBox:hover { border-color:#B5CDDE; }
QLineEdit:focus, QComboBox:focus { border-color:#197CC2; }
QComboBox:disabled, QLineEdit:disabled { background:#F0F4F8; color:#698198; border-color:#DAE7F1; }
QComboBox QLineEdit { border:0; border-radius:0; background:transparent; padding:0; min-height:0; }
QComboBox::drop-down { border:0; width:28px; }
QComboBox::down-arrow { image:url(__ARROW__); width:16px; height:16px; }
QGroupBox { background:white; border:1px solid #DAE7F1; border-radius:10px; margin-top:0; padding:42px 14px 14px; font-size:16px; font-weight:600; }
QGroupBox::title { subcontrol-origin:border; subcontrol-position:top left; left:16px; top:14px; color:#18364F; }
QTableWidget, QListWidget { background:white; border:1px solid #DAE7F1; border-radius:6px; alternate-background-color:#F7FAFD; selection-background-color:#D6EBF9; selection-color:#18364F; }
QHeaderView::section { background:#F7FAFD; border:0; border-bottom:1px solid #DAE7F1; padding:10px 8px; color:#526A7D; font-size:13px; font-weight:600; }
QTableWidget::item { padding:8px; border-bottom:1px solid #EEF3F8; }
QTabWidget::pane { border:1px solid #DAE7F1; background:white; }
QTabBar::tab { height:32px; padding:0 16px; border:0; border-bottom:2px solid transparent; border-top:2px solid transparent; font-size:13px; font-weight:600; background:#F7FAFD; }
QTabBar::tab:selected { color:#116FAE; border-bottom-color:#298CCB; background:white; }
QTabBar::tab:hover { background:#EDF6FD; }
QTabBar::tab:focus { border-top-color:#298CCB; }
QScrollArea { border:0; }
QScrollBar:vertical { width:10px; background:#F5F8FC; margin:0; }
QScrollBar:horizontal { height:10px; background:#F5F8FC; margin:0; }
QScrollBar::handle { background:#B5CDDE; border-radius:5px; min-height:28px; min-width:28px; }
QScrollBar::handle:hover { background:#526A7D; }
QScrollBar::add-line, QScrollBar::sub-line { width:0; height:0; }
QToolTip { background:white; color:#213A4F; border:1px solid #DAE7F1; }
""".replace("__ARROW__", (ASSETS / "chevron-down.svg").as_posix())
