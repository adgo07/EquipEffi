"""GB18613验收候选单台页面；输入和选项来自Application契约。"""
from datetime import date
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLabel,
    QComboBox, QLineEdit, QPushButton, QScrollArea, QGroupBox)
from ....application.services.motor_analysis_service import MotorAnalysisRequest
from ....application.services.motor_basis_formatter import format_motor_basis_lines


class MotorAnalysisPage(QWidget):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.contract = service.input_contract
        self.field_inputs = {}
        self._last_result = self._last_outcome = None
        self.last_record_status = None
        outer = QVBoxLayout(self)
        heading = QLabel("电动机分析 · 接入验收候选")
        outer.addWidget(heading)
        overview = service.standard_overview()
        title = QLabel(f"{overview['standard_code']}《{overview['name']}》")
        title.setWordWrap(True)
        outer.addWidget(title)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        self.category = QComboBox()
        self.category.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.category.setMinimumContentsLength(12)
        self.category.setObjectName("motorCategory")
        self.category.addItem("请选择设备类别…", None)
        for item in self.contract.categories:
            self.category.addItem(item.label, item.category_id)
        layout.addWidget(QLabel("设备类别"))
        layout.addWidget(self.category)
        hint = QLabel("效率填写1～100的百分数点值，如85%填85。请填额定输出功率下实测效率；铭牌效率不能替代实测值。")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.scope_hint = QLabel()
        self.scope_hint.setWordWrap(True)
        layout.addWidget(self.scope_hint)
        self.fields_group = QGroupBox("设备参数")
        self.fields_form = QFormLayout(self.fields_group)
        self.fields_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.fields_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.addWidget(self.fields_group)
        self.evaluate_button = QPushButton("分析")
        self.evaluate_button.clicked.connect(self.evaluate)
        layout.addWidget(self.evaluate_button)
        self.conclusion = QLabel("填写参数后点击分析。")
        self.conclusion.setObjectName("motorConclusion")
        self.summary = QLabel()
        self.thresholds_label = QLabel()
        self.explanation = QLabel()
        self.record_label = QLabel()
        for label in (self.conclusion, self.summary, self.thresholds_label, self.explanation, self.record_label):
            label.setWordWrap(True)
            layout.addWidget(label)
        layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)
        self.category.currentIndexChanged.connect(self._on_category_changed)

    def _on_category_changed(self, *_):
        while self.fields_form.rowCount():
            self.fields_form.removeRow(0)
        self.field_inputs.clear()
        category = self.category.currentData()
        if not category:
            self.scope_hint.clear()
            return
        self.scope_hint.setText("\n".join((self.contract.scope_hint(category),
                                           self.contract.test_basis_hint(category))))
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
            self.fields_form.addRow(label, widget)
            self.field_inputs[field.field_id] = widget

    def _collect_values(self):
        category = self.category.currentData()
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
        return result
