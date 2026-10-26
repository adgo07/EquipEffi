"""语义尺寸起点；不冻结最终视觉设计。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class DesignTokens:
    spacing: int = 8
    font_size: int = 14
    title_font_size: int = 24
    control_height: int = 40
    page_margin: int = 24
    navigation_width: int = 242
    section_gap: int = 16
    radius: int = 6


TOKENS = DesignTokens()
