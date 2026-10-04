"""GB 19762-2025 离心泵统一应用分析契约（Phase 3 P3-G01；Phase 4 接入生命周期契约）。

本模块是 Phase 3 的**唯一**离心泵产品级入口：清水泵与石油化工泵共用同一
Use Case、同一输入契约与同一结果契约；`pump_water` / `pump_chemical` 只作为
内部 rule profile identity 存在，不作为两个用户产品。

Phase 4：设备无关的 Workspace / Record 生命周期（快照模型、仓储端口、
错误语义、稳定指纹算法）已抽到 `equipeffi.application.lifecycle`。
本模块只保留 **pump-specific** 内容：请求/结果契约、类别目录与路由、
evaluator 装配、阈值 / trace / grade、GB19762 provenance，
以及 Finalize 的**具体业务允许状态政策**。

分层边界（由 tests/contract/test_architecture_boundaries.py 强制）：
本模块位于 application 层，**不得**导入 `sqlite3`、`equipeffi.infrastructure`
或 `equipeffi.presentation`。持久化只能经 lifecycle ports 中的 Protocol。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from uuid import uuid4
from decimal import Decimal
import json
from typing import Any

from ...domain.common.enums import Conclusion
from ...domain.common.models import DeviceDraft
from ...domain.evaluation.device_types import (
    DeviceTypeResolutionError,
    resolve_device_type,
)
from ..lifecycle import (
    AnalysisError,
    RecordRepository,
    RecordSnapshot,
    WorkspaceRepository,
    WorkspaceSnapshot,
    business_keys_metadata,
    stable_fingerprint,
)
from .pump_release_gate import pump_release_support

PUMP_PUBLIC_DEVICE_TYPE = "centrifugal_pump"
GB19762_STANDARD_CODE = "GB 19762-2025"
GB19762_PACK_ID = "gb19762_2025_water_v1"

#: 内部 rule profile；只有这两个值可以出现在 result.rule_profile 中。
RULE_PROFILES: tuple[str, ...] = ("pump_water", "pump_chemical")

#: **唯一**一处声明"哪些输入字段会影响泵业务结论"。
#:
#: 生命周期层不认识这些字段：它只是把它们当作需要纳入指纹的不透明键。
#: `PumpAnalysisRequest.request_fingerprint()` 与 `WorkspaceSnapshot` 的指纹
#: 都经此集合 + `stable_fingerprint()` 计算，因此不存在第二处业务字段清单。
PUMP_FINGERPRINT_KEYS: tuple[str, ...] = (
    "QBEP", "HBEP", "speed", "efficiency", "suction", "stages"
)


def _pump_payload(request: "PumpAnalysisRequest") -> dict[str, Any]:
    """构造成 Workspace 持久化的载荷。

    业务键集合作为**自描述元数据**随载荷一起持久化（Phase 4 阻塞修复）：
    这样跨进程恢复时 `WorkspaceSnapshot.request_fingerprint()` 无需任何产品模块
    被导入，也不依赖全局可变状态，且不同业务输入不会碰撞。
    """

    return request.raw_values() | {
        "project_name": request.project_name,
        "equipment_no": request.equipment_no,
    } | business_keys_metadata(PUMP_FINGERPRINT_KEYS)

#: 已确认“不适用”的类别文本（沿用 evaluator 既有契约，不在此新造规则）。
OTHER_CATEGORY_VALUES: frozenset[str] = frozenset(
    {"OTHER", "其他类别", "其他（请备注说明）", "其他(请备注说明)"}
)


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

#: 类别**唯一决定**的输入字段。键为 `PUMP_CATEGORIES` 的 `visible_name`。
#:
#: 依据是既有领域路由（`domain/evaluation/evaluators/pump.py`），不是 UI 新造的规则：
#:
#: - 级数：`"多级" in category` 为假时，级数必须恰好为 1
#:   （见 `pump.py` 的 `is_multistage` 分支）；为真时级数由用户填写且必须 > 1。
#: - **吸入方式**：只有**清水类**的类别名显式含「单吸」/「双吸」时才由类别唯一决定
#:   （领域层 `category_suction` 会据此判定冲突，见 `pump.py`）。
#:   **石油化工类不约束吸入方式**：`pump.py` 的石化分支只校验 `suction ∈ {单吸, 双吸}`
#:   并把它用于吸入方式系数，**没有**类别↔吸入方式一致性检查；已批准 Golden
#:   `GC-PUMP-V5-CHEMICAL-DOUBLE-SUCTION` 正是「单级石油化工离心泵 + 双吸」。
#:   因此把石化泵锁成单吸会**改变合法业务输入**（并改变比转速与结果），属越权约束。
#: - **管道清水离心泵**的类别名既不含「单吸」也不含「双吸」→ 只锁定级数。
#:
#: 注意：锁定只表示"该值由类别唯一决定、界面默认填入并禁止改成**与类别冲突**的值"，
#: 它**不得**被用来抹掉标准与已批准真值允许的其它合法取值。
CATEGORY_FIELD_CONSTRAINTS: dict[str, dict[str, str]] = {
    "单级单吸清水离心泵": {"stages": "1", "suction": "单吸"},
    "单级双吸清水离心泵": {"stages": "1", "suction": "双吸"},
    "管道清水离心泵": {"stages": "1"},
    "多级清水离心泵": {},
    "轻型多级清水离心泵（立式）": {},
    "轻型多级清水离心泵（卧式）": {},
    # 石化类：级数由类别名中的"单级"唯一决定；吸入方式**不**由类别决定。
    "单级石油化工离心泵": {"stages": "1"},
    "多级石油化工离心泵": {},
}

#: 用户可填写的数值字段（其余为类别锁定字段）。
LOCKABLE_FIELDS: tuple[str, ...] = ("stages", "suction")


def category_field_constraints(product_category: str | None) -> dict[str, str]:
    """返回该类别被唯一决定的字段；无约束时返回空字典。"""

    return dict(CATEGORY_FIELD_CONSTRAINTS.get(str(product_category or ""), {}))

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
    #: 绑定草稿修订号；从 Workspace 评价时由 `request_from_workspace` 填入。
    workspace_revision: int | None = None

    def raw_values(self) -> dict[str, Any]:
        """转成领域 evaluator 消费的原始字段字典。

        字段清单复用 `PUMP_FINGERPRINT_KEYS`，避免同一份业务字段集合
        在本模块出现第二个字面量。
        """

        values: dict[str, Any] = {"product_type": self.product_category}
        for key in PUMP_FINGERPRINT_KEYS:
            value = getattr(self, key)
            if value is not None and str(value) != "":
                values[key] = value
        return values

    def input_snapshot(self) -> dict[str, Any]:
        """完整输入快照（Workspace / Record 共用同一形状）。"""

        return self.raw_values() | {
            "product_category": self.product_category,
            "as_of": self.as_of.isoformat(),
            "project_name": self.project_name,
            "equipment_no": self.equipment_no,
        }

    def request_fingerprint(self) -> str:
        """输入指纹：对影响业务结论的全部输入取稳定哈希。

        Finalize 用它证明"被固化的结果确实对应当前 Workspace 的输入"，
        防止新输入与旧结果错配进入同一正式 Record。

        算法在 `lifecycle.models.stable_fingerprint`，业务键集合在本模块
        `PUMP_FINGERPRINT_KEYS`——**各只有一处**。
        """

        values: dict[str, Any] = {
            "product_category": self.product_category,
            "as_of": self.as_of,
        }
        for key in PUMP_FINGERPRINT_KEYS:
            values[key] = getattr(self, key)
        return stable_fingerprint(values)


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
    #: 结果来源声明：是否实际执行了具体 rule_profile。
    #: 类别级结论（其他类别 / 类别缺失等）没有 ruleset，必须显式记录 no-ruleset 原因，
    #: 且不得携带 Canonical 包哈希（禁止伪造 provenance）。
    provenance: dict[str, Any] = field(default_factory=dict)
    #: 非阻断提示（例如所选标准版本相对评价日期的生命周期状态）。
    #: **不是**业务判定结果：不得进入 `evaluation_status` / `issue_codes` /
    #: `missing_fields`，也不得影响 Finalize 权限。
    warnings: tuple[str, ...] = ()
    raw_values: dict[str, Any] = field(default_factory=dict)
    workspace_revision: int | None = None
    request_fingerprint: str = ""
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
            "provenance": dict(self.provenance),
            "warnings": list(self.warnings),
            "raw_values": dict(self.raw_values),
            "workspace_revision": self.workspace_revision,
            "request_fingerprint": self.request_fingerprint,
            "requires_category_confirmation": self.requires_category_confirmation,
            "finalizable": self.finalizable,
            "not_finalizable_reason": self.not_finalizable_reason,
        }


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


@dataclass(frozen=True)
class AnalysisOutcome:
    """「分析 + 自动固化」的返回契约（Phase 7）。

    ``record_status`` 只允许三个取值：

    ```text
    RECORDED       已自动形成不可变历史 Record
    NOT_RECORDED   合法评价但按业务规则不固化（状态不在白名单 / 业务拒绝）
    SAVE_FAILED    计算结果已产生，但历史记录**保存失败**（系统失败）
    ```

    `SAVE_FAILED` 必须被调用方显示为"保存失败"，**不得**显示为已保存。
    """

    request: PumpAnalysisRequest
    result: PumpAnalysisResult
    record: RecordSnapshot | None
    record_status: str
    record_error: str = ""

    @property
    def recorded(self) -> bool:
        return self.record_status == "RECORDED"

    @property
    def save_failed(self) -> bool:
        return self.record_status == "SAVE_FAILED"


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

    def _lifecycle_warnings(self, pack: dict[str, Any], as_of: date) -> tuple[str, ...]:
        """标准生命周期提示：**非阻断**、**只需几个字**。

        Owner 规则（Phase 5）：评价日期不是业务门禁。未实施 / 已废止 / 已被替代
        只作为提示，不得阻止计算、不得改写 `evaluation_status`、`issue_codes`、
        `missing_fields` 或 Finalize 权限，也不得自动切换到其他标准版本；
        不做复杂确认流程。

        这些提示刻意**不**进入 `issue_codes`：那是业务判定结果的一部分，
        而生命周期只是所选标准版本相对评价日期的元信息。
        """

        effective = self._effective_date(pack)
        if effective is None:
            return ()
        if as_of < effective:
            # Owner 指定的简短短语，不含日期、不要求确认。
            return ("该标准尚未实施",)
        # 已废止 / 已被替代需要标准生命周期元数据（`superseded_by` / 废止日期等）。
        # 当前 Canonical Pack 只提供 `effective_date`，因此**不**对"晚于实施日期"
        # 做推测性提示——不为凑齐短语而私造公共规则。补齐须走标准映射流程
        # （已登记 QA-P3-002）。
        return ()

    # -- 标准概览 read model（Phase 6 G02）----------------------------------
    #
    # 只**组合已有权威数据**，不新增第二套标准事实源：
    # 标准事实来自注入的标准仓库（Canonical pack），用户可见类别来自本模块自己的
    # `PUMP_CATEGORIES` 目录，发布门禁来自本模块的 `_release_support`。
    # Presentation 不得自行维护第二份标准表。

    def standard_overview(self, *, as_of: date | None = None,
                          show_lifecycle_warning: bool = False) -> dict[str, Any]:
        """当前正式标准的展示元数据（供标准库页面使用）。

        ``as_of`` 默认取本机当天，使 ``lifecycle_state`` 反映**当前**真实状态。
        ``show_lifecycle_warning``：标准库展示的是当前标准事实，只有调用方
        明确要针对某个日期发问时才给出提示文案，避免把"相对某日尚未实施"
        无条件显示成当前标准状态。
        """

        as_of = as_of if as_of is not None else date.today()

        scopes: list[dict[str, Any]] = []
        standard_name = ""
        standard_code = GB19762_STANDARD_CODE
        effective_date = ""
        status = ""
        data_version = ""
        source_file = ""

        for rule_profile in RULE_PROFILES:
            pack = self._pack(rule_profile)
            standard_name = standard_name or str(pack.get("standard_name", ""))
            standard_code = str(pack.get("standard_code", standard_code))
            effective_date = effective_date or str(pack.get("effective_date", ""))
            status = status or str(pack.get("status", ""))
            data_version = data_version or str(pack.get("data_version", ""))
            source_file = source_file or str(pack.get("source_file", ""))
            scopes.append({
                "rule_profile": rule_profile,
                "pack_id": str(pack.get("pack_id", "")),
                "categories": [category.visible_name
                               for category in PUMP_CATEGORIES
                               if resolve_rule_profile(category.visible_name) == rule_profile],
                "support_status": self._release_support(rule_profile),
            })

        return {
            "standard_code": standard_code,
            "standard_name": standard_name,
            "status": status,
            "effective_date": effective_date,
            "data_version": data_version,
            "source_file": source_file,
            "scopes": scopes,
            "supported_categories": [category.visible_name for category in PUMP_CATEGORIES
                                     if not category.special],
            "special_categories": [category.visible_name for category in PUMP_CATEGORIES
                                   if category.special],
            # 当前 Canonical Pack 未提供废止/替代元数据；如实说明而不是留空或编造。
            "supersession_note": "当前标准数据未提供废止或被替代关系信息。",
            # 生命周期提示（非阻断）：由**真实日期**推导，不硬编码结论。
            # 评价日期不是业务门禁，因此该提示永不阻断计算。
            "lifecycle_warning": self._standard_lifecycle_warning(
                pack, as_of if show_lifecycle_warning else None),
            "lifecycle_state": self._standard_lifecycle_state(pack, as_of),
            "as_of_policy": "评价日期用于记录与追溯；不影响所选标准的计算。",
        }

    def _standard_lifecycle_state(self, pack: dict[str, Any],
                                  as_of: date | None) -> str:
        """返回标准相对给定日期的真实生命周期状态。

        取值刻意保持最小且**不推测**：

        ```text
        NOT_YET_EFFECTIVE  评价日期早于 Canonical 实施日期
        EFFECTIVE          评价日期已达到 / 晚于实施日期
        UNKNOWN            没有实施日期元数据
        ```

        当前 Canonical Pack 未提供废止 / 替代（`superseded_by` 等）元数据，
        因此**不得**推测"已废止 / 已被替代"（补齐须走标准映射流程，已登记
        `QA-P3-002`）。
        """

        effective = self._effective_date(pack)
        if effective is None or as_of is None:
            return "UNKNOWN"
        return "EFFECTIVE" if as_of >= effective else "NOT_YET_EFFECTIVE"

    def _standard_lifecycle_warning(self, pack: dict[str, Any],
                                    as_of: date | None) -> str:
        """生命周期**非阻断**提示；无提示时返回空串。"""

        state = self._standard_lifecycle_state(pack, as_of)
        if state == "NOT_YET_EFFECTIVE":
            return "该标准尚未实施"
        return ""

    def _base_result(self, request: PumpAnalysisRequest, pack: dict[str, Any],
                     rule_profile: str | None) -> dict[str, Any]:
        return {
            "rule_profile": rule_profile,
            "standard_code": request.standard_code,
            "product_category": request.product_category,
            "as_of": request.as_of,
            # 固化本次评价所用的完整输入与指纹：Finalize 必须核对它们，
            # 否则可能把"新输入 + 旧结果"写进同一正式 Record。
            "raw_values": request.input_snapshot(),
            "request_fingerprint": request.request_fingerprint(),
            "workspace_revision": request.workspace_revision,
            "provenance": self._ruleset_provenance(rule_profile),
            "references": {
                "standard": self._pack_reference(pack, rule_profile or ""),
                "numeric_profile_id": "EQUIPEFFI_PUMP_DECIMAL50_V2",
                "calculator_version": rule_profile or "",
                "result_contract_version": "1.0",
            },
        }

    @staticmethod
    def _ruleset_provenance(rule_profile: str) -> dict[str, Any]:
        """实际执行了具体规则集的结果来源声明。"""

        return {
            "ruleset_executed": True,
            "rule_profile": rule_profile,
            "no_ruleset_reason": None,
        }

    @staticmethod
    def _category_provenance(reason: str, *, status: str) -> dict[str, Any]:
        """类别级结论的来源声明：没有 ruleset，也不得伪造 Canonical provenance。"""

        return {
            "ruleset_executed": False,
            "rule_profile": None,
            "no_ruleset_reason": reason,
            "category_level_status": status,
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
        # Owner 正式决定（2026-10-02，取代此前"提前日期不执行计算"的设计）：
        # 评价日期 `as_of` **只用于**默认新建日期、用户手动修改、Record 追溯与
        # Reopen 显示，**不是标准执行门禁**。用户可以主动使用未实施、现行或已废止的
        # 标准版本；只要明确选定版本，软件就按该版本的冻结规则正常计算。
        #
        # 因此这里**不再**以 `as_of < effective_date` 短路，也不再改写
        # evaluation_status / issue_codes / missing_fields / Finalize 权限。
        # 标准生命周期状态只作为**非阻断提示**（`warnings`）。
        lifecycle_warnings = self._lifecycle_warnings(pack, request.as_of)

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
            # 生命周期提示与业务判定严格分离：不进入 issue_codes / missing_fields，
            # 也不参与 finalizable 计算。
            warnings=lifecycle_warnings,
            finalizable=finalizable,
            not_finalizable_reason=reason,
        )

    # -- 特殊结果 -----------------------------------------------------------

    @staticmethod
    def _frozen_fields(request: PumpAnalysisRequest) -> dict[str, Any]:
        """所有结果路径都必须携带的输入冻结字段。"""

        return {
            "raw_values": request.input_snapshot(),
            "request_fingerprint": request.request_fingerprint(),
            "workspace_revision": request.workspace_revision,
        }

    def _uncertain(self, request: PumpAnalysisRequest) -> PumpAnalysisResult:
        # `None` 状态不在白名单内，因此不可固化：类别未确认不构成正式结论。
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
            **self._frozen_fields(request),
            **self._category_provenance_dict("类别未确认，未执行任何规则集", status="UNRESOLVED"),
            requires_category_confirmation=True,
            finalizable=False,
            not_finalizable_reason="类别未确认，不构成正式评价结论。",
        )

    def _not_applicable(self, request: PumpAnalysisRequest) -> PumpAnalysisResult:
        # 类别级正式结论：状态在白名单内，允许形成 Record（不伪造 ruleset provenance）。
        status = "OUT_OF_STANDARD_SCOPE"
        return PumpAnalysisResult(
            rule_profile=None,
            standard_code=request.standard_code,
            product_category=request.product_category,
            as_of=request.as_of,
            evaluation_status=status,
            category_status="NOT_APPLICABLE",
            support_status=None,
            ui_conclusion=Conclusion.NOT_APPLICABLE.value,
            grade=None,
            issue_codes=("CATEGORY_NOT_APPLICABLE",),
            explanation="已确认该产品类别不属于 GB 19762—2025 列出的泵型，不执行标准公式。",
            **self._frozen_fields(request),
            **self._category_provenance_dict(
                "已确认类别不在 GB 19762—2025 列出的泵型内，未执行任何规则集", status=status),
            finalizable=True,
        )

    def _unresolved(self, request: PumpAnalysisRequest, *, reason: str,
                    invalid: bool = False) -> PumpAnalysisResult:
        """类别无法解析。

        必须区分「未填写」与「填了但不认识」：
        未填写 → `INSUFFICIENT_DATA` + `CATEGORY_MISSING`（白名单内，可形成 Record）；
        填了但不认识 → `INVALID_INPUT` + `CATEGORY_UNRESOLVED`（不可固化）。
        """

        if invalid:
            issue_codes = ("CATEGORY_UNRESOLVED",)
            missing_fields: tuple[str, ...] = ()
        else:
            issue_codes = ("CATEGORY_UNRESOLVED", "CATEGORY_MISSING")
            missing_fields = ("产品类别",)
        status = "INVALID_INPUT" if invalid else "INSUFFICIENT_DATA"
        finalizable = status in FINALIZABLE_STATUSES
        return PumpAnalysisResult(
            rule_profile=None,
            standard_code=request.standard_code,
            product_category=request.product_category,
            as_of=request.as_of,
            evaluation_status=status,
            category_status="UNRESOLVED",
            support_status=None,
            ui_conclusion=Conclusion.UNABLE_TO_JUDGE.value,
            grade=None,
            issue_codes=issue_codes,
            missing_fields=missing_fields,
            explanation=reason,
            **self._frozen_fields(request),
            **self._category_provenance_dict(
                "类别未解析，未执行任何规则集", status=status),
            finalizable=finalizable,
            not_finalizable_reason="" if finalizable else "类别状态为 INVALID_INPUT，不构成正式评价结论。",
        )

    @staticmethod
    def _category_provenance_dict(reason: str, *, status: str) -> dict[str, Any]:
        return {"provenance": CentrifugalPumpAnalysisService._category_provenance(
            reason, status=status)}

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
        """发布门禁：**委托**给共享单一事实源。

        Phase 6 R1：这里曾经硬编码 `pump_water` / `pump_chemical` → `SUPPORTED`。
        那使"与遗留 `EvaluationService` 共用同一份门禁策略"只停留在注释里：
        在内存中替换共享策略后，两条路径会返回不同状态。现在改为直接调用
        `pump_release_gate.pump_release_support`，使该声明可被机械证明。

        策略本体与依据见 `application/services/pump_release_gate.py`。
        """
        return pump_release_support(rule_profile)

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
            payload=_pump_payload(request),
            schema_version=1,
            created_at_utc=now,
            updated_at_utc=now,
            revision=1,
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
            payload=_pump_payload(request),
            schema_version=1,
            created_at_utc=existing.created_at_utc if existing else now,
            updated_at_utc=now,
            revision=(existing.revision + 1) if existing else 1,
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

    def delete_workspace(self, workspace_id: str) -> None:
        """删除未正式化的草稿。正式 Record 不可删除，也不受影响。"""

        if self._workspaces is None:
            raise AnalysisError("未装配 Workspace 仓储，无法删除草稿")
        self._workspaces.delete_workspace(workspace_id)

    # -- Workspace <- -> 契约 转换 ------------------------------------------

    def request_from_workspace(self, workspace: WorkspaceSnapshot,
                               *, record_id: str = "analysis") -> PumpAnalysisRequest:
        """把草稿还原成统一输入，并绑定草稿修订号。"""

        payload = workspace.payload
        return PumpAnalysisRequest(
            product_category=workspace.product_category,
            as_of=date.fromisoformat(workspace.as_of),
            QBEP=payload.get("QBEP"),
            HBEP=payload.get("HBEP"),
            speed=payload.get("speed"),
            efficiency=payload.get("efficiency"),
            suction=payload.get("suction"),
            stages=payload.get("stages"),
            project_name=payload.get("project_name"),
            equipment_no=payload.get("equipment_no"),
            record_id=record_id,
            standard_code=workspace.standard_code,
            workspace_revision=workspace.revision,
        )

    def save_workspace_from_request(self, workspace_id: str,
                                    request: PumpAnalysisRequest) -> WorkspaceSnapshot:
        """按 workspace_id 是否存在决定新建或更新（Qt 保存草稿入口）。"""

        existing = self.load_workspace(workspace_id)
        if existing is None:
            return self.create_workspace(workspace_id, request)
        return self.update_workspace(workspace_id, request)

    def evaluate_workspace(self, workspace_id: str,
                           *, record_id: str = "analysis") -> PumpAnalysisResult:
        """从草稿读取输入并评价；结果绑定该草稿的当前修订号。"""

        workspace = self.load_workspace(workspace_id)
        if workspace is None:
            raise AnalysisError(f"草稿不存在: {workspace_id}")
        return self.evaluate(self.request_from_workspace(workspace, record_id=record_id))

    def analyze_and_record(self, request: PumpAnalysisRequest, *,
                           record_id: str | None = None) -> "AnalysisOutcome":
        """Phase 7 正式分析流程：评价 + **自动**固化合法业务终态。

        产品规则（Owner，Phase 7）：用户点击「分析」后，只要形成**合法业务终态**，
        就自动保存为不可变历史 Record；不存在用户手工「保存为正式记录」这一步。

        本方法**不放宽任何既有安全门禁**：固化仍走 `finalize()`，因此业务状态白名单、
        输入指纹比对、类别/日期一致性、Canonical provenance 检查一条不减。
        它只是把触发者从"用户点击"改成"合法评价完成后自动执行"。

        **系统异常与业务结论严格分离**：

        - 评价阶段抛出的任何异常**不被转换**成业务状态（如 `INSUFFICIENT_DATA`
          或"无法判定"），而是原样向上抛出，由调用方按系统失败处理；
        - 固化阶段的 `AnalysisError` 是**业务拒绝**（状态不在白名单、指纹不一致等），
          返回 `record_status = "NOT_RECORDED"`；
        - 固化阶段的**其他**异常（`LifecyclePersistenceError` / `OSError` /
          `sqlite3.Error` 等）是**系统失败**，返回 `record_status = "SAVE_FAILED"`
          并携带根因，调用方**不得**显示为保存成功。
        """

        result = self.evaluate(request)

        if not result.finalizable:
            return AnalysisOutcome(request=request, result=result,
                                   record=None, record_status="NOT_RECORDED",
                                   record_error=result.not_finalizable_reason)

        target_id = record_id or f"ANALYSIS-{uuid4().hex[:12]}"
        try:
            record = self.finalize(record_id=target_id, workspace_id=None,
                                   request=request, result=result)
        except AnalysisError as error:
            return AnalysisOutcome(request=request, result=result, record=None,
                                   record_status="NOT_RECORDED", record_error=str(error))
        except Exception as error:  # noqa: BLE001 - 系统失败必须与业务结论分离
            return AnalysisOutcome(request=request, result=result, record=None,
                                   record_status="SAVE_FAILED",
                                   record_error=f"{type(error).__name__}: {error}")
        return AnalysisOutcome(request=request, result=result, record=record,
                               record_status="RECORDED")

    def finalize(self, *, record_id: str, workspace_id: str | None,
                 request: PumpAnalysisRequest, result: PumpAnalysisResult) -> RecordSnapshot:
        """把一次评价固化为不可变 Record。

        只有同时满足以下条件才允许固化：

        1. 结果状态属于 `FINALIZABLE_STATUSES`（`INVALID_INPUT` 与执行异常被拒绝）；
        2. **传入的 request 与产生 result 的那次评价完全一致**（指纹比对）；
        3. 若绑定 Workspace，则该 Workspace 的当前 revision 与评价时的 revision 一致。

        第 2、3 条用于防止"新输入 + 旧结果"被写进同一正式 Record。
        """

        if self._records is None:
            raise AnalysisError("未装配 Record 仓储，无法固化正式记录")

        # (1) 独立按 evaluation_status 白名单判断，**不得**只信 result.finalizable。
        #     与结果对象自报的 finalizable 矛盾时 fail closed（拒绝）。
        status = result.evaluation_status
        if not isinstance(status, str) or status not in FINALIZABLE_STATUSES:
            raise AnalysisError(
                f"评价状态 {status!r} 不在允许固化的白名单内"
                f"（仅允许 {'/'.join(sorted(FINALIZABLE_STATUSES))}）；拒绝固化正式记录"
            )
        if not result.finalizable:
            raise AnalysisError(
                result.not_finalizable_reason
                or "结果自报不可固化，与评价状态矛盾；拒绝固化正式记录"
            )

        # (2) 输入指纹必须与产生该结果的输入一致，否则拒绝固化。
        expected = request.request_fingerprint()
        if not result.request_fingerprint:
            raise AnalysisError(
                "结果未携带输入指纹，无法证明它对应本次输入；拒绝固化正式记录"
            )
        if result.request_fingerprint != expected:
            raise AnalysisError(
                "输入已在分析之后被修改，当前结果不再对应当前输入；"
                "请重新分析后再保存正式记录"
            )
        if result.product_category != request.product_category:
            raise AnalysisError("结果与输入的设备类别不一致，拒绝固化正式记录")
        if result.as_of != request.as_of:
            raise AnalysisError("结果与输入的评价日期不一致，拒绝固化正式记录")

        # (4) Canonical hash 只在**实际执行了具体 rule_profile** 时才是必需证据。
        #     类别级结论（其他类别 / 类别缺失等）没有 ruleset，不得伪造 provenance，
        #     但必须显式记录 no-ruleset 原因。
        #     `as_of` 不参与本判定：日期不是执行门禁，实际执行了规则集就必须有 hash。
        provenance = dict(result.provenance or {})
        ruleset_executed = bool(provenance.get("ruleset_executed"))
        if ruleset_executed:
            if not str(provenance.get("rule_profile") or "").strip():
                raise AnalysisError(
                    "结果声明执行了规则集但未记录 rule_profile；拒绝固化正式记录"
                )
            canonical_hash = str(
                result.references.get("standard", {}).get("pack_hash", "") or ""
            ).strip()
            if not canonical_hash:
                raise AnalysisError(
                    "实际执行了规则集的结果未携带 Canonical 包哈希，"
                    "无法证明业务真值来源；拒绝固化正式记录"
                )
        else:
            if not str(provenance.get("no_ruleset_reason") or "").strip():
                raise AnalysisError(
                    "结果未执行规则集但未记录 no-ruleset 原因；拒绝固化正式记录"
                )
            if str(result.references.get("standard", {}).get("pack_hash", "") or "").strip():
                raise AnalysisError(
                    "未执行规则集的结果不得携带 Canonical 包哈希（禁止伪造 provenance）；"
                    "拒绝固化正式记录"
                )

        # (3) 绑定 Workspace 时必须核对 revision，防止草稿在分析后又被改动。
        if workspace_id is not None:
            if self._workspaces is None:
                raise AnalysisError("未装配 Workspace 仓储，无法核对草稿修订号")
            workspace = self._workspaces.load_workspace(workspace_id)
            if workspace is None:
                raise AnalysisError(f"草稿不存在，无法固化正式记录: {workspace_id}")
            if result.workspace_revision is None:
                raise AnalysisError(
                    "结果未绑定草稿修订号，无法证明它对应当前草稿；拒绝固化正式记录"
                )
            if workspace.revision != result.workspace_revision:
                raise AnalysisError(
                    "草稿已在分析之后被修改，当前结果已过期；请重新分析后再保存正式记录"
                )
            # 显式传入本产品的业务键集合：Phase 4 之前的旧草稿没有
            # `_business_keys` 元数据，其"缺失字段 = None"的语义只能由产品层提供
            # （从载荷内容反推会静默改变历史指纹，已实测会拒绝 Base 本可合法
            # 固化的 INSUFFICIENT_DATA 草稿）。
            if workspace.request_fingerprint(PUMP_FINGERPRINT_KEYS) != expected:
                raise AnalysisError("草稿输入与待固化结果不一致，拒绝固化正式记录")

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
            # 固化结果自带的那次输入，而不是调用方此刻传入的输入。
            input_snapshot=dict(result.raw_values) | {
                "request_fingerprint": result.request_fingerprint,
                "workspace_revision": result.workspace_revision,
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
