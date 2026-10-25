"""变压器单台分析表单与按设备切换的薄页面。"""
from __future__ import annotations

import logging
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ....application.services.transformer_analysis_service import (
    TransformerAnalysisRequest,
    TRANSFORMER_SCOPE_HINT,
    format_transformer_basis_lines,
)
from ..labels import format_metric, user_grade_text
from ..tokens import TOKENS

_LOGGER = logging.getLogger("equipeffi.qt.transformer")

_THRESHOLD_LABELS = (
    ("no_load_loss_1", "空载损耗限值（1级）"),
    ("load_loss_1", "负载损耗限值（1级）"),
    ("no_load_loss_2", "空载损耗限值（2级）"),
    ("load_loss_2", "负载损耗限值（2级）"),
    ("no_load_loss_3", "空载损耗限值（3级）"),
    ("load_loss_3", "负载损耗限值（3级）"),
)


class TransformerAnalysisPage(QWidget):
    """按 Application 注入的输入契约生成表单，保留数值原始文本。"""

    def __init__(self, service, *, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
        self.contract = service.input_contract
        self.category_options = tuple(self.contract.categories)
        self._category_by_id = {item.category_id: item for item in self.category_options}
        self._category_by_label = {item.label: item for item in self.category_options}
        self.field_inputs: dict[str, QWidget] = {}
        self._last_result = None
        self._last_outcome = None
        self.last_record_status: str | None = None
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(*(TOKENS.page_margin,) * 4)
        outer.setSpacing(TOKENS.section_gap)

        heading = QLabel("新建分析")
        font = heading.font()
        font.setPixelSize(TOKENS.title_font_size)
        font.setBold(True)
        heading.setFont(font)
        outer.addWidget(heading)
        standard = self.service.standard_overview()
        standard_label = QLabel(
            f"适用标准：{standard.get('standard_code', 'GB 20052-2024')}《"
            f"{standard.get('name', '电力变压器能效限定值及能效等级')}》"
        )
        standard_label.setWordWrap(True)
        outer.addWidget(standard_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setSpacing(TOKENS.section_gap)

        basic = QGroupBox("基本信息")
        basic_form = QFormLayout(basic)
        self.project_name = QLineEdit()
        self.project_name.setPlaceholderText("可选")
        self.equipment_no = QLineEdit()
        self.equipment_no.setPlaceholderText("可选")
        basic_form.addRow("企业/项目名称", self.project_name)
        basic_form.addRow("设备编号", self.equipment_no)
        layout.addWidget(basic)

        category_box = QGroupBox("产品类别")
        category_layout = QVBoxLayout(category_box)
        self.category = QComboBox()
        self.category.setObjectName("transformerCategory")
        self.category.addItem("请选择产品类别…", None)
        for option in self.category_options:
            self.category.addItem(option.label, option.category_id)
        category_layout.addWidget(self.category)
        self.category_help = QLabel(TRANSFORMER_SCOPE_HINT)
        self.category_help.setWordWrap(True)
        category_layout.addWidget(self.category_help)
        layout.addWidget(category_box)

        self.fields_group = QGroupBox("设备参数")
        self.fields_form = QFormLayout(self.fields_group)
        layout.addWidget(self.fields_group)

        self.evaluate_button = QPushButton("分析")
        self.evaluate_button.clicked.connect(self.evaluate)
        action_row = QHBoxLayout()
        action_row.addWidget(self.evaluate_button)
        action_row.addStretch()
        layout.addLayout(action_row)

        self.result_group = QGroupBox("分析结果")
        result_layout = QVBoxLayout(self.result_group)
        self.conclusion = QLabel("完成参数填写后点击「分析」。")
        self.conclusion.setObjectName("transformerConclusion")
        self.conclusion.setWordWrap(True)
        font = self.conclusion.font()
        font.setBold(True)
        self.conclusion.setFont(font)
        result_layout.addWidget(self.conclusion)
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        result_layout.addWidget(self.summary)
        self.thresholds_label = QLabel("")
        self.thresholds_label.setWordWrap(True)
        result_layout.addWidget(self.thresholds_label)
        self.explanation = QLabel("")
        self.explanation.setWordWrap(True)
        result_layout.addWidget(self.explanation)
        self.record_label = QLabel("")
        self.record_label.setWordWrap(True)
        result_layout.addWidget(self.record_label)
        layout.addWidget(self.result_group)
        layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        self.category.currentIndexChanged.connect(self._on_category_changed)
        self._on_category_changed()

    def _on_category_changed(self, *_args) -> None:
        while self.fields_form.rowCount():
            self.fields_form.removeRow(0)
        self.field_inputs.clear()
        category_id = self.category.currentData()
        if not category_id:
            return

        options = tuple(self.contract.condition_options(category_id))
        fields = tuple(self.contract.visible_fields(category_id))
        for field in fields:
            marker = "（必填）" if field.required else (
                "（适用时必填）" if field.required_when else "")
            label = field.label + marker
            if field.unit:
                label += f"（{field.unit}）"
            if field.field_id == "standard_conditions":
                control = QComboBox()
                control.setObjectName("transformerStandardConditions")
                control.addItem("请选择标准条件…", None)
                for option in options:
                    control.addItem(option.label, option.condition_id)
            else:
                control = QLineEdit()
                control.setObjectName(f"transformerField_{field.field_id}")
                if field.required:
                    control.setPlaceholderText("请输入")
                elif field.required_when:
                    control.setPlaceholderText("适用时填写")
                else:
                    control.setPlaceholderText("可选")
            self.field_inputs[field.field_id] = control
            self.fields_form.addRow(label, control)

        if not fields:
            note = QLabel("此类别没有可填写的额定参数。")
            note.setWordWrap(True)
            self.fields_form.addRow(note)

    def _collect_values(self) -> dict:
        category_id = self.category.currentData()
        if not category_id:
            raise ValueError("请先选择产品类别。")
        category = self._category_by_id[category_id]
        values = {
            "category_id": category_id,
            "category": category.label,
            "project_name": self.project_name.text().strip() or None,
            "equipment_no": self.equipment_no.text().strip() or None,
        }
        for field_id, control in self.field_inputs.items():
            if isinstance(control, QComboBox):
                value = control.currentData()
            else:
                raw_text = control.text()
                value = raw_text if raw_text.strip() else None
            if value not in (None, ""):
                values[field_id] = value
        return values

    def evaluate(self):
        self._last_result = None
        self._last_outcome = None
        self.last_record_status = None
        self.record_label.setText("")
        self.thresholds_label.setText("")
        self.explanation.setText("")
        try:
            values = self._collect_values()
        except ValueError as error:
            self._show_error(str(error))
            return None

        request = TransformerAnalysisRequest(values=values, as_of=date.today())
        try:
            outcome = self.service.analyze_and_record(request)
        except Exception:  # noqa: BLE001 - 执行异常不能伪装为业务结论
            _LOGGER.exception("变压器分析执行失败（系统异常）")
            self.last_record_status = "SAVE_FAILED"
            self._show_error("分析未能完成，请检查输入或联系技术人员。")
            return None

        self._last_outcome = outcome
        self._last_result = outcome.result
        self.last_record_status = outcome.record_status
        self._render(outcome.result)
        self._render_record_status(outcome)
        return outcome.result

    def _show_error(self, message: str) -> None:
        self.conclusion.setText(message)
        self.summary.setText("")
        self.thresholds_label.setText("")
        self.explanation.setText("")
        self.record_label.setText("")

    def _render(self, result) -> None:
        self.conclusion.setText(str(result.ui_conclusion or "—"))
        category = (self._category_by_id.get(result.product_category)
                    or self._category_by_label.get(result.product_category))
        category_label = category.label if category else str(result.product_category or "—")
        lines = [f"设备类别：{category_label}", f"评价日期：{result.as_of.isoformat()}"]
        grade = user_grade_text(result.grade)
        if grade:
            lines.append(f"能效等级：{grade}")
        missing = self._missing_field_labels(result)
        if missing:
            lines.append("缺失信息：" + "、".join(missing))
        if getattr(result, "support_status", None) == "IMPLEMENTED":
            lines.append("软件状态：已接入，尚待正式支持验收。")
        self.summary.setText("\n".join(lines))

        threshold_lines = []
        for key, label in _THRESHOLD_LABELS:
            value = (result.thresholds or {}).get(key)
            if value is not None:
                threshold_lines.append(f"{label}：{format_metric(value, name=key)} W")
        self.thresholds_label.setText("\n".join(threshold_lines))
        explanation = str(result.explanation or "").strip()
        explanation_lines = ([f"判定说明：{explanation}"] if explanation else [])
        explanation_lines.extend(format_transformer_basis_lines(
            getattr(result, "trace", ())))
        self.explanation.setText("\n".join(explanation_lines))

    def _missing_field_labels(self, result) -> list[str]:
        category = (self._category_by_id.get(result.product_category)
                    or self._category_by_label.get(result.product_category))
        if category is None:
            return []
        labels = {field.field_id: field.label
                  for field in self.contract.visible_fields(category.category_id)}
        return [labels[field_id] for field_id in result.missing_fields if field_id in labels]

    def _render_record_status(self, outcome) -> None:
        status = outcome.record_status
        if status == "SAVED":
            text = "本次分析已自动保存到分析记录。"
            color = "#1f6f3f"
        elif status == "SAVE_FAILED":
            text = "计算结果已产生，但历史记录保存失败，本次结果未被记录。"
            color = "#a03020"
        else:
            text = "本次未形成可保存的正式结论。"
            color = "#8a6d00"
        self.record_label.setText(text)
        self.record_label.setStyleSheet(f"color: {color};")


class DeviceAnalysisPage(QWidget):
    """在泵和变压器页面间切换；默认保留原有泵流程。"""

    def __init__(self, pump_page: QWidget, transformer_page: TransformerAnalysisPage,
                 parent: QWidget | None = None, *, motor_page=None):
        super().__init__(parent)
        self.pump_page = pump_page
        self.transformer_page = transformer_page
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(TOKENS.page_margin,) * 4)
        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("分析设备"))
        self.device_selector = QComboBox()
        self.device_selector.setObjectName("analysisDeviceSelector")
        self.device_selector.addItem("离心泵", "centrifugal_pump")
        self.device_selector.addItem("变压器", "transformer")
        selector_row.addWidget(self.device_selector)
        selector_row.addStretch()
        layout.addLayout(selector_row)
        self.pages = QStackedWidget()
        self.pages.addWidget(pump_page)
        self.pages.addWidget(transformer_page)
        self.motor_page = motor_page
        if motor_page is not None:
            self.device_selector.addItem("电动机（验收候选）", "motor_lv")
            self.pages.addWidget(motor_page)
        layout.addWidget(self.pages, 1)
        self.device_selector.currentIndexChanged.connect(self.pages.setCurrentIndex)
        self.device_selector.setCurrentIndex(0)

    def select_standard(self, standard_code: str | None) -> None:
        if standard_code == "GB 18613-2020" and self.motor_page is not None:
            self.device_selector.setCurrentIndex(2)
        elif standard_code == "GB 20052-2024":
            self.device_selector.setCurrentIndex(1)
        elif standard_code == "GB 19762-2025":
            self.device_selector.setCurrentIndex(0)
