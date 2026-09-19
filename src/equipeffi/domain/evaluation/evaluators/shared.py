"""评价器共用输入校验、结果封装、区间及条件匹配辅助函数。"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from ...common.enums import ComparisonDirection, Conclusion
from ...common.models import EvaluationResult
from ..decimal_math import decimal


def _value(values: dict[str, Any], *names: str) -> Any:
    for name in names:
        if values.get(name) not in (None, ""):
            return values[name]
    return None


def _decimal_sequence(value: Any) -> list[Decimal]:
    """Parse a finite list of decimal inputs used by multi-stage equipment.

    API clients may send a JSON list; hand-entered integrations may send a
    comma/semicolon separated string.  Empty or non-numeric items are rejected
    instead of silently dropping a stage.
    """

    if isinstance(value, (list, tuple)):
        items = list(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("序列不能为空")
        items = re.split(r"[,，;；|、\s]+", text)
    else:
        raise ValueError("序列必须为列表或分隔文本")
    if not items or any(item in (None, "") for item in items):
        raise ValueError("序列包含空值")
    try:
        parsed = [decimal(item) for item in items]
    except (TypeError, ValueError) as exc:
        raise ValueError("序列包含非数值项") from exc
    if any(not item.is_finite() for item in parsed):
        raise ValueError("序列包含非有限数")
    return parsed


def _missing(values: dict[str, Any], fields: list[tuple[str, tuple[str, ...]]]) -> list[str]:
    return [display for display, aliases in fields if _value(values, *aliases) is None]


def _reference(pack: dict[str, Any], table: str = "", clause: str = "") -> dict[str, Any]:
    return {
        "standard_code": pack.get("standard_code", ""),
        "standard_name": pack.get("standard_name", ""),
        "table": table,
        "clause": clause,
        "pack_id": pack.get("pack_id", ""),
        "data_version": pack.get("data_version", ""),
        "status": pack.get("status", ""),
        "effective_date": pack.get("effective_date", ""),
    }


def unable(record_id: str, pack: dict[str, Any], reason: str, missing: list[str] | None = None) -> EvaluationResult:
    return EvaluationResult(
        record_id=record_id,
        conclusion=Conclusion.UNABLE_TO_JUDGE,
        missing_fields=missing or [],
        standard_reference=_reference(pack),
        explanation=reason,
        notes=[reason],
        trace=[{"step_type": "终止", "output": Conclusion.UNABLE_TO_JUDGE.value, "reason": reason}],
    )


def out_of_scope(record_id: str, pack: dict[str, Any], reason: str) -> EvaluationResult:
    return EvaluationResult(
        record_id=record_id,
        conclusion=Conclusion.OUT_OF_SCOPE,
        standard_reference=_reference(pack),
        explanation=reason,
        trace=[{"step_type": "范围检查", "output": Conclusion.OUT_OF_SCOPE.value, "reason": reason}],
    )


def _active_or_unable(values: dict[str, Any], pack: dict[str, Any]) -> EvaluationResult | None:
    if pack.get("status") != "active":
        reason = pack.get("unavailable_reason") or f"标准数据状态为{pack.get('status', 'unknown')}，尚未激活"
        return unable(str(values.get("record_id", "")), pack, reason)
    return None


def _positive_or_unable(values: dict[str, Any], pack: dict[str, Any], fields: list[tuple[str, tuple[str, ...]]]) -> EvaluationResult | None:
    invalid: list[str] = []
    non_numeric: list[str] = []
    for display, aliases in fields:
        value = _value(values, *aliases)
        if value is None:
            continue
        try:
            if decimal(value) <= 0:
                invalid.append(display)
        except ValueError:
            non_numeric.append(display)
    if non_numeric:
        return unable(str(values.get("record_id", "")), pack, f"以下参数不是有效数值：{'、'.join(non_numeric)}", non_numeric)
    if invalid:
        return unable(str(values.get("record_id", "")), pack, f"以下参数必须为正数：{'、'.join(invalid)}", invalid)
    return None


def _positive_integer_or_unable(
    values: dict[str, Any], pack: dict[str, Any], fields: list[tuple[str, tuple[str, ...]]]
) -> EvaluationResult | None:
    """Validate optional count fields which are used as discrete standard axes.

    A stage count is not a continuous engineering value: allowing ``1.5`` to
    reach the specific-speed calculation would silently create a fictitious
    single-stage head.  Keep this guard in the evaluator as well as in the V4
    workbook validation so API/manual input follows the same contract.
    """
    invalid: list[str] = []
    non_numeric: list[str] = []
    non_integer: list[str] = []
    for display, aliases in fields:
        value = _value(values, *aliases)
        if value is None:
            continue
        try:
            number = decimal(value)
        except ValueError:
            non_numeric.append(display)
            continue
        if number <= 0:
            invalid.append(display)
        elif number != number.to_integral_value():
            non_integer.append(display)
    if non_numeric:
        return unable(str(values.get("record_id", "")), pack, f"以下参数不是有效数值：{'、'.join(non_numeric)}", non_numeric)
    if invalid:
        return unable(str(values.get("record_id", "")), pack, f"以下参数必须为正数：{'、'.join(invalid)}", invalid)
    if non_integer:
        return unable(str(values.get("record_id", "")), pack, f"以下参数必须为正整数：{'、'.join(non_integer)}", non_integer)
    return None


def _percent_or_unable(values: dict[str, Any], pack: dict[str, Any], display: str, aliases: tuple[str, ...], maximum: int = 100) -> EvaluationResult | None:
    value = _value(values, *aliases)
    if value is None:
        return None
    try:
        number = decimal(value)
    except ValueError:
        return unable(str(values.get("record_id", "")), pack, f"{display}不是有效数值", [display])
    if not Decimal(1) <= number <= Decimal(maximum):
        return unable(str(values.get("record_id", "")), pack, f"{display}应按百分数本值填写且位于1~{maximum}", [display])
    return None


def _range_or_unable(
    values: dict[str, Any],
    pack: dict[str, Any],
    display: str,
    aliases: tuple[str, ...],
    minimum: Decimal,
    maximum: Decimal,
    *,
    minimum_inclusive: bool = True,
    maximum_inclusive: bool = True,
) -> EvaluationResult | None:
    """Reject a supplied physical parameter outside its standard input domain.

    This is deliberately limited to domains explicitly represented by the V4
    contract/standard (rather than guessing engineering plausibility).  The
    validation layer reports the same issue for workbooks; keeping the guard in
    the evaluator makes manual/API requests follow the same safety boundary.
    """
    value = _value(values, *aliases)
    if value is None:
        return None
    try:
        number = decimal(value)
    except ValueError:
        return unable(str(values.get("record_id", "")), pack, f"{display}不是有效数值", [display])
    lower_ok = number >= minimum if minimum_inclusive else number > minimum
    upper_ok = number <= maximum if maximum_inclusive else number < maximum
    if not (lower_ok and upper_ok):
        left = "[" if minimum_inclusive else "("
        right = "]" if maximum_inclusive else ")"
        return out_of_scope(str(values.get("record_id", "")), pack, f"{display}应位于{left}{minimum}，{maximum}{right}范围内")
    return None


def _result(
    values: dict[str, Any],
    pack: dict[str, Any],
    conclusion: Conclusion,
    actual: dict[str, Any],
    calculated: dict[str, Any],
    limits: dict[str, Any],
    comparisons: list[dict[str, Any]],
    table: str,
    lookups: list[dict[str, Any]] | None = None,
    clause: str = "",
) -> EvaluationResult:
    # 将查表/计算后得到的标准阈值也写入公共轨迹。部分评价器的等级比较
    # 只记录了通过与否（例如变压器的空载损耗 AND 负载损耗），若不单独
    # 保存阈值，API/JSONL/Excel轨迹就无法复核“比较所用的标准数据”。
    trace_steps = list(lookups or [])
    # 即使标准行全部为“—”而没有可展示的数值阈值，只要发生了查表/计算，
    # 也必须生成公共“标准查询结果”步骤，供窗口、JSONL和移动端追溯表号及
    # data_id；不能因limits为空而丢失标准来源。
    if limits or trace_steps:
        # 将本次查表/计算链中出现的稳定数据ID汇总到“标准查询结果”步骤，
        # 便于Excel、JSONL和移动端在不解析各设备专属字段的情况下回溯
        # 实际使用的标准记录。嵌套查表（如潜水泵表4）也一并收集。
        data_ids: list[str] = []

        def collect_ids(value: Any) -> None:
            if isinstance(value, dict):
                candidate = value.get("data_id")
                if candidate not in (None, "") and str(candidate) not in data_ids:
                    data_ids.append(str(candidate))
                nested_ids = value.get("data_ids")
                if isinstance(nested_ids, list):
                    for nested_id in nested_ids:
                        if nested_id not in (None, "") and str(nested_id) not in data_ids:
                            data_ids.append(str(nested_id))
                for child in value.values():
                    collect_ids(child)
            elif isinstance(value, list):
                for child in value:
                    collect_ids(child)

        collect_ids(trace_steps)
        standard_result = {
            "step_type": "标准查询结果",
            "table": table,
            "output": dict(limits),
            "clause": clause,
        }
        if data_ids:
            standard_result["data_ids"] = data_ids
        trace_steps.append({
            **standard_result,
        })
    return EvaluationResult(
        record_id=str(values.get("record_id", "")),
        conclusion=conclusion,
        actual_metrics=actual,
        calculated_metrics=calculated,
        limits=limits,
        comparisons=comparisons,
        lookups=lookups or [],
        trace=trace_steps + [{"step_type": "等级比较", **item} for item in comparisons],
        standard_reference=_reference(pack, table, clause),
        explanation=f"按{pack.get('standard_code', '')}{table}的设计/标称指标判定为{conclusion.value}",
    )


def _attach_lookup_trace(
    result: EvaluationResult,
    pack: dict[str, Any],
    table: str,
    lookups: list[dict[str, Any]],
) -> EvaluationResult:
    """为提前终止的查表结果补齐公共追溯步骤。

    某些标准行全部为“—”或插值端点不可用时，评价器必须返回“无法判定”，
    但不能因此丢失已经完成的查表记录。这个辅助函数让这些终止分支和正常
    ``_result``路径都输出同样的“标准查询结果”步骤，跨端消费者无需解析
    设备专属的``lookups``字段才能取得数据ID。
    """
    normalized = list(lookups)
    data_ids: list[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            candidate = value.get("data_id")
            if candidate not in (None, "") and str(candidate) not in data_ids:
                data_ids.append(str(candidate))
            nested_ids = value.get("data_ids")
            if isinstance(nested_ids, list):
                for nested_id in nested_ids:
                    if nested_id not in (None, "") and str(nested_id) not in data_ids:
                        data_ids.append(str(nested_id))
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(normalized)
    clause = ""
    if result.standard_reference:
        clause = str(result.standard_reference.get("clause", "") or "")

    def find_clause(value: Any) -> str:
        if isinstance(value, dict):
            for key in ("source_clause", "clause", "standard_clause"):
                candidate = value.get(key)
                if candidate not in (None, ""):
                    return str(candidate)
            for child in value.values():
                found = find_clause(child)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = find_clause(child)
                if found:
                    return found
        return ""

    if not clause:
        clause = find_clause(normalized)
    query_step: dict[str, Any] = {
        "step_type": "标准查询结果",
        "table": table,
        "output": dict(result.limits),
        "clause": clause,
    }
    if data_ids:
        query_step["data_ids"] = data_ids
    result.lookups = normalized
    result.trace = normalized + [query_step] + result.trace
    result.standard_reference = _reference(pack, table, query_step["clause"])
    return result


def _attach_metrics(
    result: EvaluationResult,
    actual: dict[str, Any] | None = None,
    calculated: dict[str, Any] | None = None,
) -> EvaluationResult:
    """Keep values already evaluated when a later range/table gate stops.

    A range miss is still a useful result: the caller should be able to see
    the submitted metric and any deterministic intermediate calculation.  A
    number of evaluators intentionally return early on an out-of-scope table
    lookup, so centralizing the merge avoids silently discarding that context.
    """
    if actual:
        result.actual_metrics.update(actual)
    if calculated:
        result.calculated_metrics.update(calculated)
    return result



def _interval_hit(value: Any, expression: str) -> bool:
    try:
        number = decimal(value)
    except ValueError:
        # 条件字段可能来自批量粘贴；非法文本应作为“不命中”交给上层
        # 结构化返回无法判定/不在范围，而不能让整个批处理抛异常。
        return False
    text = str(expression).replace(" ", "").replace("～", "~")
    # 标准区间常带No、机号、ψ、ns、γ等变量名；去掉变量名后统一按数值和比较符解析。
    text = re.sub(r"[A-Za-z\u4e00-\u9fff]+", "", text)
    number_pattern = r"-?\d+(?:\.\d+)?"
    nums = [decimal(item) for item in re.findall(number_pattern, text)]
    if not nums:
        return False
    if "~" in text and len(nums) >= 2:
        # 标准中既有“700~1000”，也有“>700~1000”。
        # 波浪号两侧的比较符属于对应端点，不能一律按闭区间处理。
        left_text, right_text = text.split("~", 1)
        left_match = re.search(rf"(?P<op><=|>=|≤|≥|<|>)?({number_pattern})\s*$", left_text)
        right_match = re.search(rf"^(?P<op><=|>=|≤|≥|<|>)?({number_pattern})", right_text)
        if left_match and right_match:
            low = decimal(left_match.group(2))
            high = decimal(right_match.group(2))
            low_op = left_match.group("op") or "≥"
            high_op = right_match.group("op") or "≤"
            lower_ok = number > low if low_op == ">" else number >= low if low_op in {"≥", ">="} else number < low if low_op == "<" else number <= low if low_op in {"≤", "<="} else number >= low
            upper_ok = number < high if high_op == "<" else number <= high if high_op in {"≤", "<="} else number > high if high_op == ">" else number >= high if high_op in {"≥", ">="} else number <= high
            return lower_ok and upper_ok
        return nums[0] <= number <= nums[-1]
    chain = re.fullmatch(
        rf"({number_pattern})(<=|≥|>=|≤|<|>)(.*?)(<=|≥|>=|≤|<|>)({number_pattern})",
        text,
    )
    if chain:
        low, left_op, _, right_op, high = chain.groups()
        low_d, high_d = decimal(low), decimal(high)
        if left_op in ("<", "≤", "<="):
            lower_ok = number > low_d if left_op == "<" else number >= low_d
        else:
            lower_ok = number < low_d if left_op == ">" else number <= low_d
        if right_op in ("<", "≤", "<="):
            upper_ok = number < high_d if right_op == "<" else number <= high_d
        else:
            upper_ok = number > high_d if right_op == ">" else number >= high_d
        return lower_ok and upper_ok
    if len(nums) == 1:
        target = nums[0]
        before = re.fullmatch(rf".*?(<=|≥|>=|≤|<|>)({number_pattern})", text)
        if before:
            op = before.group(1)
            return {"<": number < target, "≤": number <= target, "<=": number <= target, ">": number > target, "≥": number >= target, ">=": number >= target}[op]
        after = re.fullmatch(rf"({number_pattern})(<=|≥|>=|≤|<|>).*", text)
        if after:
            op = after.group(2)
            return {"<": number > target, "≤": number >= target, "<=": number >= target, ">": number < target, "≥": number <= target, ">=": number <= target}[op]
        return number == target
    return False


def _matching_boundary(value: Any, minimum: Any, maximum: Any, boundaries: list[dict[str, Any]]) -> dict[str, Any] | None:
    """返回与标准行端点对应的显式开闭区间。

    ``None``/空字符串的上限表示标准原文的无上限区间，不应被
    当成数值或人为哨兵值。``value``保留在接口中以兼容既有调用方。
    """
    try:
        minimum_d = decimal(minimum)
        maximum_d = None if maximum in (None, "") else decimal(maximum)
    except (TypeError, ValueError):
        return None
    for boundary in boundaries:
        try:
            boundary_max = boundary.get("max")
            boundary_max_d = None if boundary_max in (None, "") else decimal(boundary_max)
            if decimal(boundary["min"]) == minimum_d and boundary_max_d == maximum_d:
                return dict(boundary)
        except (KeyError, TypeError, ValueError):
            continue
    return None


def _explicit_boundary_hit(value: Any, minimum: Any, maximum: Any, boundaries: list[dict[str, Any]]) -> bool:
    """按标准原文的开闭端点匹配；支持标准明确的无上限区间。"""
    try:
        number = decimal(value)
        minimum_d = decimal(minimum)
        maximum_d = None if maximum in (None, "") else decimal(maximum)
    except (TypeError, ValueError):
        return False
    boundary = _matching_boundary(number, minimum_d, maximum_d, boundaries)
    if boundary is None:
        return minimum_d <= number if maximum_d is None else minimum_d <= number <= maximum_d
    lower_ok = number >= minimum_d if boundary.get("min_inclusive", True) else number > minimum_d
    if maximum_d is None or boundary.get("max") in (None, ""):
        upper_ok = True
    else:
        upper_ok = number <= maximum_d if boundary.get("max_inclusive", True) else number < maximum_d
    return lower_ok and upper_ok


def _condition_hit(value: Any, expression: str, variable: str) -> bool:
    text = expression.replace(" ", "")
    # 锅炉标准把燃料热值写成“按实际化验值”；本工具所有输入均为
    # 出厂设计/铭牌值，因此机器包同步使用“按设计燃料化验值”时，
    # 两者都表示该条件不是固定数值档，不应强制套用区间解析。
    if not text or any(token in text for token in ("实际", "设计", "化验值")):
        return True
    return _interval_hit(value, text.replace(variable, ""))


def _condition_text(value: Any) -> str:
    """Normalize harmless presentation differences in standard conditions.

    V4 validation displays standard IDs with spaces (``GB/T 19409``), while
    older extracted tables often omit them.  Spaces and full-width brackets
    are presentation-only; punctuation and the actual enum words remain
    significant.  This helper is intentionally not used for numeric values.
    """

    return (
        str(value)
        .replace("\u3000", "")
        .replace(" ", "")
        .replace("（", "(")
        .replace("）", ")")
    )


def _condition_matches(key: str, actual: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        return any(_condition_matches(key, actual, item) for item in expected)
    if key in {"product_standard", "source", "unit_type", "category", "evaluation_system"}:
        return _condition_text(actual) == _condition_text(expected)
    return str(actual) == str(expected)


def _record_matches(record: dict[str, Any], values: dict[str, Any]) -> bool:
    for key, expected in record.get("conditions", {}).items():
        actual = _value(values, key, record.get("condition_aliases", {}).get(key, key))
        if not _condition_matches(key, actual, expected):
            return False
    metric = record.get("range_metric")
    if metric:
        actual = _value(values, metric)
        if actual is None:
            return False
        try:
            number = decimal(actual)
        except ValueError:
            return False
        if record.get("min") is not None and (number < decimal(record["min"]) or (not record.get("min_inclusive", True) and number == decimal(record["min"]))):
            return False
        if record.get("max") is not None and (number > decimal(record["max"]) or (not record.get("max_inclusive", True) and number == decimal(record["max"]))):
            return False
    return True
