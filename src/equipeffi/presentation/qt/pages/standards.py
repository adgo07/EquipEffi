"""标准库：当前正式标准的真实产品页面。

所有标准事实都来自**当前正式 Application read model**
（`CentrifugalPumpAnalysisService.standard_overview()`），它组合的是既有权威数据
（Canonical 标准包 + 产品类别目录 + 发布门禁）。

本页**不**维护第二份标准表、**不**解析 Markdown/PDF、**不**硬编码第二套标准数据。
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..labels import support_status_text
from ..tokens import TOKENS

#: 标准生命周期内部状态 → 面向用户的中文说明（只翻译，不新增事实）。
LIFECYCLE_STATE_LABELS = {
    "EFFECTIVE": "已实施",
    "NOT_YET_EFFECTIVE": "尚未实施",
    "UNKNOWN": "未提供实施日期",
}

#: 发布门禁内部取值 → 面向用户的说明。仅用于把权威取值翻译成中文，不新增事实。
_SUPPORT_STATUS_HINT = {
    "SUPPORTED": "本版本已正式支持",
    "NOT_IN_RELEASE_SCOPE": "本版本尚未开放",
}


class StandardsPage(QWidget):
    """展示当前正式标准并允许基于该标准开始分析。"""

    def __init__(self, service, navigator=None, parent: QWidget | None = None,
                 *, transformer=None, motor=None):
        super().__init__(parent)
        self.service = service
        self.transformer_service = transformer
        self.motor_service = motor
        self.navigator = navigator
        self.standard_code: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(TOKENS.page_margin,) * 4)
        layout.setSpacing(TOKENS.section_gap)

        heading = QLabel("标准库")
        font = heading.font()
        font.setPixelSize(TOKENS.title_font_size)
        font.setBold(True)
        heading.setFont(font)
        layout.addWidget(heading)

        self.intro = QLabel()
        self.intro.setWordWrap(True)
        self.intro.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.intro)

        self.standard_selector = None
        if transformer is not None:
            self.standard_selector = QComboBox()
            self.standard_selector.setObjectName("standardSelector")
            pump_overview = service.standard_overview()
            transformer_overview = transformer.standard_overview()
            self.standard_selector.addItem(
                f"{pump_overview['standard_code']} · {pump_overview['standard_name']}",
                pump_overview["standard_code"])
            self.standard_selector.addItem(
                f"{transformer_overview['standard_code']} · {transformer_overview['name']}",
                transformer_overview["standard_code"])
            if motor is not None:
                motor_overview = motor.standard_overview()
                self.standard_selector.addItem(
                    f"{motor_overview['standard_code']} · {motor_overview['name']}（验收候选）",
                    motor_overview["standard_code"])
            self.standard_selector.currentIndexChanged.connect(self.refresh)
            layout.addWidget(self.standard_selector)

        facts_group = QGroupBox("标准信息")
        self.facts = QLabel()
        self.facts.setWordWrap(True)
        self.facts.setTextFormat(Qt.TextFormat.PlainText)
        facts_layout = QVBoxLayout(facts_group)
        facts_layout.addWidget(self.facts)
        layout.addWidget(facts_group)

        scopes_group = QGroupBox("适用范围与软件支持状态")
        self.scopes = QLabel()
        self.scopes.setWordWrap(True)
        self.scopes.setTextFormat(Qt.TextFormat.PlainText)
        scopes_layout = QVBoxLayout(scopes_group)
        scopes_layout.addWidget(self.scopes)
        layout.addWidget(scopes_group)

        source_group = QGroupBox("来源与替代关系")
        self.source = QLabel()
        self.source.setWordWrap(True)
        self.source.setTextFormat(Qt.TextFormat.PlainText)
        source_layout = QVBoxLayout(source_group)
        source_layout.addWidget(self.source)
        layout.addWidget(source_group)
        self.source_group = source_group
        if transformer is not None:
            # This read model has no user-facing source/document view; keep the
            # older pump presentation intact while the new standard is selected.
            source_group.setVisible(False)

        actions = QHBoxLayout()
        self.start_button = QPushButton("基于该标准开始分析")
        self.start_button.clicked.connect(self._start_analysis)
        actions.addWidget(self.start_button)
        actions.addStretch()
        layout.addLayout(actions)
        layout.addStretch()

        self.refresh()

    # -- 数据 ---------------------------------------------------------------

    def refresh(self) -> None:
        selected_code = (self.standard_selector.currentData()
                         if self.standard_selector is not None else None)
        if self.motor_service is not None and selected_code == "GB 18613-2020":
            self._render_transformer(self.motor_service.standard_overview())
            self.intro.setText("电动机接入验收候选；尚未宣布正式支持。")
            return
        if (self.transformer_service is not None
                and selected_code == self.transformer_service.standard_overview()["standard_code"]):
            self._render_transformer(self.transformer_service.standard_overview())
            return

        overview = self.service.standard_overview()
        self.source_group.setVisible(True)
        self._render_pump(overview)

    def _render_pump(self, overview) -> None:
        self.standard_code = overview["standard_code"]

        self.intro.setText(
            "当前版本正式使用的标准。标准参数、限值与本项目对标准依据的引用，"
            "均来自该标准的权威数据；本页不另存一份标准数据。")

        self.facts.setText("\n".join([
            f"标准号：{overview['standard_code']}",
            f"标准名称：{overview['standard_name']}",
            f"状态：{overview['status'] or '—'}",
            f"实施日期：{overview['effective_date'] or '—'}",
            f"数据版本：{overview['data_version'] or '—'}",
            f"评价日期说明：{overview['as_of_policy']}",
        ]))

        lines: list[str] = []
        lines.append("支持类别：" + "、".join(overview["supported_categories"]))
        if overview["special_categories"]:
            lines.append("其他可选项：" + "、".join(overview["special_categories"]))
        lines.append("")
        for scope in overview["scopes"]:
            status = support_status_text(scope["support_status"])
            hint = _SUPPORT_STATUS_HINT.get(str(scope["support_status"]), "")
            categories = "、".join(scope["categories"]) or "—"
            lines.append(f"{categories}：{status}" + (f"（{hint}）" if hint else ""))
        self.scopes.setText("\n".join(lines))

        lines = [
            f"标准数据来源：{overview['source_file'] or '—'}",
            f"替代关系：{overview['supersession_note']}",
            f"生命周期状态：{LIFECYCLE_STATE_LABELS.get(overview['lifecycle_state'], '—')}",
        ]
        # 生命周期提示由**真实日期**推导；无提示时不显示占位文字。
        if overview["lifecycle_warning"]:
            lines.append(f"提示：{overview['lifecycle_warning']}（仅提示，不阻止计算）")
        self.source.setText("\n".join(lines))

    def _render_transformer(self, overview) -> None:
        self.standard_code = overview["standard_code"]
        self.source_group.setVisible(False)
        self.intro.setText(
            "本标准已接入当前软件实现；软件支持状态与标准正式发布状态分别管理。")
        self.facts.setText("\n".join((
            f"标准号：{overview['standard_code']}",
            f"标准名称：{overview['name']}",
            f"版本：{overview['edition']}",
            f"实施日期：{overview.get('effective_date') or '—'}",
        )))
        status = overview.get("support_status")
        status_text = ("已接入，尚待正式支持验收"
                       if status == "IMPLEMENTED" else "当前状态以软件记录为准")
        lines = [f"软件状态：{status_text}"]
        scope = str(overview.get("scope_text") or "").strip()
        if scope:
            lines.append(f"适用范围：{scope}")
        notes = str(overview.get("notes") or "").strip()
        if notes:
            lines.append(f"说明：{notes}")
        self.scopes.setText("\n".join(lines))

    # -- 动作 ---------------------------------------------------------------

    def _start_analysis(self) -> None:
        if self.navigator is not None:
            self.navigator.open_analysis(standard_code=self.standard_code)
