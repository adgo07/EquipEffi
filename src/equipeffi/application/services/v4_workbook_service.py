from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Sequence

from ...application.ports.v4_workbook import V4WorkbookEvaluationRow, V4WorkbookReader, V4WorkbookRow, V4WorkbookWriter
from ...domain.common.enums import EliminationScope
from ...domain.common.models import EvaluationResult
from .evaluation_facade import EvaluationFacade


@dataclass(frozen=True)
class V4WorkbookEvaluation:
    source: Path
    rows: tuple[V4WorkbookRow, ...]
    results: tuple[EvaluationResult, ...]
    elimination_scope: EliminationScope = EliminationScope.MOTOR_BATCHES_1_4


class V4WorkbookService:
    """V4批量编排层，不包含任何具体Excel库调用。"""

    def __init__(self, facade: EvaluationFacade, reader: V4WorkbookReader):
        self.facade = facade
        self.reader = reader

    def evaluate(
        self,
        source: Path,
        *,
        elimination_scope: EliminationScope | None = None,
        as_of: date | str = date(2026, 8, 23),
    ) -> V4WorkbookEvaluation:
        rows = tuple(self.reader.read_rows(source))
        effective_scope = elimination_scope
        if effective_scope is not None:
            try:
                # Keep the returned batch envelope typed as ``EliminationScope``
                # even when a host adapter supplies the workbook setting as a
                # plain string.
                effective_scope = EliminationScope(str(effective_scope))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"工作簿淘汰判定口径无效: {elimination_scope}") from exc
        else:
            read_settings = getattr(self.reader, "read_settings", None)
            settings = read_settings(source) if read_settings is not None else {}
            configured = settings.get("elimination_scope") if isinstance(settings, dict) else None
            try:
                effective_scope = EliminationScope(configured) if configured else EliminationScope.MOTOR_BATCHES_1_4
            except ValueError as exc:
                raise ValueError(f"工作簿淘汰判定口径无效: {configured}") from exc
        results = tuple(
            self.facade.evaluate_v4(row.record_id, row.sheet_name, dict(row.values), elimination_scope=effective_scope, as_of=as_of)
            for row in rows
        )
        return V4WorkbookEvaluation(source=source, rows=rows, results=results, elimination_scope=effective_scope)

    def evaluate_and_write(
        self,
        source: Path,
        destination: Path,
        *,
        writer: V4WorkbookWriter,
        elimination_scope: EliminationScope | None = None,
        as_of: date | str = date(2026, 8, 23),
    ) -> Path:
        evaluation = self.evaluate(source, elimination_scope=elimination_scope, as_of=as_of)
        if source.resolve() == destination.resolve():
            raise ValueError("V4结果文件不能覆盖输入文件")
        paired = tuple(V4WorkbookEvaluationRow(row, result) for row, result in zip(evaluation.rows, evaluation.results))
        return writer.write_results(source, destination, paired)
