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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ....application.services.centrifugal_pump_analysis_service import (
    CentrifugalPumpAnalysisService,
)
from ..tokens import TOKENS
from ....application.services.centrifugal_pump_analysis_service import (
    PUMP_ANALYSIS_DETAIL_METRIC_IDS,
    PUMP_LEVEL_LIMIT_METRIC_IDS,
    PUMP_METRIC_IDS,
    THRESHOLD_DISPLAY_NAMES,
    RecordQuery,
    user_conclusion_from_snapshot,
)
from ..labels import format_metric, support_status_text, user_grade_text
from ..widgets.collapsible import CollapsibleSection

#: 结论筛选项 → 匹配的 `evaluation_status` 集合（"全部" 不筛选）。
#:
#: 界面只出现**中文业务说法**；机器状态只在内部用于构造 SQL 条件（M2 第五条）。
CONCLUSION_FILTERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("全部结论", ()),
    ("已判定等级", ("SUCCESS",)),
    ("不在范围", ("OUT_OF_STANDARD_SCOPE",)),
    ("资料不足 / 输入有误", ("INSUFFICIENT_DATA", "INVALID_INPUT")),
)

#: 每页条数（保持简单，不做复杂分页框架）。
PAGE_SIZE = 100
BATCH_RECORD_PAGE_SIZE = 50


