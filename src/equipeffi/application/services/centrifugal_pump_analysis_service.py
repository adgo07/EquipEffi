"""GB 19762-2025 离心泵统一应用分析契约（Phase 3 P3-G01）。

本模块是 Phase 3 的**唯一**离心泵产品级入口：清水泵与石油化工泵共用同一
Use Case、同一输入契约与同一结果契约；`pump_water` / `pump_chemical` 只作为
内部 rule profile identity 存在，不作为两个用户产品。

分层边界（由 tests/contract/test_architecture_boundaries.py 强制）：
本模块位于 application 层，**不得**导入 `sqlite3`、`equipeffi.infrastructure`
或 `equipeffi.presentation`。持久化只能经 ports 中的 Protocol。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Protocol

from ...domain.common.enums import Conclusion
from ...domain.common.models import DeviceDraft
from ...domain.evaluation.device_types import (
    DeviceTypeResolutionError,
    resolve_device_type,
)

PUMP_PUBLIC_DEVICE_TYPE = "centrifugal_pump"
GB19762_STANDARD_CODE = "GB 19762-2025"
GB19762_PACK_ID = "gb19762_2025_water_v1"

#: 内部 rule profile；只有这两个值可以出现在 result.rule_profile 中。
RULE_PROFILES: tuple[str, ...] = ("pump_water", "pump_chemical")

#: 已确认“不适用”的类别文本（沿用 evaluator 既有契约，不在此新造规则）。
OTHER_CATEGORY_VALUES: frozenset[str] = frozenset(
    {"OTHER", "其他类别", "其他（请备注说明）", "其他(请备注说明)"}
)


class AnalysisError(ValueError):
    """统一分析入口的输入/状态错误；不得与业务“无法判定”混淆。"""


# ---------------------------------------------------------------------------
# 统一类别目录（8 个正式类别 + 2 个特殊项）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PumpCategory:
    """一个用户可见的泵类别。

    ``visible_name`` 是用户看到的正式类别名，同时也是传给领域路由的
    ``product_type``；两者必须一致，避免 UI 自行发明第二套类别文本。
    """

    visible_name: str
    group: str
    help_text: str
    special: str | None = None


PUMP_CATEGORY_GROUPS: tuple[tuple[str, str], ...] = (
    ("water", "清水类"),
    ("chemical", "石油化工类"),
    ("special", "其他"),
)


def _cat(name: str, group: str, help_text: str, special: str | None = None) -> PumpCategory:
    return PumpCategory(name, group, help_text, special)


#: 正式类别目录。顺序即 UI 建议展示顺序。
PUMP_CATEGORIES: tuple[PumpCategory, ...] = (
    _cat("单级单吸清水离心泵", "water",
         "只有一个叶轮、水从一侧吸入的清水泵。"),
    _cat("单级双吸清水离心泵", "water",
         "只有一个叶轮、水从两侧同时吸入的清水泵。"),
    _cat("管道清水离心泵", "water",
         "直接安装在管道中、泵体与管道同轴的清水泵。"),
    _cat("多级清水离心泵", "water",
         "同一根轴上串联多个叶轮的清水泵，级数大于 1。"),
    _cat("轻型多级清水离心泵（立式）", "water",
         "立式安装的轻型多级清水泵。"),
    _cat("轻型多级清水离心泵（卧式）", "water",
         "卧式安装的轻型多级清水泵。"),
    _cat("单级石油化工离心泵", "chemical",
         "用于石油化工介质的单级离心泵，级数为 1。"),
    _cat("多级石油化工离心泵", "chemical",
         "用于石油化工介质的多级离心泵，级数大于 1。"),
    _cat("其他类别", "special",
         "已确认不属于 GB 19762—2025 列出的任一泵型；不进行等级判定。",
         special="other"),
    _cat("不确定类别", "special",
         "暂时无法判断实际泵型。请先确认泵型说明后再进行分析；本项不执行计算。",
         special="uncertain"),
)

_CATEGORY_BY_NAME = {category.visible_name: category for category in PUMP_CATEGORIES}
UNCERTAIN_CATEGORY = "不确定类别"


def category_names() -> tuple[str, ...]:
    """全部用户可见类别名（UI 与测试共用同一来源）。"""

    return tuple(category.visible_name for category in PUMP_CATEGORIES)


def formal_category_names() -> tuple[str, ...]:
    """只含 8 个正式类别名（不含特殊项）。"""

    return tuple(c.visible_name for c in PUMP_CATEGORIES if c.special is None)


def resolve_rule_profile(product_category: str | None) -> str | None:
    """把用户可见类别精确路由到内部 rule profile。

    只做**精确名称**匹配（复用领域路由表），**不做**任何子串猜测：
    “清水”“化工”“多级”等子串一律不参与判断。无法唯一确定时返回 None。
    """

    text = str(product_category or "").strip()
    if not text or text in OTHER_CATEGORY_VALUES or text == UNCERTAIN_CATEGORY:
        return None
    try:
        resolution = resolve_device_type(PUMP_PUBLIC_DEVICE_TYPE, {"product_type": text})
    except DeviceTypeResolutionError:
        return None
    internal = resolution.internal_device_type
    return internal if internal in RULE_PROFILES else None


# ---------------------------------------------------------------------------
# 统一输入 / 结果契约
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PumpAnalysisRequest:
    """统一离心泵分析输入。

    ``rule_profile`` **不在**本契约中：它由 ``product_category`` 精确派生，
    用户不得直接选择内部 profile。``as_of`` 为必填，没有隐式默认值。
    """

    product_category: str
    as_of: date
    QBEP: str | None = None
    HBEP: str | None = None
    speed: str | None = None
    efficiency: str | None = None
    suction: str | None = None
    stages: str | None = None
    project_name: str | None = None
    equipment_no: str | None = None
    record_id: str = "analysis"
    standard_code: str = GB19762_STANDARD_CODE

    def raw_values(self) -> dict[str, Any]:
        """转成领域 evaluator 消费的原始字段字典。"""

        values: dict[str, Any] = {"product_type": self.product_category}
        for key in ("QBEP", "HBEP", "speed", "efficiency", "suction", "stages"):
            value = getattr(self, key)
            if value is not None and str(value) != "":
                values[key] = value
        return values


@dataclass(frozen=True)
class PumpAnalysisResult:
    """统一离心泵分析结果。

    结果骨架对两个 rule profile 完全一致；差异只出现在 ``calculation_trace``
    与 ``extra_metrics`` 的内容上。
    """

    rule_profile: str | None
    standard_code: str
    product_category: str
    as_of: date
    evaluation_status: str | None
    category_status: str | None
    support_status: str | None
    ui_conclusion: str
    grade: str | None
    issue_codes: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    matched_rule_id: str | None = None
    thresholds: dict[str, Any] = field(default_factory=dict)
    calculation_trace: dict[str, Any] = field(default_factory=dict)
    extra_metrics: dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    references: dict[str, Any] = field(default_factory=dict)
    requires_category_confirmation: bool = False
    finalizable: bool = False
    not_finalizable_reason: str = ""

    def as_snapshot(self) -> dict[str, Any]:
        """可 JSON 序列化的快照（用于 Record / 展示投影）。"""

        return {
            "rule_profile": self.rule_profile,
            "standard_code": self.standard_code,
            "product_category": self.product_category,
            "as_of": self.as_of.isoformat(),
            "evaluation_status": self.evaluation_status,
            "category_status": self.category_status,
            "support_status": self.support_status,
            "ui_conclusion": self.ui_conclusion,
            "grade": self.grade,
            "issue_codes": list(self.issue_codes),
            "missing_fields": list(self.missing_fields),
            "matched_rule_id": self.matched_rule_id,
            "thresholds": dict(self.thresholds),
            "calculation_trace": dict(self.calculation_trace),
            "extra_metrics": dict(self.extra_metrics),
            "explanation": self.explanation,
            "references": dict(self.references),
            "requires_category_confirmation": self.requires_category_confirmation,
            "finalizable": self.finalizable,
            "not_finalizable_reason": self.not_finalizable_reason,
        }


# ---------------------------------------------------------------------------
# 持久化端口（应用层只依赖 Protocol；SQLite 实现在 infrastructure）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkspaceSnapshot:
    workspace_id: str
    standard_code: str
    device_type: str
    product_category: str
    rule_profile: str | None
    as_of: str
    payload: dict[str, Any]
    schema_version: int
    created_at_utc: str
    updated_at_utc: str


@dataclass(frozen=True)
class RecordSnapshot:
    record_id: str
    workspace_id: str | None
    standard_code: str
    standard_version: str
    device_type: str
    product_category: str
    rule_profile: str | None
    as_of: str
    evaluation_status: str
    grade: str | None
    ui_conclusion: str
    input_snapshot: dict[str, Any]
    result_snapshot: dict[str, Any]
    reference_snapshot: dict[str, Any]
    ruleset_version: str
    calculator_version: str
    numeric_profile_id: str
    canonical_version: str
    canonical_package_hash: str
    result_contract_version: str
    schema_version: int
    created_at_utc: str
    finalized_at_utc: str


class WorkspaceRepository(Protocol):
    def save_workspace(self, snapshot: WorkspaceSnapshot) -> None: ...
    def load_workspace(self, workspace_id: str) -> WorkspaceSnapshot | None: ...
    def list_workspaces(self, limit: int = 50) -> list[WorkspaceSnapshot]: ...
    def delete_workspace(self, workspace_id: str) -> None: ...


class RecordRepository(Protocol):
    def append_record(self, snapshot: RecordSnapshot) -> None: ...
    def load_record(self, record_id: str) -> RecordSnapshot | None: ...
    def list_records(self, limit: int = 200) -> list[RecordSnapshot]: ...


# ---------------------------------------------------------------------------
# 统一分析服务
# ---------------------------------------------------------------------------

#: Finalize 允许的业务状态（Phase 3 已批准规则）。
FINALIZABLE_STATUSES: frozenset[str] = frozenset(
    {"SUCCESS", "OUT_OF_STANDARD_SCOPE", "INSUFFICIENT_DATA"}
)

_GRADE_BY_CONCLUSION = {
    Conclusion.LEVEL_1: "1",
    Conclusion.LEVEL_2: "2",
    Conclusion.LEVEL_3: "3",
    Conclusion.NOT_COMPLIANT: "BELOW_MINIMUM",
}

#: 统一 trace 允许出现的派生量内部键（按 rule profile 白名单）。
#: 只投影白名单键，避免把计算器内部中间变量原样泄漏到统一结果。
_TRACE_KEYS_BY_PROFILE: dict[str, tuple[str, ...]] = {
    "pump_water": ("suction_factor", "stage_count", "q_for_ns_m3s", "h_for_ns_m",
                   "ns_raw", "输出功率_kW"),
    "pump_chemical": ("suction_factor", "stage_count", "q_for_ns_m3s", "h_for_ns_m",
                      "ns_raw", "输出功率_kW", "基准效率_%", "效率修正值_%",
                      "规定点效率_%"),
}

#: 内部派生量 → 用户可理解名称（UI 只消费本表，不直接暴露内部键）。
DERIVED_DISPLAY_NAMES: dict[str, str] = {
    "suction_factor": "吸入方式系数",
    "stage_count": "级数",
    "q_for_ns_m3s": "比转速用流量（m³/s）",
    "h_for_ns_m": "单级扬程（m）",
    "ns_raw": "比转速 ns",
    "输出功率_kW": "输出功率（kW）",
    "基准效率_%": "基准效率 η_b（%）",
    "效率修正值_%": "效率修正值 Δη（%）",
    "规定点效率_%": "规定点效率 η₀（%）",
}

#: 内部阈值键 → 用户可理解名称。
THRESHOLD_DISPLAY_NAMES: dict[str, str] = {
    "1级效率_%": "1级能效效率限值（%）",
    "2级效率_%": "2级能效效率限值（%）",
    "3级效率_%": "3级能效效率限值（%）",
}


class CentrifugalPumpAnalysisService:
    """GB 19762-2025 离心泵统一分析 Use Case。

    依赖通过构造函数注入；具体标准仓库与 evaluator 由外层装配提供，
    因此本模块不需要导入 infrastructure。
    """

    def __init__(self, standards: Any, workspaces: WorkspaceRepository | None = None,
                 records: RecordRepository | None = None, *, version: str = ""):
        self._standards = standards
        self._workspaces = workspaces
        self._records = records
        self._version = version

    # -- 内部 ---------------------------------------------------------------

    def _pack(self, rule_profile: str) -> dict[str, Any]:
        return self._standards.get_pack(rule_profile)

    @staticmethod
    def _pack_reference(pack: dict[str, Any], rule_profile: str) -> dict[str, Any]:
        return {
            "standard_code": pack.get("standard_code", GB19762_STANDARD_CODE),
            "standard_name": pack.get("standard_name", ""),
            "pack_id": pack.get("pack_id", ""),
            "rule_profile": rule_profile,
            "data_version": pack.get("data_version", ""),
            "effective_date": pack.get("effective_date", ""),
            "pack_hash": pack.get("pack_hash", ""),
        }

    def _effective_date(self, pack: dict[str, Any]) -> date | None:
        raw = pack.get("effective_date")
        if raw in (None, ""):
            return None
        try:
            return date.fromisoformat(str(raw).strip())
        except (TypeError, ValueError):
            return None

    def _base_result(self, request: PumpAnalysisRequest, pack: dict[str, Any],
                     rule_profile: str | None) -> dict[str, Any]:
        return {
            "rule_profile": rule_profile,
            "standard_code": request.standard_code,
            "product_category": request.product_category,
            "as_of": request.as_of,
            "references": {
                "standard": self._pack_reference(pack, rule_profile or ""),
                "numeric_profile_id": "EQUIPEFFI_PUMP_DECIMAL50_V2",
                "calculator_version": rule_profile or "",
                "result_contract_version": "1.0",
            },
        }

    @staticmethod
    def _finalize_flags(evaluation_status: str | None) -> tuple[bool, str]:
        if evaluation_status in FINALIZABLE_STATUSES:
            return True, ""
        if evaluation_status == "INVALID_INPUT":
            return False, "输入非法，不能形成正式记录；请修正后重新分析。"
        return False, "系统执行异常，不能伪装为业务结论，也不能形成正式记录。"

    # -- 公开 Use Case ------------------------------------------------------

    def evaluate(self, request: PumpAnalysisRequest) -> PumpAnalysisResult:
        """统一评价入口。

        ``as_of`` 为必填（无隐式默认）；``rule_profile`` 由类别精确派生。
        """

        if not isinstance(request.as_of, date):
            raise AnalysisError("as_of 必须是显式日期，统一分析入口不提供隐式默认值")

        category = str(request.product_category or "").strip()
        if not category:
            return self._unresolved(request, reason="未提供产品类别，无法确定适用的标准泵型。")

        if category == UNCERTAIN_CATEGORY:
            return self._uncertain(request)

        rule_profile = resolve_rule_profile(category)
        if rule_profile is None:
            if category in OTHER_CATEGORY_VALUES:
                return self._not_applicable(request)
            return self._unresolved(
                request,
                reason="产品类别未精确匹配 GB 19762—2025 已登记的泵型，无法确定适用规则。",
                invalid=True,
            )

        pack = self._pack(rule_profile)
        effective = self._effective_date(pack)
        if effective is not None and request.as_of < effective:
            base = self._base_result(request, pack, rule_profile)
            return PumpAnalysisResult(
                **base,
                evaluation_status="INSUFFICIENT_DATA",
                category_status="APPLICABLE",
                support_status=self._release_support(rule_profile),
                ui_conclusion=Conclusion.UNABLE_TO_JUDGE.value,
                grade=None,
                issue_codes=("STANDARD_NOT_YET_EFFECTIVE",),
                missing_fields=(),
                explanation=(
                    f"评价日期早于标准实施日期 {effective.isoformat()}，"
                    "该日期不允许使用本版本标准，不执行计算。"
                ),
                finalizable=False,
                not_finalizable_reason="评价日期早于标准实施日期，不构成正式评价结论。",
            )

        evaluator = build_pump_evaluator(rule_profile)
        result = evaluator.evaluate(dict(request.raw_values()), pack)

        base = self._base_result(request, pack, rule_profile)
        ui_conclusion = result.conclusion.value
        grade = result.grade if result.grade is not None else _GRADE_BY_CONCLUSION.get(result.conclusion)
        matched_rule_id = None
        if result.lookups:
            matched_rule_id = result.lookups[0].get("data_id")
        finalizable, reason = self._finalize_flags(result.evaluation_status)
        support_status = self._release_support(rule_profile)

        return PumpAnalysisResult(
            **base,
            evaluation_status=result.evaluation_status,
            category_status=result.category_status,
            support_status=support_status,
            ui_conclusion=ui_conclusion,
            grade=grade,
            issue_codes=tuple(result.issue_codes),
            missing_fields=tuple(result.missing_fields),
            matched_rule_id=matched_rule_id,
            thresholds=self._thresholds(result),
            calculation_trace=self._trace(result, rule_profile),
            extra_metrics=self._extra_metrics(result),
            explanation=result.explanation,
            finalizable=finalizable,
            not_finalizable_reason=reason,
        )

    # -- 特殊结果 -----------------------------------------------------------

    def _uncertain(self, request: PumpAnalysisRequest) -> PumpAnalysisResult:
        return PumpAnalysisResult(
            rule_profile=None,
            standard_code=request.standard_code,
            product_category=request.product_category,
            as_of=request.as_of,
            evaluation_status=None,
            category_status="UNRESOLVED",
            support_status=None,
            ui_conclusion=Conclusion.UNABLE_TO_JUDGE.value,
            grade=None,
            issue_codes=("CATEGORY_UNCERTAIN",),
            explanation=(
                "尚未确认实际泵型，未执行计算。请对照下列说明确认类别后重新分析："
                "单级/多级看叶轮数量；单吸/双吸看入口方向；清水泵与石油化工泵看输送介质与标准适用范围。"
            ),
            requires_category_confirmation=True,
            finalizable=False,
            not_finalizable_reason="类别未确认，不构成正式评价结论。",
        )

    def _not_applicable(self, request: PumpAnalysisRequest) -> PumpAnalysisResult:
        return PumpAnalysisResult(
            rule_profile=None,
            standard_code=request.standard_code,
            product_category=request.product_category,
            as_of=request.as_of,
            evaluation_status="OUT_OF_STANDARD_SCOPE",
            category_status="NOT_APPLICABLE",
            support_status=None,
            ui_conclusion=Conclusion.NOT_APPLICABLE.value,
            grade=None,
            issue_codes=("CATEGORY_NOT_APPLICABLE",),
            explanation="已确认该产品类别不属于 GB 19762—2025 列出的泵型，不执行标准公式。",
        )

    def _unresolved(self, request: PumpAnalysisRequest, *, reason: str,
                    invalid: bool = False) -> PumpAnalysisResult:
        """类别无法解析。

        必须区分「未填写」与「填了但不认识」：
        未填写 → `INSUFFICIENT_DATA` + `CATEGORY_MISSING`；
        填了但不认识 → `INVALID_INPUT` + `CATEGORY_UNRESOLVED`。两者不得混为一个状态。
        """

        if invalid:
            issue_codes = ("CATEGORY_UNRESOLVED",)
            missing_fields: tuple[str, ...] = ()
        else:
            issue_codes = ("CATEGORY_UNRESOLVED", "CATEGORY_MISSING")
            missing_fields = ("产品类别",)
        return PumpAnalysisResult(
            rule_profile=None,
            standard_code=request.standard_code,
            product_category=request.product_category,
            as_of=request.as_of,
            evaluation_status="INVALID_INPUT" if invalid else "INSUFFICIENT_DATA",
            category_status="UNRESOLVED",
            support_status=None,
            ui_conclusion=Conclusion.UNABLE_TO_JUDGE.value,
            grade=None,
            issue_codes=issue_codes,
            missing_fields=missing_fields,
            explanation=reason,
        )

    # -- 投影 ---------------------------------------------------------------

    @staticmethod
    def _text(value: Any) -> str | None:
        """统一把领域数值（可能是 Decimal）转成可 JSON 序列化的文本。"""

        return None if value is None else str(value)

    @classmethod
    def _normalize(cls, value: Any) -> Any:
        """递归把 Decimal 归一为文本，保证结果快照可 JSON 序列化。

        `Result / Record Envelope` 的数值必须作为十进制文本跨序列化边界，
        Decimal 不依赖隐式 float 转换（Numeric Contract v1 §2）。
        """

        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, dict):
            return {str(k): cls._normalize(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._normalize(v) for v in value]
        return value

    @classmethod
    def _thresholds(cls, result: Any) -> dict[str, Any]:
        return {
            THRESHOLD_DISPLAY_NAMES.get(key, key): cls._text(value)
            for key, value in (result.limits or {}).items()
        }

    @classmethod
    def _extra_metrics(cls, result: Any) -> dict[str, Any]:
        return {key: cls._text(value) for key, value in (result.actual_metrics or {}).items()}

    @classmethod
    def _trace(cls, result: Any, rule_profile: str) -> dict[str, Any]:
        metrics = result.calculated_metrics or {}
        allowed = _TRACE_KEYS_BY_PROFILE.get(rule_profile, ())
        derived = {
            DERIVED_DISPLAY_NAMES.get(key, key): cls._text(metrics.get(key))
            for key in allowed
            if key in metrics
        }
        return {
            "derived": derived,
            "thresholds_internal": [
                cls._text(v) for v in metrics.get("grade_thresholds_internal", [])
            ],
            "steps": cls._normalize(list(result.trace)),
        }

    @staticmethod
    def _release_support(rule_profile: str) -> str | None:
        """发布门禁：Phase 3 不得改动。

        `pump_chemical` 的 `support_status` 在 Standard Development Guide
        Stage D 独立验收通过前保持 `NOT_IN_RELEASE_SCOPE`。
        """

        if rule_profile == "pump_water":
            return "SUPPORTED"
        if rule_profile == "pump_chemical":
            return "NOT_IN_RELEASE_SCOPE"
        return None

    # -- Workspace / Record 编排（持久化经 Protocol） ------------------------

    def create_workspace(self, workspace_id: str, request: PumpAnalysisRequest) -> WorkspaceSnapshot:
        if self._workspaces is None:
            raise AnalysisError("未装配 Workspace 仓储，无法创建草稿")
        now = _utc_now()
        snapshot = WorkspaceSnapshot(
            workspace_id=workspace_id,
            standard_code=request.standard_code,
            device_type=PUMP_PUBLIC_DEVICE_TYPE,
            product_category=request.product_category,
            rule_profile=resolve_rule_profile(request.product_category),
            as_of=request.as_of.isoformat(),
            payload=request.raw_values() | {
                "project_name": request.project_name,
                "equipment_no": request.equipment_no,
            },
            schema_version=1,
            created_at_utc=now,
            updated_at_utc=now,
        )
        self._workspaces.save_workspace(snapshot)
        return snapshot

    def update_workspace(self, workspace_id: str, request: PumpAnalysisRequest) -> WorkspaceSnapshot:
        if self._workspaces is None:
            raise AnalysisError("未装配 Workspace 仓储，无法更新草稿")
        existing = self._workspaces.load_workspace(workspace_id)
        now = _utc_now()
        snapshot = WorkspaceSnapshot(
            workspace_id=workspace_id,
            standard_code=request.standard_code,
            device_type=PUMP_PUBLIC_DEVICE_TYPE,
            product_category=request.product_category,
            rule_profile=resolve_rule_profile(request.product_category),
            as_of=request.as_of.isoformat(),
            payload=request.raw_values() | {
                "project_name": request.project_name,
                "equipment_no": request.equipment_no,
            },
            schema_version=1,
            created_at_utc=existing.created_at_utc if existing else now,
            updated_at_utc=now,
        )
        self._workspaces.save_workspace(snapshot)
        return snapshot

    def load_workspace(self, workspace_id: str) -> WorkspaceSnapshot | None:
        if self._workspaces is None:
            raise AnalysisError("未装配 Workspace 仓储，无法读取草稿")
        return self._workspaces.load_workspace(workspace_id)

    def list_workspaces(self, limit: int = 50) -> list[WorkspaceSnapshot]:
        if self._workspaces is None:
            return []
        return self._workspaces.list_workspaces(limit)

    def finalize(self, *, record_id: str, workspace_id: str | None,
                 request: PumpAnalysisRequest, result: PumpAnalysisResult) -> RecordSnapshot:
        """把一次评价固化为不可变 Record。

        只允许 `FINALIZABLE_STATUSES`；`INVALID_INPUT` 与执行异常被拒绝。
        """

        if self._records is None:
            raise AnalysisError("未装配 Record 仓储，无法固化正式记录")
        if not result.finalizable:
            raise AnalysisError(result.not_finalizable_reason or "当前结果不允许形成正式记录")

        now = _utc_now()
        snapshot = RecordSnapshot(
            record_id=record_id,
            workspace_id=workspace_id,
            standard_code=result.standard_code,
            standard_version=str(result.references.get("standard", {}).get("data_version", "")),
            device_type=PUMP_PUBLIC_DEVICE_TYPE,
            product_category=result.product_category,
            rule_profile=result.rule_profile,
            as_of=result.as_of.isoformat(),
            evaluation_status=str(result.evaluation_status),
            grade=result.grade,
            ui_conclusion=result.ui_conclusion,
            input_snapshot=request.raw_values() | {
                "project_name": request.project_name,
                "equipment_no": request.equipment_no,
                "as_of": request.as_of.isoformat(),
                "product_category": request.product_category,
            },
            result_snapshot=result.as_snapshot(),
            reference_snapshot=dict(result.references),
            ruleset_version=str(result.references.get("standard", {}).get("rule_profile", "")),
            calculator_version=str(result.references.get("calculator_version", "")),
            numeric_profile_id=str(result.references.get("numeric_profile_id", "")),
            canonical_version=str(result.references.get("standard", {}).get("data_version", "")),
            canonical_package_hash=str(result.references.get("standard", {}).get("pack_hash", "")),
            result_contract_version=str(result.references.get("result_contract_version", "1.0")),
            schema_version=1,
            created_at_utc=now,
            finalized_at_utc=now,
        )
        self._records.append_record(snapshot)
        return snapshot

    def list_records(self, limit: int = 200) -> list[RecordSnapshot]:
        if self._records is None:
            return []
        return self._records.list_records(limit)

    def open_record(self, record_id: str) -> RecordSnapshot:
        """Reopen：只读原快照，**不调用 evaluator**、不按今天日期重算。"""

        if self._records is None:
            raise AnalysisError("未装配 Record 仓储，无法打开历史记录")
        snapshot = self._records.load_record(record_id)
        if snapshot is None:
            raise AnalysisError(f"正式记录不存在: {record_id}")
        return snapshot


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def build_pump_evaluator(rule_profile: str) -> Any:
    """按内部 rule profile 构造领域 evaluator。

    作为模块级工厂存在，便于测试在 Reopen 场景中替换它并证明
    “打开历史记录不会重新调用 evaluator”。
    """

    from ...domain.evaluation.evaluator_registry import EVALUATOR_FACTORIES

    return EVALUATOR_FACTORIES[rule_profile]()
