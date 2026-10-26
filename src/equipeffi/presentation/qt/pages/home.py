"""无侧栏任务首页，最近记录来自正式服务。"""
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                              QLabel, QPushButton, QListWidget, QListWidgetItem, QScrollArea)
from ....application.services.centrifugal_pump_analysis_service import user_conclusion_from_snapshot
from ..style import brand, icon


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
            button = QPushButton(f"{name}\n\n{description}   →")
            button.setObjectName("taskCard")
            button.setIcon(icon(symbol, "#FFFFFF" if not self.task_buttons else "#197CC2"))
            button.setIconSize(QSize(28, 28))
            button.setMinimumHeight(150)
            button.setProperty("primary", not self.task_buttons)
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
