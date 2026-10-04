"""设置：只显示真实可配置项；**不显示内部机器键名**。

当前真实用户偏好只有日志级别与上次使用的目录（`SettingsService.KEYS`）。
**不制造**无实际价值的设置；普通用户**不得**设置 Numeric precision、rule profile、
calculator、internal ID、canonical version 或任何算法开关——这些不是用户偏好，
而是业务与工程契约，必须由版本化证据固定。

同时提供极简"关于"与运行信息。**不提前**做 installer / update system。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..tokens import TOKENS

#: 普通用户**不得**出现的设置项（机械门禁会检查它们不出现在本页）。
FORBIDDEN_SETTING_TOKENS: tuple[str, ...] = (
    "Numeric precision", "numeric_profile", "rule_profile", "calculator",
    "internal_id", "canonical", "EQUIPEFFI_PUMP_DECIMAL50_V2", "算法开关",
)


class SettingsPage(QWidget):
    """应用设置 + 关于 + 运行信息。"""

    def __init__(self, settings, service=None, *, app_version: str = "",
                 data_location: Path | None = None, navigator=None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.settings = settings
        self.service = service
        self.app_version = app_version
        self.data_location = data_location
        self.navigator = navigator

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(TOKENS.page_margin,) * 4)
        layout.setSpacing(TOKENS.section_gap)

        heading = QLabel("设置")
        font = heading.font()
        font.setPixelSize(TOKENS.title_font_size)
        font.setBold(True)
        heading.setFont(font)
        layout.addWidget(heading)

        preferences = QGroupBox("应用设置")
        preferences_layout = QVBoxLayout(preferences)
        preferences_layout.addWidget(QLabel("日志级别（记录运行信息时使用）"))
        self.log_level = QComboBox()
        self.log_level.addItems(sorted(type(settings).LEVELS))
        current = settings.get("log.level", "INFO") or "INFO"
        index = self.log_level.findText(current)
        self.log_level.setCurrentIndex(index if index >= 0 else 0)
        self.log_level.currentTextChanged.connect(self._save_log_level)
        preferences_layout.addWidget(self.log_level)

        self.last_directory = QLabel()
        self.last_directory.setWordWrap(True)
        preferences_layout.addWidget(self.last_directory)

        self.notice = QLabel("")
        self.notice.setWordWrap(True)
        preferences_layout.addWidget(self.notice)
        preferences_layout.addWidget(QLabel(
            "数值精度、规则集、计算器与标准版本等由版本化证据固定，"
            "不作为用户设置项。"))
        layout.addWidget(preferences)

        about = QGroupBox("关于")
        about_layout = QVBoxLayout(about)
        self.about = QLabel()
        self.about.setWordWrap(True)
        self.about.setTextFormat(Qt.TextFormat.PlainText)
        about_layout.addWidget(self.about)
        layout.addWidget(about)

        runtime = QGroupBox("运行信息")
        runtime_layout = QVBoxLayout(runtime)
        self.runtime = QLabel()
        self.runtime.setWordWrap(True)
        self.runtime.setTextFormat(Qt.TextFormat.PlainText)
        runtime_layout.addWidget(self.runtime)
        self.refresh_button = QPushButton("刷新运行信息")
        self.refresh_button.clicked.connect(self.refresh)
        runtime_layout.addWidget(self.refresh_button)
        layout.addWidget(runtime)

        layout.addStretch()
        self.refresh()

    # -- 数据 ---------------------------------------------------------------

    def refresh(self) -> None:
        overview = self.service.standard_overview() if self.service is not None else None
        standard_line = (f"当前正式标准：{overview['standard_code']}"
                         f"《{overview['standard_name']}》"
                         if overview else "当前正式标准：—")

        self.about.setText("\n".join([
            f"应用版本：{self.app_version or '—'}",
            standard_line,
            "适用产品：GB 19762—2025 离心泵（清水泵与石油化工泵使用同一分析流程）",
        ]))

        # 普通用户不得看到内部机器键名（last.directory / window.geometry /
        # window.state / log.level 等）。只展示业务中文名称与真实路径。
        location = str(self.data_location) if self.data_location else "（未能确定，请检查安装）"
        self.runtime.setText("\n".join([
            f"数据存储位置：{location}",
            "记录与草稿存放于该目录下的 records.sqlite；运行日志存放于 logs 子目录。",
        ]))

        last = self.settings.get("last.directory", "")
        self.last_directory.setText(
            f"上次使用的目录：{last}" if last else "上次使用的目录：（尚未使用）")

    # -- 动作 ---------------------------------------------------------------

    def _save_log_level(self, value: str) -> None:
        try:
            self.settings.set("log.level", value)
        except (ValueError, TypeError) as error:
            self.notice.setText(f"设置未保存：{error}")
            return
        self.notice.setText("已保存。")
