"""标准列表与独立三分区详情，仅投影已装配服务的权威元数据。"""
from datetime import date
from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStackedWidget, QScrollArea, QGroupBox)
from ..style import heading, icon
from ..tokens import TOKENS

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
        outer = QVBoxLayout(self)
        outer.setContentsMargins(TOKENS.page_margin, TOKENS.page_margin, TOKENS.page_margin, TOKENS.page_margin)
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
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["标准编号", "标准名称", "标准状态", "实施日期", "软件支持"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setMinimumSectionSize(40)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for index, width in enumerate((160, 300, 115, 120, 220)):
            self.table.setColumnWidth(index, width)
        self.table.horizontalHeader().setMinimumSectionSize(100)
        self.table.cellClicked.connect(lambda row, column: self.open_detail(row) if column in (0, 1) else None)
        self.table.cellActivated.connect(lambda row, column: self.open_detail(row))
        layout.addWidget(self.table, 1)
        self.list_status = QLabel()
        layout.addWidget(self.list_status)
        self.stack.addWidget(listing)
        detail = QWidget()
        layout = QVBoxLayout(detail)
        layout.setContentsMargins(0, 0, 0, 0)
        self.back_button = QPushButton("返回标准库")
        self.back_button.setIcon(icon("back"))
        self.back_button.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.detail_heading = heading("")
        layout.addWidget(self.detail_heading)
        actions = QHBoxLayout()
        self.source_button = QPushButton("查看标准原文")
        self.source_button.setIcon(icon("book"))
        self.source_button.clicked.connect(self._open_source)
        self.start_button = QPushButton("按此标准分析")
        self.start_button.setProperty("primary", True)
        self.start_button.clicked.connect(self._start_analysis)
        actions.addWidget(self.source_button)
        actions.addWidget(self.start_button)
        actions.addStretch()
        layout.addLayout(actions)
        self.feedback = QLabel()
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)
        scroll = QScrollArea()
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
        self._catalog = []
        for service in self.services:
            overview = service.standard_overview()
            row = dict(overview)
            row["name"] = overview.get("standard_name") or overview.get("name") or "未提供"
            row["scope"] = overview.get("scope_text") or "、".join(overview.get("supported_categories", ()))
            state = overview.get("lifecycle_state")
            if not state:
                effective = overview.get("effective_date")
                try:
                    state = "EFFECTIVE" if date.today() >= date.fromisoformat(effective) else "NOT_YET_EFFECTIVE"
                except (ValueError, TypeError):
                    state = "UNKNOWN"
            row["lifecycle_state"] = state
            if service is self.motor_service:
                row["support"] = "验收候选"
            elif overview.get("support_status") == "IMPLEMENTED":
                row["support"] = "已接入，待正式支持验收"
            else:
                statuses = [s.get("support_status") for s in overview.get("scopes", ())]
                row["support"] = "正式支持" if statuses and all(s == "SUPPORTED" for s in statuses) else "尚未开放"
            self._catalog.append(row)
        self._filter()

    def _filter(self, *_):
        # 不重建输入控件，中文预编辑、焦点和光标保持 Qt 原生行为。
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

    def resizeEvent(self, event):
        if hasattr(self, "table"):
            available = self.table.viewport().width() - sum(self.table.columnWidth(i) for i in (0, 2, 3, 4))
            self.table.setColumnWidth(1, max(300, available))
            self.table.resizeRowsToContents()
        super().resizeEvent(event)

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
        if "19762" in item["standard_code"]:
            text = "按产品类别及适用条件评价泵效率（%），划分1级、2级、3级。输入流量（m³/h）、扬程（m）、转速（r/min）、泵效率（%）及适用类别条件。具体等级限值与关键参数由分析服务按所选类别提供。"
        elif "20052" in item["standard_code"]:
            text = "按适用型式、额定参数及标准条件查取空载损耗与负载损耗限值（W），分别比较并给出最终等级。不同类别采用相应表格与条件，具体限值在分析结果和保存的计算依据中查看。"
        else:
            text = "按电动机类别及适用额定参数采用表1至表6的效率限值（%），评价1级、2级、3级。实测效率口径与额定参数须符合所选类别条件；具体限值由分析服务提供。"
        self.section_labels[2].setText(text)
        self.stack.setCurrentIndex(1)

    def _open_source(self):
        item = getattr(self, "_selected", {})
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
