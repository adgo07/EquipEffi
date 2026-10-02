"""`records.sqlite` 的 Workspace / Record 仓储实现（Phase 3 P3-G03）。

本模块属于 infrastructure，实现 application 层的 `WorkspaceRepository` /
`RecordRepository` Protocol。Record 写入后不可变：不提供 update / delete 记录
的入口，重复写入同一 `record_id` 会被显式拒绝。
"""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3

from ...application.services.centrifugal_pump_analysis_service import (
    AnalysisError,
    RecordSnapshot,
    WorkspaceSnapshot,
)


def _dumps(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _loads(text: str) -> dict:
    value = json.loads(text)
    return value if isinstance(value, dict) else {}


class SqliteWorkspaceRepository:
    """可变 Workspace 草稿仓储。"""

    def __init__(self, database: Path):
        self.database = Path(database)

    def save_workspace(self, snapshot: WorkspaceSnapshot) -> None:
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute(
                """
                INSERT INTO workspace (
                    workspace_id, standard_code, device_type, product_category,
                    rule_profile, as_of, payload_json, schema_version,
                    created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(workspace_id) DO UPDATE SET
                    standard_code = excluded.standard_code,
                    device_type = excluded.device_type,
                    product_category = excluded.product_category,
                    rule_profile = excluded.rule_profile,
                    as_of = excluded.as_of,
                    payload_json = excluded.payload_json,
                    schema_version = excluded.schema_version,
                    updated_at_utc = excluded.updated_at_utc
                """,
                (
                    snapshot.workspace_id, snapshot.standard_code, snapshot.device_type,
                    snapshot.product_category, snapshot.rule_profile, snapshot.as_of,
                    _dumps(snapshot.payload), snapshot.schema_version,
                    snapshot.created_at_utc, snapshot.updated_at_utc,
                ),
            )

    def load_workspace(self, workspace_id: str) -> WorkspaceSnapshot | None:
        with closing(sqlite3.connect(self.database)) as connection:
            row = connection.execute(
                """
                SELECT workspace_id, standard_code, device_type, product_category,
                       rule_profile, as_of, payload_json, schema_version,
                       created_at_utc, updated_at_utc
                FROM workspace WHERE workspace_id = ?
                """,
                (workspace_id,),
            ).fetchone()
        return None if row is None else _workspace_from_row(row)

    def list_workspaces(self, limit: int = 50) -> list[WorkspaceSnapshot]:
        with closing(sqlite3.connect(self.database)) as connection:
            rows = connection.execute(
                """
                SELECT workspace_id, standard_code, device_type, product_category,
                       rule_profile, as_of, payload_json, schema_version,
                       created_at_utc, updated_at_utc
                FROM workspace ORDER BY updated_at_utc DESC LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return [_workspace_from_row(row) for row in rows]

    def delete_workspace(self, workspace_id: str) -> None:
        """只删除尚未正式化的草稿；正式 Record 不受影响。"""

        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("DELETE FROM workspace WHERE workspace_id = ?", (workspace_id,))


def _workspace_from_row(row) -> WorkspaceSnapshot:
    return WorkspaceSnapshot(
        workspace_id=row[0], standard_code=row[1], device_type=row[2],
        product_category=row[3], rule_profile=row[4], as_of=row[5],
        payload=_loads(row[6]), schema_version=int(row[7]),
        created_at_utc=row[8], updated_at_utc=row[9],
    )


class SqliteRecordRepository:
    """不可变 Record 仓储。

    `append_record` 只追加；同一 `record_id` 重复写入会被拒绝，且**没有**
    update / delete 记录的方法，保证 Finalize 后不可变。
    """

    def __init__(self, database: Path):
        self.database = Path(database)

    def append_record(self, snapshot: RecordSnapshot) -> None:
        with closing(sqlite3.connect(self.database)) as connection, connection:
            existing = connection.execute(
                "SELECT 1 FROM record WHERE record_id = ?", (snapshot.record_id,)
            ).fetchone()
            if existing is not None:
                raise AnalysisError(
                    f"正式记录已存在且不可变，拒绝覆盖: {snapshot.record_id}"
                )
            connection.execute(
                """
                INSERT INTO record (
                    record_id, workspace_id, standard_code, standard_version,
                    device_type, product_category, rule_profile, as_of,
                    evaluation_status, grade, ui_conclusion,
                    input_snapshot_json, result_snapshot_json, reference_snapshot_json,
                    ruleset_version, calculator_version, numeric_profile_id,
                    canonical_version, canonical_package_hash, result_contract_version,
                    schema_version, created_at_utc, finalized_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.record_id, snapshot.workspace_id, snapshot.standard_code,
                    snapshot.standard_version, snapshot.device_type, snapshot.product_category,
                    snapshot.rule_profile, snapshot.as_of, snapshot.evaluation_status,
                    snapshot.grade, snapshot.ui_conclusion,
                    _dumps(snapshot.input_snapshot), _dumps(snapshot.result_snapshot),
                    _dumps(snapshot.reference_snapshot),
                    snapshot.ruleset_version, snapshot.calculator_version,
                    snapshot.numeric_profile_id, snapshot.canonical_version,
                    snapshot.canonical_package_hash, snapshot.result_contract_version,
                    snapshot.schema_version, snapshot.created_at_utc, snapshot.finalized_at_utc,
                ),
            )

    def load_record(self, record_id: str) -> RecordSnapshot | None:
        with closing(sqlite3.connect(self.database)) as connection:
            row = connection.execute(
                f"SELECT {_RECORD_COLUMNS} FROM record WHERE record_id = ?", (record_id,)
            ).fetchone()
        return None if row is None else _record_from_row(row)

    def list_records(self, limit: int = 200) -> list[RecordSnapshot]:
        with closing(sqlite3.connect(self.database)) as connection:
            rows = connection.execute(
                f"SELECT {_RECORD_COLUMNS} FROM record ORDER BY finalized_at_utc DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [_record_from_row(row) for row in rows]


_RECORD_COLUMNS = (
    "record_id, workspace_id, standard_code, standard_version, device_type, "
    "product_category, rule_profile, as_of, evaluation_status, grade, ui_conclusion, "
    "input_snapshot_json, result_snapshot_json, reference_snapshot_json, "
    "ruleset_version, calculator_version, numeric_profile_id, canonical_version, "
    "canonical_package_hash, result_contract_version, schema_version, "
    "created_at_utc, finalized_at_utc"
)


def _record_from_row(row) -> RecordSnapshot:
    return RecordSnapshot(
        record_id=row[0], workspace_id=row[1], standard_code=row[2], standard_version=row[3],
        device_type=row[4], product_category=row[5], rule_profile=row[6], as_of=row[7],
        evaluation_status=row[8], grade=row[9], ui_conclusion=row[10],
        input_snapshot=_loads(row[11]), result_snapshot=_loads(row[12]),
        reference_snapshot=_loads(row[13]),
        ruleset_version=row[14], calculator_version=row[15], numeric_profile_id=row[16],
        canonical_version=row[17], canonical_package_hash=row[18],
        result_contract_version=row[19], schema_version=int(row[20]),
        created_at_utc=row[21], finalized_at_utc=row[22],
    )
