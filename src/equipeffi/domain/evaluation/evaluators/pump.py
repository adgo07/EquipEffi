"""GB 19762-2025清水和石油化工离心泵评价器。"""
from __future__ import annotations

from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from functools import wraps
from typing import Any


PUMP_NUMERIC_PRECISION = 50
PUMP_DECIMAL_CONTEXT = Context(prec=PUMP_NUMERIC_PRECISION, rounding=ROUND_HALF_EVEN)
_RAW_NUMERIC_FIELDS = (
    ("QBEP", "flow_m3h", "flow", "流量"),
    ("HBEP", "head_m", "head", "扬程"),
    ("speed", "rated_speed_rpm", "额定转速"),
    ("stages", "级数"),
    ("efficiency", "pump_efficiency", "泵效率"),
)
_OTHER_CATEGORY_VALUES = {"OTHER", "其他类别", "其他（请备注说明）", "其他(请备注说明)"}
_PUMP_FIELD_ALIASES = {
    "产品类别": ("category", "product_type", "设备类别"),
    "流量": ("flow_m3h", "QBEP", "flow", "流量"),
    "扬程": ("head_m", "HBEP", "head", "扬程"),
    "额定转速": ("rated_speed_rpm", "speed", "额定转速"),
    "级数": ("stages", "级数"),
    "泵效率": ("pump_efficiency", "efficiency", "泵效率"),
    "单双吸": ("suction", "单双吸"),
}
_PUMP_INVALID_ISSUE_CODES = {
    "流量": "FLOW_INVALID",
    "扬程": "HEAD_INVALID",
    "额定转速": "SPEED_INVALID",
    "级数": "STAGES_INVALID",
    "泵效率": "EFFICIENCY_INVALID",
    "单双吸": "SUCTION_INVALID",
}


def _pump_inputs(values: dict[str, Any]) -> dict[str, Any]:
    """Accept v0.3 names and legacy field names without inserting defaults."""
    normalized = dict(values)
    aliases = {
        "product_type": "category",
        "QBEP": "flow_m3h",
        "HBEP": "head_m",
        "speed": "rated_speed_rpm",
        "efficiency": "pump_efficiency",
    }
    for source, target in aliases.items():
        if normalized.get(target) in (None, "") and normalized.get(source) not in (None, ""):
            normalized[target] = normalized[source]
    category_aliases = {
        "单级单吸清水离心泵": "单级单吸", "单级双吸清水离心泵": "单级双吸",
        "管道清水离心泵": "管道", "多级清水离心泵": "多级",
        "轻型多级清水离心泵（立式）": "轻型多级立式",
        "轻型多级清水离心泵（卧式）": "轻型多级卧式",
    }
    if normalized.get("category") in category_aliases:
        normalized["category"] = category_aliases[normalized["category"]]
    return normalized


def _is_other_category(category: Any) -> bool:
    return str(category or "").strip() in _OTHER_CATEGORY_VALUES


def _strict_pump_decimal(value: Any) -> Decimal:
    """Parse exact decimal text; reject an already-rounded binary float."""
    if isinstance(value, float):
        raise ValueError("离心泵数值必须以十进制文本传入，不能先解析为binary float")
    if isinstance(value, Decimal):
        number = value
    elif isinstance(value, (str, int)) and not isinstance(value, bool):
        try:
            number = Decimal(str(value).strip())
        except InvalidOperation as exc:
            raise ValueError("不是有效十进制文本") from exc
    else:
        raise ValueError("离心泵数值必须是十进制文本")
    if not number.is_finite():
        raise ValueError("数值必须为有限十进制数")
    return number


def _category_status(profile: str, category: Any, pack: dict[str, Any]) -> str:
    if _is_other_category(category):
        return "NOT_APPLICABLE"
    if not str(category or "").strip():
        return "UNRESOLVED"
    if profile == "pump_water":
        known = {str(row.get("type", "")) for row in pack.get("water", {}).get("ci", [])}
    else:
        known = {"单级石油化工离心泵", "多级石油化工离心泵", "单级", "多级"}
    return "APPLICABLE" if str(category).strip() in known else "UNRESOLVED"


def _has_pump_value(values: dict[str, Any], display_field: str) -> bool:
    return any(values.get(name) not in (None, "") for name in _PUMP_FIELD_ALIASES.get(display_field, ()))


def _finalize_pump_result(profile: str, values: dict[str, Any], pack: dict[str, Any], result):
    from ...common.enums import Conclusion

    category = values.get("category", values.get("product_type"))
    category_status = _category_status(profile, category, pack)
    result.category_status = category_status
    result.grade = None
    result.issue_codes = []

    if category_status == "NOT_APPLICABLE":
        result.conclusion = Conclusion.NOT_APPLICABLE
        result.evaluation_status = "OUT_OF_STANDARD_SCOPE"
        result.issue_codes = ["CATEGORY_NOT_APPLICABLE"]
        for step in result.trace:
            if step.get("output") == Conclusion.OUT_OF_SCOPE.value:
                step["output"] = Conclusion.NOT_APPLICABLE.value
        return result

    if category_status == "UNRESOLVED":
        result.conclusion = Conclusion.UNABLE_TO_JUDGE
        result.evaluation_status = "INSUFFICIENT_DATA" if not str(category or "").strip() else "INVALID_INPUT"
        result.issue_codes = ["CATEGORY_UNRESOLVED"]
        if not str(category or "").strip():
            result.issue_codes.append("CATEGORY_MISSING")
        return result

    if result.conclusion is Conclusion.OUT_OF_SCOPE:
        result.conclusion = Conclusion.NOT_APPLICABLE
        result.evaluation_status = "OUT_OF_STANDARD_SCOPE"
        result.issue_codes = ["OUT_OF_STANDARD_SCOPE"]
        for step in result.trace:
            if step.get("output") == Conclusion.OUT_OF_SCOPE.value:
                step["output"] = Conclusion.NOT_APPLICABLE.value
        return result

    if result.conclusion is Conclusion.UNABLE_TO_JUDGE:
        invalid_fields = [field for field in result.missing_fields if _has_pump_value(values, field)]
        missing_fields = [field for field in result.missing_fields if field not in invalid_fields]
        result.missing_fields = missing_fields
        if invalid_fields:
            result.evaluation_status = "INVALID_INPUT"
            result.issue_codes = [
                _PUMP_INVALID_ISSUE_CODES.get(field, "INVALID_INPUT")
                for field in invalid_fields
            ]
        elif missing_fields:
            result.evaluation_status = "INSUFFICIENT_DATA"
            for field in missing_fields:
                code = {"单双吸": "SUCTION_MISSING", "级数": "STAGES_MISSING", "产品类别": "CATEGORY_MISSING"}.get(field, "REQUIRED_INPUT_MISSING")
                if code not in result.issue_codes:
                    result.issue_codes.append(code)
        else:
            result.evaluation_status = "INVALID_INPUT"
            explanation = result.explanation
            if "单双吸" in explanation or "suction" in explanation.lower():
                result.issue_codes.append("SUCTION_CATEGORY_CONFLICT")
            elif "级数" in explanation or "stage" in explanation.lower():
                result.issue_codes.append("STAGE_CATEGORY_CONFLICT")
            elif "类别" in explanation:
                result.issue_codes.append("CATEGORY_UNRESOLVED")
            else:
                result.issue_codes.append("INVALID_INPUT")
        return result

    result.evaluation_status = "SUCCESS"
    result.grade = {
        Conclusion.LEVEL_1: "1",
        Conclusion.LEVEL_2: "2",
        Conclusion.LEVEL_3: "3",
        Conclusion.NOT_COMPLIANT: "BELOW_MINIMUM",
    }.get(result.conclusion)
    return result


