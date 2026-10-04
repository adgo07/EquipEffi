"""标准库：当前正式标准的真实产品页面。

所有标准事实都来自**当前正式 Application read model**
（`CentrifugalPumpAnalysisService.standard_overview()`），它组合的是既有权威数据
（Canonical 标准包 + 产品类别目录 + 发布门禁）。

本页**不**维护第二份标准表、**不**解析 Markdown/PDF、**不**硬编码第二套标准数据。
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..labels import support_status_text
from ..tokens import TOKENS

#: 发布门禁内部取值 → 面向用户的说明。仅用于把权威取值翻译成中文，不新增事实。
_SUPPORT_STATUS_HINT = {
    "SUPPORTED": "本版本已正式支持",
    "NOT_IN_RELEASE_SCOPE": "本版本尚未开放",
}


class StandardsPage(QWidget):
    """展示当前正式标准并允许基于该标准开始分析。"""

    def __init__(self, service, navigator=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service
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
        overview = self.service.standard_overview()
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

        self.source.setText("\n".join([
            f"标准数据来源：{overview['source_file'] or '—'}",
            f"替代关系：{overview['supersession_note']}",
            f"生命周期提示：{overview['lifecycle_warning']}（仅提示，不阻止计算）",
        ]))

    # -- 动作 ---------------------------------------------------------------

    def _start_analysis(self) -> None:
        if self.navigator is not None:
            self.navigator.open_analysis()
