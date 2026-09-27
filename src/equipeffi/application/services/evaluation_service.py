from datetime import date, datetime
import threading
from typing import Any

from ...domain.common.enums import Conclusion, EliminationScope
from ...domain.common.models import DeviceDraft, EvaluationResult
from ...domain.evaluation.evaluator_registry import EVALUATOR_FACTORIES
from ...domain.evaluation.device_types import DeviceTypeResolutionError, resolve_device_type
from ...domain.evaluation.elimination import EliminationMatcher
from .input_normalization import normalize_evaluation_input


DEFAULT_EVALUATION_DATE = date(2026, 8, 23)


def _coerce_elimination_scope(value: EliminationScope | str | None) -> EliminationScope:
    """Normalize the catalog scope at the core-service boundary.

    Public adapters already validate the enum, but the service is also called
    directly by the V4/JSONL/Android adapters and by maintenance scripts.  A
    plain string is equal to a ``StrEnum`` for many operations, yet it is not
    the same object: ``EliminationMatcher`` deliberately uses enum identity to
    select catalog entries.  Normalizing here prevents a string scope from
    accidentally evaluating entries from the wrong catalog.
    """

    if isinstance(value, EliminationScope):
        return value
    try:
        return EliminationScope(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"淘汰目录口径无效: {value}") from exc


def _coerce_as_of(value: date | str | None) -> date:
    """Normalize the reproducibility date at the core-service boundary."""

    if value in (None, ""):
        return DEFAULT_EVALUATION_DATE
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def scope_requires_industry_catalog(scope: EliminationScope) -> bool:
    """产业目录口径在数据未导入前不得静默退化为“未命中”。"""

    return scope in {
        EliminationScope.INDUSTRY_ONLY,
        EliminationScope.INDUSTRY_AND_MOTOR_BATCHES,
    }


def _standard_effective_date(pack: dict[str, Any]) -> date | None:
    """读取可确定的标准实施日期；非ISO描述按未知处理。"""

    raw = pack.get("effective_date")
    if raw in (None, ""):
        return None
    try:
        return date.fromisoformat(str(raw).strip())
    except (TypeError, ValueError):
        # 例如“按适用产品标准”不是本层可判断的日期，不能猜测。
        return None


def _pump_release_support(internal_device_type: str) -> str | None:
    if internal_device_type == "pump_water":
        return "SUPPORTED"
    if internal_device_type == "pump_chemical":
        return "NOT_IN_RELEASE_SCOPE"
    return None


def _requested_pump_release_support(device_type: str, values: dict[str, Any]) -> str | None:
    if str(device_type) in {"pump_water", "pump_chemical"}:
        return _pump_release_support(str(device_type))
    if str(device_type) not in {"centrifugal_pump", "离心泵"}:
        return None
    try:
        resolution = resolve_device_type(device_type, values)
    except DeviceTypeResolutionError:
        # An unresolved public category has no release-approved Profile route.
        return "NOT_IN_RELEASE_SCOPE"
    return _pump_release_support(resolution.internal_device_type)


def _apply_pump_release_support(result: EvaluationResult, internal_device_type: str) -> EvaluationResult:
    support_status = _pump_release_support(internal_device_type)
    if support_status is not None:
        result.support_status = support_status
    return result