def _pump_status(profile: str):
    def decorate(method):
        @wraps(method)
        def wrapped(self, values: dict[str, Any], pack: dict[str, Any]):
            normalized = _pump_inputs(values)
            with localcontext(PUMP_DECIMAL_CONTEXT):
                result = method(self, normalized, pack)
            return _finalize_pump_result(profile, normalized, pack, result)

        return wrapped

    return decorate


def _pump_category_gate(profile: str, values: dict[str, Any], pack: dict[str, Any], unable, out_of_scope):
    category_value = values.get("category", values.get("product_type"))
    category = str(category_value or "").strip()
    if _is_other_category(category):
        return out_of_scope(
            str(values.get("record_id", "")), pack,
            "已确认该产品类别不属于本标准列出的泵型，不执行标准公式",
        )
    if profile == "pump_water":
        known = {str(row.get("type", "")) for row in pack.get("water", {}).get("ci", [])}
    else:
        known = {"单级石油化工离心泵", "多级石油化工离心泵", "单级", "多级"}
    if category not in known:
        missing = ["产品类别"] if not category else []
        reason = "产品类别缺失，无法确定GB 19762-2025产品类别" if not category else f"产品类别{category!r}无法映射到GB 19762-2025泵型"
        return unable(str(values.get("record_id", "")), pack, reason, missing)
    return None


def _pump_binary_float_gate(values: dict[str, Any], pack: dict[str, Any], unable):
    float_fields: list[str] = []
    labels = {
        "QBEP": "QBEP", "flow_m3h": "QBEP", "flow": "QBEP", "流量": "QBEP",
        "HBEP": "HBEP", "head_m": "HBEP", "head": "HBEP", "扬程": "HBEP",
        "speed": "speed", "rated_speed_rpm": "speed", "额定转速": "speed",
        "stages": "stages", "级数": "stages",
        "efficiency": "efficiency", "pump_efficiency": "efficiency", "泵效率": "efficiency",
    }
    for key, label in labels.items():
        if isinstance(values.get(key), float) and label not in float_fields:
            float_fields.append(label)
    if float_fields:
        return unable(
            str(values.get("record_id", "")), pack,
            "离心泵数值必须按十进制文本传入；拒绝已解析为binary float的字段：" + "、".join(float_fields),
        )
    return None


def _pump_alias_conflicts(values: dict[str, Any]) -> list[str]:
    groups = (
        ("产品类别", ("product_type", "category", "设备类别"), False),
        ("QBEP", ("QBEP", "flow_m3h", "flow", "流量"), True),
        ("HBEP", ("HBEP", "head_m", "head", "扬程"), True),
        ("speed", ("speed", "rated_speed_rpm", "额定转速"), True),
        ("stages", ("stages", "级数"), True),
        ("suction", ("suction", "单双吸"), False),
        ("efficiency", ("efficiency", "pump_efficiency", "泵效率"), True),
    )
    conflicts: list[str] = []
    for label, keys, numeric in groups:
        present = [(key, values[key]) for key in keys if values.get(key) not in (None, "")]
        if len(present) < 2:
            continue
        try:
            normalized = [(_strict_pump_decimal(value) if numeric else str(value).strip()) for _, value in present]
        except ValueError:
            continue  # Parsing/validation below reports the malformed raw field.
        if label == "产品类别":
            aliases = {
                "单级单吸清水离心泵": "单级单吸", "单级双吸清水离心泵": "单级双吸",
                "管道清水离心泵": "管道", "多级清水离心泵": "多级",
                "轻型多级清水离心泵（立式）": "轻型多级立式",
                "轻型多级清水离心泵（卧式）": "轻型多级卧式",
            }
            normalized = [aliases.get(str(value), value) for value in normalized]
        if any(value != normalized[0] for value in normalized[1:]):
            conflicts.append(label)
    return conflicts


def _specific_speed_in_context(values: dict[str, Any], chemical: bool = False) -> tuple[Decimal, dict[str, Any]]:
    """Calculate the standard specific-speed inputs for a centrifugal pump."""

    from ..device_evaluators import _value
    from ..decimal_math import decimal

    values = _pump_inputs(values)
    q_h = _strict_pump_decimal(_value(values, "flow_m3h", "流量"))
    n = _strict_pump_decimal(_value(values, "rated_speed_rpm", "额定转速"))
    h = _strict_pump_decimal(_value(values, "head_m", "扬程"))
    stages_raw = _value(values, "stages", "级数")
    suction = str(_value(values, "suction", "单双吸") or "").strip()
    if stages_raw in (None, "") or suction not in {"单吸", "双吸"}:
        raise ValueError("比转速计算必须显式提供合法的suction和stages")
    stages = _strict_pump_decimal(stages_raw)
    if stages <= 0 or stages != stages.to_integral_value():
        raise ValueError("stages必须为正整数")
    suction_factor = Decimal("2") if suction == "双吸" else Decimal("1")
    q_ns_m3h = q_h / suction_factor
    q_ns = q_ns_m3h / Decimal("3600")
    stage_count = int(stages)
    h_ns = h / Decimal(stage_count)
    head_power = PUMP_DECIMAL_CONTEXT.power(h_ns, Decimal("0.75"))
    ns = Decimal("3.65") * n * q_ns.sqrt() / head_power
    derived = {
        "suction_factor": suction_factor,
        "stage_count": stage_count,
        "q_for_ns_m3s": q_ns,
        "h_for_ns_m": h_ns,
        "ns_raw": ns,
        # 保留现有报告字段作为兼容映射，值仍来自显式Q/H/K/L。
        "计算流量_m3/h": q_ns_m3h,
        "单级扬程_m": h_ns,
        "比转速": ns,
    }
    return ns, derived


