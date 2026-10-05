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
  `CentrifugalPumpAnalysisService.evaluate()`，不复制任何公式、等级判断或边界规则，
  也**不**绕过 Application 直接调用 Domain evaluator。
- **不得逐行调用 `analyze_and_record()`**：那是"单次分析 + 单条 Record"的产品流程，
  Excel 批量逐行调用它会创建几千条单台 Record。本模块**从不**调用 `finalize`。
- **行级独立**：一行失败不得回滚或中断其他行的合法评价；系统级失败被明确报告。
- **行号映射稳定**：每个结果都带原 Excel 行号，结果按行号排序写回。
- 行启用是语义式的（见 reader）：只填「安装位置」的行会被读取并报告问题。

统计口径（Owner Phase 8B）
--------------------------
- **数量按 Excel「数量」列加权**：某行 数量=20、结论=2级 → 批次汇总「2级 +20 台」。
- 同时分别给出：**数据行数**、**设备数量总计**、**完成正式评价数量**（台）。
- 输入错误按**行**单独统计；若该行数量本身合法，其数量只作辅助信息，
  **不得**伪装成正式评价数量。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
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
SHEET_NAME = "离心泵"

#: 用户可见正式结论的**固定口径**（用于批次汇总与结果 Workbook）。
CONCLUDED_STATUSES: tuple[str, ...] = ("SUCCESS",)
UNEVALUATED_CONCLUSION = "无法评价"
INVALID_CONCLUSION = "输入错误"
EXECUTION_ERROR_CONCLUSION = "执行失败"


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_quantity(value: Any) -> tuple[Decimal | None, str | None]:
    """解析并校验「数量」：必填、正整数、> 0（Owner 规则 8）。

    Excel 的 Data Validation **只是辅助**，用户可以直接粘贴绕过它，因此软件
    必须自己执行同一条规则。空白**不得**默认按 1 处理。

    返回 ``(数量, None)`` 或 ``(None, 原因)``。
    """

    if value in (None, ""):
        return None, "缺少数量"
    text = str(value).strip()
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError, TypeError):
        return None, f"数量应为正整数（当前为「{text}」）"
    if not number.is_finite():
        return None, f"数量应为正整数（当前为「{text}」）"
    if number != number.to_integral_value():
        return None, f"数量应为正整数，不得为小数（当前为「{text}」）"
    if number <= 0:
        return None, f"数量应为大于 0 的正整数（当前为「{text}」）"
    return number, None


@dataclass
class BatchRowIssue:
    """需要关注的一行（输入错误 / 执行失败 / 未形成正式结论）。"""

    row_number: int
    kind: str          # INPUT_ERROR / EXECUTION_ERROR / UNEVALUATED
    reason: str
    quantity: int | None = None

    def as_dict(self) -> dict:
        return {"row": self.row_number, "kind": self.kind,
                "reason": self.reason, "quantity": self.quantity}


@dataclass
class BatchEvaluationSummary:
    """一次批量评价的可序列化总结（`batch_record.summary_json` 的内容）。

    两个维度**分开**记录，不得混用：

    ```text
    行维度：data_row_count / concluded_rows / input_error_rows / execution_error_rows
    数量维度（台）：total_quantity / evaluated_quantity / conclusion_quantities
    ```
    """

    data_row_count: int = 0
    total_quantity: int = 0
    evaluated_quantity: int = 0
    concluded_rows: int = 0
    unevaluated_rows: int = 0
    input_error_rows: int = 0
    execution_error_rows: int = 0
    #: 正式结论 → 台数（**数量加权**）。
    conclusion_quantities: dict[str, int] = field(default_factory=dict)
    #: 正式结论 → 行数（辅助口径）。
    conclusion_rows: dict[str, int] = field(default_factory=dict)
    #: 输入错误行的合法数量（**辅助信息**，不计入正式评价数量）。
    input_error_quantity: int = 0
    issues: list[BatchRowIssue] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "data_row_count": self.data_row_count,
            "total_quantity": self.total_quantity,
            "evaluated_quantity": self.evaluated_quantity,
            "concluded_rows": self.concluded_rows,
            "unevaluated_rows": self.unevaluated_rows,
            "input_error_rows": self.input_error_rows,
            "execution_error_rows": self.execution_error_rows,
            "conclusion_quantities": dict(sorted(self.conclusion_quantities.items())),
            "conclusion_rows": dict(sorted(self.conclusion_rows.items())),
            "input_error_quantity": self.input_error_quantity,
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
    evaluation_date: str = ""
    #: 结果 Workbook 已生成但批次记录写入失败时，这里带可读原因（不得静默吞错）。
    batch_record_error: str = ""
    #: 本批次首个成功评价的原始结果（仅用于取 Canonical / Numeric 引用）。
    first_result: Any = None

    @property
    def records_created(self) -> int:
        """Excel 批量评价产生的**单台 Record** 数——恒为 0（Owner 规则 9）。"""

        return 0

    @property
    def batch_record_saved(self) -> bool:
        return not self.batch_record_error


