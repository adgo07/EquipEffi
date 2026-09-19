"""GB 24500-2020工业锅炉评价器。"""
from __future__ import annotations

from decimal import Decimal
from typing import Any


class BoilerEvaluator:
    def evaluate(self, values: dict[str, Any], pack: dict[str, Any]):
        from ..device_evaluators import (
            _active_or_unable,
            _attach_lookup_trace,
            _attach_metrics,
            _condition_hit,
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
        from ..grading import grade_three
        from ...common.enums import ComparisonDirection, Conclusion

        if result := _active_or_unable(values, pack):
            return result
        missing = _missing(values, [("燃烧方式", ("combustion_method", "燃烧方式")), ("燃料品种", ("fuel", "燃料品种")), ("设计热效率", ("design_efficiency", "设计热效率"))])
        evaporation = _value(values, "evaporation_tph", "蒸发量")
        thermal_power = _value(values, "thermal_power_mw", "热功率")
        capacity = evaporation if evaporation is not None else thermal_power
        if capacity is None:
            missing.append("蒸发量或热功率")
        if missing:
            return unable(str(values.get("record_id", "")), pack, "缺少工业锅炉判定参数", missing)
        if result := _positive_or_unable(values, pack, [("蒸发量或热功率", ("evaporation_tph", "蒸发量", "thermal_power_mw", "热功率"))]):
            return result
        # D和Q均填写时，若两者落在标准不同容量列，不能静默选择其一。
        try:
            evaporation_value = decimal(evaporation) if evaporation is not None else None
            thermal_value = decimal(thermal_power) if thermal_power is not None else None
        except ValueError:
            return unable(str(values.get("record_id", "")), pack, "蒸发量或热功率不是有效数值", ["蒸发量或热功率"])
        if evaporation_value is not None and evaporation_value <= 0 or thermal_value is not None and thermal_value <= 0:
            return unable(str(values.get("record_id", "")), pack, "蒸发量和热功率必须为正数", ["蒸发量或热功率"])
        combustion, fuel = str(_value(values, "combustion_method", "燃烧方式")), str(_value(values, "fuel", "燃料品种"))
        category_text = str(_value(values, "category", "设备类别") or "")
        category_condensing: bool | None = None
        # V4完整设备类别（例如“室燃燃烧锅炉（燃气冷凝）”）本身带有
        # 冷凝属性。独立“是否冷凝”字段若另有填写，必须与类别一致；
        # 先保存类别语义，待标准表定位后再构造候选行并安全早退。
        if any(token in category_text for token in ("非冷凝", "无冷凝")):
            category_condensing = False
        elif "冷凝" in category_text:
            category_condensing = True
        condensing = str(_value(values, "condensing", "是否冷凝") or "")
        explicit_condensing = _value(values, "condensing", "是否冷凝") is not None
        condensing_token = condensing.strip().lower()
        if condensing_token in {"非冷凝", "无冷凝", "否", "no", "n", "false", "0"}:
            is_condensing = False
        elif condensing_token in {"是", "冷凝", "冷凝式", "yes", "y", "true", "1"}:
            is_condensing = True
        elif condensing_token:
            # 独立字段一旦填写，必须是受支持的枚举；只有真正留空时
            # 才允许从V4“设备类别”文字推断，避免无效值被静默吞掉。
            return unable(str(values.get("record_id", "")), pack, "是否冷凝不是有效枚举值", ["是否冷凝"])
        else:
            # 与V4ValidationService保持一致：独立字段为空时，允许从
            # 类别文字识别冷凝属性；否定词优先，避免“非冷凝”误命中。
            if any(token in category_text for token in ("非冷凝", "无冷凝")):
                is_condensing = False
            else:
                is_condensing = "冷凝" in category_text
        efficiency_max = 110 if is_condensing else 100
        if result := _range_or_unable(values, pack, "干燥无灰基挥发分", ("volatile_matter_percent", "vdaf", "干燥无灰基挥发分"), Decimal(0), Decimal(100)):
            return result
        if result := _percent_or_unable(values, pack, "设计热效率", ("design_efficiency", "设计热效率"), efficiency_max):
            return result
        actual = decimal(_value(values, "design_efficiency", "设计热效率"))
        actual_metrics = {"设计热效率_%": actual}
        # GB 24500-2020第5.2条对电加热锅炉只规定一个能效限定值（≥97%），
        # 没有1级/2级分档。V4用“电锅炉/电力”表达该产品，不能套用燃煤、燃气表。
        # 只能匹配规范枚举或已注册的直接API兼容值；不能用“文本中包含电”
        # 推断，否则“其他电源”等非法燃料会绕过燃料标准表直接得到3级。
        is_electric_boiler = fuel == "电力" or combustion in {"电加热锅炉", "电锅炉"}
        if is_electric_boiler:
            limit_spec = pack.get("electric_boiler_limit") or {}
            limit = limit_spec.get("efficiency")
            if limit is None:
                return unable(str(values.get("record_id", "")), pack, "标准包缺少电加热锅炉第5.2条能效限定值")
            threshold = decimal(limit)
            passed = actual >= threshold
            conclusion = Conclusion.LEVEL_3 if passed else Conclusion.NOT_COMPLIANT
            comparison = {
                "level": conclusion.value if passed else Conclusion.NOT_COMPLIANT.value,
                "actual": str(actual),
                "direction": ">=",
                "threshold": str(threshold),
                "passed": passed,
            }
            return _result(
                values,
                pack,
                conclusion,
                actual_metrics,
                {"电加热锅炉能效限定值_%": threshold},
                # 同时填入V4“3级热效率”结果列，明确它只是最低限定值的映射；
                # 1级/2级没有标准数值，保持为空而不是复制97%。
                {"能效限定值_%": threshold, "3级热效率_%": threshold},
                [comparison],
                "5.2",
                [{"step_type": "固定门槛", "table": "5.2", "source_page": limit_spec.get("source_page", 6), "matching": "电加热锅炉", "threshold": str(threshold), "direction": ">="}],
                clause="5.2",
            )
        # 燃烧方式是标准离散分类；只允许规范值与标准表type精确相等。
        # 子串命中会把“层状燃烧燃煤（扩展）”等未注册分类静默路由到
        # 表1，进而产生看似有效的能效等级。
        table = next((item for item in pack["tables"] if item["type"] == combustion), None)
        if table is None:
            lookup = {
                "step_type": "精确查表",
                "table": "表1～表4",
                "matching": "燃烧方式",
                "query_conditions": {"combustion_method": combustion, "fuel": fuel},
                "match_status": "燃烧方式未命中",
                "candidate_tables": [
                    {"table": item.get("name", ""), "type": item.get("type", ""), "source_page": item.get("source_page", "")}
                    for item in pack.get("tables", [])
                ],
                "source_clause": "表1～表4",
            }
            result = _attach_metrics(out_of_scope(str(values.get("record_id", "")), pack, "燃烧方式不在标准表"), actual_metrics)
            return _attach_lookup_trace(result, pack, "表1～表4", [lookup])
        if category_condensing is not None and explicit_condensing and category_condensing != is_condensing:
            expected = "冷凝" if category_condensing else "非冷凝"
            candidate_pool = [
                item for item in table.get("rows", [])
                if item.get("fuel") == fuel and item.get("class") in {"冷凝", "非冷凝"}
            ]
            if not candidate_pool:
                candidate_pool = [item for item in table.get("rows", []) if item.get("fuel") == fuel]
            lookup = {
                "step_type": "精确查表",
                "table": table.get("name", ""),
                "data_ids": [str(item.get("data_id")) for item in candidate_pool if item.get("data_id") not in (None, "")],
                "matching": "设备类别+燃料+是否冷凝",
                "query_conditions": {
                    "category": category_text,
                    "category_condensing": expected,
                    "fuel": fuel,
                    "condensing": condensing,
                },
                "category_condensing": expected,
                "condensing": condensing,
                "candidate_count": len(candidate_pool),
                "candidate_rows": [
                    {
                        "data_id": str(item.get("data_id", "")),
                        "fuel": item.get("fuel", ""),
                        "class": item.get("class", ""),
                        "q_cond": item.get("q_cond", ""),
                        "v_cond": item.get("v_cond", ""),
                    }
                    for item in candidate_pool
                ],
                "match_status": "类别与是否冷凝冲突",
                "source_clause": "表1～表4",
                "source_page": table.get("source_page", ""),
                "no_interpolation": True,
            }
            result = _attach_metrics(
                unable(str(values.get("record_id", "")), pack, f"设备类别中的{expected}与是否冷凝字段{condensing}冲突，无法唯一匹配标准行", ["设备类别/是否冷凝"]),
                actual_metrics,
            )
            return _attach_lookup_trace(result, pack, str(table.get("name", "")), [lookup])
        q = _value(values, "lower_heating_value_kjkg", "收到基低位发热量")
        v = _value(values, "volatile_matter_percent", "干燥无灰基挥发分")
        explicit_class = str(_value(values, "fuel_class", "燃料类别") or "")
        condensing_class = "冷凝" if is_condensing else "非冷凝" if condensing else ""
        fuel_class = explicit_class or condensing_class
        # “是否冷凝”和“燃料类别”同时填写时，两者都是标准表4的
        # 选行条件。若明确相互矛盾，不能静默优先其中一个字段后判级。
        # 保留同一燃料的冷凝/非冷凝候选行，交给用户补正输入。
        if explicit_class in {"冷凝", "非冷凝"} and condensing_class and explicit_class != condensing_class:
            candidate_pool = [
                item for item in table.get("rows", [])
                if item.get("fuel") == fuel and item.get("class") in {"冷凝", "非冷凝"}
            ]
            if not candidate_pool:
                candidate_pool = [item for item in table.get("rows", []) if item.get("fuel") == fuel]
            lookup = {
                "step_type": "精确查表",
                "table": table.get("name", ""),
                "data_ids": [str(item.get("data_id")) for item in candidate_pool if item.get("data_id") not in (None, "")],
                "matching": "燃烧方式+燃料+是否冷凝+燃料类别",
                "query_conditions": {
                    "combustion_method": combustion,
                    "fuel": fuel,
                    "condensing": condensing,
                    "fuel_class": explicit_class,
                    "lower_heating_value_kjkg": str(q) if q is not None else "",
                    "volatile_matter_percent": str(v) if v is not None else "",
                },
                "candidate_count": len(candidate_pool),
                "candidate_rows": [
                    {
                        "data_id": str(item.get("data_id", "")),
                        "fuel": item.get("fuel", ""),
                        "class": item.get("class", ""),
                        "q_cond": item.get("q_cond", ""),
                        "v_cond": item.get("v_cond", ""),
                    }
                    for item in candidate_pool
                ],
                "match_status": "冷凝条件冲突",
                "source_clause": "表1～表4",
                "source_page": table.get("source_page", ""),
            }
            result = _attach_metrics(
                unable(str(values.get("record_id", "")), pack, "是否冷凝与燃料类别相互冲突，无法唯一匹配标准行"),
                actual_metrics,
            )
            return _attach_lookup_trace(result, pack, str(table.get("name", "")), [lookup])
        candidates = [
            item for item in table["rows"]
            if item["fuel"] == fuel
            and (not fuel_class or not item.get("class") or item["class"] == fuel_class)
            and (not item.get("q_cond") or any(token in item.get("q_cond", "") for token in ("实际", "设计", "化验值")) or (q is not None and _condition_hit(q, item.get("q_cond", ""), "Q")))
            and (not item.get("v_cond") or (v is not None and _condition_hit(v, item.get("v_cond", ""), "V")))
        ]
        if len(candidates) != 1:
            # 当热值为有效数值、且在当前燃料/类别候选中没有任何一个
            # Q区间命中时，这是明确超出标准容量/热值范围，而不是
            # “热值缺失/挥发分缺失”导致的无法唯一选行。保持候选行
            # 证据不变，避免把标准表下限外输入误报为无法判定。
            q_out_of_scope = False
            if q is not None:
                try:
                    decimal(q)
                except (TypeError, ValueError):
                    pass
                else:
                    q_candidates = [
                        item for item in table.get("rows", [])
                        if item.get("fuel") == fuel
                        and (not fuel_class or not item.get("class") or item.get("class") == fuel_class)
                        and item.get("q_cond")
                        and not any(token in item.get("q_cond", "") for token in ("实际", "设计", "化验值"))
                    ]
                    q_out_of_scope = bool(q_candidates) and not any(
                        _condition_hit(q, item.get("q_cond", ""), "Q") for item in q_candidates
                    )
            candidate_pool = [
                item for item in table.get("rows", [])
                if item.get("fuel") == fuel
                and (not fuel_class or not item.get("class") or item.get("class") == fuel_class)
            ]
            if not candidate_pool:
                candidate_pool = list(table.get("rows", []))
            lookup = {
                "step_type": "精确查表",
                "table": table.get("name", ""),
                "data_ids": [str(item.get("data_id")) for item in candidate_pool if item.get("data_id") not in (None, "")],
                "matching": "燃烧方式+燃料+热值/挥发分+容量+冷凝条件",
                "query_conditions": {
                    "combustion_method": combustion,
                    "fuel": fuel,
                    "fuel_class": fuel_class,
                    "lower_heating_value_kjkg": str(q) if q is not None else "",
                    "volatile_matter_percent": str(v) if v is not None else "",
                },
                "candidate_count": len(candidates),
                "candidate_rows": [
                    {
                        "data_id": str(item.get("data_id", "")),
                        "fuel": item.get("fuel", ""),
                        "class": item.get("class", ""),
                        "q_cond": item.get("q_cond", ""),
                        "v_cond": item.get("v_cond", ""),
                    }
                    for item in candidate_pool
                ],
                "match_status": "标准行多重命中" if len(candidates) > 1 else "标准行未命中",
                "source_clause": "表1～表4",
                "source_page": table.get("source_page", ""),
            }
            if len(candidates) > 1:
                reason = "燃料热值、挥发分或类别匹配到多个标准行，无法唯一确定"
            elif q_out_of_scope:
                reason = "收到基低位发热量超出该燃料类别的标准适用范围"
            else:
                reason = "燃料热值、挥发分或类别不足以唯一匹配标准行"
            result_factory = out_of_scope if q_out_of_scope else unable
            result = _attach_metrics(
                result_factory(str(values.get("record_id", "")), pack, reason),
                actual_metrics,
            )
            return _attach_lookup_trace(result, pack, str(table.get("name", "")), [lookup])
        row = candidates[0]
        row_index = next((index for index, candidate in enumerate(table.get("rows", []), start=1) if candidate is row), None)
        row_lookup = {
            "step_type": "精确查表",
            "table": table["name"],
            "data_id": row.get("data_id") or (f"GB24500-{table['name']}-R{row_index:02d}" if row_index is not None else ""),
            "source_page": table.get("source_page", ""),
            "source_clause": "表1～表4",
            "matching": "燃烧方式+燃料+热值/挥发分+容量+冷凝条件",
            "fuel": fuel,
            "fuel_class": fuel_class,
            "q_condition": row.get("q_cond", ""),
            "v_condition": row.get("v_cond", ""),
            "query_conditions": {
                "combustion_method": combustion,
                "fuel": fuel,
                "fuel_class": fuel_class,
                "evaporation_tph": str(evaporation_value) if evaporation_value is not None else "",
                "thermal_power_mw": str(thermal_value) if thermal_value is not None else "",
                "lower_heating_value_kjkg": str(q) if q is not None else "",
                "volatile_matter_percent": str(v) if v is not None else "",
                "condensing": condensing,
            },
            "match_status": "命中",
        }
        capacity_value = decimal(capacity)
        cap_idx = 0
        if len(row["eff"]) > 1:
            basis = table.get("capacity_basis")
            if not isinstance(basis, list) or len(basis) < 2:
                result = _attach_metrics(unable(str(values.get("record_id", "")), pack, f"{table['name']}的容量列定义未配置"), actual_metrics)
                return _attach_lookup_trace(result, pack, table["name"], [row_lookup])
            limits_by_field = {str(item.get("field")): item.get("limit") for item in basis if isinstance(item, dict)}
            if "evaporation_tph" not in limits_by_field or "thermal_power_mw" not in limits_by_field:
                result = _attach_metrics(unable(str(values.get("record_id", "")), pack, f"{table['name']}的容量列单位定义不完整"), actual_metrics)
                return _attach_lookup_trace(result, pack, table["name"], [row_lookup])
            d_limit = decimal(limits_by_field["evaporation_tph"])
            q_limit = decimal(limits_by_field["thermal_power_mw"])
            d_high = evaporation_value is not None and evaporation_value > d_limit
            q_high = thermal_value is not None and thermal_value > q_limit
            if evaporation_value is not None and thermal_value is not None and d_high != q_high:
                result = _attach_metrics(unable(str(values.get("record_id", "")), pack, "蒸发量和热功率对应的标准容量列不一致，无法唯一选择指标"), actual_metrics)
                row_lookup.update({
                    "capacity_basis": "D(t/h)+Q(MW)",
                    "evaporation_limit_tph": str(d_limit),
                    "thermal_power_limit_mw": str(q_limit),
                    "match_status": "容量列不一致",
                })
                return _attach_lookup_trace(result, pack, table["name"], [row_lookup])
            cap_idx = 1 if (d_high or q_high) else 0
        thresholds = row["eff"][cap_idx]
        conclusion, comparisons = grade_three(actual, thresholds, ComparisonDirection.GREATER_OR_EQUAL)
        capacity_basis = "D(t/h)" if evaporation_value is not None else "Q(MW)"
        row_lookup.update({
            "capacity_basis": capacity_basis,
            "capacity_value": str(capacity_value),
            "thresholds": [str(value) for value in thresholds],
        })
        return _result(values, pack, conclusion, actual_metrics, {"容量判定基准": capacity_basis}, {f"{i+1}级热效率_%": thresholds[i] for i in range(3)}, comparisons, table["name"], [row_lookup], clause="表1～表4")
