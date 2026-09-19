"""GB 32030-2022潜水电泵评价器。"""
from __future__ import annotations

from decimal import Decimal
from typing import Any


class SubmersibleEvaluator:
    @staticmethod
    def _calculate_eta_db(values: dict[str, Any], pack: dict[str, Any]):
        """按GB/T25409附录A计算小型潜水电泵ηDB（仅精确档，不插值/外推）。"""
        from ..device_evaluators import _value
        from ..decimal_math import decimal

        calc = pack.get("product_standard_calculation") or {}
        if not calc or str(_value(values, "category", "设备类别") or "") != "小型潜水电泵":
            return None, {}, {"reason": "仅小型潜水电泵配置了GB/T25409附录A自动计算"}
        required = {
            "流量": ("flow_m3h", "流量"),
            "泵型": ("pump_form", "泵型", "安装型式"),
            "比转速": ("specific_speed", "比转速"),
        }
        missing = [label for label, aliases in required.items() if _value(values, *aliases) is None]
        if missing:
            return None, {"missing": missing}, {"reason": "GB/T25409附录A自动计算缺少参数"}
        try:
            flow = decimal(_value(values, *required["流量"]))
            ns = decimal(_value(values, *required["比转速"]))
            power = decimal(_value(values, "rated_power_kw", "额定功率"))
        except ValueError:
            return None, {}, {"reason": "流量、比转速或额定功率不是有效数值"}
        if flow <= 0 or ns <= 0 or power <= 0:
            return None, {}, {"reason": "流量、比转速和额定功率必须为正数"}
        form = {"下泵": "下泵式", "上泵": "上泵式"}.get(str(_value(values, *required["泵型"])).strip(), str(_value(values, *required["泵型"])).strip())
        if form not in {"下泵式", "上泵式", "QXL", "QXR"}:
            return None, {}, {"reason": "泵型必须明确为下泵式、上泵式、QXL或QXR"}
        flow_rows = calc.get("eta_sp_by_flow", {}).get(form, {})
        flow_key = next((key for key in flow_rows if decimal(key) == flow), None)
        if flow_key is None:
            return None, {}, {
                "reason": "流量不在GB/T25409附录A表A1离散档，标准未授权插值或外推",
                "lookup": {
                    "step_type": "精确查表",
                    "table": "GB/T25409-2010附录A表A1",
                    "data_id": f"GBT25409-A1-{form}",
                    "matching": f"泵型={form}; 输入流量={flow}m³/h",
                    "input_flow_m3h": str(flow),
                    "candidate_flow_m3h": [str(key) for key in flow_rows],
                    "match_status": "流量档未命中",
                    "no_interpolation": True,
                    "source_clause": "A.1",
                    "source_file": calc.get("source_file", ""),
                    "source_pages": calc.get("source_pages", ""),
                },
            }
        eta_sp = decimal(flow_rows[flow_key])
        family = "QXL/QXR" if form in {"QXL", "QXR"} else "普通型"
        delta_rows = calc.get("delta_by_specific_speed", {}).get(family, {})
        delta_key = next((key for key in delta_rows if "~" not in key and "≥" not in key and decimal(key) == ns), None)
        if delta_key is None and Decimal(120) <= ns <= Decimal(210):
            delta_key = "120~210"
        if delta_key is None and ns >= Decimal(500):
            delta_key = "≥500"
        if delta_key is None:
            return None, {}, {
                "reason": "比转速不在GB/T25409附录A表A2离散档，标准未授权插值或外推",
                "lookup": {
                    "step_type": "精确查表",
                    "table": "GB/T25409-2010附录A表A2",
                    "data_id": f"GBT25409-A2-{family}",
                    "matching": f"型式={form}; 输入比转速={ns}",
                    "input_specific_speed": str(ns),
                    "candidate_specific_speed": [str(key) for key in delta_rows],
                    "match_status": "比转速档未命中",
                    "no_interpolation": True,
                    "source_clause": "A.2",
                    "source_file": calc.get("source_file", ""),
                    "source_pages": calc.get("source_pages", ""),
                },
            }
        delta = decimal(delta_rows[delta_key])
        flow_match_status = "区间命中" if any(token in str(flow_key) for token in ("~", "≥", "≤", "<", ">")) else "精确命中"
        specific_speed_match_status = "区间命中" if any(token in str(delta_key) for token in ("~", "≥", "≤", "<", ">")) else "精确命中"
        # A1/A2已经完成离散查表后，后续还可能因缺少表4电动机效率条件
        # 而无法计算ηDB。把这两条成功查表记录单独保存，避免早退时只
        # 返回“缺少条件”而丢掉已经确定的标准依据。
        flow_lookup = {
            "step_type": "精确查表",
            "table": "GB/T25409-2010附录A表A1",
            "data_id": f"GBT25409-A1-{form}-{flow_key}",
            "matching": f"泵型={form}; 输入流量={flow}m³/h",
            "input_flow_m3h": str(flow),
            "matched_flow_m3h": str(flow_key),
            "standard_value_etaSP_%": str(eta_sp),
            "match_status": flow_match_status,
            "no_interpolation": True,
            "source_clause": "A.1",
            "source_file": calc.get("source_file", ""),
            "source_pages": calc.get("source_pages", ""),
        }
        specific_speed_lookup = {
            "step_type": "精确查表",
            "table": "GB/T25409-2010附录A表A2",
            "data_id": f"GBT25409-A2-{family}-{delta_key}",
            "matching": f"型式={form}; 输入比转速={ns}",
            "input_specific_speed": str(ns),
            "matched_specific_speed": str(delta_key),
            "standard_value_delta_eta_%": str(delta),
            "match_status": specific_speed_match_status,
            "no_interpolation": True,
            "source_clause": "A.2",
            "source_file": calc.get("source_file", ""),
            "source_pages": calc.get("source_pages", ""),
        }
        base_calculated = {
            "泵效率ηSP_%": eta_sp,
            "比转速修正Δη_%": delta,
            "泵效率ηB_%": eta_sp - delta,
        }

        def auto_failure(reason: str, missing: list[str] | None = None, extra_lookup: dict[str, Any] | None = None):
            failure_lookups = [flow_lookup, specific_speed_lookup]
            if extra_lookup:
                failure_lookups.append(extra_lookup)
            return None, {"missing": missing or [], "calculated_metrics": dict(base_calculated)}, {
                "reason": reason,
                "lookups": failure_lookups,
            }

        motor_eta_value = _value(values, "motor_efficiency", "电动机效率")
        motor_lookup = None
        if motor_eta_value is None:
            phase = str(_value(values, "motor_phase", "电动机相数", "相数") or "").strip()
            structure = str(_value(values, "motor_structure", "电动机结构", "电泵型式") or "").strip()
            speed_value = _value(values, "sync_speed_rpm", "同步转速", "rated_speed_rpm", "额定转速")
            if phase not in {"单相", "三相"} or structure not in {"充油式", "充水式", "干式"} or speed_value is None:
                missing = []
                if phase not in {"单相", "三相"}:
                    missing.append("电动机相数")
                if structure not in {"充油式", "充水式", "干式"}:
                    missing.append("电动机结构")
                if speed_value is None:
                    missing.append("同步转速")
                return auto_failure("缺少GB/T25409表4查电动机效率所需参数", missing)
            try:
                speed = decimal(speed_value)
            except ValueError:
                return auto_failure("同步转速不是有效数值", ["同步转速"])
            speed_key = "3000" if speed == Decimal(3000) else "1500" if speed == Decimal(1500) else ""
            power_key = next((key for key in calc.get("motor_efficiency_table4", {}) if decimal(key) == power), None)
            motor_key = f"{phase}|{structure}|{speed_key}" if speed_key else ""
            table_row = calc.get("motor_efficiency_table4", {}).get(power_key or "", {})
            motor_eta_value = table_row.get(motor_key)
            if motor_eta_value is None:
                motor_lookup = {
                    "step_type": "精确查表",
                    "table": "GB/T25409-2010表4",
                    "data_id": f"GBT25409-T4-P{power_key or 'NA'}",
                    "matching": f"功率={power_key or '未命中'}kW; {motor_key or '相数/结构/同步转速未形成有效组合'}",
                    "input_power_kw": str(power),
                    "candidate_power_kw": [str(key) for key in calc.get("motor_efficiency_table4", {})],
                    "match_status": "电动机效率档未命中",
                    "source_clause": "4.3.1、附录A.2",
                    "source_file": calc.get("source_file", ""),
                    "source_pages": calc.get("source_pages", ""),
                    "standard_marker": "—",
                    "no_data": True,
                    "dash_semantics": "—表示该组合不作要求或表中无数据，不等同于零",
                }
                return auto_failure(
                    "GB/T25409表4中该功率、相数、结构或同步转速组合为“—”或不在表内",
                    extra_lookup=motor_lookup,
                )
            motor_lookup = {
                "step_type": "精确查表",
                "table": "GB/T25409-2010表4",
                "data_id": f"GBT25409-T4-P{power_key}",
                "matching": f"功率={power_key}kW; {motor_key}",
                "match_status": "命中",
                "source_clause": "4.3.1、附录A.2",
                "source_file": calc.get("source_file", ""),
                "source_pages": calc.get("source_pages", ""),
            }
        try:
            motor_eta = decimal(motor_eta_value)
        except ValueError:
            return auto_failure("电动机效率不是有效数值", ["电动机效率"])
        if not Decimal(1) <= motor_eta <= Decimal(100):
            return auto_failure("电动机效率应按百分数本值填写且位于1~100", ["电动机效率"])
        eta_b = eta_sp - delta
        eta_db = eta_b * motor_eta / Decimal(100) - Decimal("1.5")
        if eta_db <= 0:
            return auto_failure("按附录A计算得到的ηDB不为正数")
        calculated = {"泵效率ηSP_%": eta_sp, "比转速修正Δη_%": delta, "泵效率ηB_%": eta_b, "电动机效率ηD_%": motor_eta, "规定效率ηDB_%": eta_db}
        lookup = {"step_type": "标准查表+公式计算", "table": "GB/T25409-2010附录A表A1、表A2、表4", "data_id": f"GBT25409-A1-{form}-{flow_key}-A2-{delta_key}", "matching": f"泵型={form}; 流量={flow_key}m³/h; 比转速={delta_key}; 电动机效率{('由表4查得' if motor_lookup else '为输入值')}", "formula": "ηB=ηSP−Δη；ηDB=ηB×ηD/100−1.5（百分数本值）", "source_clause": "A.1～A.2", "source_file": calc.get("source_file", ""), "source_pages": calc.get("source_pages", "")}
        if motor_lookup:
            lookup["motor_efficiency_lookup"] = motor_lookup
        return eta_db, calculated, lookup

    def evaluate(self, values: dict[str, Any], pack: dict[str, Any]):
        from ..device_evaluators import (
            _active_or_unable,
            _attach_lookup_trace,
            _attach_metrics,
            _interval_hit,
            _missing,
            _percent_or_unable,
            _positive_or_unable,
            _range_or_unable,
            _result,
            _value,
            out_of_scope,
            unable,
        )
        from ..decimal_math import decimal
        from ..grading import grade_three_optional
        from ...common.enums import ComparisonDirection

        if result := _active_or_unable(values, pack):
            return result
        missing = _missing(values, [("设备类别", ("category", "设备类别")), ("标准型式", ("subtype", "标准型式")), ("额定功率", ("rated_power_kw", "额定功率")), ("电泵效率", ("pump_efficiency", "电泵效率")), ("效率容差Δη", ("efficiency_tolerance", "效率容差"))])
        if missing:
            return unable(str(values.get("record_id", "")), pack, "潜水电泵缺少能效判定参数；不采用经验近似", missing)
        if result := _positive_or_unable(values, pack, [("额定功率", ("rated_power_kw", "额定功率"))]):
            return result
        if result := _range_or_unable(values, pack, "工作温度", ("working_temperature_c", "temperature", "工作温度"), Decimal(0), Decimal(100)):
            return result
        if result := _percent_or_unable(values, pack, "电泵效率", ("pump_efficiency", "电泵效率")):
            return result
        actual = decimal(_value(values, "pump_efficiency", "电泵效率"))
        actual_metrics = {"电泵效率_%": actual}
        calculated: dict[str, Any] = {}
        lookups: list[dict[str, Any]] = []

        def with_context(result, table: str = ""):
            """保留已算出的ηDB上下文及其引用标准查表记录。"""
            _attach_metrics(result, actual_metrics, calculated)
            if lookups:
                table_name = table or "/".join(str(item.get("table", "")) for item in lookups if isinstance(item, dict))
                return _attach_lookup_trace(result, pack, table_name, list(lookups))
            return result

        def table_data_id(table_row: dict[str, Any]) -> str:
            """返回标准包中表级稳定ID；旧包没有时才使用兼容回退。"""

            return str(table_row.get("data_id") or f"GB32030-{table_row.get('name', '')}")

        def power_row_lookup(
            table_row: dict[str, Any],
            *,
            subtype: str,
            match_status: str,
            input_power: Decimal,
            bin_index: int | None = None,
        ) -> dict[str, Any]:
            """保留功率档查询的候选范围和来源，不替未命中输入选档。"""

            ranges = table_row.get("power_ranges") or []
            table_id = table_data_id(table_row)
            subtype_list = table_row.get("subtypes") or []
            subtype_index = subtype_list.index(subtype) if subtype in subtype_list else None
            candidate_rows = []
            for index, expression in enumerate(ranges):
                candidate_rows.append({
                    "data_id": f"{table_id}-P{index + 1:02d}-S{(subtype_index + 1):02d}" if subtype_index is not None else f"{table_id}-P{index + 1:02d}",
                    "source_data_id": table_id,
                    "power_range": expression,
                    "subtype": subtype,
                    "source_pages": table_row.get("source_pages", ""),
                })
            lookup: dict[str, Any] = {
                "step_type": "精确查表",
                "table": table_row.get("name", ""),
                "data_id": (
                    candidate_rows[bin_index]["data_id"]
                    if bin_index is not None and 0 <= bin_index < len(candidate_rows)
                    else f"{table_id}-POWER-MISS"
                ),
                "source_data_id": table_id,
                "matching": "类别+标准型式+功率档",
                "input_power_kw": str(input_power),
                "subtype": subtype,
                "candidate_rows": candidate_rows,
                "candidate_data_ids": [row["data_id"] for row in candidate_rows],
                "match_status": match_status,
                "no_interpolation": True,
                "source_pages": table_row.get("source_pages", ""),
                "source_clause": table_row.get("source_clause") or table_row.get("name", ""),
            }
            return lookup

        specified_efficiency = _value(values, "specified_efficiency", "规定效率")
        if specified_efficiency is None:
            eta_db, auto_calculated, auto_lookup = self._calculate_eta_db(values, pack)
            if eta_db is None:
                result = unable(str(values.get("record_id", "")), pack, auto_lookup.get("reason", "无法按GB/T25409附录A计算规定效率ηDB"), auto_calculated.get("missing", []))
                auto_metrics = auto_calculated.get("calculated_metrics")
                if not isinstance(auto_metrics, dict):
                    auto_metrics = {}
                auto_lookups = auto_lookup.get("lookups")
                if not isinstance(auto_lookups, list):
                    lookup = auto_lookup.get("lookup")
                    auto_lookups = [lookup] if lookup else []
                if auto_lookups:
                    result.actual_metrics = dict(actual_metrics)
                    _attach_metrics(result, actual_metrics, auto_metrics)
                    table_name = "/".join(str(item.get("table", "")) for item in auto_lookups if isinstance(item, dict))
                    return _attach_lookup_trace(result, pack, table_name, auto_lookups)
                return _attach_metrics(result, actual_metrics, auto_metrics)
            specified_efficiency = eta_db
            calculated.update(auto_calculated)
            lookups.append(auto_lookup)
        else:
            if result := _percent_or_unable(values, pack, "规定效率ηDB", ("specified_efficiency", "规定效率")):
                return with_context(result)
        try:
            if decimal(_value(values, "efficiency_tolerance", "效率容差")) < 0:
                return with_context(unable(str(values.get("record_id", "")), pack, "效率容差不得为负数", ["效率容差Δη"]), "GB 32030-2022")
        except ValueError:
            return with_context(unable(str(values.get("record_id", "")), pack, "效率容差不是有效数值", ["效率容差Δη"]), "GB 32030-2022")
        category, subtype = str(_value(values, "category", "设备类别")), str(_value(values, "subtype", "标准型式"))
        power = decimal(_value(values, "rated_power_kw", "额定功率"))
        table = next((item for item in pack["tables"] if item["type"] == category and subtype in item["subtypes"]), None)
        if table is None:
            candidate_tables = [
                {
                    "data_id": table_data_id(item),
                    "table": item.get("name", ""),
                    "category": item.get("type", ""),
                    "subtypes": list(item.get("subtypes") or []),
                    "power_ranges": list(item.get("power_ranges") or []),
                    "source_pages": item.get("source_pages", ""),
                }
                for item in pack.get("tables", [])
            ]
            lookups.append({
                "step_type": "精确查表",
                "table": "表1/表2/表3/表4/表6",
                "data_id": "GB32030-TABLE-MISS",
                "matching": "设备类别+标准型式",
                "input_category": category,
                "input_subtype": subtype,
                "candidate_tables": candidate_tables,
                "candidate_data_ids": [item["data_id"] for item in candidate_tables],
                "match_status": "类别/型式未命中",
                "source_clause": "表1～表4、表6",
            })
            return with_context(out_of_scope(str(values.get("record_id", "")), pack, "潜水电泵类别或型式不在标准表"), "表1/表2/表3/表4/表6")
        # 功率档端点严格按GB 32030-2022表1～表4、表6原文处理。
        power_ranges = table.get("power_ranges") or []
        if len(power_ranges) == len(table.get("power_bins", [])):
            bin_idx = next((idx for idx, expression in enumerate(power_ranges) if _interval_hit(power, expression.replace("P_N", ""))), None)
        else:
            # 兼容旧标准包：仅在没有显式端点元数据时使用历史区间约定。
            bin_idx = next((idx for idx, limits in enumerate(table["power_bins"]) if decimal(limits[0]) < power <= decimal(limits[1]) or (idx == 0 and decimal(limits[0]) <= power <= decimal(limits[1]))), None)
        subtype_idx = table["subtypes"].index(subtype)
        if bin_idx is None:
            lookup = power_row_lookup(
                table,
                subtype=subtype,
                match_status="功率档未命中",
                input_power=power,
            )
            lookups.append(lookup)
            return with_context(out_of_scope(str(values.get("record_id", "")), pack, "额定功率不在标准范围"), table.get("name", ""))
        eta_db = decimal(specified_efficiency)
        tolerance = decimal(_value(values, "efficiency_tolerance", "效率容差"))
        offsets: list[Decimal | None] = []
        dash_levels: list[str] = []
        for level in ("1", "2"):
            level_rows = table.get("offsets", {}).get(level)
            if not isinstance(level_rows, list) or bin_idx >= len(level_rows) or level_rows[bin_idx] is None:
                offsets.append(None)
                dash_levels.append(level)
                continue
            row_offsets = level_rows[bin_idx]
            if subtype_idx >= len(row_offsets):
                return with_context(unable(str(values.get("record_id", "")), pack, f"标准表{table['name']}的型式列与偏移数据列数不一致"), table.get("name", ""))
            offset = row_offsets[subtype_idx]
            if offset is None:
                dash_levels.append(level)
                offsets.append(None)
            else:
                offsets.append(decimal(offset))
        thresholds: list[Decimal | None] = [eta_db + offset if offset is not None else None for offset in offsets] + [eta_db - tolerance]
        conclusion, comparisons = grade_three_optional(actual, thresholds, ComparisonDirection.GREATER_OR_EQUAL)
        calculated.update({"规定效率ηDB_%": eta_db, "效率容差Δη_%": tolerance})
        lookups.append({
            "step_type": "精确查表",
            "table": table["name"],
            "data_id": f"GB32030-{table['name']}-P{bin_idx + 1:02d}-S{subtype_idx + 1:02d}",
            "source_data_id": table_data_id(table),
            "matching": "类别+标准型式+功率档",
            "input_power_kw": str(power),
            "power_range": power_ranges[bin_idx] if power_ranges else "",
            "standard_dash_levels": dash_levels,
            "dash_semantics": "—表示该等级不作要求，不参与比较",
            "source_pages": table.get("source_pages", ""),
            "source_clause": table.get("source_clause") or table.get("name", ""),
            "query_conditions": {
                "category": category,
                "subtype": subtype,
                "rated_power_kw": str(power),
                "specified_efficiency": str(eta_db),
                "efficiency_tolerance": str(tolerance),
            },
            "match_status": "命中",
        })
        limits = {f"{i + 1}级效率_%": threshold for i, threshold in enumerate(thresholds) if threshold is not None}
        return _result(
            values,
            pack,
            conclusion,
            actual_metrics,
            calculated,
            limits,
            comparisons,
            table["name"],
            lookups,
            clause=table.get("source_clause") or table["name"],
        )
