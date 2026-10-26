"""GB18613验收候选单台页面；输入和选项来自Application契约。"""
from datetime import date
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLabel, QHBoxLayout,
    QComboBox, QLineEdit, QPushButton, QScrollArea, QGroupBox)
from ....application.services.motor_analysis_service import MotorAnalysisRequest
from ....application.services.motor_basis_formatter import format_motor_basis_lines
from ..tokens import TOKENS
from ..widgets.form_fields import (searchable_categories, selected_category, field_form,
                                  field_row, responsive_forms, primary_action)


class MotorAnalysisPage(QWidget):
    def __init__(self, service, parent=None, *, navigator=None):
        super().__init__(parent)
        self.service = service
        self.navigator = navigator
        self.last_saved_record_id = None
        self._category_values = {}
        self._editing_category = None
        self.contract = service.input_contract
        self.field_inputs = {}
        self._last_result = self._last_outcome = None
        self.last_record_status = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(*(TOKENS.page_margin,) * 4)
        heading = QLabel("电动机分析 · 接入验收候选")
        self.heading = heading
        heading.setObjectName("pageHeading")
        outer.addWidget(heading)
        overview = service.standard_overview()
        title = QLabel(f"{overview['standard_code']}《{overview['name']}》")
        title.setWordWrap(True)
        outer.addWidget(title)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(TOKENS.section_gap)
        category_group = QGroupBox("产品类别与适用条件")
        category_layout = QVBoxLayout(category_group)
        self.category = QComboBox()
        self.category.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.category.setMinimumContentsLength(12)
        self.category.setObjectName("motorCategory")
        self.category.addItem("请选择设备类别…", None)
        for item in self.contract.categories:
            self.category.addItem(item.label, item.category_id)
        searchable_categories(self.category)
        category_layout.addWidget(self.category)
        hint = QLabel("效率填写1～100的百分数点值，如85%填85。请填额定输出功率下实测效率；铭牌效率不能替代实测值。")
        hint.setWordWrap(True)
        category_layout.addWidget(hint)
        self.scope_hint = QLabel()
        self.scope_hint.setWordWrap(True)
        category_layout.addWidget(self.scope_hint)
        layout.addWidget(category_group)
        self.fields_group = QGroupBox("额定参数")
        self.fields_form = field_form(self.fields_group)
        self.fields_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.fields_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.addWidget(self.fields_group)
        self.efficiency_group = QGroupBox("实测效率与口径")
        self.efficiency_form = field_form(self.efficiency_group)
        layout.addWidget(self.efficiency_group)
        self.evaluate_button = QPushButton("分析")
        self.evaluate_button.setProperty("primary", True)
        self.evaluate_button.clicked.connect(self.evaluate)
        actions = QHBoxLayout()
        actions.addWidget(self.evaluate_button)
        self.view_record_button = QPushButton("查看记录")
        self.view_record_button.setProperty("primary", True)
        self.view_record_button.clicked.connect(lambda: self.navigator.open_records(record_id=self.last_saved_record_id) if self.navigator and self.last_saved_record_id else None)
        self.view_record_button.hide()
        actions.addWidget(self.view_record_button)
        actions.addStretch()
        layout.addLayout(actions)
        result = QGroupBox("分析结果")
        result_layout = QVBoxLayout(result)
        self.stale_label = QLabel("输入已变更，请重新分析")
        self.stale_label.setWordWrap(True)
        self.stale_label.setProperty("warning", True)
        self.stale_label.hide()
        result_layout.addWidget(self.stale_label)
        self.conclusion = QLabel("填写参数后点击分析。")
        self.conclusion.setObjectName("motorConclusion")
        self.conclusion.setProperty("coreResult", True)
        self.summary = QLabel()
        self.thresholds_label = QLabel()
        self.explanation = QLabel()
        self.record_label = QLabel()
        for label in (self.conclusion, self.summary, self.thresholds_label, self.explanation, self.record_label):
            label.setWordWrap(True)
            result_layout.addWidget(label)
        layout.addWidget(result)
        layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)
        self.category.currentIndexChanged.connect(self._on_category_changed)
        self.category.editTextChanged.connect(self._mark_stale)
        self._on_category_changed()

    def resizeEvent(self, event):
        if hasattr(self, "efficiency_form"):
            responsive_forms([self.fields_form, self.efficiency_form], self.width())
        super().resizeEvent(event)

    def _mark_stale(self, *_):
        if self._last_result is not None:
            self.stale_label.show()
            self.view_record_button.hide()
            self.evaluate_button.setText("分析")
            primary_action(self.evaluate_button, True)

    def _on_category_changed(self, *_):
        if self._editing_category:
            self._category_values[self._editing_category] = {
                key: control.currentData() if isinstance(control, QComboBox) else control.text()
                for key, control in self.field_inputs.items()}
        for form in (self.fields_form, self.efficiency_form):
            while form.rowCount():
                form.removeRow(0)
        self.field_inputs.clear()
        category = selected_category(self.category)
        self._editing_category = category
        self._mark_stale()
        if not category:
            self.scope_hint.clear()
            self.fields_group.hide()
            self.efficiency_group.hide()
            return
        self.scope_hint.setText("\n".join((f"已选类别：{self.category.currentText()}", self.contract.scope_hint(category),
                                           self.contract.efficiency_basis_hint(category))))
        for field in self.contract.visible_fields(category):
            label = field.label + ("（必填）" if field.required else "")
            if field.unit:
                label += f"（{field.unit}）"
            options = self.contract.options(category, field.field_id)
            if options:
                widget = QComboBox()
                widget.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
                widget.setMinimumContentsLength(12)
                widget.addItem("请选择…" if field.required else "按字段要求填报（可留空）", None)
                for value, text in options:
                    widget.addItem(text, value)
            else:
                widget = QLineEdit()
                widget.setPlaceholderText("请输入" if field.required else "可选")
                if field.field_id == "rated_frequency_hz":
                    widget.setPlaceholderText("如50或5～120；范围文本按不在范围处理")
                elif field.field_id == "poles":
                    widget.setPlaceholderText("正偶数，如2、4、10；表外极数按不在范围处理")
            widget.setObjectName(f"motorField_{field.field_id}")
            form = self.efficiency_form if field.field_id in {"measured_efficiency_pct", "efficiency_basis_status"} else self.fields_form
            field_row(form, label, widget)
            previous = self._category_values.get(category, {}).get(field.field_id)
            if previous is not None:
                if isinstance(widget, QComboBox):
                    widget.setCurrentIndex(max(widget.findData(previous), 0))
                else:
                    widget.setText(previous)
            (widget.currentIndexChanged if isinstance(widget, QComboBox) else widget.textChanged).connect(self._mark_stale)
            self.field_inputs[field.field_id] = widget
        self.fields_group.setVisible(self.fields_form.rowCount() > 0)
        self.efficiency_group.setVisible(self.efficiency_form.rowCount() > 0)

    def _collect_values(self):
        category = selected_category(self.category)
        if not category:
            raise ValueError("请先选择设备类别。")
        values = {"category_id": category}
        for key, widget in self.field_inputs.items():
            value = widget.currentData() if isinstance(widget, QComboBox) else widget.text()
            if value is not None and str(value).strip():
                values[key] = value
        return values

    def evaluate(self):
        self._last_result = self._last_outcome = None
        self.last_record_status = None
        self.last_saved_record_id = None
        self.view_record_button.hide()
        self.stale_label.hide()
        self.evaluate_button.setText("分析")
        primary_action(self.evaluate_button, True)
        for label in (self.summary, self.thresholds_label, self.explanation, self.record_label):
            label.clear()
        try:
            values = self._collect_values()
        except ValueError as error:
            self.conclusion.setText(str(error))
            return None
        try:
            outcome = self.service.analyze_and_record(MotorAnalysisRequest(values, date.today()))
        except Exception:
            logging.getLogger(__name__).exception("电动机分析执行失败")
            self.conclusion.setText("分析执行失败，请查看诊断日志。此次未形成评价记录。")
            return None
        result = outcome.result
        self._last_result, self._last_outcome = result, outcome
        self.last_record_status = outcome.record_status
        self.conclusion.setText(result.ui_conclusion)
        self.summary.setText("电动机接入验收候选，尚未宣布正式支持。")
        lines = []
        for grade in (1, 2, 3):
            threshold = result.thresholds.get(f"grade_{grade}", {})
            if threshold.get("state") == "AVAILABLE":
                lines.append(f"{grade}级效率限值：{threshold['display_text']}%")
            elif threshold.get("state") == "NO_INDICATOR":
                lines.append(f"{grade}级效率限值：—（标准无指标）")
        self.thresholds_label.setText("\n".join(lines))
        self.explanation.setText("\n".join([result.explanation, *format_motor_basis_lines(result.trace)]))
        saved = outcome.record_status
        self.record_label.setText("本次分析已自动保存到分析记录。" if saved == "SAVED" else
            "计算已完成，但历史记录保存失败；本次结果未被记录。" if saved == "SAVE_FAILED" else
            "本次未形成可保存的正式结论。")
        if saved == "SAVED" and outcome.record:
            self.last_saved_record_id = outcome.record.record_id
            self.view_record_button.setVisible(self.navigator is not None)
            self.evaluate_button.setText("再次分析")
            primary_action(self.evaluate_button, False)
            self.record_label.setText(self.record_label.text() + "再次分析会生成新记录。")
        return result
