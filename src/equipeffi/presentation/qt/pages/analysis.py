"""统一 GB 19762—2025 离心泵分析页（Phase 3 P3-G02）。

一个页面同时承载清水类与石油化工类全部正式类别；用户**不**选择
`pump_water` / `pump_chemical`，也不看到任何内部 rule profile、field_id 或 rule_id。

本模块只做投影与调用：所有公式、查表、等级比较、边界判断都在 Application /
Domain 层。Qt 不得复制任何业务算法。
"""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
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
    CentrifugalPumpAnalysisService,
    PumpAnalysisRequest,
    PumpAnalysisResult,
)
from ..tokens import TOKENS

#: 规定点参数字段（用户可见标签 + 内部字段名）。
POINT_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("QBEP", "规定点流量 Q_BEP", "m³/h"),
    ("HBEP", "规定点扬程 H_BEP", "m"),
    ("speed", "规定点转速 n", "r/min"),
    ("efficiency", "规定点泵效率 η", "%"),
)

#: 吸入方式选项（沿用已批准业务枚举，不在 UI 新造值）。
SUCTION_OPTIONS: tuple[str, ...] = ("单吸", "双吸")

#: 自动锁定的级数（类别文本前缀只有一个标准级数的类别）。
_SINGLE_STAGE_CATEGORIES = frozenset(
    {"单级单吸清水离心泵", "单级双吸清水离心泵", "管道清水离心泵", "单级石油化工离心泵"}
)


