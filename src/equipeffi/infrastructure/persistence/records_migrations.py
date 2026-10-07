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
    # 002：为 workspace 增加修订号。必须作为**新迁移**追加，不得改写 001，
    # 否则已存在的 records.sqlite 会因 001 的 checksum 变化而被拒绝打开。
    # `ALTER TABLE ... ADD COLUMN` 是 additive / compatible，符合
    # NEVER_DESTRUCTIVE_RECORD_ASSET；已有草稿行取默认值 1。
    RecordsMigration(2, "002_add_workspace_revision", (
        "ALTER TABLE workspace ADD COLUMN revision INTEGER NOT NULL DEFAULT 1",
    )),
    # 003（Phase 8）：Excel 批量评价的**最小 additive** 总结记录。
    #
    # Owner 规则 9/10：Excel 批量评价**不得**为每个数据行创建普通单台 Record；
    # 一次 Workbook / 一次离心泵批量评价 → 一条 batch_record 总结记录，逐设备
    # 详细结果保存在结果 Workbook。允许为此新增最小 additive 持久化结构，
    # **不得**改变现有单台 `record` 语义——因此这里新建独立表，绝不动 `record`。
    #
    # 只存"这一次批次"的客观事实：载体文件与哈希、行数统计、结论分布（JSON）、
    # 不合法行（JSON）。**不**复制逐设备结果、**不**建 lineage / audit 通用框架。
    RecordsMigration(3, "003_create_batch_record", (
        """
        CREATE TABLE IF NOT EXISTS batch_record (
            batch_record_id TEXT PRIMARY KEY,
            standard_code TEXT NOT NULL,
            device_type TEXT NOT NULL,
            source_workbook TEXT NOT NULL,
            source_workbook_sha256 TEXT NOT NULL,
            result_workbook TEXT,
            result_workbook_sha256 TEXT,
            total_rows INTEGER NOT NULL,
            evaluated_count INTEGER NOT NULL,
            unevaluated_count INTEGER NOT NULL,
            invalid_count INTEGER NOT NULL,
            summary_json TEXT NOT NULL,
            schema_version INTEGER NOT NULL,
            created_at_utc TEXT NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_batch_record_created_at "
        "ON batch_record (created_at_utc DESC)",
    )),
    # 004（Phase 8B）：补齐 Owner 规格要求的批次记录字段。
    #
    # 003 已随 Phase 8 的首个提交进入仓库与用户数据库，**不得改写**它
    # （否则既有 records.sqlite 会因 checksum 变化而被拒绝打开）。
    # 因此新增 004 以 `ALTER TABLE ... ADD COLUMN` 追加列——additive / compatible，
    # 旧库升级后新列为 NULL / 默认值，既有数据不受影响。
    #
    # 仍**不**建逐行明细表：逐设备详细结果保存在结果 Workbook。
    RecordsMigration(4, "004_extend_batch_record", (
        "ALTER TABLE batch_record ADD COLUMN sheet_name TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE batch_record ADD COLUMN evaluation_date TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE batch_record ADD COLUMN source_file_name TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE batch_record ADD COLUMN output_file_name TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE batch_record ADD COLUMN template_id TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE batch_record ADD COLUMN template_version TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE batch_record ADD COLUMN template_sha256 TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE batch_record ADD COLUMN data_row_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE batch_record ADD COLUMN total_quantity INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE batch_record ADD COLUMN evaluated_quantity INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE batch_record ADD COLUMN app_version TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE batch_record ADD COLUMN canonical_version TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE batch_record ADD COLUMN numeric_profile_id TEXT NOT NULL DEFAULT ''",
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
