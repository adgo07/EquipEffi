"""就近补充说明气泡；必要输入和操作后果仍留在页面正文。"""
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtWidgets import QApplication, QFrame, QWidget, QVBoxLayout, QPushButton, QLabel
from ..style import icon


class SupplementaryInfo(QWidget):
    def __init__(self, name, text="", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.toggle_button = QPushButton(name)
        self.toggle_button.setIcon(icon("info"))
        self.toggle_button.setAccessibleName(name)
        self.toggle_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setProperty("role", "light")
        layout.addWidget(self.toggle_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.popup = QFrame(self, Qt.WindowType.Popup)
        self.popup.setAttribute(Qt.WidgetAttribute.WA_NoMouseReplay)
        self.popup.setAccessibleName(name)
        popup_layout = QVBoxLayout(self.popup)
        self.content = QLabel()
        self.content.setWordWrap(True)
        self.content.setMaximumWidth(360)
        self.content.setMinimumWidth(240)
        self.content.setTextFormat(Qt.TextFormat.PlainText)
        popup_layout.addWidget(self.content)
        self.close_button = QPushButton("关闭说明")
        self.close_button.clicked.connect(self.popup.hide)
        popup_layout.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignRight)
        self.popup.installEventFilter(self)
        self.close_button.installEventFilter(self)
        self.toggle_button.clicked.connect(self._toggle)
        self.set_content(text)

    def _toggle(self, checked):
        if not checked:
            self.popup.hide()
            return
        self.popup.adjustSize()
        anchor = self.toggle_button.mapToGlobal(QPoint(0, self.toggle_button.height()))
        screen = QApplication.screenAt(anchor) or self.toggle_button.screen()
        bounds = screen.availableGeometry()
        x = max(bounds.left(), min(anchor.x(), bounds.right() - self.popup.width() + 1))
        y = anchor.y()
        if y + self.popup.height() > bounds.bottom() + 1:
            y = self.toggle_button.mapToGlobal(QPoint(0, 0)).y() - self.popup.height()
        y = max(bounds.top(), min(y, bounds.bottom() - self.popup.height() + 1))
        self.popup.move(x, y)
        self.popup.show()
        self.close_button.setFocus()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.popup.hide()
            return True
        if watched is self.popup and event.type() == QEvent.Type.Hide:
            self.toggle_button.setChecked(False)
            self.toggle_button.setFocus()
        return super().eventFilter(watched, event)

    def set_content(self, text):
        self.popup.hide()
        self.content.setText(text)
        self.toggle_button.setChecked(False)
        self.setVisible(bool(text.strip()))
