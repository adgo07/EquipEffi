"""UI typo prevention only; retain raw Decimal text and blank business inputs."""
from decimal import Decimal, InvalidOperation
import re
from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QLabel, QLineEdit, QVBoxLayout, QWidget, QScrollArea
from shiboken6 import isValid
from ....application.services.motor_analysis_service import motor_numeric_text_issue

_EDIT = re.compile(r"\+?(?:[0-9]*(?:\.[0-9]*)?)(?:[eE][+-]?[0-9]*)?\Z")
_FREQUENCY_RANGE_PREFIX = re.compile(
    r"\+?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\s*-\s*\Z")


class NumericValidator(QValidator):
    def __init__(self, mode="positive", *, motor_field=None, parent=None):
        super().__init__(parent)
        self.mode, self.motor_field = mode, motor_field
        self.rejected_nonfinite = False

    def eventFilter(self, watched, event):
        # During native form removal Qt can deliver FocusOut after the editor
        # has begun destruction and expose only its QWidget base wrapper.
        if not isinstance(watched, QLineEdit) or not isValid(watched):
            return False
        if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self.rejected_nonfinite = False
            watched.numeric_error.hide()
        if event.type() == QEvent.Type.FocusOut:
            show_issue(watched)
        return False

    def issue(self, text):
        value = text.strip()
        if not value:  # Missing data remains the original service's decision.
            return None
        if self.mode == "frequency" and _FREQUENCY_RANGE_PREFIX.fullmatch(value):
            return "频率范围未填写完整，请补充连字符后的频率"
        if self.motor_field:
            issue = motor_numeric_text_issue(self.motor_field, value)
            if issue:
                return issue
        try:
            number = Decimal(value)
        except InvalidOperation:
            if self.mode == "frequency" and not motor_numeric_text_issue("rated_frequency_hz", value):
                return None
            return "请输入完整的十进制数值"
        if not number.is_finite():
            return "请输入有限数值，不能使用NaN或Inf"
        if number < 0:
            return "不能为负数"
        if self.mode not in {"nonnegative", "pump_percent"} and number == 0:
            return "必须大于0"
        if self.mode in {"integer", "even"}:
            if number != number.to_integral_value():
                return "请输入正整数" if self.mode == "integer" else "请输入正偶数"
            digits, exponent = number.as_tuple().digits, number.as_tuple().exponent
            last = digits[len(digits) + min(exponent, 0) - 1] if exponent <= 0 else 0
            if self.mode == "even" and last % 2:
                return "请输入正偶数"
        if self.mode in {"pump_percent", "motor_percent"} and number > 100:
            return "不能超过100%"
        if self.mode == "motor_percent" and number < 1:
            return "额定效率须为1%至100%"
        return None

    def validate(self, text, position):
        value = text.strip()
        if not value:
            return self.State.Intermediate, text, position
        if value.casefold().lstrip("+-") in {"nan", "snan", "inf", "infinity"}:
            self.rejected_nonfinite = True
            return self.State.Invalid, text, position
        if value == "-":
            return self.State.Intermediate, text, position
        if self.mode == "frequency" and _FREQUENCY_RANGE_PREFIX.fullmatch(value):
            return self.State.Intermediate, text, position
        if self.mode == "frequency" and not motor_numeric_text_issue("rated_frequency_hz", value):
            try:
                Decimal(value)
            except InvalidOperation:
                return self.State.Acceptable, text, position
        if value.startswith("-"):
            return self.State.Invalid, text, position
        if self.mode == "frequency" and not motor_numeric_text_issue("rated_frequency_hz", value):
            return self.State.Acceptable if self.issue(value) is None else self.State.Intermediate, text, position
        if not _EDIT.fullmatch(value):
            return self.State.Invalid, text, position
        # Intermediate permits 0 -> 0.5, decimal points and exponent editing.
        return (self.State.Acceptable if self.issue(value) is None else self.State.Intermediate), text, position


def numeric_field(edit, label, mode="positive", *, motor_field=None):
    validator = NumericValidator(mode, motor_field=motor_field, parent=edit)
    edit.setValidator(validator)
    # QLineEdit's default 32767 length must not truncate valid Decimal input.
    edit.setMaxLength(2147483647)
    edit.numeric_label = label
    edit.numeric_error = QLabel()
    edit.numeric_error.setWordWrap(True)
    edit.numeric_error.setStyleSheet("color:#B9484A; font-size:13px;")
    edit.numeric_error.hide()
    edit.installEventFilter(validator)
    def changed():
        validator.rejected_nonfinite = False
        edit.numeric_error.hide()
    edit.textChanged.connect(changed)
    edit.inputRejected.connect(lambda: show_issue(edit))
    edit.editingFinished.connect(lambda: show_issue(edit))
    return edit


def numeric_container(edit):
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(edit)
    layout.addWidget(edit.numeric_error)
    return container


def show_issue(edit):
    if not isValid(edit) or not isValid(edit.numeric_error):
        return None
    validator = edit.validator()
    if not isinstance(validator, NumericValidator) or not isValid(validator):
        return None
    issue = ("NaN或Inf已被拒绝，请修正输入后分析" if validator.rejected_nonfinite
             else validator.issue(edit.text()))
    edit.numeric_error.setText(f"{edit.numeric_label}：{issue}" if issue else "")
    edit.numeric_error.setVisible(bool(issue))
    return issue


def validate_numeric_fields(controls):
    invalid = [edit for edit in controls if isinstance(edit, QLineEdit)
               and hasattr(edit, "numeric_error") and show_issue(edit)]
    if invalid:
        invalid[0].setFocus()
        QTimer.singleShot(0, invalid[0], lambda: reveal_error(invalid[0]))
    return not invalid


def reveal_error(edit):
    if not edit.numeric_error.isVisible():
        return
    ancestor = edit.parentWidget()
    while ancestor is not None:
        if isinstance(ancestor, QScrollArea):
            ancestor.ensureWidgetVisible(edit.numeric_error, 0, 16)
            return
        ancestor = ancestor.parentWidget()


def rejected_states(controls):
    return {key: edit.validator().rejected_nonfinite for key, edit in controls.items()
            if hasattr(edit, "numeric_error")}


def restore_rejection(edit, rejected):
    if hasattr(edit, "numeric_error"):
        edit.validator().rejected_nonfinite = rejected
        if rejected:
            show_issue(edit)
