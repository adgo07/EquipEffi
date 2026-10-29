"""统一 GB 19762—2025 离心泵分析页。

产品流程（Owner，Phase 7）只有一条：

```text
选择泵型 → 填写参数 → 点击「分析」 → 显示清晰结果
         → 合法业务终态**自动**形成不可变历史记录
         → 之后从「分析记录」打开查看当时的输入、结果与依据
```

因此本页**没有**分析草稿、**没有**评价日期输入、**没有**「保存为正式记录」，
**没有**技术详情折叠区。

约束：

- 一个页面同时承载清水类与石油化工类全部正式类别；用户**不**选择
  `pump_water` / `pump_chemical`，也看不到任何内部 rule profile、field_id 或 rule_id。
- 本模块只做投影与调用：所有公式、查表、等级比较、边界判断都在 Application /
  Domain 层。Qt 不得复制任何业务算法。
- 类别唯一决定的字段（级数 / 吸入方式）取自 Application 的
  `category_field_constraints`，本模块**不新造**业务规则。
- 显示格式化（2 位小数）**只作用于本页文本**，不回写 Result、Record 快照、
  阈值比较或 Golden 真值。
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QRadioButton,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ....application.services.centrifugal_pump_analysis_service import (
    PUMP_CATEGORIES,
    PUMP_CATEGORY_GROUPS,
    PUMP_ANALYSIS_DETAIL_METRIC_IDS,
    PUMP_LEVEL_LIMIT_METRIC_IDS,
    PUMP_METRIC_IDS,
    THRESHOLD_DISPLAY_NAMES,
    CentrifugalPumpAnalysisService,
    PumpAnalysisRequest,
    PumpAnalysisResult,
    category_field_constraints,
)
from ..tokens import TOKENS
from ..widgets.page_layout import page_gutter
from ..style import icon
from ..labels import (
    format_metric,
    issue_code_texts,
    user_conclusion_text,
    user_grade_text,
)

_LOGGER = logging.getLogger("equipeffi.qt.analysis")

from ..widgets.choice_combo import ChoiceComboBox
from ..widgets.numeric_input import numeric_field, numeric_container, validate_numeric_fields

#: 设备参数字段（用户可见标签 + 内部字段名 + 单位）。
#:
#: Owner Phase 8 R1 / UI01：普通界面不用「规定点」这类术语，也不显示
#: `Q_BEP` / `H_BEP` / `η_BEP` 等复杂符号。**只改 Presentation 文案**：
#: 内部字段名（`QBEP` / `HBEP` / `speed` / `efficiency`）与业务计算契约不变。
POINT_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("QBEP", "流量 Q", "m³/h"),
    ("HBEP", "扬程 H", "m"),
    ("speed", "转速 n", "r/min"),
    ("efficiency", "泵效率 η", "%"),
)

#: 吸入方式选项（沿用已批准业务枚举，不在 UI 新造值）。
SUCTION_OPTIONS: tuple[str, ...] = ("单吸", "双吸")

#: 系统执行失败的统一用户文案（真实原因只进日志）。
SYSTEM_FAILURE_TEXT = "分析未能完成，请检查输入或联系技术人员。"


def format_display_number(value: Any, *, name: str = "") -> str:
    """把计算派生量显示为 2 位小数（转发到共享实现，保留旧调用点兼容）。"""

    return format_metric(value, name=name)


class AnalysisPage(QWidget):
    """统一离心泵分析页。"""

    def __init__(self, service: CentrifugalPumpAnalysisService,
                 *, record_id_factory: Callable[[], str] | None = None,
                 navigator=None, as_of: date | None = None):
        super().__init__()
        self.service = service
        self.navigator = navigator
        self._record_id_factory = record_id_factory
        #: 评价日期默认取**本机当天**（Owner 规则，Phase 7：页面不显示、不要求填写）。
        #: 该覆盖只供测试固定日期，**不产生任何用户可见控件**。
        self._as_of_override = as_of
        self._last_request: PumpAnalysisRequest | None = None
        self._last_result: PumpAnalysisResult | None = None
        #: 最近一次**自动**形成的正式记录编号。
        self.last_saved_record_id: str | None = None
        #: 最近一次记录保存状态：RECORDED / NOT_RECORDED / SAVE_FAILED。
        self.last_record_status: str | None = None
        self._responsive_grids = []
        self._build()

    # -- 构建 ---------------------------------------------------------------

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        page_gutter(outer)
        outer.setSpacing(TOKENS.section_gap)

        heading = QLabel("新建分析")
        self.heading = heading
        heading.setObjectName("pageHeading")
        outer.addWidget(heading)

        standard = QLabel("适用标准：GB 19762—2025《离心泵能效限定值及能效等级》")
        standard.setWordWrap(True)
        outer.addWidget(standard)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(TOKENS.section_gap)
        layout.addWidget(self._basic_group())
        layout.addWidget(self._category_group())
        layout.addWidget(self._points_group())
        layout.addWidget(self._conditions_group())
        layout.addWidget(self._actions())
        layout.addWidget(self._result_group())
        layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        # 先建好输入控件再应用一次类别联动，避免信号早于控件创建。
        self._on_category_changed()
        self.stale_label = QLabel("输入已变更，请重新分析")
        self.stale_label.setWordWrap(True)
        self.stale_label.setStyleSheet("color:#956420;")
        self.result_group.layout().insertWidget(0, self.stale_label)
        self.stale_label.hide()
        for edit in (self.project_name, self.equipment_no, self.stages, *self.point_inputs.values()):
            edit.textChanged.connect(self._mark_stale)
        self.category.currentIndexChanged.connect(self._mark_stale)
        self.suction.currentIndexChanged.connect(self._mark_stale)

    def resizeEvent(self, event):
        columns = 2 if self.width() >= 680 else 1
        for grid, widgets in self._responsive_grids:
            for index, widget in enumerate(widgets):
                grid.addWidget(widget, index // columns, index % columns)
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(1, 1 if columns == 2 else 0)
        super().resizeEvent(event)

    def _fields(self, group, fields):
        grid = QGridLayout(group)
        grid.setSpacing(12)
        widgets = []
        for label, control in fields:
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)
            caption = QLabel(label)
            caption.setWordWrap(True)
            layout.addWidget(caption)
            layout.addWidget(control)
            if hasattr(control, "numeric_error"):
                layout.addWidget(control.numeric_error)
            widgets.append(widget)
            grid.addWidget(widget, len(widgets) - 1, 0)
        self._responsive_grids.append((grid, widgets))

    def _mark_stale(self, *_):
        if self._last_result is not None:
            self.stale_label.show()
            self.view_record_button.hide()
            self.evaluate_button.setText("分析")
            self.evaluate_button.setToolTip("")
            self.evaluate_button.setProperty("primary", True)
            self.evaluate_button.style().unpolish(self.evaluate_button)
            self.evaluate_button.style().polish(self.evaluate_button)

    def _basic_group(self) -> QGroupBox:
        """基本信息：企业/项目名称与设备编号。

        **不含评价日期**：新分析自动采用本机当天日期（Owner 规则，Phase 7）。
        """

        group = QGroupBox("基本信息")
        self.project_name = QLineEdit()
        self.project_name.setPlaceholderText("可选")
        self.equipment_no = QLineEdit()
        self.equipment_no.setPlaceholderText("可选")
        self._fields(group, [("企业/项目名称（可选）", self.project_name), ("设备编号（可选）", self.equipment_no)])
        return group

    def _category_group(self) -> QGroupBox:
        group = QGroupBox("产品类别")
        layout = QVBoxLayout(group)
        self.category = ChoiceComboBox()
        # 不预选任何正式类别：软件不得替用户猜泵型（猜错会把用户导向错误规则）。
        self.category.addItem("请选择产品类别…", None)
        group_labels = dict(PUMP_CATEGORY_GROUPS)
        for group_key, _ in PUMP_CATEGORY_GROUPS:
            entries = [c for c in PUMP_CATEGORIES if c.group == group_key]
            if not entries:
                continue
            self.category.insertSeparator(self.category.count())
            self.category.addItem(f"— {group_labels.get(group_key, group_key)} —", None)
            model = self.category.model().item(self.category.count() - 1)
            if model is not None:
                model.setEnabled(False)
            for category in entries:
                self.category.addItem(category.visible_name, category.visible_name)
        self.category.setCurrentIndex(0)
        self.category.setEditable(True)
        self.category.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.category.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.category.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.category.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.category.lineEdit().setPlaceholderText("搜索或选择产品类别")
        self.category.editTextChanged.connect(self._on_category_text_changed)
        layout.addWidget(self.category)
        self.category_help = QLabel("")
        self.category_help.setWordWrap(True)
        layout.addWidget(self.category_help)
        self.category.currentIndexChanged.connect(self._on_category_changed)
        return group

    def _points_group(self) -> QGroupBox:
        group = QGroupBox("设备参数")
        self.point_inputs: dict[str, QLineEdit] = {}
        fields = []
        for key, label, unit in POINT_FIELDS:
            edit = QLineEdit()
            numeric_field(edit, label, "pump_percent" if key == "efficiency" else "positive")
            edit.setPlaceholderText("请输入设备参数数值")
            fields.append((f"{label}（{unit}）", edit))
            self.point_inputs[key] = edit
        self._fields(group, fields)
        return group

    def _conditions_group(self):
        group = QGroupBox("类别条件")
        grid = QGridLayout(group)
        grid.addWidget(QLabel("吸入方式"), 0, 0)
        self.suction = QComboBox(self)
        self.suction.addItem("请选择", None)
        for option in SUCTION_OPTIONS:
            self.suction.addItem(option, option)
        self.suction.hide()
        radios = QWidget()
        radio_layout = QHBoxLayout(radios)
        radio_layout.setContentsMargins(0, 0, 0, 0)
        self.suction_buttons = []
        for option in SUCTION_OPTIONS:
            radio = QRadioButton(option)
            radio.toggled.connect(lambda checked, value=option: self.suction.setCurrentIndex(self.suction.findData(value)) if checked else None)
            radio_layout.addWidget(radio)
            self.suction_buttons.append(radio)
        radio_layout.addStretch()
        self.suction.currentIndexChanged.connect(self._sync_suction)
        grid.addWidget(radios, 0, 1)
        grid.addWidget(QLabel("级数"), 1, 0)
        self.stages = QLineEdit()
        numeric_field(self.stages, "级数", "integer")
        grid.addWidget(numeric_container(self.stages), 1, 1)
        # 类别锁定说明：让用户知道该值由泵型唯一决定，不是软件随意填的。
        self.locked_hint = QLabel("")
        self.locked_hint.setWordWrap(True)
        self.locked_hint.setStyleSheet("color: #65727e;")
        grid.addWidget(self.locked_hint, 2, 0, 1, 2)
        return group

    def _actions(self) -> QWidget:
        holder = QFrame()
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        self.evaluate_button = QPushButton("分析")
        self.evaluate_button.setProperty("primary", True)
        self.evaluate_button.clicked.connect(self.evaluate)
        layout.addWidget(self.evaluate_button)
        self.view_record_button = QPushButton("查看记录")
        self.view_record_button.setProperty("primary", True)
        self.view_record_button.setIcon(icon("records"))
        self.view_record_button.clicked.connect(lambda: self.navigator.open_records(record_id=self.last_saved_record_id) if self.navigator and self.last_saved_record_id else None)
        self.view_record_button.hide()
        layout.addWidget(self.view_record_button)
        layout.addStretch()
        return holder

    def _result_group(self) -> QGroupBox:
        group = QGroupBox("分析结果")
        self.result_group = group
        layout = QVBoxLayout(group)
        self.conclusion = QLabel("—")
        self.conclusion.setObjectName("coreResult")
        font = self.conclusion.font()
        font.setPixelSize(TOKENS.title_font_size)
        font.setBold(True)
        self.conclusion.setFont(font)
        layout.addWidget(self.conclusion)
        self.summary = QLabel("尚未分析。")
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.summary)

        # 非阻断提示（标准生命周期）。默认隐藏；不参与判定。
        self.warning_label = QLabel("")
        self.warning_label.setWordWrap(True)
        self.warning_label.setTextFormat(Qt.TextFormat.PlainText)
        self.warning_label.setStyleSheet("color: #956420;")
        self.warning_label.setVisible(False)
        layout.addWidget(self.warning_label)

        # 第二层：关键实际值与对应限值。
        self.values_label = QLabel("")
        self.values_label.setWordWrap(True)
        self.values_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.values_label)

        # Owner Phase 8 R1 / UI02：普通结果区不再展示「判定说明 / 为什么 /
        # 所选标准 / 标准依据」。底层 explanation / references / provenance
        # 仍完整保存在 Result 与 Record 中（只是本页不展示）。
        self.reason_label = QLabel("")
        self.reason_label.setWordWrap(True)
        self.reason_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.reason_label)

        # 第四层：所选标准与已有标准依据。
        self.basis = QLabel("")
        self.basis.setWordWrap(True)
        self.basis.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.basis)

        # 历史记录状态：明确区分"已形成历史记录"与"记录保存失败"。
        self.record_label = QLabel("")
        self.record_label.setWordWrap(True)
        self.record_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.record_label)
        return group

    # -- 交互 ---------------------------------------------------------------

    def current_category(self) -> str | None:
        if self.category.currentText() != self.category.itemText(self.category.currentIndex()):
            return None
        return self.category.currentData()

    def _on_category_text_changed(self, *_):
        if hasattr(self, "stale_label"):
            self._mark_stale()

    def _sync_suction(self, *_):
        for radio in self.suction_buttons:
            radio.setAutoExclusive(False)
            radio.setChecked(radio.text() == self.suction.currentData())
            radio.setAutoExclusive(True)
            radio.setEnabled(self.suction.isEnabled())

    def _on_category_changed(self, *_: object) -> None:
        """应用类别唯一决定的字段约束（级数 / 吸入方式）。

        约束来自 Application 的 `category_field_constraints`，本页不新造规则：
        被锁定的字段自动赋值并禁止用户修改；未锁定的字段保持用户选择
        （例如"管道清水离心泵"的吸入方式、多级泵的级数）。
        """

        category = self.current_category()
        entry = next((c for c in PUMP_CATEGORIES if c.visible_name == category), None)
        self.category_help.setText(
            f"已选类别：{entry.visible_name}\n{entry.help_text}" if entry is not None
            else "请选择产品类别。若无法判断，可选“不确定类别”查看判断说明。")

        constraints = category_field_constraints(category)
        locked_labels: list[str] = []

        stages_value = constraints.get("stages")
        if stages_value is not None:
            self.stages.setText(stages_value)
            self.stages.setEnabled(False)
            locked_labels.append(f"级数 = {stages_value}")
        else:
            self.stages.setEnabled(True)
            if category is None:
                self.stages.clear()

        suction_value = constraints.get("suction")
        if suction_value is not None:
            index = self.suction.findData(suction_value)
            if index >= 0:
                self.suction.setCurrentIndex(index)
            self.suction.setEnabled(False)
            locked_labels.append(f"吸入方式 = {suction_value}")
        else:
            self.suction.setEnabled(True)
            if category is None:
                self.suction.setCurrentIndex(0)

        self.locked_hint.setText(
            "该泵型已唯一确定：" + "、".join(locked_labels) + "（由标准适用范围决定，不可修改）"
            if locked_labels else "")
        self._sync_suction()

    def _collect_request(self) -> PumpAnalysisRequest | None:
        category = self.current_category()
        if not category:
            self._show_error("请先选择产品类别。")
            return None
        if not validate_numeric_fields([*self.point_inputs.values(), self.stages]):
            self.last_record_status = "NOT_RECORDED"
            self._show_error("请修正标出的数值输入。此次未形成分析记录。")
            return None
        values = {key: (edit.text().strip() or None)
                  for key, edit in self.point_inputs.items()}

        # 锁定字段**强制**取权威值：不依赖控件状态，用户改不动、也绕不过。
        constraints = category_field_constraints(category)
        suction = constraints.get("suction", self.suction.currentData())
        stages = constraints.get("stages", self.stages.text().strip() or None)

        return PumpAnalysisRequest(
            product_category=category,
            # 评价日期自动取本机当天，用户不填、不选（Owner 规则，Phase 7）。
            as_of=self._as_of_override or date.today(),
            suction=suction,
            stages=stages,
            project_name=self.project_name.text().strip() or None,
            equipment_no=self.equipment_no.text().strip() or None,
            **values,
        )

    def _next_record_id(self) -> str | None:
        return self._record_id_factory() if self._record_id_factory is not None else None

    def evaluate(self) -> PumpAnalysisResult | None:
        """执行「分析」：评价 + 自动固化合法业务终态。

        开始前先作废上一次结果，避免把旧结果当成新输入。

        **系统异常与业务结论严格分离**：评价阶段的异常原样抛出并由本页按系统失败
        处理（真实原因进日志），**不**被转换成"无法判定"或"资料不足"。
        """

        self._last_request = None
        self._last_result = None
        self.last_saved_record_id = None
        self.last_record_status = None
        self.stale_label.hide()
        self.view_record_button.hide()
        self.evaluate_button.setText("分析")
        self.evaluate_button.setToolTip("")
        self.evaluate_button.setProperty("primary", True)
        self.evaluate_button.style().unpolish(self.evaluate_button)
        self.evaluate_button.style().polish(self.evaluate_button)

        request = self._collect_request()
        if request is None:
            return None
        try:
            outcome = self.service.analyze_and_record(
                request, record_id=self._next_record_id())
        except Exception:  # noqa: BLE001 - 系统失败不得伪装成业务结论
            _LOGGER.exception("分析执行失败（系统异常）")
            self._show_error(SYSTEM_FAILURE_TEXT)
            self.last_record_status = "SAVE_FAILED"
            return None

        self._last_request = request
        self._last_result = outcome.result
        self.last_record_status = outcome.record_status
        self.last_saved_record_id = (outcome.record.record_id if outcome.record else None)
        self._render(outcome.result)
        self._render_record_status(outcome)
        if outcome.recorded:
            self.view_record_button.setVisible(self.navigator is not None)
            self.evaluate_button.setText("再次分析")
            self.evaluate_button.setProperty("primary", False)
            self.evaluate_button.style().unpolish(self.evaluate_button)
            self.evaluate_button.style().polish(self.evaluate_button)
            self.evaluate_button.setToolTip("再次分析会产生一条新的分析记录。")
        return outcome.result

    # -- 展示 ---------------------------------------------------------------

    def _show_error(self, message: str) -> None:
        self.conclusion.setText("—")
        self.summary.setText(message)
        self.basis.setText("")
        self.values_label.setText("")
        self.reason_label.setText("")
        self.record_label.setText("")
        self.warning_label.setText("")
        self.warning_label.setVisible(False)

    def _render_record_status(self, outcome) -> None:
        """区分「已形成历史记录」与「历史记录保存失败」。"""

        if outcome.recorded:
            self.record_label.setText(
                f"已自动保存为历史记录：{outcome.record.record_id}"
                f"（可在「分析记录」中打开查看）。再次分析会生成新记录。")
            self.record_label.setStyleSheet("color: #168268;")
        elif outcome.save_failed:
            self.record_label.setText(
                "计算结果已产生，但历史记录保存失败，本次结果未被记录。"
                "请检查数据存储是否可写，或联系技术人员。")
            self.record_label.setStyleSheet("color: #B9484A;")
        else:
            reason = outcome.record_error or "当前结果不构成正式评价结论"
            self.record_label.setText(f"本次未形成历史记录：{reason}")
            self.record_label.setStyleSheet("color: #956420;")

    def _render(self, result: PumpAnalysisResult) -> None:
        """按产品信息层级渲染：结论 → 实际值与限值 → 解释 → 标准依据。

        普通层只用 Result Contract 已提供的信息；**不由 UI 发明业务解释**。
        内部证据（provenance / rule / pack hash / trace）仍完整保存在 Result 与
        Record 中，只是本页不展示。
        """

        # 第一层：最终结论 / 等级 / 不在范围 / 无法判定。
        # Phase 8 Owner 规则 7：Qt 与 Excel 的用户可见结论必须一致，
        # 因此共用 Application 的同一套结论文案。
        self.conclusion.setText(user_conclusion_text(result))
        first = [f"设备类别：{result.product_category}",
                 f"评价日期：{result.as_of.isoformat()}"]
        grade_text = user_grade_text(result.grade)
        if grade_text:
            first.append(f"能效等级：{grade_text}")
        if result.missing_fields:
            first.append("缺失信息：" + "、".join(result.missing_fields))
        # 普通结果区只显示用户可读的中文说明；内部 `issue_codes` 是审计标识，
        # 保存在 Result / Record 中，本页不展示。
        hints = issue_code_texts(result.issue_codes)
        if hints:
            first.append("提示：" + "、".join(hints))
        self.summary.setText("\n".join(first))

        # 标准生命周期提示：非阻断。单独展示，不与判定结果混排。
        self.warning_label.setText(
            "\n".join(f"⚠ {text}" for text in result.warnings))
        self.warning_label.setVisible(bool(result.warnings))

        # 第二层：关键实际值与对应限值（派生量显示 2 位小数；限值保持原文精度）。
        second: list[str] = []
        actual_key = "泵效率_%"
        actual_metric = (result.metrics_by_id or {}).get(
            PUMP_METRIC_IDS["actual_efficiency"])
        actual_efficiency = (actual_metric.value if actual_metric is not None
                             else (result.extra_metrics or {}).get(actual_key))
        if actual_efficiency is not None:
            second.append(f"实际泵效率：{format_metric(actual_efficiency, name=str(actual_key))}%")
        metrics = result.metrics_by_id or {}
        stable_thresholds = [metrics[metric_id] for metric_id in PUMP_LEVEL_LIMIT_METRIC_IDS
                             if metric_id in metrics]
        if stable_thresholds:
            # 普通界面限值保留 2 位小数（**仅显示**；等级比较仍用完整精度）。
            second.append("对应等级效率限值：" + "；".join(
                f"{metric.display_name} "
                f"{format_metric(metric.value, name=metric.display_name)}"
                for metric in stable_thresholds))
        elif result.thresholds:
            # Phase 3–8 历史结果对象仍可按原显示映射读取。
            second.append("对应等级效率限值：" + "；".join(
                f"{THRESHOLD_DISPLAY_NAMES.get(name, name)} "
                f"{format_metric(value, name=str(name))}"
                for name, value in result.thresholds.items()))
        if not second:
            second.append("本次评价没有可展示的实际值与限值对比。")
        self.values_label.setText("\n".join(second))

        # Owner Phase 8 R1 / UI02：删除「为什么是这个结果」「所选标准」
        # 「标准依据」三块普通用户解释/依据文案。
        self.reason_label.setText("")

        # 保留：关键计算参数（用户友好名称 + 合理格式化）。
        stable_details = [result.metrics_by_id[metric_id]
                          for metric_id in PUMP_ANALYSIS_DETAIL_METRIC_IDS
                          if metric_id in result.metrics_by_id]
        if stable_details:
            self.basis.setText("关键计算参数：" + "；".join(
                f"{metric.display_name} "
                f"{format_metric(metric.value, name=metric.display_name)}"
                for metric in stable_details))
        else:
            derived = result.calculation_trace.get("derived") or {}
            if derived:
                self.basis.setText("关键计算参数：" + "；".join(
                    f"{name} {format_metric(value, name=str(name))}"
                    for name, value in derived.items()))
            else:
                self.basis.setText("")