def _evaluate_reference_result(
    internal_device_type: str,
    values: dict[str, Any],
    pack: dict[str, Any],
    *,
    public_device_type: str,
    elimination_scope: EliminationScope,
    prefix_trace: list[dict[str, Any]],
    guard_trace: list[dict[str, Any]],
    reason: str,
    missing_fields: list[str] | None = None,
    elimination_match: dict[str, Any] | None = None,
) -> tuple[EvaluationResult | None, str | None]:
    """在不确定淘汰门禁早退前保留可确定的能效参考证据。

    产业目录非全文和淘汰附加条件缺失都不能改变最终的“无法判定”。
    但只要标准包可用，就应让对应评价器提供实际指标、查表结果和比较
    轨迹。该辅助函数只包装评价器结果，不修改标准值，也不会把参考结论
    当成最终结论。
    """

    try:
        reference_result = EVALUATOR_FACTORIES[internal_device_type]().evaluate(values, pack)
    except (ValueError, ArithmeticError) as exc:
        return None, str(exc)

    reference_conclusion = reference_result.conclusion
    if reference_conclusion not in {
        Conclusion.UNABLE_TO_JUDGE,
        Conclusion.OUT_OF_SCOPE,
    }:
        reference_result.reference_conclusion = reference_conclusion
    reference_result.conclusion = Conclusion.UNABLE_TO_JUDGE
    reference_result.public_device_type = public_device_type
    reference_result.internal_device_type = internal_device_type
    reference_result.elimination_scope = elimination_scope
    reference_result.elimination_match = elimination_match
    if missing_fields:
        reference_result.missing_fields = list(dict.fromkeys([
            *missing_fields,
            *reference_result.missing_fields,
        ]))
    reference_result.trace = [
        *prefix_trace,
        *guard_trace,
        {
            "step_type": "能效参考判定",
            "output": reference_conclusion.value,
            "final_output": Conclusion.UNABLE_TO_JUDGE.value,
            "reason": f"{reason}；该能效结果仅作参考，不改变最终结论",
        },
        *reference_result.trace,
    ]
    reference_result.explanation = f"{reason}；能效参考判定为{reference_conclusion.value}"
    return reference_result, None


