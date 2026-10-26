"""本地家族视觉与资产；不依赖中央仓运行环境。"""
from pathlib import Path
import xml.etree.ElementTree as ET

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QLabel

ASSETS = Path(__file__).with_name("assets")


def icon(name: str, color: str = "#197CC2") -> QIcon:
    root = ET.parse(ASSETS / "icons.svg").getroot()
    symbol = next(s for s in root if s.get("id") == f"qz-icon-{name}")
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
           + ''.join(ET.tostring(c, encoding="unicode") for c in symbol) + '</svg>')
    renderer = QSvgRenderer(svg.replace("currentColor", color).encode())
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


class BrandLabel(QLabel):
    def __init__(self, height):
        super().__init__()
        self._image = QPixmap(str(ASSETS / "qingzhou-logo.png"))
        self._height = height
        self.setPixmap(self._image.scaledToHeight(height, Qt.TransformationMode.SmoothTransformation))
        self.setFixedHeight(height)
        self.setMinimumWidth(0)
        self.setAccessibleName("青舟")

    def resizeEvent(self, event):
        self.setPixmap(self._image.scaled(self.width(), self._height,
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        super().resizeEvent(event)


def brand(height: int = 52) -> QLabel:
    return BrandLabel(height)


def heading(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("pageHeading")
    label.setWordWrap(True)
    return label


STYLE = """
QWidget { font-family: 'Microsoft YaHei UI', 'Microsoft YaHei'; font-size:14px; color:#213A4F; }
QMainWindow, QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget { background:#F5F8FC; }
QLabel { background:transparent; }
QLabel#pageHeading { font-size:24px; font-weight:600; color:#18364F; }
QLabel#homeHeading { font-size:30px; font-weight:800; color:#18364F; }
QLabel#coreResult { font-size:26px; font-weight:600; color:#18364F; }
QLabel#muted { color:#698198; font-size:13px; }
QFrame#sidebar { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #E6F2FC,stop:0.5 #EDF6FD,stop:1 #E6F2FB); border-right:1px solid #DAE7F1; }
QListWidget#navigation { background:transparent; border:0; outline:0; }
QListWidget#navigation::item { min-height:46px; padding:0 10px; margin:3px 0; border-radius:9px; }
QListWidget#navigation::item:selected { background:#D6EBF9; color:#116FAE; border-left:3px solid #298CCB; }
QListWidget#navigation::item:focus { border:1px solid #298CCB; }
QPushButton { background:white; border:1px solid #DAE7F1; border-radius:6px; padding:8px 14px; min-height:22px; }
QPushButton:hover { background:#EAF4FC; border-color:#197CC2; }
QPushButton:checked { background:#D6EBF9; color:#116FAE; border-color:#298CCB; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus { border:2px solid #197CC2; }
QPushButton:disabled { color:#698198; background:#F0F4F8; }
QPushButton[primary="true"] { background:#197CC2; color:white; border-color:#197CC2; }
QPushButton#taskCard { text-align:left; background:white; border-radius:14px; padding:22px; font-size:16px; }
QPushButton#taskCard[primary="true"] { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #174E7C,stop:1 #197CC2); color:white; }
QLineEdit, QComboBox { background:white; border:1px solid #DAE7F1; border-radius:6px; min-height:24px; padding:7px 10px; selection-background-color:#D6EBF9; }
QComboBox:disabled, QLineEdit:disabled { background:#F0F4F8; color:#526A7D; }
QComboBox::drop-down { border:0; width:24px; }
QComboBox::down-arrow { image:url(__ARROW__); width:16px; height:16px; }
QGroupBox { background:white; border:1px solid #DAE7F1; border-radius:10px; margin-top:12px; padding:20px 14px 12px; }
QGroupBox::title { subcontrol-origin:margin; left:16px; color:#18364F; font-size:16px; font-weight:600; }
QTableWidget, QListWidget { background:white; border:1px solid #DAE7F1; border-radius:6px; alternate-background-color:#F7FAFD; selection-background-color:#D6EBF9; selection-color:#18364F; }
QHeaderView::section { background:#F7FAFD; border:0; border-bottom:1px solid #DAE7F1; padding:12px 8px; color:#526A7D; }
QTableWidget::item { padding:8px; border-bottom:1px solid #EEF3F8; }
QScrollArea { border:0; }
QToolTip { background:white; color:#213A4F; border:1px solid #DAE7F1; }
""".replace("__ARROW__", (ASSETS / "chevron-down.svg").as_posix())
