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
    QWidget, QStackedWidget, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QGridLayout, QButtonGroup, QSizePolicy,
)

from ....application.services.centrifugal_pump_analysis_service import (
    CentrifugalPumpAnalysisService,
)
from ..tokens import TOKENS
from ..style import heading, icon
from ....application.services.centrifugal_pump_analysis_service import (
    PUMP_ANALYSIS_DETAIL_METRIC_IDS,
    PUMP_LEVEL_LIMIT_METRIC_IDS,
    PUMP_METRIC_IDS,
    THRESHOLD_DISPLAY_NAMES,
    RecordQuery,
    user_conclusion_from_snapshot,
)
from ....application.services.transformer_analysis_service import (
    format_transformer_basis_lines,
    get_transformer_input_contract,
)
from ....application.services.motor_analysis_service import get_motor_input_contract
from ..labels import format_metric, support_status_text, user_grade_text

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


def _batch_standard_label(standard_code: str | None, summary) -> str:
    """把混合批次内部标记投影成可读标准号。"""

    if standard_code != "MULTI":
        return standard_code or "未记录"
    sheets = summary.get("sheets", ()) if isinstance(summary, dict) else ()
    codes = list(dict.fromkeys(str(item.get("standard_code") or "")
                               for item in sheets if item.get("standard_code")))
    return "、".join(codes) if codes else "多个标准"


def _batch_sheet_label(sheet_name: str | None, sheets) -> str:
    if sheet_name != "MULTI":
        return sheet_name or "未记录"
    names = list(dict.fromkeys(str(item.get("sheet_name"))
                               for item in sheets if item.get("sheet_name")))
    return "、".join(names) if names else "多个工作表"


