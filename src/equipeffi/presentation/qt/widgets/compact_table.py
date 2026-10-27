"""Single-line, full-text-preserving tables; fit columns at ordinary widths."""
from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtWidgets import QTableWidget, QHeaderView


class CompactTable(QTableWidget):
    def __init__(self, headers, narrow_widths, compact_widths, parent=None):
        super().__init__(0, len(headers), parent)
        self.narrow_widths, self.compact_widths = narrow_widths, compact_widths
        self.setHorizontalHeaderLabels(headers)
        self.setWordWrap(False)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.verticalHeader().hide()
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.verticalHeader().setMinimumSectionSize(40)
        self.verticalHeader().setMaximumSectionSize(40)
        self.verticalHeader().setDefaultSectionSize(40)
        self.horizontalHeader().setMinimumSectionSize(28)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.horizontalHeader().setTextElideMode(Qt.TextElideMode.ElideRight)
        for index, title in enumerate(headers):
            self.horizontalHeaderItem(index).setToolTip(title)
        self.setStyleSheet("QTableWidget {font-size:13px;} QTableWidget::item {padding:5px;} "
            "QHeaderView::section {padding:7px 4px; font-size:13px;} "
            "QPushButton {min-height:0; padding:3px 6px; font-size:13px;}")
        self._fit_timer = QTimer(self)
        self._fit_timer.setSingleShot(True)
        self._fit_timer.timeout.connect(self.fit_columns)
        self.viewport().installEventFilter(self)
        self.fit_columns()

    def setItem(self, row, column, item):
        item.setToolTip(item.text())
        super().setItem(row, column, item)

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
