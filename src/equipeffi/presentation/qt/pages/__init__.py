from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..tokens import TOKENS


def placeholder_page(title: str) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(*(TOKENS.page_margin,) * 4)
    layout.setSpacing(TOKENS.section_gap)
    heading = QLabel(title)
    font = heading.font()
    font.setPixelSize(TOKENS.title_font_size)
    heading.setFont(font)
    layout.addWidget(heading)
    label = QLabel("尚未在 Phase 2 实现")
    label.setWordWrap(True)
    layout.addWidget(label)
    layout.addStretch()
    return page
