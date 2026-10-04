"""首页：只承载真实高价值任务。

复用现有 `list_workspaces()` / `list_records()`；**不新增** records schema，
也**不建立**第二套 persistence。刻意不做 KPI / Dashboard / 无业务价值图表。
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..tokens import TOKENS


class HomePage(QWidget):
    """开始新分析 / 打开最近历史记录 / 查看当前正式标准。

Phase 7：普通用户界面没有「分析草稿」概念，因此本页不提供草稿入口；
每次「分析」都会自动形成一条历史记录，本页直接列出最近记录。
"""

    def __init__(self, service, navigator=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        self.navigator = navigator
        self._record_ids: list[str] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(TOKENS.page_margin,) * 4)
        layout.setSpacing(TOKENS.section_gap)

        heading = QLabel("首页")
        font = heading.font()
        font.setPixelSize(TOKENS.title_font_size)
        font.setBold(True)
        heading.setFont(font)
        layout.addWidget(heading)

        self.standard_label = QLabel()
        self.standard_label.setWordWrap(True)
        self.standard_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.standard_label)

        primary = QHBoxLayout()
        self.new_analysis_button = QPushButton("开始新的离心泵分析")
        self.new_analysis_button.clicked.connect(self._start_new_analysis)
        primary.addWidget(self.new_analysis_button)
        self.open_standard_button = QPushButton("查看当前正式标准")
        self.open_standard_button.clicked.connect(self._open_standard)
        primary.addWidget(self.open_standard_button)
        primary.addStretch()
        layout.addLayout(primary)

        records_group = QGroupBox("最近的历史记录")
        records_layout = QVBoxLayout(records_group)
        self.records = QListWidget()
        self.records.itemDoubleClicked.connect(self._open_record_item)
        records_layout.addWidget(self.records)
        self.open_record_button = QPushButton("打开选中的记录")
        self.open_record_button.clicked.connect(self._open_selected_record)
        records_layout.addWidget(self.open_record_button)
        layout.addWidget(records_group)

        layout.addStretch()
        self.refresh()

    # -- 数据 ---------------------------------------------------------------

    def refresh(self) -> None:
        """刷新标准信息与最近历史记录。"""

        overview = self.service.standard_overview()
        self.standard_label.setText(
            f"当前正式标准：{overview['standard_code']}《{overview['standard_name']}》\n"
            f"实施日期：{overview['effective_date'] or '—'}"
        )

        self._record_ids = []
        self.records.clear()
        for record in self.service.list_records(limit=5):
            grade = f"{record.grade}" if record.grade else record.ui_conclusion
            self.records.addItem(QListWidgetItem(
                f"{record.record_id}　{record.product_category}　{grade}"
                f"　{record.as_of}"))
            self._record_ids.append(record.record_id)

        has_records = bool(self._record_ids)
        self.open_record_button.setEnabled(has_records)
        if not has_records:
            self.records.addItem(QListWidgetItem("暂无正式记录"))

    # -- 动作 ---------------------------------------------------------------

    def _start_new_analysis(self) -> None:
        if self.navigator is not None:
            self.navigator.open_analysis()

    def _open_standard(self) -> None:
        if self.navigator is not None:
            self.navigator.open_standards()

    def _open_record_item(self, item: QListWidgetItem) -> None:
        self._open_record(self.records.row(item))

    def _open_selected_record(self) -> None:
        self._open_record(self.records.currentRow())

    def _open_record(self, row: int) -> None:
        if 0 <= row < len(self._record_ids) and self.navigator is not None:
            self.navigator.open_records(record_id=self._record_ids[row])
