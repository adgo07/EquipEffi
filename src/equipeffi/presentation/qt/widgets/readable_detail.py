"""记录快照文本的可读排版；不重算、不补齐或改写字段。"""
from html import escape
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel


class ReadableDetail(QLabel):
    def __init__(self, text=""):
        super().__init__()
        self._plain = ""
        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.setText(text)

    def setText(self, text):
        self._plain = text
        paragraphs = []
        for line in text.splitlines():
            if not line:
                paragraphs.append('<p style="margin:14px 0 0 0;"></p>')
            elif line in ("保存时输入数据", "计算依据"):
                paragraphs.append(f'<h3 style="font-size:16px; color:#18364F; margin:18px 0 12px;">{escape(line)}</h3>')
            else:
                name, sep, value = line.partition("：")
                content = (f'<b>{escape(name)}：</b>{escape(value)}' if sep else escape(line))
                color = '#116FAE' if name == '评价结论' else '#213A4F'
                paragraphs.append(f'<p style="line-height:150%; margin:0 0 10px; color:{color};">{content}</p>')
        super().setText(''.join(paragraphs))
        self.setAccessibleDescription(text)

    def text(self):
        return self._plain

    def clear(self):
        self.setText("")