def _specific_speed(values: dict[str, Any], chemical: bool = False) -> tuple[Decimal, dict[str, Any]]:
    with localcontext(PUMP_DECIMAL_CONTEXT):
        return _specific_speed_in_context(values, chemical)


def _known_pump_diagnostics(values: dict[str, Any]) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    """Retain independently computable measurements when flow is out of scope."""
    def value(*keys: str):
        for key in keys:
            if values.get(key) not in (None, ""):
                return values[key]
        return None

    actual_metrics: dict[str, Decimal] = {}
    calculated_metrics: dict[str, Decimal] = {}
    try:
        efficiency_raw = value("efficiency", "pump_efficiency", "泵效率")
        if efficiency_raw is not None:
            efficiency = _strict_pump_decimal(efficiency_raw)
            if Decimal("0") <= efficiency <= Decimal("100"):
                actual_metrics["泵效率_%"] = efficiency
    except (ValueError, InvalidOperation):
        pass

    try:
        q = _strict_pump_decimal(value("QBEP", "flow_m3h", "flow", "流量"))
        head = _strict_pump_decimal(value("HBEP", "head_m", "head", "扬程"))
        if q > 0 and head > 0:
            with localcontext(PUMP_DECIMAL_CONTEXT):
                calculated_metrics["输出功率_kW"] = Decimal("9.81") * q / Decimal("3600") * head
    except (ValueError, InvalidOperation, TypeError):
        pass

    if all(value(*keys) is not None for keys in (
        ("QBEP", "flow_m3h", "flow", "流量"),
        ("HBEP", "head_m", "head", "扬程"),
        ("speed", "rated_speed_rpm", "额定转速"),
        ("stages", "级数"),
    )) and str(value("suction", "单双吸") or "").strip() in {"单吸", "双吸"}:
        try:
            _, ns_diagnostics = _specific_speed_in_context(values)
            calculated_metrics.update(ns_diagnostics)
        except (ValueError, InvalidOperation, TypeError, ZeroDivisionError):
            pass
    return actual_metrics, calculated_metrics


