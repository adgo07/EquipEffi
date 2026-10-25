"""统一工作簿编排：各专业服务评价，一次写出，一次追加批次记录。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
import logging
from typing import Any

from ..lifecycle import BatchRecordSnapshot
from ..ports.batch_workbook import BatchRowOutcome
from .pump_batch_evaluation_service import (
    BatchEvaluationResult, BatchEvaluationSummary, BatchRowIssue,
    PumpBatchEvaluationService, _BatchProvenance, _sha256_of, parse_quantity,
)
from .transformer_analysis_service import TransformerAnalysisRequest, snapshot_value
from .transformer_basis_formatter import format_transformer_basis_lines


@dataclass
class WorkbookEvaluationSummary(BatchEvaluationSummary):
    sheets: list[dict[str, Any]] = field(default_factory=list)
    unprocessed_sheets: tuple[str, ...] = ()

    def as_dict(self):
        return super().as_dict() | {
            "schema_version": 2, "sheets": snapshot_value(self.sheets),
            "unprocessed_sheets": list(self.unprocessed_sheets)}


class WorkbookEvaluationService(PumpBatchEvaluationService):
    """保留泵逐行评价行为；变压器通过独立的同核应用服务评价。"""

    def __init__(self, analysis, transformer, *, motor=None, **kwargs):
        super().__init__(analysis, **kwargs)
        self.transformer = transformer
        self.motor = motor
        self._devices = {
            "离心泵": ("centrifugal_pump", "GB 19762-2025", "离心泵"),
            "变压器": ("transformer", "GB 20052-2024", "transformer"),
            "电动机": ("motor", "GB 18613-2020", "motor_lv"),
        }

    def evaluate_workbook(self, source: Path, *, destination: Path | None = None,
                          as_of: date | None = None, persist: bool = True):
        source = Path(source)
        as_of = as_of or date.today()
        workbook = self.reader.read(source)
        if not any(sheet.rows for sheet in workbook.sheets.values()):
            raise ValueError("没有可评价数据；未接通Sheet的内容未评价。")
        if self.motor is None and getattr(workbook.sheets.get("电动机"), "rows", ()):
            raise ValueError("本构建未启用电动机接入验收候选，不能评价电动机Sheet。")
        total = WorkbookEvaluationSummary(unprocessed_sheets=workbook.unprocessed_sheets)
        by_sheet = {}
        for name, sheet in workbook.sheets.items():
            summary = BatchEvaluationSummary(data_row_count=len(sheet.rows))
            provenance = _BatchProvenance()
            references: list[dict[str, Any]] = []
            rows = {}
            for row in sheet.rows:
                if name == "离心泵":
                    rows[row.row_number] = self._evaluate_row(
                        row, as_of=as_of, summary=summary, provenance=provenance)
                elif name == "变压器":
                    rows[row.row_number] = self._transformer_row(
                        row, as_of, summary, references)
                elif name == "电动机":
                    rows[row.row_number] = self._motor_row(row, as_of, summary, references)
                else:
                    raise ValueError(f"未登记的批量处理设备：{name}")
            by_sheet[name] = rows
            for issue in summary.issues:
                issue.sheet_name = name
            for key in ("data_row_count", "total_quantity", "evaluated_quantity",
                        "concluded_rows", "unevaluated_rows", "input_error_rows",
                        "execution_error_rows", "input_error_quantity"):
                setattr(total, key, getattr(total, key) + getattr(summary, key))
            for key in ("conclusion_quantities", "conclusion_rows"):
                target = getattr(total, key)
                for label, count in getattr(summary, key).items():
                    target[label] = target.get(label, 0) + count
            total.issues.extend(summary.issues)
            if name == "离心泵" and provenance.evaluated:
                references = [{
                    "standard_code": provenance.standard_code or None,
                    "standard_year": provenance.standard_year or None,
                    "standard_version": None,
                    "data_version": provenance.data_versions[0] if len(provenance.data_versions) == 1 else None,
                    "data_versions": list(provenance.data_versions),
                    "rule_profiles": list(provenance.rule_profiles),
                    "ruleset_version": None,
                    "result_contract_version": provenance.result_contract_version or None,
                    "canonical_version": provenance.canonical_version,
                    "canonical_package_hash": provenance.canonical_package_hash,
                    "numeric_profile_id": provenance.numeric_profile_id,
                    "calculator_version": provenance.calculator_version}]
            total.sheets.append(summary.as_dict() | {
                "sheet_name": name,
                "sheet_id": self._devices[name][0],
                "standard_code": self._devices[name][1],
                "device_type": self._devices[name][2],
                "template": sheet.template_identity,
                "evaluation_provenance": references,
            })
        destination = destination or self.writer.default_destination(source)
        result_path = self.writer.write(source, by_sheet, Path(destination),
                                        batch_summary=total.as_dict())
        result = BatchEvaluationResult(
            batch_record_id=self._record_id_factory(), source_workbook=str(source),
            source_workbook_sha256=_sha256_of(source), result_workbook=str(result_path),
            result_workbook_sha256=_sha256_of(result_path), summary=total,
            evaluation_date=as_of.isoformat(),
            outcomes=[{"sheet_name": name, "outcome": outcome}
                      for name, rows in by_sheet.items() for outcome in rows.values()])
        if persist and self.batch_repository is not None:
            try:
                self._persist_workbook(result, workbook.template_identity)
            except Exception as error:
                result.batch_record_error = f"{type(error).__name__}: {error}"
        return result

    def _transformer_row(self, row, as_of, summary, references):
        return self._device_row(row, as_of, summary, references, self.transformer,
                                TransformerAnalysisRequest, format_transformer_basis_lines)

    def _motor_row(self, row, as_of, summary, references):
        from .motor_analysis_service import MotorAnalysisRequest
        from .motor_basis_formatter import format_motor_basis_lines
        return self._device_row(row, as_of, summary, references, self.motor,
                                MotorAnalysisRequest, format_motor_basis_lines)

    def _device_row(self, row, as_of, summary, references, service, request_type, basis_formatter):
        quantity, error = parse_quantity(row.values.get("quantity"))
        if row.input_errors:
            summary.input_error_rows += 1
            quantity = int(quantity) if not error else 0
            summary.total_quantity += quantity
            summary.input_error_quantity += quantity
            reason = "；".join(row.input_errors)
            summary.issues.append(BatchRowIssue(row.row_number, "INPUT_ERROR", reason, quantity or None))
            return BatchRowOutcome(row.row_number, False, "输入错误", "INVALID_INPUT", None,
                                   messages=row.input_errors, quantity=quantity, is_input_error=True)
        if error:
            summary.input_error_rows += 1
            summary.issues.append(BatchRowIssue(row.row_number, "INPUT_ERROR", error))
            return BatchRowOutcome(row.row_number, False, "输入错误", "INVALID_INPUT", None,
                                   messages=(error,), is_input_error=True)
        quantity = int(quantity)
        summary.total_quantity += quantity
        try:
            result = service.evaluate(request_type(row.values, as_of))
        except Exception as error:
            logging.getLogger(__name__).exception("设备批量评价执行失败，行%s", row.row_number)
            summary.execution_error_rows += 1
            reason = f"执行失败：{type(error).__name__}"
            summary.issues.append(BatchRowIssue(row.row_number, "EXECUTION_ERROR", reason, quantity))
            return BatchRowOutcome(row.row_number, False, "执行失败", None, None,
                                   messages=(reason,), quantity=quantity, is_execution_error=True)
        status = result.evaluation_status
        if status == "INVALID_INPUT":
            summary.input_error_rows += 1
            summary.input_error_quantity += quantity
            summary.issues.append(BatchRowIssue(
                row.row_number, "INPUT_ERROR", result.explanation, quantity))
            return BatchRowOutcome(row.row_number, False, "输入错误", status, None,
                                   messages=(result.explanation,), quantity=quantity,
                                   is_input_error=True)
        if status:
            summary.concluded_rows += 1
            summary.evaluated_quantity += quantity
        else:
            summary.unevaluated_rows += 1
            summary.issues.append(BatchRowIssue(
                row.row_number, "UNEVALUATED", result.explanation, quantity))
        conclusion = result.ui_conclusion
        summary.conclusion_rows[conclusion] = summary.conclusion_rows.get(conclusion, 0) + 1
        summary.conclusion_quantities[conclusion] = summary.conclusion_quantities.get(conclusion, 0) + quantity
        if result.trace and result.references not in references:
            references.append(result.references)
        messages = tuple(message for message in (
            result.explanation, *basis_formatter(result.trace))
            if message)
        return BatchRowOutcome(
            row.row_number, bool(status), conclusion, status, result.grade,
            messages=messages,
            thresholds=result.thresholds, quantity=quantity)

    def _persist_workbook(self, result, identity):
        summary = result.summary
        active = [sheet for sheet in summary.sheets if sheet["data_row_count"]]
        single = active[0] if len(active) == 1 else None
        refs = single["evaluation_provenance"] if single else []
        reference = refs[0] if len(refs) == 1 else {}
        mixed = len(active) > 1
        payload = summary.as_dict() | {"template": dict(identity)}
        if single:
            payload["evaluation_provenance"] = reference
        self.batch_repository.append_batch_record(BatchRecordSnapshot(
            batch_record_id=result.batch_record_id,
            standard_code=single["standard_code"] if single else ("MULTI" if mixed else ""),
            device_type=single["device_type"] if single else ("MULTI" if mixed else ""),
            sheet_name=single["sheet_name"] if single else ("MULTI" if mixed else ""),
            evaluation_date=result.evaluation_date, source_workbook=result.source_workbook,
            source_workbook_sha256=result.source_workbook_sha256,
            source_file_name=Path(result.source_workbook).name,
            result_workbook=result.result_workbook,
            result_workbook_sha256=result.result_workbook_sha256,
            output_file_name=Path(result.result_workbook).name,
            template_id=identity.get("template_id", ""),
            template_version=identity.get("template_version", ""),
            template_sha256=identity.get("asset_sha256", ""),
            total_rows=summary.data_row_count, evaluated_count=summary.concluded_rows,
            unevaluated_count=summary.unevaluated_rows,
            invalid_count=summary.input_error_rows + summary.execution_error_rows,
            data_row_count=summary.data_row_count, total_quantity=summary.total_quantity,
            evaluated_quantity=summary.evaluated_quantity, summary=payload,
            app_version=self.app_version,
            canonical_version="MULTI" if mixed else reference.get("canonical_version", ""),
            numeric_profile_id="MULTI" if mixed else reference.get("numeric_profile_id", ""),
            schema_version=4, created_at_utc=datetime.now(timezone.utc).isoformat()))
