"""无侧栏任务首页，最近记录来自正式服务。"""
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                              QLabel, QPushButton, QListWidget, QListWidgetItem, QScrollArea,
                              QStyleOptionButton, QStyle, QStylePainter, QSizePolicy)
from ....application.services.centrifugal_pump_analysis_service import user_conclusion_from_snapshot
from ..style import brand, icon


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
        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)
        symbol_label = QLabel()
        symbol_label.setPixmap(icon(symbol, "#FFFFFF" if primary else "#197CC2").pixmap(28, 28))
        layout.addWidget(symbol_label)
        text = QVBoxLayout()
        text.setSpacing(10)
        title = QLabel(name)
        title.setObjectName("taskTitle")
        description_label = QLabel(description)
        description_label.setObjectName("taskDescription")
        for label in (title, description_label):
            label.setWordWrap(True)
            text.addWidget(label)
        layout.addLayout(text, 1)
        for label in self.findChildren(QLabel):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def sizeHint(self):
        return QSize(260, 180)

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
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)
        bar = QHBoxLayout()
        bar.addWidget(brand())
        bar.addStretch()
        settings = QPushButton("设置")
        settings.setIcon(icon("settings"))
        settings.clicked.connect(lambda: navigator.open_settings() if navigator else None)
        bar.addWidget(settings)
        layout.addLayout(bar)
        title = QLabel("设备能效分析工具")
        title.setObjectName("homeHeading")
        title.setWordWrap(True)
        layout.addWidget(title)
        subtitle = QLabel("查询标准，完成设备分析与批量评价")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
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
        row = QHBoxLayout()
        row.addWidget(QLabel("最近分析记录"))
        row.addStretch()
        all_records = QPushButton("查看全部")
        all_records.clicked.connect(lambda: navigator.open_records() if navigator else None)
        row.addWidget(all_records)
        layout.addLayout(row)
        self.records = QListWidget()
        self.records.setMinimumHeight(180)
        self.records.itemActivated.connect(self._open_record_item)
        layout.addWidget(self.records)
        self.record_status = QLabel()
        self.record_status.setWordWrap(True)
        layout.addWidget(self.record_status)
        self.retry_button = QPushButton("重试")
        self.retry_button.clicked.connect(self.refresh)
        layout.addWidget(self.retry_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)
        self._columns = 0
        self.refresh()

    def resizeEvent(self, event):
        columns = 4 if self.width() >= 1200 else 2 if self.width() >= 700 else 1
        if columns != self._columns:
            self._columns = columns
            for index, button in enumerate(self.task_buttons):
                self.cards.addWidget(button, index // columns, index % columns)
            for column in range(4):
                self.cards.setColumnStretch(column, (147 if column == 0 else 100) if column < columns else 0)
        super().resizeEvent(event)

    def refresh(self):
        self.records.clear()
        self._record_ids = []
        try:
            records = self.service.list_records(limit=5)
        except Exception:
            self.record_status.setText("暂时无法读取记录")
            self.retry_button.show()
            return
        self.retry_button.hide()
        self.record_status.setText("" if records else "尚无分析记录，可点击「新建分析」开始。")
        for record in records:
            values = getattr(record, "input_snapshot", None) or {}
            name = values.get("project_name") or values.get("equipment_no") or record.product_category
            conclusion = user_conclusion_from_snapshot(
                {"grade": record.grade, "evaluation_status": record.evaluation_status}, record.ui_conclusion)
            item = QListWidgetItem(f"{name}　 ·　{conclusion}　 ·　{record.as_of}")
            item.setToolTip(record.record_id)
            item.setSizeHint(QSize(0, 42))
            self.records.addItem(item)
            self._record_ids.append(record.record_id)

    def _start_new_analysis(self):
        if self.navigator:
            self.navigator.open_analysis()

    def _open_standard(self):
        if self.navigator:
            self.navigator.open_standards()

    def _open_record_item(self, item):
        self._open_record(self.records.row(item))

    def _open_record(self, row):
        if self.navigator and 0 <= row < len(self._record_ids):
            self.navigator.open_records(record_id=self._record_ids[row])
