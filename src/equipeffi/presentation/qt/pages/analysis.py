"""统一 GB 19762—2025 离心泵分析页（Phase 3 P3-G02）。

一个页面同时承载清水类与石油化工类全部正式类别；用户**不**选择
`pump_water` / `pump_chemical`，也不看到任何内部 rule profile、field_id 或 rule_id。

本模块只做投影与调用：所有公式、查表、等级比较、边界判断都在 Application /
Domain 层。Qt 不得复制任何业务算法。
"""
from __future__ import annotations

from datetime import date
from typing import Callable
from uuid import uuid4

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
    QToolBox,
    QVBoxLayout,
    QWidget,
)

from ....application.services.centrifugal_pump_analysis_service import (
    PUMP_CATEGORIES,
    PUMP_CATEGORY_GROUPS,
    AnalysisError,
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

    def __init__(self, service: CentrifugalPumpAnalysisService,
                 *, workspace_id: str | None = None,
                 record_id_factory: Callable[[], str] | None = None):
        super().__init__()
        self.service = service
        self._workspace_id = workspace_id
        self._record_id_factory = record_id_factory
        self._last_request: PumpAnalysisRequest | None = None
        self._last_result: PumpAnalysisResult | None = None
        self._saved_record_id: str | None = None
        #: 最近一次保存成功的正式记录编号（供 shell / 测试读取）。
        self.last_saved_record_id: str | None = None
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

        # 技术详情渐进展示：内部 rule / data id / Numeric Profile 归此处，
        # 默认折叠，不占据普通业务结果区（但审计能力保留）。
        self.technical_box = QToolBox()
        technical_page = QWidget()
        technical_layout = QVBoxLayout(technical_page)
        self.technical = QLabel("")
        self.technical.setWordWrap(True)
        self.technical.setTextFormat(Qt.TextFormat.PlainText)
        self.technical.setAlignment(Qt.AlignmentFlag.AlignTop)
        technical_layout.addWidget(self.technical)
        technical_layout.addStretch()
        self.technical_box.addItem(technical_page, "技术详情（规则编号、数据版本、数值配置）")
        self.technical_box.setCurrentIndex(-1)
        layout.addWidget(self.technical_box)
        return group

    # -- 交互 ---------------------------------------------------------------

    def current_category(self) -> str | None:
        return self.category.currentData()

    def _on_category_changed(self, *_: object) -> None:
        category = self.current_category()
        entry = next((c for c in PUMP_CATEGORIES if c.visible_name == category), None)
        if entry is None:
            self.category_help.setText(
                "请选择产品类别。若无法判断，可选“不确定类别”查看判断说明。")
        else:
            self.category_help.setText(entry.help_text)
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
        self._last_request = request
        self._last_result = result
        self._render(result)
        self.finalize_button.setEnabled(result.finalizable)
        return result

    def finalize(self) -> str:
        """把当前分析固化为正式记录；返回状态说明文本（同时显示在结果区）。

        必须携带产生该结果的 request（指纹核对）与草稿修订号；任何不一致都会被
        Application 层拒绝，本页不自行放宽。
        """

        if self._last_result is None or self._last_request is None:
            self._show_error("请先执行分析，再保存正式记录。")
            return "NO_RESULT"
        if not self._last_result.finalizable:
            self._show_error(self._last_result.not_finalizable_reason or "当前结果不允许保存。")
            return "NOT_FINALIZABLE"

        # 保存前必须确认表单自分析后没有被修改，否则会把旧结果当成新输入保存。
        current = self._collect_request()
        if current is None:
            return "REJECTED"
        if current.request_fingerprint() != self._last_result.request_fingerprint:
            self._show_error(
                "输入已在分析之后被修改，当前结果已过期；请重新分析后再保存正式记录。")
            return "STALE_RESULT"

        workspace_id = self._workspace_id
        if workspace_id is not None:
            try:
                # 草稿必须先落盘，Finalize 才能核对修订号。
                workspace = self.service.save_workspace_from_request(
                    workspace_id, self._last_request)
                request = self.service.request_from_workspace(workspace)
                result = self.service.evaluate(request)
                self._last_request, self._last_result = request, result
                if not result.finalizable:
                    self._show_error(result.not_finalizable_reason or "当前结果不允许保存。")
                    return "NOT_FINALIZABLE"

                record_id = self._next_record_id()
                record = self.service.finalize(record_id=record_id, workspace_id=workspace_id,
                                               request=request, result=result)
            except AnalysisError as error:
                self._show_error(str(error))
                return "REJECTED"
        else:
            try:
                record_id = self._next_record_id()
                record = self.service.finalize(
                    record_id=record_id, workspace_id=None,
                    request=self._last_request, result=self._last_result)
            except AnalysisError as error:
                self._show_error(str(error))
                return "REJECTED"

        self._saved_record_id = record.record_id
        self.last_saved_record_id = record.record_id
        self.finalize_button.setEnabled(False)
        self.summary.setText(
            f"{self.summary.text()}\n正式记录已保存：{record.record_id}"
            f"（{record.finalized_at_utc}）")
        return "SAVED"

    def load_workspace(self, workspace_id: str) -> bool:
        """把草稿载入表单（Reopen/继续编辑入口）。"""

        workspace = self.service.load_workspace(workspace_id)
        if workspace is None:
            return False
        self._workspace_id = workspace_id
        index = self.category.findData(workspace.product_category)
        if index >= 0:
            self.category.setCurrentIndex(index)
        self.as_of.setText(workspace.as_of)
        payload = workspace.payload
        for key, edit in self.point_inputs.items():
            edit.setText("" if payload.get(key) in (None, "") else str(payload[key]))
        suction = payload.get("suction")
        suction_index = self.suction.findData(suction) if suction else 0
        self.suction.setCurrentIndex(max(suction_index, 0))
        if self.stages.isEnabled():
            stages = payload.get("stages")
            self.stages.setText("" if stages in (None, "") else str(stages))
        self.project_name.setText(str(payload.get("project_name") or ""))
        self.equipment_no.setText(str(payload.get("equipment_no") or ""))
        self._last_request = self._last_result = None
        self.finalize_button.setEnabled(False)
        return True

    def _next_record_id(self) -> str:
        if self._record_id_factory is not None:
            return self._record_id_factory()
        return f"{self._workspace_id or 'ANALYSIS'}-{uuid4().hex[:12]}"

    # -- 展示 ---------------------------------------------------------------

    def _show_error(self, message: str) -> None:
        self.conclusion.setText("—")
        self.summary.setText(message)
        self.basis.setText("")
        self.technical.setText("")
        self.finalize_button.setEnabled(False)

    def _render(self, result: PumpAnalysisResult) -> None:
        self.conclusion.setText(result.ui_conclusion)
        lines = [f"设备类别：{result.product_category}",
                 f"评价日期：{result.as_of.isoformat()}"]
        if result.grade:
            lines.append(f"能效等级：{result.grade}")
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
        basis_lines.append("标准依据：GB 19762—2025《离心泵能效限定值及能效等级》")
        if not result.finalizable and result.not_finalizable_reason:
            basis_lines.append("不可保存原因：" + result.not_finalizable_reason)
        self.basis.setText("\n".join(basis_lines))

        # 内部 Rule / data id 属于技术详情，不占普通业务结果区。
        self._render_technical(result)

    def _render_technical(self, result: PumpAnalysisResult) -> None:
        standard = result.references.get("standard") or {}
        rows = [
            ("评价状态", result.evaluation_status or "—"),
            ("类别状态", result.category_status or "—"),
            ("命中规则", result.matched_rule_id or "—"),
            ("规则集", standard.get("rule_profile") or "—"),
            ("标准包", standard.get("pack_id") or "—"),
            ("数据版本", standard.get("data_version") or "—"),
            ("数值配置", result.references.get("numeric_profile_id") or "—"),
            ("结果契约", result.references.get("result_contract_version") or "—"),
        ]
        self.technical.setText("\n".join(f"{name}：{value}" for name, value in rows))
