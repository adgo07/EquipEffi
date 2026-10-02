"""Phase 2 唯一正式应用切片；仅管理 UI/运行设置。"""
from ..ports.settings_repository import SettingsRepository


class SettingsService:
    KEYS = frozenset({"window.geometry", "window.state", "log.level", "last.directory"})
    LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})

    def __init__(self, repository: SettingsRepository):
        self._repository = repository

    def get(self, key: str, default: str = "") -> str:
        self._check_key(key)
        value = self._repository.get(key)
        return default if value is None else value

    def set(self, key: str, value: str) -> None:
        self._check_key(key)
        if not isinstance(value, str):
            raise TypeError("设置值必须为字符串")
        if key == "log.level" and value not in self.LEVELS:
            raise ValueError("日志级别无效")
        self._repository.set(key, value)

    @classmethod
    def _check_key(cls, key: str) -> None:
        if key not in cls.KEYS:
            raise ValueError("本阶段只允许应用设置，不能保存业务数据")
