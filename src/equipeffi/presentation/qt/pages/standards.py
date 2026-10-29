"""标准列表与独立三分区详情，仅投影已装配服务的权威元数据。"""
from datetime import date
import logging
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QEvent, QTimer
from PySide6.QtGui import QDesktopServices, QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QTableWidgetItem,
    QAbstractItemView, QStackedWidget, QScrollArea, QGroupBox)
from ..style import heading, icon
from ..tokens import TOKENS
from ..widgets.page_layout import page_gutter
from ..widgets.compact_table import CompactTable

LIFECYCLE_STATE_LABELS = {
    "EFFECTIVE": "已实施", "NOT_YET_EFFECTIVE": "尚未实施", "UNKNOWN": "未提供实施日期"}


class StandardsPage(QWidget):
    def __init__(self, service, navigator=None, parent=None, *, transformer=None, motor=None):
        super().__init__(parent)
        self.service, self.navigator = service, navigator
        self.services = [s for s in (service, transformer, motor) if s is not None]
        self.motor_service = motor
        self.standard_code = None
        self._catalog = []
        self._visible = []
        self._load_error = False
        outer = QVBoxLayout(self)
        page_gutter(outer)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)
        listing = QWidget()
        layout = QVBoxLayout(listing)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(heading("标准库"))
        subtitle = QLabel("查询标准与适用范围，选择标准后开始设备分析")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)
        filters = QGridLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索标准编号、名称或适用对象")
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("标准关键词")
        self.status_filter = QComboBox()
        self.status_filter.setAccessibleName("标准状态")
        self.status_filter.addItem("全部标准状态", "")
        for state, label in LIFECYCLE_STATE_LABELS.items():
            self.status_filter.addItem(label, state)
        filters.addWidget(self.search, 0, 0)
        filters.addWidget(self.status_filter, 0, 1)
        filters.setColumnStretch(0, 1)
        layout.addLayout(filters)
        self.table = CompactTable(["标准编号", "标准名称", "标准状态", "实施日期", "软件支持"],
                                  [160, 300, 115, 120, 220], [122, 200, 78, 92, 148])
        self._column_timer = QTimer(self)
        self._column_timer.setSingleShot(True)
        self._column_timer.timeout.connect(self._resize_columns)
        self.table.viewport().installEventFilter(self)
        self.table.setHorizontalHeaderLabels(["标准编号", "标准名称", "标准状态", "实施日期", "软件支持"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setMinimumSectionSize(48)
        self.table.cellClicked.connect(lambda row, column: self.open_detail(row) if column in (0, 1) else None)
        self.table.cellActivated.connect(lambda row, column: self.open_detail(row))
        layout.addWidget(self.table, 1)
        self.list_status = QLabel()
        self.list_status.setWordWrap(True)
        layout.addWidget(self.list_status)
        self.retry_button = QPushButton("重试")
        self.retry_button.clicked.connect(self.refresh)
        self.retry_button.hide()
        layout.addWidget(self.retry_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.stack.addWidget(listing)
        detail = QWidget()
        layout = QVBoxLayout(detail)
        layout.setContentsMargins(0, 0, 0, 0)
        self.back_button = QPushButton("返回标准库")
        self.back_button.setIcon(icon("back"))
        self.back_button.clicked.connect(self.show_list)
        self.detail_heading = heading("")
        detail_header = QHBoxLayout()
        detail_header.addWidget(self.detail_heading, 1)
        detail_header.addWidget(self.back_button)
        layout.addLayout(detail_header)
        actions = QHBoxLayout()
        self.source_button = QPushButton("查看标准原文")
        self.source_button.setIcon(icon("book"))
        self.source_button.clicked.connect(self._open_source)
        self.start_button = QPushButton("按此标准分析")
        self.start_button.setProperty("primary", True)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self._start_analysis)
        actions.addWidget(self.source_button)
        actions.addWidget(self.start_button)
        actions.addStretch()
        layout.addLayout(actions)
        self.feedback = QLabel()
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)
        scroll = QScrollArea()
        self.detail_scroll = scroll
        scroll.setWidgetResizable(True)
        body = QWidget()
        sections = QVBoxLayout(body)
        sections.setContentsMargins(0, 0, 0, 0)
        self.section_labels = []
        for title in ("基本信息", "适用范围", "标准要求"):
            box = QGroupBox(title)
            content = QVBoxLayout(box)
            label = QLabel()
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            content.addWidget(label)
            sections.addWidget(box)
            self.section_labels.append(label)
        sections.addStretch()
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)
        self.stack.addWidget(detail)
        self.search.textChanged.connect(self._filter)
        self.status_filter.currentIndexChanged.connect(self._filter)
        self.refresh()

    def refresh(self):
        try:
            catalog = self._read_catalog()
        except Exception:  # 展示读取失败，不能把旧目录或部分目录伪装成本次成功。
            logging.getLogger("equipeffi.qt.standards").exception("标准目录读取失败")
            self._catalog = []
            self._load_error = True
            self.show_list()
            self._filter()
            self.retry_button.show()
            return
        self._catalog = catalog
        self._load_error = False
        self.retry_button.hide()
        self._filter()

    def _read_catalog(self):
        catalog = []
        for service in self.services:
            overview = service.standard_overview()
            row = dict(overview)
            row["name"] = overview.get("standard_name") or overview.get("name") or "未提供"
            row["scope"] = overview.get("scope_text") or "、".join(overview.get("supported_categories", ()))
            special = overview.get("special_categories", ())
            if special:
                row["scope"] += "\n其他可选项（不表示正式支持类别）：" + "、".join(special)
            state = overview.get("lifecycle_state")
            if not state:
                effective = overview.get("effective_date")
                try:
                    state = "EFFECTIVE" if date.today() >= date.fromisoformat(effective) else "NOT_YET_EFFECTIVE"
                except (ValueError, TypeError):
                    state = "UNKNOWN"
            row["lifecycle_state"] = state
            if overview.get("support_status") == "SUPPORTED":
                row["support"] = "正式支持"
            elif overview.get("support_status") == "IMPLEMENTED":
                row["support"] = "已实现，待验收"
            else:
                statuses = [s.get("support_status") for s in overview.get("scopes", ())]
                row["support"] = "正式支持" if statuses and all(s == "SUPPORTED" for s in statuses) else "未开放"
            catalog.append(row)
        return catalog

    def _filter(self, *_):
        # 不重建输入控件，中文预编辑、焦点和光标保持 Qt 原生行为。
        if self._load_error:
            self._visible = []
            self.table.setRowCount(0)
            self.list_status.setText("暂时无法读取标准目录，请重试。")
            return
        keyword = self.search.text().strip().casefold().replace("—", "-")
        state = self.status_filter.currentData()
        selected = self.table.currentRow()
        code = self.table.item(selected, 0).text() if selected >= 0 else None
        scroll = self.table.verticalScrollBar().value()
        self._visible = [row for row in self._catalog if
            (not state or row["lifecycle_state"] == state) and
            keyword in " ".join((row["standard_code"], row["name"], row["scope"])).casefold().replace("—", "-")]
        self.table.setRowCount(len(self._visible))
        for index, row in enumerate(self._visible):
            values = (row["standard_code"], row["name"], LIFECYCLE_STATE_LABELS.get(row["lifecycle_state"], "未提供"),
                      row.get("effective_date") or "未提供", row["support"])
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (0, 1):
                    item.setForeground(QColor("#197CC2"))
                    item.setToolTip("打开标准详情")
                self.table.setItem(index, column, item)
            if row["standard_code"] == code:
                self.table.selectRow(index)
        self.table.resizeRowsToContents()
        self.table.verticalScrollBar().setValue(scroll)
        self.list_status.setText(f"共 {len(self._visible)} 项标准" if self._visible else "没有匹配的标准，请调整关键词或标准状态。")

    def eventFilter(self, watched, event):
        if watched is self.table.viewport() and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            # The viewport already has its new geometry. Fit before painting,
            # then retain the deferred pass for scrollbar/layout follow-ups.
            self._resize_columns()
            self._column_timer.start(0)
        return super().eventFilter(watched, event)

    def _resize_columns(self):
        if not self.table.isVisible() or getattr(self, "_fitting_columns", False):
            return
        self._fitting_columns = True
        try:
            self.table.fit_columns()
        finally:
            self._fitting_columns = False

    def show_list(self, message=None):
        self.standard_code = None
        self._selected = None
        self.start_button.setEnabled(False)
        self.stack.setCurrentIndex(0)
        if message:
            self.list_status.setText(message)

    def open_detail(self, row):
        if not 0 <= row < len(self._visible):
            return
        item = self._visible[row]
        self.standard_code = item["standard_code"]
        self._selected = item
        self.detail_heading.setText(item["name"])
        self.feedback.clear()
        self.section_labels[0].setText("\n".join((
            f"标准编号：{item['standard_code']}", f"标准名称：{item['name']}",
            f"版本：{item.get('edition') or item['standard_code'].rsplit('-', 1)[-1]}",
            f"标准状态：{LIFECYCLE_STATE_LABELS.get(item['lifecycle_state'], '未提供')}",
            f"实施日期：{item.get('effective_date') or '未提供'}")))
        self.section_labels[1].setText(item["scope"] or "当前元数据未提供适用范围，请查阅标准原文。")
        # 这里只概述已有评价模型，不复制限值、公式或类别选表规则。
        code = item["standard_code"].replace("—", "-")
        if item.get("requirements_text"):
            text = item["requirements_text"]
        elif code == "GB 19762-2025":
            text = "按产品类别及适用条件评价泵效率（%），划分1级、2级、3级。输入流量（m³/h）、扬程（m）、转速（r/min）、泵效率（%）及适用类别条件。所选类别的具体等级限值与关键参数可在分析结果中查看。"
        elif code == "GB 20052-2024":
            text = "按适用型式、额定参数及标准条件查取空载损耗与负载损耗限值（W），分别比较并给出最终等级。不同类别采用相应表格与条件，具体限值在分析结果和保存的计算依据中查看。"
        elif code == "GB 18613-2020":
            text = "按电动机类别及适用额定参数采用表1至表6的效率限值（%），评价1级、2级、3级。实测效率口径与额定参数须符合所选类别条件；具体限值可在分析结果中查看。"
        else:
            text = "当前元数据未提供标准要求摘要，请查阅标准原文。"
        self.section_labels[2].setText(text)
        self.stack.setCurrentIndex(1)
        self.start_button.setEnabled(True)
        self.detail_scroll.verticalScrollBar().setValue(0)

    def _open_source(self):
        item = getattr(self, "_selected", None) or {}
        # source_file 是来源证据，不等于可打开文件；不猜本机路径或打包原件。
        location = item.get("document_url") or item.get("document_path")
        if not location:
            self.feedback.setText("当前没有可打开的标准原文。")
            return
        url = QUrl(location) if str(location).startswith(("https://", "http://")) else QUrl.fromLocalFile(str(Path(location).resolve()))
        if not url.isLocalFile() or Path(url.toLocalFile()).is_file():
            if QDesktopServices.openUrl(url):
                self.feedback.clear()
                return
        self.feedback.setText("标准原文未能打开，请检查文件位置或链接是否可用。")

    def _start_analysis(self):
        if self.navigator and self.standard_code:
            self.navigator.open_analysis(standard_code=self.standard_code)
