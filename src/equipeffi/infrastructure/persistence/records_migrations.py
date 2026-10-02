"""`records.sqlite` 的独立 forward-only 迁移。

策略：`NEVER_DESTRUCTIVE_RECORD_ASSET`。

与 `user.sqlite` 的迁移链**完全独立**：本模块有自己的迁移列表、自己的历史表
(`record_schema_migration_history`) 和独立的 runner。不得把 records 接入
`migrations.migrate_user_database`，也不得复用 `migration_history` 表。

只允许 forward-only、additive / compatible migration。禁止 DROP 正式记录、
覆盖历史 Record、自动降级、重建整个 `records.sqlite` 或破坏性重写。
若必须做破坏性迁移，必须停机请求用户决定。
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import sqlite3

#: 本 runner 只管理的数据库文件名。
RECORDS_DB_NAME = "records.sqlite"
RECORDS_HISTORY_TABLE = "record_schema_migration_history"

#: 禁止出现在 records 迁移语句中的破坏性关键字（防御性校验）。
_DESTRUCTIVE_TOKENS = ("DROP TABLE", "DROP INDEX", "DROP COLUMN", "TRUNCATE", "DELETE FROM")


class RecordsMigrationError(RuntimeError):
    """records 迁移版本、校验和或破坏性语句校验失败。"""


@dataclass(frozen=True)
class RecordsMigration:
    schema_version: int
    migration_id: str
    statements: tuple[str, ...]

    @property
    def checksum(self) -> str:
        return sha256("\n".join(self.statements).encode("utf-8")).hexdigest()

    def assert_additive(self) -> None:
        """拒绝任何破坏性语句，保证 records 资产不被不可逆重写。"""

        for statement in self.statements:
            upper = statement.upper()
            for token in _DESTRUCTIVE_TOKENS:
                if token in upper:
                    raise RecordsMigrationError(
                        f"records 迁移 {self.migration_id} 含破坏性语句 {token}；"
                        "records.sqlite 为 NEVER_DESTRUCTIVE_RECORD_ASSET，必须停机请求用户决定"
                    )


RECORDS_MIGRATIONS: tuple[RecordsMigration, ...] = (
    RecordsMigration(1, "001_create_workspace_and_record", (
        """
        CREATE TABLE IF NOT EXISTS workspace (
            workspace_id TEXT PRIMARY KEY,
            standard_code TEXT NOT NULL,
            device_type TEXT NOT NULL,
            product_category TEXT,
            rule_profile TEXT,
            as_of TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            schema_version INTEGER NOT NULL,
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS record (
            record_id TEXT PRIMARY KEY,
            workspace_id TEXT,
            standard_code TEXT NOT NULL,
            standard_version TEXT,
            device_type TEXT NOT NULL,
            product_category TEXT,
            rule_profile TEXT,
            as_of TEXT NOT NULL,
            evaluation_status TEXT NOT NULL,
            grade TEXT,
            ui_conclusion TEXT NOT NULL,
            input_snapshot_json TEXT NOT NULL,
            result_snapshot_json TEXT NOT NULL,
            reference_snapshot_json TEXT NOT NULL,
            ruleset_version TEXT,
            calculator_version TEXT,
            numeric_profile_id TEXT,
            canonical_version TEXT,
            canonical_package_hash TEXT,
            result_contract_version TEXT,
            schema_version INTEGER NOT NULL,
            created_at_utc TEXT NOT NULL,
            finalized_at_utc TEXT NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_record_finalized_at ON record (finalized_at_utc DESC)",
        "CREATE INDEX IF NOT EXISTS idx_workspace_updated_at ON workspace (updated_at_utc DESC)",
    )),
)


def migrate_records_database(path: Path, *, app_version: str,
                             migrations: tuple[RecordsMigration, ...] = RECORDS_MIGRATIONS) -> None:
    """把 `records.sqlite` 前向迁移到当前版本。

    幂等：重复运行不会重复建表，也不会改写已登记的历史。
    forward-only：只追加尚未应用的迁移；不提供 down migration。
    """

    path = Path(path)
    if path.name != RECORDS_DB_NAME:
        raise RecordsMigrationError(
            f"本 runner 只管理 {RECORDS_DB_NAME}；不得把其他数据库接入 records 迁移链"
        )

    versions = [m.schema_version for m in migrations]
    if versions != list(range(1, len(migrations) + 1)):
        raise RecordsMigrationError("records 迁移版本必须连续且不重复")
    for migration in migrations:
        migration.assert_additive()

    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(f"""CREATE TABLE IF NOT EXISTS {RECORDS_HISTORY_TABLE} (
            schema_version INTEGER PRIMARY KEY,
            migration_id TEXT UNIQUE NOT NULL,
            checksum TEXT NOT NULL,
            applied_at_utc TEXT NOT NULL,
            applied_by_app_version TEXT NOT NULL
        )""")
        history = connection.execute(
            f"SELECT schema_version, migration_id, checksum FROM {RECORDS_HISTORY_TABLE} "
            "ORDER BY schema_version"
        ).fetchall()

        if [row[0] for row in history] != list(range(1, len(history) + 1)):
            raise RecordsMigrationError("records 迁移历史存在缺口；不得自动重建记录库")
        for version, migration_id, checksum in history:
            if version > len(migrations):
                raise RecordsMigrationError(
                    "records 库版本高于当前应用支持版本；不得自动降级或重建"
                )
            expected = migrations[version - 1]
            if (migration_id, checksum) != (expected.migration_id, expected.checksum):
                raise RecordsMigrationError(
                    f"records 迁移校验和或身份不匹配：{migration_id}"
                )

        for migration in migrations[len(history):]:
            for statement in migration.statements:
                connection.execute(statement)
            connection.execute(
                f"INSERT INTO {RECORDS_HISTORY_TABLE} VALUES (?, ?, ?, ?, ?)",
                (
                    migration.schema_version,
                    migration.migration_id,
                    migration.checksum,
                    datetime.now(timezone.utc).isoformat(),
                    app_version,
                ),
            )
