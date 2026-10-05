"""分析记录（History / Reopen）页。

清水泵与石油化工泵记录出现在**同一个列表**；打开记录只读原快照，
不重新计算、不追溯改写当时的支持状态。

Phase 6 补齐搜索与筛选。筛选只作用于**快照里已有的字段**，
不新增 schema、不重算、不修改历史记录。
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
from ....application.services.centrifugal_pump_analysis_service import (
    THRESHOLD_DISPLAY_NAMES,
    user_conclusion_from_snapshot,
)
from ..labels import support_status_text
from ..labels import format_metric
from ..widgets.collapsible import CollapsibleSection

#: 结论筛选项 → 匹配的 evaluation_status 集合（"全部" 不筛选）。
CONCLUSION_FILTERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("全部结论", ()),
    ("已判定等级", ("SUCCESS",)),
    ("不适用（超出标准范围）", ("OUT_OF_STANDARD_SCOPE",)),
    ("无法判定（信息不足）", ("INSUFFICIENT_DATA", "INVALID_INPUT")),
)


class RecordsPage(QWidget):
    """正式记录历史页。"""

    def __init__(self, service: CentrifugalPumpAnalysisService, navigator=None):
        super().__init__()
        self.service = service
        self.navigator = navigator
        self._records: list = []
        self._visible: list = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(TOKENS.page_margin,) * 4)
        layout.setSpacing(TOKENS.section_gap)

        heading = QLabel("分析记录")
        font = heading.font()
        font.setPixelSize(TOKENS.title_font_size)
        font.setBold(True)
        heading.setFont(font)
        layout.addWidget(heading)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("搜索"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("按记录编号、设备类别或标准搜索")
        self.search.textChanged.connect(self._apply_filters)
        filters.addWidget(self.search, 2)

        filters.addWidget(QLabel("泵型"))
        self.category_filter = QComboBox()
        self.category_filter.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(self.category_filter, 1)

        filters.addWidget(QLabel("结论"))
        self.conclusion_filter = QComboBox()
        for label, _ in CONCLUSION_FILTERS:
            self.conclusion_filter.addItem(label)
        self.conclusion_filter.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(self.conclusion_filter, 1)

        filters.addWidget(QLabel("评价日期"))
        self.date_filter = QLineEdit()
        self.date_filter.setPlaceholderText("YYYY-MM-DD")
        self.date_filter.textChanged.connect(self._apply_filters)
        filters.addWidget(self.date_filter, 1)
        layout.addLayout(filters)

        self.filter_summary = QLabel("")
        layout.addWidget(self.filter_summary)

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

        # 技术详情渐进展示：内部 rule / data id / Numeric 配置归此处，默认真正收起。
        # Phase 7：普通页面重点是业务详情；内部标识集中在最底部**默认折叠**的
        # 「审计信息」入口，保留审计能力但不再是普通页面重点。
        self.technical_box = CollapsibleSection("审计信息（技术诊断用）", expanded=False)
        self.technical = QLabel("")
        self.technical.setWordWrap(True)
        self.technical.setTextFormat(Qt.TextFormat.PlainText)
        self.technical.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.technical_box.set_content(self.technical)
        detail_layout.addWidget(self.technical_box)
        detail_layout.addStretch()
        holder.addWidget(detail_group, 3)
        layout.addLayout(holder, 1)

        buttons = QHBoxLayout()
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh)
        buttons.addWidget(self.refresh_button)
        self.clear_filters_button = QPushButton("清除筛选")
        self.clear_filters_button.clicked.connect(self.clear_filters)
        buttons.addWidget(self.clear_filters_button)
        buttons.addStretch()
        layout.addLayout(buttons)

    # -- 数据 ---------------------------------------------------------------

    def refresh(self) -> None:
        self._records = list(self.service.list_records())
        self._sync_category_filter()
        self._apply_filters()

    def _sync_category_filter(self) -> None:
        """泵型筛选项来自记录快照，不引入第二份泵型目录。"""

        current = self.category_filter.currentText()
        categories = sorted({record.product_category for record in self._records
                             if record.product_category})
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("全部泵型")
        self.category_filter.addItems(categories)
        index = self.category_filter.findText(current)
        self.category_filter.setCurrentIndex(index if index >= 0 else 0)
        self.category_filter.blockSignals(False)

    def filtered_records(self) -> list:
        """当前筛选后的记录（只读筛选已有快照字段）。"""

        keyword = self.search.text().strip().lower()
        category = self.category_filter.currentText()
        conclusion_index = max(self.conclusion_filter.currentIndex(), 0)
        statuses = CONCLUSION_FILTERS[conclusion_index][1]
        as_of = self.date_filter.text().strip()

        selected = []
        for record in self._records:
            if keyword:
                haystack = " ".join([
                    record.record_id, record.product_category, record.standard_code,
                    record.ui_conclusion,
                ]).lower()
                if keyword not in haystack:
                    continue
            if category and category != "全部泵型" and record.product_category != category:
                continue
            if statuses and record.evaluation_status not in statuses:
                continue
            if as_of and not record.as_of.startswith(as_of):
                continue
            selected.append(record)
        return selected

    def _apply_filters(self, *_args) -> None:
        self._visible = self.filtered_records()
        self.list.blockSignals(True)
        self.list.clear()
        for record in self._visible:
            grade = record.grade or record.ui_conclusion
            self.list.addItem(QListWidgetItem(
                f"{record.as_of} | {record.standard_code} | "
                f"{record.product_category} | {grade}"))
        self.list.blockSignals(False)
        self.filter_summary.setText(
            f"共 {len(self._records)} 条记录，当前显示 {len(self._visible)} 条。")
        if not self._visible:
            self.detail.setText("没有符合条件的记录。" if self._records
                                else "尚无正式记录。完成一次分析并保存后会显示在这里。")
            self.technical.setText("")

    def clear_filters(self) -> None:
        self.search.clear()
        self.date_filter.clear()
        self.conclusion_filter.setCurrentIndex(0)
        self.category_filter.setCurrentIndex(0)
        self._apply_filters()

    def _on_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._visible):
            return
        self.show_record(self._visible[row].record_id)

    def show_record(self, record_id: str) -> str:
        """Reopen：只读原快照，不调用 evaluator、不按今天日期重算。"""

        snapshot = self.service.open_record(record_id)
        result = snapshot.result_snapshot
        input_snapshot = snapshot.input_snapshot

        # 业务详情：面向用户，不出现内部 rule / data id / profile 名。
        # 全部取自**不可变快照**，因此天然是"当时"的事实，不重算、不改写。
        lines = [
            f"记录编号：{snapshot.record_id}",
            f"采用标准：{snapshot.standard_code}",
            f"设备类别：{snapshot.product_category}",
            f"评价日期：{snapshot.as_of}",
            f"评价结论：{user_conclusion_from_snapshot(result, snapshot.ui_conclusion)}",
        ]
        if snapshot.grade:
            lines.append(f"能效等级：{snapshot.grade}")
        # 冻结的判定解释与缺失信息：这是"为什么是这个结论"的唯一依据，
        # 资料不足（INSUFFICIENT_DATA）的 Record 尤其必须能看到缺了什么。
        missing = result.get("missing_fields") or []
        if missing:
            lines.append("缺失信息：" + "、".join(str(item) for item in missing))
        explanation = str(result.get("explanation") or "").strip()
        if explanation:
            lines.append(f"判定说明：{explanation}")
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
            # 只格式化**显示**；快照里的原值保持完整精度，不写回。
            lines.append("原等级阈值：" + "；".join(
                f"{THRESHOLD_DISPLAY_NAMES.get(name, name)} "
                f"{format_metric(value, name=str(name))}"
                for name, value in thresholds.items()))
        derived = (result.get("calculation_trace") or {}).get("derived") or {}
        if derived:
            # 必须保留**名称**：只显示数值串会让用户无法理解该参数是什么。
            lines.append("原关键计算参数：" + "；".join(
                f"{name} {format_metric(value, name=str(name))}"
                for name, value in derived.items()))

        # 标准依据：只展示快照里**真实存在**的依据，不伪造。
        # Phase 3～6 的旧 Record 可能未冻结这些字段，此时降级说明而不是编造。
        lines.extend(self._basis_lines(snapshot, result))
        lines.append(f"保存时间：{snapshot.finalized_at_utc}")
        text = "\n".join(lines)
        self.detail.setText(text)
        self._render_technical(snapshot, result)
        return text

    @staticmethod
    def _basis_lines(snapshot, result) -> list[str]:
        """从**快照自身**还原标准依据；缺失时降级说明，不伪造。

        只冻结运行时**真实存在且可信**的依据（标准号/名称、数据版本、
        Canonical 包哈希、命中数据 ID、表号与来源页）。不快照整张标准表、
        不建 Citation Framework、不为不存在的数据编造条款/页码。
        """

        standard = snapshot.reference_snapshot.get("standard") or {}
        lines: list[str] = []
        code = snapshot.standard_code or standard.get("standard_code") or ""
        if code:
            lines.append(f"原标准依据：{code}《离心泵能效限定值及能效等级》")
        data_version = standard.get("data_version") or snapshot.canonical_version or ""
        if data_version:
            lines.append(f"标准数据版本：{data_version}")
        if snapshot.canonical_package_hash:
            lines.append(f"标准数据指纹：{snapshot.canonical_package_hash}")

        # 命中依据来自快照自身的 trace「标准查询结果」步骤（真实存在才展示）。
        data_ids: list[str] = []
        tables: list[str] = []
        clauses: list[str] = []
        for step in (result.get("calculation_trace") or {}).get("steps") or []:
            if not isinstance(step, dict) or step.get("step_type") != "标准查询结果":
                continue
            data_ids.extend(str(item) for item in (step.get("data_ids") or []))
            if step.get("table"):
                tables.append(str(step["table"]))
            if step.get("clause"):
                clauses.append(str(step["clause"]))
        # 面向用户的标准依据用**标准表 / 条款**；内部 `data_id`
        # （如 `GB19762-T3-01`）是审计标识，只允许出现在折叠的审计信息区。
        if tables:
            lines.append("标准表：" + "、".join(dict.fromkeys(tables)))
        if clauses:
            lines.append("标准条款：" + "、".join(dict.fromkeys(clauses)))
        del data_ids  # 仅在审计信息区展示

        # 依据类字段（数据版本 / 指纹 / 命中条目 / 表 / 条款）一个都没有时，
        # 说明这是保存时未冻结依据的旧 Record：明确降级，不伪造。
        has_detail = any(
            marker in "\n".join(lines)
            for marker in ("标准数据版本", "标准数据指纹",
                           "标准表", "标准条款"))
        if not has_detail:
            lines.append("该历史记录保存时未包含完整标准依据。")
        return lines

    def _render_technical(self, snapshot, result) -> None:
        """审计信息：内部标识集中在此，不进入普通业务详情。"""

        standard = snapshot.reference_snapshot.get("standard") or {}
        rows = [
            ("评价状态", snapshot.evaluation_status or "—"),
            ("命中规则", result.get("matched_rule_id") or "—"),
            ("类别状态", result.get("category_status") or "—"),
            # 支持状态取自**不可变快照本身**，因此它天然就是"当时"的事实：
            # Phase 3/4 期间形成的 chemical Record 快照里是
            # `NOT_IN_RELEASE_SCOPE`，这里就显示"当前版本未支持"，
            # 不会被追溯改成"正式支持"。不重算、不改写 snapshot。
            ("支持状态", support_status_text(result.get("support_status"))),
            ("规则集标识", standard.get("rule_profile") or snapshot.ruleset_version or "—"),
            ("标准包", standard.get("pack_id") or "—"),
            ("数据版本", snapshot.canonical_version or "—"),
            ("数值配置", snapshot.numeric_profile_id or "—"),
            ("结果契约", snapshot.result_contract_version or "—"),
            ("输入指纹", snapshot.input_snapshot.get("request_fingerprint") or "—"),
            ("命中数据 ID", "、".join(
                str(item) for step in (result.get("calculation_trace") or {}).get("steps") or []
                if isinstance(step, dict) and step.get("step_type") == "标准查询结果"
                for item in (step.get("data_ids") or [])) or "—"),
        ]
        self.technical.setText("\n".join(f"{name}：{value}" for name, value in rows))
