"""可展开/收起的技术详情容器（Phase 3 R1）。

`QToolBox.setCurrentIndex(-1)` 在部分平台上会自行选中第一页，导致"默认折叠"
只是名义上的。这里用一个显式的切换按钮 + 内容容器实现真实折叠：

- 构造后内容**默认隐藏**（`setVisible(False)`，不是仅靠样式）；
- 点击标题栏切换展开/收起；
- `is_expanded()` / `set_expanded()` 供测试与调用方使用。

本模块只做展示，不含任何业务逻辑。
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout, QWidget


class CollapsibleSection(QWidget):
    """带标题按钮的可折叠区域，默认收起。"""

    def __init__(self, title: str, *, expanded: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self._title = title
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.toggle_button = QPushButton()
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(expanded)
        self.toggle_button.clicked.connect(self._on_toggled)
        self.toggle_button.setStyleSheet("text-align: left; padding: 4px;")
        layout.addWidget(self.toggle_button)

        self.content = QFrame()
        self.content.setFrameShape(QFrame.Shape.StyledPanel)
        self.content.setVisible(expanded)
        layout.addWidget(self.content)

        self._sync_button_text()

    # -- 状态 ---------------------------------------------------------------

    def _sync_button_text(self) -> None:
        arrow = "▼" if self.toggle_button.isChecked() else "▶"
        self.toggle_button.setText(f"{arrow} {self._title}")

    def _on_toggled(self, checked: bool) -> None:
        self.set_expanded(bool(checked))

    def is_expanded(self) -> bool:
        return self.toggle_button.isChecked() and self.content.isVisible()

    def set_expanded(self, expanded: bool) -> None:
        self.toggle_button.setChecked(bool(expanded))
        self.content.setVisible(bool(expanded))
        self._sync_button_text()

    def set_content(self, widget: QWidget, layout: QVBoxLayout | None = None) -> None:
        """把内容控件放入折叠区。"""

        target = layout if layout is not None else QVBoxLayout(self.content)
        target.setContentsMargins(6, 6, 6, 6)
        target.addWidget(widget)
