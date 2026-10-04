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
    """开始新分析 / 继续最近草稿 / 打开最近正式记录 / 查看当前正式标准。"""

    def __init__(self, service, navigator=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        self.navigator = navigator
        self._draft_ids: list[str] = []
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

        drafts_group = QGroupBox("继续最近的草稿")
        drafts_layout = QVBoxLayout(drafts_group)
        self.drafts = QListWidget()
        self.drafts.itemDoubleClicked.connect(self._open_draft_item)
        drafts_layout.addWidget(self.drafts)
        self.resume_button = QPushButton("继续选中的草稿")
        self.resume_button.clicked.connect(self._resume_selected_draft)
        drafts_layout.addWidget(self.resume_button)
        layout.addWidget(drafts_group)

        records_group = QGroupBox("最近的正式记录")
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
        """刷新标准信息、最近草稿与最近记录。"""

        overview = self.service.standard_overview()
        self.standard_label.setText(
            f"当前正式标准：{overview['standard_code']}《{overview['standard_name']}》\n"
            f"实施日期：{overview['effective_date'] or '—'}"
        )

        self._draft_ids = []
        self.drafts.clear()
        for workspace in self.service.list_workspaces(limit=5):
            label = f"{workspace.workspace_id}　{workspace.product_category}"
            if workspace.updated_at_utc:
                label += f"　更新于 {workspace.updated_at_utc}"
            self.drafts.addItem(QListWidgetItem(label))
            self._draft_ids.append(workspace.workspace_id)

        self._record_ids = []
        self.records.clear()
        for record in self.service.list_records(limit=5):
            grade = f"{record.grade}" if record.grade else record.ui_conclusion
            self.records.addItem(QListWidgetItem(
                f"{record.record_id}　{record.product_category}　{grade}"
                f"　{record.as_of}"))
            self._record_ids.append(record.record_id)

        has_drafts = bool(self._draft_ids)
        self.resume_button.setEnabled(has_drafts)
        if not has_drafts:
            self.drafts.addItem(QListWidgetItem("暂无草稿"))

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

    def _open_draft_item(self, item: QListWidgetItem) -> None:
        self._open_draft(self.drafts.row(item))

    def _resume_selected_draft(self) -> None:
        self._open_draft(self.drafts.currentRow())

    def _open_draft(self, row: int) -> None:
        if 0 <= row < len(self._draft_ids) and self.navigator is not None:
            self.navigator.open_analysis(workspace_id=self._draft_ids[row])

    def _open_record_item(self, item: QListWidgetItem) -> None:
        self._open_record(self.records.row(item))

    def _open_selected_record(self) -> None:
        self._open_record(self.records.currentRow())

    def _open_record(self, row: int) -> None:
        if 0 <= row < len(self._record_ids) and self.navigator is not None:
            self.navigator.open_records(record_id=self._record_ids[row])