class EvaluationService:
    def __init__(self, standards: Any, elimination: EliminationMatcher | None = None):
        self.standards = standards
        self.elimination = elimination or EliminationMatcher()
        # 标准包在一个评价服务实例的生命周期内视为不可变快照。此前批量
        # 判定每一行都会重新读取JSON并深拷贝完整标准包；对于HVAC大表，
        # 这会造成不必要的磁盘、解析和CPU开销。评价器只读pack，因此可
        # 安全复用同一快照；锁只保护首次加载，避免并发Web请求重复加载。
        self._pack_cache: dict[str, dict[str, Any]] = {}
        self._pack_cache_lock = threading.Lock()

    def _get_pack(self, device_type: str) -> dict[str, Any]:
        cached = self._pack_cache.get(device_type)
        if cached is not None:
            return cached
        with self._pack_cache_lock:
            cached = self._pack_cache.get(device_type)
            if cached is None:
                cached = self.standards.get_pack(device_type)
                self._pack_cache[device_type] = cached
            return cached

    def evaluate(
        self,
        draft: DeviceDraft,
        as_of: date | str = DEFAULT_EVALUATION_DATE,
        elimination_scope: EliminationScope | str = EliminationScope.MOTOR_BATCHES_1_4,
    ) -> EvaluationResult:
        # Keep the domain invariant strong even when a non-API caller passes a
        # value read from a workbook/JSON configuration.  Valid strings are
        # accepted for adapter friendliness; invalid values fail explicitly
        # instead of reaching ``scope.value`` later and raising an opaque
        # AttributeError.
        elimination_scope = _coerce_elimination_scope(elimination_scope)
        input_values = dict(draft.normalized_values or draft.raw_values)
        try:
            effective_as_of = _coerce_as_of(as_of)
        except (TypeError, ValueError) as exc:
            reason = f"判定基准日期as_of无效: {as_of}"
            return EvaluationResult(
                record_id=draft.record_id,
                conclusion=Conclusion.UNABLE_TO_JUDGE,
                public_device_type=str(draft.metadata.get("public_device_type", draft.device_type)),
                support_status=_requested_pump_release_support(str(draft.device_type), input_values),
                elimination_scope=elimination_scope,
                explanation=reason,
                missing_fields=["as_of"],
                notes=[str(exc)],
                trace=[{
                    "step_type": "判定基准日期",
                    "as_of": str(as_of),
                    "scope": elimination_scope.value,
                    "output": Conclusion.UNABLE_TO_JUDGE.value,
                    "reason": reason,
                }],
            )
        try:
            resolution = resolve_device_type(draft.device_type, input_values)
        except DeviceTypeResolutionError as exc:
            public_pump = str(draft.device_type) in {"centrifugal_pump", "离心泵"}
            if public_pump:
                category = str(input_values.get("product_type", input_values.get("category", input_values.get("设备类别", ""))) or "").strip()
                is_other = category in {"OTHER", "其他类别", "其他（请备注说明）", "其他(请备注说明)"}
                if is_other:
                    return EvaluationResult(
                        record_id=draft.record_id,
                        conclusion=Conclusion.NOT_APPLICABLE,
                        public_device_type="centrifugal_pump",
                        support_status="NOT_IN_RELEASE_SCOPE",
                        category_status="NOT_APPLICABLE",
                        evaluation_status="OUT_OF_STANDARD_SCOPE",
                        issue_codes=["CATEGORY_NOT_APPLICABLE"],
                        explanation="已确认该产品类别不属于本标准列出的泵型，不执行标准公式",
                        standard_reference={"standard_code": "GB 19762-2025", "standard_name": "离心泵能效限定值及能效等级"},
                        trace=[{"step_type": "泵类别判定", "output": Conclusion.NOT_APPLICABLE.value, "reason": "CATEGORY_NOT_APPLICABLE"}],
                    )
                missing = not category
                reason = "产品类别缺失，无法确定GB 19762-2025产品类别" if missing else str(exc)
                return EvaluationResult(
                    record_id=draft.record_id,
                    conclusion=Conclusion.UNABLE_TO_JUDGE,
                    public_device_type="centrifugal_pump",
                    support_status="NOT_IN_RELEASE_SCOPE",
                    category_status="UNRESOLVED",
                    evaluation_status="INSUFFICIENT_DATA" if missing else "INVALID_INPUT",
                    issue_codes=["CATEGORY_UNRESOLVED", *( ["CATEGORY_MISSING"] if missing else [])],
                    explanation=reason,
                    missing_fields=["产品类别"] if missing else [],
                    standard_reference={"standard_code": "GB 19762-2025", "standard_name": "离心泵能效限定值及能效等级"},
                    trace=[{"step_type": "泵类别判定", "output": Conclusion.UNABLE_TO_JUDGE.value, "reason": "CATEGORY_UNRESOLVED"}],
                )
            return EvaluationResult(
                record_id=draft.record_id,
                conclusion=Conclusion.UNABLE_TO_JUDGE,
                public_device_type=str(draft.metadata.get("public_device_type", draft.device_type)),
                elimination_scope=elimination_scope,
                explanation=str(exc),
                missing_fields=["设备类型路由信息"],
                trace=[
                    {"step_type": "判定基准日期", "as_of": effective_as_of.isoformat(), "output": "已确定"},
                    {"step_type": "设备类型路由", "scope": elimination_scope.value, "output": Conclusion.UNABLE_TO_JUDGE.value, "reason": str(exc)},
                ],
            )

        internal_device_type = resolution.internal_device_type
        public_device_type = str(draft.metadata.get("public_device_type", resolution.public_device_type))
        if internal_device_type not in EVALUATOR_FACTORIES:
            raise KeyError(f"未注册设备评价器: {internal_device_type}")

        values, normalization_changes = normalize_evaluation_input(internal_device_type, input_values)
        values.setdefault("record_id", draft.record_id)
        source_trace = []
        if draft.metadata.get("input_source") == "V4":
            source_trace.append({
                "step_type": "V4工作表适配",
                "sheet": draft.metadata.get("v4_sheet", ""),
                "public_device_type": public_device_type,
                "internal_device_type": internal_device_type,
                "changes": draft.metadata.get("v4_route_changes", []),
            })
        route_trace = {
            "step_type": "公共设备类型路由",
            "requested_type": draft.device_type,
            "public_device_type": public_device_type,
            "internal_device_type": internal_device_type,
            "changes": list(resolution.changes),
        }
        normalization_trace = {"step_type": "输入规范化", "as_of": effective_as_of.isoformat(), "device_type": internal_device_type, "changes": normalization_changes}
        pack = self._get_pack(internal_device_type)
        if internal_device_type == "pump_chemical":
            category = str(values.get("category", values.get("product_type", "")) or "").strip()
            if category in {"OTHER", "其他类别", "其他（请备注说明）", "其他(请备注说明)"}:
                return EvaluationResult(
                    record_id=draft.record_id,
                    conclusion=Conclusion.NOT_APPLICABLE,
                    public_device_type=public_device_type,
                    internal_device_type=internal_device_type,
                    support_status="NOT_IN_RELEASE_SCOPE",
                    category_status="NOT_APPLICABLE",
                    evaluation_status="OUT_OF_STANDARD_SCOPE",
                    issue_codes=["CATEGORY_NOT_APPLICABLE"],
                    standard_reference={"standard_code": pack.get("standard_code", ""), "pack_id": pack.get("pack_id", ""), "data_version": pack.get("data_version", "")},
                    explanation="已确认该产品类别不属于本标准列出的泵型，不执行标准公式",
                    trace=[{"step_type": "Profile范围", "output": Conclusion.NOT_APPLICABLE.value, "reason": "CATEGORY_NOT_APPLICABLE"}],
                )
            if category not in {"单级石油化工离心泵", "多级石油化工离心泵", "单级", "多级"}:
                missing_category = not category
                return EvaluationResult(
                    record_id=draft.record_id,
                    conclusion=Conclusion.UNABLE_TO_JUDGE,
                    public_device_type=public_device_type,
                    internal_device_type=internal_device_type,
                    support_status="NOT_IN_RELEASE_SCOPE",
                    category_status="UNRESOLVED",
                    evaluation_status="INSUFFICIENT_DATA" if missing_category else "INVALID_INPUT",
                    issue_codes=["CATEGORY_UNRESOLVED", *( ["CATEGORY_MISSING"] if missing_category else [])],
                    standard_reference={"standard_code": pack.get("standard_code", ""), "pack_id": pack.get("pack_id", ""), "data_version": pack.get("data_version", "")},
                    explanation="石化泵产品类别未解析；未执行公式，当前Profile尚未进入发布支持状态",
                    missing_fields=["产品类别"] if missing_category else [],
                    trace=[{"step_type": "泵类别判定", "output": Conclusion.UNABLE_TO_JUDGE.value, "reason": "CATEGORY_UNRESOLVED"}],
                )
            # 化工泵已列入Windows V1目标范围，但V1发布支持仍受同等Phase 1门禁约束。
            return EvaluationResult(
                record_id=draft.record_id,
                conclusion=Conclusion.NOT_IN_RELEASE_SCOPE,
                public_device_type=public_device_type,
                internal_device_type=internal_device_type,
                support_status="NOT_IN_RELEASE_SCOPE",
                category_status="APPLICABLE",
                evaluation_status=None,
                issue_codes=["PROFILE_NOT_IN_RELEASE_SCOPE"],
                standard_reference={"standard_code": pack.get("standard_code", ""), "pack_id": pack.get("pack_id", ""), "data_version": pack.get("data_version", ""), "status": pack.get("status", "")},
                explanation="pump_chemical已纳入Windows V1目标范围，但尚未通过等同于清水泵的Phase 1验收门槛；当前版本未支持",
                trace=[{"step_type": "Profile范围", "output": Conclusion.NOT_IN_RELEASE_SCOPE.value, "reason": "PROFILE_NOT_IN_RELEASE_SCOPE"}],
            )
        decision = self.elimination.match(internal_device_type, values, elimination_scope)
        effective_date = _standard_effective_date(pack)

        # 标准实施日前不得调用评价器。尤其是产业目录处于非全文状态时，
        # 之前的“未覆盖”门禁会先调用评价器并把未来标准的阈值作为参考
        # 结果返回；明确命中产业淘汰目录时也会错误地产生未来参考等级。
        # 淘汰目录判定独立于能效标准，因此保留明确/疑似命中证据，但
        # 跳过所有标准查表、计算和比较，直到调用方提供不早于实施日的
        # as_of。这样既不改变淘汰结论，也不把未来标准值泄露到结果中。
        if effective_date is not None and effective_as_of < effective_date:
            if decision.matched:
                elimination_output = "明确命中"
                conclusion = Conclusion.ELIMINATED
                explanation = "明确命中淘汰目录；标准尚未实施，未计算参考能效等级"
                missing_fields: list[str] = []
            elif decision.possible:
                elimination_output = "疑似命中"
                conclusion = Conclusion.UNABLE_TO_JUDGE
                explanation = "型号疑似命中淘汰目录，但附加条件信息不足；标准尚未实施，未计算参考能效等级"
                missing_fields = list((decision.detail or {}).get("missing_conditions", []))
            else:
                elimination_output = "未命中"
                conclusion = Conclusion.UNABLE_TO_JUDGE
                explanation = f"判定基准日期{effective_as_of.isoformat()}早于标准实施日期{effective_date.isoformat()}，不能使用该标准"
                missing_fields = []
            elimination_trace = {
                "step_type": "淘汰检查",
                "scope": elimination_scope.value,
                "output": elimination_output,
            }
            if decision.detail:
                elimination_trace.update(decision.detail)
            standard_date_reason = (
                f"判定基准日期{effective_as_of.isoformat()}早于标准实施日期{effective_date.isoformat()}，"
                "不能使用该标准；标准查表和能效计算已跳过"
            )
            standard_date_trace = {
                "step_type": "标准生效日期",
                "as_of": effective_as_of.isoformat(),
                "effective_date": effective_date.isoformat(),
                "output": conclusion.value if conclusion is Conclusion.UNABLE_TO_JUDGE else "已跳过",
                "reason": standard_date_reason,
                "standard_evaluation_skipped": True,
            }
            return _apply_pump_release_support(EvaluationResult(
                record_id=draft.record_id,
                conclusion=conclusion,
                public_device_type=public_device_type,
                internal_device_type=internal_device_type,
                elimination_match=decision.detail if (decision.matched or decision.possible) else None,
                elimination_scope=elimination_scope,
                explanation=explanation,
                missing_fields=missing_fields,
                standard_reference={
                    "standard_code": pack.get("standard_code", ""),
                    "pack_id": pack.get("pack_id", ""),
                    "effective_date": effective_date.isoformat(),
                    "data_version": pack.get("data_version", ""),
                },
                notes=[standard_date_reason],
                trace=[
                    *source_trace,
                    normalization_trace,
                    route_trace,
                    elimination_trace,
                    standard_date_trace,
                ],
            ), internal_device_type)
        if decision.possible:
            # 型号已经疑似命中淘汰目录，但附加条件（例如生产年份）缺失时，
            # 最终结论必须保持“无法判定”。同时保留可确定的能效参考证据。
            possible_trace = {
                "step_type": "淘汰检查",
                "scope": elimination_scope.value,
                "output": "疑似命中",
                **(decision.detail or {}),
            }
            missing_conditions = list((decision.detail or {}).get("missing_conditions", []))
            reference_result, reference_error = _evaluate_reference_result(
                internal_device_type,
                values,
                pack,
                public_device_type=public_device_type,
                elimination_scope=elimination_scope,
                prefix_trace=[*source_trace, normalization_trace, route_trace],
                guard_trace=[possible_trace],
                reason="型号疑似命中淘汰目录，但附加条件信息不足",
                missing_fields=missing_conditions,
                elimination_match=decision.detail,
            )
            if reference_result is not None:
                return _apply_pump_release_support(reference_result, internal_device_type)

            fallback = EvaluationResult(
                record_id=draft.record_id,
                conclusion=Conclusion.UNABLE_TO_JUDGE,
                public_device_type=public_device_type,
                internal_device_type=internal_device_type,
                elimination_match=decision.detail,
                elimination_scope=elimination_scope,
                standard_reference={"pack_id": pack.get("pack_id"), "data_version": pack.get("data_version")},
                explanation="型号疑似命中淘汰目录，但附加条件信息不足",
                missing_fields=list((decision.detail or {}).get("missing_conditions", [])),
                trace=[
                    *source_trace,
                    normalization_trace,
                    route_trace,
                    {"step_type": "淘汰检查", "scope": elimination_scope.value, "output": "疑似命中", **(decision.detail or {})},
                ],
            )
            if reference_error:
                fallback.notes.append(f"能效参考判定异常：{reference_error}")
            return _apply_pump_release_support(fallback, internal_device_type)
        # 产业结构调整目录当前可能只载入用户明确提供的受控子集。目录
        # 未完成全文核对时，未命中不能被解释为“未淘汰”，否则会绕过
        # 尚未导入的条目继续给出能效等级。明确命中/条件不足仍在上面
        # 按原规则返回；第一至第四批单独口径不受此门禁影响。
        if (
            not decision.matched
            and scope_requires_industry_catalog(elimination_scope)
            and not getattr(self.elimination, "industry_catalog_complete", False)
        ):
            if not self.elimination.has_industry_catalog:
                reason = "当前版本未载入产业结构调整目录条目；请改用第一至第四批机电淘汰目录口径，或待产业目录数据载入后再判定"
            else:
                reason = "当前产业结构调整目录仅载入用户提供的受控条目，尚非全文；未命中不代表不在目录，暂无法判定"
            industry_guard_trace = {
                "step_type": "淘汰检查",
                "scope": elimination_scope.value,
                "output": "未覆盖、无法判定",
                "reason": reason,
                "catalog_status": getattr(self.elimination, "industry_catalog_status", ""),
                "catalog_complete": False,
            }
            reference_result, reference_error = _evaluate_reference_result(
                internal_device_type,
                values,
                pack,
                public_device_type=public_device_type,
                elimination_scope=elimination_scope,
                prefix_trace=[*source_trace, normalization_trace, route_trace],
                guard_trace=[industry_guard_trace],
                reason=reason,
            )
            if reference_result is not None:
                return _apply_pump_release_support(reference_result, internal_device_type)

            fallback = EvaluationResult(
                record_id=draft.record_id,
                conclusion=Conclusion.UNABLE_TO_JUDGE,
                public_device_type=public_device_type,
                internal_device_type=internal_device_type,
                elimination_scope=elimination_scope,
                standard_reference={
                    "standard_code": pack.get("standard_code", ""),
                    "pack_id": pack.get("pack_id"),
                    "data_version": pack.get("data_version"),
                },
                explanation=reason,
                notes=[reason],
                trace=[
                    *source_trace,
                    normalization_trace,
                    route_trace,
                    industry_guard_trace,
                ],
            )
            if reference_error:
                fallback.notes.append(f"能效参考判定异常：{reference_error}")
            return _apply_pump_release_support(fallback, internal_device_type)
        evaluator = EVALUATOR_FACTORIES[internal_device_type]()
        try:
            result = evaluator.evaluate(values, pack)
        except (ValueError, ArithmeticError) as exc:
            result = EvaluationResult(
                record_id=draft.record_id,
                conclusion=Conclusion.UNABLE_TO_JUDGE,
                public_device_type=public_device_type,
                internal_device_type=internal_device_type,
                standard_reference={"pack_id": pack.get("pack_id"), "data_version": pack.get("data_version")},
                explanation=f"输入参数格式或数值无效：{exc}",
                notes=[str(exc)],
                trace=[{"step_type": "输入校验", "output": "无法判定", "reason": str(exc)}],
            )
        result.elimination_scope = elimination_scope
        result.public_device_type = public_device_type
        result.internal_device_type = internal_device_type
        prefix_trace = [*source_trace, normalization_trace, route_trace]
        result.trace[0:0] = prefix_trace
        elimination_trace = {
            "step_type": "淘汰检查",
            "scope": elimination_scope.value,
            "output": "明确命中" if decision.matched else "未命中",
        }
        # 命中时将目录可审计字段同时写入轨迹；结果对象中的
        # elimination_match 仍保留同一份结构化详情供API直接使用。
        if decision.matched and decision.detail:
            elimination_trace.update(decision.detail)
        result.trace.insert(len(prefix_trace), elimination_trace)
        if decision.matched:
            result.reference_conclusion = result.conclusion
            result.conclusion = Conclusion.ELIMINATED
            result.elimination_match = decision.detail
            result.explanation = f"明确命中淘汰目录；参考能效等级为{result.reference_conclusion.value}"
        return _apply_pump_release_support(result, internal_device_type)
