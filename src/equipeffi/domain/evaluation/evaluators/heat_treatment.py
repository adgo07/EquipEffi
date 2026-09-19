"""GB/T 36561-2018热处理设备评价器。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ...common.enums import Conclusion


class HeatTreatmentEvaluator:
    def evaluate(self, values: dict[str, Any], pack: dict[str, Any]) -> EvaluationResult:
        from ..device_evaluators import (
            _active_or_unable,
            _attach_metrics,
            _attach_lookup_trace,
            _interval_hit,
            _missing,
            _positive_or_unable,
            _result,
            _value,
            out_of_scope,
            unable,
        )
        from ..decimal_math import decimal

        if result := _active_or_unable(values, pack):
            return result
        missing = _missing(values, [("设备类别", ("category", "设备类别")), ("能源类型", ("energy_type", "能源类型")), ("总折合重量", ("equivalent_weight_t", "总折合重量"))])
        if missing:
            return unable(str(values.get("record_id", "")), pack, "缺少热处理设备判定参数", missing)
        if result := _positive_or_unable(values, pack, [("总折合重量", ("equivalent_weight_t", "总折合重量"))]):
            return result
        energy = str(_value(values, "energy_type", "能源类型"))
        # V4的规范电炉枚举值为“电力”；“电炉”仅作为既有直接API的
        # 兼容别名。不能使用“文本中包含电”来推断能源路径，否则诸如
        # “其他电源”这类非法枚举会被静默当成电炉并直接得到等级。
        is_electric_energy = energy in {"电力", "电炉"}
        weight = decimal(_value(values, "equivalent_weight_t", "总折合重量"))
        missing_electricity = False
        missing_fuel_consumption = False
        missing_fuel_heat = False
        # 电炉路径不读取燃料热值，但后续统一构造表8查询证据时仍需
        # 安全地输出该输入项。先初始化为None，避免电炉路径访问未绑定局部变量。
        calorific_value: Decimal | None = None
        if is_electric_energy:
            consumed = _value(values, "total_electricity_kwh", "总耗电量")
            if consumed is None:
                # 总耗电量只参与可比单耗计算，不参与表8炉型/规格选择。
                # 先继续完成唯一标准行查找，避免在输入缺失时丢失可复核的
                # 一等、二等、三等阈值和来源；没有可靠能耗值时不生成比较。
                consumed_value = None
                comparable = None
                missing_electricity = True
            else:
                try:
                    consumed_value = decimal(consumed)
                except ValueError:
                    return unable(str(values.get("record_id", "")), pack, "总耗电量不是有效数值", ["总耗电量"])
                if consumed_value <= 0:
                    return unable(str(values.get("record_id", "")), pack, "总耗电量必须为正数", ["总耗电量"])
                comparable = consumed_value / weight
            unit = "kWh/t"
        else:
            consumed, calorific = _value(values, "fuel_consumption", "燃料总耗量"), _value(values, "fuel_calorific_value_kjkg", "燃料热值")
            if consumed is None and calorific is None:
                return unable(str(values.get("record_id", "")), pack, "燃料炉缺少燃料总耗量或燃料热值", ["燃料总耗量", "燃料热值"])
            missing_fuel_consumption = consumed is None
            missing_fuel_heat = calorific is None
            try:
                calorific_value = None if missing_fuel_heat else decimal(calorific)
                consumed_value = None if missing_fuel_consumption else decimal(consumed)
            except ValueError:
                return unable(str(values.get("record_id", "")), pack, "燃料总耗量或燃料热值不是有效数值", ["燃料总耗量", "燃料热值"])
            if (consumed_value is not None and consumed_value <= 0) or (calorific_value is not None and calorific_value <= 0):
                return unable(str(values.get("record_id", "")), pack, "燃料总耗量和燃料热值必须为正数", ["燃料总耗量", "燃料热值"])
            # GB/T 36561-2018表9按燃料品种给出折标系数α；燃气/燃油
            # 的热值单位与V4燃料耗量均为m³，不能默认α=1。
            coefficient_rows = [
                (index, item)
                for index, item in enumerate(pack.get("fuel_coefficients", []), start=1)
                if str(item.get("fuel", "")) == energy
            ]
            if not missing_fuel_heat and not coefficient_rows:
                # 仍然记录表9已经执行的燃料品种查找；这样“未知燃料”
                # 与其他提前终止分支一样，复核端可以看到比较过的原文行。
                lookup_rows = [
                    {
                        "step_type": "精确查表",
                        "table": "表9",
                        "source_clause": "表9",
                        "data_id": candidate.get("data_id") or f"GB36561-T9-{row_index:02d}",
                        "source_page": candidate.get("source_page", ""),
                        "fuel": candidate.get("fuel", ""),
                        "condition": candidate.get("condition", ""),
                        "candidate_alpha": str(candidate.get("alpha", "")),
                        "input_fuel": energy,
                        "input_fuel_calorific_value": "" if calorific_value is None else str(calorific_value),
                        "match_status": "燃料品种未命中",
                    }
                    for row_index, candidate in enumerate(pack.get("fuel_coefficients", []), start=1)
                ]
                result = unable(
                    str(values.get("record_id", "")),
                    pack,
                    "燃料品种不在GB/T 36561-2018表9，无法确定燃料系数α",
                    ["能源类型"],
                )
                return _attach_lookup_trace(result, pack, "表9", lookup_rows)
            # 表9的α与燃料热值区间绑定；燃料名称相同但热值越界时不能
            # 继续套用该系数，否则会把不适用的燃料折算结果判入等级。
            fuel_coefficient_candidates: list[dict[str, Any]] = []
            if missing_fuel_heat:
                fuel_coefficient_candidates = [
                    {
                        "data_id": candidate.get("data_id") or f"GB36561-T9-{row_index:02d}",
                        "fuel": candidate.get("fuel", energy),
                        "condition": candidate.get("condition", ""),
                        "candidate_alpha": str(candidate.get("alpha", "")),
                        "source_page": candidate.get("source_page", ""),
                        "match_status": "燃料热值未提供",
                    }
                    for row_index, candidate in coefficient_rows
                ]
                coefficient_candidates: list[tuple[int, dict[str, Any]]] = []
            else:
                coefficient_candidates = [
                    (index, item) for index, item in coefficient_rows
                    if _interval_hit(calorific_value, str(item.get("condition", "")))
                ]
            if not missing_fuel_heat and not coefficient_candidates:
                # 这是一次已经完成的标准查表，但输入没有命中表9的热值区间。
                # 不能伪造折标系数，也不能只返回范围结论而丢失查表证据；
                # 将每个同燃料候选行及其原文条件写入轨迹，供复核/导出端使用。
                lookup_rows = []
                for row_index, candidate in coefficient_rows:
                    lookup_rows.append({
                        "step_type": "精确查表",
                        "table": "表9",
                        "source_clause": "表9",
                        "data_id": candidate.get("data_id") or f"GB36561-T9-{row_index:02d}",
                        "source_page": candidate.get("source_page", ""),
                        "fuel": candidate.get("fuel", energy),
                        "condition": candidate.get("condition", ""),
                        "candidate_alpha": str(candidate.get("alpha", "")),
                        "input_fuel_calorific_value": "" if calorific_value is None else str(calorific_value),
                        "match_status": "未命中",
                    })
                result = out_of_scope(
                    str(values.get("record_id", "")),
                    pack,
                    "燃料热值不在GB/T 36561-2018表9对应区间，无法使用该燃料系数α",
                )
                return _attach_lookup_trace(result, pack, "表9", lookup_rows)
            if not missing_fuel_heat and len(coefficient_candidates) > 1:
                lookup_rows = [
                    {
                        "step_type": "精确查表",
                        "table": "表9",
                        "source_clause": "表9",
                        "data_id": candidate.get("data_id") or f"GB36561-T9-{row_index:02d}",
                        "source_page": candidate.get("source_page", ""),
                        "fuel": candidate.get("fuel", energy),
                        "condition": candidate.get("condition", ""),
                        "candidate_alpha": str(candidate.get("alpha", "")),
                        "input_fuel_calorific_value": "" if calorific_value is None else str(calorific_value),
                        "match_status": "多重命中",
                    }
                    for row_index, candidate in coefficient_candidates
                ]
                result = unable(
                    str(values.get("record_id", "")),
                    pack,
                    "燃料热值同时命中多个燃料系数α区间",
                    ["燃料热值"],
                )
                return _attach_lookup_trace(result, pack, "表9", lookup_rows)
            coefficient_index, coefficient = coefficient_candidates[0] if coefficient_candidates else (None, None)
            if not missing_fuel_heat and coefficient is None:
                return unable(str(values.get("record_id", "")), pack, "燃料品种不在GB/T 36561-2018表9，无法确定燃料系数α", ["能源类型"])
            alpha: Decimal | None = None
            if not missing_fuel_heat:
                try:
                    alpha = decimal(coefficient.get("alpha"))
                except (TypeError, ValueError):
                # 标准资源损坏或尚未完成校对时不能让单条评价抛出
                # Decimal异常，也不能把α默认为1。保留已命中的
                # 表9行、原始α和来源，交给标准数据校对流程处理。
                    lookup = {
                        "step_type": "精确查表",
                        "table": "表9",
                        "source_clause": "表9",
                        "data_id": coefficient.get("data_id") or f"GB36561-T9-{coefficient_index:02d}",
                        "source_page": coefficient.get("source_page", ""),
                        "fuel": coefficient.get("fuel", energy),
                        "condition": coefficient.get("condition", ""),
                        "candidate_alpha": str(coefficient.get("alpha", "")),
                        "input_fuel": energy,
                        "input_fuel_calorific_value": "" if calorific_value is None else str(calorific_value),
                        "match_status": "燃料系数无效",
                    }
                    result = unable(
                        str(values.get("record_id", "")),
                        pack,
                        "GB/T 36561-2018表9命中的燃料系数α不是有效数值，无法计算可比单耗",
                        ["燃料系数α"],
                    )
                    return _attach_lookup_trace(result, pack, "表9", [lookup])
            comparable = None if (missing_fuel_consumption or missing_fuel_heat) else consumed_value * calorific_value * alpha / (Decimal(29308) * weight)
            unit = "kgce/t"
        calculated_context: dict[str, Any] = {}
        actual_context: dict[str, Any] = {}
        if comparable is not None:
            calculated_context["可比单耗未舍入值"] = comparable
            actual_context["可比单耗"] = comparable
            actual_context["电炉可比单耗" if is_electric_energy else "燃料炉可比单耗"] = comparable
        if not is_electric_energy and alpha is not None:
            calculated_context.update({
                "燃料系数α": alpha,
                "燃料折标系数_kgce每原单位": alpha * decimal(calorific) / Decimal(29308),
            })
        category = str(_value(values, "category", "设备类别"))
        power = _value(values, "rated_power_kw", "额定功率")
        temperature = _value(values, "rated_temperature_c", "额定温度")
        energy_text = str(_value(values, "energy_type", "能源类型") or "")
        candidates = []
        selected_row_index = None
        for row_index, row in enumerate(pack["table8"], start=1):
            if row["furnace"] != category or row["unit"] != unit:
                continue
            specification = str(row.get("spec", ""))
            if not specification:
                candidates.append(row)
                continue
            if "电加热" in specification and not is_electric_energy:
                continue
            if "燃料加热" in specification and is_electric_energy:
                continue
            if "额定功率" in specification:
                if power is None or not _interval_hit(power, specification):
                    continue
            if "℃" in specification or "温度" in specification:
                if temperature is None or not _interval_hit(temperature, specification):
                    continue
            candidates.append(row)
        if len(candidates) != 1:
            spec = str(_value(values, "specification", "规格") or "")
            candidates = [row for row in candidates if row.get("spec") == spec]
        if len(candidates) != 1:
            candidate_pool = [
                row for row in pack.get("table8", [])
                if row.get("furnace") == category and row.get("unit") == unit
            ]
            if not candidate_pool:
                candidate_pool = list(pack.get("table8", []))
            candidate_rows = []
            for row_index, candidate in enumerate(candidate_pool, start=1):
                candidate_rows.append({
                    "data_id": candidate.get("data_id") or f"GB36561-T8-{row_index:02d}",
                    "furnace": candidate.get("furnace", ""),
                    "spec": candidate.get("spec", ""),
                    "unit": candidate.get("unit", ""),
                    "levels": [str(value) for value in candidate.get("level", [])],
                    "source_page": candidate.get("source_page", pack.get("table8_source_page", "")),
                })
            lookup = {
                "step_type": "精确查表",
                "table": "表8",
                "data_ids": [row["data_id"] for row in candidate_rows],
                "matching": "炉型+能源类型+规格（额定功率/额定温度）",
                "query_conditions": {
                    "furnace": category,
                    "energy_type": energy_text,
                    "rated_power_kw": str(power) if power is not None else "",
                    "rated_temperature_c": str(temperature) if temperature is not None else "",
                    "specification": spec,
                    "unit": unit,
                },
                "candidate_count": len(candidates),
                "candidate_rows": candidate_rows,
                "match_status": "炉型规格多重命中" if len(candidates) > 1 else "炉型规格未命中或条件不足",
                "no_interpolation": True,
                "source_page": candidate_rows[0]["source_page"] if candidate_rows else pack.get("table8_source_page", ""),
                "source_clause": "表8",
            }
            result = _attach_metrics(
                unable(
                    str(values.get("record_id", "")),
                    pack,
                    "无法唯一匹配炉型规格，请按标准规格填写",
                    ["总耗电量"] if missing_electricity else None,
                ),
                actual_context,
                calculated_context,
            )
            return _attach_lookup_trace(result, pack, "表8", [lookup])
        row = candidates[0]
        # table8当前为稳定的平铺顺序；记录行号作为可读数据ID，避免
        # 仅凭中文规格在校对册/判定轨迹中无法唯一定位标准行。
        for row_index, candidate in enumerate(pack["table8"], start=1):
            if candidate is row:
                selected_row_index = row_index
                break
        levels = (Conclusion.FIRST_CLASS, Conclusion.SECOND_CLASS, Conclusion.THIRD_CLASS)
        consumption_text = "" if consumed_value is None else str(consumed_value)
        calorific_text = "" if calorific_value is None else str(calorific_value)
        lookup = {
            "step_type": "公式计算" if comparable is not None else "精确查表",
            "rule": "电炉bk=W/Gz；燃料炉bk1=QDW×B×α/(29308×Gz)",
            # 优先使用标准包中与校对册对应的稳定 data_id；只有临时/旧
            # 测试包没有该字段时才用行号回退，不能用评价器生成的ID遮蔽
            # 机器标准记录本身的追溯ID。
            "data_id": row.get("data_id") or (f"GB36561-T8-{selected_row_index:02d}" if selected_row_index is not None else ""),
            "table": "表8",
            "source_clause": "表8",
            "match_status": "命中",
            "unit": unit,
            "specification": row.get("spec", ""),
            "source_page": pack.get("table8_source_page", 11),
            "inputs": {
                "equivalent_weight_t": str(weight),
                "energy_type": energy,
                "consumption": consumption_text,
            },
            "query_conditions": {
                "category": category,
                "energy_type": energy_text,
                "equivalent_weight_t": str(weight),
                "total_electricity_kwh": consumption_text if is_electric_energy else "",
                "fuel_consumption": consumption_text if not is_electric_energy else "",
                "fuel_calorific_value_kjkg": calorific_text if not is_electric_energy else "",
                "rated_power_kw": str(power) if power is not None else "",
                "rated_temperature_c": str(temperature) if temperature is not None else "",
                "specification": str(_value(values, "specification", "规格") or ""),
            },
            "thresholds": [str(value) for value in row["level"]],
        }
        limits = {levels[i].value: row["level"][i] for i in range(3)}
        if not is_electric_energy:
            lookup["inputs"].update({
                "fuel_calorific_value": calorific_text,
                "fuel_consumption": consumption_text,
            })
            if missing_fuel_heat:
                lookup.update({
                    "fuel_coefficient_match_status": "燃料热值未提供",
                    "fuel_coefficient_candidate_data_ids": [item["data_id"] for item in fuel_coefficient_candidates],
                    "fuel_coefficient_candidates": fuel_coefficient_candidates,
                    "fuel_coefficient_table": "表9",
                    "fuel_coefficient_source_clause": "表9",
                    "fuel_coefficient_source_page": [item["source_page"] for item in fuel_coefficient_candidates],
                })
            else:
                lookup.update({
                    "fuel_coefficient": str(alpha),
                    "fuel_coefficient_data_id": f"GB36561-T9-{coefficient_index:02d}",
                    "fuel_coefficient_table": "表9",
                    "fuel_coefficient_source_clause": "表9",
                    "fuel_coefficient_source_page": coefficient.get("source_page", ""),
                    "fuel_coefficient_condition": coefficient.get("condition", ""),
                })
        if missing_electricity:
            result = unable(
                str(values.get("record_id", "")),
                pack,
                "电炉缺少总耗电量，无法计算可比单耗或进行能效等级比较",
                ["总耗电量"],
            )
            result.limits = limits
            return _attach_lookup_trace(result, pack, "表8", [lookup])
        if missing_fuel_consumption:
            result = _attach_metrics(
                unable(
                    str(values.get("record_id", "")),
                    pack,
                    "燃料炉缺少燃料总耗量，无法计算可比单耗或进行能效等级比较",
                    ["燃料总耗量"],
                ),
                actual_context,
                calculated_context,
            )
            result.limits = limits
            return _attach_lookup_trace(result, pack, "表8", [lookup])
        if missing_fuel_heat:
            result = _attach_metrics(
                unable(
                    str(values.get("record_id", "")),
                    pack,
                    "燃料炉缺少燃料热值，无法确定燃料系数或进行能效等级比较",
                    ["燃料热值"],
                ),
                actual_context,
                calculated_context,
            )
            result.limits = limits
            return _attach_lookup_trace(result, pack, "表8", [lookup])
        comparisons, conclusion = [], Conclusion.NOT_COMPLIANT
        for level, threshold in zip(levels, row["level"]):
            passed = comparable <= decimal(threshold)
            comparisons.append({"level": level.value, "actual": str(comparable), "direction": "<=", "threshold": str(threshold), "passed": passed})
            if passed and conclusion is Conclusion.NOT_COMPLIANT:
                conclusion = level
        calculated = calculated_context
        actual_metrics = actual_context
        return _result(values, pack, conclusion, actual_metrics, calculated, limits, comparisons, "表8", [lookup], clause="表8")
