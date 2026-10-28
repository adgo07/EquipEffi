"""可换行列表：默认48 DIP，长中文按内容增加行高。"""
from PySide6.QtCore import QEvent, QTimer, Qt, QRect
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QTableWidget, QHeaderView


class CompactTable(QTableWidget):
    def __init__(self, headers, narrow_widths, compact_widths, parent=None):
        super().__init__(0, len(headers), parent)
        self.narrow_widths, self.compact_widths = narrow_widths, compact_widths
        self.setHorizontalHeaderLabels(headers)
        self.setWordWrap(True)
        self.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.verticalHeader().hide()
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.verticalHeader().setMinimumSectionSize(48)
        self.verticalHeader().setDefaultSectionSize(48)
        self.horizontalHeader().setMinimumSectionSize(28)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.horizontalHeader().setTextElideMode(Qt.TextElideMode.ElideRight)
        for index, title in enumerate(headers):
            self.horizontalHeaderItem(index).setToolTip(title)
        self.setStyleSheet("QTableWidget {font-size:13px;} QTableWidget::item {padding:5px;} "
            "QHeaderView::section {padding:7px 4px; font-size:13px;} "
            "QPushButton {min-height:24px; max-height:24px; padding:0 6px; font-size:13px;}")
        self.fit_content_height = False
        self._fit_timer = QTimer(self)
        self._fit_timer.setSingleShot(True)
        self._fit_timer.timeout.connect(self.fit_columns)
        self.viewport().installEventFilter(self)
        self.fit_columns()
        self.itemChanged.connect(lambda *_: self._fit_timer.start(0))
        self.horizontalHeader().sectionResized.connect(lambda *_: self._fit_timer.start(0))

    def setItem(self, row, column, item):
        item.setToolTip(item.text())
        super().setItem(row, column, item)
        # Initial insertion need not emit itemChanged on every Qt/model path.
        self._fit_timer.start(0)

    def changeEvent(self, event):
        super().changeEvent(event)
        if hasattr(self, "_fit_timer") and event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._fit_timer.start(0)

    def eventFilter(self, watched, event):
        if watched is self.viewport() and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self._fit_timer.start(0)
        return super().eventFilter(watched, event)

    def fit_columns(self):
        available = self.viewport().width()
        if available < 640:
            widths = self.narrow_widths
        else:
            remaining = available - sum(self.compact_widths)
            # Give surplus space to descriptive columns; keep actions reachable.
            weights = [max(width - 60, 0) for width in self.compact_widths]
            total = sum(weights) or 1
            widths = [base + remaining * weight // total for base, weight in zip(self.compact_widths, weights)]
            widths[1] += available - sum(widths)
        for index, width in enumerate(widths):
            if self.columnWidth(index) != width:
                self.setColumnWidth(index, width)
        self.resizeRowsToContents()

    def resizeRowsToContents(self):
        """所有列表加载路径都使用同一测量，不能再被Qt默认测量覆盖。"""
        self.ensurePolished()
        # Qt's stock sizeHintForRow may ignore wrapping under a stylesheet.
        # Measure against the final column width, including Chinese breakpoints.
        metrics = QFontMetrics(self.font())
        for row in range(self.rowCount()):
            height = 48
            for column in range(self.columnCount()):
                item = self.item(row, column)
                if item is not None:
                    bounds = QRect(0, 0, max(1, self.columnWidth(column) - 20), 100000)
                    required = metrics.boundingRect(bounds, Qt.TextFlag.TextWordWrap, item.text()).height() + 16
                    height = max(height, required)
            if self.rowHeight(row) != height:
                self.setRowHeight(row, height)
        if self.fit_content_height:
            height = sum(self.rowHeight(row) for row in range(self.rowCount()))
            height += self.horizontalHeader().height() + self.frameWidth() * 2
            if self.horizontalScrollBar().maximum() > 0:
                height += self.horizontalScrollBar().sizeHint().height()
            self.setFixedHeight(height)