class WaterPumpEvaluator:
    @_pump_status("pump_water")
    def evaluate(self, values: dict[str, Any], pack: dict[str, Any]):
        from ..device_evaluators import (
            _active_or_unable,
            _attach_metrics,
            _attach_lookup_trace,
            _explicit_boundary_hit,
            _missing,
            _percent_or_unable,
            _positive_integer_or_unable,
            _positive_or_unable,
            _result,
            _specific_speed,
            _value,
            out_of_scope,
            unable,
        )
        from ..decimal_math import decimal, rounded
        from ..grading import grade_three
        from ...common.enums import ComparisonDirection

        if result := _active_or_unable(values, pack):
            return result
        if conflicts := _pump_alias_conflicts(values):
            return unable(str(values.get("record_id", "")), pack, "同一泵原始输入的别名字段冲突：" + "、".join(conflicts))
        if result := _pump_category_gate("pump_water", values, pack, unable, out_of_scope):
            return result
        if result := _pump_binary_float_gate(values, pack, unable):
            return result
        category = str(_value(values, "category", "product_type", "设备类别"))
        suction = str(_value(values, "suction", "单双吸") or "").strip()
        water_rows = list(pack["water"].get("ci", []))
        q_raw = _value(values, "flow_m3h", "QBEP", "流量")
        if q_raw not in (None, ""):
            try:
                q_probe = _strict_pump_decimal(q_raw)
            except ValueError:
                q_probe = None
            if q_probe is not None and q_probe > 0:
                flow_rows = [
                    row for row in water_rows
                    if row.get("type") == category
                    and _explicit_boundary_hit(
                        q_probe, row["q_min"], row["q_max"],
                        [{"min": row["q_min"], "max": row["q_max"],
                          "min_inclusive": row.get("min_inclusive", True),
                          "max_inclusive": row.get("max_inclusive", True)}],
                    )
                ]
                if not flow_rows:
                    result = out_of_scope(str(values.get("record_id", "")), pack, "总流量QBEP未命中GB 19762-2025表3适用区间")
                    candidate_rows = [row for row in water_rows if row.get("type") == category]
                    lookup = {
                        "step_type": "精确查表", "table": "表3",
                        "data_ids": [str(row.get("data_id")) for row in candidate_rows if row.get("data_id") not in (None, "")],
                        "matching": "泵型+总流量QBEP", "category": category,
                        "flow_value_m3h": str(q_probe), "match_status": "流量档位未命中",
                        "flow_ranges": [
                            {
                                "min": str(row["q_min"]), "max": str(row["q_max"]),
                                "min_inclusive": row.get("min_inclusive", True),
                                "max_inclusive": row.get("max_inclusive", True),
                            }
                            for row in candidate_rows
                        ],
                        "source_clause": "6.1、6.2、表3",
                        "source_pages": candidate_rows[0].get("source_pages", "") if candidate_rows else "",
                        "no_interpolation": True,
                    }
                    result = _attach_metrics(result, *_known_pump_diagnostics(values))
                    return _attach_lookup_trace(result, pack, "表3", [lookup])
        missing = _missing(values, [("设备类别", ("category", "设备类别")), ("流量", ("flow_m3h", "流量")), ("扬程", ("head_m", "扬程")), ("额定转速", ("rated_speed_rpm", "额定转速")), ("泵效率", ("pump_efficiency", "泵效率"))])
        # 泵效率只用于最终三级比较，不参与清水泵的泵型/流量查表、
        # 比转速和C1～C3公式计算。单独缺失时延后比较，以保留
        # 可复核的计算值、标准阈值和来源；其他判定轴缺失仍直接退出。
        defer_efficiency_missing = missing == ["泵效率"]
        if missing and not defer_efficiency_missing:
            return unable(str(values.get("record_id", "")), pack, "缺少清水离心泵判定参数", missing)
        if result := _positive_or_unable(values, pack, [
            ("流量", ("flow_m3h", "流量")), ("扬程", ("head_m", "扬程")),
            ("额定转速", ("rated_speed_rpm", "额定转速")), ("级数", ("stages", "级数")),
        ]):
            return result
        if result := _positive_integer_or_unable(values, pack, [("级数", ("stages", "级数"))]):
            return result
        if result := _percent_or_unable(values, pack, "泵效率", ("pump_efficiency", "泵效率")):
            return result
        q = decimal(_value(values, "flow_m3h", "流量"))
        actual = None if defer_efficiency_missing else decimal(_value(values, "pump_efficiency", "泵效率"))
        actual_metrics = {} if actual is None else {"泵效率_%": actual}
        output_power = Decimal("9.81") * q / Decimal(3600) * decimal(_value(values, "head_m", "扬程"))
        # GB 19762-2025表3只覆盖标准列出的清水泵型。公共枚举中的
        # “其他（请备注说明）”不能被默认解释为单级单吸；否则会在
        # 类别尚未确定时使用默认级数/单双吸计算出虚假的比转速。
        known_types: list[str] = []
        for row in water_rows:
            row_type = str(row.get("type", ""))
            if row_type and row_type not in known_types:
                known_types.append(row_type)
        if category not in known_types:
            lookup = {
                "step_type": "精确查表",
                "table": "表3",
                "data_ids": [
                    str(row.get("data_id"))
                    for row in water_rows
                    if row.get("data_id") not in (None, "")
                ],
                "matching": "设备类别",
                "category": category,
                "candidate_types": known_types,
                "candidate_count": len(water_rows),
                "candidate_rows": [
                    {
                        "data_id": str(row.get("data_id", "")),
                        "type": row.get("type", ""),
                        "q_min": str(row.get("q_min", "")),
                        "q_max": str(row.get("q_max", "")),
                        "min_inclusive": row.get("min_inclusive", True),
                        "max_inclusive": row.get("max_inclusive", True),
                    }
                    for row in water_rows
                ],
                "match_status": "设备类别未命中",
                "standard_rule": "GB 19762-2025表3仅适用于标准列出的清水泵型；其他类别不得默认映射",
                "source_clause": "6.1、6.2、表3",
                "source_pages": sorted({
                    str(row.get("source_pages"))
                    for row in water_rows
                    if row.get("source_pages") not in (None, "")
                }),
                "no_interpolation": True,
            }
            result = _attach_metrics(
                out_of_scope(str(values.get("record_id", "")), pack, "设备类别不在GB 19762-2025表3标准清水泵型范围内，不能默认按单级单吸计算"),
                actual_metrics,
                {"输出功率_kW": output_power},
            )
            return _attach_lookup_trace(result, pack, "表3", [lookup])
        if "多级" in category and _value(values, "stages", "级数") is None:
            # 多级泵的级数决定单级扬程，单级扬程又参与比转速公式；缺少级数时
            # 不能默认按1级计算，也不能取最近的比转速档。流量已知时仍筛选
            # 表3中该泵型对应的全部流量候选，供补录级数后复核。
            candidate_rows = [
                row for row in water_rows
                if row.get("type") == category
                and _explicit_boundary_hit(
                    q,
                    row["q_min"],
                    row["q_max"],
                    [{
                        "min": row["q_min"],
                        "max": row["q_max"],
                        "min_inclusive": row.get("min_inclusive", True),
                        "max_inclusive": row.get("max_inclusive", True),
                    }],
                )
            ]
            if not candidate_rows:
                candidate_rows = [row for row in water_rows if row.get("type") == category]
                match_status = "级数未提供且流量未命中"
            else:
                match_status = "级数未提供"
            candidate_ids = [
                str(row.get("data_id"))
                for row in candidate_rows
                if row.get("data_id") not in (None, "")
            ]
            lookup = {
                "step_type": "精确查表",
                "table": "表3",
                "data_ids": candidate_ids,
                "matching": "泵型+流量+级数（级数缺失）",
                "category": category,
                "candidate_count": len(candidate_rows),
                "candidate_rows": [
                    {
                        "data_id": str(row.get("data_id", "")),
                        "type": row.get("type", ""),
                        "q_min": str(row.get("q_min", "")),
                        "q_max": str(row.get("q_max", "")),
                        "flow_boundary": {
                            "min": row.get("q_min"),
                            "max": row.get("q_max"),
                            "min_inclusive": row.get("min_inclusive", True),
                            "max_inclusive": row.get("max_inclusive", True),
                        },
                        "ci": [str(value) for value in row.get("ci", [])],
                    }
                    for row in candidate_rows
                ],
                "query_conditions": {
                    "category": category,
                    "flow_m3h": str(q),
                    "head_m": str(_value(values, "head_m", "扬程")),
                    "rated_speed_rpm": str(_value(values, "rated_speed_rpm", "额定转速")),
                    "stages": "",
                    "suction": suction,
                    "pump_efficiency": "" if actual is None else str(actual),
                    "specific_speed": "",
                },
                "match_status": match_status,
                "standard_rule": "GB 19762-2025表3多级泵按泵型和流量查C1～C3；缺少级数时不得计算单级扬程、比转速或默认取档",
                "source_clause": "6.1、6.2、表3",
                "source_pages": sorted({
                    str(row.get("source_pages"))
                    for row in candidate_rows
                    if row.get("source_pages") not in (None, "")
                }),
                "no_interpolation": True,
                "missing_dimension": "级数",
            }
            result = _attach_metrics(
                unable(str(values.get("record_id", "")), pack, "多级清水离心泵缺少级数，无法计算单级扬程和比转速", ["级数"]),
                actual_metrics,
                {"输出功率_kW": output_power},
            )
            return _attach_lookup_trace(result, pack, "表3", [lookup])
        stages_value = _value(values, "stages", "级数")
        if stages_value is None:
            return unable(str(values.get("record_id", "")), pack, "缺少清水泵实际级数stages", ["级数"])
        if suction not in {"单吸", "双吸"}:
            return unable(str(values.get("record_id", "")), pack, "缺少或非法清水泵单双吸suction", ["单双吸"])
        stage_number = _strict_pump_decimal(stages_value)
        is_multistage = "多级" in category
        if (is_multistage and stage_number <= Decimal("1")) or (not is_multistage and stage_number != Decimal("1")):
            return unable(str(values.get("record_id", "")), pack, "清水泵类别与实际级数冲突")
        # V4同时保留完整设备类别和“单双吸”字段。类别已经明确为单吸/双吸时，
        # 两者若冲突，不能用单双吸字段静默把流量折半后继续套用另一类标准表；
        # 这会产生无法追溯的错误比转速和能效等级。
        category_suction = "双吸" if "双吸" in category else "单吸" if "单吸" in category else ""
        if category_suction and category_suction != suction:
            candidate_types = ["单级单吸", "单级双吸"]
            candidate_rows = [row for row in pack["water"]["ci"] if row.get("type") in candidate_types]
            lookup = {
                "step_type": "精确查表",
                "table": "表3",
                "data_ids": [str(row.get("data_id")) for row in candidate_rows if row.get("data_id") not in (None, "")],
                "matching": "设备类别+单双吸+流量",
                "category": category,
                "suction": suction,
                "flow_value_m3h": str(q),
                "candidate_types": candidate_types,
                "candidate_rows": [
                    {
                        "data_id": str(row.get("data_id", "")),
                        "type": row.get("type", ""),
                        "q_min": str(row.get("q_min", "")),
                        "q_max": str(row.get("q_max", "")),
                        "min_inclusive": row.get("min_inclusive", True),
                        "max_inclusive": row.get("max_inclusive", True),
                    }
                    for row in candidate_rows
                ],
                "match_status": "设备类别与单双吸冲突",
                "source_clause": "6.1、6.2、表3",
                "source_pages": candidate_rows[0].get("source_pages", "") if candidate_rows else "",
                "no_interpolation": True,
            }
            result = _attach_metrics(
                unable(str(values.get("record_id", "")), pack, "设备类别与单双吸字段冲突，无法唯一确定有效流量和标准类别"),
                actual_metrics,
                {"输出功率_kW": output_power},
            )
            return _attach_lookup_trace(result, pack, "表3", [lookup])
        ns, calculated = _specific_speed(values)
        calculated["输出功率_kW"] = output_power
        ci_candidates = [
            row for row in pack["water"]["ci"]
            if row["type"] == category
            and _explicit_boundary_hit(
                q,
                row["q_min"],
                row["q_max"],
                [{
                    "min": row["q_min"],
                    "max": row["q_max"],
                    "min_inclusive": row.get("min_inclusive", True),
                    "max_inclusive": row.get("max_inclusive", True),
                }],
            )
        ]
        ci_row = ci_candidates[0] if len(ci_candidates) == 1 else None
        if ci_row is None:
            candidate_rows = [row for row in pack["water"]["ci"] if row["type"] == category]
            lookup = {
                "step_type": "精确查表",
                "table": "表3",
                "data_ids": [str(row.get("data_id")) for row in candidate_rows if row.get("data_id") not in (None, "")],
                "matching": "泵型+流量",
                "flow_value_m3h": str(q),
                "flow_ranges": [
                    {
                        "min": str(row["q_min"]),
                        "max": str(row["q_max"]),
                        "min_inclusive": row.get("min_inclusive", True),
                        "max_inclusive": row.get("max_inclusive", True),
                    }
                    for row in candidate_rows
                ],
                "match_status": "流量档位多重命中" if len(ci_candidates) > 1 else "流量档位未命中",
                "source_clause": "6.1、6.2、表3",
                "source_pages": candidate_rows[0].get("source_pages", "") if candidate_rows else "",
            }
            if len(ci_candidates) > 1:
                result = _attach_metrics(unable(str(values.get("record_id", "")), pack, "流量命中多个清水离心泵标准分档，区间边界无法唯一确定", ["流量"]), actual_metrics, calculated)
            else:
                result = _attach_metrics(out_of_scope(str(values.get("record_id", "")), pack, "流量或泵型超出清水离心泵公式适用范围"), actual_metrics, calculated)
            return _attach_lookup_trace(result, pack, "表3", [lookup])
        kind = "多级" if "多级" in category else "单级"
        coeff = {key: decimal(value) for key, value in pack["water"]["formulas"][kind].items()}
        ln_ns, ln_q = ns.ln(), q.ln()
        base = coeff["a"] * ln_ns**2 + coeff["b"] * ln_q**2 + coeff["c"] * ln_ns * ln_q + coeff["d"] * ln_ns + coeff["e"] * ln_q
        thresholds = [base - decimal(item) for item in ci_row["ci"]]
        calculated["grade_thresholds_internal"] = [str(value) for value in thresholds]
        calculated.update({f"C{i+1}": ci_row["ci"][i] for i in range(3)})
        lookup = {
            "step_type": "公式计算",
            "rule": "GB 19762-2025公式(1)~(3)",
            "data_id": ci_row.get("data_id", ""),
            "parameters": {key: str(value) for key, value in calculated.items()},
            "grade_thresholds_internal": [str(value) for value in thresholds],
            "table": "表3",
            "matching": "泵型+流量",
            "query_conditions": {
                "category": category,
                "flow_m3h": str(q),
                "head_m": str(_value(values, "head_m", "扬程")),
                "rated_speed_rpm": str(_value(values, "rated_speed_rpm", "额定转速")),
                "stages": str(_value(values, "stages", "级数")),
                "suction": suction,
                "pump_efficiency": "" if actual is None else str(actual),
            },
            "match_status": "命中",
            "source_clause": "6.1、6.2、表3",
            "source_pages": ci_row.get("source_pages", ""),
            "flow_boundary": {
                "min": str(ci_row["q_min"]),
                "max": str(ci_row["q_max"]),
                "min_inclusive": ci_row.get("min_inclusive", True),
                "max_inclusive": ci_row.get("max_inclusive", True),
            },
        }
        limits = {f"{i+1}级效率_%": rounded(thresholds[i]) for i in range(3)}
        if defer_efficiency_missing:
            result = _attach_metrics(
                unable(str(values.get("record_id", "")), pack, "缺少泵效率，无法进行能效等级比较", ["泵效率"]),
                actual_metrics,
                calculated,
            )
            result.limits = limits
            return _attach_lookup_trace(result, pack, "表1/表3", [lookup])
        conclusion, comparisons = grade_three(actual, thresholds, ComparisonDirection.GREATER_OR_EQUAL)
        return _result(values, pack, conclusion, actual_metrics, calculated, limits, comparisons, "表1/表3", [lookup], clause="6.1、6.2、表3")


