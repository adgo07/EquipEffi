"""局部布局辅助：弹性留白，不引入页面继承或路由框架。"""
from PySide6.QtCore import QEvent, QObject


class PageGutter(QObject):
    def __init__(self, layout, surface):
        super().__init__(surface)
        self.layout, self.surface = layout, surface
        surface.installEventFilter(self)
        self.apply()

    def apply(self):
        width = self.surface.width()
        gutter = round(max(22, min(48, width * 0.034)))
        horizontal = max(gutter, (width - 1440 + 1) // 2)
        margins = self.layout.contentsMargins()
        if (margins.left(), margins.top(), margins.right(), margins.bottom()) != (horizontal, 22, horizontal, 22):
            self.layout.setContentsMargins(horizontal, 22, horizontal, 22)
            # Commit the new gutter before descendants handle their first show.
            self.layout.activate()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self.apply()
        return False


def page_gutter(layout, surface=None):
    surface = surface or layout.parentWidget()
    helper = PageGutter(layout, surface)
    # Python ownership must survive until the native surface is destroyed.
    surface._page_gutter = helper
    return helper
