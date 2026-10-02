"""分析记录（History / Reopen）页（Phase 3 P3-G02/G03）。

清水泵与石油化工泵记录出现在**同一个列表**；打开记录只读原快照，
不重新计算。
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

from ....application.services.centrifugal_pump_analysis_service import (
    CentrifugalPumpAnalysisService,
)
from ..tokens import TOKENS


class RecordsPage(QWidget):
    """正式记录历史页。"""

    def __init__(self, service: CentrifugalPumpAnalysisService):
        super().__init__()
        self.service = service
        self._records: list = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(TOKENS.page_margin,) * 4)
        layout.setSpacing(TOKENS.section_gap)

        heading = QLabel("分析记录")
        font = heading.font()
        font.setPixelSize(TOKENS.title_font_size)
        heading.setFont(font)
        layout.addWidget(heading)

        holder = QHBoxLayout()
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._on_selected)
        holder.addWidget(self.list, 2)

        detail_group = QGroupBox("记录详情")
        detail_layout = QVBoxLayout(detail_group)
        self.detail = QLabel("请选择一条记录。")
        self.detail.setWordWrap(True)
        self.detail.setTextFormat(Qt.TextFormat.PlainText)
        self.detail.setAlignment(Qt.AlignmentFlag.AlignTop)
        detail_layout.addWidget(self.detail)
        detail_layout.addStretch()
        holder.addWidget(detail_group, 3)
        layout.addLayout(holder, 1)

        buttons = QHBoxLayout()
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh)
        buttons.addWidget(self.refresh_button)
        buttons.addStretch()
        layout.addLayout(buttons)

    def refresh(self) -> None:
        self._records = list(self.service.list_records())
        self.list.clear()
        for record in self._records:
            item = QListWidgetItem(
                f"{record.finalized_at_utc[:10]} | {record.standard_code} | "
                f"{record.product_category} | {record.ui_conclusion}"
            )
            self.list.addItem(item)
        if not self._records:
            self.detail.setText("尚无正式记录。完成一次分析并保存后会显示在这里。")

    def _on_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._records):
            return
        self.show_record(self._records[row].record_id)

    def show_record(self, record_id: str) -> str:
        """Reopen：只读原快照，不调用 evaluator、不按今天日期重算。"""

        snapshot = self.service.open_record(record_id)
        result = snapshot.result_snapshot
        lines = [
            f"记录编号：{snapshot.record_id}",
            f"采用标准：{snapshot.standard_code}",
            f"设备类别：{snapshot.product_category}",
            f"评价日期：{snapshot.as_of}",
            f"评价结论：{snapshot.ui_conclusion}",
        ]
        if snapshot.grade:
            lines.append(f"能效等级：{snapshot.grade}")
        if snapshot.evaluation_status:
            lines.append(f"评价状态：{snapshot.evaluation_status}")
        input_snapshot = snapshot.input_snapshot
        lines.append("原输入：" + "；".join(
            f"{key} {input_snapshot[key]}"
            for key in ("QBEP", "HBEP", "speed", "efficiency", "suction", "stages")
            if input_snapshot.get(key) not in (None, "")))
        thresholds = result.get("thresholds") or {}
        if thresholds:
            lines.append("原等级阈值：" + "；".join(
                f"{name} {value}" for name, value in thresholds.items()))
        derived = (result.get("calculation_trace") or {}).get("derived") or {}
        if derived:
            lines.append("原关键计算参数：" + "；".join(
                f"{name} {value}" for name, value in derived.items()))
        if result.get("matched_rule_id"):
            lines.append(f"原标准依据：GB 19762—2025（命中规则 {result['matched_rule_id']}）")
        lines.append(f"保存时间：{snapshot.finalized_at_utc}")
        text = "\n".join(lines)
        self.detail.setText(text)
        return text
