"""空压机薄表单：只经Application计算与保存。"""
from datetime import date
import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QGroupBox, QComboBox
from ....application.services.compressor_analysis_service import CompressorAnalysisRequest
from ..widgets.page_layout import page_gutter
from ..widgets.choice_combo import ChoiceComboBox
from ..widgets.form_fields import field_form, field_row, selected_category, searchable_categories
from ..widgets.numeric_input import numeric_field, validate_numeric_fields


class CompressorAnalysisPage(QWidget):
    def __init__(self, service, parent=None, *, navigator=None):
        super().__init__(parent)
        self.service, self.navigator = service, navigator
        self.field_inputs = {}
        self.field_errors = {}
        self.last_saved_record_id = None
        self._last_result = None
        self._last_outcome = None
        outer = QVBoxLayout(self)
        page_gutter(outer)
        self.heading = QLabel("空压机分析")
        self.heading.setObjectName("pageHeading")
        outer.addWidget(self.heading)
        title = QLabel("GB 19153-2019《容积式空气压缩机能效限定值及能效等级》 · 已实现，待验收")
        title.setWordWrap(True)
        outer.addWidget(title)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        self.category = ChoiceComboBox()
        self.category.addItem("请选择设备类别…", None)
        for c in service.input_contract.categories:
            self.category.addItem(c.label, c.category_id)
        searchable_categories(self.category)
        layout.addWidget(QLabel("设备类别"))
        layout.addWidget(self.category)
        self.fields_group = QGroupBox("设备参数")
        self.form = field_form(self.fields_group)
        layout.addWidget(self.fields_group)
        self.evaluate_button = QPushButton("分析")
        self.evaluate_button.setProperty("primary", True)
        self.evaluate_button.clicked.connect(self.evaluate)
        layout.addWidget(self.evaluate_button)
        self.conclusion = QLabel("填写参数后点击分析。")
        self.conclusion.setProperty("coreResult", True)
        self.explanation = QLabel()
        self.explanation.setWordWrap(True)
        self.record_label = QLabel()
        self.record_label.setWordWrap(True)
        self.stale_label = QLabel("输入已变更，请重新分析")
        self.stale_label.hide()
        self.view_record_button = QPushButton("查看记录")
        self.view_record_button.hide()
        self.view_record_button.clicked.connect(lambda: self.navigator.open_records(
            record_id=self.last_saved_record_id) if self.navigator and self.last_saved_record_id else None)
        for widget in (self.stale_label, self.conclusion,
                       self.explanation, self.record_label, self.view_record_button):
            layout.addWidget(widget)
        layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)
        self.category.currentIndexChanged.connect(self._category_changed)
        self._category_changed()

    def _mark_stale(self, *_):
        if self._last_result is not None:
            self.stale_label.show()
            self.view_record_button.hide()

    def _category_changed(self, *_):
        retained = {k: w.text() for k, w in self.field_inputs.items() if k in {
            "device_name", "model", "location", "user_note"}}
        while self.form.rowCount():
            self.form.removeRow(0)
        self.field_inputs = {}
        self.field_errors = {}
        category = selected_category(self.category)
        for f in self.service.input_contract.visible_fields(category):
            options = self.service.input_contract.options(category, f.field_id)
            if options:
                widget = ChoiceComboBox()
                widget.addItem("请选择…", None)
                for value, label in options:
                    widget.addItem(label, value)
                widget.currentIndexChanged.connect(self._mark_stale)
            else:
                widget = QLineEdit()
                widget.setText(retained.get(f.field_id, ""))
                if f.unit:
                    numeric_field(widget, f.label, "positive")
                widget.textChanged.connect(self._mark_stale)
            widget.setObjectName("compressorField_" + f.field_id)
            label = f.label + ("（必填）" if f.required else "") + \
                (f"（{f.unit}）" if f.unit else "")
            field_row(self.form, label, widget)
            self.field_inputs[f.field_id] = widget
            error = QLabel()
            error.setWordWrap(True)
            error.hide()
            self.form.addRow("", error)
            self.field_errors[f.field_id] = error
        self._mark_stale()

    def evaluate(self):
        self.view_record_button.hide()
        self.stale_label.hide()
        self.record_label.clear()
        self.explanation.clear()
        self.last_saved_record_id = None
        self._last_result = None
        self._last_outcome = None
        self.conclusion.setText("请核对输入后分析。")
        for label in self.field_errors.values():
            label.hide()
        if not validate_numeric_fields(self.field_inputs.values()):
            return None
        values = {
            "category_id": selected_category(
                self.category),
            "input_contract_revision": "compressor-input.v1"}
        for key, widget in self.field_inputs.items():
            values[key] = widget.currentData() if isinstance(
                widget, QComboBox) else widget.text()
        self.evaluate_button.setEnabled(False)
        self.evaluate_button.setText("分析中…")
        try:
            outcome = self.service.analyze_and_record(
                CompressorAnalysisRequest(values, date.today()))
        except Exception:
            logging.getLogger(__name__).exception("空压机分析执行失败")
            self.conclusion.setText("分析执行失败，请重试或查看诊断日志。此次未形成记录。")
            return None
        finally:
            self.evaluate_button.setEnabled(True)
            self.evaluate_button.setText("分析")
        result = outcome.result
        self._last_result = result
        self._last_outcome = outcome
        self.conclusion.setText(result.ui_conclusion)
        self.explanation.setText(result.explanation)
        for key in (*result.missing_fields, *result.invalid_fields):
            if key in self.field_errors:
                self.field_errors[key].setText(
                    "请填写有效的" +
                    next(
                        f.label for f in self.service.input_contract.visible_fields(
                            values["category_id"]) if f.field_id == key))
                self.field_errors[key].show()
        if outcome.record_status == "SAVED":
            self.last_saved_record_id = outcome.record.record_id
            self.view_record_button.setVisible(self.navigator is not None)
            self.record_label.setText("本次分析已自动保存。再次分析会新增记录。")
        elif outcome.record_status == "SAVE_FAILED":
            self.record_label.setText("计算已完成，但记录保存失败，请重试。")
        return result
