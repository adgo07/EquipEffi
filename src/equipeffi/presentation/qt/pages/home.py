"""无侧栏任务首页，最近记录来自正式服务。"""
import logging
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
                              QLabel, QPushButton, QTableWidgetItem, QScrollArea, QAbstractItemView,
                              QStyleOptionButton, QStyle, QStylePainter, QSizePolicy)
from ....application.services.centrifugal_pump_analysis_service import user_conclusion_from_snapshot
from ..style import brand, icon
from ..widgets.page_layout import page_gutter
from ..widgets.compact_table import CompactTable


class TaskCard(QPushButton):
    """保留原生按钮键盘/焦点行为，标题与说明分别排版。"""

    def __init__(self, name, description, symbol, primary=False):
        super().__init__(f"{name}\n{description}")
        self.setObjectName("taskCard")
        self.setProperty("primary", primary)
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setAccessibleName(name)
        self.setAccessibleDescription(description)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(12)
        symbol_label = QLabel()
        symbol_label.setPixmap(icon(symbol, "#FFFFFF" if primary else "#197CC2").pixmap(36, 36))
        layout.addWidget(symbol_label, alignment=Qt.AlignmentFlag.AlignLeft)
        text = QVBoxLayout()
        text.setSpacing(10)
        title = QLabel(name)
        title.setObjectName("taskTitle")
        title.setProperty("onPrimary", primary)
        description_label = QLabel(description)
        description_label.setObjectName("taskDescription")
        description_label.setProperty("onPrimary", primary)
        for label in (title, description_label):
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            text.addWidget(label)
        layout.addLayout(text)
        for label in self.findChildren(QLabel):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def sizeHint(self):
        return QSize(200, 172)

    def minimumSizeHint(self):
        return QSize(0, 150)

    def paintEvent(self, event):
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.text = ""
        option.icon = QIcon()
        painter = QStylePainter(self)
        painter.drawControl(QStyle.ControlElement.CE_PushButton, option)


class HomePage(QWidget):
    def __init__(self, service, navigator=None, parent=None, *, transformer=None, motor=None):
        super().__init__(parent)
        self.service, self.navigator = service, navigator
        self._record_ids = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        page_gutter(layout, scroll.viewport())
        layout.setSpacing(24)
        bar = QHBoxLayout()
        self.brand = brand()
        self.brand.setFixedWidth(180)
        bar.addWidget(self.brand)
        divider = QFrame()
        divider.setFixedSize(1, 60)
        divider.setStyleSheet("background:#BAD0E0;")
        bar.addWidget(divider)
        titles = QVBoxLayout()
        title = QLabel("设备能效分析工具")
        title.setObjectName("homeHeading")
        title.setWordWrap(True)
        title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        titles.addWidget(title)
        subtitle = QLabel("查询标准，完成设备分析与批量评价")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        subtitle.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        titles.addWidget(subtitle)
        bar.addLayout(titles, 1)
        settings = QPushButton("设置")
        settings.setIcon(icon("settings"))
        settings.clicked.connect(lambda: navigator.open_settings() if navigator else None)
        bar.addWidget(settings)
        layout.addLayout(bar)
        self.cards = QGridLayout()
        self.cards.setSpacing(14)
        self.task_buttons = []
        for name, description, symbol, action in (
            ("标准库", "查询标准与适用范围", "book", self._open_standard),
            ("新建分析", "填写设备参数并分析", "plus", self._start_new_analysis),
            ("表格导入", "统一工作簿批量评价", "excel", lambda: navigator.open_batch() if navigator else None),
            ("分析记录", "查看已保存的分析结果", "records", lambda: navigator.open_records() if navigator else None),
        ):
            button = TaskCard(name, description, symbol, primary=not self.task_buttons)
            button.clicked.connect(action)
            self.task_buttons.append(button)
        layout.addLayout(self.cards)
        self.recent_card = QFrame()
        self.recent_card.setObjectName("homeRecent")
        self.recent_card.setStyleSheet("QFrame#homeRecent {background:white; border:1px solid #DAE7F1; border-radius:12px;}")
        recent = QVBoxLayout(self.recent_card)
        recent.setContentsMargins(18, 16, 18, 16)
        row = QHBoxLayout()
        recent_title = QLabel("最近分析记录")
        recent_title.setStyleSheet("font-size:16px; font-weight:600;")
        row.addWidget(recent_title)
        row.addStretch()
        all_records = QPushButton("查看全部")
        all_records.clicked.connect(lambda: navigator.open_records() if navigator else None)
        row.addWidget(all_records)
        recent.addLayout(row)
        self.records = CompactTable(["设备/项目", "采用标准", "结论", "评价日期", "操作"],
                                    [210, 160, 100, 115, 68], [200, 180, 75, 110, 62])
        self.records.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.records.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.records.cellActivated.connect(lambda row, column: self._open_record(row))
        self.records.cellDoubleClicked.connect(lambda row, column: self._open_record(row))
        recent.addWidget(self.records)
        self.record_status = QLabel()
        self.record_status.setWordWrap(True)
        self.record_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.record_status.setMinimumHeight(64)
        recent.addWidget(self.record_status)
        self.retry_button = QPushButton("重试")
        self.retry_button.clicked.connect(self.refresh)
        recent.addWidget(self.retry_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.recent_card)
        layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)
        self._columns = 0
        self.refresh()

    def resizeEvent(self, event):
        self.brand.setFixedWidth(180)
        columns = 4 if self.width() >= 900 else 2 if self.width() >= 540 else 1
        if columns != self._columns:
            self._columns = columns
            for index, button in enumerate(self.task_buttons):
                self.cards.addWidget(button, index // columns, index % columns)
            for column in range(4):
                self.cards.setColumnStretch(column, 1 if column < columns else 0)
        super().resizeEvent(event)

    def refresh(self):
        self.records.setRowCount(0)
        self.records.hide()
        self.record_status.show()
        self._record_ids = []
        try:
            records = self.service.list_records(limit=5)
        except Exception:
            logging.getLogger("equipeffi.qt.home").exception("最近分析记录读取失败")
            self.record_status.setText("暂时无法读取记录")
            self.retry_button.show()
            return
        self.retry_button.hide()
        self.records.setVisible(bool(records))
        self.record_status.setVisible(not records)
        self.records.setRowCount(len(records))
        self.records.fit_content_height = True
        self.record_status.setText("" if records else "尚无分析记录，可点击「新建分析」开始。")
        for row, record in enumerate(records):
            values = getattr(record, "input_snapshot", None) or {}
            name = values.get("project_name") or values.get("equipment_no") or record.product_category
            conclusion = user_conclusion_from_snapshot(
                {"grade": record.grade, "evaluation_status": record.evaluation_status}, record.ui_conclusion)
            self._record_ids.append(record.record_id)
            for column, value in enumerate((name, record.standard_code, conclusion, record.as_of)):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, record.record_id)
                self.records.setItem(row, column, item)
            button = QPushButton("打开")
            button.clicked.connect(lambda checked=False, index=row: self._open_record(index))
            self.records.setCellWidget(row, 4, button)

    def _start_new_analysis(self):
        if self.navigator:
            self.navigator.open_analysis()

    def _open_standard(self):
        if self.navigator:
            self.navigator.open_standards()

    def _open_record(self, row):
        if self.navigator and 0 <= row < len(self._record_ids):
            self.navigator.open_records(record_id=self._record_ids[row])
