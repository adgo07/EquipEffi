from dataclasses import dataclass, field
from typing import Any

from .enums import Conclusion, DataStatus, EliminationScope
from .issues import ValidationIssue


@dataclass
class RawDeviceRecord:
    record_id: str
    device_type: str
    values: dict[str, Any] = field(default_factory=dict)
    source: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceDraft:
    record_id: str
    device_type: str
    raw_values: dict[str, Any] = field(default_factory=dict)
    normalized_values: dict[str, Any] = field(default_factory=dict)
    issues: list[ValidationIssue] = field(default_factory=list)
    status: DataStatus = DataStatus.DRAFT
    revision: int = 0
    # 输入来源元数据（例如V4工作表路由）；不参与设备参数本身的判定。
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    record_id: str
    conclusion: Conclusion
    reference_conclusion: Conclusion | None = None
    actual_metrics: dict[str, Any] = field(default_factory=dict)
    calculated_metrics: dict[str, Any] = field(default_factory=dict)
    limits: dict[str, Any] = field(default_factory=dict)
    comparisons: list[dict[str, Any]] = field(default_factory=list)
    lookups: list[dict[str, Any]] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    # 判定轨迹的公开版本号由领域结果携带，而不只在某个序列化器中
    # 临时补字段。这样直接调用核心服务的桌面、JSONL和未来移动端适配器
    # 也能获得同一结果契约；新增字段保持默认值以兼容旧构造调用。
    trace_schema_version: str = "1.0"
    elimination_match: dict[str, Any] | None = None
    missing_fields: list[str] = field(default_factory=list)
    standard_reference: dict[str, Any] = field(default_factory=dict)
    elimination_scope: EliminationScope = EliminationScope.MOTOR_BATCHES_1_4
    explanation: str = ""
    notes: list[str] = field(default_factory=list)
    # 与能效结论分离的数据质量问题；用于V4“自动备注”和API返回。
    data_quality_issues: list[dict[str, Any]] = field(default_factory=list)
    # 对外使用V4公共类型；内部类型用于追溯实际调用的标准评价器。
    public_device_type: str = ""
    internal_device_type: str = ""
    # 分层离心泵结果契约。非泵设备维持 None/空列表以兼容既有结果。
    support_status: str | None = None
    category_status: str | None = None
    evaluation_status: str | None = None
    grade: str | None = None
    issue_codes: list[str] = field(default_factory=list)

    @property
    def elimination(self) -> dict[str, Any] | None:
        """Public-contract alias for the structured elimination match.

        The domain name ``elimination_match`` remains for backwards
        compatibility with existing callers. Cross-platform consumers use
        the shorter ``elimination`` key, so expose both without storing two
        independently mutable copies.
        """

        return self.elimination_match


@dataclass
class ReportModel:
    project_id: str
    results: list[EvaluationResult] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    issues: list[ValidationIssue] = field(default_factory=list)
