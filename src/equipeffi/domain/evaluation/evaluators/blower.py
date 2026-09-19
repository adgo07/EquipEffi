"""GB 28381-2012鼓风机评价器。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ...common.enums import Conclusion
from ...common.models import EvaluationResult


class BlowerEvaluator:
    def evaluate(self, values: dict[str, Any], pack: dict[str, Any]) -> EvaluationResult:
        from ..device_evaluators import (
            _active_or_unable,
            _attach_lookup_trace,
            _attach_metrics,
            _decimal_sequence,
            _interval_hit,
            _missing,
            _positive_or_unable,
            _range_or_unable,
            _result,
            _value,
            out_of_scope,
            unable,
        )
        from ..decimal_math import decimal

        if result := _active_or_unable(values, pack):
            return result
        missing = _missing(values, [
            ("设备类别", ("category", "设备类别")),
            ("叶轮出口宽度", ("impeller_width_mm", "叶轮出口宽度")),
            ("叶轮出口直径", ("impeller_diameter_mm", "叶轮出口直径")),
        ])
        if missing:
            return unable(str(values.get("record_id", "")), pack, "缺少鼓风机判定参数", missing)
        if result := _positive_or_unable(values, pack, [
            ("叶轮出口宽度", ("impeller_width_mm", "叶轮出口宽度")),
            ("叶轮出口直径", ("impeller_diameter_mm", "叶轮出口直径")),
        ]):
            return result
        if result := _range_or_unable(values, pack, "绝热指数k", ("isentropic_k", "k", "绝热指数k"), Decimal(1), Decimal(2)):
            return result
        category = str(_value(values, "category", "设备类别"))
        ratio = decimal(_value(values, "impeller_width_mm", "叶轮出口宽度")) / decimal(_value(values, "impeller_diameter_mm", "叶轮出口直径"))
        diameter = decimal(_value(values, "impeller_diameter_mm", "叶轮出口直径"))
        calculated: dict[str, Any] = {"b2/D2": ratio}
        refs: list[dict[str, Any]] = []
        reported_efficiency = _value(values, "polytropic_efficiency", "多变效率")
        stage_efficiency_input = _value(values, "stage_efficiencies", "各级多变效率")
        # GB 28381-2012规定多变效率应由进、出口绝对压力和绝对温度计算：
        # ηp=((k-1)/k×ln(p2/p1))/ln(T2/T1)。V4字段温度单位为K、压力单位为kPa。
        raw_efficiency_fields = [
            ("进口绝对压力", ("inlet_absolute_pressure_kpa", "p1", "进口绝对压力")),
            ("出口绝对压力", ("outlet_absolute_pressure_kpa", "p2", "出口绝对压力")),
            ("进口温度", ("inlet_temperature_k", "t1", "进口温度")),
            ("出口温度", ("outlet_temperature_k", "t2", "出口温度")),
            ("绝热指数k", ("isentropic_k", "k", "绝热指数k")),
        ]
        raw_missing = _missing(values, raw_efficiency_fields)
        actual_efficiency = None
        defer_efficiency_missing = False
        efficiency_missing_fields: list[str] = []
        known_raw_inputs: dict[str, Any] = {}
        for label, aliases, output_key in (
            ("进口绝对压力", raw_efficiency_fields[0][1], "进口绝对压力_kPa"),
            ("出口绝对压力", raw_efficiency_fields[1][1], "出口绝对压力_kPa"),
            ("进口温度", raw_efficiency_fields[2][1], "进口温度_K"),
            ("出口温度", raw_efficiency_fields[3][1], "出口温度_K"),
            ("绝热指数k", raw_efficiency_fields[4][1], "绝热指数k"),
        ):
            raw_value = _value(values, *aliases)
            if raw_value is not None:
                try:
                    known_raw_inputs[output_key] = decimal(raw_value)
                except ValueError:
                    # 仍由后续效率/范围校验报告原始非法值；不猜测或替换输入。
                    known_raw_inputs[output_key] = raw_value
        if stage_efficiency_input is not None:
            # GB 28381-2012规定多级鼓风机按各级多变效率平均值判定。
            # 逐级输入是可选扩展；一旦提供就必须完整覆盖级数，禁止用
            # 单个值或缺项替代平均值。
            stage = _value(values, "stages", "级数")
            if stage is None:
                return unable(str(values.get("record_id", "")), pack, "提供各级多变效率时必须填写级数", ["级数"])
            try:
                stage_count_decimal = decimal(stage)
                if stage_count_decimal <= 0 or stage_count_decimal != stage_count_decimal.to_integral_value():
                    raise ValueError("级数必须为正整数")
                stage_count = int(stage_count_decimal)
                stage_efficiencies = _decimal_sequence(stage_efficiency_input)
            except (TypeError, ValueError) as exc:
                return unable(str(values.get("record_id", "")), pack, f"各级多变效率或级数无效：{exc}", ["各级多变效率", "级数"])
            if stage_count != len(stage_efficiencies):
                return unable(str(values.get("record_id", "")), pack, f"各级多变效率数量{len(stage_efficiencies)}与级数{stage_count}不一致", ["各级多变效率"])
            if any(not Decimal(1) <= item <= Decimal(100) for item in stage_efficiencies):
                return unable(str(values.get("record_id", "")), pack, "各级多变效率应按百分数本值填写且位于1~100", ["各级多变效率"])
            actual_efficiency = sum(stage_efficiencies, Decimal(0)) / Decimal(stage_count)
            calculated.update({
                "各级多变效率_%": stage_efficiencies,
                "各级多变效率平均值_%": actual_efficiency,
                "级数": stage_count,
            })
            refs.append({
                "step_type": "公式计算",
                "formula": "ηp,avg=Σηp,i/n",
                "inputs": {"stage_efficiencies_%": [str(item) for item in stage_efficiencies], "stages": stage_count},
                "value": str(actual_efficiency),
                "source_clause": "5.3、5.4（多级各级平均值）",
                "source_page": "4-5",
            })
        elif not raw_missing:
            try:
                p1 = decimal(_value(values, *raw_efficiency_fields[0][1]))
                p2 = decimal(_value(values, *raw_efficiency_fields[1][1]))
                t1 = decimal(_value(values, *raw_efficiency_fields[2][1]))
                t2 = decimal(_value(values, *raw_efficiency_fields[3][1]))
                k = decimal(_value(values, *raw_efficiency_fields[4][1]))
                if min(p1, p2, t1, t2) <= 0 or p2 <= p1 or t2 <= t1 or k <= 1:
                    raise ValueError("压力、温度必须为正且出口值应高于进口值，绝热指数k必须大于1")
                actual_efficiency = ((k - 1) / k * (p2 / p1).ln() / (t2 / t1).ln()) * Decimal(100)
                calculated.update({
                    "多变效率计算值_%": actual_efficiency,
                    "进口绝对压力_kPa": p1,
                    "出口绝对压力_kPa": p2,
                    "进口温度_K": t1,
                    "出口温度_K": t2,
                    "绝热指数k": k,
                })
                refs.append({
                    "step_type": "公式计算",
                    "formula": "ηp=((k-1)/k×ln(p2/p1))/ln(T2/T1)×100",
                    "inputs": {"p1_kPa": str(p1), "p2_kPa": str(p2), "T1_K": str(t1), "T2_K": str(t2), "k": str(k)},
                    "value": str(actual_efficiency),
                    "source_clause": "5.2式(1)",
                    "source_page": "3-4",
                })
            except (ValueError, ArithmeticError) as exc:
                return unable(str(values.get("record_id", "")), pack, f"多变效率计算失败：{exc}")
        elif reported_efficiency is not None:
            try:
                actual_efficiency = decimal(reported_efficiency)
            except ValueError:
                return unable(str(values.get("record_id", "")), pack, "多变效率不是有效数值", ["多变效率"])
        else:
            # 几何参数仍可唯一确定标准表行；不能因压力/温度缺失而丢失
            # b₂/D₂、标准阈值和查询来源。最终比较延后到查表完成后。
            defer_efficiency_missing = True
            efficiency_missing_fields = list(dict.fromkeys(["多变效率", *raw_missing]))
            calculated.update(known_raw_inputs)
        if actual_efficiency is None and not defer_efficiency_missing:
            return unable(str(values.get("record_id", "")), pack, "缺少多变效率，且缺少用于计算的进口/出口压力、温度或绝热指数", raw_missing)
        if actual_efficiency is not None and not Decimal(1) <= actual_efficiency <= Decimal(100):
            return unable(str(values.get("record_id", "")), pack, "多变效率应按百分数本值填写且位于1~100", ["多变效率"])
        actual = actual_efficiency
        deferred_actual_metrics: dict[str, Any] = {} if defer_efficiency_missing else {"多变效率_%": actual}
        thresholds: dict[str, Any] = {}
        normalized_category = category.replace("离心", "").replace("鼓风机", "")
        is_three_dimensional = str(_value(values, "three_dimensional", "是否三元流动叶轮") or "").strip() in {"是", "是的", "true", "1"}
        is_cantilever = str(_value(values, "cantilever", "是否悬臂式") or "").strip() in {"是", "是的", "true", "1"}
        # GB 28381-2012第5.3.2、5.4.2：三元流动叶轮表值提高5%；
        # 悬臂式单级双支撑机型在对应表值上增加1个百分点。这里保留
        # 未修正原表值，并将修正值写入标准结果和判定轨迹。
        table_adjustment = Decimal(0)
        if is_three_dimensional:
            table_adjustment += Decimal(5)
        if is_cantilever and normalized_category in {"单级双支撑低速", "单级双支撑高速"}:
            table_adjustment += Decimal(1)
        if table_adjustment:
            calculated["结构修正_百分点"] = table_adjustment
        no_data_refs: list[dict[str, Any]] = []
        stage = _value(values, "stages", "级数")
        query_conditions = {
            "category": category,
            "impeller_width_mm": str(decimal(_value(values, "impeller_width_mm", "叶轮出口宽度"))),
            "impeller_diameter_mm": str(diameter),
            "b2_d2": str(ratio),
            "stages": "" if stage is None else str(stage),
        }
        matching = "型式+D₂档位+b₂/D₂档位+级数（多级时）"
        if normalized_category.startswith("多级") and stage is None:
            # 多级表同时按限定值和节能评价值列出2~3级、4~6级等行。
            # 缺少级数时不能默认取第一档，也不能让第一张表的早退
            # 掩盖另一类标准结果；保留两张表的全部候选记录供复核。
            missing_stage_refs: list[dict[str, Any]] = []
            for kind in ("限定值", "节能评价值"):
                table = next((item for item in pack.get("tables", []) if item.get("type") == normalized_category and item.get("kind") == kind), None)
                if table is None:
                    continue
                rows = list(table.get("rows", []))
                source_clause = "5.3.2" if kind == "限定值" else "5.4.2"
                missing_stage_refs.append({
                    "step_type": "精确查表",
                    "table": table.get("name", ""),
                    "kind": kind,
                    "data_ids": [
                        str(item.get("data_id"))
                        for item in rows
                        if item.get("data_id") not in (None, "")
                    ],
                    "b2/D2": str(ratio),
                    "D2_mm": str(diameter),
                    "D2_ranges": list(table.get("d2_ranges", [])),
                    "stage_ranges": sorted({str(item.get("stages", "")) for item in rows if item.get("stages")}),
                    "candidate_count": len(rows),
                    "match_status": "级数未提供",
                    "matching": matching,
                    "query_conditions": dict(query_conditions),
                    "source_clause": source_clause,
                    "source_page": table.get("source_page", ""),
                    "no_interpolation": True,
                })
            result = _attach_metrics(
                unable(str(values.get("record_id", "")), pack, "多级鼓风机缺少级数，无法唯一确定标准行", ["级数"]),
                deferred_actual_metrics,
                calculated,
            )
            if missing_stage_refs:
                return _attach_lookup_trace(result, pack, "/".join(item.get("table", "") for item in missing_stage_refs), refs + missing_stage_refs)
            return result
        for kind in ("限定值", "节能评价值"):
            table = next((item for item in pack.get("tables", []) if item.get("type") == normalized_category and item.get("kind") == kind), None)
            if table is None:
                continue
            d_idx = next((idx for idx, expr in enumerate(table["d2_ranges"]) if _interval_hit(diameter, expr)), None)
            if normalized_category.startswith("多级"):
                row_pool = [item for item in table["rows"] if item.get("stages") and _interval_hit(stage, item.get("stages", ""))]
            else:
                # 单级表只使用无级数行；粗校对数据中偶尔混入多级行，不能静默复用。
                row_pool = [item for item in table["rows"] if not item.get("stages")]
            source_clause = "5.3.2" if kind == "限定值" else "5.4.2"
            if d_idx is None:
                # 尺寸档未命中时也要保留查表证据，但不能把任一相邻档
                # 当作阈值、最近档或可外推档。候选行的稳定ID只表示
                # 本次查询实际检查过的标准记录，不表示命中。
                candidate_ids = [
                    str(item.get("data_id"))
                    for item in row_pool
                    if item.get("data_id") not in (None, "")
                ]
                refs.append({
                    "step_type": "精确查表",
                    "table": table["name"],
                    "kind": kind,
                    "data_ids": candidate_ids,
                    "b2/D2": str(ratio),
                    "D2_mm": str(diameter),
                    "D2_ranges": list(table.get("d2_ranges", [])),
                    "match_status": "D₂档位未命中",
                    "matching": matching,
                    "query_conditions": dict(query_conditions),
                    "source_clause": source_clause,
                    "source_page": table.get("source_page", ""),
                })
                continue
            row = next((item for item in row_pool if _interval_hit(ratio, item.get("b2_d2", ""))), None)
            if row is None:
                candidate_ids = [
                    str(item.get("data_id"))
                    for item in row_pool
                    if item.get("data_id") not in (None, "")
                ]
                refs.append({
                    "step_type": "精确查表",
                    "table": table["name"],
                    "kind": kind,
                    "data_ids": candidate_ids,
                    "b2/D2": str(ratio),
                    "D2_mm": str(diameter),
                    "D2_range": table["d2_ranges"][d_idx],
                    "b2_D2_ranges": [item.get("b2_d2", "") for item in row_pool],
                    "match_status": "b₂/D₂档位未命中",
                    "matching": matching,
                    "query_conditions": dict(query_conditions),
                    "source_clause": source_clause,
                    "source_page": table.get("source_page", ""),
                })
                continue
            row_index = next((index for index, item in enumerate(table.get("rows", []), start=1) if item is row), 1)
            if d_idx >= len(row.get("eff", [])) or row["eff"][d_idx] is None:
                no_data_ref = {
                    "step_type": "精确查表",
                    "table": table["name"],
                    "kind": kind,
                    # 标准包行已有稳定ID；旧/临时包才按表行和尺寸档回退。
                    "data_id": row.get("data_id") or f"GB28381-{kind}-T{table.get('type', normalized_category)}-R{row_index:03d}-D{d_idx + 1:02d}",
                    "b2/D2": str(ratio),
                    "D2_mm": str(diameter),
                    "standard_marker": "—",
                    "no_data": True,
                    "dash_semantics": "—表示该档不作要求，不等同于零或普通空值",
                    "matching": matching,
                    "match_status": "命中",
                    "source_clause": source_clause,
                    "source_page": table.get("source_page", ""),
                    "query_conditions": dict(query_conditions),
                }
                no_data_refs.append(no_data_ref)
                refs.append(no_data_ref)
                continue
            raw_threshold = decimal(row["eff"][d_idx])
            thresholds[kind] = raw_threshold + table_adjustment
            refs.append({
                "step_type": "精确查表",
                "table": table["name"],
                "kind": kind,
                "data_id": row.get("data_id") or f"GB28381-{kind}-T{table.get('type', normalized_category)}-R{row_index:03d}-D{d_idx + 1:02d}",
                "b2/D2": str(ratio),
                "D2_mm": str(diameter),
                    "raw_threshold": str(raw_threshold),
                    "structure_adjustment_percentage_points": str(table_adjustment),
                    "matching": matching,
                    "match_status": "命中",
                    "source_clause": source_clause,
                    "source_page": table.get("source_page", ""),
                    "query_conditions": dict(query_conditions),
            })
        if "限定值" not in thresholds:
            if no_data_refs:
                result = unable(str(values.get("record_id", "")), pack, "命中的鼓风机标准档位包含‘—’或无数据，无法判定")
                result.actual_metrics = dict(deferred_actual_metrics)
                result.calculated_metrics.update(calculated)
                return _attach_lookup_trace(result, pack, "/".join(item.get("table", "") for item in no_data_refs), refs)
            result = _attach_metrics(out_of_scope(str(values.get("record_id", "")), pack, "鼓风机尺寸比或直径超出表格范围"), deferred_actual_metrics, calculated)
            if refs:
                return _attach_lookup_trace(result, pack, "/".join(item.get("table", "") for item in refs), refs)
            return result
        if defer_efficiency_missing:
            table_reference = "/".join(item.get("table", "") for item in refs)
            result = unable(
                str(values.get("record_id", "")),
                pack,
                "缺少多变效率，且缺少用于计算的进口/出口压力、温度或绝热指数",
                efficiency_missing_fields,
            )
            result.actual_metrics = {}
            result.calculated_metrics.update(calculated)
            result.limits = dict(thresholds)
            return _attach_lookup_trace(result, pack, table_reference, refs)
        comparisons = []
        if "节能评价值" in thresholds:
            passed = actual >= decimal(thresholds["节能评价值"])
            comparisons.append({"level": Conclusion.SAVING_VALUE.value, "actual": str(actual), "direction": ">=", "threshold": str(thresholds["节能评价值"]), "passed": passed})
            if passed:
                conclusion = Conclusion.SAVING_VALUE
            else:
                conclusion = Conclusion.LIMIT_VALUE if actual >= decimal(thresholds["限定值"]) else Conclusion.NOT_COMPLIANT
        else:
            conclusion = Conclusion.LIMIT_VALUE if actual >= decimal(thresholds["限定值"]) else Conclusion.NOT_COMPLIANT
        comparisons.append({"level": Conclusion.LIMIT_VALUE.value, "actual": str(actual), "direction": ">=", "threshold": str(thresholds["限定值"]), "passed": actual >= decimal(thresholds["限定值"])})
        actual_metrics = {"多变效率_%": actual}
        if reported_efficiency is not None and raw_missing == []:
            actual_metrics["填报多变效率_%"] = decimal(reported_efficiency)
        table_reference = "/".join(item.get("table", "公式计算") for item in refs)
        clauses = list(dict.fromkeys(
            str(item.get("source_clause"))
            for item in refs
            if item.get("source_clause") not in (None, "")
        ))
        return _result(
            values,
            pack,
            conclusion,
            actual_metrics,
            calculated,
            thresholds,
            comparisons,
            table_reference,
            refs,
            clause="/".join(clauses) or table_reference,
        )