class RecordsPage(QWidget):
    """正式记录历史页。"""

    def __init__(self, service: CentrifugalPumpAnalysisService, navigator=None, *,
                 batch=None):
        super().__init__()
        self.service = service
        self.navigator = navigator
        self.batch_service = batch
        #: 当前已加载的**投影**（跨页累积，用于列表显示）
        self._visible: list = []
        #: 符合条件的总数（由 SQL COUNT 给出，不是"已加载条数"）
        self._total = 0
        #: 下一页偏移量
        self._offset = 0
        #: 已加载条数上限（供测试与提示使用）
        self._records: list = []
        #: 批次列表按需递增加载；每次多取一条作为“还有更早记录”的哨兵。
        self._batch_limit = BATCH_RECORD_PAGE_SIZE
        self._batch_visible: list = []
        self._batch_has_more = False
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
        heading_row = QHBoxLayout()
        heading_row.addWidget(heading)
        heading_row.addStretch()
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh)
        heading_row.addWidget(self.refresh_button)
        layout.addLayout(heading_row)

        self.tabs = QTabWidget()
        self.single_tab = QWidget()
        single_layout = QVBoxLayout(self.single_tab)

        single_layout.addWidget(QLabel("以下筛选仅作用于单台分析记录。"))
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
        single_layout.addLayout(filters)

        self.filter_summary = QLabel("")
        single_layout.addWidget(self.filter_summary)

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

        # Owner Phase 8 R1 / UI03：普通产品界面不展示审计信息区域。
        # 证据继续保存在 Record；这里保留不可见占位以兼容既有内部调用点。
        self.technical = QLabel("")
        self.technical.setVisible(False)
        self.technical_box = None
        detail_layout.addStretch()
        holder.addWidget(detail_group, 3)
        single_layout.addLayout(holder, 1)

        buttons = QHBoxLayout()
        self.clear_filters_button = QPushButton("清除筛选")
        self.clear_filters_button.clicked.connect(self.clear_filters)
        buttons.addWidget(self.clear_filters_button)
        self.load_more_button = QPushButton("加载更多")
        self.load_more_button.clicked.connect(self.load_more)
        self.load_more_button.setEnabled(False)
        buttons.addWidget(self.load_more_button)
        buttons.addStretch()
        single_layout.addLayout(buttons)
        self.tabs.addTab(self.single_tab, "单台分析记录")

        self.batch_tab = None
        self.batch_list = None
        self.batch_detail = None
        self.batch_summary = None
        self.batch_load_more_button = None
        if self.batch_service is not None:
            self.batch_tab = QWidget()
            batch_layout = QVBoxLayout(self.batch_tab)
            batch_layout.addWidget(QLabel(
                "批次记录独立于单台分析记录，单台筛选不会影响此列表。"))
            self.batch_summary = QLabel("尚无批量评价记录。")
            batch_layout.addWidget(self.batch_summary)

            batch_holder = QHBoxLayout()
            self.batch_list = QListWidget()
            self.batch_list.currentRowChanged.connect(self._on_batch_selected)
            batch_holder.addWidget(self.batch_list, 2)

            batch_detail_group = QGroupBox("批次详情（只读）")
            batch_detail_layout = QVBoxLayout(batch_detail_group)
            self.batch_detail = QLabel("请选择一条批次记录。")
            self.batch_detail.setWordWrap(True)
            self.batch_detail.setTextFormat(Qt.TextFormat.PlainText)
            self.batch_detail.setAlignment(Qt.AlignmentFlag.AlignTop)
            batch_detail_layout.addWidget(self.batch_detail)
            batch_holder.addWidget(batch_detail_group, 3)
            batch_layout.addLayout(batch_holder, 1)

            batch_buttons = QHBoxLayout()
            self.batch_load_more_button = QPushButton("加载更多批次")
            self.batch_load_more_button.clicked.connect(
                self.load_more_batch_records)
            self.batch_load_more_button.setEnabled(False)
            batch_buttons.addWidget(self.batch_load_more_button)
            batch_buttons.addStretch()
            batch_layout.addLayout(batch_buttons)
            self.tabs.addTab(self.batch_tab, "批量评价记录")

        layout.addWidget(self.tabs, 1)

    # -- 数据 ---------------------------------------------------------------

    def refresh(self) -> None:
        """刷新单台记录与批次记录；两类数据各走自身只读服务。"""

        self._sync_category_filter()
        self._reload()
        self.refresh_batch_records()

    def refresh_batch_records(self) -> None:
        """重新读取最近批次；不读取工作簿，也不运行评价器。"""

        if self.batch_service is None:
            return
        self._batch_limit = BATCH_RECORD_PAGE_SIZE
        self._load_batch_records()

    def load_more_batch_records(self) -> None:
        """递增读取上限，使列表中的更早批次始终可继续访问。"""

        if self.batch_service is None or not self._batch_has_more:
            return
        self._batch_limit += BATCH_RECORD_PAGE_SIZE
        self._load_batch_records()

    def _load_batch_records(self) -> None:
        try:
            records = list(self.batch_service.list_batch_records(
                limit=self._batch_limit + 1))
        except Exception:  # noqa: BLE001 - 失败明确显示，不伪装成无历史
            import logging

            logging.getLogger("equipeffi.qt.records").exception(
                "查询批量评价记录失败")
            self.batch_summary.setText("读取批量评价记录失败，请稍后重试。")
            self.batch_load_more_button.setEnabled(False)
            return

        selected_id = None
        selected_row = self.batch_list.currentRow()
        if 0 <= selected_row < len(self._batch_visible):
            selected_id = self._batch_visible[selected_row].batch_record_id
        self._batch_has_more = len(records) > self._batch_limit
        self._batch_visible = records[:self._batch_limit]
        self.batch_list.blockSignals(True)
        self.batch_list.clear()
        for record in self._batch_visible:
            date_text = record.evaluation_date or record.created_at_utc[:10]
            saved_at = record.created_at_utc.replace("T", " ")
            source_name = record.source_file_name or "未记录文件名"
            self.batch_list.addItem(QListWidgetItem(
                f"{date_text} | {saved_at} UTC | {source_name} | "
                f"{record.standard_code} | {record.data_row_count} 行 | "
                f"{record.total_quantity} 台"))
        self.batch_list.blockSignals(False)

        if not self._batch_visible:
            self.batch_detail.setText(
                "尚无批量评价记录。完成一次 Excel 批量评价后会显示在这里。")
        else:
            selected_index = next(
                (i for i, record in enumerate(self._batch_visible)
                 if record.batch_record_id == selected_id),
                0)
            # setCurrentRow 会经 currentRowChanged 打开所选快照一次。
            self.batch_list.setCurrentRow(selected_index)
        if self._batch_has_more:
            self.batch_summary.setText(
                f"已显示最近 {len(self._batch_visible)} 条批次记录；"
                "还有更早记录，可继续加载。")
        else:
            self.batch_summary.setText(
                f"已显示 {len(self._batch_visible)} 条批次记录，"
                "已全部显示。")
        self.batch_load_more_button.setEnabled(self._batch_has_more)

    def _on_batch_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._batch_visible):
            return
        self.show_batch_record(self._batch_visible[row].batch_record_id)

    def show_batch_record(self, batch_record_id: str) -> str:
        """显示批次原始摘要快照；只读，不触发重新评价。"""

        try:
            snapshot = self.batch_service.open_batch_record(batch_record_id)
        except Exception:  # noqa: BLE001 - 列表项失效时保留明确错误状态
            import logging

            logging.getLogger("equipeffi.qt.records").exception(
                "打开批量评价记录失败")
            text = "无法读取这条批次记录，请刷新后重试。"
            self.batch_detail.setText(text)
            return text

        summary = snapshot.summary if isinstance(snapshot.summary, dict) else {}
        source_name = snapshot.source_file_name or "未记录"
        result_name = snapshot.output_file_name or "未生成"
        lines = [
            f"采用标准：{snapshot.standard_code or '未记录'}",
            f"工作表：{snapshot.sheet_name or '未记录'}",
            f"评价日期：{snapshot.evaluation_date or '未记录'}",
            f"输入工作簿：{source_name}",
            f"结果工作簿：{result_name}",
            f"数据行数：{snapshot.data_row_count}",
            f"设备数量总计：{snapshot.total_quantity} 台",
            f"完成正式评价行数：{snapshot.evaluated_count} 行",
            f"完成正式评价数量：{snapshot.evaluated_quantity} 台",
            f"未形成正式结论行数：{snapshot.unevaluated_count} 行",
        ]
        if "input_error_rows" in summary or "execution_error_rows" in summary:
            lines.extend((
                f"输入错误行数：{summary.get('input_error_rows', 0)} 行",
                f"执行失败行数：{summary.get('execution_error_rows', 0)} 行",
            ))
        else:
            lines.append(f"输入错误或执行失败行数：{snapshot.invalid_count} 行")
        conclusion_quantities = summary.get("conclusion_quantities")
        if isinstance(conclusion_quantities, dict) and conclusion_quantities:
            distribution = "；".join(
                f"{name} {quantity} 台"
                for name, quantity in conclusion_quantities.items())
            lines.append(f"正式结论分布：{distribution}")
        if snapshot.created_at_utc:
            lines.append(f"保存时间：{snapshot.created_at_utc}")
        text = "\n".join(lines)
        self.batch_detail.setText(text)
        return text

    def _sync_category_filter(self) -> None:
        """泵型筛选项来自数据库里**真实出现过**的类别，不引入第二份泵型目录。"""

        current = self.category_filter.currentText()
        try:
            categories = list(self.service.record_categories())
        except Exception:  # noqa: BLE001 - 筛选项不可用不应让整页失效
            import logging

            logging.getLogger("equipeffi.qt.records").exception("读取泵型筛选项失败")
            categories = []
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("全部泵型")
        self.category_filter.addItems(categories)
        index = self.category_filter.findText(current)
        self.category_filter.setCurrentIndex(index if index >= 0 else 0)
        self.category_filter.blockSignals(False)

    def build_query(self, offset: int = 0) -> RecordQuery:
        """把界面筛选条件转成**查询参数**（筛选在 SQL 里执行）。"""

        conclusion_index = max(self.conclusion_filter.currentIndex(), 0)
        statuses = CONCLUSION_FILTERS[conclusion_index][1]
        category = self.category_filter.currentText()
        return RecordQuery(
            keyword=self.search.text().strip(),
            product_category="" if category in ("", "全部泵型") else category,
            statuses=tuple(statuses),
            as_of_prefix=self.date_filter.text().strip(),
            limit=PAGE_SIZE,
            offset=max(offset, 0),
        )

    def _reload(self) -> None:
        """重新查询第一页并重建列表。"""

        self._offset = 0
        self._visible = []
        self._load_page(reset=True)

    def load_more(self) -> None:
        """加载下一页（简单"加载更多"，不引入复杂分页框架）。"""

        if self._offset >= self._total:
            return
        self._load_page(reset=False)

    def _load_page(self, *, reset: bool) -> None:
        try:
            page = self.service.search_records(self.build_query(self._offset))
        except Exception:  # noqa: BLE001 - 查询失败只提示，不伪装成"无记录"
            import logging

            logging.getLogger("equipeffi.qt.records").exception("查询历史记录失败")
            self.filter_summary.setText("读取历史记录失败，请稍后重试。")
            return
        self._total = page.total
        self._visible = list(page.records) if reset else [*self._visible,
                                                          *page.records]
        self._offset = page.offset + len(page.records)
        self._render_list()
        self._update_summary()

    def _render_list(self) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for record in self._visible:
            conclusion = user_conclusion_from_snapshot(
                {"grade": record.grade,
                 "evaluation_status": record.evaluation_status},
                record.ui_conclusion)
            self.list.addItem(QListWidgetItem(
                f"{record.as_of} | {record.standard_code} | "
                f"{record.product_category} | {conclusion}"))
        self.list.blockSignals(False)
        if not self._visible:
            self.detail.setText("没有符合条件的记录。" if self._total or self.search.text()
                                else "尚无正式记录。完成一次分析并保存后会显示在这里。")
            if self.technical is not None:
                self.technical.setText("")

    def _update_summary(self) -> None:
        shown = len(self._visible)
        if shown < self._total:
            self.filter_summary.setText(
                f"符合条件的记录共 {self._total} 条，已显示最近 {shown} 条"
                "（可点「加载更多」继续）。")
        else:
            self.filter_summary.setText(f"符合条件的记录共 {self._total} 条，已全部显示。")
        self.load_more_button.setEnabled(shown < self._total)

    def _apply_filters(self, *_args) -> None:
        """筛选条件变化：回到第一页重新查询。"""

        self._reload()

    def filtered_records(self) -> list:
        """当前**已加载**的筛选结果（只用于界面显示与测试）。"""

        return list(self._visible)

    def clear_filters(self) -> None:
        for widget in (self.search, self.date_filter):
            widget.blockSignals(True)
            widget.clear()
            widget.blockSignals(False)
        for combo in (self.conclusion_filter, self.category_filter):
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self._reload()

    def _on_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._visible):
            return
        # `show_record` 会用 record_id 取**完整不可变快照**（列表只有轻量投影）。
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
        grade_text = user_grade_text(snapshot.grade)
        if grade_text:
            lines.append(f"能效等级：{grade_text}")
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
        metric_snapshot = result.get("metrics_by_id")
        actual_metric = (metric_snapshot.get(PUMP_METRIC_IDS["actual_efficiency"])
                         if isinstance(metric_snapshot, dict) else None)
        if not isinstance(actual_metric, dict):
            actual_value = (result.get("extra_metrics") or {}).get("泵效率_%")
        else:
            actual_value = actual_metric.get("value")
        if actual_value is not None:
            lines.append(f"实际泵效率：{format_metric(actual_value, name='泵效率_%')}%")
        stable_thresholds = []
        if isinstance(metric_snapshot, dict):
            stable_thresholds = [metric_snapshot[metric_id]
                                 for metric_id in PUMP_LEVEL_LIMIT_METRIC_IDS
                                 if isinstance(metric_snapshot.get(metric_id), dict)]
        if stable_thresholds:
            lines.append("原等级阈值：" + "；".join(
                f"{metric.get('display_name') or metric.get('metric_id')} "
                f"{format_metric(metric.get('value'), name=str(metric.get('display_name') or ''))}"
                for metric in stable_thresholds))
        else:
            thresholds = result.get("thresholds") or {}
            if thresholds:
                # 只格式化**显示**；快照里的原值保持完整精度，不写回。
                lines.append("原等级阈值：" + "；".join(
                    f"{THRESHOLD_DISPLAY_NAMES.get(name, name)} "
                    f"{format_metric(value, name=str(name))}"
                    for name, value in thresholds.items()))
        stable_details = []
        if isinstance(metric_snapshot, dict):
            stable_details = [metric_snapshot[metric_id]
                              for metric_id in PUMP_ANALYSIS_DETAIL_METRIC_IDS
                              if isinstance(metric_snapshot.get(metric_id), dict)]
        if stable_details:
            lines.append("原关键计算参数：" + "；".join(
                f"{metric.get('display_name') or metric.get('metric_id')} "
                f"{format_metric(metric.get('value'), name=str(metric.get('display_name') or ''))}"
                for metric in stable_details))
        else:
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
