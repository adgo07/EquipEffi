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
    QToolBox,
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

        # 技术详情渐进展示：内部 rule / data id / Numeric 配置归此处，默认折叠。
        self.technical_box = QToolBox()
        technical_page = QWidget()
        technical_layout = QVBoxLayout(technical_page)
        self.technical = QLabel("")
        self.technical.setWordWrap(True)
        self.technical.setTextFormat(Qt.TextFormat.PlainText)
        self.technical.setAlignment(Qt.AlignmentFlag.AlignTop)
        technical_layout.addWidget(self.technical)
        technical_layout.addStretch()
        self.technical_box.addItem(technical_page, "技术详情（规则编号、数据版本、数值配置）")
        self.technical_box.setCurrentIndex(-1)
        detail_layout.addWidget(self.technical_box)
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
        input_snapshot = snapshot.input_snapshot

        # 业务详情：面向用户，不出现内部 rule / data id / profile 名。
        lines = [
            f"记录编号：{snapshot.record_id}",
            f"采用标准：{snapshot.standard_code}",
            f"设备类别：{snapshot.product_category}",
            f"评价日期：{snapshot.as_of}",
            f"评价结论：{snapshot.ui_conclusion}",
        ]
        if snapshot.grade:
            lines.append(f"能效等级：{snapshot.grade}")
        for label, key in (("规定点流量 Q_BEP（m³/h）", "QBEP"),
                           ("规定点扬程 H_BEP（m）", "HBEP"),
                           ("规定点转速 n（r/min）", "speed"),
                           ("规定点泵效率 η（%）", "efficiency"),
                           ("吸入方式", "suction"), ("级数", "stages")):
            value = input_snapshot.get(key)
            if value not in (None, ""):
                lines.append(f"{label}：{value}")
        if input_snapshot.get("project_name"):
            lines.append(f"企业/项目名称：{input_snapshot['project_name']}")
        if input_snapshot.get("equipment_no"):
            lines.append(f"设备编号：{input_snapshot['equipment_no']}")
        thresholds = result.get("thresholds") or {}
        if thresholds:
            lines.append("原等级阈值：" + "；".join(
                f"{name} {value}" for name, value in thresholds.items()))
        derived = (result.get("calculation_trace") or {}).get("derived") or {}
        if derived:
            lines.append("原关键计算参数：" + "；".join(
                f"{name} {value}" for name, value in derived.items()))
        lines.append("原标准依据：GB 19762—2025《离心泵能效限定值及能效等级》")
        lines.append(f"保存时间：{snapshot.finalized_at_utc}")
        text = "\n".join(lines)
        self.detail.setText(text)
        self._render_technical(snapshot, result)
        return text

    def _render_technical(self, snapshot, result) -> None:
        """技术详情：审计需要的内部标识集中在此，不进入普通业务详情。"""

        standard = snapshot.reference_snapshot.get("standard") or {}
        rows = [
            ("评价状态", snapshot.evaluation_status or "—"),
            ("命中规则", result.get("matched_rule_id") or "—"),
            ("类别状态", result.get("category_status") or "—"),
            ("规则集", standard.get("rule_profile") or "—"),
            ("标准包", standard.get("pack_id") or "—"),
            ("数据版本", snapshot.canonical_version or "—"),
            ("数值配置", snapshot.numeric_profile_id or "—"),
            ("结果契约", snapshot.result_contract_version or "—"),
            ("输入指纹", snapshot.input_snapshot.get("request_fingerprint") or "—"),
            ("草稿修订号", snapshot.input_snapshot.get("workspace_revision", "—")),
        ]
        self.technical.setText("\n".join(f"{name}：{value}" for name, value in rows))
