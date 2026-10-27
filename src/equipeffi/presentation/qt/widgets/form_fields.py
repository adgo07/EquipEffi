"""专业表单的展示辅助，不选择业务类别或修改输入值。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QCompleter, QFormLayout, QLabel
from .numeric_input import numeric_container


def searchable_categories(combo):
    combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    combo.setMinimumContentsLength(10)
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
    combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    combo.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)


def selected_category(combo):
    return combo.currentData() if combo.currentText() == combo.itemText(combo.currentIndex()) else None


def field_form(group):
    form = QFormLayout(group)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
    form.setSpacing(12)
    return form


def field_row(form, text, control):
    label = QLabel(text)
    label.setWordWrap(True)
    label.setMinimumWidth(190)
    form.addRow(label, numeric_container(control) if hasattr(control, "numeric_error") else control)


def responsive_forms(forms, width):
    for form in forms:
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows if width < 680
                              else QFormLayout.RowWrapPolicy.WrapLongRows)


def primary_action(button, enabled):
    button.setProperty("primary", enabled)
    button.style().unpolish(button)
    button.style().polish(button)
