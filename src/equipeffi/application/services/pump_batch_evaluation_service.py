"""Phase 8B：Excel 批量评价（Application 编排层）。

产品语义（Owner Phase 8）
-------------------------
```text
一次 Workbook / 一次离心泵批量评价
        → 一条 batch_record 总结记录
        → 结果 Workbook 保存逐设备详细结果
```

关键边界
--------
- **Excel 不是业务计算引擎**：每一行都调用正式 Application 契约
  （`CentrifugalPumpAnalysisService.evaluate`），不复制任何业务算法。
- **不得为每个数据行创建普通单台 Record**（Owner 规则 9）：本模块**不**调用
  `finalize`，只累计统计并写结果 Workbook。
- 行启用是语义式的（见 `pump_workbook_reader`）：只填了「安装位置」的行会被读取，
  并在批次汇总中作为"不合法/资料不足"行被报告，而不是静默跳过。
- 系统异常（Python 异常）**不得**伪装成业务结论：单行异常计入 `invalid`，
  并保留可读原因；批次本身继续处理其余行。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from ..ports.batch_workbook import BatchRowOutcome, BatchSourceRow
from .centrifugal_pump_analysis_service import (
    CentrifugalPumpAnalysisService,
    PUMP_CATEGORIES,
    PumpAnalysisRequest,
    user_conclusion_text,
)

#: 一张 Sheet 承载清水 + 石油化工离心泵（Owner 规则 2）。
PUMP_DEVICE_TYPE = "离心泵"
PUMP_STANDARD_CODE = "GB 19762-2025"

#: 不进入正式评价的结论分类（用于批次汇总计数）。
INVALID_CATEGORY_STATUS = "UNRESOLVED"


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


@dataclass
class BatchRowIssue:
    row_number: int
    reason: str

    def as_dict(self) -> dict:
        return {"row": self.row_number, "reason": self.reason}


@dataclass
class BatchEvaluationSummary:
    """一次批量评价的可序列化总结（`batch_record.summary_json` 的内容）。"""

    total_rows: int = 0
    evaluated_rows: int = 0
    unevaluated_rows: int = 0
    invalid_rows: int = 0
    conclusion_counts: dict[str, int] = field(default_factory=dict)
    grade_counts: dict[str, int] = field(default_factory=dict)
    issues: list[BatchRowIssue] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "total_rows": self.total_rows,
            "evaluated_rows": self.evaluated_rows,
            "unevaluated_rows": self.unevaluated_rows,
            "invalid_rows": self.invalid_rows,
            "conclusion_counts": dict(sorted(self.conclusion_counts.items())),
            "grade_counts": dict(sorted(self.grade_counts.items())),
            "issues": [issue.as_dict() for issue in self.issues],
        }


@dataclass
class BatchEvaluationResult:
    batch_record_id: str
    source_workbook: str
    source_workbook_sha256: str
    result_workbook: str | None
    result_workbook_sha256: str | None
    outcomes: list[Any] = field(default_factory=list)
    summary: BatchEvaluationSummary = field(default_factory=BatchEvaluationSummary)

    @property
    def records_created(self) -> int:
        """Excel 批量评价产生的**单台 Record** 数——恒为 0（Owner 规则 9）。"""

        return 0


def _quantity_error(values: dict) -> str | None:
    """校验「数量」：必填、正整数、> 0（Owner 规则 8）。

    Excel 的 Data Validation **只是辅助**，用户可以直接粘贴绕过它，因此软件
    必须自己执行同一条规则。空白**不得**默认按 1 处理。
    """

    from decimal import Decimal, InvalidOperation

    raw = values.get("quantity")
    if raw in (None, ""):
        return "缺少数量"
    text = str(raw).strip()
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError, TypeError):
        return f"数量应为正整数（当前为「{text}」）"
    if not number.is_finite():
        return f"数量应为正整数（当前为「{text}」）"
    if number != number.to_integral_value():
        return f"数量应为正整数，不得为小数（当前为「{text}」）"
    if number <= 0:
        return f"数量应为大于 0 的正整数（当前为「{text}」）"
    return None


def _request_from_row(row, *, as_of: date) -> PumpAnalysisRequest:
    """把 Excel 行投影成正式 Application 请求。

    只使用**正式输入字段**；模板中的旧计算结果列不会进入请求。

    字段对应（Excel → 正式请求）：

    ```text
    设备类别 -> product_category      流量 -> QBEP
    扬程     -> HBEP                  额定转速 -> speed
    泵效率   -> efficiency            单吸/双吸 -> suction
    级数     -> stages
    型号     -> equipment_no          安装位置 -> project_name
    ```

    `设备名称` 是 Excel 载体字段（用于人工识别设备），**不在**正式请求契约中，
    因此不参与业务计算；它仍原样保留在结果 Workbook 与批次来源文件中。
    """

    values = row.values
    return PumpAnalysisRequest(
        product_category=str(values.get("category") or "").strip(),
        as_of=as_of,
        QBEP=values.get("flow", ""),
        HBEP=values.get("head", ""),
        speed=values.get("speed", ""),
        efficiency=values.get("efficiency", ""),
        suction=str(values.get("suction") or "").strip(),
        stages=values.get("stages", ""),
        equipment_no=str(values.get("model") or "").strip(),
        project_name=str(values.get("location") or "").strip(),
    )


class PumpBatchEvaluationService:
    """把「离心泵」Sheet 的每一行交给正式 Application 评价。"""

    def __init__(self, analysis: CentrifugalPumpAnalysisService, *,
                 reader, writer, batch_repository=None,
                 record_id_factory: Callable[[], str] | None = None):
        # 载体端口**必须**由装配层注入：Application 不认识 Excel / openpyxl。
        self.analysis = analysis
        self.reader = reader
        self.writer = writer
        self.batch_repository = batch_repository
        self._record_id_factory = record_id_factory or (
            lambda: f"BATCH-{uuid4().hex[:12]}")

    # -- 主流程 ------------------------------------------------------------

    def evaluate_workbook(self, source: Path, *, destination: Path | None = None,
                          as_of: date | None = None, persist: bool = True):
        """读取 → 逐行正式评价 → 写结果 Workbook → 记一条 batch_record。"""

        source = Path(source)
        as_of = as_of or date.today()
        workbook = self.reader.read(source)
        summary = BatchEvaluationSummary(total_rows=len(workbook.rows))
        outcomes: dict[int, Any] = {}

        for row in workbook.rows:
            outcome = self._evaluate_row(row, as_of=as_of, summary=summary)
            outcomes[row.row_number] = outcome
            summary.evaluated_rows += 1

        result_path = None
        result_sha = None
        if destination is not None:
            result_path = self.writer.write(source, outcomes, Path(destination))
            result_sha = _sha256_of(result_path)

        batch_record_id = self._record_id_factory()
        result = BatchEvaluationResult(
            batch_record_id=batch_record_id,
            source_workbook=str(source),
            source_workbook_sha256=_sha256_of(source),
            result_workbook=str(result_path) if result_path else None,
            result_workbook_sha256=result_sha,
            outcomes=[outcomes[key] for key in sorted(outcomes)],
            summary=summary,
        )
        if persist and self.batch_repository is not None:
            self._persist(result)
        return result

    def _evaluate_row(self, row, *, as_of: date,
                      summary: BatchEvaluationSummary):
        # 软件侧输入校验先于计算：Excel 验证可被粘贴绕过，不能替代软件最终验证。
        quantity_error = _quantity_error(row.values)
        if quantity_error:
            summary.invalid_rows += 1
            summary.conclusion_counts["无法评价"] = (
                summary.conclusion_counts.get("无法评价", 0) + 1)
            summary.issues.append(BatchRowIssue(row.row_number, quantity_error))
            return _invalid_outcome(row.row_number, quantity_error)

        try:
            request = _request_from_row(row, as_of=as_of)
            evaluated = self.analysis.evaluate(request)
        except Exception as error:  # noqa: BLE001 - 单行系统异常不得中断整批
            # 系统执行失败**不得**伪装成业务结论（Owner 规则 7 的反面同样成立）。
            summary.invalid_rows += 1
            summary.issues.append(BatchRowIssue(
                row.row_number, f"系统执行失败：{type(error).__name__}: {error}"))
            return _failed_outcome(row.row_number, error)

        outcome = _outcome_from_result(row.row_number, evaluated)
        snapshot = evaluated.as_snapshot()
        conclusion = user_conclusion_text(evaluated)
        summary.conclusion_counts[conclusion] = (
            summary.conclusion_counts.get(conclusion, 0) + 1)
        if outcome.grade:
            summary.grade_counts[str(outcome.grade)] = (
                summary.grade_counts.get(str(outcome.grade), 0) + 1)

        # 只有**形成正式评价结论**的终态才算"已评价"（Owner 规则 7/9）：
        # `不确定类别` 与资料不足都**没有** `evaluation_status`，因此计入未评价，
        # 并进入批次汇总的"需要关注"清单，而不是被静默跳过。
        if not snapshot.get("evaluation_status"):
            summary.unevaluated_rows += 1
            reason = str(snapshot.get("explanation") or "").strip() or conclusion
            summary.issues.append(BatchRowIssue(row.row_number, reason))
        return outcome

    # -- 持久化 ------------------------------------------------------------

    def _persist(self, result: BatchEvaluationResult) -> None:
        from ...application.lifecycle import BatchRecordSnapshot

        summary = result.summary
        self.batch_repository.append_batch_record(BatchRecordSnapshot(
            batch_record_id=result.batch_record_id,
            standard_code=PUMP_STANDARD_CODE,
            device_type=PUMP_DEVICE_TYPE,
            source_workbook=result.source_workbook,
            source_workbook_sha256=result.source_workbook_sha256,
            result_workbook=result.result_workbook,
            result_workbook_sha256=result.result_workbook_sha256,
            total_rows=summary.total_rows,
            evaluated_count=summary.evaluated_rows,
            unevaluated_count=summary.unevaluated_rows,
            invalid_count=summary.invalid_rows,
            summary=summary.as_dict(),
            schema_version=3,
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        ))


def _invalid_outcome(row_number: int, reason: str) -> BatchRowOutcome:
    """软件侧输入校验失败行：用户可见结论为「无法评价」，并给出可读原因。"""

    return BatchRowOutcome(
        row_number=row_number, evaluated=False, conclusion="无法评价",
        evaluation_status=None, grade=None, messages=(reason,), derived={})


def _failed_outcome(row_number: int, error: Exception) -> BatchRowOutcome:
    """系统失败行：与业务结论**明确区分**，绝不写成「无法评价」或「无法判定」。"""

    return BatchRowOutcome(
        row_number=row_number, evaluated=False, conclusion="评价失败",
        evaluation_status=None, grade=None,
        messages=(f"系统执行失败：{type(error).__name__}: {error}",), derived={})


def _outcome_from_result(row_number: int, result) -> BatchRowOutcome:
    """把正式 Application 结果投影成可写回的行结果（纯 Application，不依赖 Excel）。"""

    snapshot = result.as_snapshot()
    derived = dict((result.calculation_trace or {}).get("derived") or {})
    messages: list[str] = []
    missing = snapshot.get("missing_fields") or []
    if missing:
        messages.append("缺少" + "、".join(str(item) for item in missing))
    explanation = str(snapshot.get("explanation") or "").strip()
    if explanation:
        messages.append(explanation)
    for warning in snapshot.get("warnings") or ():
        messages.append(str(warning))
    return BatchRowOutcome(
        row_number=row_number,
        evaluated=bool(snapshot.get("evaluation_status")),
        conclusion=user_conclusion_text(result),
        evaluation_status=snapshot.get("evaluation_status"),
        grade=snapshot.get("grade"),
        messages=tuple(messages),
        derived=derived)


def formal_category_names() -> tuple[str, ...]:
    """正式类别枚举（唯一来源：Application 契约）。"""

    return tuple(item.visible_name for item in PUMP_CATEGORIES)