class AnalysisPage(QWidget):
    """统一离心泵分析页。"""

    def __init__(self, service: CentrifugalPumpAnalysisService):
        super().__init__()
        self.service = service
        self._build()

    # -- 构建 ---------------------------------------------------------------

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(*(TOKENS.page_margin,) * 4)
        outer.setSpacing(TOKENS.section_gap)

        heading = QLabel("离心泵能效分析")
        font = heading.font()
        font.setPixelSize(TOKENS.title_font_size)
        heading.setFont(font)
        outer.addWidget(heading)

        standard = QLabel("适用标准：GB 19762—2025《离心泵能效限定值及能效等级》")
        standard.setWordWrap(True)
        outer.addWidget(standard)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setSpacing(TOKENS.section_gap)
        layout.addWidget(self._basic_group())
        layout.addWidget(self._category_group())
        layout.addWidget(self._points_group())
        layout.addWidget(self._actions())
        layout.addWidget(self._result_group())
        layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        # 先建好输入控件再应用一次类别联动，避免信号早于控件创建。
        self._on_category_changed()

    def _basic_group(self) -> QGroupBox:
        group = QGroupBox("基本信息")
        form = QFormLayout(group)
        self.project_name = QLineEdit()
        self.project_name.setPlaceholderText("可选")
        self.equipment_no = QLineEdit()
        self.equipment_no.setPlaceholderText("可选")
        self.as_of = QLineEdit(date.today().isoformat())
        self.as_of.setToolTip("评价日期决定使用哪个版本的标准；计算与保存都使用该日期。")
        form.addRow("企业/项目名称", self.project_name)
        form.addRow("设备编号", self.equipment_no)
        form.addRow("评价日期", self.as_of)
        return group

    def _category_group(self) -> QGroupBox:
        group = QGroupBox("产品类别")
        layout = QVBoxLayout(group)
        self.category = QComboBox()
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
        self.category.setCurrentIndex(self._first_selectable_index())
        layout.addWidget(self.category)
        self.category_help = QLabel("")
        self.category_help.setWordWrap(True)
        layout.addWidget(self.category_help)
        self.category.currentIndexChanged.connect(self._on_category_changed)
        return group

    def _points_group(self) -> QGroupBox:
        group = QGroupBox("规定点参数（BEP）")
        grid = QGridLayout(group)
        self.point_inputs: dict[str, QLineEdit] = {}
        for row, (key, label, unit) in enumerate(POINT_FIELDS):
            grid.addWidget(QLabel(f"{label}（{unit}）"), row, 0)
            edit = QLineEdit()
            edit.setPlaceholderText("请输入标准规定点数值")
            grid.addWidget(edit, row, 1)
            self.point_inputs[key] = edit
        grid.addWidget(QLabel("吸入方式"), len(POINT_FIELDS), 0)
        self.suction = QComboBox()
        self.suction.addItem("请选择", None)
        for option in SUCTION_OPTIONS:
            self.suction.addItem(option, option)
        grid.addWidget(self.suction, len(POINT_FIELDS), 1)
        grid.addWidget(QLabel("级数"), len(POINT_FIELDS) + 1, 0)
        self.stages = QLineEdit()
        grid.addWidget(self.stages, len(POINT_FIELDS) + 1, 1)
        return group

    def _actions(self) -> QWidget:
        holder = QFrame()
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        self.evaluate_button = QPushButton("分析")
        self.evaluate_button.clicked.connect(self.evaluate)
        self.finalize_button = QPushButton("保存为正式记录")
        self.finalize_button.clicked.connect(self.finalize)
        self.finalize_button.setEnabled(False)
        layout.addWidget(self.evaluate_button)
        layout.addWidget(self.finalize_button)
        layout.addStretch()
        return holder

    def _result_group(self) -> QGroupBox:
        group = QGroupBox("分析结果")
        layout = QVBoxLayout(group)
        self.conclusion = QLabel("—")
        font = self.conclusion.font()
        font.setPixelSize(TOKENS.title_font_size)
        font.setBold(True)
        self.conclusion.setFont(font)
        layout.addWidget(self.conclusion)
        self.summary = QLabel("尚未分析。")
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.summary)
        self.basis = QLabel("")
        self.basis.setWordWrap(True)
        self.basis.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.basis)
        return group

    # -- 交互 ---------------------------------------------------------------

    def _first_selectable_index(self) -> int:
        """第一个可选项索引（跳过组标题分隔项）。"""

        for index in range(self.category.count()):
            if self.category.itemData(index):
                return index
        return 0

    def current_category(self) -> str | None:
        return self.category.currentData()

    def _on_category_changed(self, *_: object) -> None:
        category = self.current_category()
        entry = next((c for c in PUMP_CATEGORIES if c.visible_name == category), None)
        self.category_help.setText(entry.help_text if entry else "请选择产品类别。")
        if category in _SINGLE_STAGE_CATEGORIES:
            # 类别本身已唯一决定级数；这是既有业务契约，不是 UI 新造规则。
            self.stages.setText("1")
            self.stages.setEnabled(False)
        else:
            self.stages.setEnabled(True)
            if category is None:
                self.stages.clear()

    def _collect_request(self) -> PumpAnalysisRequest | None:
        category = self.current_category()
        if not category:
            self._show_error("请先选择产品类别。")
            return None
        try:
            as_of = date.fromisoformat(self.as_of.text().strip())
        except ValueError:
            self._show_error("评价日期格式应为 YYYY-MM-DD。")
            return None
        values = {key: (edit.text().strip() or None)
                  for key, edit in self.point_inputs.items()}
        return PumpAnalysisRequest(
            product_category=category,
            as_of=as_of,
            suction=self.suction.currentData(),
            stages=self.stages.text().strip() or None,
            project_name=self.project_name.text().strip() or None,
            equipment_no=self.equipment_no.text().strip() or None,
            **values,
        )

    def evaluate(self) -> PumpAnalysisResult | None:
        request = self._collect_request()
        if request is None:
            return None
        result = self.service.evaluate(request)
        self._render(result)
        self.finalize_button.setEnabled(result.finalizable)
        return result

    def finalize(self) -> None:
        """由外部注入 Record 写入前不执行；Phase 3 在 shell 层装配。"""

        self._show_error("保存需要先装配正式记录存储。")

    # -- 展示 ---------------------------------------------------------------

    def _show_error(self, message: str) -> None:
        self.conclusion.setText("—")
        self.summary.setText(message)
        self.basis.setText("")
        self.finalize_button.setEnabled(False)

    def _render(self, result: PumpAnalysisResult) -> None:
        self.conclusion.setText(result.ui_conclusion)
        lines = [f"设备类别：{result.product_category}",
                 f"评价日期：{result.as_of.isoformat()}"]
        if result.grade:
            lines.append(f"能效等级：{result.grade}")
        if result.evaluation_status:
            lines.append(f"评价状态：{result.evaluation_status}")
        if result.missing_fields:
            lines.append("缺失信息：" + "、".join(result.missing_fields))
        if result.issue_codes:
            lines.append("提示：" + "、".join(result.issue_codes))
        lines.append(f"判定说明：{result.explanation}")
        self.summary.setText("\n".join(lines))

        basis_lines: list[str] = []
        if result.thresholds:
            basis_lines.append("等级阈值：" + "；".join(
                f"{name} {value}" for name, value in result.thresholds.items()))
        derived = result.calculation_trace.get("derived") or {}
        if derived:
            basis_lines.append("关键计算参数：" + "；".join(
                f"{name} {value}" for name, value in derived.items()))
        if result.extra_metrics:
            basis_lines.append("实际参数：" + "；".join(
                f"{name} {value}" for name, value in result.extra_metrics.items()))
        if result.matched_rule_id:
            basis_lines.append(f"标准依据：GB 19762—2025（命中规则 {result.matched_rule_id}）")
        if not result.finalizable and result.not_finalizable_reason:
            basis_lines.append("不可保存原因：" + result.not_finalizable_reason)
        self.basis.setText("\n".join(basis_lines))
