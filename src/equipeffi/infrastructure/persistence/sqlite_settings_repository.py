from contextlib import closing
"""唯一接线的 Phase 2 SQLite 实现：只保存应用设置。"""
from pathlib import Path
import sqlite3

from ...application.ports.settings_repository import SettingsRepository


class SqliteSettingsRepository(SettingsRepository):
    def __init__(self, database: Path):
        self.database = Path(database)

    def get(self, key: str) -> str | None:
        with closing(sqlite3.connect(self.database)) as connection, connection:
            row = connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return None if row is None else row[0]

    def set(self, key: str, value: str) -> None:
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value),
            )