def _request_from_row(row: BatchSourceRow, *, as_of: date) -> PumpAnalysisRequest:
    """把 Excel 行投影成正式 Application 请求。

    只使用**正式输入字段**；模板中的旧计算结果列不会进入请求。

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
                 template_identity: dict[str, str] | None = None,
                 template_resource=None,
                 record_id_factory: Callable[[], str] | None = None,
                 app_version: str = ""):
        # 载体端口**必须**由装配层注入：Application 不认识 Excel / openpyxl。
        self.analysis = analysis
        self.reader = reader
        self.writer = writer
        self.batch_repository = batch_repository
        self.template_identity = dict(template_identity or {})
        self.template_resource = template_resource
        self._first_result = None
        self.app_version = app_version
        self._record_id_factory = record_id_factory or (
            lambda: f"BATCH-{uuid4().hex[:12]}")

    # -- 空白模板一次输出 --------------------------------------------------

    def export_blank_template(self, destination: Path) -> Path:
        """一次操作输出正式空白模板（**不**询问任何行数 / 不逐 Sheet 配置容量）。"""

        if self.template_resource is None:
            raise RuntimeError("未装配正式模板资源，无法输出空白模板")
        return Path(self.template_resource.download_to(Path(destination)))

    # -- 主流程 ------------------------------------------------------------

    def evaluate_workbook(self, source: Path, *, destination: Path | None = None,
                          as_of: date | None = None, persist: bool = True):
        """读取 → 逐行正式评价 → 写结果 Workbook → 记一条 batch_record。

        持久化时点（Owner Phase 8B）：必须在「正式批量评价完成 + 结果 Workbook
        已成功生成 + output SHA-256 已取得」**之后**才写 `batch_record`。
        若评价完成但结果文件保存失败 → 向上抛出，**不**写"成功完成"的批次记录。
        若结果文件已生成但批次记录写入失败 → 结果照常返回，并带可读的
        `batch_record_error`，由界面明确告知用户，**不得静默吞错**。
        """

        source = Path(source)
        as_of = as_of or date.today()
        workbook = self.reader.read(source)
        summary = BatchEvaluationSummary(data_row_count=len(workbook.rows))
        outcomes: dict[int, BatchRowOutcome] = {}

        for row in workbook.rows:
            outcomes[row.row_number] = self._evaluate_row(
                row, as_of=as_of, summary=summary)

        # 默认输出名由载体端口给出（Application 不认识 Excel，因此不自己拼日期）。
        if destination is None:
            destination = Path(self.writer.default_destination(source))
        # 结果文件写失败必须向上暴露：绝不能写一个"成功完成"的批次记录。
        result_path = self.writer.write(source, outcomes, Path(destination))
        result_sha = _sha256_of(result_path)

        result = BatchEvaluationResult(
            batch_record_id=self._record_id_factory(),
            source_workbook=str(source),
            source_workbook_sha256=_sha256_of(source),
            result_workbook=str(result_path) if result_path else None,
            result_workbook_sha256=result_sha,
            outcomes=[outcomes[key] for key in sorted(outcomes)],
            summary=summary,
            evaluation_date=as_of.isoformat(),
            first_result=self._first_result,
        )
        if persist and self.batch_repository is not None:
            try:
                self._persist(result)
            except Exception as error:  # noqa: BLE001 - 明确报告，不中断结果交付
                result.batch_record_error = f"{type(error).__name__}: {error}"
        return result

    def _evaluate_row(self, row: BatchSourceRow, *, as_of: date,
                      summary: BatchEvaluationSummary) -> BatchRowOutcome:
        quantity, quantity_error = parse_quantity(row.values.get("quantity"))

        if quantity_error:
            # 输入问题：不属于正式评价结论；按**行**单独统计。
            summary.input_error_rows += 1
            if quantity is not None:
                summary.input_error_quantity += int(quantity)
            summary.issues.append(BatchRowIssue(
                row.row_number, "INPUT_ERROR", quantity_error,
                int(quantity) if quantity is not None else None))
            return BatchRowOutcome(
                row_number=row.row_number, evaluated=False,
                conclusion=INVALID_CONCLUSION, evaluation_status=None, grade=None,
                messages=(quantity_error,), derived={},
                quantity=int(quantity) if quantity is not None else 0,
                is_input_error=True)

        summary.total_quantity += int(quantity)

        try:
            request = _request_from_row(row, as_of=as_of)
            evaluated = self.analysis.evaluate(request)
        except Exception as error:  # noqa: BLE001 - 单行系统异常不得中断整批
            # 系统执行失败：不属于正式评价结论，且不得伪装成业务结论。
            summary.execution_error_rows += 1
            summary.issues.append(BatchRowIssue(
                row.row_number, "EXECUTION_ERROR",
                f"系统执行失败：{type(error).__name__}: {error}", int(quantity)))
            return BatchRowOutcome(
                row_number=row.row_number, evaluated=False,
                conclusion=EXECUTION_ERROR_CONCLUSION, evaluation_status=None,
                grade=None,
                messages=(f"系统执行失败：{type(error).__name__}: {error}",),
                derived={}, quantity=int(quantity), is_execution_error=True)

        if self._first_result is None:
            self._first_result = evaluated
        outcome = _outcome_from_result(row.row_number, evaluated, int(quantity))
        snapshot = evaluated.as_snapshot()
        conclusion = user_conclusion_text(evaluated)

        summary.conclusion_rows[conclusion] = (
            summary.conclusion_rows.get(conclusion, 0) + 1)
        summary.conclusion_quantities[conclusion] = (
            summary.conclusion_quantities.get(conclusion, 0) + int(quantity))

        if snapshot.get("evaluation_status"):
            summary.concluded_rows += 1
            summary.evaluated_quantity += int(quantity)
        else:
            # `不确定类别` 与资料不足都**没有** `evaluation_status`：
            # 计入未评价并进入"需要关注"，而不是被静默跳过。
            summary.unevaluated_rows += 1
            reason = str(snapshot.get("explanation") or "").strip() or conclusion
            summary.issues.append(BatchRowIssue(
                row.row_number, "UNEVALUATED", reason, int(quantity)))
        return outcome

    # -- 持久化 ------------------------------------------------------------

    def _persist(self, result: BatchEvaluationResult) -> None:
        from ...application.lifecycle import BatchRecordSnapshot

        summary = result.summary
        identity = self.template_identity
        references = _version_references(self._first_result)
        self.batch_repository.append_batch_record(BatchRecordSnapshot(
            batch_record_id=result.batch_record_id,
            standard_code=PUMP_STANDARD_CODE,
            device_type=PUMP_DEVICE_TYPE,
            sheet_name=SHEET_NAME,
            evaluation_date=result.evaluation_date or date.today().isoformat(),
            source_file_name=Path(result.source_workbook).name,
            source_workbook=result.source_workbook,
            source_workbook_sha256=result.source_workbook_sha256,
            result_workbook=result.result_workbook,
            result_workbook_sha256=result.result_workbook_sha256,
            output_file_name=(Path(result.result_workbook).name
                              if result.result_workbook else ""),
            template_id=identity.get("template_id", ""),
            template_version=identity.get("template_version", ""),
            template_sha256=identity.get("asset_sha256", ""),
            data_row_count=summary.data_row_count,
            total_quantity=summary.total_quantity,
            evaluated_quantity=summary.evaluated_quantity,
            # 兼容既有列（003 引入）：行数口径与"完成正式评价"口径分开。
            total_rows=summary.data_row_count,
            evaluated_count=summary.concluded_rows,
            unevaluated_count=summary.unevaluated_rows,
            invalid_count=(summary.input_error_rows + summary.execution_error_rows),
            summary=summary.as_dict(),
            app_version=self.app_version,
            canonical_version=references.get("canonical_version", ""),
            numeric_profile_id=references.get("numeric_profile_id", ""),
            schema_version=4,
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        ))


def _version_references(result) -> dict[str, str]:
    """从**已产生的正式评价结果**取 Canonical / Numeric 引用。

    这些引用只存在于 Result 契约里（标准仓储本身没有版本属性），因此取自
    本批次首个成功评价的结果。取不到时留空，**不得编造**。
    """

    if result is None:
        return {}
    references = dict(getattr(result, "references", None) or {})
    standard = dict(references.get("standard") or {})
    out: dict[str, str] = {}
    data_version = str(standard.get("data_version") or "").strip()
    if data_version:
        out["canonical_version"] = data_version
    profile = str(references.get("numeric_profile_id") or "").strip()
    if profile:
        out["numeric_profile_id"] = profile
    pack_hash = str(standard.get("pack_hash") or "").strip()
    if pack_hash:
        out["canonical_package_hash"] = pack_hash
    return out


def _outcome_from_result(row_number: int, result,
                         quantity: int = 0) -> BatchRowOutcome:
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
    thresholds = dict(result.thresholds or {})
    return BatchRowOutcome(
        row_number=row_number,
        evaluated=bool(snapshot.get("evaluation_status")),
        conclusion=user_conclusion_text(result),
        evaluation_status=snapshot.get("evaluation_status"),
        grade=snapshot.get("grade"),
        messages=tuple(messages),
        derived=derived,
        thresholds=thresholds,
        quantity=quantity)


def formal_category_names() -> tuple[str, ...]:
    """正式类别枚举（唯一来源：Application 契约）。"""

    return tuple(item.visible_name for item in PUMP_CATEGORIES)