class ChemicalPumpEvaluator:
    @_pump_status("pump_chemical")
    def evaluate(self, values: dict[str, Any], pack: dict[str, Any]):
        from ..device_evaluators import (
            _active_or_unable,
            _attach_metrics,
            _attach_lookup_trace,
            _explicit_boundary_hit,
            _matching_boundary,
            _missing,
            _percent_or_unable,
            _positive_integer_or_unable,
            _positive_or_unable,
            _result,
            _specific_speed,
            _value,
            out_of_scope,
            unable,
        )
        from ..decimal_math import decimal, rounded
        from ..grading import grade_three
        from ...common.enums import ComparisonDirection

        if result := _active_or_unable(values, pack):
            return result
        if conflicts := _pump_alias_conflicts(values):
            return unable(str(values.get("record_id", "")), pack, "同一泵原始输入的别名字段冲突：" + "、".join(conflicts))
        if result := _pump_category_gate("pump_chemical", values, pack, unable, out_of_scope):
            return result
        if result := _pump_binary_float_gate(values, pack, unable):
            return result
        chemical_rules = pack["chemical"]
        q_boundaries = chemical_rules.get("interval_boundaries", {}).get("flow_q", [])
        q_probe_raw = _value(values, "flow_m3h", "QBEP", "流量")
        if q_probe_raw not in (None, ""):
            try:
                q_probe = _strict_pump_decimal(q_probe_raw)
            except ValueError:
                q_probe = None
            if q_probe is not None and Decimal("0") < q_probe <= Decimal("5"):
                result = out_of_scope(str(values.get("record_id", "")), pack, "石油化工离心泵要求总流量QBEP大于5 m³/h")
                category = str(_value(values, "category", "product_type", "设备类别"))
                pump_kind = "多级" if "多级" in category else "单级"
                candidate_rows = [row for row in chemical_rules["level_offsets"] if row.get("pump") == pump_kind]
                flow_ranges = []
                for row in candidate_rows:
                    boundary = _matching_boundary(q_probe, row["q_min"], row["q_max"], q_boundaries) or {}
                    flow_ranges.append({
                        "min": str(row["q_min"]), "max": str(row["q_max"]),
                        "min_inclusive": boundary.get("min_inclusive", row.get("min_inclusive", True)),
                        "max_inclusive": boundary.get("max_inclusive", row.get("max_inclusive", True)),
                    })
                lookup = {
                    "step_type": "精确查表", "table": "表2",
                    "data_ids": [str(row.get("data_id")) for row in candidate_rows if row.get("data_id") not in (None, "")],
                    "matching": "泵级数类型+总流量QBEP", "category": category,
                    "flow_value_m3h": str(q_probe),
                    "flow_ranges": flow_ranges,
                    "match_status": "流量档位未命中：总流量低于开区间下界",
                    "source_clause": "表2/公式(4)~(7)",
                    "source_pages": candidate_rows[0].get("source_pages", "") if candidate_rows else "",
                    "no_interpolation": True,
                }
                result = _attach_metrics(result, *_known_pump_diagnostics(values))
                return _attach_lookup_trace(result, pack, "表2", [lookup])
        missing = _missing(values, [("设备类别", ("category", "设备类别")), ("流量", ("flow_m3h", "流量")), ("扬程", ("head_m", "扬程")), ("额定转速", ("rated_speed_rpm", "额定转速")), ("泵效率", ("pump_efficiency", "泵效率"))])
        # 泵效率仅用于最终三级比较，不参与化工泵的泵级数类型、
        # 流量/比转速查表或ηb、Δη、η0计算。单独缺失时延后比较，
        # 保留完整的公式结果、标准阈值和来源；其他判定轴缺失仍直接退出。
        defer_efficiency_missing = missing == ["泵效率"]
        if missing and not defer_efficiency_missing:
            return unable(str(values.get("record_id", "")), pack, "缺少石油化工离心泵判定参数", missing)
        if result := _positive_or_unable(values, pack, [
            ("流量", ("flow_m3h", "流量")), ("扬程", ("head_m", "扬程")),
            ("额定转速", ("rated_speed_rpm", "额定转速")), ("级数", ("stages", "级数")),
        ]):
            return result
        if result := _positive_integer_or_unable(values, pack, [("级数", ("stages", "级数"))]):
            return result
        if result := _percent_or_unable(values, pack, "泵效率", ("pump_efficiency", "泵效率")):
            return result
        category = str(_value(values, "category", "设备类别"))
        stage_value = _value(values, "stages", "级数")
        pump_kind = "多级" if "多级" in category else "单级" if "单级" in category else ""
        q = decimal(_value(values, "flow_m3h", "流量"))
        output_power = Decimal("9.81") * q / Decimal(3600) * decimal(_value(values, "head_m", "扬程"))
        actual = None if defer_efficiency_missing else decimal(_value(values, "pump_efficiency", "泵效率"))
        actual_metrics = {} if actual is None else {"泵效率_%": actual}
        if pump_kind == "多级" and stage_value is None:
            # 多级泵的级数决定单级扬程，进而决定比转速；缺少级数时
            # 不能默认按1级计算，也不能取某个最近的ns档。流量已知时，
            # 仍可筛出表2中该流量对应的全部多级候选行，供补录级数后复核。
            candidate_rows = [
                row for row in chemical_rules["level_offsets"]
                if row.get("pump") == "多级"
                and _explicit_boundary_hit(q, row["q_min"], row["q_max"], q_boundaries)
            ]
            if not candidate_rows:
                candidate_rows = [
                    row for row in chemical_rules["level_offsets"]
                    if row.get("pump") == "多级"
                ]
                match_status = "级数未提供且流量未命中"
            else:
                match_status = "级数未提供"
            candidate_ids = [
                str(row.get("data_id"))
                for row in candidate_rows
                if row.get("data_id") not in (None, "")
            ]

            def flow_boundary(row: dict[str, Any]) -> dict[str, Any]:
                boundary = _matching_boundary(q, row["q_min"], row["q_max"], q_boundaries)
                if boundary is not None:
                    return boundary
                return {
                    "min": row["q_min"],
                    "max": row["q_max"],
                    "min_inclusive": row.get("min_inclusive", True),
                    "max_inclusive": row.get("max_inclusive", True),
                }

            lookup = {
                "step_type": "精确查表",
                "table": "表2",
                "data_ids": candidate_ids,
                "matching": "泵级数类型+流量+比转速（级数缺失）",
                "category": "多级",
                "pump_kind": "多级",
                "candidate_count": len(candidate_rows),
                "candidate_rows": [
                    {
                        "data_id": str(row.get("data_id", "")),
                        "pump": row.get("pump", ""),
                        "q_min": str(row.get("q_min", "")),
                        "q_max": str(row.get("q_max", "")),
                        "flow_boundary": flow_boundary(row),
                        "ns_min": str(row.get("ns_min", "")),
                        "ns_max": str(row.get("ns_max", "")),
                        "eta0_uses_delta": bool(row.get("eta0_uses_delta")),
                        "offsets": [str(value) for value in row.get("offsets", [])],
                    }
                    for row in candidate_rows
                ],
                "query_conditions": {
                    "category": category,
                    "pump_kind": "多级",
                    "flow_m3h": str(q),
                    "head_m": str(_value(values, "head_m", "扬程")),
                    "rated_speed_rpm": str(_value(values, "rated_speed_rpm", "额定转速")),
                    "stages": "",
                    "suction": str(_value(values, "suction", "单双吸") or ""),
                    "pump_efficiency": "" if actual is None else str(actual),
                    "specific_speed": "",
                },
                "match_status": match_status,
                "standard_rule": "GB 19762-2025表2按单级/多级、流量和比转速查表；缺少级数时不得计算单级扬程、比转速或默认取档",
                "source_clause": "表2/公式(4)~(7)",
                "source_pages": sorted({
                    str(row.get("source_pages"))
                    for row in candidate_rows
                    if row.get("source_pages") not in (None, "")
                }),
                "no_interpolation": True,
                "missing_dimension": "级数",
            }
            result = _attach_metrics(
                unable(str(values.get("record_id", "")), pack, "多级石油化工离心泵缺少级数，无法计算单级扬程和比转速", ["级数"]),
                actual_metrics,
                {"输出功率_kW": output_power},
            )
            return _attach_lookup_trace(result, pack, "表2", [lookup])
        if stage_value is None:
            return unable(str(values.get("record_id", "")), pack, "缺少石油化工泵实际级数stages", ["级数"])
        suction = str(_value(values, "suction", "单双吸") or "").strip()
        if suction not in {"单吸", "双吸"}:
            return unable(str(values.get("record_id", "")), pack, "缺少或非法石油化工泵单双吸suction", ["单双吸"])
        # 标准表2仅定义“单级”和“多级”两类。公共V4枚举还允许
        # “其他（请备注说明）”，但该值不能被默认解释为单级；否则
        # 未知类别会带着默认级数进入比转速公式并错误返回等级。
        if not pump_kind:
            candidate_rows = [
                row for row in chemical_rules["level_offsets"]
                if row.get("pump") in {"单级", "多级"}
            ]
            lookup = {
                "step_type": "精确查表",
                "table": "表2",
                "data_ids": [
                    str(row.get("data_id"))
                    for row in candidate_rows
                    if row.get("data_id") not in (None, "")
                ],
                "matching": "设备类别",
                "category": category,
                "candidate_types": ["单级", "多级"],
                "candidate_count": len(candidate_rows),
                "candidate_rows": [
                    {
                        "data_id": str(row.get("data_id", "")),
                        "pump": row.get("pump", ""),
                        "q_min": str(row.get("q_min", "")),
                        "q_max": str(row.get("q_max", "")),
                        "ns_min": str(row.get("ns_min", "")),
                        "ns_max": str(row.get("ns_max", "")),
                    }
                    for row in candidate_rows
                ],
                "match_status": "设备类别未命中",
                "standard_rule": "GB 19762-2025表2仅适用于单级或多级石油化工离心泵；其他类别不得默认映射",
                "source_clause": "表2/公式(4)~(7)",
                "source_pages": sorted({
                    str(row.get("source_pages"))
                    for row in candidate_rows
                    if row.get("source_pages") not in (None, "")
                }),
                "no_interpolation": True,
            }
            result = _attach_metrics(
                out_of_scope(str(values.get("record_id", "")), pack, "设备类别不在GB 19762-2025表2的单级或多级范围内，不能默认按单级计算"),
                actual_metrics,
                {"输出功率_kW": output_power},
            )
            return _attach_lookup_trace(result, pack, "表2", [lookup])
        if pump_kind and stage_value is not None:
            stage_number = decimal(stage_value)
            stage_conflict = (pump_kind == "单级" and stage_number != Decimal(1)) or (pump_kind == "多级" and stage_number <= Decimal(1))
            if stage_conflict:
                candidate_types = ["单级", "多级"]
                candidate_rows = [row for row in chemical_rules["level_offsets"] if row.get("pump") in candidate_types]
                lookup = {
                    "step_type": "精确查表",
                    "table": "表2",
                    "data_ids": [str(row.get("data_id")) for row in candidate_rows if row.get("data_id") not in (None, "")],
                    "matching": "设备类别+级数+流量+比转速",
                    "category": pump_kind,
                    "stages": str(stage_number),
                    "flow_value_m3h": str(q),
                    "candidate_types": candidate_types,
                    "candidate_rows": [
                        {
                            "data_id": str(row.get("data_id", "")),
                            "pump": row.get("pump", ""),
                            "q_min": str(row.get("q_min", "")),
                            "q_max": str(row.get("q_max", "")),
                            "ns_min": str(row.get("ns_min", "")),
                            "ns_max": str(row.get("ns_max", "")),
                        }
                        for row in candidate_rows
                    ],
                    "match_status": "泵级数与设备类别冲突",
                    "source_clause": "表2/公式(4)~(7)",
                    "source_pages": candidate_rows[0].get("source_pages", "") if candidate_rows else "",
                    "no_interpolation": True,
                }
                result = _attach_metrics(
                    unable(str(values.get("record_id", "")), pack, "泵级数与设备类别冲突，无法唯一确定单级扬程和比转速"),
                    actual_metrics,
                    {"输出功率_kW": output_power},
                )
                return _attach_lookup_trace(result, pack, "表2", [lookup])
        ns, calculated = _specific_speed(values, True)
        # 多级泵的比转速按标准公式使用单级扬程；把实际采用的级数
        # 一并写入正常查表记录，避免报告只能看到除级数后的结果而无法复核。
        stage_number = decimal(stage_value)
        calculated["输出功率_kW"] = output_power
        kind = pump_kind
        ns_boundaries = chemical_rules.get("interval_boundaries", {}).get("specific_speed_ns", [])
        rule = next((row for row in chemical_rules["level_offsets"] if row["pump"] == kind
                     and _explicit_boundary_hit(q, row["q_min"], row["q_max"], q_boundaries)
                     and _explicit_boundary_hit(ns, row["ns_min"], row["ns_max"], ns_boundaries)), None)
        if rule is None:
            candidate_rows = [row for row in chemical_rules["level_offsets"] if row["pump"] == kind]
            lookup = {
                "step_type": "精确查表",
                "table": "表2",
                "data_ids": [str(row.get("data_id")) for row in candidate_rows if row.get("data_id") not in (None, "")],
                "matching": "泵级数类型+流量+比转速",
                "flow_value_m3h": str(q),
                "specific_speed": str(ns),
                "flow_ranges": [
                    {
                        "min": str(row["q_min"]),
                        "max": str(row["q_max"]),
                        "min_inclusive": (
                            _matching_boundary(q, row["q_min"], row["q_max"], q_boundaries)
                            or {}
                        ).get("min_inclusive", row.get("min_inclusive", True)),
                        "max_inclusive": (
                            _matching_boundary(q, row["q_min"], row["q_max"], q_boundaries)
                            or {}
                        ).get("max_inclusive", row.get("max_inclusive", True)),
                    }
                    for row in candidate_rows
                ],
                "specific_speed_ranges": [
                    {
                        "min": str(row["ns_min"]),
                        "max": str(row["ns_max"]),
                        "min_inclusive": (
                            _matching_boundary(ns, row["ns_min"], row["ns_max"], ns_boundaries)
                            or {}
                        ).get("min_inclusive", row.get("min_inclusive", True)),
                        "max_inclusive": (
                            _matching_boundary(ns, row["ns_min"], row["ns_max"], ns_boundaries)
                            or {}
                        ).get("max_inclusive", row.get("max_inclusive", True)),
                    }
                    for row in candidate_rows
                ],
                "match_status": "流量或比转速档位未命中",
                "source_clause": "表2/公式(4)~(7)",
                "source_pages": candidate_rows[0].get("source_pages", "") if candidate_rows else "",
            }
            result = _attach_metrics(out_of_scope(str(values.get("record_id", "")), pack, "流量或比转速超出石油化工离心泵适用范围"), actual_metrics, calculated)
            return _attach_lookup_trace(result, pack, "表2", [lookup])
        rule_index = next((index for index, item in enumerate(chemical_rules["level_offsets"], start=1) if item is rule), 1)
        ln_q = min(q, Decimal(3000)).ln()
        eta_coeff = [decimal(x) for x in pack["chemical"]["eta_b"][kind]]
        eta_b = sum(coef * ln_q ** (6 - idx) for idx, coef in enumerate(eta_coeff))
        delta_eta = Decimal(0)
        if rule["eta0_uses_delta"]:
            coeff_key = "ns_20_120" if ns < 120 else "ns_210_300"
            delta_coeff = [decimal(x) for x in pack["chemical"]["delta_eta"][coeff_key]]
            delta_eta = sum(coef * ns ** (6 - idx) for idx, coef in enumerate(delta_coeff))
        eta0 = eta_b - delta_eta
        thresholds = [eta0 + decimal(offset) for offset in rule["offsets"]]
        calculated["grade_thresholds_internal"] = [str(value) for value in thresholds]
        calculated.update({"基准效率_%": eta_b, "效率修正值_%": delta_eta, "规定点效率_%": eta0})
        q_boundary = _matching_boundary(q, rule["q_min"], rule["q_max"], q_boundaries)
        ns_boundary = _matching_boundary(ns, rule["ns_min"], rule["ns_max"], ns_boundaries)
        lookup = {
            "step_type": "公式计算",
            "rule": "GB 19762-2025公式(4)~(7)",
            "table": "表2",
            "source_clause": "表2/公式(4)~(7)",
            "matching": "泵级数类型+流量+比转速",
            "query_conditions": {
                "category": category,
                "pump_kind": kind,
                "flow_m3h": str(q),
                "head_m": str(_value(values, "head_m", "扬程")),
                "rated_speed_rpm": str(_value(values, "rated_speed_rpm", "额定转速")),
                "stages": str(stage_number),
                "suction": str(_value(values, "suction", "单双吸") or ""),
                "pump_efficiency": "" if actual is None else str(actual),
                "specific_speed": str(ns),
            },
            "match_status": "命中",
            # 化工泵表2规则行已带有校对后的稳定ID；旧/临时包才回退到行号。
            "data_id": rule.get("data_id") or f"GB19762-T2-R{rule_index:03d}",
            "stages": str(stage_number),
            "eta0_formula": "η0=ηb-Δη" if rule["eta0_uses_delta"] else "η0=ηb",
            "eta0_uses_delta": bool(rule["eta0_uses_delta"]),
            "offsets": [str(value) for value in rule["offsets"]],
            "parameters": {key: str(value) for key, value in calculated.items()},
            "grade_thresholds_internal": [str(value) for value in thresholds],
            "flow_boundary": q_boundary,
            "specific_speed_boundary": ns_boundary,
            "boundary_source": chemical_rules.get("interval_boundaries", {}).get("source_clause", ""),
            "source_pages": rule.get("source_pages", ""),
        }
        limits = {f"{i+1}级效率_%": rounded(thresholds[i]) for i in range(3)}
        if defer_efficiency_missing:
            result = _attach_metrics(
                unable(str(values.get("record_id", "")), pack, "缺少泵效率，无法进行能效等级比较", ["泵效率"]),
                actual_metrics,
                calculated,
            )
            result.limits = limits
            return _attach_lookup_trace(result, pack, "表2/公式(4)~(7)", [lookup])
        conclusion, comparisons = grade_three(actual, thresholds, ComparisonDirection.GREATER_OR_EQUAL)
        return _result(values, pack, conclusion, actual_metrics, calculated, limits, comparisons, "表2/公式(4)~(7)", [lookup], clause="表2/公式(4)~(7)")
