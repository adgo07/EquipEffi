"""`records.sqlite` 的批次总结记录仓储（Phase 8，Owner 规则 9/10）。

本模块属于 infrastructure，实现 application 生命周期层的
`BatchRecordRepository` Protocol，并且**只依赖设备无关的 lifecycle 契约**——
不 import 任何 `*_analysis_service` 产品模块（架构门禁强制）。

语义边界
--------
- `batch_record` 记录"一次 Excel 批量评价发生了什么"：载体文件与哈希、行数统计、
  结论分布、不合法行。**不**逐设备复制结果，**不**建通用 lineage / audit 框架。
- 只追加：不提供 update / delete；重复写入同一 `batch_record_id` 会被显式拒绝。
- **不触碰** 既有 `record` 表：单台 Record 的语义完全不变。
"""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3

from ...application.lifecycle import (
    BatchRecordSnapshot,
    LifecyclePersistenceError,
    RecordConflictError,
)


def _dumps(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _loads(text: str) -> dict:
    value = json.loads(text)
    return value if isinstance(value, dict) else {}


def _from_row(row) -> BatchRecordSnapshot:
    return BatchRecordSnapshot(
        batch_record_id=row[0], standard_code=row[1], device_type=row[2],
        source_workbook=row[3], source_workbook_sha256=row[4],
        result_workbook=row[5], result_workbook_sha256=row[6],
        total_rows=row[7], evaluated_count=row[8], unevaluated_count=row[9],
        invalid_count=row[10], summary=_loads(row[11]),
        schema_version=row[12], created_at_utc=row[13],
        sheet_name=row[14], evaluation_date=row[15], source_file_name=row[16],
        output_file_name=row[17], template_id=row[18], template_version=row[19],
        template_sha256=row[20], data_row_count=row[21], total_quantity=row[22],
        evaluated_quantity=row[23], app_version=row[24],
        canonical_version=row[25], numeric_profile_id=row[26])


_COLUMNS = ("batch_record_id, standard_code, device_type, source_workbook, "
            "source_workbook_sha256, result_workbook, result_workbook_sha256, "
            "total_rows, evaluated_count, unevaluated_count, invalid_count, "
            "summary_json, schema_version, created_at_utc, "
            "sheet_name, evaluation_date, source_file_name, output_file_name, "
            "template_id, template_version, template_sha256, data_row_count, "
            "total_quantity, evaluated_quantity, app_version, "
            "canonical_version, numeric_profile_id")


class SqliteBatchRecordRepository:
    """批次总结记录仓储：只追加，重复主键拒绝。"""

    def __init__(self, database: Path):
        self.database = Path(database)

    def append_batch_record(self, snapshot: BatchRecordSnapshot) -> None:
        try:
            with closing(sqlite3.connect(self.database)) as connection, connection:
                connection.execute(
                    f"INSERT INTO batch_record ({_COLUMNS}) "
                    "VALUES (" + ", ".join("?" * 27) + ")",
                    (
                        snapshot.batch_record_id, snapshot.standard_code,
                        snapshot.device_type, snapshot.source_workbook,
                        snapshot.source_workbook_sha256, snapshot.result_workbook,
                        snapshot.result_workbook_sha256, snapshot.total_rows,
                        snapshot.evaluated_count, snapshot.unevaluated_count,
                        snapshot.invalid_count, _dumps(snapshot.summary),
                        snapshot.schema_version, snapshot.created_at_utc,
                        snapshot.sheet_name, snapshot.evaluation_date,
                        snapshot.source_file_name, snapshot.output_file_name,
                        snapshot.template_id, snapshot.template_version,
                        snapshot.template_sha256, snapshot.data_row_count,
                        snapshot.total_quantity, snapshot.evaluated_quantity,
                        snapshot.app_version, snapshot.canonical_version,
                        snapshot.numeric_profile_id,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise RecordConflictError(
                f"批次记录已存在，不得覆盖：{snapshot.batch_record_id}"
            ) from error
        except sqlite3.Error as error:
            raise LifecyclePersistenceError(
                f"保存批次记录失败（{self.database}）：{error}"
            ) from error

    def load_batch_record(self, batch_record_id: str) -> BatchRecordSnapshot | None:
        try:
            with closing(sqlite3.connect(self.database)) as connection:
                row = connection.execute(
                    f"SELECT {_COLUMNS} FROM batch_record WHERE batch_record_id = ?",
                    (batch_record_id,),
                ).fetchone()
        except sqlite3.Error as error:
            raise LifecyclePersistenceError(
                f"读取批次记录失败（{self.database}）：{error}"
            ) from error
        return None if row is None else _from_row(row)

    def list_batch_records(self, limit: int = 50) -> list[BatchRecordSnapshot]:
        try:
            with closing(sqlite3.connect(self.database)) as connection:
                rows = connection.execute(
                    f"SELECT {_COLUMNS} FROM batch_record "
                    "ORDER BY created_at_utc DESC LIMIT ?",
                    (int(limit),),
                ).fetchall()
        except sqlite3.Error as error:
            raise LifecyclePersistenceError(
                f"列出批次记录失败（{self.database}）：{error}"
            ) from error
        return [_from_row(row) for row in rows]