class RecordsPage(QWidget):
    """正式记录历史页。"""

    def __init__(self, service: CentrifugalPumpAnalysisService, navigator=None, *,
                 batch=None, transformer=None, motor=None):
        super().__init__()
        self.service = service
        self.transformer_service = transformer
        self.motor_service = motor
        self.motor_contract = motor.input_contract if motor is not None else get_motor_input_contract()
        self.transformer_contract = (transformer.input_contract
                                     if transformer is not None else get_transformer_input_contract())
        self._transformer_categories = {
            item.category_id: item.label
            for item in getattr(self.transformer_contract, "categories", ())
        }
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
        outer = QVBoxLayout(self)
        outer.setContentsMargins(*(TOKENS.page_margin,) * 4)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)
        listing = QWidget()
        layout = QVBoxLayout(listing)
        layout.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        top.addWidget(heading("分析记录"))
        top.addStretch()
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh)
        top.addWidget(self.refresh_button)
        layout.addLayout(top)
        selector = QHBoxLayout()
        self.classification = QButtonGroup(self)
        self.single_button = QPushButton("单台分析")
        self.batch_button = QPushButton("批量评价")
        for index, button in enumerate((self.single_button, self.batch_button)):
            button.setCheckable(True)
            self.classification.addButton(button, index)
            selector.addWidget(button)
        selector.addStretch()
        self.single_button.setChecked(True)
        self.batch_button.setEnabled(self.batch_service is not None)
        layout.addLayout(selector)
        self.lists = QStackedWidget()
        self.single_tab = QWidget()
        single = QVBoxLayout(self.single_tab)
        single.setContentsMargins(0, 0, 0, 0)
        filters = QGridLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索记录编号、设备类别、标准或结论")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._apply_filters)
        filters.addWidget(self.search, 0, 0, 1, 2)
        self.category_filter = QComboBox()
        self.category_filter.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.category_filter.setMinimumContentsLength(8)
        self.category_filter.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(self.category_filter, 1, 0)
        self.conclusion_filter = QComboBox()
        for label, _ in CONCLUSION_FILTERS:
            self.conclusion_filter.addItem(label)
        self.conclusion_filter.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(self.conclusion_filter, 1, 1)
        self.date_filter = QLineEdit()
        self.date_filter.setPlaceholderText("评价日期 YYYY-MM-DD")
        self.date_filter.textChanged.connect(self._apply_filters)
        filters.addWidget(self.date_filter, 2, 0)
        self.clear_filters_button = QPushButton("清除筛选")
        self.clear_filters_button.clicked.connect(self.clear_filters)
        filters.addWidget(self.clear_filters_button, 2, 1)
        single.addLayout(filters)
        self.filter_summary = QLabel()
        self.filter_summary.setWordWrap(True)
        single.addWidget(self.filter_summary)
        self.list = self._table(["设备/项目", "设备类别", "采用标准", "结论", "评价日期", "操作"], [230, 240, 160, 100, 120, 90])
        self.list.cellActivated.connect(lambda row, column: self._on_selected(row))
        self.list.cellDoubleClicked.connect(lambda row, column: self._on_selected(row))
        single.addWidget(self.list, 1)
        self.load_more_button = QPushButton("加载更多")
        self.load_more_button.clicked.connect(self.load_more)
        single.addWidget(self.load_more_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.lists.addWidget(self.single_tab)
        self.batch_tab = QWidget()
        batch_layout = QVBoxLayout(self.batch_tab)
        batch_layout.setContentsMargins(0, 0, 0, 0)
        self.batch_search = QLineEdit()
        self.batch_search.setPlaceholderText("搜索全部批次：输入文件名、标准或工作表")
        self.batch_search.setClearButtonEnabled(True)
        self.batch_search.textChanged.connect(self.refresh_batch_records)
        batch_layout.addWidget(self.batch_search)
        self.batch_summary = QLabel()
        self.batch_summary.setWordWrap(True)
        batch_layout.addWidget(self.batch_summary)
        self.batch_list = self._table(["输入文件", "标准/设备", "数据行数", "设备台数", "处理摘要", "保存时间", "操作"], [220, 200, 100, 100, 210, 200, 90])
        self.batch_list.cellActivated.connect(lambda row, column: self._on_batch_selected(row))
        self.batch_list.cellDoubleClicked.connect(lambda row, column: self._on_batch_selected(row))
        batch_layout.addWidget(self.batch_list, 1)
        self.batch_load_more_button = QPushButton("加载更多批次")
        self.batch_load_more_button.clicked.connect(self.load_more_batch_records)
        batch_layout.addWidget(self.batch_load_more_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.lists.addWidget(self.batch_tab)
        self.classification.idClicked.connect(self.lists.setCurrentIndex)
        layout.addWidget(self.lists, 1)
        self.stack.addWidget(listing)
        detail_page = QWidget()
        detail_layout = QVBoxLayout(detail_page)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        self.back_button = QPushButton("返回分析记录")
        self.back_button.setIcon(icon("back"))
        self.back_button.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        detail_layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.detail_heading = heading("记录详情")
        detail_layout.addWidget(self.detail_heading)
        self.detail_tabs = QTabWidget()
        self._detail_scrolls = []
        labels = []
        for title in ("基本信息与结果", "输入数据与计算依据"):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            body = QWidget()
            content = QVBoxLayout(body)
            label = QLabel("请选择一条记录。")
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            content.addWidget(label)
            content.addStretch()
            scroll.setWidget(body)
            self.detail_tabs.addTab(scroll, title)
            self._detail_scrolls.append(scroll)
            labels.append(label)
        self.detail, self.inputs_detail = labels
        self.batch_detail = self.detail
        # 既有内部投影不加入产品页面控件树；正式快照中的证据保持完整。
        self.technical = QLabel()
        self.technical.hide()
        self.technical_box = None
        detail_layout.addWidget(self.detail_tabs, 1)
        self.stack.addWidget(detail_page)

    @staticmethod
    def _table(headers, widths):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().hide()
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setWordWrap(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for index, width in enumerate(widths):
            table.setColumnWidth(index, width)
        table.verticalHeader().setMinimumSectionSize(40)
        return table

    def _enter_detail(self, title):
        self.detail_heading.setText(title)
        self.detail_tabs.setCurrentIndex(0)
        self.stack.setCurrentIndex(1)
        for scroll in self._detail_scrolls:
            scroll.verticalScrollBar().setValue(0)

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
            keyword = self.batch_search.text().strip()
            records = list(self.batch_service.list_batch_records(limit=self._batch_limit + 1, **({"keyword": keyword} if keyword else {})))
        except Exception:  # noqa: BLE001 - 失败明确显示，不伪装成无历史
            import logging

            logging.getLogger("equipeffi.qt.records").exception(
                "查询批量评价记录失败")
            self._batch_visible = []
            self.batch_list.setRowCount(0)
            self.batch_summary.setText("读取批量评价记录失败，请点击刷新重试。")
            self.batch_load_more_button.setEnabled(False)
            return

        selected_id = None
        selected_row = self.batch_list.currentRow()
        if 0 <= selected_row < len(self._batch_visible):
            selected_id = self._batch_visible[selected_row].batch_record_id
        self._batch_has_more = len(records) > self._batch_limit
        self._batch_visible = records[:self._batch_limit]
        self.batch_list.setRowCount(len(self._batch_visible))
        for row, record in enumerate(self._batch_visible):
            summary = record.summary or {}
            values = (record.source_file_name or "未记录文件名",
                      _batch_standard_label(record.standard_code, summary),
                      str(record.data_row_count), str(record.total_quantity),
                      f"已评价 {record.evaluated_count} 行；未形成结论 {record.unevaluated_count} 行",
                      record.created_at_utc.replace("T", " ") + " UTC")
            for column, value in enumerate(values):
                self.batch_list.setItem(row, column, QTableWidgetItem(value))
            button = QPushButton("查看")
            button.clicked.connect(lambda checked=False, rid=record.batch_record_id: self.show_batch_record(rid))
            self.batch_list.setCellWidget(row, 6, button)
            if record.batch_record_id == selected_id:
                self.batch_list.selectRow(row)
        self.batch_list.resizeRowsToContents()
        if not self._batch_visible and self.stack.currentIndex() == 0:
            self.batch_detail.setText("尚无批量评价记录。")
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
            self.inputs_detail.clear()
            self._enter_detail("批次记录无法读取")
            return text

        summary = snapshot.summary if isinstance(snapshot.summary, dict) else {}
        source_name = snapshot.source_file_name or "该记录未保存此信息"
        result_name = snapshot.output_file_name or "该记录未保存此信息"
        lines = [
            f"采用标准：{_batch_standard_label(snapshot.standard_code, summary)}",
            f"工作表：{_batch_sheet_label(snapshot.sheet_name, summary.get('sheets', ())) }",
            f"评价日期：{snapshot.evaluation_date or '未记录'}",
            f"输入工作簿：{source_name}",
            f"结果工作簿：{result_name}",
            f"设备数量总计：{snapshot.total_quantity} 台",
            f"完成正式评价数量：{snapshot.evaluated_quantity} 台",
            f"数据行数：{snapshot.data_row_count}",
            f"完成正式评价行数：{snapshot.evaluated_count} 行",
            f"未形成正式结论行数：{snapshot.unevaluated_count} 行",
        ]
        from ....application.services.batch_summary_formatter import format_device_summary_lines
        lines.extend(format_device_summary_lines(summary.get("sheets", ())))
        unprocessed = summary.get("unprocessed_sheets") or ()
        if unprocessed:
            lines.append("未处理工作表：" + "、".join(str(name) for name in unprocessed))
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
        for row, record in enumerate(self._batch_visible):
            if record.batch_record_id == batch_record_id:
                self.batch_list.selectRow(row)
        self.inputs_detail.setText(self._batch_basis(snapshot, summary))
        self.batch_button.setChecked(True)
        self.lists.setCurrentIndex(1)
        self._enter_detail("批量评价记录")
        return text

    def _sync_category_filter(self) -> None:
        """泵型筛选项来自数据库里**真实出现过**的类别，不引入第二份泵型目录。"""

        current = self.category_filter.currentData()
        try:
            categories = list(self.service.record_categories())
        except Exception:  # noqa: BLE001 - 筛选项不可用不应让整页失效
            import logging

            logging.getLogger("equipeffi.qt.records").exception("读取泵型筛选项失败")
            categories = []
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        all_label = "全部类别" if self.transformer_service is not None else "全部泵型"
        self.category_filter.addItem(all_label, "")
        for category in categories:
            label = self._category_label(category)
            self.category_filter.addItem(label, category)
        index = self.category_filter.findData(current)
        self.category_filter.setCurrentIndex(index if index >= 0 else 0)
        self.category_filter.blockSignals(False)

    def build_query(self, offset: int = 0) -> RecordQuery:
        """把界面筛选条件转成**查询参数**（筛选在 SQL 里执行）。"""

        conclusion_index = max(self.conclusion_filter.currentIndex(), 0)
        statuses = CONCLUSION_FILTERS[conclusion_index][1]
        category = self.category_filter.currentData()
        return RecordQuery(
            keyword=self.search.text().strip(),
            product_category=category or "",
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
            if reset:
                self._visible = []
                self.list.setRowCount(0)
            self.load_more_button.setEnabled(False)
            self.filter_summary.setText("读取历史记录失败，请点击刷新重试。")
            return
        self._total = page.total
        self._visible = list(page.records) if reset else [*self._visible,
                                                          *page.records]
        self._offset = page.offset + len(page.records)
        self._render_list()
        self._update_summary()

    def _render_list(self) -> None:
        selected = self.list.currentRow()
        scroll = self.list.verticalScrollBar().value()
        self.list.setRowCount(len(self._visible))
        for row, record in enumerate(self._visible):
            conclusion = user_conclusion_from_snapshot(
                {"grade": record.grade, "evaluation_status": record.evaluation_status}, record.ui_conclusion)
            category = self._category_label(record.product_category)
            values = (getattr(record, "display_name", "") or category, category, record.standard_code, conclusion, record.as_of)
            for column, value in enumerate(values):
                self.list.setItem(row, column, QTableWidgetItem(value))
            button = QPushButton("查看")
            button.clicked.connect(lambda checked=False, rid=record.record_id: self.show_record(rid))
            self.list.setCellWidget(row, 5, button)
        self.list.resizeRowsToContents()
        if 0 <= selected < len(self._visible):
            self.list.selectRow(selected)
        self.list.verticalScrollBar().setValue(scroll)
        if not self._visible and self.stack.currentIndex() == 0:
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

        try:
            snapshot = self.service.open_record(record_id)
        except Exception:
            import logging
            logging.getLogger("equipeffi.qt.records").exception("打开单台记录失败")
            self.detail.setText("无法读取这条记录，请返回列表并刷新后重试。")
            self.inputs_detail.clear()
            self._enter_detail("记录无法读取")
            return self.detail.text()
        result = snapshot.result_snapshot
        input_snapshot = snapshot.input_snapshot

        if getattr(snapshot, "device_type", "") == "motor_lv":
            return self._show_motor_record(snapshot, result, input_snapshot)
        if getattr(snapshot, "device_type", "") == "transformer":
            return self._show_transformer_record(snapshot, result, input_snapshot)

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
        self._display_record(snapshot, result)
        self._render_technical(snapshot, result)
        return text

    def _category_label(self, value: str) -> str:
        motor_labels = {item.category_id: item.label for item in getattr(self.motor_contract, "categories", ())}
        return motor_labels.get(value, self._transformer_categories.get(value, value))

    def _show_motor_record(self, snapshot, result, inputs):
        from ....application.services.motor_basis_formatter import format_motor_basis_lines
        category = inputs.get("category_id") or snapshot.product_category
        contract = self.motor_contract
        if contract is None:
            # 仅读取静态字段标签，不加载标准包或重新运行算法。
            from ....application.services.motor_analysis_service import get_motor_input_contract
            contract = get_motor_input_contract()
        label = next((item.label for item in contract.categories
                      if item.category_id == category), snapshot.product_category)
        lines = [f"采用标准：{snapshot.standard_code}",
                 f"设备类别：{label}", f"评价日期：{snapshot.as_of}",
                 f"评价结论：{result.get('ui_conclusion') or snapshot.ui_conclusion}"]
        if result.get("support_status") == "IMPLEMENTED":
            lines.append("软件状态：已接入，尚待正式支持验收。")
        for field in contract.visible_fields(category):
            value = inputs.get(field.field_id)
            if value is None or value == "":
                continue
            choices = dict(contract.options(category, field.field_id))
            if field.field_id == "efficiency_basis_status":
                choices["AS_DECLARED_BY_FIELD"] = "按字段要求填报"
            value = choices.get(value, value)
            unit = f"（{field.unit}）" if field.unit else ""
            lines.append(f"{field.label}{unit}：{value}")
        for level, value in (result.get("thresholds") or {}).items():
            if not isinstance(value, dict):
                continue
            if value.get("state") == "AVAILABLE":
                lines.append(f"{level[-1]}级效率限值：{value.get('display_text', '')}%")
            elif value.get("state") == "NO_INDICATOR":
                lines.append(f"{level[-1]}级效率限值：—（标准无指标）")
        if result.get("explanation"):
            lines.append(result["explanation"])
        lines.extend(format_motor_basis_lines(result.get("trace", ())))
        lines.append(f"保存时间：{snapshot.finalized_at_utc}")
        text = "\n".join(lines)
        self._display_record(snapshot, result)
        return text

    def _show_transformer_record(self, snapshot, result, input_snapshot) -> str:
        """展示变压器记录的冻结快照，不调用计算服务。"""

        category_id = input_snapshot.get("category_id") or snapshot.product_category
        category_label = (self._transformer_categories.get(category_id)
                          or input_snapshot.get("category_label")
                          or self._category_label(snapshot.product_category)
                          or "变压器")
        lines = [
            f"采用标准：{snapshot.standard_code}",
            f"设备类别：{category_label}",
            f"评价日期：{snapshot.as_of}",
            f"评价结论：{user_conclusion_from_snapshot(result, snapshot.ui_conclusion)}",
        ]
        grade = user_grade_text(snapshot.grade)
        if grade:
            lines.append(f"能效等级：{grade}")
        values = input_snapshot
        category = next((item for item in getattr(self.transformer_contract, "categories", ())
                         if item.category_id == category_id), None)
        fields = (self.transformer_contract.visible_fields(category_id)
                  if category is not None else ())
        field_labels = {field.field_id: field for field in fields}
        for field_id, field in field_labels.items():
            value = values.get(field_id)
            if value in (None, "", {}):
                continue
            if field_id == "standard_conditions":
                value = self._condition_label(category_id, value)
            elif isinstance(value, dict):
                continue
            unit = f"（{field.unit}）" if field.unit else ""
            lines.append(f"{field.label}{unit}：{value}")
        if values.get("project_name"):
            lines.append(f"企业/项目名称：{values['project_name']}")
        if values.get("equipment_no"):
            lines.append(f"设备编号：{values['equipment_no']}")

        missing = [field_labels[key].label for key in result.get("missing_fields", ())
                   if key in field_labels]
        if missing:
            lines.append("缺失信息：" + "、".join(missing))
        explanation = str(result.get("explanation") or "").strip()
        if explanation:
            lines.append(f"判定说明：{explanation}")
        lines.extend(format_transformer_basis_lines(result.get("trace")))
        thresholds = result.get("thresholds") or {}
        threshold_labels = (
            ("no_load_loss_1", "空载损耗限值（1级）"),
            ("load_loss_1", "负载损耗限值（1级）"),
            ("no_load_loss_2", "空载损耗限值（2级）"),
            ("load_loss_2", "负载损耗限值（2级）"),
            ("no_load_loss_3", "空载损耗限值（3级）"),
            ("load_loss_3", "负载损耗限值（3级）"),
        )
        threshold_lines = [f"{label}：{format_metric(thresholds[key], name=key)} W"
                           for key, label in threshold_labels
                           if thresholds.get(key) is not None]
        if threshold_lines:
            lines.extend(threshold_lines)
        if result.get("support_status") == "IMPLEMENTED":
            lines.append("软件状态：已接入，尚待正式支持验收。")
        if snapshot.finalized_at_utc:
            lines.append(f"保存时间：{snapshot.finalized_at_utc}")
        text = "\n".join(lines)
        self._display_record(snapshot, result)
        return text

    def _condition_label(self, category_id: str, value) -> str:
        options = self.transformer_contract.condition_options(category_id)
        if isinstance(value, str):
            option = next((item for item in options if item.condition_id == value), None)
            return option.label if option else "已记录"
        if isinstance(value, dict):
            option = next((item for item in options
                           if dict(item.values) == value), None)
            return option.label if option else "已记录"
        return "已记录"

    def _display_record(self, snapshot, result):
        """两个页签均只投影本条快照；字段契约仅提供名称与单位。"""
        inputs = snapshot.input_snapshot or {}
        absent = "该记录未保存此信息"
        category = inputs.get("category_id") or snapshot.product_category
        device = getattr(snapshot, "device_type", "")
        basic = [f"采用标准：{snapshot.standard_code or absent}",
                 f"设备类别：{self._category_label(category)}",
                 f"评价日期：{snapshot.as_of or absent}",
                 f"评价结论：{user_conclusion_from_snapshot(result, snapshot.ui_conclusion)}"]
        for label, key in (("企业/项目名称", "project_name"), ("设备编号", "equipment_no")):
            if device != "motor_lv":
                basic.append(f"{label}：{inputs.get(key) or absent}")
        status = result.get("support_status")
        basic.append("保存时软件状态：" + ("已接入，尚待正式支持验收" if status == "IMPLEMENTED"
                     else support_status_text(status) if status else absent))
        if result.get("explanation"):
            basic.append(f"判定说明：{result['explanation']}")
        if result.get("missing_fields"):
            basic.append("本次存在缺失信息，详见输入数据。")
        input_lines = []
        basis = []
        if device in ("transformer", "motor_lv"):
            contract = self.transformer_contract if device == "transformer" else self.motor_contract
            if contract is None:
                if device == "transformer":
                    from ....application.services.transformer_analysis_service import get_transformer_input_contract
                    contract = get_transformer_input_contract()
                    self.transformer_contract = contract
                else:
                    from ....application.services.motor_analysis_service import get_motor_input_contract
                    contract = get_motor_input_contract()
            known = next((item for item in contract.categories if item.category_id == category), None)
            if known:
                basic[1] = f"设备类别：{known.label}"
                for field in contract.visible_fields(category):
                    value = inputs.get(field.field_id)
                    if value not in (None, ""):
                        if field.field_id == "standard_conditions":
                            value = self._condition_label(category, value)
                        elif device == "motor_lv":
                            choices = dict(contract.options(category, field.field_id))
                            if field.field_id == "efficiency_basis_status":
                                choices["AS_DECLARED_BY_FIELD"] = "按字段要求填报"
                            value = choices.get(value, value)
                    unit = f"（{field.unit}）" if field.unit else ""
                    input_lines.append(f"{field.label}{unit}：{value if value not in (None, '') else absent}")
            if device == "transformer":
                from .transformer_analysis import _THRESHOLD_LABELS
                for key, label in _THRESHOLD_LABELS:
                    if (result.get("thresholds") or {}).get(key) is not None:
                        basic.append(f"{label}：{format_metric(result['thresholds'][key], name=key)} W")
                for key, label in (("no_load_loss_w", "空载损耗"), ("load_loss_w", "负载损耗")):
                    if inputs.get(key) is not None:
                        basic.append(f"{label}：{inputs[key]} W")
                basis = format_transformer_basis_lines(result.get("trace", ()))
            else:
                from ....application.services.motor_basis_formatter import format_motor_basis_lines
                for key, threshold in (result.get("thresholds") or {}).items():
                    if isinstance(threshold, dict) and threshold.get("state") == "AVAILABLE":
                        basic.append(f"{key[-1]}级效率限值：{threshold.get('display_text', absent)}%")
                    elif isinstance(threshold, dict) and threshold.get("state") == "NO_INDICATOR":
                        basic.append(f"{key[-1]}级效率限值：—（标准无指标）")
                if inputs.get("measured_efficiency_pct") is not None:
                    basic.append(f"实测效率：{inputs['measured_efficiency_pct']}%")
                basis = format_motor_basis_lines(result.get("trace", ()))
        else:
            for key, label in (("QBEP", "流量 Q（m³/h）"), ("HBEP", "扬程 H（m）"),
                               ("speed", "转速 n（r/min）"), ("efficiency", "泵效率 η（%）"),
                               ("suction", "吸入方式"), ("stages", "级数")):
                input_lines.append(f"{label}：{inputs.get(key) if inputs.get(key) not in (None, '') else absent}")
            metrics = result.get("metrics_by_id") or {}
            for metric_id in (PUMP_METRIC_IDS["actual_efficiency"], *PUMP_LEVEL_LIMIT_METRIC_IDS):
                metric = metrics.get(metric_id)
                if isinstance(metric, dict):
                    basic.append(f"{metric.get('display_name', '效率')}：{format_metric(metric.get('value'), name=str(metric.get('display_name') or ''))}")
            if not metrics:
                for key, value in (result.get("thresholds") or {}).items():
                    basic.append(f"{THRESHOLD_DISPLAY_NAMES.get(key, key)}：{format_metric(value, name=key)}")
            basis = self._basis_lines(snapshot, result)
            for metric_id in PUMP_ANALYSIS_DETAIL_METRIC_IDS:
                metric = metrics.get(metric_id)
                if isinstance(metric, dict):
                    basis.append(f"{metric.get('display_name', '')}：{format_metric(metric.get('value'), name=str(metric.get('display_name') or ''))}")
            if not any(metric_id in metrics for metric_id in PUMP_ANALYSIS_DETAIL_METRIC_IDS):
                for key, value in ((result.get("calculation_trace") or {}).get("derived") or {}).items():
                    basis.append(f"{key}：{format_metric(value, name=str(key))}")
        basic.append(f"保存时间：{snapshot.finalized_at_utc or absent}")
        self.detail.setText("\n".join(basic))
        self.inputs_detail.setText("保存时输入数据\n" + "\n".join(input_lines or [absent])
                                  + "\n\n计算依据\n" + "\n".join(basis or ["该记录未保存完整计算依据。未使用当前标准补齐。 "]))
        self.single_button.setChecked(True)
        for row, record in enumerate(self._visible):
            if record.record_id == snapshot.record_id:
                self.list.selectRow(row)
        self.lists.setCurrentIndex(0)
        self._enter_detail("单台分析记录")

    @staticmethod
    def _batch_basis(snapshot, summary):
        lines = ["本批次保存了工作表摘要与问题统计；未保存逐行完整输入，不从当前工作簿补造。",
                 f"模板版本：{getattr(snapshot, 'template_version', '') or '该记录未保存此信息'}"]
        from ....application.services.batch_summary_formatter import format_device_summary_lines
        lines.extend(format_device_summary_lines(summary.get("sheets", ())))
        kinds = {"INPUT_ERROR": "输入错误", "EXECUTION_ERROR": "执行失败", "UNEVALUATED": "未形成正式结论"}
        for issue in summary.get("issues", ()):
            if isinstance(issue, dict):
                lines.append(f"{issue.get('sheet_name') or '工作表'} · 第{issue.get('row', '未记录')}行 · "
                             f"{kinds.get(issue.get('kind'), '问题')}：{issue.get('reason') or '该记录未保存此信息'}")
        if not summary.get("issues"):
            lines.append("本批次未记录需关注的行。" if "issues" in summary else
                         "该记录未保存逐行问题明细；不补造缺失信息。")
        return "\n".join(lines)

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
            (("开发状态", "已接入，尚待正式支持验收")
             if result.get("support_status") == "IMPLEMENTED"
             else ("支持状态", support_status_text(result.get("support_status")))),
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
