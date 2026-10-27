"""Native choices with whole-field opening and scroll-safe closed state."""
from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QComboBox, QScrollArea


class ChoiceComboBox(QComboBox):
    _pressed = False
    def setEditable(self, editable):
        super().setEditable(editable)
        if self.lineEdit() is not None:
            self.lineEdit().installEventFilter(self)

    def wheelEvent(self, event):
        if self.view().isVisible():
            super().wheelEvent(event)
        else:
            self._scroll_page(event)

    def _scroll_page(self, event):
        ancestor = self.parentWidget()
        while ancestor is not None:
            if isinstance(ancestor, QScrollArea):
                viewport = ancestor.viewport()
                local = QPointF(viewport.mapFromGlobal(event.globalPosition().toPoint()))
                forwarded = QWheelEvent(local, event.globalPosition(), event.pixelDelta(), event.angleDelta(),
                    event.buttons(), event.modifiers(), event.phase(), event.inverted())
                QApplication.sendEvent(viewport, forwarded)
                event.setAccepted(forwarded.isAccepted())
                return
            ancestor = ancestor.parentWidget()
        event.ignore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.view().isVisible():
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self._pressed = True
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._pressed and event.button() == Qt.MouseButton.LeftButton:
            self._pressed = False
            self._open_after_release()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _open_after_release(self):
        # Finish the whole-field click before opening the native popup;
        # retain the platform's normal popup animation and keyboard behavior.
        QTimer.singleShot(0, self, self._show_if_available)

    def _show_if_available(self):
        if self.isVisible() and self.isEnabled():
            self.showPopup()

    def eventFilter(self, watched, event):
        if watched is self.lineEdit():
            if event.type() == QEvent.Type.Wheel and not self.view().isVisible():
                self._scroll_page(event)
                return True
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self.setFocus(Qt.FocusReason.MouseFocusReason)
                self._pressed = True
                return True
            if event.type() == QEvent.Type.MouseButtonRelease and self._pressed and event.button() == Qt.MouseButton.LeftButton:
                self._pressed = False
                self._open_after_release()
                return True
        return super().eventFilter(watched, event)
