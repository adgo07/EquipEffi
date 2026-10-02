"""与存储技术无关的应用设置端口。"""
from typing import Protocol


class SettingsRepository(Protocol):
    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str) -> None: ...
