from contextlib import closing
"""仅 user.sqlite 的非破坏性前向迁移。catalog 可重建，records 不在此切片。"""
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import sqlite3

DB_POLICIES = {
    "catalog.sqlite": "REBUILDABLE_DERIVED",
    "user.sqlite": "MIGRATABLE_USER_ASSET",
    "records.sqlite": "NEVER_DESTRUCTIVE_RECORD_ASSET",
}


class MigrationError(RuntimeError):
    """迁移版本或校验和不匹配；不得自动重建用户资产。"""


@dataclass(frozen=True)
class Migration:
    schema_version: int
    migration_id: str
    statements: tuple[str, ...]

    @property
    def checksum(self) -> str:
        return sha256("\n".join(self.statements).encode("utf-8")).hexdigest()


USER_MIGRATIONS = (Migration(1, "001_create_settings", (
    "CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
)),)


def migrate_user_database(path: Path, *, app_version: str, migrations=USER_MIGRATIONS) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("""CREATE TABLE IF NOT EXISTS migration_history (
            schema_version INTEGER PRIMARY KEY,
            migration_id TEXT UNIQUE NOT NULL,
            checksum TEXT NOT NULL,
            applied_at_utc TEXT NOT NULL,
            applied_by_app_version TEXT NOT NULL
        )""")
        history = connection.execute(
            "SELECT schema_version, migration_id, checksum FROM migration_history ORDER BY schema_version"
        ).fetchall()
        versions = [m.schema_version for m in migrations]
        if versions != list(range(1, len(migrations) + 1)):
            raise MigrationError("迁移版本必须连续且不重复")
        if [row[0] for row in history] != list(range(1, len(history) + 1)):
            raise MigrationError("用户库迁移历史存在缺口")
        for version, migration_id, checksum in history:
            if version > len(migrations):
                raise MigrationError("用户库版本高于当前应用支持版本")
            expected = migrations[version - 1]
            if (migration_id, checksum) != (expected.migration_id, expected.checksum):
                raise MigrationError(f"迁移校验和或身份不匹配：{migration_id}")
        for migration in migrations[len(history):]:
            for statement in migration.statements:
                connection.execute(statement)
            connection.execute("INSERT INTO migration_history VALUES (?, ?, ?, ?, ?)", (
                migration.schema_version, migration.migration_id, migration.checksum,
                datetime.now(timezone.utc).isoformat(), app_version,
            ))
