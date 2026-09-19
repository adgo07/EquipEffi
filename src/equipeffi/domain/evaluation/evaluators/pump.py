"""GB 19762-2025清水和石油化工离心泵评价器。"""
from __future__ import annotations

from decimal import Decimal
from typing import Any


def _specific_speed(values: dict[str, Any], chemical: bool = False) -> tuple[Decimal, dict[str, Any]]:
    """Calculate the standard specific-speed inputs for a centrifugal pump."""

    from ..device_evaluators import _value
    from ..decimal_math import decimal

    q_h = decimal(_value(values, "flow_m3h", "流量"))
    n = decimal(_value(values, "rated_speed_rpm", "额定转速"))
    h = decimal(_value(values, "head_m", "扬程"))
    stages = decimal(_value(values, "stages", "级数") or 1)
    category = str(_value(values, "category", "设备类别") or "")
    suction = str(_value(values, "suction", "单双吸") or "")
    q_effective = q_h / 2 if "双吸" in category or suction == "双吸" else q_h
    h_effective = h / stages if "多级" in category else h
    q_s = q_effective / Decimal(3600)
    denominator = (h_effective.ln() * Decimal("0.75")).exp()
    ns = Decimal("3.65") * n * q_s.sqrt() / denominator
    return ns, {"计算流量_m3/h": q_effective, "单级扬程_m": h_effective, "比转速": ns}


class WaterPumpEvaluator:
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
        category = str(_value(values, "category", "设备类别"))
        suction = str(_value(values, "suction", "单双吸") or "").strip()
        q = decimal(_value(values, "flow_m3h", "流量"))
        actual = None if defer_efficiency_missing else decimal(_value(values, "pump_efficiency", "泵效率"))
        actual_metrics = {} if actual is None else {"泵效率_%": actual}
        output_power = Decimal("9.81") * q / Decimal(3600) * decimal(_value(values, "head_m", "扬程"))
        # GB 19762-2025表3只覆盖标准列出的清水泵型。公共枚举中的
        # “其他（请备注说明）”不能被默认解释为单级单吸；否则会在
        # 类别尚未确定时使用默认级数/单双吸计算出虚假的比转速。
        water_rows = list(pack["water"].get("ci", []))
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
        # V4同时保留完整设备类别和“单双吸”字段。类别已经明确为单吸/双吸时，
        # 两者若冲突，不能用单双吸字段静默把流量折半后继续套用另一类标准表；
        # 这会产生无法追溯的错误比转速和能效等级。
        category_suction = "双吸" if "双吸" in category else "单吸" if "单吸" in category else ""
        if category_suction and suction and category_suction != suction:
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
        calculated.update({f"C{i+1}": ci_row["ci"][i] for i in range(3)})
        lookup = {
            "step_type": "公式计算",
            "rule": "GB 19762-2025公式(1)~(3)",
            "data_id": ci_row.get("data_id", ""),
            "parameters": {key: str(value) for key, value in calculated.items()},
            "table": "表3",
            "matching": "泵型+流量",
            "query_conditions": {
                "category": category,
                "flow_m3h": str(q),
                "head_m": str(_value(values, "head_m", "扬程")),
                "rated_speed_rpm": str(_value(values, "rated_speed_rpm", "额定转速")),
                "stages": str(_value(values, "stages", "级数") or "1"),
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
        chemical_rules = pack["chemical"]
        q_boundaries = chemical_rules.get("interval_boundaries", {}).get("flow_q", [])
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
        stage_number = decimal(stage_value) if stage_value is not None else Decimal(1)
        calculated["输出功率_kW"] = output_power
        kind = pump_kind or ("多级" if "多级" in category else "单级")
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
